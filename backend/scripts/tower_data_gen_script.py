"""
Enhanced Transmission Tower Dataset Generator for India
Generates realistic 33kV-765kV transmission infrastructure data
Version: 2.0
"""

import random
import json
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict

# ============================================================================
# RAW MATERIAL PRICING (Dec 2024 - State-wise in INR)
# ============================================================================

# Steel prices per kg by state (TMT/Structural steel)
STEEL_PRICES_STATE = {
    "Punjab": 58.50, "Haryana": 60.00, "West UP": 58.00, "East UP": 57.50,
    "MP": 56.00, "HP": 62.00, "Uttarakhand": 61.00, "J&K": 63.00,
    "Assam": 64.00, "Meghalaya": 65.00, "Arunachal": 66.00,
    "Gujarat": 59.00, "Maharashtra Coast": 60.50, "Odisha": 58.50, "AP Coast": 57.00,
    "Karnataka": 58.00, "Tamil Nadu": 66.00, "Kerala": 60.00,
    "Maharashtra": 60.00, "Telangana": 66.00, "North Bengal": 63.00, "Sikkim": 65.00,
    "Delhi": 61.00, "Mumbai": 62.00, "Bangalore": 58.50, "Kolkata": 60.50
}

# Cement prices per 50kg bag by state
CEMENT_PRICES_STATE = {
    "Punjab": 350.00, "Haryana": 360.00, "West UP": 340.00, "East UP": 335.00,
    "MP": 330.00, "HP": 380.00, "Uttarakhand": 375.00, "J&K": 390.00,
    "Assam": 400.00, "Meghalaya": 410.00, "Arunachal": 420.00,
    "Gujarat": 345.00, "Maharashtra Coast": 365.00, "Odisha": 340.00, "AP Coast": 330.00,
    "Karnataka": 340.00, "Tamil Nadu": 360.00, "Kerala": 355.00,
    "Maharashtra": 365.00, "Telangana": 360.00, "North Bengal": 385.00, "Sikkim": 400.00,
    "Delhi": 370.00, "Mumbai": 380.00, "Bangalore": 345.00, "Kolkata": 375.00
}

# Aluminium conductor (ACSR) prices per kg by state
ALUMINIUM_PRICES_STATE = {
    "Punjab": 180.00, "Haryana": 185.00, "West UP": 175.00, "East UP": 170.00,
    "MP": 165.00, "HP": 195.00, "Uttarakhand": 190.00, "J&K": 200.00,
    "Assam": 210.00, "Meghalaya": 215.00, "Arunachal": 220.00,
    "Gujarat": 178.00, "Maharashtra Coast": 185.00, "Odisha": 175.00, "AP Coast": 170.00,
    "Karnataka": 175.00, "Tamil Nadu": 190.00, "Kerala": 182.00,
    "Maharashtra": 185.00, "Telangana": 180.00, "North Bengal": 200.00, "Sikkim": 210.00,
    "Delhi": 188.00, "Mumbai": 190.00, "Bangalore": 178.00, "Kolkata": 195.00
}

# GST rates (%) - Updated as of Dec 2024
GST_RATES = {
    "steel": 18.0,      # Iron and steel products
    "cement": 18.0,     # Reduced from 28% in Sept 2025 reforms
    "aluminium": 18.0,  # ACSR conductors and aluminium products
    "transport": 18.0,  # Transportation services
    "labour": 18.0      # Construction labour and contractor services
}

# State-specific transport cost multipliers (logistics difficulty)
TRANSPORT_MULTIPLIER_STATE = {
    "Punjab": 1.00, "Haryana": 1.00, "West UP": 1.05, "East UP": 1.05,
    "MP": 1.10, "HP": 1.30, "Uttarakhand": 1.25, "J&K": 1.40,
    "Assam": 1.35, "Meghalaya": 1.40, "Arunachal": 1.50,
    "Gujarat": 1.05, "Maharashtra Coast": 1.10, "Odisha": 1.15, "AP Coast": 1.10,
    "Karnataka": 1.05, "Tamil Nadu": 1.08, "Kerala": 1.12,
    "Maharashtra": 1.08, "Telangana": 1.10, "North Bengal": 1.25, "Sikkim": 1.35,
    "Delhi": 1.00, "Mumbai": 1.05, "Bangalore": 1.08, "Kolkata": 1.10
}

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class TowerProfile:
    """Engineering specifications for tower types"""
    steel_kg_range: Tuple[float, float]
    concrete_m3_range: Tuple[float, float]
    aluminium_kg_per_m_range: Tuple[float, float]
    span_m_range: Tuple[float, float]
    height_m_range: Tuple[float, float]
    foundation_depth_m_range: Tuple[float, float]

# Voltage-specific tower profiles (engineering accurate)
TOWER_PROFILES = {
    "33kV": {
        "S":  TowerProfile((900, 1500), (15, 25), (1.5, 2.5), (100, 150), (12, 18), (2.5, 4.0)),
        "LA": TowerProfile((1200, 1800), (20, 30), (2.0, 3.0), (90, 130), (14, 20), (3.0, 4.5)),
        "MA": TowerProfile((1500, 2200), (25, 35), (2.0, 3.0), (80, 120), (15, 22), (3.5, 5.0)),
        "HA": TowerProfile((2000, 2800), (30, 45), (3.0, 4.0), (70, 110), (16, 24), (4.0, 5.5)),
    },
    "66kV": {
        "S":  TowerProfile((1500, 2200), (20, 35), (2.0, 3.5), (120, 180), (15, 22), (3.0, 5.0)),
        "LA": TowerProfile((2000, 2800), (30, 45), (2.5, 4.0), (110, 160), (18, 25), (3.5, 5.5)),
        "MA": TowerProfile((2500, 3500), (35, 50), (3.0, 4.5), (100, 140), (20, 28), (4.0, 6.0)),
        "DE": TowerProfile((3000, 4200), (45, 65), (4.0, 5.5), (100, 140), (22, 30), (4.5, 6.5)),
    },
    "132kV": {
        "S":  TowerProfile((3500, 5000), (40, 60), (3.5, 5.0), (200, 300), (22, 32), (4.5, 6.5)),
        "LA": TowerProfile((4500, 6500), (50, 75), (4.0, 6.0), (180, 280), (25, 35), (5.0, 7.0)),
        "MA": TowerProfile((5500, 7500), (60, 85), (4.5, 6.5), (160, 260), (28, 38), (5.5, 7.5)),
        "HA": TowerProfile((6500, 9000), (70, 100), (5.0, 7.5), (140, 240), (30, 42), (6.0, 8.5)),
        "DE": TowerProfile((8000, 11000), (85, 120), (6.0, 8.5), (160, 260), (32, 45), (7.0, 9.5)),
    },
    "220kV": {
        "S":  TowerProfile((7000, 10000), (80, 110), (5.5, 7.5), (250, 350), (30, 42), (6.5, 9.0)),
        "LA": TowerProfile((9000, 13000), (100, 140), (6.5, 9.0), (230, 330), (34, 46), (7.5, 10.0)),
        "MA": TowerProfile((11000, 16000), (120, 165), (7.5, 10.0), (210, 310), (38, 50), (8.5, 11.0)),
        "HA": TowerProfile((13000, 19000), (140, 190), (8.5, 11.5), (190, 290), (42, 55), (9.5, 12.5)),
        "DE": TowerProfile((16000, 23000), (170, 230), (10.0, 13.5), (210, 310), (45, 60), (11.0, 14.0)),
    },
    "400kV": {
        "S":  TowerProfile((18000, 25000), (180, 250), (11.0, 15.0), (300, 400), (42, 55), (10.0, 13.5)),
        "LA": TowerProfile((22000, 30000), (220, 300), (13.0, 17.0), (280, 380), (46, 60), (11.5, 15.0)),
        "MA": TowerProfile((26000, 36000), (260, 350), (15.0, 20.0), (260, 360), (50, 65), (13.0, 17.0)),
        "HA": TowerProfile((30000, 42000), (300, 400), (17.0, 23.0), (240, 340), (54, 70), (14.5, 19.0)),
        "DE": TowerProfile((36000, 50000), (360, 480), (20.0, 27.0), (260, 360), (58, 75), (16.5, 21.0)),
    },
    "765kV": {
        "S":  TowerProfile((45000, 60000), (450, 600), (25.0, 35.0), (350, 450), (55, 70), (16.0, 22.0)),
        "LA": TowerProfile((55000, 75000), (550, 750), (30.0, 42.0), (330, 430), (60, 78), (18.5, 24.5)),
        "MA": TowerProfile((65000, 90000), (650, 900), (35.0, 48.0), (310, 410), (65, 85), (21.0, 27.5)),
        "HA": TowerProfile((75000, 105000), (750, 1050), (40.0, 55.0), (290, 390), (70, 92), (23.5, 30.5)),
    }
}

# Tower type descriptions
TOWER_TYPES = {
    "S": "Suspension",
    "LA": "Light Angle (0-15°)",
    "MA": "Medium Angle (15-30°)",
    "HA": "Heavy Angle (30-60°)",
    "DE": "Dead End/Termination",
    "NB": "Narrow Base",
    "G": "Gantry",
    "WZ": "Wind Zone Reinforced",
    "EQ": "Seismic Reinforced",
    "MP": "Monopole"
}

# Conductor specifications by voltage
CONDUCTOR_SPECS = {
    "33kV": [
        {"type": "ACSR Dog", "size": "100 sq.mm", "circuits": 1},
        {"type": "ACSR Rabbit", "size": "50 sq.mm", "circuits": 1},
        {"type": "AAC Mosquito", "size": "100 sq.mm", "circuits": 1},
    ],
    "66kV": [
        {"type": "ACSR Panther", "size": "200 sq.mm", "circuits": 1},
        {"type": "ACSR Dog", "size": "100 sq.mm", "circuits": 1},
    ],
    "132kV": [
        {"type": "ACSR Zebra", "size": "300 sq.mm", "circuits": 1},
        {"type": "ACSR Panther", "size": "200 sq.mm", "circuits": 2},
    ],
    "220kV": [
        {"type": "ACSR Moose", "size": "400 sq.mm", "circuits": 1},
        {"type": "ACSR Zebra", "size": "300 sq.mm", "circuits": 2},
    ],
    "400kV": [
        {"type": "ACSR Moose", "size": "400 sq.mm", "circuits": 2},
        {"type": "Quad Moose", "size": "4x400 sq.mm", "circuits": 2},
    ],
    "765kV": [
        {"type": "Quad Bersimis", "size": "4x500 sq.mm", "circuits": 2},
        {"type": "Octal Moose", "size": "8x400 sq.mm", "circuits": 2},
    ]
}

# Geographic clusters with realistic zones
CLUSTERS = {
    "northern_plains": {
        "terrain": "plain",
        "lat_range": (28.0, 32.0),
        "lng_range": (75.0, 80.0),
        "states": ["Punjab", "Haryana", "West UP"],
        "wind_zones": [2, 3],
        "seismic_zones": ["IV", "V"],
    },
    "central_plains": {
        "terrain": "plain",
        "lat_range": (23.0, 27.0),
        "lng_range": (75.0, 82.0),
        "states": ["MP", "East UP"],
        "wind_zones": [2, 3],
        "seismic_zones": ["II", "III"],
    },
    "himalayan_region": {
        "terrain": "hilly",
        "lat_range": (29.0, 34.0),
        "lng_range": (75.0, 80.0),
        "states": ["HP", "Uttarakhand", "J&K"],
        "wind_zones": [3, 4, 5],
        "seismic_zones": ["IV", "V"],
    },
    "northeast_hills": {
        "terrain": "hilly",
        "lat_range": (24.0, 28.0),
        "lng_range": (88.0, 95.0),
        "states": ["Assam", "Meghalaya", "Arunachal"],
        "wind_zones": [3, 4],
        "seismic_zones": ["V"],
    },
    "western_coastal": {
        "terrain": "windy",
        "lat_range": (15.0, 23.0),
        "lng_range": (69.0, 75.0),
        "states": ["Gujarat", "Maharashtra Coast"],
        "wind_zones": [4, 5, 6],
        "seismic_zones": ["III"],
    },
    "eastern_coastal": {
        "terrain": "windy",
        "lat_range": (17.0, 22.0),
        "lng_range": (82.0, 87.0),
        "states": ["Odisha", "AP Coast"],
        "wind_zones": [5, 6],
        "seismic_zones": ["II", "III"],
    },
    "southern_peninsula": {
        "terrain": "plain",
        "lat_range": (8.0, 16.0),
        "lng_range": (75.0, 80.0),
        "states": ["Karnataka", "Tamil Nadu", "Kerala"],
        "wind_zones": [3, 4],
        "seismic_zones": ["II", "III"],
    },
    "deccan_plateau": {
        "terrain": "plain",
        "lat_range": (17.0, 21.0),
        "lng_range": (75.0, 79.0),
        "states": ["Maharashtra", "Telangana"],
        "wind_zones": [2, 3],
        "seismic_zones": ["II"],
    },
    "seismic_belt": {
        "terrain": "seismic",
        "lat_range": (26.0, 28.0),
        "lng_range": (88.0, 92.0),
        "states": ["North Bengal", "Sikkim"],
        "wind_zones": [3, 4],
        "seismic_zones": ["IV", "V"],
    },
    "metro_urban": {
        "terrain": "urban",
        "lat_range": (12.0, 28.0),
        "lng_range": (72.0, 88.0),
        "states": ["Delhi", "Mumbai", "Bangalore", "Kolkata"],
        "wind_zones": [2, 3, 4],
        "seismic_zones": ["II", "III", "IV"],
    }
}

# Voltage distribution (realistic for Indian grid)
VOLTAGE_DISTRIBUTION = [
    ("33kV", 0.40),
    ("66kV", 0.20),
    ("132kV", 0.20),
    ("220kV", 0.12),
    ("400kV", 0.07),
    ("765kV", 0.01),
]

# Terrain distribution
TERRAIN_DISTRIBUTION = [
    ("northern_plains", 0.15),
    ("central_plains", 0.15),
    ("himalayan_region", 0.12),
    ("northeast_hills", 0.08),
    ("western_coastal", 0.12),
    ("eastern_coastal", 0.10),
    ("southern_peninsula", 0.15),
    ("deccan_plateau", 0.10),
    ("seismic_belt", 0.03),
    ("metro_urban", 0.05),
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def weighted_choice(distribution: List[Tuple[str, float]]) -> str:
    """Select item based on weighted distribution"""
    r = random.random()
    cumulative = 0
    for item, prob in distribution:
        cumulative += prob
        if r <= cumulative:
            return item
    return distribution[0][0]

def rnd(range_tuple: Tuple[float, float], decimals: int = 2) -> float:
    """Generate random value within range"""
    return round(random.uniform(*range_tuple), decimals)

def random_coord(cluster: Dict) -> Tuple[float, float]:
    """Generate random coordinates within cluster"""
    lat = round(random.uniform(*cluster["lat_range"]), 6)
    lng = round(random.uniform(*cluster["lng_range"]), 6)
    return lat, lng

def get_terrain_modifier(terrain: str, tower_type: str) -> float:
    """Material multiplier based on terrain difficulty"""
    modifiers = {
        "plain": {"S": 1.0, "LA": 1.0, "MA": 1.05, "HA": 1.08, "DE": 1.10},
        "hilly": {"S": 1.15, "LA": 1.20, "MA": 1.25, "HA": 1.30, "DE": 1.35},
        "windy": {"S": 1.12, "LA": 1.15, "MA": 1.18, "HA": 1.22, "DE": 1.25},
        "seismic": {"S": 1.18, "LA": 1.22, "MA": 1.28, "HA": 1.35, "DE": 1.40},
        "urban": {"S": 1.05, "LA": 1.08, "MA": 1.10, "HA": 1.12, "DE": 1.15},
    }
    return modifiers.get(terrain, {}).get(tower_type, 1.0)

def calculate_material_costs(state: str, steel_kg: float, concrete_m3: float, 
                            aluminium_kg: float) -> Dict:
    """Calculate material costs with state-wise pricing and GST"""
    
    # Get base prices for state
    steel_price_per_kg = STEEL_PRICES_STATE.get(state, 60.0)
    cement_price_per_bag = CEMENT_PRICES_STATE.get(state, 360.0)
    aluminium_price_per_kg = ALUMINIUM_PRICES_STATE.get(state, 185.0)
    transport_multiplier = TRANSPORT_MULTIPLIER_STATE.get(state, 1.0)
    
    # Convert cement to concrete cost (1 m3 concrete ≈ 6.5 bags cement + aggregates)
    cement_bags_needed = concrete_m3 * 6.5
    concrete_material_cost = cement_bags_needed * cement_price_per_bag
    
    # Calculate base material costs (before GST)
    steel_base_cost = steel_kg * steel_price_per_kg
    concrete_base_cost = concrete_material_cost
    aluminium_base_cost = aluminium_kg * aluminium_price_per_kg
    
    # Apply transport multiplier
    steel_cost_with_transport = steel_base_cost * transport_multiplier
    concrete_cost_with_transport = concrete_base_cost * transport_multiplier
    aluminium_cost_with_transport = aluminium_base_cost * transport_multiplier
    
    # Calculate GST amounts
    steel_gst = steel_cost_with_transport * (GST_RATES["steel"] / 100)
    concrete_gst = concrete_cost_with_transport * (GST_RATES["cement"] / 100)
    aluminium_gst = aluminium_cost_with_transport * (GST_RATES["aluminium"] / 100)
    
    # Total costs including GST
    steel_total = steel_cost_with_transport + steel_gst
    concrete_total = concrete_cost_with_transport + concrete_gst
    aluminium_total = aluminium_cost_with_transport + aluminium_gst
    
    return {
        "steel": {
            "base_cost_inr": round(steel_base_cost, 2),
            "transport_cost_inr": round(steel_cost_with_transport - steel_base_cost, 2),
            "gst_amount_inr": round(steel_gst, 2),
            "gst_rate_percent": GST_RATES["steel"],
            "total_cost_inr": round(steel_total, 2),
            "price_per_kg_inr": round(steel_price_per_kg, 2)
        },
        "concrete": {
            "base_cost_inr": round(concrete_base_cost, 2),
            "transport_cost_inr": round(concrete_cost_with_transport - concrete_base_cost, 2),
            "gst_amount_inr": round(concrete_gst, 2),
            "gst_rate_percent": GST_RATES["cement"],
            "total_cost_inr": round(concrete_total, 2),
            "cement_bags_needed": round(cement_bags_needed, 2),
            "price_per_bag_inr": round(cement_price_per_bag, 2)
        },
        "aluminium": {
            "base_cost_inr": round(aluminium_base_cost, 2),
            "transport_cost_inr": round(aluminium_cost_with_transport - aluminium_base_cost, 2),
            "gst_amount_inr": round(aluminium_gst, 2),
            "gst_rate_percent": GST_RATES["aluminium"],
            "total_cost_inr": round(aluminium_total, 2),
            "price_per_kg_inr": round(aluminium_price_per_kg, 2)
        },
        "summary": {
            "total_material_cost_before_gst": round(steel_cost_with_transport + concrete_cost_with_transport + aluminium_cost_with_transport, 2),
            "total_gst_amount": round(steel_gst + concrete_gst + aluminium_gst, 2),
            "total_material_cost_with_gst": round(steel_total + concrete_total + aluminium_total, 2),
            "transport_multiplier": transport_multiplier,
            "state": state
        }
    }

# ============================================================================
# TOWER GENERATION
# ============================================================================

def generate_tower(tower_id: int) -> Dict:
    """Generate a single realistic tower record"""
    
    # Select voltage and cluster
    voltage = weighted_choice(VOLTAGE_DISTRIBUTION)
    cluster_key = weighted_choice(TERRAIN_DISTRIBUTION)
    cluster = CLUSTERS[cluster_key]
    
    # Select tower type based on voltage
    available_types = list(TOWER_PROFILES[voltage].keys())
    tower_type = random.choice(available_types)
    profile = TOWER_PROFILES[voltage][tower_type]
    
    # Get coordinates and zones
    lat, lng = random_coord(cluster)
    wind_zone = random.choice(cluster["wind_zones"])
    seismic_zone = random.choice(cluster["seismic_zones"])
    state = random.choice(cluster["states"])
    
    # Apply terrain modifier
    terrain_mod = get_terrain_modifier(cluster["terrain"], tower_type)
    
    # Calculate materials with terrain adjustment
    steel_kg = rnd(profile.steel_kg_range) * terrain_mod
    concrete_m3 = rnd(profile.concrete_m3_range) * terrain_mod
    aluminium_kg_per_m = rnd(profile.aluminium_kg_per_m_range)
    span_m = rnd(profile.span_m_range)
    height_m = rnd(profile.height_m_range)
    foundation_depth_m = rnd(profile.foundation_depth_m_range) * terrain_mod
    
    # Select conductor
    conductor = random.choice(CONDUCTOR_SPECS[voltage])
    
    # Calculate derived values
    total_conductor_length_m = span_m * conductor["circuits"] * 3  # 3 phases
    total_aluminium_kg = aluminium_kg_per_m * total_conductor_length_m
    
    # Calculate costs with state-wise pricing and GST
    material_costs = calculate_material_costs(state, steel_kg, concrete_m3, total_aluminium_kg)
    
    # Age and condition (for realistic dataset)
    age_years = random.randint(1, 45)
    condition_score = max(50, 100 - age_years * random.uniform(0.8, 1.5))
    
    return {
        "tower_id": f"TWR-{tower_id:05d}",
        "voltage": voltage,
        "tower_type": tower_type,
        "tower_type_description": TOWER_TYPES.get(tower_type, "Unknown"),
        "location": {
            "lat": lat,
            "lng": lng,
            "cluster": cluster_key,
            "terrain": cluster["terrain"],
            "state": state
        },
        "engineering": {
            "steel_kg": round(steel_kg, 2),
            "concrete_m3": round(concrete_m3, 2),
            "height_m": height_m,
            "foundation_depth_m": foundation_depth_m,
            "span_m": span_m
        },
        "conductor": {
            "type": conductor["type"],
            "size": conductor["size"],
            "circuits": conductor["circuits"],
            "aluminium_kg_per_m": aluminium_kg_per_m,
            "total_conductor_length_m": round(total_conductor_length_m, 2),
            "total_aluminium_kg": round(total_aluminium_kg, 2)
        },
        "environmental": {
            "wind_zone": wind_zone,
            "seismic_zone": f"Zone {seismic_zone}",
            "terrain_modifier": round(terrain_mod, 3)
        },
        "operational": {
            "age_years": age_years,
            "commissioning_year": 2024 - age_years,
            "condition_score": round(condition_score, 1),
            "maintenance_priority": "High" if condition_score < 70 else "Medium" if condition_score < 85 else "Low"
        },
        "cost_analysis": material_costs
    }

# ============================================================================
# MAIN GENERATION FUNCTION
# ============================================================================

def generate_dataset(num_towers: int = 10000, output_file: str = "tower_dataset_india.json"):
    """Generate complete dataset with validation"""
    
    print(f"Generating {num_towers} transmission towers...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    towers = []
    for i in range(1, num_towers + 1):
        tower = generate_tower(i)
        towers.append(tower)
        
        if i % 1000 == 0:
            print(f"  Generated {i}/{num_towers} towers...")
    
    # Calculate statistics
    voltage_counts = {}
    terrain_counts = {}
    state_counts = {}
    total_cost_by_state = {}
    
    for tower in towers:
        v = tower["voltage"]
        t = tower["location"]["terrain"]
        s = tower["location"]["state"]
        
        voltage_counts[v] = voltage_counts.get(v, 0) + 1
        terrain_counts[t] = terrain_counts.get(t, 0) + 1
        state_counts[s] = state_counts.get(s, 0) + 1
        
        # Aggregate costs by state
        if s not in total_cost_by_state:
            total_cost_by_state[s] = {
                "total_steel_cost": 0,
                "total_concrete_cost": 0,
                "total_aluminium_cost": 0,
                "total_gst": 0,
                "tower_count": 0
            }
        
        costs = tower["cost_analysis"]
        total_cost_by_state[s]["total_steel_cost"] += costs["steel"]["total_cost_inr"]
        total_cost_by_state[s]["total_concrete_cost"] += costs["concrete"]["total_cost_inr"]
        total_cost_by_state[s]["total_aluminium_cost"] += costs["aluminium"]["total_cost_inr"]
        total_cost_by_state[s]["total_gst"] += costs["summary"]["total_gst_amount"]
        total_cost_by_state[s]["tower_count"] += 1
    
    # Create final dataset
    dataset = {
        "metadata": {
            "version": "2.1",
            "generated_at": datetime.now().isoformat(),
            "total_towers": num_towers,
            "voltage_distribution": voltage_counts,
            "terrain_distribution": terrain_counts,
            "state_distribution": state_counts,
            "description": "Synthetic transmission tower dataset for India with state-wise material costs and GST",
            "pricing_reference": {
                "steel_price_range_inr_per_kg": f"{min(STEEL_PRICES_STATE.values()):.2f} - {max(STEEL_PRICES_STATE.values()):.2f}",
                "cement_price_range_inr_per_bag": f"{min(CEMENT_PRICES_STATE.values()):.2f} - {max(CEMENT_PRICES_STATE.values()):.2f}",
                "aluminium_price_range_inr_per_kg": f"{min(ALUMINIUM_PRICES_STATE.values()):.2f} - {max(ALUMINIUM_PRICES_STATE.values()):.2f}",
                "gst_rates": GST_RATES,
                "pricing_date": "December 2024"
            },
            "cost_summary_by_state": {
                state: {
                    "tower_count": data["tower_count"],
                    "total_material_cost_inr": round(data["total_steel_cost"] + data["total_concrete_cost"] + data["total_aluminium_cost"], 2),
                    "total_gst_inr": round(data["total_gst"], 2),
                    "avg_cost_per_tower_inr": round((data["total_steel_cost"] + data["total_concrete_cost"] + data["total_aluminium_cost"]) / data["tower_count"], 2)
                }
                for state, data in total_cost_by_state.items()
            }
        },
        "towers": towers
    }
    
    # Save to file
    with open(output_file, "w") as f:
        json.dump(dataset, f, indent=2)
    
    print(f"\n✓ Dataset saved to: {output_file}")
    print(f"  Total file size: {len(json.dumps(dataset)) / 1024 / 1024:.2f} MB")
    print(f"\nVoltage Distribution:")
    for v, count in sorted(voltage_counts.items()):
        print(f"  {v}: {count} towers ({count/num_towers*100:.1f}%)")
    print(f"\nTerrain Distribution:")
    for t, count in sorted(terrain_counts.items()):
        print(f"  {t}: {count} towers ({count/num_towers*100:.1f}%)")
    print(f"\nTop 10 States by Tower Count:")
    for state, count in sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {state}: {count} towers")
    print(f"\nCost Summary (Top 5 States by Total Cost):")
    cost_summary = dataset["metadata"]["cost_summary_by_state"]
    top_states = sorted(cost_summary.items(), key=lambda x: x[1]["total_material_cost_inr"], reverse=True)[:5]
    for state, data in top_states:
        print(f"  {state}:")
        print(f"    Towers: {data['tower_count']}")
        print(f"    Total Material Cost: ₹{data['total_material_cost_inr']:,.2f}")
        print(f"    Total GST: ₹{data['total_gst_inr']:,.2f}")
        print(f"    Avg Cost/Tower: ₹{data['avg_cost_per_tower_inr']:,.2f}")
    
    return dataset

# ============================================================================
# EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Generate 10,000 tower dataset
    dataset = generate_dataset(10000, "tower_dataset_india_10k.json")
    
    # Generate sample preview (100 towers)
    sample = generate_dataset(100, "tower_dataset_india_sample.json")
    
    print("\n✓ Generation complete!")
    print("  Main dataset: tower_dataset_india_10k.json")
    print("  Sample dataset: tower_dataset_india_sample.json")
    