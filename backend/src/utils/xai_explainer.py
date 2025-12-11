"""
Explainable AI (XAI) Module
Generates human-readable explanations for system decisions
"""

from typing import Dict, List, Any
import src.config as config
from src.core.models import ActionPlan


class XAIExplainer:
    """Generates explanations for NEXUS decisions"""
    
    @staticmethod
    def explain_vendor_selection(
        vendor_name: str,
        landed_cost: float,
        eta_days: int,
        reliability: float,
        alternatives: List[Dict],
        strategy: str = "balanced"
        ) -> str:
        """
        Explain why a particular vendor was selected
        
        Args:
            vendor_name: Selected vendor
            landed_cost: Total delivered cost
            eta_days: Estimated delivery time
            reliability: Vendor reliability score
            alternatives: List of rejected vendors with their scores
            strategy: Optimization strategy used
        
        Returns:
            Human-readable explanation
        """
        weights = config.OPTIMIZATION_STRATEGIES[strategy]
        
        explanation = f"Selected '{vendor_name}' using '{strategy}' strategy.\n"
        explanation += f"  • Landed Cost: ₹{landed_cost:,.0f}\n"
        explanation += f"  • Expected Delivery: {eta_days} days\n"
        explanation += f"  • Reliability: {reliability:.1%}\n"
        
        if alternatives:
            explanation += f"\nAlternatives considered:\n"
            for alt in alternatives[:3]:  # Show top 3 alternatives
                reason = alt.get('rejection_reason', 'Lower overall score')
                explanation += f"  • {alt['vendor']}: {reason}\n"
        
        # Strategy explanation
        if strategy == "rush":
            explanation += "\nPrioritized delivery speed over cost due to urgent requirement."
        elif strategy == "cost_focused":
            explanation += "\nPrioritized cost savings as timeline allows flexibility."
        elif strategy == "risk_averse":
            explanation += "\nPrioritized vendor reliability to minimize delivery risk."
        
        return explanation
    
    @staticmethod
    def explain_transfer_decision(from_warehouse: str,
                                  to_warehouse: str,
                                  material_name: str,
                                  quantity: int,
                                  transfer_cost: float,
                                  distance_km: float,
                                  vs_new_procurement_cost: float = None) -> str:
        """
        Explain why an inter-warehouse transfer was chosen
        
        Args:
            from_warehouse: Source warehouse
            to_warehouse: Destination warehouse
            material_name: Material being transferred
            quantity: Quantity transferred
            transfer_cost: Cost of transfer
            distance_km: Distance
            vs_new_procurement_cost: Alternative procurement cost (if available)
        
        Returns:
            Explanation string
        """
        explanation = f"Transfer {quantity} units of '{material_name}' from {from_warehouse} to {to_warehouse}.\n"
        explanation += f"  • Distance: {distance_km:.1f} km\n"
        explanation += f"  • Transfer Cost: ₹{transfer_cost:,.0f}\n"
        
        if vs_new_procurement_cost:
            savings = vs_new_procurement_cost - transfer_cost
            savings_pct = (savings / vs_new_procurement_cost) * 100
            explanation += f"  • Savings vs New Purchase: ₹{savings:,.0f} ({savings_pct:.1f}%)\n"
            explanation += "\nReason: Utilizing existing inventory is more cost-effective than new procurement."
        else:
            explanation += "\nReason: Optimizing inventory distribution across network."
        
        return explanation
    
    @staticmethod
    def explain_project_hold(project_name: str,
                            reason: str,
                            impact: str,
                            recommended_action: str) -> str:
        """
        Explain why a project was put on hold
        
        Args:
            project_name: Project identifier
            reason: Primary reason for hold
            impact: Impact description
            recommended_action: What to do next
        
        Returns:
            Explanation string
        """
        explanation = f"⚠️  Project '{project_name}' PLACED ON HOLD\n"
        explanation += f"\nReason: {reason}\n"
        explanation += f"Impact: {impact}\n"
        explanation += f"Recommended Action: {recommended_action}\n"
        
        return explanation
    
    @staticmethod
    def explain_demand_forecast(material_name: str,
                               region: str,
                               capex_demand: int,
                               opex_demand: int,
                               safety_buffer: int,
                               total: int,
                               factors: Dict[str, Any]) -> str:
        """
        Explain how demand forecast was calculated
        
        Args:
            material_name: Material being forecasted
            region: Region
            capex_demand: Capital project demand
            opex_demand: Operational/maintenance demand
            safety_buffer: Safety stock buffer
            total: Total forecasted demand
            factors: Dictionary of adjustment factors (weather, sentiment, etc.)
        
        Returns:
            Explanation string
        """
        explanation = f"Demand Forecast for '{material_name}' in {region} region:\n"
        explanation += f"  • CapEx Demand (Projects): {capex_demand} units\n"
        explanation += f"  • OpEx Demand (Maintenance): {opex_demand} units\n"
        explanation += f"  • Safety Buffer: {safety_buffer} units\n"
        explanation += f"  • TOTAL FORECAST: {total} units\n"
        
        if factors:
            explanation += "\nAdjustment Factors Applied:\n"
            if 'weather' in factors:
                explanation += f"  • Weather Impact: {factors['weather']:.1%} multiplier\n"
            if 'sentiment' in factors:
                explanation += f"  • Market Sentiment: {factors['sentiment']}\n"
            if 'seasonality' in factors:
                explanation += f"  • Seasonal Pattern: {factors['seasonality']}\n"
        
        return explanation
    
    @staticmethod
    def explain_no_action(material_name: str, 
                         region: str,
                         current_stock: int,
                         required: int) -> str:
        """
        Explain why no procurement/transfer is needed
        
        Args:
            material_name: Material
            region: Region
            current_stock: Current inventory
            required: Required quantity
        
        Returns:
            Explanation string
        """
        excess = current_stock - required
        explanation = f"No action needed for '{material_name}' in {region}.\n"
        explanation += f"  • Current Stock: {current_stock} units\n"
        explanation += f"  • Required: {required} units\n"
        explanation += f"  • Excess: {excess} units\n"
        explanation += "\nReason: Sufficient inventory available."
        
        return explanation
    
    @staticmethod
    def explain_shelf_life_hold(material_name: str,
                               shelf_life_days: int,
                               project_start_days: int) -> str:
        """
        Explain why procurement is held due to shelf life
        
        Args:
            material_name: Material
            shelf_life_days: Shelf life in days
            project_start_days: Days until project needs material
        
        Returns:
            Explanation string
        """
        explanation = f"⚠️  Procurement HOLD for '{material_name}'\n"
        explanation += f"  • Material Shelf Life: {shelf_life_days} days\n"
        explanation += f"  • Project Start: {project_start_days} days from now\n"
        explanation += f"  • Risk: Material will expire before use\n"
        explanation += f"\nRecommendation: Schedule procurement {project_start_days - shelf_life_days + 30} days from now."
        
        return explanation
    
    @staticmethod
    def format_action_summary(action_plan: 'ActionPlan') -> str:
        """
        Create a formatted summary of the daily action plan
        
        Args:
            action_plan: ActionPlan object
        
        Returns:
            Formatted summary string
        """
        summary = f"\n{'='*70}\n"
        summary += f"ACTION PLAN - {action_plan.date.strftime('%Y-%m-%d')} - {action_plan.region} Region\n"
        summary += f"{'='*70}\n\n"
        
        # Purchase Orders
        if action_plan.purchase_orders:
            summary += f"📦 PURCHASE ORDERS ({len(action_plan.purchase_orders)}):\n"
            for po in action_plan.purchase_orders:
                summary += f"  • {po.id}: {po.quantity} units from {po.vendor_id}\n"
                summary += f"    Cost: ₹{po.landed_cost:,.0f} | ETA: {po.expected_delivery_date.strftime('%Y-%m-%d')}\n"
            summary += f"\n  Total Procurement: ₹{action_plan.total_procurement_cost:,.0f}\n\n"
        else:
            summary += "📦 No purchase orders today.\n\n"
        
        # Transfers
        if action_plan.transfer_orders:
            summary += f"🚚 TRANSFER ORDERS ({len(action_plan.transfer_orders)}):\n"
            for to in action_plan.transfer_orders:
                summary += f"  • {to.id}: {to.quantity} units | {to.from_warehouse_id} → {to.to_warehouse_id}\n"
                summary += f"    Cost: ₹{to.transport_cost:,.0f} | Distance: {to.distance_km:.1f} km\n"
            summary += f"\n  Total Transfer Cost: ₹{action_plan.total_transfer_cost:,.0f}\n\n"
        else:
            summary += "🚚 No transfers today.\n\n"
        
        # Holds
        if action_plan.projects_on_hold:
            summary += f"⚠️  PROJECTS ON HOLD ({len(action_plan.projects_on_hold)}):\n"
            for proj_id in action_plan.projects_on_hold:
                summary += f"  • {proj_id}\n"
            summary += "\n"
        
        # Alerts
        if action_plan.alerts:
            summary += f"🔔 ALERTS & WARNINGS:\n"
            for alert in action_plan.alerts:
                summary += f"  • {alert}\n"
            summary += "\n"
        
        summary += f"{'='*70}\n"
        
        return summary
