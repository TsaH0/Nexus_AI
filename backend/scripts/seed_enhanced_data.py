"""
NEXUS Enhanced Seed Script - Complete Project Data
====================================================

This script seeds the database with:
1. VOLTAGE-SPECIFIC MATERIALS - Materials for 400kV, 220kV, 132kV, 33kV
2. PROJECT-SPECIFIC INVENTORY - Different stock at different warehouses
3. TRANSACTION HISTORY - Past material movements
4. FUTURE PROCUREMENTS - Planned orders with timelines
5. ALERTS DATA - Sample alerts for testing

Run: python -m scripts.seed_enhanced_data
"""

import random
import json
from datetime import datetime, timedelta
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker

from src.api.db_models import (
    Base, Material, Warehouse, InventoryStock,
    Substation, SubstationProject, ProjectMaterialNeed,
    MaterialTransfer, PurchaseOrder, Vendor, ProjectIssue,
    InventoryTransaction
)


# ============================================================================
# VOLTAGE-SPECIFIC MATERIALS (Complete BOQ for all voltage levels)
# ============================================================================

MATERIALS_BY_VOLTAGE = {
    "400kV": [
        {"code": "MAT-400-T01", "name": "400kV D/C Tower - Type A (Suspension)", "category": "Towers & Structures", "unit": "Nos", "unit_price": 1250000.0, "lead_time_days": 45, "min_order_qty": 1},
        {"code": "MAT-400-T02", "name": "400kV D/C Tower - Type B (Tension)", "category": "Towers & Structures", "unit": "Nos", "unit_price": 1650000.0, "lead_time_days": 45, "min_order_qty": 1},
        {"code": "MAT-400-T03", "name": "400kV D/C Tower - Type C (Dead End)", "category": "Towers & Structures", "unit": "Nos", "unit_price": 1850000.0, "lead_time_days": 60, "min_order_qty": 1},
        {"code": "MAT-400-C01", "name": "ACSR Moose Conductor 400kV", "category": "Conductor", "unit": "km", "unit_price": 125000.0, "lead_time_days": 30, "min_order_qty": 10},
        {"code": "MAT-400-C02", "name": "OPGW Earth Wire 400kV", "category": "Conductor", "unit": "km", "unit_price": 235000.0, "lead_time_days": 45, "min_order_qty": 5},
        {"code": "MAT-400-I01", "name": "Composite Long Rod Insulator 400kV", "category": "Insulator", "unit": "Nos", "unit_price": 18500.0, "lead_time_days": 21, "min_order_qty": 50},
        {"code": "MAT-400-I02", "name": "Disc Insulator String 400kV", "category": "Insulator", "unit": "Set", "unit_price": 45000.0, "lead_time_days": 21, "min_order_qty": 20},
        {"code": "MAT-400-H01", "name": "Suspension Clamp Assembly 400kV", "category": "Hardware", "unit": "Set", "unit_price": 12500.0, "lead_time_days": 14, "min_order_qty": 20},
        {"code": "MAT-400-H02", "name": "Tension Clamp Assembly 400kV", "category": "Hardware", "unit": "Set", "unit_price": 18500.0, "lead_time_days": 14, "min_order_qty": 20},
        {"code": "MAT-400-CT01", "name": "400kV Current Transformer", "category": "Substation Equipment", "unit": "Nos", "unit_price": 850000.0, "lead_time_days": 60, "min_order_qty": 3},
        {"code": "MAT-400-PT01", "name": "400kV Potential Transformer", "category": "Substation Equipment", "unit": "Nos", "unit_price": 650000.0, "lead_time_days": 60, "min_order_qty": 3},
        {"code": "MAT-400-CB01", "name": "400kV SF6 Circuit Breaker", "category": "Substation Equipment", "unit": "Nos", "unit_price": 2500000.0, "lead_time_days": 90, "min_order_qty": 1},
        {"code": "MAT-400-LA01", "name": "400kV Lightning Arrester", "category": "Substation Equipment", "unit": "Nos", "unit_price": 180000.0, "lead_time_days": 30, "min_order_qty": 6},
    ],
    "220kV": [
        {"code": "MAT-220-T01", "name": "220kV D/C Tower - Type A (Suspension)", "category": "Towers & Structures", "unit": "Nos", "unit_price": 850000.0, "lead_time_days": 35, "min_order_qty": 1},
        {"code": "MAT-220-T02", "name": "220kV D/C Tower - Type B (Tension)", "category": "Towers & Structures", "unit": "Nos", "unit_price": 1150000.0, "lead_time_days": 35, "min_order_qty": 1},
        {"code": "MAT-220-T03", "name": "220kV D/C Tower - Type C (Dead End)", "category": "Towers & Structures", "unit": "Nos", "unit_price": 1350000.0, "lead_time_days": 45, "min_order_qty": 1},
        {"code": "MAT-220-C01", "name": "ACSR Zebra Conductor 220kV", "category": "Conductor", "unit": "km", "unit_price": 95000.0, "lead_time_days": 25, "min_order_qty": 10},
        {"code": "MAT-220-C02", "name": "OPGW Earth Wire 220kV", "category": "Conductor", "unit": "km", "unit_price": 185000.0, "lead_time_days": 35, "min_order_qty": 5},
        {"code": "MAT-220-I01", "name": "Composite Long Rod Insulator 220kV", "category": "Insulator", "unit": "Nos", "unit_price": 12500.0, "lead_time_days": 18, "min_order_qty": 50},
        {"code": "MAT-220-I02", "name": "Disc Insulator String 220kV", "category": "Insulator", "unit": "Set", "unit_price": 32000.0, "lead_time_days": 18, "min_order_qty": 20},
        {"code": "MAT-220-H01", "name": "Suspension Clamp Assembly 220kV", "category": "Hardware", "unit": "Set", "unit_price": 9500.0, "lead_time_days": 12, "min_order_qty": 20},
        {"code": "MAT-220-H02", "name": "Tension Clamp Assembly 220kV", "category": "Hardware", "unit": "Set", "unit_price": 14500.0, "lead_time_days": 12, "min_order_qty": 20},
        {"code": "MAT-220-CT01", "name": "220kV Current Transformer", "category": "Substation Equipment", "unit": "Nos", "unit_price": 550000.0, "lead_time_days": 45, "min_order_qty": 3},
        {"code": "MAT-220-PT01", "name": "220kV Potential Transformer", "category": "Substation Equipment", "unit": "Nos", "unit_price": 420000.0, "lead_time_days": 45, "min_order_qty": 3},
        {"code": "MAT-220-CB01", "name": "220kV SF6 Circuit Breaker", "category": "Substation Equipment", "unit": "Nos", "unit_price": 1800000.0, "lead_time_days": 75, "min_order_qty": 1},
        {"code": "MAT-220-LA01", "name": "220kV Lightning Arrester", "category": "Substation Equipment", "unit": "Nos", "unit_price": 120000.0, "lead_time_days": 25, "min_order_qty": 6},
    ],
    "132kV": [
        {"code": "MAT-132-T01", "name": "132kV D/C Tower - Type A (Suspension)", "category": "Towers & Structures", "unit": "Nos", "unit_price": 550000.0, "lead_time_days": 28, "min_order_qty": 1},
        {"code": "MAT-132-T02", "name": "132kV D/C Tower - Type B (Tension)", "category": "Towers & Structures", "unit": "Nos", "unit_price": 750000.0, "lead_time_days": 28, "min_order_qty": 1},
        {"code": "MAT-132-T03", "name": "132kV S/C Tower - Suspension", "category": "Towers & Structures", "unit": "Nos", "unit_price": 350000.0, "lead_time_days": 25, "min_order_qty": 1},
        {"code": "MAT-132-C01", "name": "ACSR Panther Conductor 132kV", "category": "Conductor", "unit": "km", "unit_price": 72000.0, "lead_time_days": 20, "min_order_qty": 10},
        {"code": "MAT-132-C02", "name": "OPGW Earth Wire 132kV", "category": "Conductor", "unit": "km", "unit_price": 145000.0, "lead_time_days": 30, "min_order_qty": 5},
        {"code": "MAT-132-I01", "name": "Composite Insulator 132kV", "category": "Insulator", "unit": "Nos", "unit_price": 8500.0, "lead_time_days": 14, "min_order_qty": 50},
        {"code": "MAT-132-I02", "name": "Disc Insulator String 132kV", "category": "Insulator", "unit": "Set", "unit_price": 22000.0, "lead_time_days": 14, "min_order_qty": 20},
        {"code": "MAT-132-H01", "name": "Suspension Clamp Assembly 132kV", "category": "Hardware", "unit": "Set", "unit_price": 7500.0, "lead_time_days": 10, "min_order_qty": 25},
        {"code": "MAT-132-H02", "name": "Tension Clamp Assembly 132kV", "category": "Hardware", "unit": "Set", "unit_price": 11500.0, "lead_time_days": 10, "min_order_qty": 25},
        {"code": "MAT-132-CT01", "name": "132kV Current Transformer", "category": "Substation Equipment", "unit": "Nos", "unit_price": 350000.0, "lead_time_days": 35, "min_order_qty": 3},
        {"code": "MAT-132-CB01", "name": "132kV SF6 Circuit Breaker", "category": "Substation Equipment", "unit": "Nos", "unit_price": 1200000.0, "lead_time_days": 60, "min_order_qty": 1},
        {"code": "MAT-132-LA01", "name": "132kV Lightning Arrester", "category": "Substation Equipment", "unit": "Nos", "unit_price": 85000.0, "lead_time_days": 20, "min_order_qty": 6},
    ],
    "33kV": [
        {"code": "MAT-033-T01", "name": "33kV D/C Tower - Steel Lattice", "category": "Towers & Structures", "unit": "Nos", "unit_price": 180000.0, "lead_time_days": 18, "min_order_qty": 5},
        {"code": "MAT-033-T02", "name": "33kV S/C Pole - PCC 11m", "category": "Towers & Structures", "unit": "Nos", "unit_price": 45000.0, "lead_time_days": 10, "min_order_qty": 10},
        {"code": "MAT-033-T03", "name": "33kV S/C Pole - RSJ 13m", "category": "Towers & Structures", "unit": "Nos", "unit_price": 65000.0, "lead_time_days": 12, "min_order_qty": 10},
        {"code": "MAT-033-C01", "name": "ACSR Dog Conductor 33kV", "category": "Conductor", "unit": "km", "unit_price": 42000.0, "lead_time_days": 14, "min_order_qty": 5},
        {"code": "MAT-033-C02", "name": "AAAC Conductor 33kV", "category": "Conductor", "unit": "km", "unit_price": 52000.0, "lead_time_days": 14, "min_order_qty": 5},
        {"code": "MAT-033-I01", "name": "Pin Insulator 33kV", "category": "Insulator", "unit": "Nos", "unit_price": 850.0, "lead_time_days": 7, "min_order_qty": 100},
        {"code": "MAT-033-I02", "name": "Disc Insulator 33kV", "category": "Insulator", "unit": "Nos", "unit_price": 1200.0, "lead_time_days": 7, "min_order_qty": 100},
        {"code": "MAT-033-H01", "name": "Cross Arm Assembly 33kV", "category": "Hardware", "unit": "Set", "unit_price": 3500.0, "lead_time_days": 7, "min_order_qty": 25},
        {"code": "MAT-033-H02", "name": "Stay Set Complete 33kV", "category": "Hardware", "unit": "Set", "unit_price": 4500.0, "lead_time_days": 7, "min_order_qty": 25},
        {"code": "MAT-033-TR01", "name": "33/11kV 5MVA Power Transformer", "category": "Substation Equipment", "unit": "Nos", "unit_price": 3500000.0, "lead_time_days": 90, "min_order_qty": 1},
        {"code": "MAT-033-CB01", "name": "33kV Vacuum Circuit Breaker", "category": "Substation Equipment", "unit": "Nos", "unit_price": 350000.0, "lead_time_days": 30, "min_order_qty": 1},
        {"code": "MAT-033-LA01", "name": "33kV Surge Arrester", "category": "Substation Equipment", "unit": "Nos", "unit_price": 25000.0, "lead_time_days": 14, "min_order_qty": 10},
    ],
    "Common": [
        {"code": "MAT-COM-F01", "name": "Concrete M30 Grade", "category": "Foundation", "unit": "cum", "unit_price": 6500.0, "lead_time_days": 2, "min_order_qty": 50},
        {"code": "MAT-COM-F02", "name": "Reinforcement Steel Fe500D", "category": "Foundation", "unit": "MT", "unit_price": 65000.0, "lead_time_days": 7, "min_order_qty": 10},
        {"code": "MAT-COM-F03", "name": "Foundation Bolts HD", "category": "Foundation", "unit": "Set", "unit_price": 15000.0, "lead_time_days": 10, "min_order_qty": 20},
        {"code": "MAT-COM-S01", "name": "Pilot Wire", "category": "Stringing", "unit": "km", "unit_price": 8500.0, "lead_time_days": 7, "min_order_qty": 10},
        {"code": "MAT-COM-S02", "name": "Running Out Blocks", "category": "Stringing", "unit": "Set", "unit_price": 45000.0, "lead_time_days": 14, "min_order_qty": 5},
        {"code": "MAT-COM-S03", "name": "Spacer Damper", "category": "Hardware", "unit": "Nos", "unit_price": 4500.0, "lead_time_days": 14, "min_order_qty": 100},
        {"code": "MAT-COM-S04", "name": "Vibration Damper", "category": "Hardware", "unit": "Nos", "unit_price": 2800.0, "lead_time_days": 14, "min_order_qty": 100},
        {"code": "MAT-COM-CT01", "name": "Line Protection Panel", "category": "Control System", "unit": "Nos", "unit_price": 2500000.0, "lead_time_days": 60, "min_order_qty": 1},
        {"code": "MAT-COM-CT02", "name": "Control & Relay Panel", "category": "Control System", "unit": "Nos", "unit_price": 1800000.0, "lead_time_days": 45, "min_order_qty": 1},
        {"code": "MAT-COM-CT03", "name": "SCADA RTU", "category": "Control System", "unit": "Nos", "unit_price": 1500000.0, "lead_time_days": 45, "min_order_qty": 1},
    ]
}

# ============================================================================
# SUBSTATIONS AND THEIR VOLTAGE REQUIREMENTS
# ============================================================================

SUBSTATIONS_CONFIG = [
    {
        "code": "KTA-400",
        "name": "Kota 400kV Substation",
        "voltage_levels": ["400kV", "220kV"],
        "has_project": True,
        "stock_multiplier": 1.0,  # Normal stock
    },
    {
        "code": "SRN-220",
        "name": "Srinagar 220kV Substation",
        "voltage_levels": ["220kV", "132kV"],
        "has_project": False,
        "stock_multiplier": 1.5,  # Extra buffer for remote area
    },
    {
        "code": "BLR-220",
        "name": "Bangalore 220kV Substation",
        "voltage_levels": ["220kV", "132kV", "33kV"],
        "has_project": False,
        "stock_multiplier": 0.6,  # Understocked
    },
]

# ============================================================================
# WAREHOUSE MATERIAL ALLOCATION
# ============================================================================

WAREHOUSE_MATERIAL_CONFIG = {
    "WH-BEAWAR": {
        "description": "Project site - LILO materials only",
        "voltage_focus": ["400kV"],
        "stock_level": "project_specific",
        "serves": ["KTA-400"],
    },
    "WH-JAIPUR": {
        "description": "Regional hub - Rajasthan",
        "voltage_focus": ["400kV", "220kV", "132kV"],
        "stock_level": "high",
        "serves": ["KTA-400"],
    },
    "WH-CHENNAI": {
        "description": "South India hub",
        "voltage_focus": ["220kV", "132kV", "33kV"],
        "stock_level": "high",
        "serves": ["BLR-220"],
    },
    "WH-HYDERABAD": {
        "description": "Central/South hub",
        "voltage_focus": ["220kV", "132kV", "33kV"],
        "stock_level": "medium",
        "serves": ["BLR-220"],
    },
    "WH-JAMMU": {
        "description": "J&K staging point",
        "voltage_focus": ["220kV", "132kV"],
        "stock_level": "buffer",
        "serves": ["SRN-220"],
    },
    "WH-MUMBAI": {
        "description": "Import hub - all materials",
        "voltage_focus": ["400kV", "220kV", "132kV", "33kV"],
        "stock_level": "high",
        "serves": [],
    },
    "WH-DELHI": {
        "description": "North India hub",
        "voltage_focus": ["400kV", "220kV", "132kV"],
        "stock_level": "medium",
        "serves": ["SRN-220"],
    },
    "WH-KOLKATA": {
        "description": "East India hub",
        "voltage_focus": ["220kV", "132kV", "33kV"],
        "stock_level": "medium",
        "serves": [],
    },
    "WH-AHMEDABAD": {
        "description": "West India hub",
        "voltage_focus": ["220kV", "132kV", "33kV"],
        "stock_level": "medium",
        "serves": [],
    },
    "WH-NAGPUR": {
        "description": "Central India hub",
        "voltage_focus": ["400kV", "220kV", "132kV"],
        "stock_level": "medium",
        "serves": [],
    },
}

# ============================================================================
# PROJECTS WITH MATERIAL REQUIREMENTS
# ============================================================================

PROJECTS_CONFIG = [
    {
        "code": "PROJ-RAJ-2024-001",
        "name": "LILO of Kota-Merta 400kV D/C at Beawar",
        "substation_code": "KTA-400",
        "voltage_level": 400,
        "line_length_km": 66.0,
        "towers_total": 90,
        "towers_erected": 78,
        "target_date": "2026-01-31",
        "status": "In Progress",
        "progress": 73.87,
        "materials_required": [
            {"code": "MAT-400-T01", "required": 54, "consumed": 45, "on_order": 6},
            {"code": "MAT-400-T02", "required": 24, "consumed": 18, "on_order": 4},
            {"code": "MAT-400-T03", "required": 12, "consumed": 6, "on_order": 4},
            {"code": "MAT-400-C01", "required": 396, "consumed": 156, "on_order": 80},
            {"code": "MAT-400-C02", "required": 66, "consumed": 26, "on_order": 26},
            {"code": "MAT-400-I01", "required": 1620, "consumed": 1200, "on_order": 220},
            {"code": "MAT-400-H01", "required": 540, "consumed": 320, "on_order": 100},
            {"code": "MAT-400-H02", "required": 288, "consumed": 150, "on_order": 80},
            {"code": "MAT-COM-F01", "required": 4500, "consumed": 4300, "on_order": 0},
            {"code": "MAT-COM-F02", "required": 850, "consumed": 810, "on_order": 50},
            {"code": "MAT-COM-CT01", "required": 4, "consumed": 0, "on_order": 2},
            {"code": "MAT-COM-CT02", "required": 4, "consumed": 0, "on_order": 2},
        ]
    },
    {
        "code": "PROJ-KAR-2024-002",
        "name": "Bangalore 220kV Substation Augmentation",
        "substation_code": "BLR-220",
        "voltage_level": 220,
        "line_length_km": 45.0,
        "towers_total": 60,
        "towers_erected": 15,
        "target_date": "2025-06-30",
        "status": "In Progress",
        "progress": 25.0,
        "materials_required": [
            {"code": "MAT-220-T01", "required": 40, "consumed": 10, "on_order": 10},
            {"code": "MAT-220-T02", "required": 15, "consumed": 3, "on_order": 5},
            {"code": "MAT-220-T03", "required": 5, "consumed": 2, "on_order": 0},
            {"code": "MAT-220-C01", "required": 270, "consumed": 45, "on_order": 50},
            {"code": "MAT-220-I01", "required": 960, "consumed": 150, "on_order": 200},
            {"code": "MAT-220-H01", "required": 360, "consumed": 30, "on_order": 80},
            {"code": "MAT-220-CB01", "required": 4, "consumed": 0, "on_order": 2},
        ]
    },
    {
        "code": "PROJ-JK-2024-003",
        "name": "Srinagar 220kV Line Extension",
        "substation_code": "SRN-220",
        "voltage_level": 220,
        "line_length_km": 35.0,
        "towers_total": 48,
        "towers_erected": 0,
        "target_date": "2025-09-30",
        "status": "Planning",
        "progress": 5.0,
        "materials_required": [
            {"code": "MAT-220-T01", "required": 32, "consumed": 0, "on_order": 0},
            {"code": "MAT-220-T02", "required": 12, "consumed": 0, "on_order": 0},
            {"code": "MAT-220-T03", "required": 4, "consumed": 0, "on_order": 0},
            {"code": "MAT-220-C01", "required": 210, "consumed": 0, "on_order": 0},
            {"code": "MAT-220-I01", "required": 768, "consumed": 0, "on_order": 0},
        ]
    },
]

# ============================================================================
# TRANSACTION HISTORY (Past 3 months)
# ============================================================================

TRANSACTION_TYPES = ["IN", "OUT", "TRANSFER_IN", "TRANSFER_OUT", "ADJUSTMENT"]

def generate_transactions(materials, warehouse_codes, start_date, num_transactions=200):
    """Generate realistic transaction history"""
    transactions = []
    
    for i in range(num_transactions):
        days_ago = random.randint(0, 90)
        trans_date = start_date - timedelta(days=days_ago)
        
        material = random.choice(materials)
        warehouse_code = random.choice(warehouse_codes)
        trans_type = random.choice(TRANSACTION_TYPES)
        
        if trans_type == "IN":
            quantity = random.randint(10, 500)
            reference_type = "PO"
        elif trans_type == "OUT":
            quantity = random.randint(5, 100)
            reference_type = "PROJECT"
        elif trans_type in ["TRANSFER_IN", "TRANSFER_OUT"]:
            quantity = random.randint(20, 200)
            reference_type = "TO"
        else:
            quantity = random.randint(-50, 50)
            reference_type = "ADJUSTMENT"
        
        transactions.append({
            "transaction_type": trans_type,
            "warehouse_code": warehouse_code,
            "material_code": material["code"],
            "quantity": quantity,
            "unit_cost": material["unit_price"],
            "total_cost": quantity * material["unit_price"],
            "reference_type": reference_type,
            "reference_id": f"{reference_type}-{trans_date.strftime('%Y%m%d')}-{i:04d}",
            "transaction_date": trans_date,
            "notes": f"Auto-generated transaction for testing"
        })
    
    return transactions

# ============================================================================
# FUTURE PROCUREMENTS (Next 6 months)
# ============================================================================

def generate_future_procurements(projects, materials):
    """Generate planned procurement orders based on project needs"""
    procurements = []
    base_date = datetime.now()
    
    for project in projects:
        for mat_req in project.get("materials_required", []):
            required = mat_req["required"]
            consumed = mat_req["consumed"]
            on_order = mat_req["on_order"]
            shortage = required - consumed - on_order
            
            if shortage > 0:
                # Find material details
                mat_code = mat_req["code"]
                material = None
                for voltage, mats in MATERIALS_BY_VOLTAGE.items():
                    for m in mats:
                        if m["code"] == mat_code:
                            material = m
                            break
                
                if material:
                    lead_time = material.get("lead_time_days", 30)
                    order_date = base_date + timedelta(days=random.randint(1, 30))
                    expected_delivery = order_date + timedelta(days=lead_time)
                    
                    # Determine urgency
                    target_date = datetime.strptime(project["target_date"], "%Y-%m-%d")
                    days_to_target = (target_date - expected_delivery).days
                    
                    if days_to_target < 30:
                        priority = "CRITICAL"
                        alert_level = 2  # WhatsApp
                    elif days_to_target < 60:
                        priority = "HIGH"
                        alert_level = 1  # Email only
                    else:
                        priority = "NORMAL"
                        alert_level = 0  # No alert
                    
                    procurements.append({
                        "project_code": project["code"],
                        "project_name": project["name"],
                        "material_code": mat_code,
                        "material_name": material["name"],
                        "quantity_required": shortage,
                        "unit_price": material["unit_price"],
                        "total_value": shortage * material["unit_price"],
                        "order_date": order_date,
                        "expected_delivery": expected_delivery,
                        "target_date": target_date,
                        "days_to_target": days_to_target,
                        "priority": priority,
                        "alert_level": alert_level,
                        "status": "Planned"
                    })
    
    return procurements

# ============================================================================
# ALERTS CONFIGURATION
# ============================================================================

ALERT_TEMPLATES = [
    {
        "type": "STOCK_LOW",
        "level": 1,
        "title_template": "Low Stock Alert: {material_name}",
        "message_template": "Stock for {material_name} at {warehouse} is below reorder point. Current: {current}, Reorder Point: {reorder_point}"
    },
    {
        "type": "STOCK_CRITICAL",
        "level": 2,
        "title_template": "CRITICAL: {material_name} Stock Depleted",
        "message_template": "URGENT: {material_name} at {warehouse} has reached critical level. Current: {current}, Required for project: {required}"
    },
    {
        "type": "PROCUREMENT_DELAYED",
        "level": 1,
        "title_template": "Procurement Delay: {material_name}",
        "message_template": "PO {po_number} for {material_name} is delayed by {delay_days} days. New ETA: {new_eta}"
    },
    {
        "type": "PROJECT_AT_RISK",
        "level": 2,
        "title_template": "PROJECT AT RISK: {project_name}",
        "message_template": "Project {project_code} timeline at risk due to material shortage. Shortfall: {shortfall_count} materials"
    },
]


# ============================================================================
# MAIN SEEDING FUNCTION
# ============================================================================

def seed_enhanced_data():
    """Seed the database with comprehensive test data"""
    
    # Database connection
    db_path = Path(__file__).parent.parent / "data" / "nexus.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("🚀 Starting enhanced data seeding...")
    
    try:
        # 1. Seed all voltage-specific materials
        print("\n📦 Seeding voltage-specific materials...")
        material_map = {}
        
        for voltage, materials in MATERIALS_BY_VOLTAGE.items():
            for mat_data in materials:
                # Check by code first
                existing = session.query(Material).filter_by(material_code=mat_data["code"]).first()
                if not existing:
                    # Also check by name to avoid unique constraint
                    existing_by_name = session.query(Material).filter_by(name=mat_data["name"]).first()
                    if existing_by_name:
                        # Use existing material by name
                        material_map[mat_data["code"]] = existing_by_name.id
                        print(f"   ⚡ Mapped existing: {mat_data['code']} -> {existing_by_name.material_code}")
                        continue
                    
                    material = Material(
                        material_code=mat_data["code"],
                        name=mat_data["name"],
                        category=mat_data["category"],
                        unit=mat_data["unit"],
                        unit_price=mat_data["unit_price"],
                        lead_time_days=mat_data["lead_time_days"],
                        min_order_quantity=mat_data["min_order_qty"],
                        safety_stock_days=30,
                        description=f"{voltage} material for transmission projects"
                    )
                    session.add(material)
                    session.flush()
                    material_map[mat_data["code"]] = material.id
                    print(f"   ✅ Added: {mat_data['code']} - {mat_data['name']}")
                else:
                    material_map[mat_data["code"]] = existing.id
        
        session.commit()
        
        # 2. Create project-specific inventory
        print("\n🏭 Seeding warehouse inventory by voltage...")
        
        warehouses = session.query(Warehouse).all()
        warehouse_map = {w.warehouse_code: w for w in warehouses}
        
        for wh_code, config in WAREHOUSE_MATERIAL_CONFIG.items():
            wh = warehouse_map.get(wh_code)
            if not wh:
                continue
                
            voltage_focus = config.get("voltage_focus", [])
            stock_level = config.get("stock_level", "medium")
            
            # Stock multipliers
            multipliers = {
                "high": (100, 500),
                "medium": (50, 200),
                "buffer": (150, 400),
                "project_specific": (20, 100),
            }
            
            min_qty, max_qty = multipliers.get(stock_level, (50, 200))
            
            for voltage in voltage_focus:
                materials = MATERIALS_BY_VOLTAGE.get(voltage, [])
                for mat in materials:
                    mat_id = material_map.get(mat["code"])
                    if not mat_id:
                        continue
                    
                    # Check if inventory entry exists
                    existing_stock = session.query(InventoryStock).filter_by(
                        warehouse_id=wh.id,
                        material_id=mat_id
                    ).first()
                    
                    if not existing_stock:
                        qty = random.randint(min_qty, max_qty)
                        reorder = int(qty * 0.3)
                        max_stock = int(qty * 2.5)
                        
                        inventory = InventoryStock(
                            warehouse_id=wh.id,
                            material_id=mat_id,
                            quantity_available=qty,
                            quantity_reserved=random.randint(0, int(qty * 0.2)),
                            quantity_in_transit=random.randint(0, int(qty * 0.1)),
                            reorder_point=reorder,
                            max_stock_level=max_stock,
                            min_stock_level=int(reorder * 0.5),
                            last_restocked_date=datetime.now() - timedelta(days=random.randint(1, 30))
                        )
                        session.add(inventory)
            
            # Add common materials to all warehouses
            for mat in MATERIALS_BY_VOLTAGE.get("Common", []):
                mat_id = material_map.get(mat["code"])
                if not mat_id:
                    continue
                
                existing_stock = session.query(InventoryStock).filter_by(
                    warehouse_id=wh.id,
                    material_id=mat_id
                ).first()
                
                if not existing_stock:
                    qty = random.randint(min_qty * 2, max_qty * 2)
                    inventory = InventoryStock(
                        warehouse_id=wh.id,
                        material_id=mat_id,
                        quantity_available=qty,
                        quantity_reserved=0,
                        quantity_in_transit=0,
                        reorder_point=int(qty * 0.3),
                        max_stock_level=int(qty * 2),
                        min_stock_level=int(qty * 0.15),
                        last_restocked_date=datetime.now() - timedelta(days=random.randint(1, 30))
                    )
                    session.add(inventory)
            
            print(f"   ✅ Populated inventory for {wh_code}")
        
        session.commit()
        
        # 3. Generate transaction history
        print("\n📊 Generating transaction history...")
        all_materials = []
        for voltage, mats in MATERIALS_BY_VOLTAGE.items():
            all_materials.extend(mats)
        
        transactions = generate_transactions(
            all_materials, 
            list(WAREHOUSE_MATERIAL_CONFIG.keys()),
            datetime.now(),
            num_transactions=300
        )
        
        # We'll add these to a log file for now since InventoryTransaction might not have all fields
        trans_log_path = Path(__file__).parent.parent / "data" / "outputs" / "transaction_history.json"
        trans_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(trans_log_path, 'w') as f:
            json.dump([{
                **t,
                "transaction_date": t["transaction_date"].isoformat()
            } for t in transactions], f, indent=2)
        
        print(f"   ✅ Generated {len(transactions)} transactions → {trans_log_path}")
        
        # 4. Generate future procurements
        print("\n📋 Generating future procurement plans...")
        procurements = generate_future_procurements(PROJECTS_CONFIG, all_materials)
        
        proc_log_path = Path(__file__).parent.parent / "data" / "outputs" / "future_procurements.json"
        
        with open(proc_log_path, 'w') as f:
            json.dump([{
                **p,
                "order_date": p["order_date"].isoformat(),
                "expected_delivery": p["expected_delivery"].isoformat(),
                "target_date": p["target_date"].isoformat()
            } for p in procurements], f, indent=2)
        
        # Count alerts needed
        critical_alerts = [p for p in procurements if p["priority"] == "CRITICAL"]
        high_alerts = [p for p in procurements if p["priority"] == "HIGH"]
        
        print(f"   ✅ Generated {len(procurements)} procurement plans → {proc_log_path}")
        print(f"   🚨 CRITICAL (WhatsApp alert): {len(critical_alerts)}")
        print(f"   ⚠️  HIGH (Email alert): {len(high_alerts)}")
        
        # 5. Create additional projects
        print("\n🏗️ Updating project material needs...")
        
        for proj_config in PROJECTS_CONFIG:
            # Find or create project
            project = session.query(SubstationProject).filter_by(
                project_code=proj_config["code"]
            ).first()
            
            if project:
                # Update material needs
                for mat_req in proj_config.get("materials_required", []):
                    mat_id = material_map.get(mat_req["code"])
                    if not mat_id:
                        continue
                    
                    # Find material for name
                    material = session.query(Material).get(mat_id)
                    
                    existing_need = session.query(ProjectMaterialNeed).filter_by(
                        project_id=project.id,
                        material_id=mat_id
                    ).first()
                    
                    required = mat_req["required"]
                    consumed = mat_req["consumed"]
                    on_order = mat_req.get("on_order", 0)
                    available = required - consumed - on_order
                    shortage = max(0, required - consumed - on_order)
                    
                    if not existing_need:
                        need = ProjectMaterialNeed(
                            project_id=project.id,
                            material_id=mat_id,
                            material_name=material.name if material else mat_req["code"],
                            quantity_needed=required,
                            quantity_available=available,
                            quantity_shortage=shortage,
                            unit=material.unit if material else "Nos",
                            unit_price=material.unit_price if material else 0,
                            total_value=shortage * (material.unit_price if material else 0),
                            priority="High" if shortage > 0 else "Normal",
                            status="Pending" if shortage > 0 else "Adequate"
                        )
                        session.add(need)
                
                print(f"   ✅ Updated material needs for {proj_config['code']}")
        
        session.commit()
        
        print("\n" + "="*60)
        print("✅ Enhanced data seeding completed successfully!")
        print("="*60)
        
        # Summary
        print("\n📊 Data Summary:")
        print(f"   Materials: {len(material_map)}")
        print(f"   Inventory Entries: {session.query(InventoryStock).count()}")
        print(f"   Transactions: {len(transactions)}")
        print(f"   Future Procurements: {len(procurements)}")
        print(f"   Alerts Required: {len(critical_alerts) + len(high_alerts)}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error during seeding: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_enhanced_data()
