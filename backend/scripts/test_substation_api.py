#!/usr/bin/env python3
"""
Substation & Transfer API Test Script
=======================================
Tests all endpoints and displays responses for the substation/warehouse system.

Run with:
    python scripts/test_substation_api.py

Make sure the API server is running:
    uvicorn src.api.server:app --reload --port 8000
"""

import requests
import json
from datetime import datetime
from typing import Optional

# API Base URL
BASE_URL = "http://localhost:8000/api/v1"

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")


def print_subheader(text: str):
    """Print a formatted subheader."""
    print(f"\n{Colors.CYAN}--- {text} ---{Colors.ENDC}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.YELLOW}ℹ {text}{Colors.ENDC}")


def pretty_json(data: dict, indent: int = 2) -> str:
    """Format JSON for pretty printing."""
    return json.dumps(data, indent=indent, default=str)


def make_request(method: str, endpoint: str, data: dict = None, params: dict = None) -> Optional[dict]:
    """Make an API request and return the response."""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, timeout=10)
        elif method.upper() == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            print_error(f"Unknown method: {method}")
            return None
        
        print(f"{Colors.BLUE}[{method.upper()}] {url}{Colors.ENDC}")
        print(f"Status: {response.status_code}")
        
        if response.status_code >= 200 and response.status_code < 300:
            print_success("Request successful")
        else:
            print_error(f"Request failed with status {response.status_code}")
        
        try:
            return response.json()
        except:
            return {"raw": response.text}
            
    except requests.exceptions.ConnectionError:
        print_error("Could not connect to API. Make sure the server is running!")
        print_info("Start the server with: uvicorn src.api.server:app --reload --port 8000")
        return None
    except Exception as e:
        print_error(f"Request error: {e}")
        return None


def test_health_check():
    """Test API health check."""
    print_header("1. API Health Check")
    
    response = make_request("GET", "/../health")
    if response:
        print(f"\n{Colors.CYAN}Response:{Colors.ENDC}")
        print(pretty_json(response))


def test_list_substations():
    """Test listing all substations."""
    print_header("2. List All Substations")
    
    response = make_request("GET", "/substations/")
    if response:
        print(f"\n{Colors.CYAN}Found {len(response)} substations:{Colors.ENDC}")
        for sub in response[:5]:  # Show first 5
            print(f"  • {sub.get('name', 'N/A')} ({sub.get('substation_code', 'N/A')}) - {sub.get('stock_status', 'N/A')}")
        if len(response) > 5:
            print(f"  ... and {len(response) - 5} more")


def test_understocked_substations():
    """Test getting understocked substations."""
    print_header("3. Understocked Substations (Critical)")
    
    response = make_request("GET", "/substations/understocked", params={"threshold": 60.0})
    if response:
        print(f"\n{Colors.CYAN}Found {len(response)} understocked substations:{Colors.ENDC}")
        for sub in response:
            print(f"\n  {Colors.RED}⚠ {sub.get('name', 'N/A')}{Colors.ENDC}")
            print(f"    Stock Level: {sub.get('stock_level_percentage', 0)}%")
            print(f"    Status: {sub.get('stock_status', 'N/A')}")
            
            critical_mats = sub.get('critical_materials', [])
            if critical_mats:
                print(f"    Critical Materials ({len(critical_mats)}):")
                for mat in critical_mats[:3]:
                    print(f"      - {mat.get('material_name', 'N/A')}: {mat.get('shortage_percentage', 0):.1f}% shortage")


def test_overstocked_substations():
    """Test getting overstocked substations."""
    print_header("4. Overstocked Substations (Potential Sources)")
    
    response = make_request("GET", "/substations/overstocked", params={"threshold": 120.0})
    if response:
        print(f"\n{Colors.CYAN}Found {len(response)} overstocked substations:{Colors.ENDC}")
        for sub in response:
            print(f"\n  {Colors.BLUE}📦 {sub.get('name', 'N/A')}{Colors.ENDC}")
            print(f"    Stock Level: {sub.get('stock_level_percentage', 0)}%")
            print(f"    Warehouse: {sub.get('warehouse_name', 'N/A')}")


def test_substation_details():
    """Test getting specific substation details."""
    print_header("5. Substation Details (ID=1)")
    
    response = make_request("GET", "/substations/1")
    if response:
        print(f"\n{Colors.CYAN}Substation Details:{Colors.ENDC}")
        print(pretty_json(response))


def test_substations_by_state():
    """Test getting substations grouped by state."""
    print_header("6. Substations by State")
    
    response = make_request("GET", "/substations/by-state")
    if response:
        print(f"\n{Colors.CYAN}Substations by State:{Colors.ENDC}")
        for state, data in sorted(response.items()):
            print(f"  {state}:")
            print(f"    Total: {data.get('count', 0)}")
            print(f"    Normal: {data.get('normal', 0)}, Understocked: {data.get('understocked', 0)}, Overstocked: {data.get('overstocked', 0)}")


def test_dashboard_summary():
    """Test getting dashboard summary."""
    print_header("7. Dashboard Summary")
    
    response = make_request("GET", "/substations/dashboard/summary")
    if response:
        print(f"\n{Colors.CYAN}Dashboard Summary:{Colors.ENDC}")
        print(f"  Total Substations: {response.get('total_substations', 0)}")
        print(f"  Average Stock Level: {response.get('average_stock_level', 0):.1f}%")
        print(f"  Critical Alerts: {response.get('critical_alerts', 0)}")
        print(f"  Active Projects: {response.get('active_projects', 0)}")
        print(f"  Delayed Projects: {response.get('delayed_projects', 0)}")
        
        status = response.get('stock_status', {})
        print(f"\n  Stock Status Breakdown:")
        print(f"    Normal: {status.get('normal', 0)}")
        print(f"    Low: {status.get('low', 0)}")
        print(f"    Understocked: {status.get('understocked', 0)}")
        print(f"    Overstocked: {status.get('overstocked', 0)}")


def test_map_data():
    """Test getting map visualization data."""
    print_header("8. Map Visualization Data")
    
    response = make_request("GET", "/substations/map/data")
    if response:
        print(f"\n{Colors.CYAN}Map Data (first 5 substations):{Colors.ENDC}")
        for sub in response[:5]:
            color = sub.get('color', '#000')
            print(f"  📍 {sub.get('name', 'N/A')}")
            print(f"     Lat: {sub.get('lat', 0)}, Lng: {sub.get('lng', 0)}")
            print(f"     Color: {color} ({sub.get('stock_status', 'N/A')})")


def test_substation_inventory():
    """Test getting substation inventory."""
    print_header("9. Substation Inventory (ID=1)")
    
    response = make_request("GET", "/substations/1/inventory")
    if response:
        print(f"\n{Colors.CYAN}Inventory Items (first 10):{Colors.ENDC}")
        for item in response[:10]:
            low_stock = "🔴" if item.get('is_low_stock') else "🟢"
            print(f"  {low_stock} {item.get('material_name', 'N/A')}")
            print(f"     Qty: {item.get('quantity', 0):.0f} {item.get('unit', '')}")
            print(f"     Available: {item.get('available_quantity', 0):.0f}")


def test_substation_projects():
    """Test getting substation projects."""
    print_header("10. Substation Projects (ID=1)")
    
    response = make_request("GET", "/substations/1/projects")
    if response:
        if len(response) == 0:
            print_info("No projects found for this substation")
        else:
            print(f"\n{Colors.CYAN}Projects:{Colors.ENDC}")
            for proj in response:
                print(f"  📋 {proj.get('name', 'N/A')}")
                print(f"     Status: {proj.get('status', 'N/A')}")
                print(f"     Progress: {proj.get('overall_progress', 0):.1f}%")
                print(f"     Delay: {proj.get('delay_days', 0)} days")


def test_distance_calculation():
    """Test distance calculation between warehouse and substation."""
    print_header("11. Distance Calculation")
    
    response = make_request("GET", "/transfers/distance/calculate", params={
        "from_warehouse_id": 1,
        "to_substation_id": 3  # Bangalore
    })
    if response:
        print(f"\n{Colors.CYAN}Distance Calculation:{Colors.ENDC}")
        print(f"  Distance: {response.get('distance_km', 0):.2f} km")
        print(f"  ETA: {response.get('estimated_eta_hours', 0):.2f} hours")
        print(f"  ETA: {response.get('estimated_eta_days', 0):.2f} days")


def test_optimal_procurement():
    """Test optimal procurement algorithm."""
    print_header("12. Optimal Procurement Algorithm")
    
    print_subheader("Finding optimal warehouses for material procurement")
    
    # First get a material ID
    materials_response = make_request("GET", "/materials/")
    if not materials_response or len(materials_response) == 0:
        print_info("No materials found. Run seed script first.")
        return
    
    material_id = materials_response[0].get('id', 1)
    material_name = materials_response[0].get('name', 'Unknown')
    
    print(f"\n{Colors.CYAN}Testing with:{Colors.ENDC}")
    print(f"  Material: {material_name} (ID: {material_id})")
    print(f"  Destination: Substation ID 3 (Bangalore)")
    print(f"  Quantity: 100 units")
    
    response = make_request("POST", "/transfers/optimal-procurement", data={
        "destination_substation_id": 3,
        "material_id": material_id,
        "quantity_needed": 100,
        "max_options": 5
    })
    
    if response:
        print(f"\n{Colors.CYAN}Optimal Procurement Options:{Colors.ENDC}")
        print(f"  Destination: {response.get('destination_substation_name', 'N/A')}")
        print(f"  Material: {response.get('material_name', 'N/A')}")
        
        options = response.get('options', [])
        if options:
            print(f"\n  Top {len(options)} Warehouse Options:")
            for i, opt in enumerate(options, 1):
                print(f"\n  {i}. {opt.get('warehouse_name', 'N/A')}")
                print(f"     Distance: {opt.get('distance_km', 0):.2f} km")
                print(f"     Available: {opt.get('available_quantity', 0):.0f} units")
                print(f"     Total Cost: ₹{opt.get('total_cost', 0):,.2f}")
                print(f"     ETA: {opt.get('eta_hours', 0):.1f} hours")
                print(f"     Score: {opt.get('optimization_score', 0):.4f}")
        
        recommended = response.get('recommended_option')
        if recommended:
            print(f"\n{Colors.GREEN}Recommended:{Colors.ENDC} {recommended.get('warehouse_name', 'N/A')}")
        
        split = response.get('split_recommendation')
        if split:
            print(f"\n{Colors.YELLOW}Split Recommendation (insufficient single source):{Colors.ENDC}")
            for s in split:
                if 'warning' in s:
                    print(f"  ⚠ {s['warning']}")
                else:
                    print(f"  - {s.get('warehouse_name', 'N/A')}: {s.get('quantity', 0)} units")


def test_create_transfer():
    """Test creating a new transfer."""
    print_header("13. Create Material Transfer")
    
    # Get material ID
    materials_response = make_request("GET", "/materials/")
    if not materials_response or len(materials_response) == 0:
        print_info("No materials found. Run seed script first.")
        return
    
    material_id = materials_response[0].get('id', 1)
    
    print_subheader("Creating transfer from Warehouse 2 to Substation 3")
    
    response = make_request("POST", "/transfers/", data={
        "source_warehouse_id": 2,
        "destination_substation_id": 3,
        "material_id": material_id,
        "quantity": 50
    })
    
    if response:
        print(f"\n{Colors.CYAN}Transfer Created:{Colors.ENDC}")
        print(f"  Transfer Code: {response.get('transfer_code', 'N/A')}")
        print(f"  Status: {response.get('status', 'N/A')}")
        print(f"  Distance: {response.get('distance_km', 0):.2f} km")
        print(f"  Transport Cost: ₹{response.get('transport_cost', 0):,.2f}")
        print(f"  Material Cost: ₹{response.get('total_material_cost', 0):,.2f}")
        print(f"  Total Cost: ₹{response.get('total_cost', 0):,.2f}")
        print(f"  ETA: {response.get('estimated_eta_hours', 0):.2f} hours")
        print(f"  Optimization Score: {response.get('optimization_score', 0):.4f}")
        
        return response.get('id')
    return None


def test_transfer_lifecycle(transfer_id: int):
    """Test transfer lifecycle: dispatch and complete."""
    print_header("14. Transfer Lifecycle")
    
    if not transfer_id:
        print_info("No transfer ID provided. Skipping lifecycle test.")
        return
    
    # Dispatch
    print_subheader(f"Dispatching Transfer {transfer_id}")
    response = make_request("POST", f"/transfers/{transfer_id}/dispatch")
    if response:
        print(f"  Status: {response.get('status', 'N/A')}")
        print(f"  Dispatch Date: {response.get('dispatch_date', 'N/A')}")
        print(f"  Expected Delivery: {response.get('expected_delivery', 'N/A')}")
    
    # Complete
    print_subheader(f"Completing Transfer {transfer_id}")
    response = make_request("POST", f"/transfers/{transfer_id}/complete")
    if response:
        print(f"  Status: {response.get('status', 'N/A')}")
        print(f"  Actual Delivery: {response.get('actual_delivery', 'N/A')}")


def test_list_transfers():
    """Test listing all transfers."""
    print_header("15. List All Transfers")
    
    response = make_request("GET", "/transfers/")
    if response:
        print(f"\n{Colors.CYAN}Found {len(response)} transfers:{Colors.ENDC}")
        for t in response[:5]:
            status_icon = {
                'Planned': '📋',
                'In Transit': '🚚',
                'Delivered': '✅',
                'Cancelled': '❌'
            }.get(t.get('status'), '❓')
            
            print(f"\n  {status_icon} {t.get('transfer_code', 'N/A')}")
            print(f"     From: {t.get('source_warehouse_name', 'N/A')}")
            print(f"     To: {t.get('destination_substation_name', 'N/A')}")
            print(f"     Material: {t.get('material_name', 'N/A')}")
            print(f"     Qty: {t.get('quantity', 0)}")
            print(f"     Status: {t.get('status', 'N/A')}")


def test_transfer_analytics():
    """Test transfer analytics."""
    print_header("16. Transfer Analytics")
    
    response = make_request("GET", "/transfers/analytics/summary", params={"days": 30})
    if response:
        print(f"\n{Colors.CYAN}Transfer Summary (Last 30 days):{Colors.ENDC}")
        print(f"  Total Transfers: {response.get('total_transfers', 0)}")
        print(f"  Total Distance: {response.get('total_distance_km', 0):,.2f} km")
        print(f"  Total Transport Cost: ₹{response.get('total_transport_cost', 0):,.2f}")
        print(f"  Total Material Cost: ₹{response.get('total_material_cost', 0):,.2f}")
        print(f"  Average ETA: {response.get('average_eta_hours', 0):.2f} hours")
        print(f"  Average Score: {response.get('average_optimization_score', 0):.4f}")
        
        by_status = response.get('by_status', {})
        if by_status:
            print(f"\n  By Status:")
            for status, count in by_status.items():
                print(f"    {status}: {count}")


def test_distance_matrix():
    """Test distance matrix between warehouses."""
    print_header("17. Warehouse Distance Matrix")
    
    response = make_request("GET", "/transfers/distance/matrix")
    if response:
        print(f"\n{Colors.CYAN}Distance Matrix (first 3 warehouses):{Colors.ENDC}")
        for wh in response[:3]:
            print(f"\n  📍 {wh.get('warehouse_name', 'N/A')} (ID: {wh.get('warehouse_id', 'N/A')})")
            distances = wh.get('distances', [])[:3]
            for d in distances:
                print(f"     → {d.get('to_warehouse_name', 'N/A')}: {d.get('distance_km', 0):.2f} km")


def run_all_tests():
    """Run all API tests."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║     NEXUS Substation & Transfer API Test Suite                   ║")
    print("║     Testing all endpoints and interactions                       ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")
    
    print(f"{Colors.YELLOW}Make sure the API server is running:{Colors.ENDC}")
    print(f"  uvicorn src.api.server:app --reload --port 8000\n")
    
    # Run tests
    test_health_check()
    test_list_substations()
    test_understocked_substations()
    test_overstocked_substations()
    test_substation_details()
    test_substations_by_state()
    test_dashboard_summary()
    test_map_data()
    test_substation_inventory()
    test_substation_projects()
    test_distance_calculation()
    test_optimal_procurement()
    transfer_id = test_create_transfer()
    test_transfer_lifecycle(transfer_id)
    test_list_transfers()
    test_transfer_analytics()
    test_distance_matrix()
    
    print_header("Tests Complete!")
    print(f"{Colors.GREEN}All tests executed. Review the output above for results.{Colors.ENDC}")


def interactive_menu():
    """Interactive menu for running individual tests."""
    tests = {
        '1': ('Health Check', test_health_check),
        '2': ('List Substations', test_list_substations),
        '3': ('Understocked Substations', test_understocked_substations),
        '4': ('Overstocked Substations', test_overstocked_substations),
        '5': ('Substation Details', test_substation_details),
        '6': ('Substations by State', test_substations_by_state),
        '7': ('Dashboard Summary', test_dashboard_summary),
        '8': ('Map Data', test_map_data),
        '9': ('Substation Inventory', test_substation_inventory),
        '10': ('Substation Projects', test_substation_projects),
        '11': ('Distance Calculation', test_distance_calculation),
        '12': ('Optimal Procurement', test_optimal_procurement),
        '13': ('Create Transfer', test_create_transfer),
        '14': ('List Transfers', test_list_transfers),
        '15': ('Transfer Analytics', test_transfer_analytics),
        '16': ('Distance Matrix', test_distance_matrix),
        'a': ('Run All Tests', run_all_tests),
    }
    
    while True:
        print(f"\n{Colors.HEADER}{'='*50}{Colors.ENDC}")
        print(f"{Colors.BOLD}NEXUS API Test Menu{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*50}{Colors.ENDC}")
        
        for key, (name, _) in tests.items():
            print(f"  {key}. {name}")
        print(f"  q. Quit")
        
        choice = input(f"\n{Colors.CYAN}Select test: {Colors.ENDC}").strip().lower()
        
        if choice == 'q':
            print(f"\n{Colors.GREEN}Goodbye!{Colors.ENDC}")
            break
        elif choice in tests:
            tests[choice][1]()
        else:
            print_error("Invalid choice. Try again.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        run_all_tests()
    else:
        interactive_menu()
