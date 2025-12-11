"""
Order Batcher - Bulk Discount Optimization
Intelligent order aggregation for economies of scale and freight optimization
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config import *
from src.core.models import PurchaseOrder, TransferOrder, Vendor, Warehouse, Material


@dataclass
class OrderBatch:
    """Represents a batched order for optimization"""
    batch_id: str
    vendor_id: Optional[str] = None  # For purchase orders
    from_warehouse_id: Optional[str] = None  # For transfers
    to_warehouse_id: Optional[str] = None
    
    # Materials in this batch
    materials: Dict[str, int] = field(default_factory=dict)  # {material_id: quantity}
    
    # Cost components
    total_material_cost: float = 0.0
    total_transport_cost: float = 0.0
    bulk_discount: float = 0.0
    freight_savings: float = 0.0
    net_cost: float = 0.0
    
    # Metadata
    order_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    reasoning: str = ""
    
    # Original orders that were batched
    original_order_ids: List[str] = field(default_factory=list)


class OrderBatcher:
    """
    Advanced order batching for cost optimization
    
    TODO: PRODUCTION ENHANCEMENTS
    1. Time-window batching (accumulate orders over days)
    2. Machine learning for optimal batch timing
    3. Multi-echelon batching (orders at different levels)
    4. Cross-functional batching (projects + maintenance)
    5. Dynamic batch size optimization
    6. Real-time freight pricing integration
    7. Container load optimization (FCL vs LCL)
    8. Multi-modal transport batching
    9. Vendor-managed inventory (VMI) batching
    10. Collaborative batching (with other buyers)
    """
    
    def __init__(self, 
                 vendors: List[Vendor],
                 warehouses: List[Warehouse],
                 materials: List[Material]):
        """
        Initialize order batcher
        
        Args:
            vendors: List of all vendors
            warehouses: List of all warehouses
            materials: List of all materials
        """
        self.vendors = vendors
        self.warehouses = warehouses
        self.materials = materials
        
        self.vendors_dict = {v.id: v for v in vendors}
        self.warehouses_dict = {w.id: w for w in warehouses}
        self.materials_dict = {m.id: m for m in materials}
        
        # Batching parameters (TODO: make configurable)
        self.min_batch_quantity = 50  # Minimum quantity for batching
        self.batch_time_window_days = 3  # Days to accumulate orders
        self.freight_optimization_enabled = True
    
    def can_batch_purchase_orders(self, 
                                  order1: PurchaseOrder, 
                                  order2: PurchaseOrder) -> bool:
        """
        Check if two purchase orders can be batched together
        
        Args:
            order1: First purchase order
            order2: Second purchase order
        
        Returns:
            True if can be batched
        
        TODO: BATCHING COMPATIBILITY CHECKS
        1. Material compatibility (can ship together?)
        2. Hazmat regulations (cannot mix certain chemicals)
        3. Temperature requirements (frozen vs ambient)
        4. Delivery window alignment
        5. Payment term compatibility
        6. Quality inspection requirements
        7. Customs clearance (for imports)
        8. Vendor capacity constraints
        """
        
        # Must be same vendor
        if order1.vendor_id != order2.vendor_id:
            return False
        
        # Must be same destination
        if order1.delivery_warehouse_id != order2.delivery_warehouse_id:
            return False
        
        # Must be within time window
        if abs((order1.order_date - order2.order_date).days) > self.batch_time_window_days:
            return False
        
        # Check delivery date compatibility
        # Use the later expected delivery date
        # TODO: More sophisticated time window logic
        
        return True
    
    def can_batch_transfer_orders(self,
                                  order1: TransferOrder,
                                  order2: TransferOrder) -> bool:
        """
        Check if two transfer orders can be batched together
        
        Args:
            order1: First transfer order
            order2: Second transfer order
        
        Returns:
            True if can be batched
        
        TODO: TRANSFER BATCHING CHECKS
        1. Vehicle capacity constraints
        2. Route optimization (multi-stop pickups)
        3. Time window compatibility
        4. Handling equipment compatibility
        5. Security requirements (high-value items)
        """
        
        # Must have same source and destination
        if (order1.from_warehouse_id != order2.from_warehouse_id or
            order1.to_warehouse_id != order2.to_warehouse_id):
            return False
        
        # Must be within time window
        if abs((order1.transfer_date - order2.transfer_date).days) > self.batch_time_window_days:
            return False
        
        return True
    
    def batch_purchase_orders(self, 
                             orders: List[PurchaseOrder]) -> List[OrderBatch]:
        """
        Batch purchase orders for optimization
        
        Args:
            orders: List of purchase orders to batch
        
        Returns:
            List of batched orders
        
        TODO: BATCHING OPTIMIZATION
        1. Use graph algorithms for optimal grouping
        2. Knapsack problem for vehicle loading
        3. Bin packing for container optimization
        4. Set cover for multi-order batching
        5. Dynamic programming for time-window optimization
        """
        
        if not orders:
            return []
        
        # Group orders by (vendor, warehouse)
        groups = defaultdict(list)
        
        for order in orders:
            key = (order.vendor_id, order.delivery_warehouse_id)
            groups[key].append(order)
        
        # Create batches
        batches = []
        batch_counter = 1
        
        for (vendor_id, warehouse_id), group_orders in groups.items():
            # Sort by order date
            group_orders.sort(key=lambda o: o.order_date)
            
            # Create batch
            batch = OrderBatch(
                batch_id=f"BATCH-PO-{batch_counter:04d}",
                vendor_id=vendor_id,
                to_warehouse_id=warehouse_id,
                order_date=min(o.order_date for o in group_orders),
                expected_delivery_date=max(o.expected_delivery_date for o in group_orders)
            )
            
            # Aggregate materials
            for order in group_orders:
                if order.material_id in batch.materials:
                    batch.materials[order.material_id] += order.quantity
                else:
                    batch.materials[order.material_id] = order.quantity
                
                batch.total_material_cost += order.total_cost
                batch.original_order_ids.append(order.id)
            
            # Calculate savings
            batch = self._calculate_batch_savings(batch, group_orders)
            
            batches.append(batch)
            batch_counter += 1
        
        return batches
    
    def batch_transfer_orders(self,
                             orders: List[TransferOrder]) -> List[OrderBatch]:
        """
        Batch transfer orders for freight optimization
        
        Args:
            orders: List of transfer orders to batch
        
        Returns:
            List of batched transfers
        
        TODO: TRANSFER BATCHING OPTIMIZATION
        1. Multi-stop route optimization
        2. Vehicle type selection (truck, train, air)
        3. Load consolidation across time windows
        4. Milk-run optimization (circular routes)
        """
        
        if not orders:
            return []
        
        # Group orders by (from_warehouse, to_warehouse)
        groups = defaultdict(list)
        
        for order in orders:
            key = (order.from_warehouse_id, order.to_warehouse_id)
            groups[key].append(order)
        
        # Create batches
        batches = []
        batch_counter = 1
        
        for (from_wh, to_wh), group_orders in groups.items():
            # Sort by transfer date
            group_orders.sort(key=lambda o: o.transfer_date)
            
            # Create batch
            batch = OrderBatch(
                batch_id=f"BATCH-TO-{batch_counter:04d}",
                from_warehouse_id=from_wh,
                to_warehouse_id=to_wh,
                order_date=min(o.transfer_date for o in group_orders),
                expected_delivery_date=max(o.expected_arrival_date for o in group_orders)
            )
            
            # Aggregate materials
            for order in group_orders:
                if order.material_id in batch.materials:
                    batch.materials[order.material_id] += order.quantity
                else:
                    batch.materials[order.material_id] = order.quantity
                
                batch.total_transport_cost += order.transport_cost
                batch.original_order_ids.append(order.id)
            
            # Calculate freight savings
            batch = self._calculate_transfer_savings(batch, group_orders)
            
            batches.append(batch)
            batch_counter += 1
        
        return batches
    
    def _calculate_batch_savings(self,
                                batch: OrderBatch,
                                original_orders: List[PurchaseOrder]) -> OrderBatch:
        """
        Calculate cost savings from batching purchase orders
        
        Args:
            batch: Order batch
            original_orders: Original orders that were batched
        
        Returns:
            Updated batch with savings calculated
        
        TODO: SAVINGS CALCULATION ENHANCEMENTS
        1. Volume discount curves (non-linear)
        2. Vendor-specific discount structures
        3. Payment term discounts (early payment)
        4. Loyalty program benefits
        5. Seasonal discount optimization
        6. Contract volume commitments
        """
        
        vendor = self.vendors_dict.get(batch.vendor_id)
        
        if not vendor:
            return batch
        
        # Calculate bulk discount
        # TODO: Implement proper discount tiers from vendor data
        total_quantity = sum(batch.materials.values())
        
        # Simple tiered discount (TODO: make this vendor-specific)
        if total_quantity >= 1000:
            discount_pct = 0.10  # 10% for 1000+ units
        elif total_quantity >= 500:
            discount_pct = 0.05  # 5% for 500+ units
        elif total_quantity >= 200:
            discount_pct = 0.02  # 2% for 200+ units
        else:
            discount_pct = 0.0
        
        batch.bulk_discount = batch.total_material_cost * discount_pct
        
        # Calculate freight savings
        # Batching reduces per-unit transport cost due to economies of scale
        original_freight = sum(order.total_cost * 0.1 for order in original_orders)  # Assume 10% is freight
        
        # Batched freight is more efficient (TODO: use actual freight calculation)
        batched_freight = original_freight * 0.8  # 20% savings
        batch.freight_savings = original_freight - batched_freight
        
        # Net cost
        batch.net_cost = batch.total_material_cost - batch.bulk_discount
        
        # Reasoning
        batch.reasoning = (
            f"Batched {len(original_orders)} orders into single shipment. "
            f"Total quantity: {total_quantity} units across {len(batch.materials)} materials. "
            f"Bulk discount: ₹{batch.bulk_discount:,.0f} ({discount_pct*100:.0f}%). "
            f"Freight savings: ₹{batch.freight_savings:,.0f}. "
            f"Total savings: ₹{batch.bulk_discount + batch.freight_savings:,.0f}."
        )
        
        return batch
    
    def _calculate_transfer_savings(self,
                                   batch: OrderBatch,
                                   original_orders: List[TransferOrder]) -> OrderBatch:
        """
        Calculate cost savings from batching transfer orders
        
        Args:
            batch: Order batch
            original_orders: Original orders that were batched
        
        Returns:
            Updated batch with savings calculated
        
        TODO: TRANSFER SAVINGS ENHANCEMENTS
        1. Load factor optimization (full truck utilization)
        2. Backhaul optimization (return trip revenue)
        3. Multi-modal optimization (rail + truck)
        4. Carrier negotiation (volume discounts)
        5. Route optimization (shortest path)
        """
        
        # Original cost: sum of individual transfers
        original_cost = sum(order.transport_cost for order in original_orders)
        
        # Batched cost: single shipment with combined load
        # Savings come from:
        # 1. Single loading/unloading instead of multiple
        # 2. Better vehicle utilization
        # 3. Route optimization
        
        # Simple model: 30% savings from batching (TODO: use actual freight model)
        batched_cost = original_cost * 0.7
        batch.freight_savings = original_cost - batched_cost
        
        batch.total_transport_cost = batched_cost
        batch.net_cost = batched_cost
        
        # Reasoning
        total_quantity = sum(batch.materials.values())
        batch.reasoning = (
            f"Consolidated {len(original_orders)} transfers into single shipment. "
            f"Total quantity: {total_quantity} units across {len(batch.materials)} materials. "
            f"Original cost: ₹{original_cost:,.0f}, "
            f"Batched cost: ₹{batched_cost:,.0f}, "
            f"Savings: ₹{batch.freight_savings:,.0f} ({(batch.freight_savings/original_cost)*100:.1f}%)."
        )
        
        return batch
    
    def optimize_batch_timing(self,
                            pending_orders: List[PurchaseOrder],
                            urgency_threshold: int = 7) -> Tuple[List[PurchaseOrder], List[PurchaseOrder]]:
        """
        Decide which orders to batch now vs wait for more orders
        
        Args:
            pending_orders: Orders waiting to be placed
            urgency_threshold: Days until needed
        
        Returns:
            (urgent_orders, can_wait_orders)
        
        TODO: TIMING OPTIMIZATION
        1. Reinforcement learning for optimal wait time
        2. Demand forecasting integration
        3. Inventory cost vs batching savings tradeoff
        4. Stockout risk consideration
        5. Seasonal demand patterns
        """
        
        urgent = []
        can_wait = []
        
        now = datetime.now()
        
        for order in pending_orders:
            days_until_needed = (order.expected_delivery_date - now).days
            
            if days_until_needed <= urgency_threshold:
                urgent.append(order)
            else:
                can_wait.append(order)
        
        return urgent, can_wait
    
    def generate_batch_report(self, batches: List[OrderBatch]) -> str:
        """
        Generate a detailed batching report
        
        Args:
            batches: List of order batches
        
        Returns:
            Formatted report string
        
        TODO: REPORTING ENHANCEMENTS
        1. Visual charts (savings by vendor, by material)
        2. Historical comparison
        3. KPI tracking (average batch size, savings rate)
        4. Executive dashboard
        """
        
        if not batches:
            return "No batches created"
        
        report = "ORDER BATCHING REPORT\n"
        report += "=" * 100 + "\n\n"
        
        total_savings = sum(b.bulk_discount + b.freight_savings for b in batches)
        total_orders = sum(len(b.original_order_ids) for b in batches)
        
        report += f"Summary:\n"
        report += f"  Total batches: {len(batches)}\n"
        report += f"  Total orders batched: {total_orders}\n"
        report += f"  Total savings: ₹{total_savings:,.0f}\n"
        report += f"  Average savings per batch: ₹{total_savings/len(batches):,.0f}\n"
        report += "\n" + "=" * 100 + "\n\n"
        
        # Detail each batch
        for batch in batches:
            report += f"Batch ID: {batch.batch_id}\n"
            
            if batch.vendor_id:
                vendor = self.vendors_dict.get(batch.vendor_id)
                report += f"  Vendor: {vendor.name if vendor else batch.vendor_id}\n"
            
            if batch.from_warehouse_id:
                report += f"  From: {batch.from_warehouse_id} → To: {batch.to_warehouse_id}\n"
            
            report += f"  Materials: {len(batch.materials)}\n"
            report += f"  Total Quantity: {sum(batch.materials.values())} units\n"
            report += f"  Bulk Discount: ₹{batch.bulk_discount:,.0f}\n"
            report += f"  Freight Savings: ₹{batch.freight_savings:,.0f}\n"
            report += f"  Total Savings: ₹{batch.bulk_discount + batch.freight_savings:,.0f}\n"
            report += f"  Orders Combined: {len(batch.original_order_ids)}\n"
            report += f"  Expected Delivery: {batch.expected_delivery_date.strftime('%Y-%m-%d') if batch.expected_delivery_date else 'TBD'}\n"
            report += "\n"
        
        return report


# TODO: FUTURE ORDER BATCHER FEATURES
"""
PRODUCTION-READY ENHANCEMENTS:

1. ADVANCED BATCHING ALGORITHMS
   - Mixed Integer Programming (MIP) for optimal batching
   - Constraint Programming for complex rules
   - Genetic algorithms for large-scale optimization
   - Simulated annealing for local optima escape
   - Column generation for decomposition

2. DYNAMIC BATCHING
   - Real-time order accumulation
   - Event-driven batching (price changes, capacity)
   - Adaptive batch windows (learn from history)
   - Predictive batching (forecast future orders)
   - Rolling horizon optimization

3. MULTI-DIMENSIONAL OPTIMIZATION
   - Cost vs time vs risk tradeoffs
   - Carbon footprint minimization
   - Inventory carrying cost consideration
   - Opportunity cost of delayed orders
   - Service level maintenance

4. FREIGHT OPTIMIZATION
   - LTL (Less Than Truckload) optimization
   - FCL (Full Container Load) vs LCL
   - Multi-modal transport (truck + rail + ship)
   - Dynamic carrier selection
   - Real-time freight pricing
   - Load consolidation centers

5. VENDOR COLLABORATION
   - Vendor Managed Inventory (VMI)
   - Collaborative planning (CPFR)
   - Consignment stock optimization
   - Drop shipping integration
   - Cross-docking opportunities

6. ADVANCED ANALYTICS
   - Machine learning for batch size prediction
   - Demand pattern recognition
   - Seasonal adjustment algorithms
   - Anomaly detection (unusual orders)
   - What-if scenario analysis

7. INTEGRATION & AUTOMATION
   - ERP integration (SAP, Oracle)
   - TMS (Transportation Management System)
   - WMS (Warehouse Management System)
   - Automated carrier booking
   - Electronic Data Interchange (EDI)
"""


if __name__ == "__main__":
    """Test order batcher"""
    from src.core.data_factory import DataFactory
    
    print("Testing Order Batcher...")
    print("="*70)
    
    # Generate test data
    factory = DataFactory(seed=42)
    factory.generate_all()
    
    # Create sample purchase orders
    sample_orders = []
    
    for i in range(5):
        order = PurchaseOrder(
            id=f"PO-TEST-{i+1:04d}",
            material_id=factory.materials[i % 3].id,
            vendor_id=factory.vendors[0].id,  # Same vendor
            quantity=100 + i * 50,
            unit_price=10000,
            total_cost=1000000,
            order_date=datetime.now() + timedelta(days=i),
            expected_delivery_date=datetime.now() + timedelta(days=7+i),
            delivery_warehouse_id=factory.warehouses[0].id,  # Same warehouse
            status='Pending',
            reasoning='Test order'
        )
        sample_orders.append(order)
    
    # Create batcher
    batcher = OrderBatcher(
        vendors=factory.vendors,
        warehouses=factory.warehouses,
        materials=factory.materials
    )
    
    # Batch orders
    batches = batcher.batch_purchase_orders(sample_orders)
    
    # Generate report
    report = batcher.generate_batch_report(batches)
    print(report)
    
    print("\n✓ Order batcher test complete!")
