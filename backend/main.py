"""
NEXUS Main Orchestrator - The Sentient Supply Chain Brain
Daily simulation loop coordinating all modules for autonomous supply chain management
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.config import *
from src.core.models import ActionPlan, PurchaseOrder, TransferOrder, ProjectHold
from src.core.data_factory import DataFactory
from src.core.bom_calculator import BOMCalculator
from src.intelligence.weather_service import WeatherService
from src.intelligence.sentinel_agent import SentinelAgent
from src.forecasting.demand_engine import DemandEngine
from src.solver.inventory_reconciler import InventoryReconciler
from src.solver.procurement_optimizer import ProcurementOptimizer
from src.solver.order_batcher import OrderBatcher
from src.utils.xai_explainer import XAIExplainer
from src.utils.logger import setup_logger, ProgressTracker


class NexusOrchestrator:
    """
    Main orchestrator coordinating all NEXUS modules.
    
    Manages the daily supply chain simulation loop, coordinating:
    - Demand forecasting (CapEx + OpEx)
    - Inventory reconciliation (transfer-first logic)
    - Procurement optimization
    - Order batching
    - Action plan generation
    """
    
    def __init__(self, 
                 simulation_start_date: Optional[datetime] = None,
                 simulation_days: int = 30,
                 optimization_strategy: str = 'balanced'):
        """
        Initialize NEXUS orchestrator
        
        Args:
            simulation_start_date: Start date for simulation (None = today)
            simulation_days: Number of days to simulate
            optimization_strategy: Procurement strategy ('balanced', 'cost_focused', 'rush', 'risk_averse')
        """
        
        self.logger = setup_logger('nexus_orchestrator')
        self.simulation_start_date = simulation_start_date or datetime.now()
        self.simulation_days = simulation_days
        self.optimization_strategy = optimization_strategy
        
        self.logger.info("="*70)
        self.logger.info("NEXUS Orchestrator Initializing...")
        self.logger.info("="*70)
        
        try:
            # Initialize data factory
            self.logger.info("Loading Digital Twin data...")
            self.data_factory = DataFactory(seed=42)
            self.data_factory.generate_all()
            
            # Initialize components
            self.logger.info("Initializing components...")
            self._initialize_components()
            
            # State tracking
            self.current_date = self.simulation_start_date
            self.action_plans = []
            self.execution_log = []
            
            self.logger.info("✓ NEXUS Orchestrator initialized")
            self.logger.info("")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize NEXUS: {e}")
            raise
    
    def _initialize_components(self):
        """Initialize all NEXUS components"""
        
        # Core calculators
        self.bom_calculator = BOMCalculator()
        
        # Intelligence layer
        self.weather_service = WeatherService()
        self.sentinel_agent = SentinelAgent()
        
        # Forecasting engine
        self.demand_engine = DemandEngine(
            projects=self.data_factory.projects,
            bom_calculator=self.bom_calculator,
            weather_service=self.weather_service,
            sentinel_agent=self.sentinel_agent
        )
        
        # Solver modules
        self.inventory_reconciler = InventoryReconciler(
            warehouses=self.data_factory.warehouses,
            materials=self.data_factory.materials
        )
        
        self.procurement_optimizer = ProcurementOptimizer(
            vendors=self.data_factory.vendors,
            warehouses=self.data_factory.warehouses,
            materials=self.data_factory.materials,
            optimization_strategy=self.optimization_strategy
        )
        
        self.order_batcher = OrderBatcher(
            vendors=self.data_factory.vendors,
            warehouses=self.data_factory.warehouses,
            materials=self.data_factory.materials
        )
        
        # Explainability
        self.xai_explainer = XAIExplainer()
        
        self.logger.info("  ✓ Core calculators initialized")
        self.logger.info("  ✓ Intelligence layer initialized")
        self.logger.info("  ✓ Forecasting engine initialized")
        self.logger.info("  ✓ Solver modules initialized")
    
    def run_daily_cycle(self, date: datetime) -> ActionPlan:
        """
        Execute one day of supply chain orchestration.
        
        Args:
            date: Date to process
        
        Returns:
            ActionPlan for the day
        """
        
        self.logger.info(f"Processing: {date.strftime('%Y-%m-%d')}")
        self.logger.info("-" * 70)
        
        try:
            # Step 1: Generate demand forecast
            self.logger.info("1. Generating demand forecast...")
            forecasts = self.demand_engine.generate_forecast_for_all_projects(
                forecast_date=date,
                horizon_days=30
            )
            self.logger.info(f"   ✓ Generated {len(forecasts)} demand forecasts")
            
            # Step 2: Aggregate demand by material and warehouse
            self.logger.info("2. Aggregating material requirements...")
            material_demands = self._aggregate_demands(forecasts)
            self.logger.info(f"   ✓ {len(material_demands)} materials needed")
            
            # Step 3: Reconcile inventory (transfer-first)
            self.logger.info("3. Reconciling inventory (transfer-first)...")
            transfer_orders, procurement_needs = self._reconcile_inventory(
                material_demands, date
            )
            self.logger.info(f"   ✓ {len(transfer_orders)} transfers, {len(procurement_needs)} to procure")
            
            # Step 4: Optimize procurement
            self.logger.info("4. Optimizing vendor selection...")
            purchase_orders = self._optimize_procurement(procurement_needs, date)
            self.logger.info(f"   ✓ {len(purchase_orders)} purchase orders")
            
            # Step 5: Batch orders for economies of scale
            self.logger.info("5. Batching orders...")
            po_batches = self.order_batcher.batch_purchase_orders(purchase_orders)
            to_batches = self.order_batcher.batch_transfer_orders(transfer_orders)
            self.logger.info(f"   ✓ {len(po_batches)} PO batches, {len(to_batches)} TO batches")
        
            # Step 6: Check for project holds
            self.logger.info("6. Checking for project holds...")
            project_holds = self._check_project_holds(date)
            self.logger.info(f"   ✓ {len(project_holds)} projects on hold")
            
            # Step 7: Create action plan
            self.logger.info("7. Creating action plan...")
            action_plan = ActionPlan(
                date=date,
                purchase_orders=purchase_orders,
                transfer_orders=transfer_orders,
                project_holds=project_holds,
                total_procurement_cost=sum(po.total_cost for po in purchase_orders),
                total_transfer_cost=sum(to.transport_cost for to in transfer_orders),
                materials_to_procure=len(set(po.material_id for po in purchase_orders)),
                reasoning=self._generate_daily_reasoning(
                    forecasts, transfer_orders, purchase_orders, project_holds
                )
            )
            
            self.logger.info(f"   ✓ Action plan created")
            self.logger.info(f"   • Procurement: ₹{action_plan.total_procurement_cost:,.0f}")
            self.logger.info(f"   • Transfers: ₹{action_plan.total_transfer_cost:,.0f}")
            self.logger.info("")
            
            return action_plan
            
        except Exception as e:
            self.logger.error(f"Error processing day {date.strftime('%Y-%m-%d')}: {e}")
            # Return empty action plan on error
            return ActionPlan(
                date=date,
                reasoning=f"Error during processing: {str(e)}"
            )
    
    def _aggregate_demands(self, forecasts) -> Dict[Tuple[str, str], int]:
        """
        Aggregate material demands by (material_id, warehouse_id)
        
        Returns:
            Dictionary of {(material_id, warehouse_id): quantity}
        """
        
        demands = {}
        
        for forecast in forecasts:
            for material_id, qty in forecast.capex_demand.items():
                # Find nearest warehouse to project
                project = next(
                    (p for p in self.data_factory.projects if p.id == forecast.project_id),
                    None
                )
                
                if project:
                    # TODO: Use actual project-to-warehouse mapping
                    warehouse = self.data_factory.warehouses[0]  # Simplified
                    
                    key = (material_id, warehouse.id)
                    demands[key] = demands.get(key, 0) + qty
            
            for material_id, qty in forecast.opex_demand.items():
                # Distribute OpEx demand across warehouses
                # TODO: Use actual regional distribution
                warehouse = self.data_factory.warehouses[0]
                
                key = (material_id, warehouse.id)
                demands[key] = demands.get(key, 0) + qty
        
        return demands
    
    def _reconcile_inventory(self,
                            material_demands: Dict[Tuple[str, str], int],
                            date: datetime) -> Tuple[List[TransferOrder], Dict]:
        """
        Reconcile inventory using transfer-first logic
        
        Returns:
            (transfer_orders, remaining_procurement_needs)
        """
        
        transfer_orders = []
        procurement_needs = {}
        order_counter = 1
        
        for (material_id, warehouse_id), quantity in material_demands.items():
            # Find warehouse
            warehouse = next(
                (w for w in self.data_factory.warehouses if w.id == warehouse_id),
                None
            )
            
            if not warehouse:
                continue
            
            # Reconcile demand
            decision = self.inventory_reconciler.reconcile_demand(
                material_id=material_id,
                required_quantity=quantity,
                destination_warehouse=warehouse
            )
            
            if decision['decision'] == 'TRANSFER' and decision['transfer_option']:
                # Create transfer order
                transfer_order = self.inventory_reconciler.create_transfer_order(
                    transfer_option=decision['transfer_option'],
                    order_id=f"TO-{date.strftime('%Y%m%d')}-{order_counter:04d}",
                    order_date=date
                )
                transfer_orders.append(transfer_order)
                order_counter += 1
            
            # Track procurement needs
            if decision['procurement_quantity'] > 0:
                procurement_needs[(material_id, warehouse_id)] = decision['procurement_quantity']
        
        return transfer_orders, procurement_needs
    
    def _optimize_procurement(self,
                             procurement_needs: Dict,
                             date: datetime) -> List[PurchaseOrder]:
        """
        Optimize vendor selection for procurement needs
        
        Returns:
            List of purchase orders
        """
        
        purchase_orders = []
        order_counter = 1
        
        for (material_id, warehouse_id), quantity in procurement_needs.items():
            # Find warehouse
            warehouse = next(
                (w for w in self.data_factory.warehouses if w.id == warehouse_id),
                None
            )
            
            if not warehouse:
                continue
            
            # Select optimal vendor
            vendor_eval = self.procurement_optimizer.select_optimal_vendor(
                material_id=material_id,
                quantity=quantity,
                delivery_warehouse=warehouse,
                order_date=date
            )
            
            if vendor_eval:
                # Create purchase order
                purchase_order = self.procurement_optimizer.create_purchase_order(
                    vendor_evaluation=vendor_eval,
                    order_id=f"PO-{date.strftime('%Y%m%d')}-{order_counter:04d}",
                    order_date=date,
                    delivery_warehouse=warehouse
                )
                purchase_orders.append(purchase_order)
                order_counter += 1
        
        return purchase_orders
    
    def _check_project_holds(self, date: datetime) -> List[ProjectHold]:
        """
        Check which projects should be held due to weather/RoW
        
        Returns:
            List of project holds
        """
        
        project_holds = []
        
        for project in self.data_factory.projects:
            # Check weather
            weather = self.weather_service.get_weather_for_location(
                project.latitude, project.longitude, date
            )
            
            if weather:
                viability = self.weather_service.assess_construction_viability(
                    project.latitude, project.longitude, date
                )
                
                if not viability['can_work']:
                    hold = ProjectHold(
                        project_id=project.id,
                        hold_reason='Weather',
                        hold_date=date,
                        expected_resume_date=date + timedelta(days=viability['delay_days']),
                        impact_description=viability['reasoning']
                    )
                    project_holds.append(hold)
                    continue
            
            # Check RoW
            row_status = self.sentinel_agent.check_row_status(
                project, date
            )
            
            if row_status['risk_level'] in ['High', 'Critical']:
                hold = ProjectHold(
                    project_id=project.id,
                    hold_reason='RoW',
                    hold_date=date,
                    expected_resume_date=date + timedelta(days=row_status.get('blocked_days', 30)),
                    impact_description=row_status.get('recommended_action', 'Hold due to RoW risk')
                )
                project_holds.append(hold)
        
        return project_holds
    
    def _generate_daily_reasoning(self,
                                 forecasts,
                                 transfer_orders,
                                 purchase_orders,
                                 project_holds) -> str:
        """Generate summary reasoning for the day"""
        
        reasoning_parts = []
        
        # Demand summary
        total_materials = sum(
            len(f.capex_demand) + len(f.opex_demand) 
            for f in forecasts
        )
        reasoning_parts.append(f"Processed {len(forecasts)} projects requiring {total_materials} material types")
        
        # Procurement summary
        if purchase_orders:
            total_cost = sum(po.total_cost for po in purchase_orders)
            reasoning_parts.append(f"Procurement: {len(purchase_orders)} orders, ₹{total_cost:,.0f}")
        
        # Transfer summary
        if transfer_orders:
            total_cost = sum(to.transport_cost for to in transfer_orders)
            reasoning_parts.append(f"Transfers: {len(transfer_orders)} orders, ₹{total_cost:,.0f}")
        
        # Holds summary
        if project_holds:
            reasoning_parts.append(f"⚠️ {len(project_holds)} projects on hold")
        
        return " | ".join(reasoning_parts)
    
    def run_simulation(self):
        """Run full multi-day simulation."""
        
        self.logger.info("="*70)
        self.logger.info(f"NEXUS Simulation: {self.simulation_days} days")
        self.logger.info(f"Strategy: {self.optimization_strategy}")
        self.logger.info(f"Start Date: {self.simulation_start_date.strftime('%Y-%m-%d')}")
        self.logger.info("="*70)
        self.logger.info("")
        
        progress = ProgressTracker(self.simulation_days, "Simulating days")
        
        for day in range(self.simulation_days):
            current_date = self.simulation_start_date + timedelta(days=day)
            
            try:
                # Run daily cycle
                action_plan = self.run_daily_cycle(current_date)
                self.action_plans.append(action_plan)
                
                # Save action plan
                self._save_action_plan(action_plan)
            except Exception as e:
                self.logger.error(f"Error on day {day}: {e}")
            
            progress.update(1)
        
        progress.complete()
        
        self.logger.info("")
        self.logger.info("="*70)
        self.logger.info("Simulation Complete!")
        self.logger.info("="*70)
        
        # Generate final report
        self._generate_summary_report()
    
    def _save_action_plan(self, action_plan: ActionPlan):
        """Save action plan to JSON file"""
        
        output_dir = os.path.join(DATA_DIR, "outputs", "action_plans")
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"action_plan_{action_plan.date.strftime('%Y%m%d')}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Convert to dict
        plan_dict = action_plan.to_dict()
        
        # Save
        with open(filepath, 'w') as f:
            json.dump(plan_dict, f, indent=2, default=str)
    
    def _generate_summary_report(self):
        """Generate final simulation summary"""
        
        self.logger.info("\nSUMMARY REPORT")
        self.logger.info("="*70)
        
        total_procurement = sum(ap.total_procurement_cost for ap in self.action_plans)
        total_transfers = sum(ap.total_transfer_cost for ap in self.action_plans)
        total_po = sum(len(ap.purchase_orders) for ap in self.action_plans)
        total_to = sum(len(ap.transfer_orders) for ap in self.action_plans)
        total_holds = sum(len(ap.project_holds) for ap in self.action_plans)
        
        self.logger.info(f"Total Days Simulated: {len(self.action_plans)}")
        self.logger.info(f"Total Purchase Orders: {total_po}")
        self.logger.info(f"Total Transfer Orders: {total_to}")
        self.logger.info(f"Total Project Holds: {total_holds}")
        self.logger.info(f"Total Procurement Cost: ₹{total_procurement:,.0f}")
        self.logger.info(f"Total Transfer Cost: ₹{total_transfers:,.0f}")
        self.logger.info(f"Total Cost: ₹{total_procurement + total_transfers:,.0f}")
        self.logger.info("")
        
        # Strategy performance
        avg_daily_cost = (total_procurement + total_transfers) / len(self.action_plans)
        self.logger.info(f"Average Daily Cost: ₹{avg_daily_cost:,.0f}")
        
        # Savings from transfers
        # TODO: Calculate actual savings vs all-procurement scenario
        
        self.logger.info("")
        self.logger.info("✓ Detailed action plans saved to: data/outputs/action_plans/")
        self.logger.info("="*70)


def run_simulation():
    """Run the NEXUS supply chain simulation"""
    # Configuration
    SIMULATION_DAYS = 7  # Start with 1 week
    OPTIMIZATION_STRATEGY = 'balanced'  # balanced, cost_focused, rush, risk_averse
    
    print("\n" + "="*70)
    print("          NEXUS - Intelligent Supply Chain Orchestration")
    print("="*70 + "\n")
    
    try:
        # Create orchestrator
        orchestrator = NexusOrchestrator(
            simulation_start_date=datetime.now(),
            simulation_days=SIMULATION_DAYS,
            optimization_strategy=OPTIMIZATION_STRATEGY
        )
        
        # Run simulation
        orchestrator.run_simulation()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


def run_api_server():
    """Run the NEXUS API server"""
    import uvicorn
    from src.api.server import app
    
    print("\n" + "="*70)
    print("          NEXUS API Server - Starting...")
    print("="*70 + "\n")
    
    print("📡 API Documentation available at:")
    print("   • Swagger UI: http://localhost:8000/docs")
    print("   • ReDoc:      http://localhost:8000/redoc")
    print("\n" + "="*70 + "\n")
    
    try:
        uvicorn.run(
            "src.api.server:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        print(f"\n❌ API Server Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


def main():
    """Main entry point for NEXUS"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="NEXUS - Intelligent Supply Chain Orchestration for POWERGRID",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run supply chain simulation
  python main.py --mode simulation
  
  # Run API server
  python main.py --mode api
  
  # Generate synthetic data
  python main.py --mode generate-data
        """
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['simulation', 'api', 'generate-data'],
        default='simulation',
        help='Operation mode: simulation (default), api, or generate-data'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to simulate (for simulation mode)'
    )
    
    parser.add_argument(
        '--strategy',
        type=str,
        choices=['balanced', 'cost_focused', 'rush', 'risk_averse'],
        default='balanced',
        help='Optimization strategy (for simulation mode)'
    )
    
    args = parser.parse_args()
    
    # Route to appropriate function based on mode
    if args.mode == 'api':
        return run_api_server()
    
    elif args.mode == 'generate-data':
        print("\n" + "="*70)
        print("          NEXUS - Generating Synthetic Data")
        print("="*70 + "\n")
        
        try:
            factory = DataFactory(seed=42)
            factory.generate_all()
            print("\n✅ Data generation completed successfully!\n")
            return 0
        except Exception as e:
            print(f"\n❌ Data generation failed: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    else:  # simulation mode
        return run_simulation()


if __name__ == "__main__":
    exit(main())
