"""
Forecasting module for demand prediction

Provides:
- DemandEngine: Dual forecasting (CapEx + OpEx)
- ProphetForecaster: Time series forecasting with Prophet
- SafetyStockCalculator: Dynamic inventory buffer optimization
"""

from .demand_engine import DemandEngine
from .prophet_forecaster import ProphetForecaster, ProphetForecast
from .safety_stock import SafetyStockCalculator, SafetyStockRecommendation

__all__ = [
    'DemandEngine',
    'ProphetForecaster',
    'ProphetForecast',
    'SafetyStockCalculator',
    'SafetyStockRecommendation'
]
