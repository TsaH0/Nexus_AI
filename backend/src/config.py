"""
Configuration file for NEXUS system
Contains all constants, rates, and configurable parameters
"""

import os
from datetime import datetime

# ============================================================================
# PROJECT METADATA
# ============================================================================
PROJECT_NAME = "NEXUS"
VERSION = "1.0.0"
ORGANIZATION = "POWERGRID"
START_DATE = datetime(2025, 1, 1)

# ============================================================================
# PATHS
# ============================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Project root
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
GENERATED_DATA_DIR = os.path.join(DATA_DIR, "generated")
OUTPUT_DIR = os.path.join(DATA_DIR, "outputs")
ACTION_PLANS_DIR = os.path.join(OUTPUT_DIR, "action_plans")
LOGS_DIR = os.path.join(OUTPUT_DIR, "simulation_logs")

# Create directories if they don't exist
os.makedirs(GENERATED_DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ACTION_PLANS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# ============================================================================
# SIMULATION PARAMETERS
# ============================================================================
NUM_PROJECTS = 50
NUM_VENDORS = 20
NUM_WAREHOUSES = 15
NUM_MATERIALS = 30
SIMULATION_DAYS = 365

# ============================================================================
# INDIAN REGIONS & STATES
# ============================================================================
REGIONS = {
    "Northern": ["Delhi", "Punjab", "Haryana", "Himachal Pradesh", "Uttarakhand", "Jammu & Kashmir"],
    "Western": ["Maharashtra", "Gujarat", "Rajasthan", "Goa"],
    "Eastern": ["West Bengal", "Odisha", "Bihar", "Jharkhand"],
    "Southern": ["Karnataka", "Tamil Nadu", "Kerala", "Andhra Pradesh", "Telangana"],
    "North-Eastern": ["Assam", "Meghalaya", "Manipur", "Nagaland", "Tripura"]
}

# Major cities with coordinates for warehouse placement
MAJOR_CITIES = {
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Kolkata": (22.5726, 88.3639),
    "Chennai": (13.0827, 80.2707),
    "Bangalore": (12.9716, 77.5946),
    "Hyderabad": (17.3850, 78.4867),
    "Ahmedabad": (23.0225, 72.5714),
    "Pune": (18.5204, 73.8567),
    "Jaipur": (26.9124, 75.7873),
    "Lucknow": (26.8467, 80.9462),
    "Bhubaneswar": (20.2961, 85.8245),
    "Guwahati": (26.1445, 91.7362),
    "Chandigarh": (30.7333, 76.7794),
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Patna": (25.5941, 85.1376)
}

# ============================================================================
# TAX RATES (GST)
# ============================================================================
GST_RATES = {
    "Steel": 0.18,
    "Copper": 0.18,
    "Aluminum": 0.18,
    "Cement": 0.28,
    "Insulators": 0.18,
    "Transformers": 0.18,
    "Cables": 0.18,
    "Switchgear": 0.18,
    "Oil": 0.18,
    "Hardware": 0.18
}

# ============================================================================
# LOGISTICS PARAMETERS
# ============================================================================
FUEL_PRICE_PER_LITER = 100.0  # INR
TRUCK_MILEAGE_KM_PER_LITER = 4.0
TRANSPORT_COST_PER_KM = FUEL_PRICE_PER_LITER / TRUCK_MILEAGE_KM_PER_LITER  # 25 INR/km
LOADING_UNLOADING_COST = 5000  # INR per transfer
WAREHOUSE_HANDLING_COST_PER_UNIT = 50  # INR

# ============================================================================
# INVENTORY PARAMETERS
# ============================================================================
BASE_SAFETY_STOCK_MULTIPLIER = 1.2  # 20% buffer
MIN_ORDER_QUANTITY = 10
MAX_WAREHOUSE_CAPACITY = 100000  # units per warehouse
INVENTORY_CARRYING_COST_ANNUAL = 0.15  # 15% of material value per year

# ============================================================================
# VENDOR PARAMETERS
# ============================================================================
VENDOR_RELIABILITY_RANGES = {
    "Excellent": (0.95, 1.0),
    "Good": (0.85, 0.95),
    "Average": (0.70, 0.85),
    "Poor": (0.50, 0.70)
}

BASE_LEAD_TIME_DAYS = {
    "Steel": 30,
    "Copper": 45,
    "Aluminum": 35,
    "Cement": 7,
    "Insulators": 60,
    "Transformers": 120,
    "Cables": 45,
    "Switchgear": 90,
    "Oil": 15,
    "Hardware": 20
}

# ============================================================================
# PROJECT PARAMETERS
# ============================================================================
PROJECT_TYPES = ["Transmission_Line", "Substation", "HVDC_Corridor"]

PROJECT_STAGES = {
    "Planning": 0.1,      # 10% of total material need
    "Foundation": 0.3,    # 30% of total material need
    "Construction": 0.5,  # 50% of total material need
    "Commissioning": 0.1  # 10% of total material need
}

TERRAIN_MULTIPLIERS = {
    "Plain": 1.0,
    "Hilly": 1.5,
    "Mountain": 2.0,
    "Coastal": 1.2,
    "Desert": 1.3
}

# ============================================================================
# WEATHER PARAMETERS
# ============================================================================
MONSOON_MONTHS = [6, 7, 8, 9]  # June to September
WINTER_MONTHS = [12, 1, 2]

WEATHER_IMPACT = {
    "Heavy_Rain": {"construction_delay": 0.5, "spares_multiplier": 1.3},
    "Moderate_Rain": {"construction_delay": 0.2, "spares_multiplier": 1.1},
    "Clear": {"construction_delay": 0.0, "spares_multiplier": 1.0},
    "Extreme_Heat": {"construction_delay": 0.1, "spares_multiplier": 1.2},
    "Cold": {"construction_delay": 0.15, "spares_multiplier": 1.15}
}

# ============================================================================
# MARKET SENTIMENT PARAMETERS
# ============================================================================
SENTIMENT_TOPICS = [
    "RoW_Issue",
    "Labor_Strike",
    "Commodity_Price_Spike",
    "Policy_Change",
    "Normal"
]

SENTIMENT_IMPACT = {
    "RoW_Issue": {"halt_project": True, "lead_time_buffer": 0},
    "Labor_Strike": {"halt_project": False, "lead_time_buffer": 15},
    "Commodity_Price_Spike": {"halt_project": False, "price_multiplier": 1.25},
    "Policy_Change": {"halt_project": False, "lead_time_buffer": 10},
    "Normal": {"halt_project": False, "lead_time_buffer": 0}
}

# ============================================================================
# OPTIMIZATION WEIGHTS (Multi-Criteria Decision Making)
# ============================================================================
OPTIMIZATION_STRATEGIES = {
    "balanced": {
        "cost_weight": 0.5,
        "time_weight": 0.3,
        "reliability_weight": 0.2
    },
    "cost_focused": {
        "cost_weight": 0.7,
        "time_weight": 0.15,
        "reliability_weight": 0.15
    },
    "rush": {
        "cost_weight": 0.15,
        "time_weight": 0.7,
        "reliability_weight": 0.15
    },
    "risk_averse": {
        "cost_weight": 0.3,
        "time_weight": 0.3,
        "reliability_weight": 0.4
    }
}

# ============================================================================
# PROPHET MODEL PARAMETERS
# ============================================================================
PROPHET_SEASONALITY_MODE = "multiplicative"
PROPHET_CHANGEPOINT_PRIOR_SCALE = 0.05
PROPHET_SEASONALITY_PRIOR_SCALE = 10.0

# High-volume consumables that benefit from Prophet forecasting
PROPHET_MATERIALS = [
    "Transformer_Oil",
    "Insulators_Disc_Type",
    "Hardware_Fasteners",
    "Cables_LT",
    "Cement_OPC"
]

# ============================================================================
# XAI (Explainable AI) PARAMETERS
# ============================================================================
ENABLE_XAI = True
XAI_DETAIL_LEVEL = "high"  # "low", "medium", "high"

# ============================================================================
# PERISHABILITY / SHELF LIFE
# ============================================================================
SHELF_LIFE_DAYS = {
    "Cement": 90,
    "Transformer_Oil": 365,
    "Cables": 730,
    "Steel": 1825,  # 5 years (with proper storage)
    "Insulators": 3650  # 10 years
}

# ============================================================================
# BULLWHIP EFFECT DAMPENING
# ============================================================================
FORECAST_SMOOTHING_ALPHA = 0.3  # Exponential smoothing coefficient
ORDER_BATCHING_WINDOW_DAYS = 7  # Aggregate orders weekly

# ============================================================================
# GNN PARAMETERS (Grid Health Monitoring)
# ============================================================================
GNN_EMBEDDING_DIM = 64
GNN_NUM_LAYERS = 3
GNN_ANOMALY_THRESHOLD = 0.75  # Cosine similarity threshold for anomaly detection
GNN_UPDATE_FREQUENCY_DAYS = 30  # Monthly grid health assessment
