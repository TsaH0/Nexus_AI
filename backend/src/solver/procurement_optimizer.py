"""
Procurement Optimizer - Multi-Criteria Vendor Selection
Advanced vendor selection using landed cost, reliability, and risk-adjusted delivery
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config import *
from src.core.models import Vendor, Warehouse, Material, PurchaseOrder
from src.utils.geo_utils import haversine_distance, calculate_transport_cost, estimate_delivery_time


@dataclass
class VendorEvaluation:
    """Comprehensive vendor evaluation result"""
    vendor: Vendor
    material_id: str
    quantity: int
    
    # Cost components
    unit_price: float
    gst_amount: float
    transport_cost: float
    landed_cost: float  # Total cost per unit delivered
    
    # Time components
    base_delivery_days: int
    risk_adjusted_days: int  # Adjusted for reliability
    expected_delivery_date: datetime
    
    # Risk factors
    reliability_score: float  # 0-1
    risk_penalty: float  # Additional cost for unreliability
    
    # Scoring
    cost_score: float  # 0-1 (higher is better)
    time_score: float  # 0-1 (higher is better)
    reliability_score_normalized: float  # 0-1 (higher is better)
    weighted_score: float  # Final score
    
    # Reasoning
    reasoning: str
    warnings: List[str]
    
    def __lt__(self, other):
        """For sorting by weighted score"""
        return self.weighted_score > other.weighted_score  # Higher score is better


class ProcurementOptimizer:
    """
    Advanced procurement optimizer with multi-criteria decision making
    
    TODO: PRODUCTION ENHANCEMENTS
    1. Machine learning for vendor performance prediction
    2. Historical data analysis (past delivery performance)
    3. Real-time price monitoring and arbitrage detection
    4. Contract compliance checking (min order quantities, volumes)
    5. Vendor capacity constraints (can they handle the order?)
    6. Lead time prediction using ML (based on season, vendor, material)
    7. Quality defect rate consideration
    8. Financial health monitoring (vendor bankruptcy risk)
    9. Geopolitical risk assessment
    10. ESG scoring (Environmental, Social, Governance)
    11. Vendor relationship management (long-term partnerships)
    12. Automated RFQ (Request for Quote) generation
    """
    
    def __init__(self, 
                 vendors: List[Vendor],
                 warehouses: List[Warehouse],
                 materials: List[Material],
                 optimization_strategy: str = 'balanced'):
        """
        Initialize procurement optimizer
        
        Args:
            vendors: List of all vendors
            warehouses: List of all warehouses
            materials: List of all materials
            optimization_strategy: One of: 'balanced', 'cost_focused', 'rush', 'risk_averse'
        """
        self.vendors = vendors
        self.warehouses = warehouses
        self.materials = materials
        self.materials_dict = {m.id: m for m in materials}
        self.vendors_dict = {v.id: v for v in vendors}
        
        # Set optimization strategy
        valid_strategies = ['balanced', 'cost_focused', 'rush', 'risk_averse']
        if optimization_strategy not in valid_strategies:
            raise ValueError(f"Invalid strategy. Must be one of: {valid_strategies}")
        
        self.optimization_strategy = optimization_strategy
        self.weights = self._get_strategy_weights()
        
        # Performance tracking (TODO: load from database)
        self.vendor_performance_history = {}
    
    def _get_strategy_weights(self) -> Dict[str, float]:
        """
        Get scoring weights based on optimization strategy
        
        Returns:
            Dictionary with weights for cost, time, reliability
        
        TODO: STRATEGY ENHANCEMENTS
        1. Dynamic weights based on material criticality
        2. Time-of-day strategies (rush during emergencies)
        3. Seasonal strategies (monsoon = prioritize reliability)
        4. Budget-aware strategies (end of quarter = cost focus)
        5. Project-specific strategies (critical path items)
        6. Learning strategies (adapt based on outcomes)
        """
        
        if self.optimization_strategy == 'cost_focused':
            return {'cost': 0.70, 'time': 0.10, 'reliability': 0.20}
        elif self.optimization_strategy == 'rush':
            return {'cost': 0.15, 'time': 0.70, 'reliability': 0.15}
        elif self.optimization_strategy == 'risk_averse':
            return {'cost': 0.20, 'time': 0.20, 'reliability': 0.60}
        else:  # balanced
            return {'cost': 0.40, 'time': 0.30, 'reliability': 0.30}
    
    def find_capable_vendors(self, 
                           material_id: str,
                           quantity: int,
                           required_by_date: Optional[datetime] = None) -> List[Vendor]:
        """
        Find vendors that can supply the material
        
        Args:
            material_id: Material to source
            quantity: Quantity needed
            required_by_date: Deadline (if any)
        
        Returns:
            List of capable vendors
        
        TODO: VENDOR FILTERING ENHANCEMENTS
        1. Certification requirements (ISO, quality standards)
        2. Vendor pre-qualification status
        3. Blacklist/whitelist management
        4. Geographic restrictions (local content requirements)
        5. Capacity utilization (vendor may be overbooked)
        6. Payment terms compatibility
        7. Currency and forex risk
        8. Import/export compliance
        """
        
        capable = []
        
        for vendor in self.vendors:
            # Check if vendor supplies this material
            if material_id not in vendor.material_prices:
                continue
            
            # Check minimum order quantity (TODO: implement MOQ in Vendor model)
            # if quantity < vendor.moq.get(material_id, 0):
            #     continue
            
            # Check lead time vs deadline
            if required_by_date:
                # Estimate if vendor can deliver on time
                avg_lead_time = vendor.avg_lead_time_days
                estimated_delivery = datetime.now() + timedelta(days=avg_lead_time)
                
                if estimated_delivery > required_by_date:
                    continue
            
            # Check vendor reliability (TODO: more sophisticated filtering)
            # if vendor.reliability_score < 0.5:  # Below threshold
            #     continue
            
            capable.append(vendor)
        
        return capable
    
    def evaluate_vendor(self,
                       vendor: Vendor,
                       material_id: str,
                       quantity: int,
                       delivery_warehouse: Warehouse,
                       order_date: datetime,
                       urgency: str = 'normal') -> VendorEvaluation:
        """
        Comprehensive vendor evaluation with all cost and risk factors
        
        Args:
            vendor: Vendor to evaluate
            material_id: Material to procure
            quantity: Quantity needed
            delivery_warehouse: Destination warehouse
            order_date: Order placement date
            urgency: 'normal' or 'urgent'
        
        Returns:
            VendorEvaluation object
        
        TODO: EVALUATION ENHANCEMENTS
        1. Historical performance analysis (actual vs promised)
        2. Seasonal reliability adjustments (monsoon delays)
        3. Currency fluctuation risk
        4. Bulk discount calculation
        5. Payment term optimization (early payment discount)
        6. Quality defect rate consideration
        7. After-sales support quality
        8. Vendor innovation capability
        9. Sustainability metrics (carbon footprint)
        10. Social responsibility scoring
        """
        
        warnings = []
        
        # 1. COST CALCULATION
        unit_price = vendor.material_prices.get(material_id, 0)
        if unit_price == 0:
            warnings.append(f"Material {material_id} not available from {vendor.name}")
        
        subtotal = unit_price * quantity
        
        # GST calculation
        material = self.materials_dict.get(material_id)
        gst_rate = GST_RATES.get(material.category if material else 'Other', 0.18)  # Default 18%
        gst_amount = subtotal * gst_rate
        
        # Transport cost
        distance = haversine_distance(
            vendor.latitude, vendor.longitude,
            delivery_warehouse.latitude, delivery_warehouse.longitude
        )
        
        transport_cost = calculate_transport_cost(
            distance_km=distance,
            quantity=quantity,
            cost_per_km=TRANSPORT_COST_PER_KM,
            loading_cost=LOADING_UNLOADING_COST
        )
        
        # Landed cost per unit
        total_cost = subtotal + gst_amount + transport_cost
        landed_cost_per_unit = total_cost / quantity if quantity > 0 else float('inf')
        
        # 2. DELIVERY TIME CALCULATION
        base_lead_time = vendor.avg_lead_time_days
        
        # Adjust for distance (longer distance = more variability)
        distance_factor = 1.0 + (distance / 1000) * 0.1  # 10% more per 1000km
        
        # Adjust for urgency
        if urgency == 'urgent':
            base_lead_time = int(base_lead_time * 0.7)  # Express delivery
            transport_cost *= 1.5  # Express costs more
        
        # Risk-adjusted delivery time
        reliability = vendor.reliability_score
        risk_buffer_days = int(base_lead_time * (1 - reliability) * 0.5)  # Unreliable = longer buffer
        
        risk_adjusted_days = base_lead_time + risk_buffer_days
        expected_delivery = order_date + timedelta(days=risk_adjusted_days)
        
        # 3. RELIABILITY ASSESSMENT
        # Risk penalty: unreliable vendors cost more (opportunity cost of delays)
        # TODO: Use actual historical data for this
        risk_penalty_pct = (1 - reliability) * 0.2  # Up to 20% penalty
        risk_penalty_cost = total_cost * risk_penalty_pct
        
        # Warnings for low reliability
        if reliability < 0.7:
            warnings.append(f"Low reliability score: {reliability:.2f}")
        
        if risk_adjusted_days > base_lead_time * 1.5:
            warnings.append(f"High delivery risk: {risk_adjusted_days} days (base: {base_lead_time})")
        
        # 4. SCORING
        # Cost score: lower cost = higher score
        # Normalize against vendor pool (TODO: make this dynamic)
        cost_score = 1.0 / (1.0 + landed_cost_per_unit / 100000)  # Sigmoid-like
        
        # Time score: faster delivery = higher score
        time_score = 1.0 / (1.0 + risk_adjusted_days / 7.0)  # Normalize to weeks
        
        # Reliability score: already 0-1
        reliability_score_normalized = reliability
        
        # Weighted score
        weighted_score = (
            self.weights['cost'] * cost_score +
            self.weights['time'] * time_score +
            self.weights['reliability'] * reliability_score_normalized
        )
        
        # 5. REASONING
        reasoning = (
            f"Vendor: {vendor.name} | "
            f"Price: ₹{unit_price:,.0f}/unit | "
            f"GST: ₹{gst_amount:,.0f} ({gst_rate*100:.0f}%) | "
            f"Transport: ₹{transport_cost:,.0f} ({distance:.0f}km) | "
            f"Landed: ₹{landed_cost_per_unit:,.0f}/unit | "
            f"ETA: {risk_adjusted_days} days | "
            f"Reliability: {reliability:.2f} | "
            f"Score: {weighted_score:.3f}"
        )
        
        return VendorEvaluation(
            vendor=vendor,
            material_id=material_id,
            quantity=quantity,
            unit_price=unit_price,
            gst_amount=gst_amount,
            transport_cost=transport_cost,
            landed_cost=landed_cost_per_unit,
            base_delivery_days=base_lead_time,
            risk_adjusted_days=risk_adjusted_days,
            expected_delivery_date=expected_delivery,
            reliability_score=reliability,
            risk_penalty=risk_penalty_cost,
            cost_score=cost_score,
            time_score=time_score,
            reliability_score_normalized=reliability_score_normalized,
            weighted_score=weighted_score,
            reasoning=reasoning,
            warnings=warnings
        )
    
    def select_optimal_vendor(self,
                            material_id: str,
                            quantity: int,
                            delivery_warehouse: Warehouse,
                            order_date: datetime,
                            required_by_date: Optional[datetime] = None,
                            urgency: str = 'normal') -> Optional[VendorEvaluation]:
        """
        Select the optimal vendor using multi-criteria optimization
        
        Args:
            material_id: Material to procure
            quantity: Quantity needed
            delivery_warehouse: Destination
            order_date: Order placement date
            required_by_date: Deadline (if any)
            urgency: 'normal' or 'urgent'
        
        Returns:
            Best VendorEvaluation or None if no suitable vendor
        
        TODO: SELECTION ENHANCEMENTS
        1. Multi-vendor splitting (diversify risk)
        2. Contract-based selection (preferred vendors)
        3. Vendor rotation policy (fairness)
        4. Negotiation automation (bid optimization)
        5. Consortium procurement (join with other buyers)
        6. Dynamic pricing (real-time quotes)
        7. Auction mechanisms (reverse auction)
        8. Long-term agreement optimization
        """
        
        # Find capable vendors
        capable_vendors = self.find_capable_vendors(
            material_id=material_id,
            quantity=quantity,
            required_by_date=required_by_date
        )
        
        if not capable_vendors:
            return None
        
        # Evaluate all capable vendors
        evaluations = []
        
        for vendor in capable_vendors:
            evaluation = self.evaluate_vendor(
                vendor=vendor,
                material_id=material_id,
                quantity=quantity,
                delivery_warehouse=delivery_warehouse,
                order_date=order_date,
                urgency=urgency
            )
            
            # Filter by deadline
            if required_by_date and evaluation.expected_delivery_date > required_by_date:
                continue
            
            evaluations.append(evaluation)
        
        if not evaluations:
            return None
        
        # Sort by weighted score (descending)
        evaluations.sort()
        
        # Return best option
        return evaluations[0]
    
    def create_purchase_order(self,
                            vendor_evaluation: VendorEvaluation,
                            order_id: str,
                            order_date: datetime,
                            delivery_warehouse: Warehouse) -> PurchaseOrder:
        """
        Create a purchase order from vendor evaluation
        
        Args:
            vendor_evaluation: Selected vendor evaluation
            order_id: Unique order ID
            order_date: Order date
            delivery_warehouse: Destination warehouse
        
        Returns:
            PurchaseOrder object
        
        TODO: PURCHASE ORDER ENHANCEMENTS
        1. Automated PO generation (PDF, EDI, API)
        2. E-signature integration
        3. Terms and conditions templating
        4. Multi-currency support
        5. Payment schedule automation
        6. Delivery milestone tracking
        7. Quality inspection checkpoints
        8. Penalty clause automation (late delivery)
        9. Integration with ERP (SAP, Oracle)
        10. Blockchain for immutability
        """
        
        vendor = vendor_evaluation.vendor
        
        # Calculate total order value
        subtotal = vendor_evaluation.unit_price * vendor_evaluation.quantity
        total_cost = subtotal + vendor_evaluation.gst_amount + vendor_evaluation.transport_cost
        
        # Enhanced reasoning with alternatives
        reasoning = (
            f"Selected {vendor.name} for {vendor_evaluation.quantity} units. "
            f"Landed cost: ₹{vendor_evaluation.landed_cost:,.0f}/unit. "
            f"Expected delivery: {vendor_evaluation.expected_delivery_date.strftime('%Y-%m-%d')}. "
            f"Reliability: {vendor_evaluation.reliability_score:.2f}. "
            f"Optimization strategy: {self.optimization_strategy}. "
            f"Score: {vendor_evaluation.weighted_score:.3f}."
        )
        
        if vendor_evaluation.warnings:
            reasoning += f" ⚠️ Warnings: {'; '.join(vendor_evaluation.warnings)}"
        
        purchase_order = PurchaseOrder(
            id=order_id,
            material_id=vendor_evaluation.material_id,
            vendor_id=vendor.id,
            quantity=vendor_evaluation.quantity,
            unit_price=vendor_evaluation.unit_price,
            total_cost=total_cost,
            order_date=order_date,
            expected_delivery_date=vendor_evaluation.expected_delivery_date,
            delivery_warehouse_id=delivery_warehouse.id,
            status='Placed',
            reasoning=reasoning
        )
        
        return purchase_order
    
    def optimize_multi_material_procurement(self,
                                          demands: Dict[str, int],
                                          delivery_warehouse: Warehouse,
                                          order_date: datetime) -> List[VendorEvaluation]:
        """
        Optimize procurement for multiple materials
        
        Args:
            demands: Dictionary of {material_id: quantity}
            delivery_warehouse: Destination
            order_date: Order date
        
        Returns:
            List of optimal vendor evaluations
        
        TODO: MULTI-MATERIAL OPTIMIZATION
        1. Vendor consolidation (same vendor for multiple materials)
        2. Freight consolidation (combine shipments)
        3. Volume discount optimization
        4. Cross-material negotiation
        5. Portfolio optimization (minimize total cost + risk)
        """
        
        optimal_selections = []
        
        for material_id, quantity in demands.items():
            vendor_eval = self.select_optimal_vendor(
                material_id=material_id,
                quantity=quantity,
                delivery_warehouse=delivery_warehouse,
                order_date=order_date
            )
            
            if vendor_eval:
                optimal_selections.append(vendor_eval)
        
        # TODO: Apply vendor consolidation optimization
        # If multiple materials can come from same vendor, consolidate
        
        return optimal_selections
    
    def compare_vendors(self, 
                       evaluations: List[VendorEvaluation],
                       top_n: int = 5) -> str:
        """
        Generate comparison report for vendor selection
        
        Args:
            evaluations: List of vendor evaluations
            top_n: Number of top vendors to show
        
        Returns:
            Formatted comparison report
        
        TODO: COMPARISON ENHANCEMENTS
        1. Visual charts (cost vs reliability)
        2. Radar plots (multi-criteria comparison)
        3. Historical performance overlay
        4. Risk heat maps
        5. Interactive dashboard
        """
        
        if not evaluations:
            return "No vendors available for comparison"
        
        # Sort by score
        sorted_evals = sorted(evaluations)[:top_n]
        
        report = "VENDOR COMPARISON REPORT\n"
        report += "=" * 100 + "\n"
        report += f"Optimization Strategy: {self.optimization_strategy.upper()}\n"
        report += f"Weights: Cost={self.weights['cost']:.0%}, Time={self.weights['time']:.0%}, Reliability={self.weights['reliability']:.0%}\n"
        report += "=" * 100 + "\n\n"
        
        report += f"{'Rank':<6} {'Vendor':<20} {'Price':<12} {'Transport':<12} {'Landed':<12} {'Days':<6} {'Rel':<6} {'Score':<8}\n"
        report += "-" * 100 + "\n"
        
        for i, eval in enumerate(sorted_evals, 1):
            report += (
                f"{i:<6} "
                f"{eval.vendor.name[:19]:<20} "
                f"₹{eval.unit_price:>10,.0f} "
                f"₹{eval.transport_cost:>10,.0f} "
                f"₹{eval.landed_cost:>10,.0f} "
                f"{eval.risk_adjusted_days:<6} "
                f"{eval.reliability_score:>5.2f} "
                f"{eval.weighted_score:>7.3f}\n"
            )
        
        report += "\n" + "=" * 100 + "\n"
        report += f"✓ SELECTED: {sorted_evals[0].vendor.name} (Score: {sorted_evals[0].weighted_score:.3f})\n"
        
        if sorted_evals[0].warnings:
            report += f"⚠️ Warnings: {', '.join(sorted_evals[0].warnings)}\n"
        
        return report


# TODO: FUTURE PROCUREMENT OPTIMIZER FEATURES
"""
PRODUCTION-READY ENHANCEMENTS:

1. ADVANCED VENDOR SELECTION
   - Multi-objective optimization (Pareto frontier)
   - Machine learning for vendor performance prediction
   - Game theory for negotiation optimization
   - Portfolio theory for vendor diversification
   - Real options analysis (flexible contracts)

2. PRICE INTELLIGENCE
   - Market price monitoring (commodity exchanges)
   - Price forecasting using time series
   - Arbitrage detection
   - Dynamic pricing negotiation
   - Futures and hedging strategies

3. CONTRACT MANAGEMENT
   - Long-term agreement optimization
   - Volume commitment planning
   - Rebate and incentive tracking
   - Contract renewal optimization
   - SLA (Service Level Agreement) management

4. RISK MANAGEMENT
   - Supply chain disruption modeling
   - Vendor financial health monitoring
   - Geopolitical risk assessment
   - Natural disaster impact analysis
   - Pandemic preparedness planning

5. SUSTAINABILITY
   - Carbon footprint tracking
   - Circular economy sourcing
   - Ethical supply chain verification
   - ESG scoring integration
   - Green procurement certification

6. AUTOMATION
   - RFQ automation (Request for Quote)
   - Reverse auction implementation
   - Auto-approval workflows
   - Exception-based management
   - Cognitive procurement (AI agents)

7. COLLABORATION
   - Supplier portal integration
   - Real-time quote exchange
   - Collaborative forecasting
   - Joint innovation programs
   - Vendor development initiatives
"""


if __name__ == "__main__":
    """Test procurement optimizer"""
    from src.core.data_factory import DataFactory
    
    print("Testing Procurement Optimizer...")
    print("="*70)
    
    # Generate test data
    factory = DataFactory(seed=42)
    factory.generate_all()
    
    # Test different strategies
    strategies = ['balanced', 'cost_focused', 'rush', 'risk_averse']
    
    test_material = factory.materials[0].id
    test_warehouse = factory.warehouses[0]
    
    for strategy in strategies:
        print(f"\n{'='*70}")
        print(f"TESTING STRATEGY: {strategy.upper()}")
        print(f"{'='*70}")
        
        optimizer = ProcurementOptimizer(
            vendors=factory.vendors,
            warehouses=factory.warehouses,
            materials=factory.materials,
            optimization_strategy=strategy
        )
        
        # Find optimal vendor
        best_vendor = optimizer.select_optimal_vendor(
            material_id=test_material,
            quantity=100,
            delivery_warehouse=test_warehouse,
            order_date=datetime.now()
        )
        
        if best_vendor:
            print(f"\n✓ Selected: {best_vendor.vendor.name}")
            print(f"  Landed Cost: ₹{best_vendor.landed_cost:,.0f}/unit")
            print(f"  Delivery: {best_vendor.risk_adjusted_days} days")
            print(f"  Reliability: {best_vendor.reliability_score:.2f}")
            print(f"  Score: {best_vendor.weighted_score:.3f}")
        else:
            print("\n✗ No suitable vendor found")
    
    print("\n✓ Procurement optimizer test complete!")
