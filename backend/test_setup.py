#!/usr/bin/env python3
"""
Quick test script to validate NEXUS setup
Run this to verify all modules are working
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing module imports...")
    
    try:
        import src.config as config
        print("✓ config")
        
        from src.core import models
        print("✓ src.core.models")
        
        from src.core import data_factory
        print("✓ src.core.data_factory")
        
        from src.core import bom_calculator
        print("✓ src.core.bom_calculator")
        
        from src.utils import geo_utils
        print("✓ src.utils.geo_utils")
        
        from src.utils import xai_explainer
        print("✓ src.utils.xai_explainer")
        
        from src.utils import logger
        print("✓ src.utils.logger")
        
        print("\n✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        return False


def test_data_generation():
    """Test data factory"""
    print("\n" + "="*70)
    print("Testing Data Generation...")
    print("="*70)
    
    try:
        from src.core.data_factory import DataFactory
        
        factory = DataFactory(seed=42)
        factory.generate_all()
        
        print("\n✅ Data generation successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Data generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bom_calculator():
    """Test BOM calculator"""
    print("\n" + "="*70)
    print("Testing BOM Calculator...")
    print("="*70)
    
    try:
        from src.core.bom_calculator import BOMCalculator
        from src.core.models import (
            Project, ProjectType, ProjectStage, 
            ProjectStatus, TerrainType
        )
        from datetime import datetime
        
        calculator = BOMCalculator()
        
        if not calculator.validate_bom_completeness():
            print("⚠️  BOM standards not loaded. Run data generation first.")
            return False
        
        # Create test project
        test_project = Project(
            id="TEST-001",
            name="Test_Transmission_Line",
            project_type=ProjectType.TRANSMISSION_LINE,
            region="Northern",
            state="Delhi",
            stage=ProjectStage.CONSTRUCTION,
            status=ProjectStatus.ACTIVE,
            start_date=datetime.now(),
            expected_end_date=datetime.now(),
            latitude=28.6,
            longitude=77.2,
            length_km=100.0,
            voltage_kv=400,
            terrain_type=TerrainType.PLAIN
        )
        
        requirements = calculator.calculate_capex_demand(test_project)
        
        print(f"\n✓ Calculated requirements for test project:")
        print(f"  Project: {test_project.name}")
        print(f"  Type: {test_project.project_type.value}")
        print(f"  Stage: {test_project.stage.value}")
        print(f"  Materials needed: {len(requirements)}")
        
        for mat_id, qty in list(requirements.items())[:5]:
            print(f"    • {mat_id}: {qty:,} units")
        
        print("\n✅ BOM calculator working correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ BOM calculator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_geo_utils():
    """Test geospatial utilities"""
    print("\n" + "="*70)
    print("Testing Geospatial Utilities...")
    print("="*70)
    
    try:
        from src.utils.geo_utils import (
            haversine_distance,
            calculate_transport_cost,
            estimate_delivery_time
        )
        
        # Test distance calculation (Delhi to Mumbai)
        delhi_lat, delhi_lon = 28.6139, 77.2090
        mumbai_lat, mumbai_lon = 19.0760, 72.8777
        
        distance = haversine_distance(delhi_lat, delhi_lon, mumbai_lat, mumbai_lon)
        print(f"\n✓ Distance Delhi to Mumbai: {distance} km")
        
        # Test transport cost
        cost = calculate_transport_cost(distance, quantity=1000)
        print(f"✓ Transport cost for 1000 units: ₹{cost:,.2f}")
        
        # Test delivery time
        eta = estimate_delivery_time(distance, base_lead_time_days=30)
        print(f"✓ Estimated delivery time: {eta} days")
        
        print("\n✅ Geo utilities working correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ Geo utilities test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("NEXUS SYSTEM VALIDATION")
    print("="*70)
    
    results = []
    
    # Test imports
    results.append(("Imports", test_imports()))
    
    # Test data generation
    results.append(("Data Generation", test_data_generation()))
    
    # Test BOM calculator
    results.append(("BOM Calculator", test_bom_calculator()))
    
    # Test geo utils
    results.append(("Geo Utilities", test_geo_utils()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All systems operational!")
        print("\nNext steps:")
        print("  1. Review generated data in data/generated/")
        print("  2. Continue with Phase 2: Intelligence Layer")
        print("  3. Run 'python main.py' once complete")
    else:
        print("\n⚠️  Some tests failed. Please review errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
