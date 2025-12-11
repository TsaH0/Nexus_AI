"""
Safety Stock Calculator - Dynamic Inventory Buffer Optimization
Calculates optimal safety stock levels based on demand variability and lead time uncertainty
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
from scipy import stats

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config import *


@dataclass
class SafetyStockRecommendation:
    """Safety stock calculation result"""
    material_id: str
    warehouse_id: str
    current_safety_stock: int
    recommended_safety_stock: int
    service_level: float  # Target service level (e.g., 0.95 = 95%)
    
    # Statistics
    avg_daily_demand: float
    demand_std_dev: float
    avg_lead_time_days: float
    lead_time_std_dev: float
    
    # Risk factors
    stockout_probability: float
    expected_shortage: float
    carrying_cost_increase: float
    
    reasoning: str
    adjustment_recommended: bool


class SafetyStockCalculator:
    """
    Advanced safety stock calculation using statistical methods
    
    TODO: PRODUCTION ENHANCEMENTS
    1. Machine learning for demand pattern recognition
    2. Seasonality-adjusted safety stock (higher in monsoon)
    3. Project-aware safety stock (critical path items)
    4. Multi-echelon optimization (network-wide)
    5. Cost-optimized service levels (balance stockout vs carrying cost)
    6. Real-time adjustment based on actual consumption
    7. ABC analysis integration (different service levels by importance)
    8. Vendor reliability-adjusted lead time
    9. RoW risk-adjusted buffers
    10. Weather-adjusted safety stock (monsoon, extreme heat)
    """
    
    def __init__(self, 
                 historical_data_path: Optional[str] = None,
                 default_service_level: float = 0.95):
        """
        Initialize safety stock calculator
        
        Args:
            historical_data_path: Path to historical consumption data
            default_service_level: Target service level (0.95 = 95% no stockout)
        
        TODO: INITIALIZATION ENHANCEMENTS
        1. Load vendor lead time statistics
        2. Load historical stockout data
        3. Configure service levels by material category
        4. Load cost parameters (holding cost, stockout cost)
        """
        
        self.historical_data_path = historical_data_path or os.path.join(
            DATA_DIR, "generated", "historical_consumption.csv"
        )
        self.default_service_level = default_service_level
        
        # Load historical data
        self.historical_data = self._load_historical_data()
        
        # Z-score lookup for service levels
        self.z_scores = {
            0.90: 1.28,  # 90% service level
            0.95: 1.65,  # 95% service level
            0.97: 1.88,  # 97% service level
            0.99: 2.33,  # 99% service level
            0.999: 3.09  # 99.9% service level
        }
    
    def _load_historical_data(self) -> pd.DataFrame:
        """
        Load historical consumption data
        
        Returns:
            DataFrame with consumption history
        
        TODO: DATA LOADING ENHANCEMENTS
        1. Include actual stockout events
        2. Include lead time data (order to delivery)
        3. Include demand spike indicators
        4. Data quality validation
        """
        
        if not os.path.exists(self.historical_data_path):
            print(f"⚠️ Historical data not found: {self.historical_data_path}")
            return pd.DataFrame()
        
        df = pd.read_csv(self.historical_data_path)
        df['date'] = pd.to_datetime(df['date'])
        
        return df
    
    def calculate_demand_statistics(self,
                                   material_id: str,
                                   warehouse_id: Optional[str] = None,
                                   days: int = 180) -> Tuple[float, float]:
        """
        Calculate average daily demand and standard deviation
        
        Args:
            material_id: Material to analyze
            warehouse_id: Specific warehouse (None = all warehouses)
            days: Number of days to analyze
        
        Returns:
            (avg_daily_demand, std_dev)
        
        TODO: DEMAND STATISTICS ENHANCEMENTS
        1. Remove outliers (Tukey's method)
        2. Trend-adjusted statistics
        3. Seasonal decomposition
        4. Demand pattern classification (stable, erratic, lumpy)
        5. Forecast-based demand (instead of historical)
        """
        
        # Filter data
        mask = self.historical_data['material_id'] == material_id
        
        if warehouse_id:
            mask &= self.historical_data['warehouse_id'] == warehouse_id
        
        # Get recent history
        cutoff_date = datetime.now() - timedelta(days=days)
        mask &= self.historical_data['date'] >= cutoff_date
        
        material_data = self.historical_data[mask]
        
        if material_data.empty:
            return 0.0, 0.0
        
        # Calculate statistics
        avg_demand = material_data['quantity'].mean()
        std_dev = material_data['quantity'].std()
        
        # Handle edge cases
        if pd.isna(avg_demand):
            avg_demand = 0.0
        if pd.isna(std_dev):
            std_dev = 0.0
        
        return avg_demand, std_dev
    
    def calculate_lead_time_statistics(self,
                                      material_id: str,
                                      vendor_id: Optional[str] = None) -> Tuple[float, float]:
        """
        Calculate average lead time and standard deviation
        
        Args:
            material_id: Material to analyze
            vendor_id: Specific vendor (None = all vendors)
        
        Returns:
            (avg_lead_time_days, std_dev_days)
        
        TODO: LEAD TIME STATISTICS ENHANCEMENTS
        1. Load actual historical lead times from order data
        2. Vendor-specific lead times
        3. Distance-adjusted lead times
        4. Seasonal lead time variations (monsoon delays)
        5. Lead time trend analysis
        6. Reliability-adjusted lead times
        """
        
        # TODO: Load from actual order history
        # For now, use vendor averages from config
        from src.core.data_factory import DataFactory
        
        factory = DataFactory(seed=42)
        
        # Find vendors supplying this material
        lead_times = []
        
        for vendor in factory.vendors:
            if material_id in vendor.material_prices:
                if vendor_id is None or vendor.id == vendor_id:
                    lead_times.append(vendor.avg_lead_time_days)
        
        if not lead_times:
            # Default fallback
            return 7.0, 2.0
        
        avg_lead_time = np.mean(lead_times)
        std_dev = np.std(lead_times) if len(lead_times) > 1 else avg_lead_time * 0.2
        
        return avg_lead_time, std_dev
    
    def calculate_safety_stock_basic(self,
                                    avg_daily_demand: float,
                                    demand_std_dev: float,
                                    avg_lead_time: float,
                                    service_level: float = 0.95) -> float:
        """
        Calculate safety stock using basic formula
        
        Formula: SS = Z × σ_demand × √(lead_time)
        
        Args:
            avg_daily_demand: Average daily demand
            demand_std_dev: Standard deviation of daily demand
            avg_lead_time: Average lead time in days
            service_level: Target service level (0.95 = 95%)
        
        Returns:
            Safety stock quantity
        
        TODO: FORMULA ENHANCEMENTS
        1. Incorporate lead time variability
        2. Non-normal demand distributions
        3. Correlated demand and lead time
        """
        
        # Get Z-score for service level
        z_score = self.z_scores.get(service_level, 1.65)
        
        # Basic formula
        safety_stock = z_score * demand_std_dev * np.sqrt(avg_lead_time)
        
        return max(0, safety_stock)
    
    def calculate_safety_stock_advanced(self,
                                       avg_daily_demand: float,
                                       demand_std_dev: float,
                                       avg_lead_time: float,
                                       lead_time_std_dev: float,
                                       service_level: float = 0.95) -> float:
        """
        Calculate safety stock with lead time variability
        
        Formula: SS = Z × √(σ_demand² × LT + demand² × σ_LT²)
        
        Args:
            avg_daily_demand: Average daily demand
            demand_std_dev: Standard deviation of daily demand
            avg_lead_time: Average lead time in days
            lead_time_std_dev: Standard deviation of lead time
            service_level: Target service level
        
        Returns:
            Safety stock quantity
        
        TODO: ADVANCED FORMULA ENHANCEMENTS
        1. Multi-echelon optimization
        2. Service level differentiation by material
        3. Cost-optimized service levels
        4. Dynamic safety stock (adjust by season)
        """
        
        # Get Z-score
        z_score = self.z_scores.get(service_level, 1.65)
        
        # Advanced formula accounting for both demand and lead time variability
        variance = (
            (demand_std_dev ** 2) * avg_lead_time +
            (avg_daily_demand ** 2) * (lead_time_std_dev ** 2)
        )
        
        safety_stock = z_score * np.sqrt(variance)
        
        return max(0, safety_stock)
    
    def calculate_stockout_probability(self,
                                      current_stock: int,
                                      avg_demand: float,
                                      demand_std_dev: float,
                                      lead_time: float) -> float:
        """
        Calculate probability of stockout given current inventory
        
        Args:
            current_stock: Current inventory level
            avg_demand: Average daily demand
            demand_std_dev: Demand standard deviation
            lead_time: Lead time in days
        
        Returns:
            Probability of stockout (0-1)
        
        TODO: STOCKOUT PROBABILITY ENHANCEMENTS
        1. Time-varying probability (by day)
        2. Severity-weighted probability (how bad is the stockout)
        3. Project impact analysis (critical path delays)
        """
        
        # Expected demand during lead time
        expected_demand = avg_demand * lead_time
        
        # Standard deviation during lead time
        demand_during_lt = demand_std_dev * np.sqrt(lead_time)
        
        if demand_during_lt == 0:
            return 0.0 if current_stock >= expected_demand else 1.0
        
        # Z-score for current stock
        z = (current_stock - expected_demand) / demand_during_lt
        
        # Probability of stockout (1 - CDF)
        stockout_prob = 1 - stats.norm.cdf(z)
        
        return stockout_prob
    
    def recommend_safety_stock(self,
                              material_id: str,
                              warehouse_id: str,
                              current_safety_stock: int,
                              service_level: Optional[float] = None,
                              use_advanced: bool = True) -> SafetyStockRecommendation:
        """
        Generate safety stock recommendation for a material at a warehouse
        
        Args:
            material_id: Material to analyze
            warehouse_id: Warehouse to analyze
            current_safety_stock: Current safety stock level
            service_level: Target service level (None = use default)
            use_advanced: Use advanced formula with lead time variability
        
        Returns:
            SafetyStockRecommendation object
        
        TODO: RECOMMENDATION ENHANCEMENTS
        1. Cost-benefit analysis (carrying cost vs stockout cost)
        2. Multi-material optimization (warehouse capacity)
        3. Seasonal recommendations (adjust by season)
        4. Project-driven recommendations (upcoming projects)
        5. ABC classification-based service levels
        """
        
        service_level = service_level or self.default_service_level
        
        # Get demand statistics
        avg_demand, demand_std = self.calculate_demand_statistics(
            material_id, warehouse_id
        )
        
        # Get lead time statistics
        avg_lead_time, lead_time_std = self.calculate_lead_time_statistics(
            material_id
        )
        
        # Calculate recommended safety stock
        if use_advanced:
            recommended_ss = self.calculate_safety_stock_advanced(
                avg_demand, demand_std, avg_lead_time, lead_time_std, service_level
            )
        else:
            recommended_ss = self.calculate_safety_stock_basic(
                avg_demand, demand_std, avg_lead_time, service_level
            )
        
        recommended_ss = int(np.ceil(recommended_ss))
        
        # Calculate stockout probability with current stock
        stockout_prob = self.calculate_stockout_probability(
            current_safety_stock, avg_demand, demand_std, avg_lead_time
        )
        
        # Calculate expected shortage (units)
        # TODO: Implement proper loss function
        expected_shortage = max(0, avg_demand * avg_lead_time - current_safety_stock)
        
        # Estimate carrying cost increase
        # TODO: Use actual carrying cost from config
        carrying_cost_per_unit = 100  # ₹100 per unit per year (simplified)
        additional_units = max(0, recommended_ss - current_safety_stock)
        carrying_cost_increase = additional_units * carrying_cost_per_unit
        
        # Generate reasoning
        reasoning = self._generate_safety_stock_reasoning(
            material_id, warehouse_id,
            current_safety_stock, recommended_ss,
            avg_demand, demand_std,
            avg_lead_time, stockout_prob,
            service_level
        )
        
        # Determine if adjustment is needed
        # Recommend change if difference > 10% or stockout risk > 10%
        pct_diff = abs(recommended_ss - current_safety_stock) / max(1, current_safety_stock)
        adjustment_needed = (pct_diff > 0.10) or (stockout_prob > 0.10)
        
        return SafetyStockRecommendation(
            material_id=material_id,
            warehouse_id=warehouse_id,
            current_safety_stock=current_safety_stock,
            recommended_safety_stock=recommended_ss,
            service_level=service_level,
            avg_daily_demand=avg_demand,
            demand_std_dev=demand_std,
            avg_lead_time_days=avg_lead_time,
            lead_time_std_dev=lead_time_std,
            stockout_probability=stockout_prob,
            expected_shortage=expected_shortage,
            carrying_cost_increase=carrying_cost_increase,
            reasoning=reasoning,
            adjustment_recommended=adjustment_needed
        )
    
    def _generate_safety_stock_reasoning(self,
                                        material_id: str,
                                        warehouse_id: str,
                                        current_ss: int,
                                        recommended_ss: int,
                                        avg_demand: float,
                                        demand_std: float,
                                        avg_lead_time: float,
                                        stockout_prob: float,
                                        service_level: float) -> str:
        """Generate human-readable reasoning"""
        
        reasoning_parts = []
        
        # Current vs recommended
        if recommended_ss > current_ss:
            diff = recommended_ss - current_ss
            pct = (diff / max(1, current_ss)) * 100
            reasoning_parts.append(
                f"Increase safety stock by {diff} units (+{pct:.1f}%)"
            )
        elif recommended_ss < current_ss:
            diff = current_ss - recommended_ss
            pct = (diff / max(1, current_ss)) * 100
            reasoning_parts.append(
                f"Reduce safety stock by {diff} units (-{pct:.1f}%)"
            )
        else:
            reasoning_parts.append("Current safety stock is optimal")
        
        # Demand pattern
        cv = (demand_std / max(0.01, avg_demand))  # Coefficient of variation
        if cv > 0.5:
            reasoning_parts.append("High demand variability (erratic)")
        elif cv > 0.3:
            reasoning_parts.append("Moderate demand variability")
        else:
            reasoning_parts.append("Stable demand pattern")
        
        # Lead time
        reasoning_parts.append(f"Lead time: {avg_lead_time:.1f} days")
        
        # Stockout risk
        if stockout_prob > 0.10:
            reasoning_parts.append(f"⚠️ HIGH stockout risk: {stockout_prob*100:.1f}%")
        elif stockout_prob > 0.05:
            reasoning_parts.append(f"Moderate stockout risk: {stockout_prob*100:.1f}%")
        else:
            reasoning_parts.append(f"Low stockout risk: {stockout_prob*100:.1f}%")
        
        # Service level
        reasoning_parts.append(f"Target: {service_level*100:.0f}% service level")
        
        return " | ".join(reasoning_parts)
    
    def optimize_warehouse_safety_stocks(self,
                                        warehouse_id: str,
                                        materials: List[str],
                                        max_capacity: Optional[int] = None) -> List[SafetyStockRecommendation]:
        """
        Optimize safety stocks for all materials in a warehouse
        
        Args:
            warehouse_id: Warehouse to optimize
            materials: List of material IDs
            max_capacity: Maximum warehouse capacity (units)
        
        Returns:
            List of recommendations
        
        TODO: WAREHOUSE OPTIMIZATION ENHANCEMENTS
        1. Capacity-constrained optimization
        2. Value-weighted optimization (expensive items first)
        3. ABC analysis (different service levels)
        4. Multi-objective optimization (minimize cost + maximize service)
        """
        
        recommendations = []
        
        for material_id in materials:
            # TODO: Get actual current safety stock from warehouse data
            current_ss = 50  # Placeholder
            
            rec = self.recommend_safety_stock(
                material_id, warehouse_id, current_ss
            )
            
            recommendations.append(rec)
        
        # Sort by adjustment priority (highest stockout risk first)
        recommendations.sort(key=lambda r: r.stockout_probability, reverse=True)
        
        return recommendations
    
    def generate_safety_stock_report(self,
                                    recommendations: List[SafetyStockRecommendation]) -> str:
        """
        Generate formatted safety stock report
        
        TODO: REPORTING ENHANCEMENTS
        1. Executive summary (total adjustments, cost impact)
        2. Priority ranking (critical adjustments)
        3. Visualization charts
        4. Historical comparison
        """
        
        if not recommendations:
            return "No recommendations available"
        
        report = "SAFETY STOCK OPTIMIZATION REPORT\n"
        report += "=" * 100 + "\n\n"
        
        # Summary statistics
        total_adjustments = sum(1 for r in recommendations if r.adjustment_recommended)
        total_cost_impact = sum(r.carrying_cost_increase for r in recommendations)
        
        report += f"Summary:\n"
        report += f"  Materials analyzed: {len(recommendations)}\n"
        report += f"  Adjustments recommended: {total_adjustments}\n"
        report += f"  Total carrying cost impact: ₹{total_cost_impact:,.0f}/year\n"
        report += "\n" + "=" * 100 + "\n\n"
        
        # Detail each recommendation
        report += f"{'Material':<15} {'Warehouse':<15} {'Current':<10} {'Recommended':<12} {'Change':<10} {'Risk':<8} {'Action'}\n"
        report += "-" * 100 + "\n"
        
        for rec in recommendations:
            if rec.adjustment_recommended:
                change = rec.recommended_safety_stock - rec.current_safety_stock
                change_str = f"{change:+d}"
                risk_str = f"{rec.stockout_probability*100:.1f}%"
                action = "⚠️ ADJUST" if abs(change) > 10 else "Monitor"
                
                report += (
                    f"{rec.material_id[:14]:<15} "
                    f"{rec.warehouse_id[:14]:<15} "
                    f"{rec.current_safety_stock:<10} "
                    f"{rec.recommended_safety_stock:<12} "
                    f"{change_str:<10} "
                    f"{risk_str:<8} "
                    f"{action}\n"
                )
        
        return report


# TODO: FUTURE SAFETY STOCK CALCULATOR FEATURES
"""
PRODUCTION-READY ENHANCEMENTS:

1. ADVANCED ALGORITHMS
   - Machine learning for demand forecasting
   - Multi-echelon optimization (network-wide)
   - Non-stationary demand modeling
   - Intermittent demand methods (Croston, TSB)
   - Service level cost optimization

2. DYNAMIC ADJUSTMENTS
   - Real-time safety stock updates
   - Seasonal safety stock profiles
   - Project-driven buffers (critical path)
   - Weather-adjusted safety stock
   - RoW risk-adjusted buffers

3. COST OPTIMIZATION
   - Carrying cost vs stockout cost tradeoff
   - Total cost of ownership (TCO) minimization
   - Value-based differentiation (ABC)
   - Obsolescence risk consideration
   - Working capital optimization

4. RISK MANAGEMENT
   - Vendor reliability integration
   - Supply chain disruption scenarios
   - Lead time volatility modeling
   - Demand spike detection
   - Early warning system

5. INTEGRATION
   - ERP system integration (SAP, Oracle)
   - Real-time inventory systems
   - Demand forecasting systems
   - Project scheduling systems
   - Financial planning systems

6. ANALYTICS
   - Service level achievement tracking
   - Stockout cost analysis
   - Inventory turn optimization
   - Dead stock identification
   - Inventory health dashboard
"""


if __name__ == "__main__":
    """Test safety stock calculator"""
    
    print("Testing Safety Stock Calculator...")
    print("="*70)
    
    # Create calculator
    calculator = SafetyStockCalculator(default_service_level=0.95)
    
    # Check if historical data exists
    if calculator.historical_data.empty:
        print("⚠️ No historical data found. Run data_factory.py first.")
    else:
        print(f"✓ Loaded {len(calculator.historical_data)} historical records")
        
        # Test materials
        materials = calculator.historical_data['material_id'].unique()[:5]
        test_warehouse = "WH-DELHI-001"
        
        print(f"\nAnalyzing safety stock for {len(materials)} materials...")
        
        recommendations = []
        for material_id in materials:
            rec = calculator.recommend_safety_stock(
                material_id=material_id,
                warehouse_id=test_warehouse,
                current_safety_stock=50,
                service_level=0.95
            )
            recommendations.append(rec)
        
        # Generate report
        report = calculator.generate_safety_stock_report(recommendations)
        print("\n" + report)
    
    print("\n✓ Safety stock calculator test complete!")
