"""
Data Factory - Digital Twin Generator
Creates realistic, correlated synthetic datasets for NEXUS simulation
"""

import os
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config import *
from src.core.models import (
    Material, Vendor, Warehouse, Project,
    ProjectType, ProjectStage, ProjectStatus, TerrainType
)


class DataFactory:
    """Generates correlated synthetic datasets for the Digital Twin"""
    
    def __init__(self, seed: int = 42):
        """Initialize with random seed for reproducibility"""
        random.seed(seed)
        np.random.seed(seed)
        self.materials: List[Material] = []
        self.vendors: List[Vendor] = []
        self.warehouses: List[Warehouse] = []
        self.projects: List[Project] = []
    
    def generate_all(self):
        """Generate complete ecosystem"""
        print("🏭 Generating Digital Twin Data...")
        
        self.materials = self.generate_materials()
        print(f"✓ Generated {len(self.materials)} materials")
        
        self.vendors = self.generate_vendors()
        print(f"✓ Generated {len(self.vendors)} vendors")
        
        self.warehouses = self.generate_warehouses()
        print(f"✓ Generated {len(self.warehouses)} warehouses")
        
        self.projects = self.generate_projects()
        print(f"✓ Generated {len(self.projects)} projects")
        
        # Generate supporting data files
        self.generate_bom_standards()
        self.generate_market_sentiment_log()
        self.generate_weather_forecast()
        self.generate_historical_consumption()
        
        # Save to CSV
        self.save_all()
        print("✓ All data saved successfully!")
    
    def generate_materials(self) -> List[Material]:
        """Generate material master data"""
        materials_data = [
            # Steel products
            ("MAT-001", "Steel_Structural_Angle", "Steel", "MT", 55000, None, False, 1000),
            ("MAT-002", "Steel_Lattice_Tower", "Steel", "MT", 60000, None, False, 1000),
            ("MAT-003", "Steel_TMT_Bars", "Steel", "MT", 52000, None, False, 1000),
            
            # Copper products
            ("MAT-004", "Copper_Conductor_ACSR", "Copper", "KM", 450000, None, False, 500),
            ("MAT-005", "Copper_Earthing_Wire", "Copper", "KM", 380000, None, False, 300),
            
            # Aluminum products
            ("MAT-006", "Aluminum_Conductor", "Aluminum", "KM", 280000, None, False, 400),
            
            # Cement
            ("MAT-007", "Cement_OPC_53Grade", "Cement", "MT", 6500, 90, True, 1000),
            ("MAT-008", "Cement_PPC", "Cement", "MT", 6200, 90, True, 1000),
            
            # Insulators
            ("MAT-009", "Insulators_Disc_Type", "Insulators", "Pieces", 850, 3650, False, 5),
            ("MAT-010", "Insulators_Polymer", "Insulators", "Pieces", 1200, 3650, False, 3),
            
            # Transformers
            ("MAT-011", "Transformer_400kV", "Transformers", "Unit", 15000000, None, False, 50000),
            ("MAT-012", "Transformer_220kV", "Transformers", "Unit", 8500000, None, False, 35000),
            ("MAT-013", "Transformer_132kV", "Transformers", "Unit", 4200000, None, False, 25000),
            
            # Cables
            ("MAT-014", "Cables_HT_11kV", "Cables", "KM", 125000, 730, False, 800),
            ("MAT-015", "Cables_LT_415V", "Cables", "KM", 45000, 730, False, 400),
            
            # Switchgear
            ("MAT-016", "Switchgear_GIS_400kV", "Switchgear", "Bay", 25000000, None, False, 15000),
            ("MAT-017", "Switchgear_AIS_220kV", "Switchgear", "Bay", 12000000, None, False, 10000),
            
            # Oil & Consumables
            ("MAT-018", "Transformer_Oil", "Oil", "KL", 95000, 365, True, 900),
            ("MAT-019", "Lubricating_Oil", "Oil", "Liters", 450, 365, True, 0.9),
            
            # Hardware & Fasteners
            ("MAT-020", "Hardware_Fasteners_Set", "Hardware", "Set", 8500, None, False, 50),
            ("MAT-021", "Hardware_Clamps", "Hardware", "Pieces", 350, None, False, 2),
            
            # Foundation materials
            ("MAT-022", "Foundation_Bolts", "Hardware", "Set", 12000, None, False, 100),
            ("MAT-023", "Gravel_Aggregate", "Cement", "MT", 1800, None, False, 1000),
            
            # Protection equipment
            ("MAT-024", "Lightning_Arrester_400kV", "Switchgear", "Unit", 580000, None, False, 150),
            ("MAT-025", "Circuit_Breaker_220kV", "Switchgear", "Unit", 3200000, None, False, 800),
            
            # Miscellaneous
            ("MAT-026", "Control_Cables", "Cables", "KM", 35000, 730, False, 300),
            ("MAT-027", "Optical_Fiber_Cable", "Cables", "KM", 28000, 730, False, 50),
            ("MAT-028", "Battery_Bank_System", "Hardware", "Set", 850000, 1825, False, 1000),
            ("MAT-029", "Diesel_Generator_500kVA", "Hardware", "Unit", 1200000, None, False, 5000),
            ("MAT-030", "Fire_Suppression_System", "Hardware", "Unit", 450000, None, False, 500),
        ]
        
        materials = []
        for data in materials_data:
            mat = Material(
                id=data[0],
                name=data[1],
                category=data[2],
                unit=data[3],
                base_price=data[4],
                shelf_life_days=data[5],
                is_perishable=data[6],
                weight_per_unit=data[7]
            )
            materials.append(mat)
        
        return materials
    
    def generate_vendors(self) -> List[Vendor]:
        """Generate vendor master data with regional specialization"""
        vendors = []
        vendor_names = [
            "Tata Steel", "JSW Steel", "SAIL", "L&T Heavy Engineering",
            "Siemens India", "ABB India", "Crompton Greaves", "Bharat Heavy Electricals",
            "Kalpataru Power", "KEC International", "Sterlite Power",
            "Apar Industries", "Gupta Power", "Skipper Limited",
            "Jyoti Structures", "STL", "Adani Transmission", "Precision Wires",
            "Supreme Industries", "Polycab India"
        ]
        
        # Regional specialization mapping
        region_specializations = {
            "Northern": ["Steel", "Cement", "Hardware"],
            "Western": ["Transformers", "Switchgear", "Cables"],
            "Eastern": ["Steel", "Copper", "Aluminum"],
            "Southern": ["Insulators", "Cables", "Oil"],
            "North-Eastern": ["Hardware", "Cement", "Cables"]
        }
        
        for i, name in enumerate(vendor_names):
            region = random.choice(list(REGIONS.keys()))
            state = random.choice(REGIONS[region])
            
            # Get a city in that region for coordinates
            city = random.choice(list(MAJOR_CITIES.keys()))
            base_coords = MAJOR_CITIES.get(city, (28.6, 77.2))
            # Add some randomness to coordinates
            lat = base_coords[0] + random.uniform(-1, 1)
            lon = base_coords[1] + random.uniform(-1, 1)
            
            # Assign specializations based on region
            base_specializations = region_specializations[region]
            # Add 1-2 more random specializations
            all_categories = list(set(GST_RATES.keys()))
            extra = random.sample([c for c in all_categories if c not in base_specializations], 
                                 k=random.randint(1, 2))
            specializations = base_specializations + extra
            
            # Reliability score (more established vendors = higher reliability)
            if i < 10:  # Top 10 are excellent
                reliability = round(random.uniform(0.95, 1.0), 3)
                max_delay = random.randint(2, 7)
                avg_lead_time = random.randint(20, 35)
            elif i < 15:  # Next 5 are good
                reliability = round(random.uniform(0.85, 0.95), 3)
                max_delay = random.randint(5, 15)
                avg_lead_time = random.randint(30, 45)
            else:  # Rest are average
                reliability = round(random.uniform(0.70, 0.85), 3)
                max_delay = random.randint(10, 30)
                avg_lead_time = random.randint(40, 60)
            
            # Price competitiveness (inverse to reliability - cheaper = less reliable)
            price_comp = round(1.1 - (reliability * 0.3), 2)
            
            # Generate material prices based on specialization
            material_prices = {}
            for mat in self.materials:
                if mat.category in specializations:
                    # Price = base price * competitiveness * random factor
                    price = mat.base_price * price_comp * random.uniform(0.95, 1.05)
                    material_prices[mat.id] = round(price, 2)
            
            vendor = Vendor(
                id=f"VEN-{i+1:03d}",
                name=name,
                region=region,
                state=state,
                specializations=specializations,
                reliability_score=reliability,
                max_delay_days=max_delay,
                price_competitiveness=price_comp,
                min_order_value=random.choice([50000, 100000, 200000, 500000]),
                material_prices=material_prices,
                avg_lead_time_days=avg_lead_time,
                latitude=lat,
                longitude=lon
            )
            vendors.append(vendor)
        
        return vendors
    
    def generate_warehouses(self) -> List[Warehouse]:
        """Generate warehouse network with realistic distribution"""
        warehouses = []
        
        # Create warehouses in major cities
        for i, (city, coords) in enumerate(MAJOR_CITIES.items()):
            # Find region
            region = None
            state = None
            for reg, states in REGIONS.items():
                for st in states:
                    if st in city or city in ["Mumbai", "Pune"] and st == "Maharashtra":
                        region = reg
                        state = st
                        break
                    elif city == "Delhi" and st == "Delhi":
                        region = reg
                        state = st
                        break
                    elif city == "Kolkata" and st == "West Bengal":
                        region = reg
                        state = st
                        break
                    elif city == "Chennai" and st == "Tamil Nadu":
                        region = reg
                        state = st
                        break
                    elif city == "Bangalore" and st == "Karnataka":
                        region = reg
                        state = st
                        break
                if region:
                    break
            
            # Default assignments
            if not region:
                if city in ["Ahmedabad", "Jaipur"]:
                    region, state = "Western", "Gujarat" if city == "Ahmedabad" else "Rajasthan"
                elif city in ["Guwahati"]:
                    region, state = "North-Eastern", "Assam"
                elif city in ["Hyderabad"]:
                    region, state = "Southern", "Telangana"
                elif city in ["Thiruvananthapuram"]:
                    region, state = "Southern", "Kerala"
                elif city in ["Lucknow"]:
                    region, state = "Northern", "Uttar Pradesh"
                elif city in ["Bhubaneswar"]:
                    region, state = "Eastern", "Odisha"
                elif city in ["Patna"]:
                    region, state = "Eastern", "Bihar"
                elif city in ["Chandigarh"]:
                    region, state = "Northern", "Chandigarh"
                else:
                    region, state = "Northern", "Delhi"
            
            capacity = random.randint(50000, 150000)
            initial_load = int(capacity * random.uniform(0.3, 0.6))
            
            warehouse = Warehouse(
                id=f"WH-{i+1:03d}",
                name=f"{city}_Central_Warehouse",
                region=region,
                state=state,
                city=city,
                latitude=coords[0],
                longitude=coords[1],
                max_capacity=capacity,
                current_load=initial_load
            )
            
            # Initialize some inventory
            num_materials = random.randint(10, 20)
            selected_materials = random.sample(self.materials, num_materials)
            for mat in selected_materials:
                qty = random.randint(100, 5000)
                warehouse.inventory[mat.id] = qty
                # Set safety stock (20% of current)
                warehouse.safety_stock[mat.id] = int(qty * 0.2)
            
            warehouses.append(warehouse)
        
        return warehouses
    
    def generate_projects(self) -> List[Project]:
        """Generate project portfolio with realistic parameters"""
        projects = []
        
        for i in range(NUM_PROJECTS):
            # Project basics
            project_type = random.choice(list(ProjectType))
            region = random.choice(list(REGIONS.keys()))
            state = random.choice(REGIONS[region])
            
            # Timeline
            start_offset = random.randint(0, 180)  # Projects started in last 6 months
            start_date = START_DATE + timedelta(days=start_offset)
            duration_days = random.randint(365, 1095)  # 1-3 years
            end_date = start_date + timedelta(days=duration_days)
            
            # Stage (proportional to time elapsed)
            elapsed_ratio = start_offset / 180
            if elapsed_ratio < 0.2:
                stage = ProjectStage.PLANNING
            elif elapsed_ratio < 0.4:
                stage = ProjectStage.FOUNDATION
            elif elapsed_ratio < 0.8:
                stage = ProjectStage.CONSTRUCTION
            else:
                stage = ProjectStage.COMMISSIONING
            
            # Status (90% active, 10% various issues)
            status_roll = random.random()
            if status_roll < 0.90:
                status = ProjectStatus.ACTIVE
            elif status_roll < 0.95:
                status = ProjectStatus.ON_HOLD
            else:
                status = ProjectStatus.DELAYED
            
            # Location (near a warehouse)
            nearby_warehouse = random.choice(self.warehouses)
            lat_offset = random.uniform(-2, 2)
            lon_offset = random.uniform(-2, 2)
            
            # Terrain
            terrain = random.choice(list(TerrainType))
            
            # Specifications
            if project_type == ProjectType.TRANSMISSION_LINE:
                length_km = round(random.uniform(50, 500), 1)
                voltage_kv = random.choice([220, 400, 765])
                capacity_mw = None
                name = f"{state}_{voltage_kv}kV_Line_{i+1}"
            elif project_type == ProjectType.SUBSTATION:
                length_km = None
                voltage_kv = random.choice([132, 220, 400])
                capacity_mw = round(random.uniform(100, 1000), 0)
                name = f"{state}_{voltage_kv}kV_Substation_{i+1}"
            else:  # HVDC
                length_km = round(random.uniform(200, 1500), 1)
                voltage_kv = random.choice([500, 800])
                capacity_mw = round(random.uniform(2000, 6000), 0)
                name = f"{region}_HVDC_Corridor_{i+1}"
            
            # RoW status (5% blocked)
            row_status = "Blocked" if random.random() < 0.05 else "Clear"
            
            project = Project(
                id=f"PRJ-{i+1:03d}",
                name=name,
                project_type=project_type,
                region=region,
                state=state,
                stage=stage,
                status=status,
                start_date=start_date,
                expected_end_date=end_date,
                latitude=nearby_warehouse.latitude + lat_offset,
                longitude=nearby_warehouse.longitude + lon_offset,
                length_km=length_km,
                voltage_kv=voltage_kv,
                capacity_mw=capacity_mw,
                terrain_type=terrain,
                row_status=row_status
            )
            
            projects.append(project)
        
        return projects
    
    def generate_bom_standards(self):
        """Generate BOM standards CSV"""
        bom_data = []
        
        # Transmission Line BOMs
        for voltage in [220, 400, 765]:
            materials_needed = {
                "MAT-001": int(5 * voltage / 100),  # Steel per km
                "MAT-002": int(8 * voltage / 100),  # Lattice tower
                "MAT-004": int(1 * voltage / 220),  # Conductor
                "MAT-009": int(50 * voltage / 220),  # Insulators
                "MAT-020": int(20 * voltage / 220),  # Hardware
            }
            
            for mat_id, qty_per_km in materials_needed.items():
                bom_data.append({
                    "Project_Type": "Transmission_Line",
                    "Voltage_kV": voltage,
                    "Material_ID": mat_id,
                    "Quantity_Per_Unit": qty_per_km,
                    "Unit": "per_km",
                    "Stage_Planning_Pct": 0.1,
                    "Stage_Foundation_Pct": 0.3,
                    "Stage_Construction_Pct": 0.5,
                    "Stage_Commissioning_Pct": 0.1
                })
        
        # Substation BOMs
        for voltage in [132, 220, 400]:
            materials_needed = {
                "MAT-011" if voltage == 400 else "MAT-012" if voltage == 220 else "MAT-013": 1,  # Transformer
                "MAT-016" if voltage == 400 else "MAT-017": 2,  # Switchgear bays
                "MAT-024": 3,  # Lightning arresters
                "MAT-025": 2,  # Circuit breakers
                "MAT-007": 500,  # Cement
                "MAT-022": 50,  # Foundation bolts
            }
            
            for mat_id, qty in materials_needed.items():
                bom_data.append({
                    "Project_Type": "Substation",
                    "Voltage_kV": voltage,
                    "Material_ID": mat_id,
                    "Quantity_Per_Unit": qty,
                    "Unit": "per_substation",
                    "Stage_Planning_Pct": 0.1,
                    "Stage_Foundation_Pct": 0.3,
                    "Stage_Construction_Pct": 0.5,
                    "Stage_Commissioning_Pct": 0.1
                })
        
        df = pd.DataFrame(bom_data)
        os.makedirs(RAW_DATA_DIR, exist_ok=True)
        df.to_csv(os.path.join(RAW_DATA_DIR, "Master_BOM_Standards.csv"), index=False)
        print("✓ Generated BOM Standards")
    
    def generate_market_sentiment_log(self):
        """Generate market sentiment data for simulation period"""
        sentiments = []
        current_date = START_DATE
        
        for day in range(SIMULATION_DAYS):
            # 95% normal days, 5% events
            if random.random() < 0.95:
                topic = "Normal"
                severity = "Low"
                description = "Normal market conditions"
                action = "Continue standard operations"
            else:
                topic = random.choice(["RoW_Issue", "Labor_Strike", "Commodity_Price_Spike", "Policy_Change"])
                severity = random.choice(["Medium", "High"])
                
                if topic == "RoW_Issue":
                    description = "Land acquisition delays reported"
                    action = "Hold procurement for affected projects"
                elif topic == "Labor_Strike":
                    description = "Transport workers strike in region"
                    action = "Buffer lead times by 15 days"
                elif topic == "Commodity_Price_Spike":
                    description = "Steel prices increased by 15-20%"
                    action = "Review vendor contracts"
                else:
                    description = "New GST rate changes announced"
                    action = "Update tax calculations"
            
            region = random.choice(list(REGIONS.keys()))
            affected_states = REGIONS[region] if random.random() < 0.5 else random.sample(REGIONS[region], k=2)
            
            sentiments.append({
                "Date": (current_date + timedelta(days=day)).strftime("%Y-%m-%d"),
                "Region": region,
                "Topic": topic,
                "Severity": severity,
                "Affected_States": ",".join(affected_states),
                "Description": description,
                "Recommended_Action": action
            })
        
        df = pd.DataFrame(sentiments)
        df.to_csv(os.path.join(RAW_DATA_DIR, "Market_Sentiment_Log.csv"), index=False)
        print("✓ Generated Market Sentiment Log")
    
    def generate_weather_forecast(self):
        """Generate weather forecast data"""
        forecasts = []
        current_date = START_DATE
        
        for day in range(SIMULATION_DAYS):
            date = current_date + timedelta(days=day)
            month = date.month
            
            for region, states in REGIONS.items():
                for state in states:
                    # Seasonal patterns
                    if month in MONSOON_MONTHS:
                        condition = random.choice(["Heavy_Rain", "Moderate_Rain", "Moderate_Rain", "Clear"])
                        precip = random.uniform(10, 100) if "Rain" in condition else random.uniform(0, 5)
                        temp = random.uniform(25, 35)
                    elif month in WINTER_MONTHS:
                        condition = random.choice(["Cold", "Clear", "Clear"])
                        precip = random.uniform(0, 5)
                        temp = random.uniform(10, 20)
                    else:
                        condition = random.choice(["Clear", "Clear", "Clear", "Extreme_Heat"])
                        precip = random.uniform(0, 5)
                        temp = random.uniform(30, 45) if condition == "Extreme_Heat" else random.uniform(25, 35)
                    
                    forecasts.append({
                        "Date": date.strftime("%Y-%m-%d"),
                        "Region": region,
                        "State": state,
                        "Condition": condition,
                        "Temperature_C": round(temp, 1),
                        "Precipitation_mm": round(precip, 1)
                    })
        
        df = pd.DataFrame(forecasts)
        df.to_csv(os.path.join(RAW_DATA_DIR, "Weather_Forecast_Master.csv"), index=False)
        print("✓ Generated Weather Forecast")
    
    def generate_historical_consumption(self):
        """Generate historical consumption data for Prophet training"""
        # Generate 2 years of historical data for high-volume consumables
        historical_data = []
        hist_start = START_DATE - timedelta(days=730)
        
        for mat in self.materials:
            if mat.name in ["Transformer_Oil", "Insulators_Disc_Type", "Hardware_Fasteners_Set", 
                           "Cables_LT_415V", "Cement_OPC_53Grade"]:
                for day in range(730):
                    date = hist_start + timedelta(days=day)
                    month = date.month
                    
                    # Base consumption with seasonal patterns
                    base = random.randint(100, 500)
                    
                    # Generate realistic temperature (seasonal)
                    if month in [4, 5, 6]:  # Summer
                        temp = random.uniform(32, 45)
                    elif month in [12, 1, 2]:  # Winter
                        temp = random.uniform(10, 22)
                    else:
                        temp = random.uniform(22, 35)
                    
                    # Generate rainfall (monsoon heavy)
                    if month in MONSOON_MONTHS:
                        rainfall = random.uniform(5, 150)
                    else:
                        rainfall = random.uniform(0, 10)
                    
                    # Summer spike for oil and insulators
                    if month in [4, 5, 6] and mat.category in ["Oil", "Insulators"]:
                        base *= 1.3
                    
                    # Monsoon spike for hardware and cement
                    if month in MONSOON_MONTHS and mat.category in ["Hardware", "Cement"]:
                        base *= 1.2
                    
                    # Add noise
                    consumption = int(base * random.uniform(0.8, 1.2))
                    
                    for region in REGIONS.keys():
                        historical_data.append({
                            "date": date.strftime("%Y-%m-%d"),  # Prophet expects lowercase
                            "material_id": mat.id,
                            "material_name": mat.name,
                            "region": region,
                            "quantity": consumption,  # Prophet expects 'y' which maps to quantity
                            "temperature": round(temp, 1),
                            "rainfall": round(rainfall, 1)
                        })
        
        df = pd.DataFrame(historical_data)
        df.to_csv(os.path.join(GENERATED_DATA_DIR, "historical_consumption.csv"), index=False)
        print("✓ Generated Historical Consumption Data")
    
    def save_all(self):
        """Save all generated data to CSV files"""
        os.makedirs(GENERATED_DATA_DIR, exist_ok=True)
        
        # Materials
        df_materials = pd.DataFrame([
            {
                "Material_ID": m.id,
                "Name": m.name,
                "Category": m.category,
                "Unit": m.unit,
                "Base_Price_INR": m.base_price,
                "Shelf_Life_Days": m.shelf_life_days,
                "Is_Perishable": m.is_perishable,
                "Weight_Per_Unit_kg": m.weight_per_unit
            }
            for m in self.materials
        ])
        df_materials.to_csv(os.path.join(GENERATED_DATA_DIR, "materials.csv"), index=False)
        
        # Vendors
        df_vendors = pd.DataFrame([
            {
                "Vendor_ID": v.id,
                "Name": v.name,
                "Region": v.region,
                "State": v.state,
                "Specializations": ",".join(v.specializations),
                "Reliability_Score": v.reliability_score,
                "Max_Delay_Days": v.max_delay_days,
                "Price_Competitiveness": v.price_competitiveness,
                "Min_Order_Value_INR": v.min_order_value
            }
            for v in self.vendors
        ])
        df_vendors.to_csv(os.path.join(GENERATED_DATA_DIR, "vendors.csv"), index=False)
        
        # Warehouses
        df_warehouses = pd.DataFrame([
            {
                "Warehouse_ID": w.id,
                "Name": w.name,
                "Region": w.region,
                "State": w.state,
                "City": w.city,
                "Latitude": w.latitude,
                "Longitude": w.longitude,
                "Max_Capacity": w.max_capacity,
                "Current_Load": w.current_load
            }
            for w in self.warehouses
        ])
        df_warehouses.to_csv(os.path.join(GENERATED_DATA_DIR, "warehouses.csv"), index=False)
        
        # Projects
        df_projects = pd.DataFrame([
            {
                "Project_ID": p.id,
                "Name": p.name,
                "Type": p.project_type.value,
                "Region": p.region,
                "State": p.state,
                "Stage": p.stage.value,
                "Status": p.status.value,
                "Start_Date": p.start_date.strftime("%Y-%m-%d"),
                "Expected_End_Date": p.expected_end_date.strftime("%Y-%m-%d"),
                "Latitude": p.latitude,
                "Longitude": p.longitude,
                "Length_km": p.length_km,
                "Voltage_kV": p.voltage_kv,
                "Capacity_MW": p.capacity_mw,
                "Terrain": p.terrain_type.value,
                "RoW_Status": p.row_status
            }
            for p in self.projects
        ])
        df_projects.to_csv(os.path.join(GENERATED_DATA_DIR, "projects.csv"), index=False)


if __name__ == "__main__":
    """Generate all datasets"""
    factory = DataFactory(seed=42)
    factory.generate_all()
    print("\n🎉 Digital Twin generation complete!")
    print(f"📁 Data saved to: {GENERATED_DATA_DIR}")
