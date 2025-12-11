"""
Seed Additional Substations and Warehouses for Demo Richness
Adds strategically placed substations and warehouses across India's power grid network
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import random

from sqlalchemy.orm import Session
from src.api.database import SessionLocal, init_db
from src.api import db_models


def calculate_distance_km(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates using Haversine formula"""
    import math
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def seed_additional_data():
    """Add more substations and warehouses for demo richness"""
    
    db = SessionLocal()
    
    try:
        # =====================================================================
        # ADDITIONAL POWERGRID SUBSTATIONS ACROSS INDIA
        # =====================================================================
        
        substations_data = [
            # Northern Region - Additional
            {"code": "SUB-DEL-001", "name": "Bawana Substation", "type": "400/220kV", "capacity": "400kV",
             "state": "Delhi", "city": "Delhi", "lat": 28.7889, "lon": 77.0515},
            {"code": "SUB-HAR-001", "name": "Jhajjar HVDC Station", "type": "765/400kV", "capacity": "765kV",
             "state": "Haryana", "city": "Jhajjar", "lat": 28.6096, "lon": 76.6566},
            {"code": "SUB-UP-001", "name": "Agra Substation", "type": "400/220kV", "capacity": "400kV",
             "state": "Uttar Pradesh", "city": "Agra", "lat": 27.1767, "lon": 78.0081},
            {"code": "SUB-PUN-001", "name": "Ludhiana Substation", "type": "220/132kV", "capacity": "220kV",
             "state": "Punjab", "city": "Ludhiana", "lat": 30.9010, "lon": 75.8573},
            
            # Western Region
            {"code": "SUB-MAH-001", "name": "Padghe HVDC Station", "type": "765/400kV", "capacity": "765kV",
             "state": "Maharashtra", "city": "Mumbai", "lat": 19.1531, "lon": 73.0855},
            {"code": "SUB-MAH-002", "name": "Pune Substation", "type": "400/220kV", "capacity": "400kV",
             "state": "Maharashtra", "city": "Pune", "lat": 18.5204, "lon": 73.8567},
            {"code": "SUB-GUJ-001", "name": "Gandhinagar Substation", "type": "400/220kV", "capacity": "400kV",
             "state": "Gujarat", "city": "Gandhinagar", "lat": 23.2156, "lon": 72.6369},
            {"code": "SUB-MP-001", "name": "Bhopal Substation", "type": "400/220kV", "capacity": "400kV",
             "state": "Madhya Pradesh", "city": "Bhopal", "lat": 23.2599, "lon": 77.4126},
            
            # Southern Region
            {"code": "SUB-KAR-002", "name": "Mysore Substation", "type": "220/132kV", "capacity": "220kV",
             "state": "Karnataka", "city": "Mysore", "lat": 12.2958, "lon": 76.6394},
            {"code": "SUB-TN-001", "name": "Chennai North Substation", "type": "400/220kV", "capacity": "400kV",
             "state": "Tamil Nadu", "city": "Chennai", "lat": 13.1389, "lon": 80.2561},
            {"code": "SUB-TN-002", "name": "Madurai Substation", "type": "220/132kV", "capacity": "220kV",
             "state": "Tamil Nadu", "city": "Madurai", "lat": 9.9252, "lon": 78.1198},
            {"code": "SUB-KER-001", "name": "Cochin Substation", "type": "220/132kV", "capacity": "220kV",
             "state": "Kerala", "city": "Kochi", "lat": 9.9312, "lon": 76.2673},
            {"code": "SUB-AP-001", "name": "Hyderabad Substation", "type": "400/220kV", "capacity": "400kV",
             "state": "Telangana", "city": "Hyderabad", "lat": 17.3850, "lon": 78.4867},
            
            # Eastern Region
            {"code": "SUB-WB-001", "name": "Kolkata Substation", "type": "400/220kV", "capacity": "400kV",
             "state": "West Bengal", "city": "Kolkata", "lat": 22.5726, "lon": 88.3639},
            {"code": "SUB-OD-001", "name": "Bhubaneswar Substation", "type": "400/220kV", "capacity": "400kV",
             "state": "Odisha", "city": "Bhubaneswar", "lat": 20.2961, "lon": 85.8245},
            {"code": "SUB-JH-001", "name": "Ranchi Substation", "type": "220/132kV", "capacity": "220kV",
             "state": "Jharkhand", "city": "Ranchi", "lat": 23.3441, "lon": 85.3096},
            {"code": "SUB-BH-001", "name": "Patna Substation", "type": "400/220kV", "capacity": "400kV",
             "state": "Bihar", "city": "Patna", "lat": 25.5941, "lon": 85.1376},
            
            # North-Eastern Region
            {"code": "SUB-AS-001", "name": "Guwahati Substation", "type": "220/132kV", "capacity": "220kV",
             "state": "Assam", "city": "Guwahati", "lat": 26.1445, "lon": 91.7362},
            
            # Special HVDC Stations
            {"code": "SUB-HV-001", "name": "Champa HVDC Station", "type": "800kV HVDC", "capacity": "765kV",
             "state": "Chhattisgarh", "city": "Champa", "lat": 22.0350, "lon": 82.6494},
            {"code": "SUB-HV-002", "name": "Kurukshetra HVDC Station", "type": "800kV HVDC", "capacity": "765kV",
             "state": "Haryana", "city": "Kurukshetra", "lat": 29.9695, "lon": 76.8783},
        ]
        
        # Check existing substations
        existing_subs = {s.substation_code for s in db.query(db_models.Substation).all()}
        
        added_substations = 0
        for sub in substations_data:
            if sub["code"] not in existing_subs:
                new_sub = db_models.Substation(
                    substation_code=sub["code"],
                    name=sub["name"],
                    substation_type=sub["type"],
                    capacity=sub["capacity"],
                    state=sub["state"],
                    city=sub["city"],
                    latitude=sub["lat"],
                    longitude=sub["lon"],
                    status="Active",
                    stock_status="Normal",
                    stock_level_percentage=random.uniform(70, 100)
                )
                db.add(new_sub)
                added_substations += 1
        
        db.commit()
        print(f"✅ Added {added_substations} new substations")
        
        # =====================================================================
        # ADDITIONAL REGIONAL WAREHOUSES
        # =====================================================================
        
        warehouses_data = [
            # Northern Region Warehouses
            {"code": "WH-NR-DEL", "name": "Delhi Central Warehouse", 
             "state": "Delhi", "city": "Delhi", "region": "Northern",
             "lat": 28.6358, "lon": 77.2245, "capacity": 5000},
            {"code": "WH-NR-JAI", "name": "Jaipur Regional Depot",
             "state": "Rajasthan", "city": "Jaipur", "region": "Northern",
             "lat": 26.8489, "lon": 75.8041, "capacity": 3000},
            {"code": "WH-NR-LKO", "name": "Lucknow Storage Facility",
             "state": "Uttar Pradesh", "city": "Lucknow", "region": "Northern",
             "lat": 26.8467, "lon": 80.9462, "capacity": 4000},
            
            # Western Region Warehouses
            {"code": "WH-WR-MUM", "name": "Mumbai Central Warehouse",
             "state": "Maharashtra", "city": "Mumbai", "region": "Western",
             "lat": 19.0760, "lon": 72.8777, "capacity": 6000},
            {"code": "WH-WR-AHM", "name": "Ahmedabad Depot",
             "state": "Gujarat", "city": "Ahmedabad", "region": "Western",
             "lat": 23.0225, "lon": 72.5714, "capacity": 4000},
            {"code": "WH-WR-NAG", "name": "Nagpur Central Depot",
             "state": "Maharashtra", "city": "Nagpur", "region": "Western",
             "lat": 21.1458, "lon": 79.0882, "capacity": 3000},
            
            # Southern Region Warehouses
            {"code": "WH-SR-BLR", "name": "Bangalore Tech Hub Warehouse",
             "state": "Karnataka", "city": "Bangalore", "region": "Southern",
             "lat": 12.9716, "lon": 77.5946, "capacity": 5500},
            {"code": "WH-SR-CHN", "name": "Chennai Port Depot",
             "state": "Tamil Nadu", "city": "Chennai", "region": "Southern",
             "lat": 13.0827, "lon": 80.2707, "capacity": 4500},
            {"code": "WH-SR-HYD", "name": "Hyderabad Central Warehouse",
             "state": "Telangana", "city": "Hyderabad", "region": "Southern",
             "lat": 17.3850, "lon": 78.4867, "capacity": 5000},
            
            # Eastern Region Warehouses
            {"code": "WH-ER-KOL", "name": "Kolkata Central Warehouse",
             "state": "West Bengal", "city": "Kolkata", "region": "Eastern",
             "lat": 22.5726, "lon": 88.3639, "capacity": 4500},
            {"code": "WH-ER-BBS", "name": "Bhubaneswar Depot",
             "state": "Odisha", "city": "Bhubaneswar", "region": "Eastern",
             "lat": 20.2961, "lon": 85.8245, "capacity": 3000},
            
            # North-Eastern Region
            {"code": "WH-NE-GUW", "name": "Guwahati Regional Depot",
             "state": "Assam", "city": "Guwahati", "region": "North-Eastern",
             "lat": 26.1445, "lon": 91.7362, "capacity": 2000},
        ]
        
        # Check existing warehouses
        existing_whs = {w.warehouse_code for w in db.query(db_models.Warehouse).all()}
        
        added_warehouses = 0
        for wh in warehouses_data:
            if wh["code"] not in existing_whs:
                new_wh = db_models.Warehouse(
                    warehouse_code=wh["code"],
                    name=wh["name"],
                    state=wh["state"],
                    city=wh["city"],
                    region=wh["region"],
                    latitude=wh["lat"],
                    longitude=wh["lon"],
                    capacity_tons=wh["capacity"],
                    is_active=True
                )
                db.add(new_wh)
                added_warehouses += 1
        
        db.commit()
        print(f"✅ Added {added_warehouses} new warehouses")
        
        # =====================================================================
        # LINK SUBSTATIONS TO NEAREST WAREHOUSES
        # =====================================================================
        
        all_warehouses = db.query(db_models.Warehouse).all()
        substations = db.query(db_models.Substation).filter(
            db_models.Substation.primary_warehouse_id == None
        ).all()
        
        linked = 0
        for sub in substations:
            if sub.latitude and sub.longitude:
                min_distance = float('inf')
                nearest_wh = None
                
                for wh in all_warehouses:
                    if wh.latitude and wh.longitude:
                        dist = calculate_distance_km(
                            sub.latitude, sub.longitude,
                            wh.latitude, wh.longitude
                        )
                        if dist < min_distance:
                            min_distance = dist
                            nearest_wh = wh
                
                if nearest_wh:
                    sub.primary_warehouse_id = nearest_wh.id
                    linked += 1
        
        db.commit()
        print(f"✅ Linked {linked} substations to nearest warehouses")
        
        # =====================================================================
        # ADD INVENTORY FOR NEW WAREHOUSES
        # =====================================================================
        
        # Get all materials
        materials = db.query(db_models.Material).limit(25).all()  # Top 25 materials
        new_warehouses = db.query(db_models.Warehouse).filter(
            db_models.Warehouse.warehouse_code.like("WH-%")
        ).all()
        
        added_inventory = 0
        for wh in new_warehouses:
            for mat in materials:
                # Check if already exists
                exists = db.query(db_models.InventoryStock).filter(
                    db_models.InventoryStock.warehouse_id == wh.id,
                    db_models.InventoryStock.material_id == mat.id
                ).first()
                
                if not exists:
                    # Random stock levels - some understocked for demo
                    if random.random() < 0.2:  # 20% understocked
                        base_qty = random.randint(10, 50)
                    elif random.random() < 0.1:  # 10% overstocked
                        base_qty = random.randint(400, 600)
                    else:  # 70% normal
                        base_qty = random.randint(100, 300)
                    
                    stock = db_models.InventoryStock(
                        warehouse_id=wh.id,
                        material_id=mat.id,
                        quantity_available=base_qty,
                        quantity_reserved=random.randint(0, int(base_qty * 0.2)),
                        quantity_in_transit=random.randint(0, int(base_qty * 0.1)),
                        reorder_point=int(base_qty * 0.4),
                        max_stock_level=int(base_qty * 2),
                        min_stock_level=int(base_qty * 0.25),
                        last_restocked_date=datetime.now() - timedelta(days=random.randint(1, 30))
                    )
                    db.add(stock)
                    added_inventory += 1
        
        db.commit()
        print(f"✅ Added {added_inventory} inventory records for new warehouses")
        
        # =====================================================================
        # ADD SOME TRANSACTIONS FOR NEW WAREHOUSES
        # =====================================================================
        
        transaction_types = ["IN", "OUT", "TRANSFER_IN", "TRANSFER_OUT"]
        added_transactions = 0
        
        for wh in new_warehouses[:5]:  # Add transactions for first 5 new warehouses
            for mat in materials[:10]:  # Top 10 materials
                for _ in range(random.randint(2, 5)):  # 2-5 transactions each
                    tx_type = random.choice(transaction_types)
                    qty = random.randint(5, 50)
                    
                    tx = db_models.InventoryTransaction(
                        transaction_type=tx_type,
                        warehouse_id=wh.id,
                        material_id=mat.id,
                        quantity=qty,
                        unit_cost=mat.unit_price or 50000,
                        total_cost=qty * (mat.unit_price or 50000),
                        reference_type="SEED",
                        reference_id=f"TX-SEED-{added_transactions:04d}",
                        remarks=f"Seeded transaction for demo",
                        performed_by="SYSTEM",
                        transaction_date=datetime.now() - timedelta(days=random.randint(1, 60))
                    )
                    db.add(tx)
                    added_transactions += 1
        
        db.commit()
        print(f"✅ Added {added_transactions} transactions")
        
        # =====================================================================
        # SUMMARY
        # =====================================================================
        
        total_substations = db.query(db_models.Substation).count()
        total_warehouses = db.query(db_models.Warehouse).count()
        total_inventory = db.query(db_models.InventoryStock).count()
        total_transactions = db.query(db_models.InventoryTransaction).count()
        
        print("\n" + "="*60)
        print("📊 NEXUS DATA SUMMARY")
        print("="*60)
        print(f"   Total Substations:   {total_substations}")
        print(f"   Total Warehouses:    {total_warehouses}")
        print(f"   Total Inventory:     {total_inventory}")
        print(f"   Total Transactions:  {total_transactions}")
        print("="*60)
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n🏗️  NEXUS - Seeding Additional Substations & Warehouses")
    print("="*60)
    seed_additional_data()
    print("\n✅ Seeding complete!")
