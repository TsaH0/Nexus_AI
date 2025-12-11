"""
Project routes for NEXUS API
CRUD operations for power grid projects
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from ..database import get_db
from .. import db_models as models
from .. import schemas

router = APIRouter()


# ============================================================================
# Request/Response Models for Add Project from Quote
# ============================================================================

class AddProjectFromQuoteRequest(BaseModel):
    """Request to add a new project from a quote"""
    project_type: str  # e.g., "33/22 kV 1 X 5 MVA New S/S(Outdoor)"
    project_name: str
    description: Optional[str] = None
    
    # Coordinates for line (optional)
    from_lat: Optional[float] = None
    from_lng: Optional[float] = None
    to_lat: Optional[float] = None
    to_lng: Optional[float] = None
    
    # Project location
    substation_id: Optional[int] = None
    state: str
    city: str
    
    # Additional parameters
    terrain: str = "normal"
    circuit_type: str = "single"
    developer: str = "POWERGRID"
    developer_type: str = "CPSU"
    target_date: Optional[str] = None  # YYYY-MM-DD
    
    # Auto-generate orders
    auto_generate_orders: bool = False


class AddProjectResponse(BaseModel):
    """Response after adding a project"""
    success: bool
    project_id: int
    project_code: str
    project_name: str
    total_cost: float
    
    # Forecast impact
    forecast_impact: Dict[str, Any]
    
    # Procurement recommendations
    material_requirements: List[Dict[str, Any]]
    shortage_risk: str  # Low, Medium, High, Critical
    procurement_health_before: float
    procurement_health_after: float


@router.get("/", response_model=List[schemas.Project])
def get_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all projects with pagination"""
    projects = db.query(models.Project).offset(skip).limit(limit).all()
    return projects


@router.get("/{project_id}", response_model=schemas.Project)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get a specific project by ID"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/", response_model=schemas.Project, status_code=201)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project"""
    # Check for duplicate name
    existing = db.query(models.Project).filter(models.Project.name == project.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Project with this name already exists")
    
    # Verify location exists
    location = db.query(models.Location).filter(models.Location.id == project.location_id).first()
    if not location:
        raise HTTPException(status_code=400, detail="Location not found")
    
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@router.post("/add-from-quote", response_model=AddProjectResponse)
def add_project_from_quote(
    request: AddProjectFromQuoteRequest,
    db: Session = Depends(get_db)
):
    """
    Add a new project from a BOQ quote.
    
    This endpoint:
    1. Gets the BOQ template for the project type
    2. Calculates line costs if coordinates provided
    3. Creates the SubstationProject
    4. Adds material requirements
    5. Simulates forecast impact
    6. Returns procurement recommendations
    
    Use this after getting a quote from /api/v1/quote/
    """
    from src.core.boq_service import get_boq_service
    from src.forecasting.material_forecast import MaterialForecastEngine
    
    boq_service = get_boq_service()
    
    # Generate quote
    quote = boq_service.generate_project_quote(
        project_type=request.project_type,
        from_lat=request.from_lat,
        from_lng=request.from_lng,
        to_lat=request.to_lat,
        to_lng=request.to_lng,
        terrain=request.terrain,
        circuit_type=request.circuit_type
    )
    
    if not quote.get('success'):
        raise HTTPException(status_code=400, detail=quote.get('error', 'Failed to generate quote'))
    
    # Calculate line length if coordinates provided
    line_length = 0
    if quote.get('line_cost'):
        line_length = quote['line_cost']['distance_km']
    
    # Extract voltage level
    voltage_level = 400
    if quote.get('voltage_level'):
        import re
        match = re.search(r'(\d+)', quote['voltage_level'])
        if match:
            voltage_level = int(match.group(1))
    
    # Generate project code
    import random
    project_code = f"PROJ-{request.state[:3].upper()}-{datetime.now().year}-{random.randint(100, 999)}"
    
    # Parse target date
    target_date = None
    if request.target_date:
        target_date = datetime.strptime(request.target_date, '%Y-%m-%d')
    else:
        target_date = datetime.now() + timedelta(days=365)  # Default 1 year
    
    # Get current forecast engine state
    forecast_engine = MaterialForecastEngine(db_session=db)
    current_forecast = forecast_engine.generate_monthly_forecast(months=6, include_project_breakdown=False)
    current_health = current_forecast['summary']['procurement_health_score']
    
    # Create the project
    project = models.SubstationProject(
        project_code=project_code,
        name=request.project_name,
        description=request.description or f"Auto-generated from quote: {request.project_type}",
        substation_id=request.substation_id,
        developer=request.developer,
        developer_type=request.developer_type,
        category="ISTS",
        project_type=quote.get('category', 'Substation'),
        circuit_type=request.circuit_type.upper(),
        voltage_level=voltage_level,
        total_line_length=line_length,
        total_tower_locations=int(line_length * 3) if line_length > 0 else 0,
        target_date=target_date,
        anticipated_cod=target_date + timedelta(days=90),
        overall_progress=0.0,
        status="Planning",
        budget_sanctioned=quote['total_project_cost'],
        budget_spent=0.0
    )
    db.add(project)
    db.flush()
    
    # Add material requirements from quote
    material_requirements = []
    for mat in quote.get('materials', [])[:20]:  # Limit to top 20 materials
        # Try to find material in database or create mapping
        mat_record = db.query(models.Material).filter(
            models.Material.name.ilike(f"%{mat['description'][:30]}%")
        ).first()
        
        mat_id = mat_record.id if mat_record else None
        
        need = models.ProjectMaterialNeed(
            project_id=project.id,
            material_id=mat_id,
            material_name=mat['description'][:100],
            quantity_needed=mat['quantity'],
            quantity_available=0,
            quantity_shortage=mat['quantity'],
            unit=mat['unit'],
            unit_price=mat['rate'],
            priority="Medium",
            status="Pending"
        )
        db.add(need)
        
        material_requirements.append({
            'material': mat['description'][:50],
            'quantity': mat['quantity'],
            'unit': mat['unit'],
            'cost': mat['cost'],
            'status': 'Pending'
        })
    
    db.commit()
    
    # Simulate forecast impact
    impact = forecast_engine.simulate_new_project_impact(
        project_type=request.project_type,
        line_length_km=line_length,
        voltage_level=f"{voltage_level}kV",
        capacity_mva=quote.get('capacity_mva', 5)
    )
    
    new_health = impact['procurement_impact']['new_health_score']
    health_change = impact['procurement_impact']['health_change']
    
    # Determine shortage risk
    if new_health >= 80:
        shortage_risk = "Low"
    elif new_health >= 60:
        shortage_risk = "Medium"
    elif new_health >= 40:
        shortage_risk = "High"
    else:
        shortage_risk = "Critical"
    
    return AddProjectResponse(
        success=True,
        project_id=project.id,
        project_code=project_code,
        project_name=request.project_name,
        total_cost=quote['total_project_cost'],
        forecast_impact={
            'additional_materials': len(impact.get('additional_demand', {})),
            'new_shortages_created': len(impact.get('new_shortages', [])),
            'health_change': health_change,
            'risk_level': impact['procurement_impact']['risk_level']
        },
        material_requirements=material_requirements[:10],
        shortage_risk=shortage_risk,
        procurement_health_before=current_health,
        procurement_health_after=new_health
    )


@router.put("/{project_id}", response_model=schemas.Project)
def update_project(project_id: int, project: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    """Update an existing project"""
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = project.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_project, key, value)
    
    db.commit()
    db.refresh(db_project)
    return db_project


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete a project"""
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(db_project)
    db.commit()
    return None


@router.get("/{project_id}/requirements", response_model=List[schemas.MaterialRequirement])
def get_project_requirements(project_id: int, db: Session = Depends(get_db)):
    """Get all material requirements for a project"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    requirements = db.query(models.MaterialRequirement).filter(
        models.MaterialRequirement.project_id == project_id
    ).all()
    return requirements
