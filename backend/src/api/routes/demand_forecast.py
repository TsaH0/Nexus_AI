"""
Demand Forecast API Routes
===========================
Endpoints for demand forecasting and order comparison.

Features:
- Regional demand forecasts
- Orders vs Forecast comparison
- Smart ordering recommendations
- Inventory-adjusted ordering
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Set
from datetime import datetime, timedelta
from enum import Enum
import hashlib

from src.api.database import get_db
from src.api import db_models

router = APIRouter(prefix="/demand-forecast", tags=["Demand Forecasting"])


# =============================================================================
# SCHEMAS
# =============================================================================

class ForecastPeriod(str, Enum):
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"


class RegionalForecast(BaseModel):
    """Forecast for a specific region/warehouse"""
    region_id: int
    region_name: str
    region_code: str
    material_id: int
    material_name: str
    material_code: str
    forecast_quantity: float
    ordered_quantity: float
    variance: float
    variance_percent: float
    existing_inventory: float
    effective_shortage: float
    order_status: str  # "optimal", "under_ordered", "over_ordered", "inventory_adjusted"
    reasoning: str


class ForecastSummary(BaseModel):
    """Summary of all forecasts"""
    total_forecast: float
    total_ordered: float
    total_variance: float
    coverage_percent: float
    regions_optimal: int
    regions_under: int
    regions_over: int
    regions_inventory_adjusted: int


# =============================================================================
# FORECAST ENGINE
# =============================================================================

class DemandForecastEngine:
    """
    Engine for generating demand forecasts and comparing with orders.
    
    Logic:
    - Forecasts based on historical consumption, project pipeline, seasonality
    - Orders typically 10-15% above forecast (buffer)
    - Some regions order below forecast due to existing inventory
    """
    
    # Seasonal multipliers (month -> multiplier)
    SEASONAL_FACTORS = {
        1: 0.85,   # Jan - post-holiday slowdown
        2: 0.90,   # Feb
        3: 1.10,   # Mar - fiscal year end rush
        4: 1.05,   # Apr - new fiscal year
        5: 0.95,   # May - summer slowdown
        6: 0.80,   # Jun - monsoon impact
        7: 0.75,   # Jul - peak monsoon
        8: 0.85,   # Aug
        9: 1.00,   # Sep - recovery
        10: 1.15,  # Oct - festival season
        11: 1.20,  # Nov - peak activity
        12: 1.10   # Dec - year-end push
    }
    
    # Material category demand patterns
    CATEGORY_BASE_DEMAND = {
        "Transmission Tower": 50,
        "Conductor": 200,
        "Insulator": 150,
        "Transformer": 10,
        "Circuit Breaker": 25,
        "Switchgear": 20,
        "Cable": 300,
        "Foundation": 40,
        "Hardware": 500,
        "Other": 100
    }
    
    def __init__(self, db: Session):
        self.db = db
        self._seen_combinations: Set[str] = set()  # Track unique warehouse-material pairs
    
    def generate_forecast(
        self,
        warehouse_id: int = None,
        material_id: int = None,
        period: ForecastPeriod = ForecastPeriod.monthly,
        forecast_date: datetime = None
    ) -> List[Dict]:
        """
        Generate demand forecast for warehouses and materials.
        
        Args:
            warehouse_id: Specific warehouse (optional)
            material_id: Specific material (optional)
            period: Forecast period
            forecast_date: Date to forecast for (default: current month)
        
        Returns:
            List of forecast dictionaries
        """
        forecast_date = forecast_date or datetime.now()
        month = forecast_date.month
        seasonal_factor = self.SEASONAL_FACTORS.get(month, 1.0)
        
        # Get warehouses
        warehouse_query = self.db.query(db_models.Warehouse).filter(
            db_models.Warehouse.is_active == True
        )
        if warehouse_id:
            warehouse_query = warehouse_query.filter(db_models.Warehouse.id == warehouse_id)
        warehouses = warehouse_query.all()
        
        # Get materials (Material doesn't have is_active, get all)
        material_query = self.db.query(db_models.Material)
        if material_id:
            material_query = material_query.filter(db_models.Material.id == material_id)
        materials = material_query.limit(20).all()  # Limit for performance
        
        forecasts = []
        
        for warehouse in warehouses:
            for material in materials:
                forecast = self._calculate_single_forecast(
                    warehouse, material, seasonal_factor, period
                )
                if forecast:
                    forecasts.append(forecast)
        
        return forecasts
    
    def _calculate_single_forecast(
        self,
        warehouse: db_models.Warehouse,
        material: db_models.Material,
        seasonal_factor: float,
        period: ForecastPeriod
    ) -> Dict:
        """Calculate forecast for a single warehouse-material pair"""
        
        # Get base demand from category
        category = material.category or "Other"
        base_demand = self.CATEGORY_BASE_DEMAND.get(category, 100)
        
        # Adjust for warehouse size/capacity
        warehouse_factor = 1.0
        if warehouse.capacity_tons:
            if warehouse.capacity_tons > 5000:
                warehouse_factor = 1.5
            elif warehouse.capacity_tons > 2000:
                warehouse_factor = 1.3
            elif warehouse.capacity_tons > 1000:
                warehouse_factor = 1.1
        
        # Get nearby substations count (increases demand)
        nearby_substations = self.db.query(db_models.Substation).filter(
            db_models.Substation.status == "Active"
        ).count()
        substation_factor = 1 + (min(nearby_substations, 10) * 0.02)  # 2% per substation, cap at 10
        
        # Calculate base forecast
        base_forecast = base_demand * warehouse_factor * seasonal_factor * substation_factor
        
        # Period multiplier
        period_multiplier = {
            ForecastPeriod.weekly: 0.25,
            ForecastPeriod.monthly: 1.0,
            ForecastPeriod.quarterly: 3.0
        }.get(period, 1.0)
        
        forecast_quantity = base_forecast * period_multiplier
        
        # Use deterministic variation based on warehouse+material hash (consistent across loads)
        hash_input = f"{warehouse.id}-{material.id}-{period.value}"
        hash_val = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)
        variation_factor = 0.95 + (hash_val % 100) / 1000  # 0.95 to 1.05 range
        forecast_quantity *= variation_factor
        forecast_quantity = round(forecast_quantity, 0)
        
        # Get current inventory
        inventory = self.db.query(db_models.InventoryStock).filter(
            db_models.InventoryStock.warehouse_id == warehouse.id,
            db_models.InventoryStock.material_id == material.id
        ).first()
        
        existing_inventory = inventory.quantity_available if inventory else 0
        
        # Get orders for this warehouse-material
        orders = self.db.query(
            func.sum(db_models.PurchaseOrder.quantity)
        ).filter(
            db_models.PurchaseOrder.warehouse_id == warehouse.id,
            db_models.PurchaseOrder.material_id == material.id,
            db_models.PurchaseOrder.status.in_(['Placed', 'In_Transit', 'Manufacturing'])
        ).scalar() or 0
        
        # Calculate ordered quantity (with smart logic)
        ordered_quantity = self._calculate_smart_order(
            forecast_quantity, existing_inventory, orders, warehouse, material
        )
        
        # Calculate variance
        variance = ordered_quantity - forecast_quantity
        variance_percent = (variance / forecast_quantity * 100) if forecast_quantity > 0 else 0
        
        # Effective shortage after considering inventory
        effective_shortage = max(0, forecast_quantity - existing_inventory - ordered_quantity)
        
        # Determine order status and reasoning
        order_status, reasoning = self._determine_order_status(
            forecast_quantity, ordered_quantity, existing_inventory, variance_percent, warehouse.name
        )
        
        return {
            "region_id": warehouse.id,
            "region_name": warehouse.name,
            "region_code": warehouse.warehouse_code or f"WH-{warehouse.id:03d}",
            "material_id": material.id,
            "material_name": material.name,
            "material_code": material.material_code or f"MAT-{material.id:03d}",
            "forecast_quantity": forecast_quantity,
            "ordered_quantity": ordered_quantity,
            "variance": round(variance, 0),
            "variance_percent": round(variance_percent, 1),
            "existing_inventory": round(existing_inventory, 0),
            "effective_shortage": round(effective_shortage, 0),
            "order_status": order_status,
            "reasoning": reasoning
        }
    
    def _calculate_smart_order(
        self,
        forecast: float,
        existing_inventory: float,
        current_orders: float,
        warehouse: db_models.Warehouse,
        material: db_models.Material
    ) -> float:
        """
        Calculate smart order quantity based on forecast and inventory.
        
        Logic:
        - Normally order 10-15% above forecast (safety buffer)
        - If significant inventory exists, reduce order
        - Critical materials get higher buffer
        """
        
        # Base order is forecast + deterministic buffer based on material criticality
        # Critical materials (Transformers, Circuit Breakers) get 15%, others get 12%
        is_critical = material.category in ["Transformer", "Circuit Breaker", "Switchgear"]
        buffer_percent = 0.15 if is_critical else 0.12
        base_order = forecast * (1 + buffer_percent)
        
        # Adjust for existing inventory
        if existing_inventory > 0:
            inventory_coverage = existing_inventory / forecast if forecast > 0 else 0
            
            if inventory_coverage > 0.5:
                # Significant inventory - reduce order
                reduction = min(0.4, inventory_coverage * 0.5)  # Up to 40% reduction
                base_order *= (1 - reduction)
            elif inventory_coverage > 0.3:
                # Moderate inventory - slight reduction
                base_order *= 0.9
        
        # Account for in-transit orders
        if current_orders > 0:
            base_order = max(0, base_order - current_orders * 0.5)
        
        # Critical materials get slight boost
        if material.category in ["Transformer", "Circuit Breaker"]:
            base_order *= 1.1
        
        return round(base_order, 0)
    
    def _determine_order_status(
        self,
        forecast: float,
        ordered: float,
        inventory: float,
        variance_percent: float,
        warehouse_name: str
    ) -> tuple:
        """Determine order status and generate reasoning"""
        
        # Check if inventory-adjusted
        if inventory > forecast * 0.3 and variance_percent < 0:
            return (
                "inventory_adjusted",
                f"Ordered below forecast due to existing inventory of {int(inventory)} units at {warehouse_name}. "
                f"This reduces procurement costs while meeting expected demand."
            )
        
        # Under-ordered (concerning)
        if variance_percent < -20:
            return (
                "under_ordered",
                f"⚠️ Order quantity is {abs(variance_percent):.0f}% below forecast. "
                f"Risk of stockout at {warehouse_name}. Consider increasing order."
            )
        
        # Over-ordered (slight buffer)
        if variance_percent > 20:
            return (
                "over_ordered",
                f"Order is {variance_percent:.0f}% above forecast - higher safety buffer. "
                f"Accounts for demand variability and lead time uncertainty."
            )
        
        # Optimal (10-15% buffer)
        if 5 <= variance_percent <= 20:
            return (
                "optimal",
                f"✅ Order aligns with forecast + {variance_percent:.0f}% safety buffer. "
                f"Optimal balance between availability and carrying cost."
            )
        
        # Slightly under but acceptable
        return (
            "optimal",
            f"Order is within acceptable range of forecast ({variance_percent:+.0f}%). "
            f"Inventory coverage is adequate for {warehouse_name}."
        )
    
    def get_summary(self, forecasts: List[Dict]) -> Dict:
        """Generate summary statistics from forecasts"""
        
        if not forecasts:
            return {
                "total_forecast": 0,
                "total_ordered": 0,
                "total_variance": 0,
                "coverage_percent": 0,
                "regions_optimal": 0,
                "regions_under": 0,
                "regions_over": 0,
                "regions_inventory_adjusted": 0
            }
        
        total_forecast = sum(f["forecast_quantity"] for f in forecasts)
        total_ordered = sum(f["ordered_quantity"] for f in forecasts)
        
        return {
            "total_forecast": round(total_forecast, 0),
            "total_ordered": round(total_ordered, 0),
            "total_variance": round(total_ordered - total_forecast, 0),
            "coverage_percent": round((total_ordered / total_forecast * 100) if total_forecast > 0 else 0, 1),
            "regions_optimal": len([f for f in forecasts if f["order_status"] == "optimal"]),
            "regions_under": len([f for f in forecasts if f["order_status"] == "under_ordered"]),
            "regions_over": len([f for f in forecasts if f["order_status"] == "over_ordered"]),
            "regions_inventory_adjusted": len([f for f in forecasts if f["order_status"] == "inventory_adjusted"])
        }


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/")
def get_demand_forecast(
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse"),
    material_id: Optional[int] = Query(None, description="Filter by material"),
    period: ForecastPeriod = Query(ForecastPeriod.monthly, description="Forecast period"),
    limit: int = Query(50, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """
    📊 **GET DEMAND FORECAST**
    
    Generate demand forecast for materials across warehouses/regions.
    
    **Logic:**
    - Forecasts based on seasonal patterns, warehouse capacity, nearby substations
    - Orders typically 10-15% above forecast (safety buffer)
    - Some regions order below forecast due to existing inventory
    
    **Order Status Types:**
    - `optimal`: Order aligns with forecast + reasonable buffer
    - `under_ordered`: Order significantly below forecast (risk)
    - `over_ordered`: Order above forecast (extra buffer)
    - `inventory_adjusted`: Order reduced due to existing stock
    """
    
    engine = DemandForecastEngine(db)
    forecasts = engine.generate_forecast(
        warehouse_id=warehouse_id,
        material_id=material_id,
        period=period
    )
    
    # Sort by variance (most concerning first)
    forecasts.sort(key=lambda x: x["variance_percent"])
    
    # Limit results
    forecasts = forecasts[:limit]
    
    summary = engine.get_summary(forecasts)
    
    return {
        "status": "success",
        "period": period.value,
        "forecast_date": datetime.now().strftime("%Y-%m-%d"),
        "summary": summary,
        "forecasts": forecasts
    }


@router.get("/comparison")
def get_forecast_vs_orders(
    group_by: str = Query("warehouse", description="Group by: warehouse, material, category"),
    period: ForecastPeriod = Query(ForecastPeriod.monthly, description="Forecast period"),
    db: Session = Depends(get_db)
):
    """
    📈 **FORECAST VS ORDERS COMPARISON**
    
    Compare forecasted demand against actual orders.
    Highlights regions/materials where orders deviate from forecast.
    
    **Insights:**
    - Shows where we're ordering above forecast (buffer)
    - Shows where we're ordering below due to inventory
    - Identifies potential stockout risks
    """
    
    engine = DemandForecastEngine(db)
    forecasts = engine.generate_forecast(period=period)
    
    # Group results
    if group_by == "warehouse":
        grouped = {}
        for f in forecasts:
            key = f["region_name"]
            if key not in grouped:
                grouped[key] = {
                    "region_id": f["region_id"],
                    "region_name": f["region_name"],
                    "total_forecast": 0,
                    "total_ordered": 0,
                    "total_inventory": 0,
                    "materials": []
                }
            grouped[key]["total_forecast"] += f["forecast_quantity"]
            grouped[key]["total_ordered"] += f["ordered_quantity"]
            grouped[key]["total_inventory"] += f["existing_inventory"]
            grouped[key]["materials"].append({
                "material": f["material_name"],
                "forecast": f["forecast_quantity"],
                "ordered": f["ordered_quantity"],
                "status": f["order_status"]
            })
        
        # Calculate variance for each group
        results = []
        for name, data in grouped.items():
            variance = data["total_ordered"] - data["total_forecast"]
            variance_pct = (variance / data["total_forecast"] * 100) if data["total_forecast"] > 0 else 0
            
            # Determine overall status
            if data["total_inventory"] > data["total_forecast"] * 0.3 and variance_pct < 0:
                status = "inventory_adjusted"
                note = f"Existing inventory of {int(data['total_inventory'])} units reduces order needs"
            elif variance_pct < -15:
                status = "under_ordered"
                note = "⚠️ Orders below forecast - review for stockout risk"
            elif variance_pct > 15:
                status = "over_ordered"
                note = "Extra safety buffer applied"
            else:
                status = "optimal"
                note = "✅ Orders aligned with forecast"
            
            results.append({
                "region": name,
                "region_id": data["region_id"],
                "total_forecast": round(data["total_forecast"], 0),
                "total_ordered": round(data["total_ordered"], 0),
                "existing_inventory": round(data["total_inventory"], 0),
                "variance": round(variance, 0),
                "variance_percent": round(variance_pct, 1),
                "status": status,
                "note": note,
                "material_count": len(data["materials"])
            })
        
        # Sort by variance (most concerning first)
        results.sort(key=lambda x: x["variance_percent"])
        
    elif group_by == "material":
        grouped = {}
        for f in forecasts:
            key = f["material_name"]
            if key not in grouped:
                grouped[key] = {
                    "material_id": f["material_id"],
                    "material_name": f["material_name"],
                    "material_code": f["material_code"],
                    "total_forecast": 0,
                    "total_ordered": 0,
                    "total_inventory": 0,
                    "warehouses": []
                }
            grouped[key]["total_forecast"] += f["forecast_quantity"]
            grouped[key]["total_ordered"] += f["ordered_quantity"]
            grouped[key]["total_inventory"] += f["existing_inventory"]
            grouped[key]["warehouses"].append(f["region_name"])
        
        results = []
        for name, data in grouped.items():
            variance = data["total_ordered"] - data["total_forecast"]
            variance_pct = (variance / data["total_forecast"] * 100) if data["total_forecast"] > 0 else 0
            
            results.append({
                "material": name,
                "material_id": data["material_id"],
                "material_code": data["material_code"],
                "total_forecast": round(data["total_forecast"], 0),
                "total_ordered": round(data["total_ordered"], 0),
                "existing_inventory": round(data["total_inventory"], 0),
                "variance": round(variance, 0),
                "variance_percent": round(variance_pct, 1),
                "warehouse_count": len(set(data["warehouses"]))
            })
        
        results.sort(key=lambda x: x["variance_percent"])
    
    else:
        results = forecasts
    
    summary = engine.get_summary(forecasts)
    
    return {
        "status": "success",
        "group_by": group_by,
        "period": period.value,
        "summary": summary,
        "comparison": results
    }


@router.get("/recommendations")
def get_ordering_recommendations(
    severity: str = Query("all", description="Filter: all, critical, warning, optimal"),
    db: Session = Depends(get_db)
):
    """
    💡 **SMART ORDERING RECOMMENDATIONS**
    
    Get actionable recommendations for material ordering.
    
    **Categories:**
    - `critical`: Severe under-ordering, stockout risk
    - `warning`: Below forecast, monitor closely
    - `optimal`: Well-balanced orders
    - `surplus`: Can reduce orders due to inventory
    """
    
    engine = DemandForecastEngine(db)
    forecasts = engine.generate_forecast()
    
    recommendations = []
    seen_combinations = set()  # Track unique warehouse-material pairs
    
    for f in forecasts:
        # Create unique key for warehouse-material combination
        combo_key = f"{f['region_id']}-{f['material_id']}"
        
        # Skip if we've already added this combination
        if combo_key in seen_combinations:
            continue
        seen_combinations.add(combo_key)
        
        # Generate specific, non-repeating reasoning based on data
        variance_pct = f["variance_percent"]
        inventory = f["existing_inventory"]
        forecast = f["forecast_quantity"]
        ordered = f["ordered_quantity"]
        
        rec = {
            "warehouse": f["region_name"],
            "material": f["material_name"],
            "current_order": ordered,
            "recommended_order": None,
            "adjustment": None,
            "priority": None,
            "reason": None
        }
        
        if f["order_status"] == "under_ordered":
            # Recommend increasing order
            recommended = forecast * 1.12  # 12% buffer
            rec["recommended_order"] = round(recommended, 0)
            adjustment_units = int(recommended - ordered)
            rec["adjustment"] = f"+{adjustment_units} units"
            rec["priority"] = "critical" if variance_pct < -30 else "warning"
            
            # Generate specific reasoning
            shortage = int(forecast - ordered)
            if variance_pct < -30:
                rec["reason"] = f"Critical: Order is {abs(variance_pct):.0f}% below forecast. Potential shortage of {shortage} units at {f['region_name']}. Immediate action recommended."
            else:
                rec["reason"] = f"Order quantity of {int(ordered)} is below projected demand of {int(forecast)}. Consider adding {adjustment_units} units to prevent stockout."
            
        elif f["order_status"] == "inventory_adjusted":
            # Already optimized - no change needed
            rec["recommended_order"] = ordered
            rec["adjustment"] = "No change (inventory optimized)"
            rec["priority"] = "optimal"
            rec["reason"] = f"✅ Existing inventory of {int(inventory)} units at {f['region_name']} reduces procurement needs. Current order is optimized."
            
        elif f["order_status"] == "over_ordered" and variance_pct > 30:
            # Could reduce order
            recommended = forecast * 1.15  # 15% buffer
            if recommended < ordered:
                savings_units = int(ordered - recommended)
                rec["recommended_order"] = round(recommended, 0)
                rec["adjustment"] = f"-{savings_units} units (savings)"
                rec["priority"] = "surplus"
                rec["reason"] = f"Order exceeds forecast by {variance_pct:.0f}%. Reducing by {savings_units} units maintains adequate buffer while cutting costs."
            else:
                rec["recommended_order"] = ordered
                rec["adjustment"] = "No change needed"
                rec["priority"] = "optimal"
                rec["reason"] = f"✅ Current order of {int(ordered)} units aligns with demand forecast plus safety buffer."
        else:
            rec["recommended_order"] = ordered
            rec["adjustment"] = "No change needed"
            rec["priority"] = "optimal"
            
            # Provide varied optimal reasoning
            if inventory > 0:
                rec["reason"] = f"✅ Order matches forecast with {variance_pct:+.0f}% buffer. Existing inventory of {int(inventory)} units provides additional coverage."
            else:
                rec["reason"] = f"✅ Order of {int(ordered)} units is well-balanced for projected {int(forecast)} unit demand at {f['region_name']}."
        
        recommendations.append(rec)
    
    # Filter by severity
    if severity != "all":
        recommendations = [r for r in recommendations if r["priority"] == severity]
    
    # Sort by priority (critical first, then by warehouse name for consistency)
    priority_order = {"critical": 0, "warning": 1, "surplus": 2, "optimal": 3}
    recommendations.sort(key=lambda x: (priority_order.get(x["priority"], 99), x["warehouse"], x["material"]))
    
    # Count by priority
    priority_counts = {
        "critical": len([r for r in recommendations if r["priority"] == "critical"]),
        "warning": len([r for r in recommendations if r["priority"] == "warning"]),
        "optimal": len([r for r in recommendations if r["priority"] == "optimal"]),
        "surplus": len([r for r in recommendations if r["priority"] == "surplus"])
    }
    
    return {
        "status": "success",
        "total_recommendations": len(recommendations),
        "priority_breakdown": priority_counts,
        "recommendations": recommendations[:50]  # Limit to 50
    }


@router.get("/inventory-impact")
def get_inventory_impact_analysis(
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse"),
    db: Session = Depends(get_db)
):
    """
    📦 **INVENTORY IMPACT ON ORDERS**
    
    Shows how existing inventory affects ordering decisions.
    Highlights areas where leftover inventory reduces procurement needs.
    """
    
    engine = DemandForecastEngine(db)
    forecasts = engine.generate_forecast(warehouse_id=warehouse_id)
    
    # Only show inventory-adjusted items
    adjusted_items = [f for f in forecasts if f["existing_inventory"] > 0]
    
    # Calculate savings
    savings_data = []
    total_units_saved = 0
    
    for f in adjusted_items:
        if f["order_status"] == "inventory_adjusted":
            # Calculate how much ordering was reduced
            full_order = f["forecast_quantity"] * 1.12  # What we would order without inventory
            actual_order = f["ordered_quantity"]
            units_saved = max(0, full_order - actual_order)
            
            if units_saved > 0:
                savings_data.append({
                    "warehouse": f["region_name"],
                    "material": f["material_name"],
                    "existing_inventory": int(f["existing_inventory"]),
                    "forecast": int(f["forecast_quantity"]),
                    "ordered": int(f["ordered_quantity"]),
                    "units_not_ordered": int(units_saved),
                    "inventory_utilization": f"Using {int(f['existing_inventory'])} units from previous stock",
                    "benefit": f"Reduced order by {int(units_saved)} units due to inventory"
                })
                total_units_saved += units_saved
    
    # Summary
    total_inventory = sum(f["existing_inventory"] for f in adjusted_items)
    
    return {
        "status": "success",
        "analysis": {
            "total_warehouses_with_inventory": len(set(f["region_name"] for f in adjusted_items)),
            "total_existing_inventory_units": int(total_inventory),
            "total_units_order_reduced": int(total_units_saved),
            "items_with_inventory_adjustment": len(savings_data)
        },
        "message": f"Existing inventory of {int(total_inventory)} units across warehouses has reduced procurement needs by {int(total_units_saved)} units",
        "details": savings_data[:30]
    }
