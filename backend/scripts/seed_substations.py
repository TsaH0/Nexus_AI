"""
NEXUS Seed Script - Substations, Warehouses, Projects & Transactions
======================================================================

This script seeds the database with:
1. SUBSTATIONS - Power infrastructure being built (Kota, Srinagar, Bangalore)
2. WAREHOUSES - Storage facilities for raw materials (separate from substations)
3. PROJECTS - Construction projects at substations (LILO project at Kota)
4. MATERIALS - Detailed BOQ items for transmission projects
5. INVENTORY - Stock levels at each warehouse
6. TRANSACTIONS - Material movements between warehouses and project sites

Key Distinction:
- Substations = Where power infrastructure is being built
- Warehouses = Where materials are stored (can be near substations or regional hubs)
"""

import random
import json
from datetime import datetime, timedelta
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker

# Import models
from src.api.db_models import (
    Base, Material, Location, Warehouse, InventoryStock,
    Substation, SubstationProject, SubstationCriticalMaterial,
    ProjectMaterialNeed, MaterialTransfer, PurchaseOrder, Vendor,
    ProjectIssue, OrderTracking
)


# ============================================================================
# SUBSTATIONS DATA (Only 3 - Kota, Srinagar, Bangalore)
# ============================================================================

SUBSTATIONS_DATA = [
    {
        "code": "KTA-400",
        "name": "Kota 400kV Substation",
        "type": "EHV",
        "capacity": "400kV",
        "state": "Rajasthan",
        "city": "Kota",
        "lat": 25.1800,
        "lng": 75.8648,
        "stock_status": "Normal",
        "stock_level": 87.5,
        "has_project": True,
        "description": "Major 400kV substation in Rajasthan, hub for LILO project"
    },
    {
        "code": "SRN-220",
        "name": "Srinagar 220kV Substation",
        "type": "EHV",
        "capacity": "220kV",
        "state": "Jammu & Kashmir",
        "city": "Srinagar",
        "lat": 34.0837,
        "lng": 74.7973,
        "stock_status": "Overstocked",
        "stock_level": 145.0,
        "has_project": False,
        "description": "Strategic buffer stock for J&K region - road blockage prone area"
    },
    {
        "code": "BLR-220",
        "name": "Bangalore 220kV Substation",
        "type": "EHV",
        "capacity": "220kV",
        "state": "Karnataka",
        "city": "Bangalore",
        "lat": 12.9716,
        "lng": 77.5946,
        "stock_status": "Understocked",
        "stock_level": 35.0,
        "has_project": False,
        "description": "Understocked - needs material replenishment from nearby hubs"
    }
]


# ============================================================================
# WAREHOUSES DATA (Separate from Substations - Regional Hubs)
# ============================================================================

WAREHOUSES_DATA = [
    # Main warehouse for Kota LILO project
    {
        "code": "WH-BEAWAR",
        "name": "Beawar Yard (Project Site)",
        "state": "Rajasthan",
        "city": "Beawar",
        "lat": 26.1011,
        "lng": 74.3200,
        "capacity_tons": 15000,
        "is_project_site": True,
        "description": "Main project yard for LILO of Kota-Merta 400kV at Beawar"
    },
    # Regional hub warehouses
    {
        "code": "WH-JAIPUR",
        "name": "Jaipur Central Warehouse",
        "state": "Rajasthan",
        "city": "Jaipur",
        "lat": 26.9124,
        "lng": 75.7873,
        "capacity_tons": 25000,
        "is_project_site": False,
        "description": "Regional hub for Rajasthan - supplies to Beawar project"
    },
    {
        "code": "WH-CHENNAI",
        "name": "Chennai Regional Hub",
        "state": "Tamil Nadu",
        "city": "Chennai",
        "lat": 13.0827,
        "lng": 80.2707,
        "capacity_tons": 30000,
        "is_project_site": False,
        "description": "Major South India hub - supplies to Bangalore"
    },
    {
        "code": "WH-HYDERABAD",
        "name": "Hyderabad Central Warehouse",
        "state": "Telangana",
        "city": "Hyderabad",
        "lat": 17.3850,
        "lng": 78.4867,
        "capacity_tons": 28000,
        "is_project_site": False,
        "description": "Central India hub - supplies to South and West"
    },
    {
        "code": "WH-JAMMU",
        "name": "Jammu Staging Warehouse",
        "state": "Jammu & Kashmir",
        "city": "Jammu",
        "lat": 32.7266,
        "lng": 74.8570,
        "capacity_tons": 10000,
        "is_project_site": False,
        "description": "Strategic staging point for J&K - buffer stock for Srinagar"
    },
    {
        "code": "WH-MUMBAI",
        "name": "Mumbai Port Warehouse",
        "state": "Maharashtra",
        "city": "Mumbai",
        "lat": 19.0760,
        "lng": 72.8777,
        "capacity_tons": 40000,
        "is_project_site": False,
        "description": "Major import hub - receives international shipments"
    },
    {
        "code": "WH-KOLKATA",
        "name": "Kolkata Eastern Hub",
        "state": "West Bengal",
        "city": "Kolkata",
        "lat": 22.5726,
        "lng": 88.3639,
        "capacity_tons": 32000,
        "is_project_site": False,
        "description": "Eastern India distribution center"
    },
    {
        "code": "WH-DELHI",
        "name": "Delhi NCR Warehouse",
        "state": "Delhi",
        "city": "New Delhi",
        "lat": 28.6139,
        "lng": 77.2090,
        "capacity_tons": 35000,
        "is_project_site": False,
        "description": "National capital region hub - supplies to North India"
    },
    {
        "code": "WH-AHMEDABAD",
        "name": "Ahmedabad Distribution Center",
        "state": "Gujarat",
        "city": "Ahmedabad",
        "lat": 23.0225,
        "lng": 72.5714,
        "capacity_tons": 28000,
        "is_project_site": False,
        "description": "Gujarat hub - Western India distribution"
    },
    {
        "code": "WH-NAGPUR",
        "name": "Nagpur Central Hub",
        "state": "Maharashtra",
        "city": "Nagpur",
        "lat": 21.1458,
        "lng": 79.0882,
        "capacity_tons": 22000,
        "is_project_site": False,
        "description": "Central India hub - strategic location for all-India distribution"
    }
]


# ============================================================================
# LILO PROJECT DATA (Detailed as per specifications)
# ============================================================================

LILO_PROJECT = {
    "project_code": "PROJ-RAJ-2024-001",
    "name": "LILO of Kota-Merta 400kV D/C at Beawar",
    "description": "LILO of Kota – Merta 400 kV D/c at Beawar (Transmission System for Evacuation of Power from REZ in Rajasthan (20GW) under Phase-III Part F)",
    "developer": "Sterlite Power",
    "developer_type": "Private Developer",
    "category": "ISTS",
    "project_type": "LILO",
    "circuit_type": "D/C",
    "voltage_level": 400,
    "total_line_length": 66.0,
    "total_tower_locations": 90,
    "target_date": datetime(2026, 1, 31),
    "anticipated_cod": datetime(2026, 3, 31),
    "delay_days": 60,
    "foundation_completed": 86,
    "foundation_total": 90,
    "tower_erected": 78,
    "tower_total": 90,
    "stringing_completed_ckm": 26.0,
    "stringing_total_ckm": 66.0,
    "overall_progress": 73.87,
    "status": "In Progress",
    "budget_sanctioned": 320000000.0,
    "budget_spent": 245000000.0,
}

DELAY_REASONS = [
    {
        "category": "Regulatory",
        "description": "PLC Approval pending with M/s Shree Cement",
        "duration": "10+ months",
        "impact": "Critical",
        "status": "Pending",
        "responsible_party": "M/s Shree Cement / Regulatory Authority",
        "affected_towers": [85, 86, 87, 88],
        "mitigation_plan": "Escalation to Ministry level"
    },
    {
        "category": "Technical Dependency",
        "description": "Delay in replacement of existing earth wire with OPGW in Kota-Merta TL by PGCIL",
        "duration": "3 months",
        "impact": "High",
        "status": "In Progress",
        "responsible_party": "PGCIL",
        "affected_towers": [1, 2, 3, 4, 5],
        "mitigation_plan": "Weekly coordination meetings with PGCIL"
    }
]


# ============================================================================
# MATERIALS DATA (Detailed BOQ for LILO Project)
# ============================================================================

MATERIALS_DATA = [
    {"code": "MAT-001", "name": "400kV D/C Tower - Type A (Suspension)", "category": "Towers & Structures", "unit": "Nos", "unit_price": 1250000.0, "lead_time_days": 45, "min_order_qty": 1, "vendor": "Kalpataru Power"},
    {"code": "MAT-002", "name": "400kV D/C Tower - Type B (Tension)", "category": "Towers & Structures", "unit": "Nos", "unit_price": 1650000.0, "lead_time_days": 45, "min_order_qty": 1, "vendor": "Kalpataru Power"},
    {"code": "MAT-003", "name": "400kV D/C Tower - Type C (Dead End)", "category": "Towers & Structures", "unit": "Nos", "unit_price": 1850000.0, "lead_time_days": 60, "min_order_qty": 1, "vendor": "Kalpataru Power"},
    {"code": "MAT-004", "name": "ACSR Moose Conductor", "category": "Conductor", "unit": "km", "unit_price": 125000.0, "lead_time_days": 30, "min_order_qty": 10, "vendor": "Apar Industries"},
    {"code": "MAT-005", "name": "OPGW Earth Wire", "category": "Conductor", "unit": "km", "unit_price": 235000.0, "lead_time_days": 45, "min_order_qty": 5, "vendor": "Sterlite Tech"},
    {"code": "MAT-006", "name": "Composite Long Rod Insulator 400kV", "category": "Insulator", "unit": "Nos", "unit_price": 18500.0, "lead_time_days": 21, "min_order_qty": 50, "vendor": "NGK Insulators"},
    {"code": "MAT-007", "name": "Suspension Clamp Assembly", "category": "Hardware", "unit": "Set", "unit_price": 12500.0, "lead_time_days": 14, "min_order_qty": 20, "vendor": "Sicame India"},
    {"code": "MAT-008", "name": "Tension Clamp Assembly", "category": "Hardware", "unit": "Set", "unit_price": 18500.0, "lead_time_days": 14, "min_order_qty": 20, "vendor": "Sicame India"},
    {"code": "MAT-009", "name": "Spacer Damper", "category": "Hardware", "unit": "Nos", "unit_price": 4500.0, "lead_time_days": 14, "min_order_qty": 100, "vendor": "Sicame India"},
    {"code": "MAT-010", "name": "Vibration Damper", "category": "Hardware", "unit": "Nos", "unit_price": 2800.0, "lead_time_days": 14, "min_order_qty": 100, "vendor": "Sicame India"},
    {"code": "MAT-011", "name": "Concrete (M30 Grade)", "category": "Foundation", "unit": "cum", "unit_price": 6500.0, "lead_time_days": 2, "min_order_qty": 50, "vendor": "UltraTech Cement"},
    {"code": "MAT-012", "name": "Reinforcement Steel (Fe500D)", "category": "Foundation", "unit": "MT", "unit_price": 65000.0, "lead_time_days": 7, "min_order_qty": 10, "vendor": "Tata Steel"},
    {"code": "MAT-013", "name": "Foundation Bolts (HD)", "category": "Foundation", "unit": "Set", "unit_price": 15000.0, "lead_time_days": 10, "min_order_qty": 20, "vendor": "Tata Steel"},
    {"code": "MAT-014", "name": "Pilot Wire", "category": "Stringing", "unit": "km", "unit_price": 8500.0, "lead_time_days": 7, "min_order_qty": 10, "vendor": "Apar Industries"},
    {"code": "MAT-015", "name": "Running Out Blocks", "category": "Stringing", "unit": "Set", "unit_price": 45000.0, "lead_time_days": 14, "min_order_qty": 5, "vendor": "Sicame India"},
    {"code": "MAT-016", "name": "Line Protection Panel", "category": "Control System", "unit": "Nos", "unit_price": 2500000.0, "lead_time_days": 60, "min_order_qty": 1, "vendor": "ABB India"},
    {"code": "MAT-017", "name": "Control & Relay Panel", "category": "Control System", "unit": "Nos", "unit_price": 1800000.0, "lead_time_days": 45, "min_order_qty": 1, "vendor": "Siemens India"},
]

PROJECT_MATERIAL_REQUIREMENTS = [
    {"material_code": "MAT-001", "required": 54, "available": 48, "consumed": 45, "on_order": 6, "status": "Adequate"},
    {"material_code": "MAT-002", "required": 24, "available": 20, "consumed": 18, "on_order": 4, "status": "Adequate"},
    {"material_code": "MAT-003", "required": 12, "available": 8, "consumed": 6, "on_order": 4, "status": "Low Stock"},
    {"material_code": "MAT-004", "required": 396, "available": 280, "consumed": 156, "on_order": 80, "status": "On Order"},
    {"material_code": "MAT-005", "required": 66, "available": 40, "consumed": 26, "on_order": 26, "status": "On Order"},
    {"material_code": "MAT-006", "required": 1620, "available": 1400, "consumed": 1200, "on_order": 220, "status": "Adequate"},
    {"material_code": "MAT-007", "required": 540, "available": 380, "consumed": 320, "on_order": 100, "status": "Adequate"},
    {"material_code": "MAT-008", "required": 288, "available": 180, "consumed": 150, "on_order": 80, "status": "Low Stock"},
    {"material_code": "MAT-009", "required": 1080, "available": 900, "consumed": 780, "on_order": 150, "status": "Adequate"},
    {"material_code": "MAT-010", "required": 720, "available": 650, "consumed": 540, "on_order": 70, "status": "Adequate"},
    {"material_code": "MAT-011", "required": 4500, "available": 800, "consumed": 4300, "on_order": 0, "status": "Adequate"},
    {"material_code": "MAT-012", "required": 850, "available": 120, "consumed": 810, "on_order": 50, "status": "Adequate"},
    {"material_code": "MAT-013", "required": 90, "available": 86, "consumed": 86, "on_order": 4, "status": "Adequate"},
    {"material_code": "MAT-014", "required": 132, "available": 100, "consumed": 52, "on_order": 30, "status": "Adequate"},
    {"material_code": "MAT-015", "required": 24, "available": 24, "consumed": 12, "on_order": 0, "status": "Adequate"},
    {"material_code": "MAT-016", "required": 4, "available": 2, "consumed": 0, "on_order": 2, "status": "On Order"},
    {"material_code": "MAT-017", "required": 4, "available": 2, "consumed": 0, "on_order": 2, "status": "On Order"},
]

CRITICAL_ALERTS = [
    {"material_code": "MAT-003", "alert_type": "Low Stock", "current_stock": 8, "required": 12, "shortfall": 4, "expected_delivery": "2025-01-15", "priority": "High"},
    {"material_code": "MAT-008", "alert_type": "Low Stock", "current_stock": 180, "required": 288, "shortfall": 108, "expected_delivery": "2024-12-28", "priority": "Medium"},
]


# ============================================================================
# MATERIAL TRANSFERS (Warehouse → Substation)
# ============================================================================

MATERIAL_TRANSFERS_DATA = [
    # Beawar Yard → Kota Substation (LILO Project)
    {"from_warehouse": "WH-BEAWAR", "to_substation": "KTA-400", "material_code": "MAT-004", "quantity": 120, "status": "Delivered", "dispatch_date": "2024-11-15", "expected_delivery": "2024-11-16", "actual_delivery": "2024-11-16", "po_number": "TRF-2024-0101"},
    {"from_warehouse": "WH-BEAWAR", "to_substation": "KTA-400", "material_code": "MAT-001", "quantity": 30, "status": "Delivered", "dispatch_date": "2024-11-20", "expected_delivery": "2024-11-21", "actual_delivery": "2024-11-21", "po_number": "TRF-2024-0102"},
    {"from_warehouse": "WH-BEAWAR", "to_substation": "KTA-400", "material_code": "MAT-003", "quantity": 8, "status": "In Transit", "dispatch_date": "2024-12-08", "expected_delivery": "2024-12-09", "po_number": "TRF-2024-0103"},
    # Jaipur Hub → Kota (supplementary)
    {"from_warehouse": "WH-JAIPUR", "to_substation": "KTA-400", "material_code": "MAT-005", "quantity": 50, "status": "In Transit", "dispatch_date": "2024-12-07", "expected_delivery": "2024-12-09", "po_number": "TRF-2024-0104"},
    {"from_warehouse": "WH-JAIPUR", "to_substation": "KTA-400", "material_code": "MAT-008", "quantity": 80, "status": "Planned", "dispatch_date": "2024-12-15", "expected_delivery": "2024-12-17", "po_number": "TRF-2024-0105"},
    # Chennai → Bangalore Substation
    {"from_warehouse": "WH-CHENNAI", "to_substation": "BLR-220", "material_code": "MAT-004", "quantity": 60, "status": "Delivered", "dispatch_date": "2024-12-01", "expected_delivery": "2024-12-02", "actual_delivery": "2024-12-02", "po_number": "TRF-2024-0201"},
    {"from_warehouse": "WH-CHENNAI", "to_substation": "BLR-220", "material_code": "MAT-006", "quantity": 100, "status": "In Transit", "dispatch_date": "2024-12-08", "expected_delivery": "2024-12-09", "po_number": "TRF-2024-0202"},
    # Hyderabad → Bangalore (supporting Bangalore expansion)
    {"from_warehouse": "WH-HYDERABAD", "to_substation": "BLR-220", "material_code": "MAT-001", "quantity": 15, "status": "Planned", "dispatch_date": "2024-12-12", "expected_delivery": "2024-12-14", "po_number": "TRF-2024-0203"},
    # Delhi → Srinagar (buffer stock replenishment - short distance compliant)
    {"from_warehouse": "WH-JAMMU", "to_substation": "SRN-220", "material_code": "MAT-009", "quantity": 50, "status": "Delivered", "dispatch_date": "2024-11-01", "expected_delivery": "2024-11-05", "actual_delivery": "2024-11-04", "po_number": "TRF-2024-0301"},
]


# ============================================================================
# VENDORS DATA
# ============================================================================

VENDORS_DATA = [
    {"code": "VEN-001", "name": "Kalpataru Power Transmission", "state": "Gujarat", "city": "Gandhinagar", "lat": 23.2156, "lng": 72.6369, "reliability": 0.95, "lead_time": 30},
    {"code": "VEN-002", "name": "Apar Industries Ltd", "state": "Gujarat", "city": "Ahmedabad", "lat": 23.0225, "lng": 72.5714, "reliability": 0.92, "lead_time": 21},
    {"code": "VEN-003", "name": "Sterlite Technologies", "state": "Maharashtra", "city": "Pune", "lat": 18.5204, "lng": 73.8567, "reliability": 0.88, "lead_time": 45},
    {"code": "VEN-004", "name": "NGK Insulators India", "state": "Maharashtra", "city": "Mumbai", "lat": 19.0760, "lng": 72.8777, "reliability": 0.96, "lead_time": 21},
    {"code": "VEN-005", "name": "Sicame India Pvt Ltd", "state": "Tamil Nadu", "city": "Chennai", "lat": 13.0827, "lng": 80.2707, "reliability": 0.90, "lead_time": 14},
    {"code": "VEN-006", "name": "ABB India Ltd", "state": "Karnataka", "city": "Bangalore", "lat": 12.9716, "lng": 77.5946, "reliability": 0.97, "lead_time": 60},
    {"code": "VEN-007", "name": "Siemens India", "state": "Maharashtra", "city": "Mumbai", "lat": 19.0760, "lng": 72.8777, "reliability": 0.95, "lead_time": 45},
    {"code": "VEN-008", "name": "Tata Steel BSL", "state": "Jharkhand", "city": "Jamshedpur", "lat": 22.8046, "lng": 86.2029, "reliability": 0.94, "lead_time": 7},
]


# ============================================================================
# PURCHASE ORDERS DATA (Orders In-Transit, Manufacturing, etc.)
# ============================================================================

PURCHASE_ORDERS_DATA = [
    # Orders in various stages for LILO project
    {"code": "PO-2024-STL-0048", "vendor_code": "VEN-002", "warehouse_code": "WH-BEAWAR", "material_code": "MAT-004", "quantity": 80, "unit_price": 125000, "status": "In_Transit", "order_date": "2024-12-01", "expected_delivery": "2024-12-10"},
    {"code": "PO-2024-STL-0045", "vendor_code": "VEN-001", "warehouse_code": "WH-JAIPUR", "material_code": "MAT-003", "quantity": 4, "unit_price": 850000, "status": "Manufacturing", "order_date": "2024-11-15", "expected_delivery": "2025-01-15"},
    {"code": "PO-2024-STL-0051", "vendor_code": "VEN-003", "warehouse_code": "WH-BEAWAR", "material_code": "MAT-005", "quantity": 26, "unit_price": 235000, "status": "Manufacturing", "order_date": "2024-11-20", "expected_delivery": "2025-01-10"},
    {"code": "PO-2024-STL-0052", "vendor_code": "VEN-005", "warehouse_code": "WH-JAIPUR", "material_code": "MAT-008", "quantity": 80, "unit_price": 18500, "status": "Placed", "order_date": "2024-12-05", "expected_delivery": "2024-12-28"},
    {"code": "PO-2024-ABB-0012", "vendor_code": "VEN-006", "warehouse_code": "WH-BEAWAR", "material_code": "MAT-016", "quantity": 2, "unit_price": 2500000, "status": "Manufacturing", "order_date": "2024-10-15", "expected_delivery": "2025-01-15"},
    {"code": "PO-2024-SIE-0008", "vendor_code": "VEN-007", "warehouse_code": "WH-BEAWAR", "material_code": "MAT-017", "quantity": 2, "unit_price": 1800000, "status": "In_Transit", "order_date": "2024-11-01", "expected_delivery": "2024-12-15"},
    # Orders for Bangalore project
    {"code": "PO-2024-KAL-0022", "vendor_code": "VEN-001", "warehouse_code": "WH-CHENNAI", "material_code": "MAT-001", "quantity": 20, "unit_price": 285000, "status": "In_Transit", "order_date": "2024-12-02", "expected_delivery": "2024-12-18"},
    {"code": "PO-2024-NGK-0015", "vendor_code": "VEN-004", "warehouse_code": "WH-HYDERABAD", "material_code": "MAT-006", "quantity": 100, "unit_price": 18500, "status": "Placed", "order_date": "2024-12-08", "expected_delivery": "2024-12-29"},
    # Delayed order
    {"code": "PO-2024-TAT-0033", "vendor_code": "VEN-008", "warehouse_code": "WH-JAIPUR", "material_code": "MAT-012", "quantity": 50, "unit_price": 65000, "status": "Delayed", "order_date": "2024-11-01", "expected_delivery": "2024-11-15"},
]


# ============================================================================
# PROJECT ISSUES DATA
# ============================================================================

PROJECT_ISSUES_DATA = [
    {
        "code": "ISS-2024-001",
        "issue_type": "REGULATORY_APPROVAL",
        "severity": "Critical",
        "status": "Open",
        "title": "PLC Approval Pending - M/s Shree Cement",
        "description": "PLC (Private Land Consent) approval pending with M/s Shree Cement for 2 tower locations (L-45, L-46). Negotiations ongoing for 10+ months.",
        "impact_timeline": 60,
        "impact_budget": 500000,
        "affected_activities": "Tower erection, Stringing"
    },
    {
        "code": "ISS-2024-002",
        "issue_type": "LAND_ACQUISITION",
        "severity": "High",
        "status": "In Progress",
        "title": "Forest Clearance Delay - Beawar Section",
        "description": "Stage-II forest clearance pending for 3 tower locations in Beawar forest range. Application submitted, awaiting approval.",
        "impact_timeline": 30,
        "impact_budget": 250000,
        "affected_activities": "Foundation work"
    },
    {
        "code": "ISS-2024-003",
        "issue_type": "MATERIAL_SHORTAGE",
        "severity": "Medium",
        "status": "Open",
        "title": "Suspension Tower Type B Shortage",
        "description": "4 units of Type B suspension towers pending from Kalpataru. Manufacturing delayed due to steel shortage.",
        "impact_timeline": 15,
        "impact_budget": 0,
        "affected_activities": "Tower erection"
    },
    {
        "code": "ISS-2024-004",
        "issue_type": "WEATHER_DELAY",
        "severity": "Low",
        "status": "Resolved",
        "title": "Monsoon Delay - Foundation Work",
        "description": "Heavy rainfall in August caused 10-day halt in foundation work at 5 locations.",
        "impact_timeline": 10,
        "impact_budget": 75000,
        "affected_activities": "Foundation work"
    },
    {
        "code": "ISS-2024-005",
        "issue_type": "VENDOR_DELAY",
        "severity": "Medium",
        "status": "In Progress",
        "title": "Control Panel Delivery Delayed",
        "description": "ABB India delayed delivery of Line Protection Panels by 2 weeks due to component shortage.",
        "impact_timeline": 14,
        "impact_budget": 0,
        "affected_activities": "Control system installation"
    },
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def haversine_distance(lat1, lng1, lat2, lng2):
    R = 6371
    lat1_rad, lat2_rad = radians(lat1), radians(lat2)
    delta_lat, delta_lng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

def calculate_transport_cost(distance_km, quantity, category):
    rates = {'Towers & Structures': 150, 'Conductor': 30, 'Insulator': 20, 'Hardware': 15, 'Foundation': 50, 'Stringing': 25, 'Control System': 100}
    return distance_km * quantity * rates.get(category, 35) / 1000

def calculate_eta_hours(distance_km):
    return distance_km / 45 + 4


# ============================================================================
# SEED FUNCTIONS
# ============================================================================

def clear_existing_data(session):
    print("Clearing existing data...")
    try:
        session.query(MaterialTransfer).delete()
        session.query(SubstationCriticalMaterial).delete()
        session.query(ProjectMaterialNeed).delete()
        session.query(SubstationProject).delete()
        session.query(Substation).delete()
        session.query(InventoryStock).delete()
        session.query(Warehouse).delete()
        session.query(Location).delete()
        session.query(Material).delete()
        session.commit()
        print("  Cleared all tables")
    except Exception as e:
        session.rollback()
        print(f"  Warning: {e}")


def seed_materials(session):
    print("Seeding materials...")
    material_ids = {}
    for mat in MATERIALS_DATA:
        m = Material(material_code=mat['code'], name=mat['name'], category=mat['category'], unit=mat['unit'],
                     unit_price=mat['unit_price'], lead_time_days=mat['lead_time_days'],
                     min_order_quantity=mat['min_order_qty'], safety_stock_days=14, description=f"Vendor: {mat['vendor']}")
        session.add(m)
        session.flush()
        material_ids[mat['code']] = m.id
    session.commit()
    print(f"  Seeded {len(material_ids)} materials")
    return material_ids


def seed_warehouses(session):
    print("Seeding warehouses...")
    warehouse_ids = {}
    for wh in WAREHOUSES_DATA:
        loc = Location(name=f"{wh['city']} Location", state=wh['state'], region=wh['state'], latitude=wh['lat'], longitude=wh['lng'])
        session.add(loc)
        session.flush()
        w = Warehouse(warehouse_code=wh['code'], name=wh['name'], state=wh['state'], city=wh['city'],
                      region=wh['state'], latitude=wh['lat'], longitude=wh['lng'], capacity_tons=wh['capacity_tons'], is_active=True)
        session.add(w)
        session.flush()
        warehouse_ids[wh['code']] = w.id
    session.commit()
    print(f"  Seeded {len(warehouse_ids)} warehouses")
    return warehouse_ids


def seed_substations(session):
    print("Seeding substations...")
    substation_ids = {}
    for sub in SUBSTATIONS_DATA:
        s = Substation(substation_code=sub['code'], name=sub['name'], substation_type=sub['type'], capacity=sub['capacity'],
                       state=sub['state'], city=sub['city'], latitude=sub['lat'], longitude=sub['lng'],
                       status="Active", stock_status=sub['stock_status'], stock_level_percentage=sub['stock_level'])
        session.add(s)
        session.flush()
        substation_ids[sub['code']] = s.id
    session.commit()
    print(f"  Seeded {len(substation_ids)} substations")
    return substation_ids


def seed_inventory(session, warehouse_ids, material_ids):
    print("Seeding inventory...")
    count = 0
    for wh_code, wh_id in warehouse_ids.items():
        wh_data = next((w for w in WAREHOUSES_DATA if w['code'] == wh_code), None)
        for mat_code, mat_id in material_ids.items():
            if wh_data and wh_data.get('is_project_site'):
                req = next((r for r in PROJECT_MATERIAL_REQUIREMENTS if r['material_code'] == mat_code), None)
                qty = req['available'] * 10 if req else random.randint(500, 2000)
            else:
                qty = random.randint(1000, 5000)
            stock = InventoryStock(warehouse_id=wh_id, material_id=mat_id, quantity_available=float(qty),
                                   quantity_reserved=float(qty * 0.1), quantity_in_transit=0.0,
                                   reorder_point=float(qty * 0.3), max_stock_level=float(qty * 2), min_stock_level=float(qty * 0.2))
            session.add(stock)
            count += 1
    session.commit()
    print(f"  Seeded {count} inventory records")


def seed_lilo_project(session, substation_ids, material_ids):
    print("Seeding LILO project...")
    kota_id = substation_ids.get('KTA-400')
    if not kota_id:
        return None
    proj = SubstationProject(
        project_code=LILO_PROJECT['project_code'], name=LILO_PROJECT['name'], description=LILO_PROJECT['description'],
        substation_id=kota_id, developer=LILO_PROJECT['developer'], developer_type=LILO_PROJECT['developer_type'],
        category=LILO_PROJECT['category'], project_type=LILO_PROJECT['project_type'], circuit_type=LILO_PROJECT['circuit_type'],
        voltage_level=LILO_PROJECT['voltage_level'], total_line_length=LILO_PROJECT['total_line_length'],
        total_tower_locations=LILO_PROJECT['total_tower_locations'], target_date=LILO_PROJECT['target_date'],
        anticipated_cod=LILO_PROJECT['anticipated_cod'], delay_days=LILO_PROJECT['delay_days'],
        foundation_completed=LILO_PROJECT['foundation_completed'], foundation_total=LILO_PROJECT['foundation_total'],
        tower_erected=LILO_PROJECT['tower_erected'], tower_total=LILO_PROJECT['tower_total'],
        stringing_completed_ckm=LILO_PROJECT['stringing_completed_ckm'], stringing_total_ckm=LILO_PROJECT['stringing_total_ckm'],
        overall_progress=LILO_PROJECT['overall_progress'], status=LILO_PROJECT['status'],
        delay_reason=json.dumps(DELAY_REASONS), budget_sanctioned=LILO_PROJECT['budget_sanctioned'], budget_spent=LILO_PROJECT['budget_spent']
    )
    session.add(proj)
    session.flush()
    for req in PROJECT_MATERIAL_REQUIREMENTS:
        mat_id = material_ids.get(req['material_code'])
        if mat_id:
            mat = session.query(Material).filter(Material.id == mat_id).first()
            shortage = max(0, float(req['required']) - float(req['available']))
            need = ProjectMaterialNeed(
                project_id=proj.id,
                material_id=mat_id,
                material_name=mat.name if mat else req['name'],
                quantity_needed=float(req['required']),
                quantity_available=float(req['available']),
                quantity_shortage=shortage,
                unit=mat.unit if mat else 'units',
                unit_price=mat.unit_price if mat else 0,
                priority="High" if req['status'] == "Low Stock" else "Medium",
                status="Pending" if shortage > 0 else "Fulfilled"
            )
            session.add(need)
    session.commit()
    print(f"  Seeded: {proj.name}")
    return proj.id


def seed_critical_materials(session, substation_ids, material_ids):
    print("Seeding critical materials...")
    kota_id = substation_ids.get('KTA-400')
    blr_id = substation_ids.get('BLR-220')
    if kota_id:
        for alert in CRITICAL_ALERTS:
            mat_id = material_ids.get(alert['material_code'])
            if mat_id:
                mat = session.query(Material).filter(Material.id == mat_id).first()
                cm = SubstationCriticalMaterial(substation_id=kota_id, material_id=mat_id, material_name=mat.name if mat else '',
                                                 current_quantity=float(alert['current_stock']), required_quantity=float(alert['required']),
                                                 shortage_percentage=(alert['shortfall'] / alert['required']) * 100, priority=alert['priority'])
                session.add(cm)
    if blr_id:
        for mat_code in ['MAT-004', 'MAT-005']:
            mat_id = material_ids.get(mat_code)
            if mat_id:
                mat = session.query(Material).filter(Material.id == mat_id).first()
                cm = SubstationCriticalMaterial(substation_id=blr_id, material_id=mat_id, material_name=mat.name if mat else '',
                                                 current_quantity=float(random.randint(10, 30)), required_quantity=float(random.randint(100, 150)),
                                                 shortage_percentage=random.uniform(60, 80), priority="Critical")
                session.add(cm)
    session.commit()
    print("  Seeded critical material alerts")


def seed_transfers(session, warehouse_ids, substation_ids, material_ids):
    """Seed material transfers from warehouses to substations"""
    print("Seeding material transfers...")
    count = 0
    for txn in MATERIAL_TRANSFERS_DATA:
        from_id = warehouse_ids.get(txn['from_warehouse'])
        to_substation_id = substation_ids.get(txn['to_substation'])
        mat_id = material_ids.get(txn['material_code'])
        
        if not all([from_id, to_substation_id, mat_id]):
            print(f"  Skipping transfer: missing warehouse/substation/material for {txn['po_number']}")
            continue
        
        # Get coordinates for distance calculation
        from_wh = next((w for w in WAREHOUSES_DATA if w['code'] == txn['from_warehouse']), None)
        to_sub = next((s for s in SUBSTATIONS_DATA if s['code'] == txn['to_substation']), None)
        
        distance = 0
        if from_wh and to_sub:
            distance = haversine_distance(from_wh['lat'], from_wh['lng'], to_sub['lat'], to_sub['lng'])
        
        mat_data = next((m for m in MATERIALS_DATA if m['code'] == txn['material_code']), None)
        dispatch = datetime.strptime(txn['dispatch_date'], '%Y-%m-%d')
        delivery = datetime.strptime(txn['expected_delivery'], '%Y-%m-%d')
        actual = datetime.strptime(txn['actual_delivery'], '%Y-%m-%d') if txn.get('actual_delivery') else None
        
        transfer = MaterialTransfer(
            transfer_code=txn['po_number'],
            source_warehouse_id=from_id,
            destination_substation_id=to_substation_id,
            material_id=mat_id,
            quantity=float(txn['quantity']),
            unit_cost=mat_data['unit_price'] if mat_data else 0,
            total_material_cost=float(txn['quantity']) * (mat_data['unit_price'] if mat_data else 0),
            distance_km=distance,
            transport_cost=calculate_transport_cost(distance, txn['quantity'], mat_data['category'] if mat_data else 'General'),
            estimated_eta_hours=calculate_eta_hours(distance),
            total_cost=float(txn['quantity']) * (mat_data['unit_price'] if mat_data else 0) + calculate_transport_cost(distance, txn['quantity'], mat_data['category'] if mat_data else 'General'),
            status=txn['status'],
            dispatch_date=dispatch,
            expected_delivery=delivery,
            actual_delivery=actual,
            optimization_score=random.uniform(0.75, 0.95),
            selected_reason="Optimal route selected"
        )
        session.add(transfer)
        count += 1
    session.commit()
    print(f"  Seeded {count} material transfers")


def seed_vendors(session):
    """Seed vendor/supplier data"""
    print("Seeding vendors...")
    vendor_ids = {}
    for v in VENDORS_DATA:
        vendor = Vendor(
            vendor_code=v['code'],
            name=v['name'],
            state=v['state'],
            city=v['city'],
            latitude=v['lat'],
            longitude=v['lng'],
            reliability_score=v['reliability'],
            avg_lead_time_days=v['lead_time'],
            is_active=True
        )
        session.add(vendor)
        session.flush()
        vendor_ids[v['code']] = vendor.id
    session.commit()
    print(f"  Seeded {len(vendor_ids)} vendors")
    return vendor_ids


def seed_purchase_orders(session, vendor_ids, warehouse_ids, material_ids):
    """Seed purchase orders in various stages"""
    print("Seeding purchase orders...")
    count = 0
    for po in PURCHASE_ORDERS_DATA:
        vendor_id = vendor_ids.get(po['vendor_code'])
        warehouse_id = warehouse_ids.get(po['warehouse_code'])
        material_id = material_ids.get(po['material_code'])
        
        if not all([vendor_id, warehouse_id, material_id]):
            print(f"  Skipping PO {po['code']}: missing vendor/warehouse/material")
            continue
        
        total_cost = po['quantity'] * po['unit_price']
        tax = total_cost * 0.18  # 18% GST
        transport = total_cost * 0.02  # 2% transport
        
        order = PurchaseOrder(
            order_code=po['code'],
            material_id=material_id,
            vendor_id=vendor_id,
            warehouse_id=warehouse_id,
            quantity=po['quantity'],
            unit_price=po['unit_price'],
            total_cost=total_cost,
            tax_amount=tax,
            transport_cost=transport,
            landed_cost=total_cost + tax + transport,
            order_date=datetime.strptime(po['order_date'], '%Y-%m-%d'),
            expected_delivery_date=datetime.strptime(po['expected_delivery'], '%Y-%m-%d'),
            status=po['status'],
            reasoning=f"Order for LILO project - Vendor: {po['vendor_code']}"
        )
        session.add(order)
        count += 1
    session.commit()
    print(f"  Seeded {count} purchase orders")


def seed_project_issues(session, substation_ids):
    """Seed project issues affecting operations"""
    print("Seeding project issues...")
    # Get the LILO project
    project = session.query(SubstationProject).filter(
        SubstationProject.project_code == LILO_PROJECT['project_code']
    ).first()
    
    if not project:
        print("  No project found, skipping issues")
        return
    
    kota_id = substation_ids.get('KTA-400')
    count = 0
    
    for issue in PROJECT_ISSUES_DATA:
        proj_issue = ProjectIssue(
            issue_code=issue['code'],
            project_id=project.id,
            substation_id=kota_id,
            issue_type=issue['issue_type'],
            severity=issue['severity'],
            status=issue['status'],
            title=issue['title'],
            description=issue['description'],
            impact_on_timeline=issue['impact_timeline'],
            impact_on_budget=issue['impact_budget'],
            affected_activities=issue['affected_activities'],
            reported_by="System Seed",
            reported_at=datetime.now() - timedelta(days=random.randint(10, 60))
        )
        
        # Mark resolved issues
        if issue['status'] == 'Resolved':
            proj_issue.resolved_at = datetime.now() - timedelta(days=random.randint(1, 10))
            proj_issue.resolved_by = "Project Manager"
            proj_issue.resolution_notes = "Issue resolved through coordination"
        
        session.add(proj_issue)
        count += 1
    
    session.commit()
    print(f"  Seeded {count} project issues")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 60)
    print("NEXUS Seed Script")
    print("Substations, Warehouses, Projects & Transactions")
    print("=" * 60)
    
    db_path = Path(__file__).parent.parent / "data" / "nexus.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        clear_existing_data(session)
        material_ids = seed_materials(session)
        warehouse_ids = seed_warehouses(session)
        substation_ids = seed_substations(session)
        vendor_ids = seed_vendors(session)
        seed_inventory(session, warehouse_ids, material_ids)
        seed_lilo_project(session, substation_ids, material_ids)
        seed_critical_materials(session, substation_ids, material_ids)
        seed_transfers(session, warehouse_ids, substation_ids, material_ids)
        seed_purchase_orders(session, vendor_ids, warehouse_ids, material_ids)
        seed_project_issues(session, substation_ids)
        
        print("\n" + "=" * 60)
        print("Seed completed!")
        print("=" * 60)
        print(f"\nSubstations: {len(substation_ids)} (Kota, Srinagar, Bangalore)")
        print(f"Warehouses: {len(warehouse_ids)} (Beawar, Jaipur, Chennai, Hyderabad, etc.)")
        print(f"Materials: {len(material_ids)}")
        print(f"Vendors: {len(vendor_ids)}")
        print("\nKey Data:")
        print("  - LILO Project at Kota: 73.87% progress, 60 days delay")
        print("  - 9 Purchase Orders (In-Transit, Manufacturing, etc.)")
        print("  - 5 Project Issues (2 Critical, 2 In Progress)")
        print("  - Srinagar: Strategic buffer stock")
        print("  - Bangalore: Active project site")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
