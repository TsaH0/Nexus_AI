"""
Inventory Reconciler - Transfer-First Logic
Smart inventory reconciliation that prioritizes using existing stock before new procurement
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config import *
from src.core.models import Warehouse, Material, TransferOrder
from src.utils.geo_utils import haversine_distance, calculate_transport_cost


@dataclass
class TransferOption:
    """Represents a potential inter-warehouse transfer"""
    from_warehouse: Warehouse
    to_warehouse: Warehouse
    material_id: str
    quantity: int
    distance_km: float
    transport_cost: float
    estimated_days: int
    cost_per_unit: float
    
    def __lt__(self, other):
        """For sorting by cost"""
        return self.cost_per_unit < other.cost_per_unit


class InventoryReconciler:
    """
    Advanced inventory reconciliation with transfer-first optimization
    
    TODO: PRODUCTION ENHANCEMENTS
    1. Real-time inventory synchronization across warehouses
    2. Concurrent transfer optimization (multiple materials simultaneously)
    3. Multi-modal transport optimization (truck + rail + air)
    4. Time-window constrained transfers (urgent vs standard)
    5. Warehouse capacity forecasting (avoid overflow)
    6. In-transit inventory tracking (materials already moving)
    7. Quality-grade matching (A-grade, B-grade materials)
    8. FIFO/FEFO enforcement (First In First Out / First Expire First Out)
    9. Consignment stock optimization (vendor-owned inventory)
    10. Cross-docking opportunities (bypass warehouse storage)
    11. Load consolidation (multiple materials in one truck)
    12. Return/reverse logistics handling
    """
    
    def __init__(self, warehouses: List[Warehouse], materials: List[Material]):
        """
        Initialize inventory reconciler
        
        Args:
            warehouses: List of all warehouses
            materials: List of all materials
        """
        self.warehouses = warehouses
        self.materials = materials
        self.materials_dict = {m.id: m for m in materials}
        
        # Pre-calculate distance matrix for performance
        self.distance_matrix = self._calculate_distance_matrix()
        
        # Track transfers in progress (TODO: integrate with actual tracking system)
        self.pending_transfers = []
        
        # Cache for performance
        self.inventory_cache = {}
        self.last_cache_update = None
    
    def _calculate_distance_matrix(self) -> Dict[Tuple[str, str], float]:
        """
        Pre-calculate distances between all warehouse pairs
        
        Returns:
            Dictionary mapping (from_wh_id, to_wh_id) to distance_km
        
        TODO: DISTANCE CALCULATION ENHANCEMENTS
        1. Use actual road network distances (Google Maps API, OSRM)
        2. Account for road quality (highway vs rural roads)
        3. Seasonal adjustments (monsoon road closures)
        4. Real-time traffic conditions
        5. Toll road optimization
        6. Multi-route options (fastest vs cheapest)
        """
        matrix = {}
        
        for wh1 in self.warehouses:
            for wh2 in self.warehouses:
                if wh1.id == wh2.id:
                    matrix[(wh1.id, wh2.id)] = 0.0
                else:
                    dist = haversine_distance(
                        wh1.latitude, wh1.longitude,
                        wh2.latitude, wh2.longitude
                    )
                    matrix[(wh1.id, wh2.id)] = dist
        
        return matrix
    
    def find_available_inventory(self, 
                                material_id: str,
                                required_quantity: int,
                                exclude_warehouse_ids: Optional[List[str]] = None) -> List[Tuple[Warehouse, int]]:
        """
        Find warehouses that have available inventory of a material
        
        Args:
            material_id: Material to search for
            required_quantity: Quantity needed
            exclude_warehouse_ids: Warehouses to exclude from search
        
        Returns:
            List of (warehouse, available_quantity) tuples
        
        TODO: INVENTORY SEARCH ENHANCEMENTS
        1. Consider quality grades and batch numbers
        2. Check expiry dates (FEFO for perishables)
        3. Reserved inventory (already allocated to other orders)
        4. In-transit inventory (on the way to warehouse)
        5. Consignment stock (vendor-owned but at our warehouse)
        6. Damaged/quarantine stock exclusion
        7. Minimum stock level constraints (don't deplete below safety stock)
        8. Lock mechanism (prevent concurrent allocation)
        """
        exclude_ids = exclude_warehouse_ids or []
        available = []
        
        for warehouse in self.warehouses:
            if warehouse.id in exclude_ids:
                continue
            
            # Get current inventory
            current_stock = warehouse.inventory.get(material_id, 0)
            safety_stock = warehouse.safety_stock.get(material_id, 0)
            
            # Available = current - safety_stock
            # We don't want to go below safety stock
            available_qty = max(0, current_stock - safety_stock)
            
            if available_qty > 0:
                available.append((warehouse, available_qty))
        
        # Sort by available quantity (descending)
        available.sort(key=lambda x: x[1], reverse=True)
        
        return available
    
    def find_optimal_transfer(self,
                            material_id: str,
                            quantity: int,
                            destination_warehouse: Warehouse,
                            max_distance_km: Optional[float] = None) -> Optional[TransferOption]:
        """
        Find the most cost-effective transfer option
        
        Args:
            material_id: Material to transfer
            quantity: Quantity needed
            destination_warehouse: Target warehouse
            max_distance_km: Maximum distance to consider (None = unlimited)
        
        Returns:
            Best TransferOption or None if not found
        
        TODO: TRANSFER OPTIMIZATION ENHANCEMENTS
        1. Multi-source transfers (combine from multiple warehouses)
        2. Partial transfer optimization (transfer less than full need)
        3. Time-sensitive optimization (urgent vs standard delivery)
        4. Carbon footprint minimization (sustainability)
        5. Truck utilization optimization (full truck loads)
        6. Backhaul opportunities (return trip optimization)
        7. Hub-and-spoke routing (via intermediate warehouses)
        8. Risk-adjusted cost (unreliable routes cost more)
        9. Seasonal route optimization (monsoon detours)
        10. Real-time carrier pricing integration
        """
        
        # Find warehouses with available inventory
        available = self.find_available_inventory(
            material_id=material_id,
            required_quantity=quantity,
            exclude_warehouse_ids=[destination_warehouse.id]
        )
        
        if not available:
            return None
        
        # Evaluate each potential source
        transfer_options = []
        
        for source_warehouse, available_qty in available:
            # Check if this warehouse has enough
            if available_qty < quantity:
                continue
            
            # Get distance
            distance = self.distance_matrix.get(
                (source_warehouse.id, destination_warehouse.id),
                0.0
            )
            
            # Check distance constraint
            if max_distance_km and distance > max_distance_km:
                continue
            
            # Calculate transport cost
            transport_cost = calculate_transport_cost(
                distance_km=distance,
                quantity=quantity,
                cost_per_km=TRANSPORT_COST_PER_KM,
                loading_cost=LOADING_UNLOADING_COST
            )
            
            # Add handling cost
            handling_cost = quantity * WAREHOUSE_HANDLING_COST_PER_UNIT
            total_cost = transport_cost + handling_cost
            
            # Estimate delivery time
            # TODO: Use real logistics API for accurate ETAs
            travel_days = max(1, int(distance / 400))  # Assume 400 km/day average
            
            # Cost per unit
            cost_per_unit = total_cost / quantity if quantity > 0 else float('inf')
            
            option = TransferOption(
                from_warehouse=source_warehouse,
                to_warehouse=destination_warehouse,
                material_id=material_id,
                quantity=quantity,
                distance_km=distance,
                transport_cost=total_cost,
                estimated_days=travel_days,
                cost_per_unit=cost_per_unit
            )
            
            transfer_options.append(option)
        
        # Return the cheapest option
        if transfer_options:
            return min(transfer_options)
        
        return None
    
    def reconcile_demand(self,
                        material_id: str,
                        required_quantity: int,
                        destination_warehouse: Warehouse,
                        vs_procurement_cost: Optional[float] = None) -> Dict[str, any]:
        """
        Reconcile demand: decide between transfer, procurement, or combination
        
        Args:
            material_id: Material needed
            required_quantity: Quantity required
            destination_warehouse: Where material is needed
            vs_procurement_cost: Cost of new procurement (for comparison)
        
        Returns:
            Reconciliation decision dictionary
        
        TODO: RECONCILIATION LOGIC ENHANCEMENTS
        1. Multi-source optimization (split between transfer + procurement)
        2. Time-cost tradeoff analysis (faster vs cheaper)
        3. Risk-adjusted decisions (prefer reliable sources)
        4. Batch splitting (multiple smaller transfers)
        5. JIT (Just-In-Time) vs buffer stock strategy
        6. Vendor relationship consideration (use or lose contracts)
        7. Working capital optimization (use inventory vs new purchase)
        8. Tax optimization (inter-state GST implications)
        9. Insurance cost consideration
        10. Quality consistency (same batch vs mixed sources)
        """
        
        result = {
            'material_id': material_id,
            'required_quantity': required_quantity,
            'destination': destination_warehouse.id,
            'decision': 'PROCURE',  # Default
            'transfer_option': None,
            'procurement_quantity': required_quantity,
            'transfer_quantity': 0,
            'cost_savings': 0.0,
            'reasoning': ''
        }
        
        # Check local warehouse first
        local_available = destination_warehouse.inventory.get(material_id, 0)
        local_safety = destination_warehouse.safety_stock.get(material_id, 0)
        local_usable = max(0, local_available - local_safety)
        
        if local_usable >= required_quantity:
            result['decision'] = 'USE_LOCAL'
            result['procurement_quantity'] = 0
            result['reasoning'] = f"Sufficient local stock available ({local_usable} units)"
            return result
        
        # Need to source from elsewhere
        shortfall = required_quantity - local_usable
        
        # Find best transfer option
        best_transfer = self.find_optimal_transfer(
            material_id=material_id,
            quantity=shortfall,
            destination_warehouse=destination_warehouse
        )
        
        if not best_transfer:
            result['decision'] = 'PROCURE'
            result['procurement_quantity'] = shortfall
            result['reasoning'] = f"No suitable transfer option found. Procure {shortfall} units."
            return result
        
        # Compare transfer cost vs procurement cost
        if vs_procurement_cost:
            cost_savings = vs_procurement_cost - best_transfer.transport_cost
            savings_pct = (cost_savings / vs_procurement_cost) * 100 if vs_procurement_cost > 0 else 0
            
            result['cost_savings'] = cost_savings
            
            if cost_savings > 0:
                # Transfer is cheaper
                result['decision'] = 'TRANSFER'
                result['transfer_option'] = best_transfer
                result['transfer_quantity'] = shortfall
                result['procurement_quantity'] = 0
                result['reasoning'] = (
                    f"Transfer from {best_transfer.from_warehouse.id} is ₹{cost_savings:,.0f} "
                    f"cheaper ({savings_pct:.1f}% savings). "
                    f"Distance: {best_transfer.distance_km:.0f}km, "
                    f"ETA: {best_transfer.estimated_days} days."
                )
            else:
                # Procurement is cheaper
                result['decision'] = 'PROCURE'
                result['procurement_quantity'] = shortfall
                result['reasoning'] = (
                    f"New procurement is ₹{abs(cost_savings):,.0f} cheaper than transfer. "
                    f"Transfer would cost ₹{best_transfer.transport_cost:,.0f}."
                )
        else:
            # No procurement cost available, default to transfer if possible
            result['decision'] = 'TRANSFER'
            result['transfer_option'] = best_transfer
            result['transfer_quantity'] = shortfall
            result['procurement_quantity'] = 0
            result['reasoning'] = (
                f"Transfer from {best_transfer.from_warehouse.id}. "
                f"Cost: ₹{best_transfer.transport_cost:,.0f}, "
                f"Distance: {best_transfer.distance_km:.0f}km, "
                f"ETA: {best_transfer.estimated_days} days."
            )
        
        return result
    
    def create_transfer_order(self,
                            transfer_option: TransferOption,
                            order_id: str,
                            order_date: datetime) -> TransferOrder:
        """
        Create a transfer order from a transfer option
        
        Args:
            transfer_option: Transfer option to execute
            order_id: Unique order ID
            order_date: Order date
        
        Returns:
            TransferOrder object
        
        TODO: TRANSFER ORDER ENHANCEMENTS
        1. Multi-leg transfers (via intermediate warehouses)
        2. Carrier selection and booking integration
        3. Real-time tracking integration (GPS)
        4. Automated documentation generation (delivery challan, e-way bill)
        5. Insurance auto-purchase for high-value transfers
        6. Temperature-controlled transport for sensitive materials
        7. Packaging requirement calculation
        8. Loading/unloading crew scheduling
        9. Quality inspection checkpoints
        10. Automated invoice reconciliation
        """
        
        expected_arrival = order_date + timedelta(days=transfer_option.estimated_days)
        
        # Generate reasoning
        material = self.materials_dict.get(transfer_option.material_id)
        material_name = material.name if material else transfer_option.material_id
        
        reasoning = (
            f"Transfer {transfer_option.quantity} units of {material_name} "
            f"from {transfer_option.from_warehouse.name} to {transfer_option.to_warehouse.name}. "
            f"Distance: {transfer_option.distance_km:.1f}km, "
            f"Cost: ₹{transfer_option.transport_cost:,.0f}, "
            f"ETA: {expected_arrival.strftime('%Y-%m-%d')}. "
            f"Using existing inventory reduces capital expenditure."
        )
        
        transfer_order = TransferOrder(
            id=order_id,
            material_id=transfer_option.material_id,
            quantity=transfer_option.quantity,
            from_warehouse_id=transfer_option.from_warehouse.id,
            to_warehouse_id=transfer_option.to_warehouse.id,
            transfer_date=order_date,
            expected_arrival_date=expected_arrival,
            transport_cost=transfer_option.transport_cost,
            distance_km=transfer_option.distance_km,
            status='Initiated',
            reasoning=reasoning
        )
        
        return transfer_order
    
    def execute_transfer(self, transfer_order: TransferOrder) -> bool:
        """
        Execute a transfer order (update warehouse inventories)
        
        Args:
            transfer_order: Transfer order to execute
        
        Returns:
            True if successful, False otherwise
        
        TODO: EXECUTION ENHANCEMENTS
        1. Two-phase commit (reserve → deduct → confirm)
        2. Rollback mechanism for failed transfers
        3. Partial delivery handling
        4. Damage/loss reporting
        5. Automated reconciliation with physical count
        6. Blockchain for tamper-proof records
        7. Real-time notification to stakeholders
        8. Automated payment processing
        """
        
        # Find source and destination warehouses
        source_wh = None
        dest_wh = None
        
        for wh in self.warehouses:
            if wh.id == transfer_order.from_warehouse_id:
                source_wh = wh
            if wh.id == transfer_order.to_warehouse_id:
                dest_wh = wh
        
        if not source_wh or not dest_wh:
            return False
        
        # Check if source has enough inventory
        if not source_wh.has_stock(transfer_order.material_id, transfer_order.quantity):
            return False
        
        # Check if destination has capacity
        if dest_wh.available_capacity() < transfer_order.quantity:
            return False
        
        # Execute transfer
        source_wh.remove_stock(transfer_order.material_id, transfer_order.quantity)
        dest_wh.add_stock(transfer_order.material_id, transfer_order.quantity)
        
        # Update status
        transfer_order.status = 'Completed'
        transfer_order.actual_arrival_date = datetime.now()
        
        return True
    
    def optimize_multi_material_transfers(self,
                                         demands: Dict[str, int],
                                         destination_warehouse: Warehouse) -> List[TransferOption]:
        """
        Optimize transfers for multiple materials simultaneously
        
        Args:
            demands: Dictionary of {material_id: quantity}
            destination_warehouse: Destination
        
        Returns:
            List of optimal transfer options
        
        TODO: MULTI-MATERIAL OPTIMIZATION
        1. Truck load optimization (combine materials in one shipment)
        2. Route optimization (multi-stop pickups)
        3. Volume and weight constraints
        4. Compatibility checks (can materials ship together?)
        5. Priority-based allocation (critical vs standard)
        6. Cost pooling (shared transport cost)
        7. Scheduling coordination (simultaneous arrivals)
        """
        
        optimal_transfers = []
        
        for material_id, quantity in demands.items():
            transfer_option = self.find_optimal_transfer(
                material_id=material_id,
                quantity=quantity,
                destination_warehouse=destination_warehouse
            )
            
            if transfer_option:
                optimal_transfers.append(transfer_option)
        
        # TODO: Apply load consolidation optimization
        # Group transfers from same source warehouse
        # Combine into single shipment to save costs
        
        return optimal_transfers


# TODO: FUTURE INVENTORY RECONCILER FEATURES
"""
PRODUCTION-READY ENHANCEMENTS:

1. REAL-TIME INVENTORY VISIBILITY
   - IoT sensors in warehouses (RFID, barcode scanners)
   - Mobile app for warehouse staff
   - Real-time stock updates (every transaction)
   - In-transit visibility (GPS tracking)
   - Cycle count automation
   - Perpetual inventory system

2. ADVANCED TRANSFER OPTIMIZATION
   - Mixed Integer Linear Programming (MILP) solver
   - Network flow optimization algorithms
   - Dynamic programming for multi-stage transfers
   - Stochastic optimization (demand uncertainty)
   - Robust optimization (worst-case scenarios)
   - Real-time re-optimization (as conditions change)

3. MULTI-MODAL TRANSPORT
   - Road + Rail optimization
   - Air freight for urgent needs
   - Coastal shipping for bulk
   - Intermodal container tracking
   - Mode selection based on urgency/cost

4. WAREHOUSE MANAGEMENT INTEGRATION
   - WMS (Warehouse Management System) API
   - Automated pick/pack/ship
   - Slotting optimization (where to store)
   - Labor management (staff scheduling)
   - Equipment utilization (forklifts, cranes)

5. QUALITY & COMPLIANCE
   - Quality grade tracking (A, B, C grade)
   - Batch/lot number traceability
   - Expiry date management (FEFO)
   - Recall management capability
   - Regulatory compliance (hazmat, food-grade)
   - ISO/GMP compliance tracking

6. FINANCIAL OPTIMIZATION
   - Working capital minimization
   - Inventory carrying cost optimization
   - Obsolescence risk management
   - Tax optimization (inter-state transfers)
   - Insurance optimization
   - Financing options (vendor managed inventory)

7. SUSTAINABILITY
   - Carbon footprint calculation
   - Route optimization for emissions
   - Electric vehicle fleet integration
   - Packaging waste reduction
   - Reverse logistics (returns, recycling)
   - Circular economy practices
"""


if __name__ == "__main__":
    """Test inventory reconciler"""
    from src.core.data_factory import DataFactory
    
    print("Testing Inventory Reconciler...")
    print("="*70)
    
    # Generate test data
    factory = DataFactory(seed=42)
    factory.generate_all()
    
    # Create reconciler
    reconciler = InventoryReconciler(
        warehouses=factory.warehouses,
        materials=factory.materials
    )
    
    # Test: Find optimal transfer
    test_dest = factory.warehouses[0]
    test_material = factory.materials[0].id
    
    print(f"\nFinding optimal transfer for {test_material} to {test_dest.name}...")
    
    transfer_option = reconciler.find_optimal_transfer(
        material_id=test_material,
        quantity=100,
        destination_warehouse=test_dest
    )
    
    if transfer_option:
        print(f"\n✓ Found transfer option:")
        print(f"  From: {transfer_option.from_warehouse.name}")
        print(f"  To: {transfer_option.to_warehouse.name}")
        print(f"  Distance: {transfer_option.distance_km:.1f} km")
        print(f"  Cost: ₹{transfer_option.transport_cost:,.0f}")
        print(f"  ETA: {transfer_option.estimated_days} days")
    else:
        print("\n✗ No suitable transfer option found")
    
    print("\n✓ Inventory reconciler test complete!")
