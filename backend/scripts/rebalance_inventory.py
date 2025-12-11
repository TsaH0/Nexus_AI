"""
Rebalance Inventory Levels
==========================
Updates inventory stock to have a healthy mix:
- 55% GREEN (optimal stock)
- 30% AMBER (low but not critical)
- 15% RED (critical - needs attention for demo)

This creates realistic data for the demo while ensuring most items are well-stocked.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import random

from sqlalchemy.orm import Session
from sqlalchemy import func
from src.api.database import SessionLocal
from src.api import db_models


def rebalance_inventory():
    """Rebalance all inventory to have proper stock levels"""
    
    db = SessionLocal()
    
    try:
        # Get all inventory stocks with material info
        stocks = db.query(
            db_models.InventoryStock,
            db_models.Material
        ).join(
            db_models.Material,
            db_models.InventoryStock.material_id == db_models.Material.id
        ).all()
        
        print(f"📦 Found {len(stocks)} inventory records to rebalance")
        
        green_count = 0
        amber_count = 0
        red_count = 0
        
        for i, (stock, material) in enumerate(stocks):
            # Determine stock level category based on position
            # This ensures a good distribution
            rand = random.random()
            
            lead_time = material.lead_time_days or 14
            
            # Calculate base metrics using SAME logic as triggers engine
            # The engine uses: base_daily_demand = min_stock_level / 7
            # So we set min_stock_level = safety_stock, then demand = safety_stock / 7
            
            # Start with realistic demand (3-12 units/day)
            base_daily_demand = random.uniform(3, 12)
            demand_multiplier = random.uniform(1.0, 1.6)  # Simulate substation impact
            adjusted_demand = base_daily_demand * demand_multiplier
            
            # Safety stock = Z * σ * √LT (using engine's formula)
            # SS = 1.65 * (demand * 0.25) * sqrt(lead_time)
            # But engine also has minimum: max(calculated_ss, demand * 7)
            safety_stock = 1.65 * (adjusted_demand * 0.25) * (lead_time ** 0.5)
            safety_stock = max(safety_stock, adjusted_demand * 7)
            
            # Reorder point = (daily_demand * lead_time) + safety_stock
            reorder_point = (adjusted_demand * lead_time) + safety_stock
            
            # Max stock = reorder_point * 2.5
            max_stock = reorder_point * 2.5
            
            # SEVERITY THRESHOLDS (match triggers_engine.py):
            # RED: UTR > 0.7 OR days_of_stock < lead_time * 0.5 OR PAR < 0.2
            # AMBER: UTR > 0.4 OR days_of_stock < lead_time OR PAR < 0.4
            # GREEN: Otherwise
            
            if rand < 0.55:
                # GREEN: Well above reorder point
                # Ensure: UTR < 0.4, days_of_stock > lead_time, PAR > 0.4
                # UTR = (ROP - stock) / ROP < 0.4  =>  stock > ROP * 0.6
                # days_of_stock = stock / demand > lead_time  =>  stock > demand * lead_time
                min_for_green = max(reorder_point * 0.65, adjusted_demand * lead_time * 1.1)
                quantity = random.uniform(min_for_green, max_stock * 0.9)
                green_count += 1
            elif rand < 0.85:
                # AMBER: Near or slightly below ROP (triggers warning)
                # UTR between 0.4 and 0.7: stock between ROP*0.3 and ROP*0.6
                # OR days_of_stock < lead_time: stock < demand * lead_time
                min_for_amber = reorder_point * 0.35
                max_for_amber = reorder_point * 0.59
                quantity = random.uniform(min_for_amber, max_for_amber)
                amber_count += 1
            else:
                # RED: Critically low
                # UTR > 0.7: stock < ROP * 0.3
                # OR days_of_stock < lead_time * 0.5: stock < demand * lead_time * 0.5
                max_for_red = min(reorder_point * 0.28, adjusted_demand * lead_time * 0.45)
                quantity = random.uniform(max_for_red * 0.3, max_for_red)
                red_count += 1
            
            # Update stock record
            stock.quantity_available = round(quantity, 2)
            stock.quantity_reserved = round(quantity * random.uniform(0.05, 0.15), 2)
            stock.quantity_in_transit = round(quantity * random.uniform(0, 0.1), 2)
            stock.reorder_point = round(reorder_point, 2)
            stock.max_stock_level = round(max_stock, 2)
            stock.min_stock_level = round(safety_stock, 2)
            stock.last_restocked_date = datetime.now() - timedelta(days=random.randint(1, 30))
            stock.updated_at = datetime.now()
        
        db.commit()
        
        print(f"\n✅ Inventory Rebalanced:")
        print(f"   🟢 GREEN (optimal):  {green_count} ({green_count*100/len(stocks):.1f}%)")
        print(f"   🟡 AMBER (low):      {amber_count} ({amber_count*100/len(stocks):.1f}%)")
        print(f"   🔴 RED (critical):   {red_count} ({red_count*100/len(stocks):.1f}%)")
        
        # Verify the distribution with actual triggers calculation
        print("\n📊 Verifying with triggers engine...")
        
        from src.core.triggers_engine import TriggersEngine, Severity, calculate_distance_km
        
        engine = TriggersEngine(db)
        all_substations = db.query(db_models.Substation).all()
        
        severity_counts = {Severity.GREEN: 0, Severity.AMBER: 0, Severity.RED: 0}
        
        # Re-query stocks
        stocks = db.query(
            db_models.InventoryStock,
            db_models.Material,
            db_models.Warehouse
        ).join(
            db_models.Material,
            db_models.InventoryStock.material_id == db_models.Material.id
        ).join(
            db_models.Warehouse,
            db_models.InventoryStock.warehouse_id == db_models.Warehouse.id
        ).all()
        
        for stock, material, warehouse in stocks:
            # Find nearby substations
            nearby_substations = []
            if warehouse.latitude and warehouse.longitude:
                for sub in all_substations:
                    if sub.latitude and sub.longitude:
                        distance = calculate_distance_km(
                            warehouse.latitude, warehouse.longitude,
                            sub.latitude, sub.longitude
                        )
                        if distance <= 200:
                            nearby_substations.append({
                                "capacity": sub.capacity or "33kV"
                            })
            
            trigger = engine.compute_triggers(
                material_code=material.material_code or f"MAT-{material.id:03d}",
                material_name=material.name,
                warehouse_code=warehouse.warehouse_code or f"WH-{warehouse.id:03d}",
                warehouse_name=warehouse.name,
                current_stock=stock.quantity_available,
                lead_time_days=material.lead_time_days or 14,
                unit_price=material.unit_price or 50000,
                nearby_substations=nearby_substations,
                max_stock_level=stock.max_stock_level
            )
            
            severity_counts[trigger.severity] += 1
        
        total = sum(severity_counts.values())
        print(f"\n📈 Actual Severity Distribution (from triggers engine):")
        print(f"   🟢 GREEN: {severity_counts[Severity.GREEN]} ({severity_counts[Severity.GREEN]*100/total:.1f}%)")
        print(f"   🟡 AMBER: {severity_counts[Severity.AMBER]} ({severity_counts[Severity.AMBER]*100/total:.1f}%)")
        print(f"   🔴 RED:   {severity_counts[Severity.RED]} ({severity_counts[Severity.RED]*100/total:.1f}%)")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n🔄 NEXUS - Rebalancing Inventory Levels")
    print("="*60)
    rebalance_inventory()
    print("\n✅ Rebalancing complete!")
