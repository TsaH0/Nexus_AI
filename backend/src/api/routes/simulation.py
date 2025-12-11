"""
Simulation routes for NEXUS API
Run supply chain simulations and get action plans
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import json
from pathlib import Path

from ..database import get_db
from .. import db_models as models
from .. import schemas

router = APIRouter()


@router.post("/run", response_model=schemas.SimulationSummary)
async def run_simulation(request: schemas.SimulationRequest, db: Session = Depends(get_db)):
    """
    Run the NEXUS supply chain simulation
    This integrates with the core orchestrator
    """
    try:
        # Import the orchestrator
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from main import NexusOrchestrator
        
        # Initialize orchestrator
        orchestrator = NexusOrchestrator()
        
        # Set strategy
        orchestrator.procurement_optimizer.optimization_strategy = request.strategy
        
        # Run simulation
        start_date = request.start_date or datetime.now()
        results = orchestrator.run_simulation(
            days=request.days,
            start_date=start_date
        )
        
        # Calculate summary
        total_po = sum(len(r.get('purchase_orders', [])) for r in results)
        total_to = sum(len(r.get('transfer_orders', [])) for r in results)
        total_holds = sum(len(r.get('project_holds', [])) for r in results)
        total_procurement = sum(r.get('procurement_cost', 0) for r in results)
        total_transfer = sum(r.get('transfer_cost', 0) for r in results)
        total_cost = total_procurement + total_transfer
        
        return schemas.SimulationSummary(
            total_days=request.days,
            total_purchase_orders=total_po,
            total_transfer_orders=total_to,
            total_project_holds=total_holds,
            total_procurement_cost=total_procurement,
            total_transfer_cost=total_transfer,
            total_cost=total_cost,
            average_daily_cost=total_cost / request.days if request.days > 0 else 0
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.get("/action-plans", response_model=List[schemas.ActionPlanResponse])
def get_action_plans(limit: int = 7):
    """Get recent action plans from the simulation output"""
    action_plans_dir = Path(__file__).parent.parent.parent.parent / "data" / "outputs" / "action_plans"
    
    if not action_plans_dir.exists():
        return []
    
    plans = []
    files = sorted(action_plans_dir.glob("action_plan_*.json"), reverse=True)[:limit]
    
    for file_path in files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                plans.append(schemas.ActionPlanResponse(
                    date=datetime.fromisoformat(data.get('date', datetime.now().isoformat())),
                    region=data.get('region', ''),
                    purchase_orders=data.get('purchase_orders', []),
                    transfer_orders=data.get('transfer_orders', []),
                    project_holds=data.get('project_holds', []),
                    total_procurement_cost=data.get('total_procurement_cost', 0),
                    total_transfer_cost=data.get('total_transfer_cost', 0),
                    reasoning=data.get('reasoning', '')
                ))
        except Exception:
            continue
    
    return plans


@router.get("/action-plans/{date}")
def get_action_plan_by_date(date: str):
    """Get action plan for a specific date (format: YYYYMMDD)"""
    action_plans_dir = Path(__file__).parent.parent.parent.parent / "data" / "outputs" / "action_plans"
    file_path = action_plans_dir / f"action_plan_{date}.json"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Action plan for {date} not found")
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading action plan: {str(e)}")


@router.get("/status")
def get_simulation_status():
    """Get current simulation status and statistics"""
    action_plans_dir = Path(__file__).parent.parent.parent.parent / "data" / "outputs" / "action_plans"
    
    if not action_plans_dir.exists():
        return {
            "status": "no_data",
            "message": "No simulation data available",
            "action_plans_count": 0
        }
    
    files = list(action_plans_dir.glob("action_plan_*.json"))
    
    if not files:
        return {
            "status": "no_data",
            "message": "No action plans generated",
            "action_plans_count": 0
        }
    
    # Get the latest action plan
    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    
    try:
        with open(latest_file, 'r') as f:
            latest_data = json.load(f)
        
        return {
            "status": "ready",
            "message": f"{len(files)} action plans available",
            "action_plans_count": len(files),
            "latest_date": latest_data.get('date'),
            "latest_procurement_cost": latest_data.get('total_procurement_cost', 0),
            "latest_transfer_cost": latest_data.get('total_transfer_cost', 0)
        }
    except Exception:
        return {
            "status": "error",
            "message": "Error reading simulation data",
            "action_plans_count": len(files)
        }


@router.post("/generate-data")
async def generate_simulation_data(seed: int = 42):
    """Generate synthetic data for simulation using DataFactory"""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from src.core.data_factory import DataFactory
        
        factory = DataFactory(seed=seed)
        factory.generate_all()
        
        return {
            "status": "success",
            "message": "Simulation data generated successfully",
            "materials": len(factory.materials),
            "vendors": len(factory.vendors),
            "warehouses": len(factory.warehouses),
            "projects": len(factory.projects)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data generation failed: {str(e)}")


@router.get("/dashboard")
def get_dashboard_data(db: Session = Depends(get_db)):
    """Get dashboard summary data"""
    # Get counts from database
    materials_count = db.query(models.Material).count()
    projects_count = db.query(models.Project).count()
    locations_count = db.query(models.Location).count()
    vendors_count = db.query(models.Vendor).count()
    warehouses_count = db.query(models.Warehouse).count()
    forecasts_count = db.query(models.Forecast).count()
    
    # Get action plan stats
    action_plans_dir = Path(__file__).parent.parent.parent.parent / "data" / "outputs" / "action_plans"
    action_plans_count = len(list(action_plans_dir.glob("action_plan_*.json"))) if action_plans_dir.exists() else 0
    
    # Get recent activity
    recent_forecasts = db.query(models.Forecast).order_by(
        models.Forecast.created_at.desc()
    ).limit(5).all()
    
    return {
        "summary": {
            "materials": materials_count,
            "projects": projects_count,
            "locations": locations_count,
            "vendors": vendors_count,
            "warehouses": warehouses_count,
            "forecasts": forecasts_count,
            "action_plans": action_plans_count
        },
        "recent_forecasts": [
            {
                "material_id": f.material_id,
                "location_id": f.location_id,
                "predicted_demand": f.predicted_demand,
                "confidence": f.confidence_level,
                "date": f.forecast_date.isoformat() if f.forecast_date else None
            }
            for f in recent_forecasts
        ]
    }
