"""
Weather Service - Advanced Weather Impact Analysis
Provides coordinate-based weather forecasting and construction impact assessment
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config import *
from src.core.models import WeatherForecast, Project


class WeatherService:
    """
    Weather service with coordinate-based precision for construction impact assessment.
    
    In production, this would integrate with:
    - Real weather APIs (OpenWeatherMap, IMD)
    - Satellite/radar data
    - ML models for micro-climate prediction
    """
    
    def __init__(self):
        """Initialize weather service"""
        self.weather_data = self._load_weather_forecasts()
        self.coordinate_cache = {}  # Cache for coordinate-based lookups
    
    def _load_weather_forecasts(self) -> pd.DataFrame:
        """
        Load weather forecast data.
        
        In production, this would connect to real-time weather APIs.
        """
        weather_file = os.path.join(RAW_DATA_DIR, "Weather_Forecast_Master.csv")
        
        if not os.path.exists(weather_file):
            print(f"⚠️  Weather forecast file not found: {weather_file}")
            return pd.DataFrame()
        
        df = pd.read_csv(weather_file)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    
    def get_weather_for_location(self, 
                                 latitude: float, 
                                 longitude: float,
                                 date: datetime,
                                 radius_km: float = 50.0) -> Optional[WeatherForecast]:
        """
        Get weather forecast for specific coordinates
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            date: Date for forecast
            radius_km: Search radius for nearby weather stations
        
        Returns:
            WeatherForecast object or None
        
        TODO: COORDINATE-BASED IMPROVEMENTS
        1. Implement proper spatial interpolation (IDW, Kriging)
        2. Use multiple nearby stations with weighted averaging
        3. Account for topography (elevation models)
        4. Micro-climate detection (coastal, valley, mountain effects)
        5. Real-time sensor fusion (satellite + ground stations)
        6. Grid-based weather models (1km x 1km resolution)
        """
        
        # TODO: Current implementation uses region-based lookup (simplified)
        # In production, this should query actual weather APIs with coordinates
        
        cache_key = f"{latitude:.2f}_{longitude:.2f}_{date.strftime('%Y%m%d')}"
        if cache_key in self.coordinate_cache:
            return self.coordinate_cache[cache_key]
        
        # Simplified: Find nearest region
        # TODO: Replace with proper coordinate-based matching
        region = self._get_region_from_coordinates(latitude, longitude)
        
        if self.weather_data.empty or not region:
            return None
        
        # Get weather data for region and date
        forecast_data = self.weather_data[
            (self.weather_data['Date'] == date) &
            (self.weather_data['Region'] == region)
        ]
        
        if forecast_data.empty:
            return None
        
        # Use first state in region (TODO: improve with coordinate matching)
        row = forecast_data.iloc[0]
        
        forecast = WeatherForecast(
            date=date,
            region=row['Region'],
            state=row['State'],
            condition=row['Condition'],
            temperature_c=row['Temperature_C'],
            precipitation_mm=row['Precipitation_mm'],
            construction_delay_factor=WEATHER_IMPACT.get(row['Condition'], {}).get('construction_delay', 0.0),
            spares_demand_multiplier=WEATHER_IMPACT.get(row['Condition'], {}).get('spares_multiplier', 1.0)
        )
        
        self.coordinate_cache[cache_key] = forecast
        return forecast
    
    def _get_region_from_coordinates(self, latitude: float, longitude: float) -> Optional[str]:
        """
        Determine region from coordinates
        
        TODO: SPATIAL IMPROVEMENTS
        1. Use proper GIS polygon matching (Shapely, GeoPandas)
        2. Load Indian state boundary GeoJSON files
        3. Implement point-in-polygon algorithms
        4. Handle border cases and overlapping regions
        5. Support for offshore locations
        """
        
        # Simplified region detection based on rough coordinate ranges
        # TODO: Replace with proper GIS boundary files
        
        # Northern: Lat 28-35, Lon 72-80
        if 28 <= latitude <= 35 and 72 <= longitude <= 80:
            return "Northern"
        
        # Western: Lat 15-25, Lon 68-77
        elif 15 <= latitude <= 25 and 68 <= longitude <= 77:
            return "Western"
        
        # Eastern: Lat 20-27, Lon 83-92
        elif 20 <= latitude <= 27 and 83 <= longitude <= 92:
            return "Eastern"
        
        # Southern: Lat 8-20, Lon 72-82
        elif 8 <= latitude <= 20 and 72 <= longitude <= 82:
            return "Southern"
        
        # North-Eastern: Lat 23-29, Lon 88-97
        elif 23 <= latitude <= 29 and 88 <= longitude <= 97:
            return "North-Eastern"
        
        # Default to nearest
        return "Northern"
    
    def get_weather_for_project(self, project: Project, date: datetime) -> Optional[WeatherForecast]:
        """
        Get weather forecast for a project location
        
        Args:
            project: Project object with coordinates
            date: Forecast date
        
        Returns:
            WeatherForecast object
        """
        return self.get_weather_for_location(
            project.latitude,
            project.longitude,
            date
        )
    
    def assess_construction_viability(self, 
                                     project: Project, 
                                     date: datetime,
                                     forecast_days: int = 7) -> Dict[str, any]:
        """
        Assess if construction is viable based on weather forecast
        
        Args:
            project: Project to assess
            date: Assessment date
            forecast_days: Number of days to forecast ahead
        
        Returns:
            Dictionary with viability assessment
        
        TODO: ADVANCED ASSESSMENTS
        1. Activity-specific weather requirements (foundation vs tower erection)
        2. Soil moisture impact on foundation work
        3. Wind speed limits for crane operations
        4. Lightning risk for high-voltage work
        5. Heat stress index for worker safety
        6. Visibility requirements for precision work
        7. Equipment-specific weather constraints
        8. Multi-day weather window detection
        """
        
        results = {
            'viable': True,
            'risk_level': 'Low',
            'delay_days': 0,
            'reasons': [],
            'recommended_actions': []
        }
        
        delay_days = 0
        reasons = []
        
        for day_offset in range(forecast_days):
            forecast_date = date + timedelta(days=day_offset)
            weather = self.get_weather_for_project(project, forecast_date)
            
            if not weather:
                continue
            
            # Check construction delay factor
            if weather.construction_delay_factor > 0.3:
                delay_days += 1
                reasons.append(f"{weather.condition} on {forecast_date.strftime('%Y-%m-%d')}")
            
            # Extreme conditions
            if weather.condition == "Heavy_Rain":
                if day_offset < 3:  # Next 3 days critical
                    results['viable'] = False
                    results['risk_level'] = 'High'
                    reasons.append("Heavy rain forecast - halt outdoor work")
            
            # Temperature extremes
            # TODO: Add heat stress calculations, cold weather concrete curing issues
            if weather.temperature_c > 45:
                reasons.append(f"Extreme heat ({weather.temperature_c}°C) - worker safety concern")
                results['risk_level'] = 'Medium' if results['risk_level'] == 'Low' else 'High'
            
            elif weather.temperature_c < 5:
                reasons.append(f"Cold weather ({weather.temperature_c}°C) - concrete curing issues")
                results['risk_level'] = 'Medium' if results['risk_level'] == 'Low' else 'High'
        
        results['delay_days'] = delay_days
        results['reasons'] = reasons
        
        # Recommended actions
        if delay_days > 3:
            results['recommended_actions'].append("Reschedule critical path activities")
        if results['risk_level'] == 'High':
            results['recommended_actions'].append("Consider temporary work suspension")
        
        # TODO: Add terrain-specific adjustments
        if project.terrain_type.value == "Mountain" and delay_days > 0:
            results['delay_days'] = int(delay_days * 1.5)  # Mountains harder to access
            results['recommended_actions'].append("Mountain terrain - extend buffer period")
        
        return results
    
    def calculate_weather_demand_multiplier(self, 
                                           region: str,
                                           date: datetime,
                                           material_category: str) -> float:
        """
        Calculate demand multiplier based on weather patterns
        
        Args:
            region: Region name
            date: Date for calculation
            material_category: Category of material
        
        Returns:
            Multiplier for demand (1.0 = normal)
        
        TODO: MATERIAL-SPECIFIC WEATHER IMPACTS
        1. Insulators: Higher failure rate in extreme heat + humidity
        2. Oil: Temperature-based viscosity changes
        3. Cables: UV degradation in high sun exposure
        4. Cement: Humidity-based storage risks
        5. Steel: Corrosion rates in coastal/humid areas
        6. Transformers: Cooling efficiency in summer
        """
        
        weather = self.get_weather_for_location(
            latitude=MAJOR_CITIES.get(region, (28.6, 77.2))[0],
            longitude=MAJOR_CITIES.get(region, (28.6, 77.2))[1],
            date=date
        )
        
        if not weather:
            return 1.0
        
        # Base multiplier
        multiplier = weather.spares_demand_multiplier
        
        # Material-specific adjustments
        # TODO: Expand this with ML-based predictions
        if material_category == "Insulators":
            # Higher failure in monsoon
            if weather.precipitation_mm > 50:
                multiplier *= 1.2
        
        elif material_category == "Oil":
            # Higher consumption in extreme heat
            if weather.temperature_c > 40:
                multiplier *= 1.15
        
        elif material_category == "Hardware":
            # Corrosion in high humidity/rain
            if weather.precipitation_mm > 20:
                multiplier *= 1.1
        
        return round(multiplier, 2)
    
    def get_seasonal_pattern(self, region: str, month: int) -> Dict[str, float]:
        """
        Get typical seasonal weather patterns for a region
        
        Args:
            region: Region name
            month: Month (1-12)
        
        Returns:
            Dictionary with seasonal factors
        
        TODO: ADVANCED SEASONAL MODELING
        1. Multi-year historical pattern analysis
        2. El Niño / La Niña impact models
        3. Climate change trend adjustments
        4. Regional micro-season identification
        5. Agricultural calendar correlation
        """
        
        patterns = {
            'construction_feasibility': 1.0,
            'spares_demand': 1.0,
            'logistics_difficulty': 1.0
        }
        
        # Monsoon season
        if month in MONSOON_MONTHS:
            patterns['construction_feasibility'] = 0.7
            patterns['spares_demand'] = 1.2
            patterns['logistics_difficulty'] = 1.3
        
        # Winter
        elif month in WINTER_MONTHS:
            patterns['construction_feasibility'] = 0.9
            patterns['spares_demand'] = 1.1
            patterns['logistics_difficulty'] = 1.1
        
        # Summer
        elif month in [4, 5, 6]:
            patterns['construction_feasibility'] = 0.85
            patterns['spares_demand'] = 1.25  # Higher equipment failure
            patterns['logistics_difficulty'] = 1.0
        
        # TODO: Region-specific adjustments
        # Himalayan region has different patterns than coastal
        
        return patterns
    
    def get_weather_forecast_summary(self, 
                                    region: str, 
                                    start_date: datetime,
                                    days: int = 7) -> Dict[str, any]:
        """
        Get aggregated weather summary for planning
        
        Args:
            region: Region name
            start_date: Start date
            days: Number of days to summarize
        
        Returns:
            Summary dictionary
        
        TODO: PLANNING ENHANCEMENTS
        1. Critical weather window identification
        2. Optimal work scheduling recommendations
        3. Resource allocation based on weather
        4. Risk probability calculations
        5. Alternative timeline scenarios
        """
        
        summary = {
            'region': region,
            'period': f"{start_date.strftime('%Y-%m-%d')} to {(start_date + timedelta(days=days)).strftime('%Y-%m-%d')}",
            'average_temp': 0.0,
            'total_precipitation': 0.0,
            'risky_days': 0,
            'optimal_days': 0,
            'conditions': []
        }
        
        temps = []
        precips = []
        
        # TODO: Use actual coordinate-based aggregation
        for day in range(days):
            date = start_date + timedelta(days=day)
            # Simplified: use region capital coordinates
            lat, lon = MAJOR_CITIES.get(list(MAJOR_CITIES.keys())[0], (28.6, 77.2))
            
            weather = self.get_weather_for_location(lat, lon, date)
            if weather:
                temps.append(weather.temperature_c)
                precips.append(weather.precipitation_mm)
                summary['conditions'].append(weather.condition)
                
                if weather.construction_delay_factor > 0.3:
                    summary['risky_days'] += 1
                elif weather.construction_delay_factor == 0:
                    summary['optimal_days'] += 1
        
        if temps:
            summary['average_temp'] = round(np.mean(temps), 1)
            summary['total_precipitation'] = round(np.sum(precips), 1)
        
        return summary


# TODO: FUTURE WEATHER SERVICE FEATURES
"""
PRODUCTION-READY ENHANCEMENTS:

1. REAL-TIME DATA INTEGRATION
   - OpenWeatherMap API integration
   - India Meteorological Department (IMD) API
   - NOAA weather data
   - Satellite imagery analysis
   - Ground sensor networks

2. ADVANCED SPATIAL ANALYSIS
   - GIS-based coordinate matching
   - Elevation/altitude impact models
   - Terrain-based weather modification
   - Coastal vs inland patterns
   - Urban heat island effects

3. MACHINE LEARNING MODELS
   - LSTM for time-series weather prediction
   - Ensemble models for accuracy
   - Historical pattern learning
   - Anomaly detection
   - Extreme event prediction

4. ACTIVITY-SPECIFIC CONSTRAINTS
   - Foundation work: Soil moisture, temperature
   - Tower erection: Wind speed limits
   - Cable pulling: Temperature ranges
   - Transformer installation: Humidity limits
   - High-voltage testing: Weather clearance

5. WORKER SAFETY INTEGRATION
   - Heat stress index (WBGT)
   - Lightning risk assessment
   - Air quality monitoring
   - UV exposure levels
   - Visibility requirements

6. SUPPLY CHAIN IMPACTS
   - Road accessibility (flooding, landslides)
   - Port operations (cyclones, storms)
   - Air freight restrictions
   - Temperature-sensitive cargo
   - Warehouse climate control

7. CLIMATE CHANGE ADAPTATION
   - Long-term trend analysis
   - Shifting monsoon patterns
   - Extreme weather frequency
   - Planning resilience
   - Adaptive strategies
"""


if __name__ == "__main__":
    """Test weather service"""
    from datetime import datetime
    
    service = WeatherService()
    
    # Test coordinate-based weather
    print("Testing Weather Service...")
    print("="*70)
    
    # Delhi coordinates
    delhi_weather = service.get_weather_for_location(28.6139, 77.2090, datetime(2025, 7, 15))
    if delhi_weather:
        print(f"\nDelhi Weather (Jul 15, 2025):")
        print(f"  Condition: {delhi_weather.condition}")
        print(f"  Temperature: {delhi_weather.temperature_c}°C")
        print(f"  Precipitation: {delhi_weather.precipitation_mm}mm")
        print(f"  Construction Impact: {delhi_weather.construction_delay_factor:.1%}")
    
    # Test project assessment
    from src.core.models import Project, ProjectType, ProjectStage, ProjectStatus, TerrainType
    
    test_project = Project(
        id="TEST-001",
        name="Test_Himachal_Line",
        project_type=ProjectType.TRANSMISSION_LINE,
        region="Northern",
        state="Himachal Pradesh",
        stage=ProjectStage.CONSTRUCTION,
        status=ProjectStatus.ACTIVE,
        start_date=datetime.now(),
        expected_end_date=datetime.now(),
        latitude=31.1,
        longitude=77.2,
        length_km=100.0,
        voltage_kv=400,
        terrain_type=TerrainType.MOUNTAIN
    )
    
    assessment = service.assess_construction_viability(test_project, datetime(2025, 7, 15))
    print(f"\nConstruction Viability Assessment:")
    print(f"  Viable: {assessment['viable']}")
    print(f"  Risk Level: {assessment['risk_level']}")
    print(f"  Delay Days: {assessment['delay_days']}")
    if assessment['reasons']:
        print(f"  Reasons: {', '.join(assessment['reasons'])}")
    
    print("\n✓ Weather service test complete!")
