"""
Inventory Triggers Engine - The Mathematical Brain
Computes Safety Stock, Reorder Point, UTR, OTR, PAR, and Severity for materials.

This is the core intelligence that drives proactive inventory management.
All calculations are DYNAMIC based on nearby substations, demand patterns, and lead times.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from enum import Enum
from datetime import datetime, timedelta
import math


class Severity(Enum):
    """Alert severity levels - Traffic light system"""
    GREEN = "GREEN"      # All good, no action needed
    AMBER = "AMBER"      # Warning, monitor closely
    RED = "RED"          # Critical, immediate action required


@dataclass
class MaterialTriggers:
    """Computed triggers for a material at a location"""
    item_id: str
    item_name: str
    warehouse_code: str
    warehouse_name: str
    current_stock: float
    
    # Computed Metrics
    safety_stock: float          # SS: Minimum buffer stock
    reorder_point: float         # ROP: When to trigger reorder
    utr: float                   # Understock Ratio (0-1, higher = worse)
    otr: float                   # Overstock Ratio (0-1, higher = overstocked)
    par: float                   # Procurement Adequacy Ratio (0-1, higher = better)
    
    # Status
    severity: Severity
    label: str
    action: str
    
    # Additional context
    daily_demand: float
    lead_time_days: int
    days_of_stock: float
    nearby_substations: int
    demand_multiplier: float
    
    def to_dict(self) -> dict:
        """Convert to API response format"""
        return {
            "item_id": self.item_id,
            "item_name": self.item_name,
            "warehouse_code": self.warehouse_code,
            "warehouse_name": self.warehouse_name,
            "current_stock": self.current_stock,
            "metrics": {
                "safety_stock": round(self.safety_stock, 2),
                "reorder_point": round(self.reorder_point, 2),
                "utr": round(self.utr, 4),
                "otr": round(self.otr, 4),
                "par": round(self.par, 4)
            },
            "status": {
                "severity": self.severity.value,
                "label": self.label,
                "action": self.action
            },
            "context": {
                "daily_demand": round(self.daily_demand, 2),
                "lead_time_days": self.lead_time_days,
                "days_of_stock": round(self.days_of_stock, 2),
                "nearby_substations": self.nearby_substations,
                "demand_multiplier": round(self.demand_multiplier, 2)
            }
        }


@dataclass
class AlertFeedItem:
    """Alert item for the alerts feed"""
    alert_id: str
    material_code: str
    material_name: str
    site_code: str
    site_name: str
    utr: float
    par: float
    severity: Severity
    message: str
    recommended_action: str
    created_at: datetime
    
    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "material": {
                "code": self.material_code,
                "name": self.material_name
            },
            "site": {
                "code": self.site_code,
                "name": self.site_name
            },
            "utr": round(self.utr, 4),
            "par": round(self.par, 4),
            "severity": self.severity.value,
            "severity_badge": self._get_badge(),
            "message": self.message,
            "recommended_action": self.recommended_action,
            "created_at": self.created_at.isoformat()
        }
    
    def _get_badge(self) -> dict:
        badges = {
            Severity.RED: {"color": "#DC2626", "bg": "#FEE2E2", "text": "CRITICAL"},
            Severity.AMBER: {"color": "#D97706", "bg": "#FEF3C7", "text": "WARNING"},
            Severity.GREEN: {"color": "#059669", "bg": "#D1FAE5", "text": "OK"}
        }
        return badges.get(self.severity, badges[Severity.GREEN])


@dataclass 
class ProfitSummary:
    """Savings summary from inventory optimization"""
    expedite_savings: float      # Savings from avoiding rush orders
    holding_savings: float       # Savings from optimized stock levels
    total_savings: float
    
    # Breakdown
    rush_orders_avoided: int
    overstock_units_reduced: float
    optimal_orders_placed: int
    
    def to_dict(self) -> dict:
        return {
            "expedite_savings": round(self.expedite_savings, 2),
            "holding_savings": round(self.holding_savings, 2),
            "total_savings": round(self.total_savings, 2),
            "currency": "INR",
            "formatted": {
                "expedite_savings": self._format_currency(self.expedite_savings),
                "holding_savings": self._format_currency(self.holding_savings),
                "total_savings": self._format_currency(self.total_savings)
            },
            "breakdown": {
                "rush_orders_avoided": self.rush_orders_avoided,
                "overstock_units_reduced": round(self.overstock_units_reduced, 2),
                "optimal_orders_placed": self.optimal_orders_placed
            }
        }
    
    def _format_currency(self, amount: float) -> str:
        """Format amount in Indian currency style"""
        if amount >= 10000000:  # 1 Crore
            return f"₹{amount/10000000:.2f} Cr"
        elif amount >= 100000:  # 1 Lakh
            return f"₹{amount/100000:.2f} L"
        elif amount >= 1000:
            return f"₹{amount/1000:.2f} K"
        return f"₹{amount:.2f}"


class TriggersEngine:
    """
    The Mathematical Brain of NEXUS Inventory Management
    
    Computes dynamic inventory triggers based on:
    - Nearby substation demand
    - Historical consumption patterns
    - Material lead times
    - Seasonal factors
    - Project pipeline
    """
    
    # Constants for calculations
    SERVICE_LEVEL_Z = 1.65  # Z-score for 95% service level
    DEMAND_VARIABILITY = 0.25  # Default CV (coefficient of variation)
    HOLDING_COST_PERCENT = 0.20  # 20% annual holding cost
    EXPEDITE_PREMIUM = 0.35  # 35% premium for rush orders
    
    # Substation demand multipliers based on capacity
    SUBSTATION_DEMAND_WEIGHTS = {
        "765kV": 3.0,
        "400kV": 2.5,
        "220kV": 2.0,
        "132kV": 1.5,
        "66kV": 1.2,
        "33kV": 1.0,
        "22kV": 0.8,
        "11kV": 0.5
    }
    
    def __init__(self, db_session=None):
        self.db = db_session
    
    def compute_triggers(
        self,
        material_code: str,
        material_name: str,
        warehouse_code: str,
        warehouse_name: str,
        current_stock: float,
        lead_time_days: int,
        unit_price: float,
        nearby_substations: List[Dict] = None,
        historical_daily_demand: float = None,
        max_stock_level: float = None,
        min_stock_level: float = None
    ) -> MaterialTriggers:
        """
        Compute all inventory triggers for a material at a warehouse.
        
        This is the CORE function - the mathematical brain.
        """
        
        # 1. Calculate demand multiplier from nearby substations
        demand_multiplier = self._calculate_demand_multiplier(nearby_substations or [])
        
        # 2. Calculate base daily demand
        if historical_daily_demand is not None and historical_daily_demand > 0:
            base_daily_demand = historical_daily_demand
        elif min_stock_level and min_stock_level > 0:
            # Use min_stock_level (safety stock) to estimate demand
            # Safety stock ≈ demand * 7 days (our min buffer)
            base_daily_demand = min_stock_level / 7
        else:
            # Default: Fixed reasonable demand based on material type
            # Use a base of 5 units/day which is typical for grid materials
            base_daily_demand = 5.0
        
        # Apply substation demand multiplier
        adjusted_daily_demand = base_daily_demand * demand_multiplier

        
        # 3. Calculate Safety Stock (SS)
        # SS = Z × σd × √LT
        # Where: Z = service level z-score, σd = demand std dev, LT = lead time
        demand_std = adjusted_daily_demand * self.DEMAND_VARIABILITY
        safety_stock = self.SERVICE_LEVEL_Z * demand_std * math.sqrt(lead_time_days)
        safety_stock = max(safety_stock, adjusted_daily_demand * 7)  # Minimum 7 days buffer
        
        # 4. Calculate Reorder Point (ROP)
        # ROP = (Daily Demand × Lead Time) + Safety Stock
        reorder_point = (adjusted_daily_demand * lead_time_days) + safety_stock
        
        # 5. Calculate Understock Ratio (UTR)
        # UTR = max(0, (ROP - Current Stock) / ROP)
        # Range: 0 (fully stocked) to 1 (completely understocked)
        if reorder_point > 0:
            utr = max(0, (reorder_point - current_stock) / reorder_point)
        else:
            utr = 0.0
        
        # 6. Calculate Overstock Ratio (OTR)
        # OTR = max(0, (Current Stock - Max Stock) / Max Stock)
        # Range: 0 (not overstocked) to >1 (heavily overstocked)
        if max_stock_level is None or max_stock_level == 0:
            # Default max = ROP * 2.5
            max_stock_level = reorder_point * 2.5
        
        if max_stock_level > 0:
            otr = max(0, (current_stock - max_stock_level) / max_stock_level)
        else:
            otr = 0.0
        
        # 7. Calculate Procurement Adequacy Ratio (PAR)
        # PAR = Current Stock / (ROP + Buffer)
        # Range: 0 (need immediate procurement) to 1+ (adequately stocked)
        buffer = adjusted_daily_demand * 7  # 7 days buffer
        par = current_stock / (reorder_point + buffer) if (reorder_point + buffer) > 0 else 0
        par = min(par, 2.0)  # Cap at 2.0 for display
        
        # 8. Calculate Days of Stock
        days_of_stock = current_stock / adjusted_daily_demand if adjusted_daily_demand > 0 else 999
        
        # 9. Determine Severity and Actions
        severity, label, action = self._determine_severity(
            utr=utr, 
            otr=otr, 
            par=par, 
            days_of_stock=days_of_stock,
            lead_time_days=lead_time_days
        )
        
        return MaterialTriggers(
            item_id=material_code,
            item_name=material_name,
            warehouse_code=warehouse_code,
            warehouse_name=warehouse_name,
            current_stock=current_stock,
            safety_stock=safety_stock,
            reorder_point=reorder_point,
            utr=utr,
            otr=otr,
            par=par,
            severity=severity,
            label=label,
            action=action,
            daily_demand=adjusted_daily_demand,
            lead_time_days=lead_time_days,
            days_of_stock=days_of_stock,
            nearby_substations=len(nearby_substations or []),
            demand_multiplier=demand_multiplier
        )
    
    def _calculate_demand_multiplier(self, nearby_substations: List[Dict]) -> float:
        """
        Calculate demand multiplier based on nearby substations.
        More substations = higher demand for materials.
        Higher voltage substations = higher material consumption.
        """
        if not nearby_substations:
            return 1.0
        
        total_weight = 0.0
        for substation in nearby_substations:
            capacity = substation.get("capacity", "33kV")
            # Extract voltage from capacity string
            voltage_key = capacity.replace(" ", "").upper()
            for key in self.SUBSTATION_DEMAND_WEIGHTS:
                if key in voltage_key:
                    total_weight += self.SUBSTATION_DEMAND_WEIGHTS[key]
                    break
            else:
                total_weight += 1.0  # Default weight
        
        # Scale the multiplier (1 substation = 1.0, more = higher)
        multiplier = 1.0 + (total_weight - 1) * 0.2 if total_weight > 1 else 1.0
        return min(multiplier, 3.0)  # Cap at 3x
    
    def _determine_severity(
        self, 
        utr: float, 
        otr: float, 
        par: float,
        days_of_stock: float,
        lead_time_days: int
    ) -> Tuple[Severity, str, str]:
        """
        Determine severity level based on metrics.
        
        Decision Matrix:
        - RED: UTR > 0.5 OR days_of_stock < lead_time OR PAR < 0.3
        - AMBER: UTR > 0.3 OR days_of_stock < lead_time * 1.2 OR PAR < 0.6
        - GREEN: Everything else
        
        Thresholds are calibrated for realistic inventory management where
        most items should be in GREEN (optimal) state.
        """
        
        # Critical conditions (RED) - Only truly critical situations
        if utr > 0.7:
            return Severity.RED, "CRITICAL UNDERSTOCK", "Immediate Procurement Required"
        
        if days_of_stock < lead_time_days * 0.5:  # Less than half lead time
            return Severity.RED, "STOCKOUT RISK", f"Stock critically low - need {lead_time_days} days lead time"
        
        if par < 0.2:
            return Severity.RED, "PROCUREMENT INADEQUATE", "Current stock inadequate for projected demand"
        
        if otr > 1.5:
            return Severity.AMBER, "SEVERE OVERSTOCK", "Consider redistribution to other warehouses"
        
        # Warning conditions (AMBER)
        if utr > 0.4:
            return Severity.AMBER, "LOW STOCK", "Plan procurement soon"
        
        if days_of_stock < lead_time_days:
            return Severity.AMBER, "STOCK DECLINING", "Monitor and prepare to reorder"
        
        if par < 0.4:
            return Severity.AMBER, "MODERATE SHORTAGE", "Review procurement schedule"
        
        if otr > 0.8:
            return Severity.AMBER, "OVERSTOCKED", "Review incoming orders"
        
        # All good (GREEN)
        if otr > 0.3:
            return Severity.GREEN, "SLIGHTLY HIGH", "Stock levels acceptable but high"
        
        return Severity.GREEN, "OPTIMAL", "Stock levels are optimal"
    
    def generate_alerts_feed(
        self,
        triggers_list: List[MaterialTriggers],
        severity_filter: Optional[List[Severity]] = None
    ) -> List[AlertFeedItem]:
        """
        Generate alerts feed from computed triggers.
        Only includes items that need attention (AMBER or RED).
        """
        alerts = []
        
        for i, trigger in enumerate(triggers_list):
            # Filter by severity if specified
            if severity_filter and trigger.severity not in severity_filter:
                continue
            
            # Skip GREEN unless specifically requested
            if trigger.severity == Severity.GREEN and not severity_filter:
                continue
            
            alert = AlertFeedItem(
                alert_id=f"ALT-{datetime.now().strftime('%Y%m%d')}-{i+1:04d}",
                material_code=trigger.item_id,
                material_name=trigger.item_name,
                site_code=trigger.warehouse_code,
                site_name=trigger.warehouse_name,
                utr=trigger.utr,
                par=trigger.par,
                severity=trigger.severity,
                message=trigger.label,
                recommended_action=trigger.action,
                created_at=datetime.now()
            )
            alerts.append(alert)
        
        # Sort by severity (RED first, then AMBER)
        severity_order = {Severity.RED: 0, Severity.AMBER: 1, Severity.GREEN: 2}
        alerts.sort(key=lambda x: (severity_order[x.severity], -x.utr))
        
        return alerts
    
    def compute_profit_summary(
        self,
        triggers_list: List[MaterialTriggers],
        avg_unit_prices: Dict[str, float] = None
    ) -> ProfitSummary:
        """
        Calculate savings from inventory optimization.
        
        Savings come from:
        1. Avoiding rush/expedite orders (early detection)
        2. Reducing holding costs (avoiding overstock)
        3. Optimal order placement
        """
        
        expedite_savings = 0.0
        holding_savings = 0.0
        rush_orders_avoided = 0
        overstock_reduced = 0.0
        optimal_orders = 0
        
        avg_unit_prices = avg_unit_prices or {}
        default_price = 50000  # Default ₹50K per unit
        
        for trigger in triggers_list:
            unit_price = avg_unit_prices.get(trigger.item_id, default_price)
            
            # 1. Expedite Savings: Early detection prevents rush orders
            if trigger.severity == Severity.RED:
                # If we caught it early, we save the expedite premium
                shortage_units = max(0, trigger.reorder_point - trigger.current_stock)
                potential_rush_cost = shortage_units * unit_price * self.EXPEDITE_PREMIUM
                expedite_savings += potential_rush_cost
                if shortage_units > 0:
                    rush_orders_avoided += 1
            
            # 2. Holding Savings: Reducing overstock saves holding costs
            if trigger.otr > 0:
                max_stock = trigger.reorder_point * 2.5
                excess_units = max(0, trigger.current_stock - max_stock)
                # Annual holding cost saved if we reduce overstock
                holding_cost_per_unit = unit_price * self.HOLDING_COST_PERCENT
                holding_savings += excess_units * holding_cost_per_unit * (1/12)  # Monthly savings
                overstock_reduced += excess_units
            
            # 3. Count optimal orders (items in GREEN status)
            if trigger.severity == Severity.GREEN:
                optimal_orders += 1
        
        total_savings = expedite_savings + holding_savings
        
        return ProfitSummary(
            expedite_savings=expedite_savings,
            holding_savings=holding_savings,
            total_savings=total_savings,
            rush_orders_avoided=rush_orders_avoided,
            overstock_units_reduced=overstock_reduced,
            optimal_orders_placed=optimal_orders
        )


# Utility functions for distance/ETA calculations
def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def estimate_delivery_eta(
    distance_km: float,
    transport_mode: str = "road"
) -> Dict:
    """
    PLACEHOLDER: Estimate delivery time based on distance.
    This will be replaced with actual logistics API integration.
    
    Returns:
        - estimated_hours: Estimated delivery time in hours
        - estimated_days: Estimated delivery time in days
        - transport_mode: Mode of transport
        - is_estimated: True (since this is a placeholder)
    """
    # Average speeds by transport mode (km/h, accounting for loading/unloading)
    speeds = {
        "road": 40,       # Trucks avg 40 km/h including stops
        "rail": 25,       # Trains slower due to schedules
        "air": 300,       # Air freight
        "express": 60     # Express road delivery
    }
    
    speed = speeds.get(transport_mode, 40)
    
    # Calculate base travel time
    travel_hours = distance_km / speed
    
    # Add handling time (loading, unloading, customs if applicable)
    handling_hours = 4  # Base handling time
    if distance_km > 500:
        handling_hours += 8  # Additional time for long distance
    if distance_km > 1000:
        handling_hours += 12  # Cross-region logistics
    
    total_hours = travel_hours + handling_hours
    estimated_days = max(1, int(total_hours / 24) + 1)  # At least 1 day
    
    return {
        "distance_km": round(distance_km, 2),
        "estimated_hours": round(total_hours, 1),
        "estimated_days": estimated_days,
        "transport_mode": transport_mode,
        "is_placeholder": True,
        "note": "This is an estimate. Will be replaced with actual logistics API."
    }


def get_nearest_warehouse(
    user_lat: float,
    user_lon: float,
    warehouses: List[Dict]
) -> Tuple[Dict, float]:
    """
    Find the nearest warehouse to given coordinates.
    Returns warehouse and distance.
    """
    if not warehouses:
        return None, 0
    
    nearest = None
    min_distance = float('inf')
    
    for wh in warehouses:
        wh_lat = wh.get('latitude', 0)
        wh_lon = wh.get('longitude', 0)
        
        if wh_lat and wh_lon:
            distance = calculate_distance_km(user_lat, user_lon, wh_lat, wh_lon)
            if distance < min_distance:
                min_distance = distance
                nearest = wh
    
    return nearest, min_distance
