"""
Inventory Management System - Demo & Test Script

This script demonstrates the full functionality of the inventory management system.
Run after starting the API server.

Usage:
    python demo_inventory.py
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/v1"

def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def print_response(title: str, data: Any):
    """Print formatted response"""
    print(f"✅ {title}")
    print(json.dumps(data, indent=2, default=str))
    print()

def test_stock_levels():
    """Test stock level queries"""
    print_section("📊 STOCK LEVEL QUERIES")
    
    # Get all stock
    response = requests.get(f"{BASE_URL}/inventory/stock", params={"limit": 5})
    if response.status_code == 200:
        stocks = response.json()
        print_response(f"All Stock (showing {len(stocks)} items)", stocks)
    
    # Get low stock items
    response = requests.get(f"{BASE_URL}/inventory/stock", params={"low_stock_only": True})
    if response.status_code == 200:
        print_response("Low Stock Items", response.json())

def test_stock_operations():
    """Test stock in/out/transfer operations"""
    print_section("🔄 STOCK OPERATIONS")
    
    # Stock IN
    print("1️⃣ Adding stock to warehouse...")
    stock_in_data = {
        "warehouse_id": 1,
        "material_id": 1,
        "quantity": 100.0,
        "unit_cost": 55000.0,
        "reference_type": "PO",
        "reference_id": "PO-DEMO-001",
        "remarks": "Demo purchase order receipt"
    }
    response = requests.post(f"{BASE_URL}/inventory/operations/stock-in", json=stock_in_data)
    if response.status_code == 200:
        print_response("Stock IN Success", response.json())
    else:
        print(f"❌ Stock IN Failed: {response.status_code} - {response.text}\n")
    
    # Stock OUT
    print("2️⃣ Issuing stock to project...")
    stock_out_data = {
        "warehouse_id": 1,
        "material_id": 1,
        "quantity": 25.0,
        "project_id": 1,
        "reference_type": "PROJECT",
        "reference_id": "PRJ-001",
        "remarks": "Demo project requirement"
    }
    response = requests.post(f"{BASE_URL}/inventory/operations/stock-out", json=stock_out_data)
    if response.status_code == 200:
        print_response("Stock OUT Success", response.json())
    else:
        print(f"❌ Stock OUT Failed: {response.status_code} - {response.text}\n")
    
    # Stock Transfer
    print("3️⃣ Transferring stock between warehouses...")
    transfer_data = {
        "material_id": 1,
        "source_warehouse_id": 1,
        "destination_warehouse_id": 2,
        "quantity": 15.0,
        "remarks": "Demo inter-warehouse transfer"
    }
    response = requests.post(f"{BASE_URL}/inventory/operations/transfer", json=transfer_data)
    if response.status_code == 200:
        print_response("Stock TRANSFER Success", response.json())
    else:
        print(f"❌ Stock TRANSFER Failed: {response.status_code} - {response.text}\n")
    
    # Stock Adjustment
    print("4️⃣ Adjusting stock (correction)...")
    adjustment_data = {
        "warehouse_id": 1,
        "material_id": 1,
        "quantity_adjustment": -5.0,
        "remarks": "Demo adjustment - damaged goods"
    }
    response = requests.post(f"{BASE_URL}/inventory/operations/adjust", json=adjustment_data)
    if response.status_code == 200:
        print_response("Stock ADJUSTMENT Success", response.json())
    else:
        print(f"❌ Stock ADJUSTMENT Failed: {response.status_code} - {response.text}\n")

def test_reservations():
    """Test stock reservation system"""
    print_section("📦 STOCK RESERVATIONS")
    
    # Create reservation
    print("1️⃣ Creating stock reservation...")
    reservation_data = {
        "warehouse_id": 1,
        "material_id": 2,
        "project_id": 1,
        "quantity": 50.0,
        "required_by_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "priority": "High",
        "remarks": "Demo reservation for critical project"
    }
    response = requests.post(f"{BASE_URL}/inventory/reservations", json=reservation_data)
    if response.status_code == 200:
        reservation = response.json()
        print_response("Reservation Created", reservation)
        reservation_id = reservation['id']
        
        # Issue against reservation
        print("2️⃣ Issuing reserved stock...")
        issue_data = {
            "quantity_to_issue": 25.0,
            "remarks": "Partial fulfillment"
        }
        response = requests.post(
            f"{BASE_URL}/inventory/reservations/{reservation_id}/issue",
            json=issue_data
        )
        if response.status_code == 200:
            print_response("Stock Issued Against Reservation", response.json())
    else:
        print(f"❌ Reservation Failed: {response.status_code} - {response.text}\n")
    
    # Get all reservations
    print("3️⃣ Getting all active reservations...")
    response = requests.get(f"{BASE_URL}/inventory/reservations", params={"status": "Active"})
    if response.status_code == 200:
        print_response("Active Reservations", response.json())

def test_transactions():
    """Test transaction history"""
    print_section("📋 TRANSACTION HISTORY")
    
    # Get recent transactions
    response = requests.get(f"{BASE_URL}/inventory/transactions", params={"limit": 10})
    if response.status_code == 200:
        transactions = response.json()
        print_response(f"Recent Transactions (showing {len(transactions)})", transactions)

def test_alerts():
    """Test alert system"""
    print_section("🚨 ALERTS")
    
    # Get unresolved alerts
    response = requests.get(f"{BASE_URL}/inventory/alerts", params={"is_resolved": False})
    if response.status_code == 200:
        alerts = response.json()
        print_response(f"Unresolved Alerts ({len(alerts)} total)", alerts[:5])  # Show first 5

def test_analytics():
    """Test analytics endpoints"""
    print_section("📈 ANALYTICS")
    
    # Overall summary
    response = requests.get(f"{BASE_URL}/inventory/analytics/summary")
    if response.status_code == 200:
        summary = response.json()
        print_response("Inventory Summary", summary)
        
        print("\n📊 Key Metrics:")
        print(f"   Total Stock Value: ₹{summary.get('total_stock_value', 0):,.2f}")
        print(f"   Reserved Value: ₹{summary.get('total_reserved_value', 0):,.2f}")
        print(f"   Low Stock Items: {summary.get('low_stock_items', 0)}")
        print(f"   Out of Stock: {summary.get('out_of_stock_items', 0)}")
        print(f"   Active Reservations: {summary.get('active_reservations', 0)}")
        print(f"   Pending Alerts: {summary.get('pending_alerts', 0)}\n")
    
    # Warehouse analytics
    response = requests.get(f"{BASE_URL}/inventory/analytics/warehouse/1")
    if response.status_code == 200:
        print_response("Warehouse 1 Analytics", response.json())
    
    # Material analytics
    response = requests.get(f"{BASE_URL}/inventory/analytics/material/1")
    if response.status_code == 200:
        print_response("Material 1 Analytics", response.json())

def main():
    """Run all tests"""
    print("\n" + "🚀"*40)
    print("  NEXUS Inventory Management System - Demo")
    print("🚀"*40)
    
    try:
        # Check if server is running
        response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health")
        if response.status_code != 200:
            print("\n❌ Error: API server is not running!")
            print("Please start the server with: uvicorn src.api.server:app --reload --port 8000")
            return
        
        print("\n✅ API Server is running!")
        
        # Run tests
        test_stock_levels()
        test_stock_operations()
        test_reservations()
        test_transactions()
        test_alerts()
        test_analytics()
        
        print_section("✨ DEMO COMPLETE")
        print("All inventory management features demonstrated successfully!")
        print("\n📖 For detailed API documentation, visit: http://localhost:8000/docs")
        print("\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to API server!")
        print("Please ensure the server is running:")
        print("  cd /Users/chiru/Projects/Nexus")
        print("  uvicorn src.api.server:app --reload --port 8000")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
