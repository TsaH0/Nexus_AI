"""
Demand Engine - Dual Demand Forecasting (CapEx + OpEx)
Combines project-based demand with operational/maintenance forecasting
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config import *
from src.core.models import Project, Material, DemandForecast, ProjectStatus
from src.core.bom_calculator import BOMCalculator
from src.intelligence.weather_service import WeatherService
from src.intelligence.sentinel_agent import SentinelAgent

try:
    from src.forecasting.prophet_forecaster import ProphetForecaster
    PROPHET_ENABLED = True
except ImportError:
    PROPHET_ENABLED = False
    print("⚠️ ProphetForecaster not available, using fallback forecasting")


class DemandEngine:
    """
    Advanced demand forecasting engine
    Combines CapEx (project-based) and OpEx (maintenance/operational) demand
    """
    
    def __init__(self, 
                 projects: List[Project] = None,
                 bom_calculator: BOMCalculator = None,
                 weather_service: WeatherService = None,
                 sentinel_agent: SentinelAgent = None):
        """
        Initialize demand engine
        
        Args:
            projects: Optional list of projects (for pre-loading)
            bom_calculator: Optional BOM calculator instance
            weather_service: Optional weather service instance
            sentinel_agent: Optional sentinel agent instance
        """
        self.projects = projects or []
        self.bom_calculator = bom_calculator or BOMCalculator()
        self.weather_service = weather_service or WeatherService()
        self.sentinel_agent = sentinel_agent or SentinelAgent()
        
        # Initialize Prophet forecaster for OpEx demand
        self.prophet_forecaster = None
        if PROPHET_ENABLED:
            try:
                self.prophet_forecaster = ProphetForecaster()
            except Exception as e:
                print(f"⚠️ Could not initialize Prophet: {e}")
        
        # Cache for performance
        self.demand_cache = {}
    
    def generate_forecast_for_all_projects(self,
                                          forecast_date: datetime,
                                          horizon_days: int = 30) -> List:
        """
        Generate demand forecasts for all projects
        
        Args:
            forecast_date: Date to forecast for
            horizon_days: Forecasting horizon in days
        
        Returns:
            List of ProjectDemandForecast objects
        """
        from dataclasses import dataclass, field
        
        @dataclass
        class ProjectDemandForecast:
            """Forecast result for a project"""
            project_id: str
            project_name: str
            region: str
            forecast_date: datetime
            capex_demand: Dict[str, int] = field(default_factory=dict)
            opex_demand: Dict[str, int] = field(default_factory=dict)
            total_demand: Dict[str, int] = field(default_factory=dict)
            reasoning: str = ""
        
        forecasts = []
        
        for project in self.projects:
            if not project.is_active():
                continue
            
            # Check RoW status
            row_status = self.sentinel_agent.check_row_status(project, forecast_date)
            if row_status.get('risk_level') == 'Critical':
                continue
            
            # Check weather viability
            weather = self.weather_service.assess_construction_viability(
                project, forecast_date, forecast_days=horizon_days
            )
            
            # Calculate CapEx demand for this project
            capex_demand = self.bom_calculator.calculate_capex_demand(project)
            
            # Apply delay factor if weather causes issues
            if weather.get('delay_days', 0) > 7:
                capex_demand = {k: int(v * 0.7) for k, v in capex_demand.items()}
            
            # Calculate total
            total_demand = dict(capex_demand)
            
            forecast = ProjectDemandForecast(
                project_id=project.id,
                project_name=project.name,
                region=project.region,
                forecast_date=forecast_date,
                capex_demand=capex_demand,
                opex_demand={},  # OpEx is calculated at region level, not project
                total_demand=total_demand,
                reasoning=f"Forecast for {project.name} ({project.stage.value} stage)"
            )
            
            forecasts.append(forecast)
        
        return forecasts
    
    def calculate_capex_demand(self,
                              projects: List[Project],
                              date: datetime,
                              region: Optional[str] = None,
                              material_filter: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Calculate Capital Expenditure demand from active projects
        
        Args:
            projects: List of projects
            date: Forecast date
            region: Optional region filter
            material_filter: Optional list of material IDs to calculate
        
        Returns:
            Dictionary mapping material_id to total quantity needed
        
        TODO: CAPEX ENHANCEMENTS
        1. Project stage probability modeling (% completion estimates)
        2. Historical deviation analysis (how accurate were past forecasts)
        3. Resource constraint modeling (can we actually use all materials)
        4. Project cancellation probability
        5. Scope change impact (expansions, modifications)
        6. Contractor capability assessment
        7. Funding availability checks
        8. Regulatory approval gating
        """
        
        total_demand = {}
        projects_included = []
        
        for project in projects:
            # Apply filters
            if region and project.region != region:
                continue
            
            if not project.is_active():
                continue
            
            # Check RoW status - critical for procurement decisions
            row_status = self.sentinel_agent.check_row_status(project, date)
            
            if row_status['risk_level'] == 'Critical':
                # RoW blocked - skip this project entirely
                continue
            
            # Check weather viability
            weather_assessment = self.weather_service.assess_construction_viability(
                project, date, forecast_days=30
            )
            
            if not weather_assessment['viable'] and weather_assessment['risk_level'] == 'High':
                # Weather will halt construction - reduce/defer demand
                continue
            
            # Calculate material requirements for this project
            project_materials = self.bom_calculator.calculate_capex_demand(project)
            
            # Apply weather delay factor
            # If weather causes delays, we may need materials later
            delay_factor = 1.0
            if weather_assessment['delay_days'] > 7:
                delay_factor = 0.7  # Reduce immediate demand by 30%
            
            # Aggregate to total demand
            for material_id, quantity in project_materials.items():
                if material_filter and material_id not in material_filter:
                    continue
                
                adjusted_qty = int(quantity * delay_factor)
                total_demand[material_id] = total_demand.get(material_id, 0) + adjusted_qty
            
            projects_included.append(project.id)
        
        # TODO: Apply project interdependency adjustments
        # Some projects may share materials or have sequence dependencies
        
        return total_demand
    
    def calculate_opex_demand(self,
                             date: datetime,
                             region: str,
                             materials: List[Material],
                             forecast_horizon_days: int = 30) -> Dict[str, int]:
        """
        Calculate Operational Expenditure demand (maintenance, spares, consumables)
        
        Args:
            date: Forecast date
            region: Region to forecast
            materials: List of materials to consider
            forecast_horizon_days: Forecasting horizon
        
        Returns:
            Dictionary mapping material_id to forecasted quantity
        
        TODO: OPEX ENHANCEMENTS
        1. Equipment age-based failure rate models
        2. Preventive maintenance scheduling integration
        3. Historical failure pattern analysis
        4. Seasonal equipment stress modeling
        5. Grid load-based wear prediction
        6. Warranty coverage optimization
        7. Repair vs replace decision models
        8. Cannibalization opportunity identification
        9. Emergency spare probability modeling
        10. Vendor lead time-based safety stock
        """
        
        opex_demand = {}
        
        for material in materials:
            # Only consumables and high-turnover items need OpEx forecasting
            # Capital equipment (transformers, switchgear) are CapEx
            if material.category in ["Oil", "Hardware", "Cement"]:
                
                # Get base forecast from Prophet (TODO: integrate actual Prophet model)
                base_forecast = self._get_prophet_forecast(
                    material_id=material.id,
                    region=region,
                    date=date,
                    horizon_days=forecast_horizon_days
                )
                
                # Apply weather multiplier
                weather_multiplier = self.weather_service.calculate_weather_demand_multiplier(
                    region=region,
                    date=date,
                    material_category=material.category
                )
                
                # Apply market sentiment multiplier
                sentiment_multiplier = self._get_sentiment_multiplier(region, date)
                
                # Final OpEx demand
                final_demand = int(base_forecast * weather_multiplier * sentiment_multiplier)
                opex_demand[material.id] = final_demand
        
        return opex_demand
    
    def _get_prophet_forecast(self,
                             material_id: str,
                             region: str,
                             date: datetime,
                             horizon_days: int) -> int:
        """
        Get Prophet-based forecast for a material
        
        Args:
            material_id: Material to forecast
            region: Region
            date: Forecast date
            horizon_days: Horizon
        
        Returns:
            Forecasted quantity
        """
        # Try to use Prophet forecaster if available
        if self.prophet_forecaster is not None:
            try:
                forecast_value = self.prophet_forecaster.get_forecast_for_date(
                    material_id=material_id,
                    region=region,
                    forecast_date=date,
                    horizon_days=horizon_days
                )
                if forecast_value > 0:
                    return forecast_value
            except Exception as e:
                # Fall back to baseline if Prophet fails
                pass
        
        # Fallback: Use simple seasonal baseline
        return self._get_baseline_forecast(material_id, date, horizon_days)
    
    def _get_baseline_forecast(self,
                              material_id: str,
                              date: datetime,
                              horizon_days: int) -> int:
        """
        Fallback baseline forecast when Prophet is not available
        
        Args:
            material_id: Material to forecast
            date: Forecast date
            horizon_days: Horizon
        
        Returns:
            Forecasted quantity
        """
        # Base monthly consumption estimate
        month = date.month
        base_qty = 500  # Base monthly consumption
        
        # Monsoon spike for certain materials
        if month in MONSOON_MONTHS:
            if "Hardware" in material_id or "Cement" in material_id or "MAT-020" in material_id:
                base_qty = int(base_qty * 1.3)
        
        # Summer spike for oils and insulators
        elif month in [4, 5, 6]:
            if "Oil" in material_id or "Insulator" in material_id or "MAT-018" in material_id:
                base_qty = int(base_qty * 1.4)
        
        # Scale to horizon
        return int(base_qty * (horizon_days / 30))
    
    def _get_sentiment_multiplier(self, region: str, date: datetime) -> float:
        """
        Get demand multiplier based on market sentiment
        
        Args:
            region: Region
            date: Date
        
        Returns:
            Multiplier (1.0 = normal)
        
        TODO: SENTIMENT IMPACT MODELING
        1. Price spike → advance procurement
        2. Strike → pre-positioning inventory
        3. Policy change → regulatory stock requirements
        """
        
        sentiments = self.sentinel_agent.scan_market_intelligence(date, region)
        
        multiplier = 1.0
        
        for sentiment in sentiments:
            if sentiment.topic == "Commodity_Price_Spike":
                # Anticipate rush buying
                multiplier *= 1.15
            elif sentiment.topic == "Labor_Strike":
                # Pre-position for disruption
                multiplier *= 1.10
        
        return multiplier
    
    def generate_demand_forecast(self,
                                 projects: List[Project],
                                 materials: List[Material],
                                 date: datetime,
                                 region: str,
                                 forecast_horizon_days: int = 30) -> Dict[str, DemandForecast]:
        """
        Generate comprehensive demand forecast combining CapEx and OpEx
        
        Args:
            projects: List of active projects
            materials: List of materials
            date: Forecast date
            region: Region to forecast
            forecast_horizon_days: Forecasting horizon
        
        Returns:
            Dictionary mapping material_id to DemandForecast object
        
        TODO: COMPREHENSIVE FORECASTING
        1. Multi-horizon forecasts (1 week, 1 month, 3 months)
        2. Confidence intervals (P10, P50, P90)
        3. Scenario analysis (best case, worst case, most likely)
        4. Sensitivity analysis (what-if scenarios)
        5. Forecast accuracy tracking and improvement
        6. Automatic model retraining based on actuals
        7. Collaborative forecasting (input from field teams)
        8. Demand sensing (real-time adjustments)
        """
        
        forecasts = {}
        
        # Calculate CapEx demand (project-based)
        capex_demand = self.calculate_capex_demand(
            projects=projects,
            date=date,
            region=region
        )
        
        # Calculate OpEx demand (operational/maintenance)
        opex_demand = self.calculate_opex_demand(
            date=date,
            region=region,
            materials=materials,
            forecast_horizon_days=forecast_horizon_days
        )
        
        # Combine and create forecast objects
        all_material_ids = set(capex_demand.keys()) | set(opex_demand.keys())
        
        for material_id in all_material_ids:
            capex_qty = capex_demand.get(material_id, 0)
            opex_qty = opex_demand.get(material_id, 0)
            
            # Get safety stock (TODO: integrate dynamic safety stock calculator)
            safety_buffer = self._calculate_safety_buffer(
                material_id=material_id,
                region=region,
                date=date,
                base_demand=capex_qty + opex_qty
            )
            
            total_demand = capex_qty + opex_qty + safety_buffer
            
            # Get weather and sentiment factors for XAI
            weather_mult = self.weather_service.calculate_weather_demand_multiplier(
                region=region,
                date=date,
                material_category=self._get_material_category(material_id, materials)
            )
            
            sentiment_mult = self._get_sentiment_multiplier(region, date)
            
            # Create forecast object with XAI reasoning
            reasoning = self._generate_forecast_reasoning(
                material_id=material_id,
                capex_qty=capex_qty,
                opex_qty=opex_qty,
                safety_buffer=safety_buffer,
                weather_mult=weather_mult,
                sentiment_mult=sentiment_mult
            )
            
            forecast = DemandForecast(
                material_id=material_id,
                region=region,
                forecast_date=date,
                forecast_horizon_days=forecast_horizon_days,
                capex_demand=capex_qty,
                opex_demand=opex_qty,
                safety_stock_buffer=safety_buffer,
                total_demand=total_demand,
                weather_multiplier=weather_mult,
                sentiment_multiplier=sentiment_mult,
                reasoning=reasoning
            )
            
            forecasts[material_id] = forecast
        
        return forecasts
    
    def _calculate_safety_buffer(self,
                                 material_id: str,
                                 region: str,
                                 date: datetime,
                                 base_demand: int) -> int:
        """
        Calculate safety stock buffer
        
        TODO: Implement dynamic safety stock calculation
        Currently uses simple percentage
        Real implementation in safety_stock.py
        
        Args:
            material_id: Material ID
            region: Region
            date: Date
            base_demand: Base demand quantity
        
        Returns:
            Safety buffer quantity
        """
        
        # Simple baseline: 20% buffer
        buffer_pct = BASE_SAFETY_STOCK_MULTIPLIER - 1.0  # 0.2
        
        # TODO: Apply dynamic adjustments based on:
        # - Lead time variability
        # - Demand variability
        # - Service level target
        # - Criticality of material
        # - Vendor reliability
        # - Seasonal risk factors
        
        return int(base_demand * buffer_pct)
    
    def _get_material_category(self, material_id: str, materials: List[Material]) -> str:
        """Get category for a material ID"""
        for mat in materials:
            if mat.id == material_id:
                return mat.category
        return "Unknown"
    
    def _generate_forecast_reasoning(self,
                                    material_id: str,
                                    capex_qty: int,
                                    opex_qty: int,
                                    safety_buffer: int,
                                    weather_mult: float,
                                    sentiment_mult: float) -> str:
        """
        Generate XAI reasoning for forecast
        
        Args:
            material_id: Material ID
            capex_qty: CapEx demand
            opex_qty: OpEx demand
            safety_buffer: Safety stock
            weather_mult: Weather multiplier
            sentiment_mult: Sentiment multiplier
        
        Returns:
            Human-readable explanation
        """
        
        explanation = f"Forecast for {material_id}:\n"
        explanation += f"  • Project Demand (CapEx): {capex_qty:,} units\n"
        explanation += f"  • Operational Demand (OpEx): {opex_qty:,} units\n"
        explanation += f"  • Safety Buffer: {safety_buffer:,} units\n"
        
        if weather_mult != 1.0:
            impact = "increased" if weather_mult > 1.0 else "decreased"
            explanation += f"  • Weather Impact: {impact} by {abs(weather_mult - 1.0):.1%}\n"
        
        if sentiment_mult != 1.0:
            impact = "increased" if sentiment_mult > 1.0 else "decreased"
            explanation += f"  • Market Sentiment: {impact} by {abs(sentiment_mult - 1.0):.1%}\n"
        
        return explanation
    
    def get_demand_trend(self,
                        material_id: str,
                        region: str,
                        start_date: datetime,
                        days: int = 30) -> List[Tuple[datetime, int]]:
        """
        Get demand trend over time
        
        Args:
            material_id: Material to analyze
            region: Region
            start_date: Start date
            days: Number of days
        
        Returns:
            List of (date, demand) tuples
        
        TODO: TREND ANALYSIS
        1. Moving average smoothing
        2. Trend decomposition (trend, seasonal, residual)
        3. Anomaly highlighting
        4. Comparative analysis (vs last year, vs plan)
        5. Forecast vs actual tracking
        """
        
        trend = []
        
        # TODO: Implement proper trend calculation
        # For now, generate simple trend
        for day_offset in range(days):
            date = start_date + timedelta(days=day_offset)
            # Placeholder - use actual forecast
            demand = 1000 + (day_offset * 10)  # Simple linear trend
            trend.append((date, demand))
        
        return trend


# TODO: FUTURE DEMAND ENGINE FEATURES
"""
PRODUCTION-READY ENHANCEMENTS:

1. ADVANCED FORECASTING TECHNIQUES
   - Ensemble methods (Prophet + ARIMA + LSTM)
   - Causal models (weather, prices, sentiment as features)
   - Intermittent demand forecasting (Croston's method)
   - Hierarchical forecasting (top-down, bottom-up, middle-out)
   - Multi-step ahead forecasting with uncertainty
   
2. MACHINE LEARNING INTEGRATION
   - Deep learning for complex patterns (LSTM, GRU)
   - Gradient boosting for feature-rich forecasting (XGBoost)
   - Transfer learning from other regions/materials
   - Online learning (continuous model updates)
   - AutoML for automatic model selection
   
3. REAL-TIME DEMAND SENSING
   - IoT sensor data (equipment health, usage patterns)
   - Point-of-sale data (for consumables)
   - Work order analysis (maintenance schedules)
   - Project management system integration
   - Field team feedback loops
   
4. COLLABORATIVE FORECASTING
   - Input from project managers
   - Vendor capacity feedback
   - Customer (end-user) input
   - Expert judgment incorporation
   - Consensus forecasting mechanisms
   
5. ADVANCED ANALYTICS
   - Forecast accuracy metrics (MAPE, RMSE, MAE)
   - Bias detection and correction
   - Forecast value added (FVA) analysis
   - Optimal forecast horizon determination
   - Forecast combination methods
   
6. SCENARIO PLANNING
   - What-if analysis tools
   - Monte Carlo simulation
   - Stress testing (extreme scenarios)
   - Sensitivity analysis dashboards
   - Risk-adjusted forecasting
   
7. OPTIMIZATION INTEGRATION
   - Demand shaping through pricing
   - Promotion and discount impact
   - Allocation optimization
   - Service level optimization
   - Total cost of ownership minimization
"""


if __name__ == "__main__":
    """Test demand engine"""
    from src.core.data_factory import DataFactory
    from datetime import datetime
    
    print("Testing Demand Engine...")
    print("="*70)
    
    # Load or generate data
    factory = DataFactory(seed=42)
    
    # Check if data exists, generate if not
    import pandas as pd
    projects_file = os.path.join(GENERATED_DATA_DIR, "projects.csv")
    if not os.path.exists(projects_file):
        print("Generating data first...")
        factory.generate_all()
    
    # Create engine
    engine = DemandEngine()
    
    # Test with mock data
    test_date = datetime(2025, 7, 15)
    region = "Northern"
    
    print(f"\nGenerating demand forecast for {region} on {test_date.strftime('%Y-%m-%d')}")
    print("(Using simplified mock data for testing)")
    
    # Create mock materials
    test_materials = [
        Material(id="MAT-001", name="Steel", category="Steel", unit="MT", base_price=55000),
        Material(id="MAT-018", name="Transformer_Oil", category="Oil", unit="KL", base_price=95000),
        Material(id="MAT-020", name="Hardware", category="Hardware", unit="Set", base_price=8500)
    ]
    
    # Test OpEx forecast
    opex = engine.calculate_opex_demand(test_date, region, test_materials)
    print(f"\nOpEx Demand Forecast:")
    for mat_id, qty in opex.items():
        print(f"  {mat_id}: {qty:,} units")
    
    print("\n✓ Demand engine test complete!")
    print("Note: Full functionality requires Prophet model integration")
