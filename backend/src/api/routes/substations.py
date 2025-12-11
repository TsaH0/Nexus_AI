"""
Substation API Routes
======================
Endpoints for managing substations, their inventory, projects, and critical materials.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.api.database import get_db
from src.api.db_models import (
    Substation, SubstationProject, SubstationCriticalMaterial,
    ProjectMaterialNeed, Warehouse, Material, InventoryStock
)
from src.api import schemas


router = APIRouter(prefix="/substations", tags=["Substations"])


# =============================================================================
# Substation CRUD
# =============================================================================

@router.get("/", response_model=List[schemas.Substation])
def list_substations(
    state: Optional[str] = None,
    stock_status: Optional[str] = None,
    status: Optional[str] = "Active",
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all substations with optional filtering.
    
    - **state**: Filter by state (e.g., "Rajasthan", "Karnataka")
    - **stock_status**: Filter by stock status ("Normal", "Overstocked", "Understocked", "Low")
    - **status**: Filter by operational status ("Active", "Inactive", "Maintenance")
    """
    query = db.query(Substation)
    
    if state:
        query = query.filter(Substation.state == state)
    if stock_status:
        query = query.filter(Substation.stock_status == stock_status)
    if status:
        query = query.filter(Substation.status == status)
    
    return query.offset(skip).limit(limit).all()


@router.get("/understocked", response_model=List[schemas.SubstationWithDetails])
def get_understocked_substations(
    threshold: float = 60.0,
    db: Session = Depends(get_db)
):
    """
    Get all substations with stock levels below threshold.
    
    - **threshold**: Stock level percentage threshold (default: 60%)
    
    Returns substations with critical material details.
    """
    substations = db.query(Substation).filter(
        and_(
            Substation.stock_level_percentage < threshold,
            Substation.status == "Active"
        )
    ).all()
    
    result = []
    for sub in substations:
        # Get critical materials
        critical_mats = db.query(SubstationCriticalMaterial).filter(
            SubstationCriticalMaterial.substation_id == sub.id
        ).all()
        
        # Get active projects count
        active_projects = db.query(SubstationProject).filter(
            and_(
                SubstationProject.substation_id == sub.id,
                SubstationProject.status.in_(["Active", "In Progress"])
            )
        ).count()
        
        # Get warehouse name
        warehouse_name = None
        if sub.primary_warehouse_id:
            warehouse = db.query(Warehouse).filter(
                Warehouse.id == sub.primary_warehouse_id
            ).first()
            if warehouse:
                warehouse_name = warehouse.name
        
        result.append(schemas.SubstationWithDetails(
            **{c.name: getattr(sub, c.name) for c in sub.__table__.columns},
            critical_materials=[
                schemas.SubstationCriticalMaterialBase(
                    substation_id=cm.substation_id,
                    material_id=cm.material_id,
                    material_name=cm.material_name,
                    current_quantity=cm.current_quantity,
                    required_quantity=cm.required_quantity,
                    shortage_percentage=cm.shortage_percentage,
                    priority=cm.priority
                ) for cm in critical_mats
            ],
            active_projects=active_projects,
            warehouse_name=warehouse_name
        ))
    
    return result


@router.get("/overstocked", response_model=List[schemas.SubstationWithDetails])
def get_overstocked_substations(
    threshold: float = 120.0,
    db: Session = Depends(get_db)
):
    """
    Get all substations with stock levels above threshold (potential sources for transfers).
    
    - **threshold**: Stock level percentage threshold (default: 120%)
    """
    substations = db.query(Substation).filter(
        and_(
            Substation.stock_level_percentage > threshold,
            Substation.status == "Active"
        )
    ).all()
    
    result = []
    for sub in substations:
        warehouse_name = None
        if sub.primary_warehouse_id:
            warehouse = db.query(Warehouse).filter(
                Warehouse.id == sub.primary_warehouse_id
            ).first()
            if warehouse:
                warehouse_name = warehouse.name
        
        result.append(schemas.SubstationWithDetails(
            **{c.name: getattr(sub, c.name) for c in sub.__table__.columns},
            critical_materials=[],
            active_projects=0,
            warehouse_name=warehouse_name
        ))
    
    return result


@router.get("/by-state", response_model=dict)
def get_substations_by_state(db: Session = Depends(get_db)):
    """Get count of substations grouped by state."""
    substations = db.query(Substation).filter(
        Substation.status == "Active"
    ).all()
    
    by_state = {}
    for sub in substations:
        if sub.state not in by_state:
            by_state[sub.state] = {
                'count': 0,
                'understocked': 0,
                'overstocked': 0,
                'normal': 0
            }
        by_state[sub.state]['count'] += 1
        
        if sub.stock_status == 'Understocked' or sub.stock_level_percentage < 60:
            by_state[sub.state]['understocked'] += 1
        elif sub.stock_status == 'Overstocked' or sub.stock_level_percentage > 120:
            by_state[sub.state]['overstocked'] += 1
        else:
            by_state[sub.state]['normal'] += 1
    
    return by_state


@router.get("/{substation_id}", response_model=schemas.SubstationWithDetails)
def get_substation(substation_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific substation.
    
    Includes:
    - Basic substation info
    - Critical materials list
    - Active project count
    - Associated warehouse
    """
    substation = db.query(Substation).filter(
        Substation.id == substation_id
    ).first()
    
    if not substation:
        raise HTTPException(status_code=404, detail="Substation not found")
    
    # Get critical materials
    critical_mats = db.query(SubstationCriticalMaterial).filter(
        SubstationCriticalMaterial.substation_id == substation_id
    ).all()
    
    # Get active projects count
    active_projects = db.query(SubstationProject).filter(
        and_(
            SubstationProject.substation_id == substation_id,
            SubstationProject.status.in_(["Active", "In Progress"])
        )
    ).count()
    
    # Get warehouse name
    warehouse_name = None
    if substation.primary_warehouse_id:
        warehouse = db.query(Warehouse).filter(
            Warehouse.id == substation.primary_warehouse_id
        ).first()
        if warehouse:
            warehouse_name = warehouse.name
    
    return schemas.SubstationWithDetails(
        **{c.name: getattr(substation, c.name) for c in substation.__table__.columns},
        critical_materials=[
            schemas.SubstationCriticalMaterialBase(
                substation_id=cm.substation_id,
                material_id=cm.material_id,
                material_name=cm.material_name,
                current_quantity=cm.current_quantity,
                required_quantity=cm.required_quantity,
                shortage_percentage=cm.shortage_percentage,
                priority=cm.priority
            ) for cm in critical_mats
        ],
        active_projects=active_projects,
        warehouse_name=warehouse_name
    )


@router.post("/", response_model=schemas.Substation)
def create_substation(
    substation: schemas.SubstationCreate,
    db: Session = Depends(get_db)
):
    """Create a new substation."""
    # Check for duplicate code
    if substation.substation_code:
        existing = db.query(Substation).filter(
            Substation.substation_code == substation.substation_code
        ).first()
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Substation with code {substation.substation_code} already exists"
            )
    
    db_substation = Substation(**substation.model_dump())
    db.add(db_substation)
    db.commit()
    db.refresh(db_substation)
    
    return db_substation


@router.put("/{substation_id}", response_model=schemas.Substation)
def update_substation(
    substation_id: int,
    substation: schemas.SubstationUpdate,
    db: Session = Depends(get_db)
):
    """Update a substation."""
    db_substation = db.query(Substation).filter(
        Substation.id == substation_id
    ).first()
    
    if not db_substation:
        raise HTTPException(status_code=404, detail="Substation not found")
    
    update_data = substation.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_substation, field, value)
    
    db_substation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_substation)
    
    return db_substation


@router.delete("/{substation_id}")
def delete_substation(substation_id: int, db: Session = Depends(get_db)):
    """Delete a substation (soft delete by setting status to Inactive)."""
    db_substation = db.query(Substation).filter(
        Substation.id == substation_id
    ).first()
    
    if not db_substation:
        raise HTTPException(status_code=404, detail="Substation not found")
    
    db_substation.status = "Inactive"
    db_substation.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": f"Substation {substation_id} deactivated"}


# =============================================================================
# Substation Inventory
# =============================================================================

@router.get("/{substation_id}/inventory", response_model=List[dict])
def get_substation_inventory(
    substation_id: int,
    category: Optional[str] = None,
    low_stock_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get inventory at a substation's warehouse.
    
    - **category**: Filter by material category
    - **low_stock_only**: Only show items below reorder point
    """
    substation = db.query(Substation).filter(
        Substation.id == substation_id
    ).first()
    
    if not substation:
        raise HTTPException(status_code=404, detail="Substation not found")
    
    if not substation.primary_warehouse_id:
        raise HTTPException(status_code=404, detail="Substation has no assigned warehouse")
    
    query = db.query(InventoryStock, Material).join(
        Material, InventoryStock.material_id == Material.id
    ).filter(
        InventoryStock.warehouse_id == substation.primary_warehouse_id
    )
    
    if category:
        query = query.filter(Material.category == category)
    
    if low_stock_only:
        query = query.filter(
            InventoryStock.quantity_available <= InventoryStock.reorder_point
        )
    
    stocks = query.all()
    
    return [
        {
            'material_id': stock.material_id,
            'material_name': material.name,
            'category': material.category,
            'unit': material.unit,
            'quantity': stock.quantity_available,
            'reserved_quantity': stock.quantity_reserved,
            'available_quantity': stock.quantity_available - stock.quantity_reserved,
            'minimum_quantity': stock.min_stock_level,
            'reorder_point': stock.reorder_point,
            'unit_cost': material.unit_price,
            'is_low_stock': stock.quantity_available <= stock.reorder_point
        }
        for stock, material in stocks
    ]


@router.get("/{substation_id}/critical-materials", response_model=List[schemas.SubstationCriticalMaterial])
def get_critical_materials(
    substation_id: int,
    priority: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get critical materials for a substation.
    
    - **priority**: Filter by priority ("Critical", "High", "Medium", "Low")
    """
    query = db.query(SubstationCriticalMaterial).filter(
        SubstationCriticalMaterial.substation_id == substation_id
    )
    
    if priority:
        query = query.filter(SubstationCriticalMaterial.priority == priority)
    
    return query.order_by(SubstationCriticalMaterial.shortage_percentage.desc()).all()


# =============================================================================
# Substation Projects
# =============================================================================

@router.get("/{substation_id}/projects", response_model=List[schemas.SubstationProject])
def get_substation_projects(
    substation_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all projects at a substation.
    
    - **status**: Filter by project status ("Active", "In Progress", "Completed", "Delayed")
    """
    query = db.query(SubstationProject).filter(
        SubstationProject.substation_id == substation_id
    )
    
    if status:
        query = query.filter(SubstationProject.status == status)
    
    return query.order_by(SubstationProject.created_at.desc()).all()


@router.get("/{substation_id}/projects/{project_id}", response_model=schemas.SubstationProjectWithDetails)
def get_project_details(
    substation_id: int,
    project_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed project information including progress and material needs."""
    project = db.query(SubstationProject).filter(
        and_(
            SubstationProject.id == project_id,
            SubstationProject.substation_id == substation_id
        )
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get substation name
    substation = db.query(Substation).filter(
        Substation.id == substation_id
    ).first()
    
    # Get material needs
    material_needs = db.query(ProjectMaterialNeed).filter(
        ProjectMaterialNeed.project_id == project_id
    ).all()
    
    # Calculate progress
    progress = {
        'foundation': {
            'completed': project.foundation_completed or 0,
            'total': project.foundation_total or 0,
            'percentage': round(
                (project.foundation_completed or 0) / (project.foundation_total or 1) * 100, 2
            )
        },
        'tower_erection': {
            'completed': project.tower_erected or 0,
            'total': project.tower_total or 0,
            'percentage': round(
                (project.tower_erected or 0) / (project.tower_total or 1) * 100, 2
            )
        },
        'stringing': {
            'completed': project.stringing_completed_ckm or 0,
            'total': project.stringing_total_ckm or 0,
            'percentage': round(
                (project.stringing_completed_ckm or 0) / (project.stringing_total_ckm or 1) * 100, 2
            )
        },
        'overall': {
            'percentage': project.overall_progress or 0
        }
    }
    
    return schemas.SubstationProjectWithDetails(
        **{c.name: getattr(project, c.name) for c in project.__table__.columns},
        progress=progress,
        material_needs=[
            schemas.ProjectMaterialNeedBase(
                project_id=mn.project_id,
                material_id=mn.material_id,
                material_name=mn.material_name,
                quantity_needed=mn.quantity_needed,
                quantity_available=mn.quantity_available,
                quantity_shortage=mn.quantity_shortage,
                unit=mn.unit,
                unit_price=mn.unit_price,
                total_value=mn.total_value,
                priority=mn.priority,
                status=mn.status
            ) for mn in material_needs
        ],
        substation_name=substation.name if substation else None
    )


# =============================================================================
# Dashboard / Analytics
# =============================================================================

@router.get("/dashboard/summary", response_model=dict)
def get_substations_dashboard(db: Session = Depends(get_db)):
    """
    Get dashboard summary for all substations.
    
    Returns:
    - Total substations count
    - Stock status breakdown
    - Critical alerts
    - Active projects count
    """
    substations = db.query(Substation).filter(
        Substation.status == "Active"
    ).all()
    
    total = len(substations)
    understocked = sum(1 for s in substations if s.stock_status == "Understocked" or s.stock_level_percentage < 60)
    overstocked = sum(1 for s in substations if s.stock_status == "Overstocked" or s.stock_level_percentage > 120)
    low_stock = sum(1 for s in substations if s.stock_status == "Low" or (60 <= s.stock_level_percentage < 80))
    normal = total - understocked - overstocked - low_stock
    
    # Count critical materials
    critical_count = db.query(SubstationCriticalMaterial).filter(
        SubstationCriticalMaterial.priority == "Critical"
    ).count()
    
    # Count active projects
    active_projects = db.query(SubstationProject).filter(
        SubstationProject.status.in_(["Active", "In Progress"])
    ).count()
    
    # Delayed projects
    delayed_projects = db.query(SubstationProject).filter(
        SubstationProject.delay_days > 0
    ).count()
    
    return {
        'total_substations': total,
        'stock_status': {
            'normal': normal,
            'low': low_stock,
            'understocked': understocked,
            'overstocked': overstocked
        },
        'critical_alerts': critical_count,
        'active_projects': active_projects,
        'delayed_projects': delayed_projects,
        'average_stock_level': round(
            sum(s.stock_level_percentage for s in substations) / max(total, 1), 2
        )
    }


@router.get("/map/data", response_model=List[dict])
def get_substations_map_data(db: Session = Depends(get_db)):
    """
    Get substation data formatted for map visualization.
    
    Returns coordinates and status for each substation.
    """
    substations = db.query(Substation).filter(
        Substation.status == "Active"
    ).all()
    
    return [
        {
            'id': s.id,
            'name': s.name,
            'code': s.substation_code,
            'lat': s.latitude,
            'lng': s.longitude,
            'state': s.state,
            'city': s.city,
            'type': s.substation_type,
            'capacity': s.capacity,
            'stock_status': s.stock_status,
            'stock_level': s.stock_level_percentage,
            'color': _get_status_color(s.stock_status, s.stock_level_percentage)
        }
        for s in substations
    ]


def _get_status_color(stock_status: str, stock_level: float) -> str:
    """Get color code for map markers based on stock status."""
    if stock_status == "Understocked" or stock_level < 50:
        return "#EF4444"  # Red
    elif stock_status == "Low" or stock_level < 70:
        return "#F59E0B"  # Orange
    elif stock_status == "Overstocked" or stock_level > 120:
        return "#3B82F6"  # Blue
    else:
        return "#10B981"  # Green
