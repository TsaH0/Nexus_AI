"""
NEXUS Configuration
Global configuration variables for the supply chain orchestration system
"""

import os
from pathlib import Path

# Project directories
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
GENERATED_DATA_DIR = DATA_DIR / "generated"
OUTPUTS_DIR = DATA_DIR / "outputs"
ACTION_PLANS_DIR = OUTPUTS_DIR / "action_plans"
SIMULATION_LOGS_DIR = OUTPUTS_DIR / "simulation_logs"

# Create directories if they don't exist
GENERATED_DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
ACTION_PLANS_DIR.mkdir(parents=True, exist_ok=True)
SIMULATION_LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Configuration constants
DEFAULT_SEED = 42
DEFAULT_SIMULATION_DAYS = 7
DEFAULT_OPTIMIZATION_STRATEGY = 'balanced'

# Data generation
NUM_MATERIALS = 30
NUM_VENDORS = 20
NUM_WAREHOUSES = 15
NUM_PROJECTS = 50
HISTORICAL_DATA_WEEKS = 50

# Forecasting
PROPHET_FORECAST_WEEKS = 12
PROPHET_CHANGEPOINT_PRIOR_SCALE = 0.05
PROPHET_SEASONALITY_PRIOR_SCALE = 10.0

# Procurement
MIN_ORDER_BATCH_SIZE = 100
MAX_ORDER_BATCH_SIZE = 10000

# Inventory
SAFETY_STOCK_DAYS = 30
REORDER_POINT_MULTIPLIER = 1.5

# Vendor evaluation weights
VENDOR_WEIGHT_COST = 0.4
VENDOR_WEIGHT_RELIABILITY = 0.3
VENDOR_WEIGHT_LEAD_TIME = 0.2
VENDOR_WEIGHT_DISTANCE = 0.1

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
