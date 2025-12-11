"""
Material Requirement routes for NEXUS API
CRUD operations for project material requirements
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import db_models as models
from .. import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.MaterialRequirement])
def get_material_requirements(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all material requirements with pagination"""
    requirements = db.query(models.MaterialRequirement).offset(skip).limit(limit).all()
    return requirements


@router.get("/{requirement_id}", response_model=schemas.MaterialRequirement)
def get_material_requirement(requirement_id: int, db: Session = Depends(get_db)):
    """Get a specific material requirement by ID"""
    requirement = db.query(models.MaterialRequirement).filter(
        models.MaterialRequirement.id == requirement_id
    ).first()
    if not requirement:
        raise HTTPException(status_code=404, detail="Material requirement not found")
    return requirement


@router.post("/", response_model=schemas.MaterialRequirement, status_code=201)
def create_material_requirement(requirement: schemas.MaterialRequirementCreate, db: Session = Depends(get_db)):
    """Create a new material requirement"""
    # Verify project exists
    project = db.query(models.Project).filter(models.Project.id == requirement.project_id).first()
    if not project:
        raise HTTPException(status_code=400, detail="Project not found")
    
    # Verify material exists
    material = db.query(models.Material).filter(models.Material.id == requirement.material_id).first()
    if not material:
        raise HTTPException(status_code=400, detail="Material not found")
    
    db_requirement = models.MaterialRequirement(**requirement.model_dump())
    db.add(db_requirement)
    db.commit()
    db.refresh(db_requirement)
    return db_requirement


@router.put("/{requirement_id}", response_model=schemas.MaterialRequirement)
def update_material_requirement(
    requirement_id: int, 
    requirement: schemas.MaterialRequirementUpdate, 
    db: Session = Depends(get_db)
):
    """Update an existing material requirement"""
    db_requirement = db.query(models.MaterialRequirement).filter(
        models.MaterialRequirement.id == requirement_id
    ).first()
    if not db_requirement:
        raise HTTPException(status_code=404, detail="Material requirement not found")
    
    update_data = requirement.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_requirement, key, value)
    
    db.commit()
    db.refresh(db_requirement)
    return db_requirement


@router.delete("/{requirement_id}", status_code=204)
def delete_material_requirement(requirement_id: int, db: Session = Depends(get_db)):
    """Delete a material requirement"""
    db_requirement = db.query(models.MaterialRequirement).filter(
        models.MaterialRequirement.id == requirement_id
    ).first()
    if not db_requirement:
        raise HTTPException(status_code=404, detail="Material requirement not found")
    
    db.delete(db_requirement)
    db.commit()
    return None


@router.get("/status/{status}", response_model=List[schemas.MaterialRequirement])
def get_requirements_by_status(status: str, db: Session = Depends(get_db)):
    """Get all material requirements with a specific status"""
    requirements = db.query(models.MaterialRequirement).filter(
        models.MaterialRequirement.status == status
    ).all()
    return requirements


@router.get("/priority/{priority}", response_model=List[schemas.MaterialRequirement])
def get_requirements_by_priority(priority: str, db: Session = Depends(get_db)):
    """Get all material requirements with a specific priority"""
    requirements = db.query(models.MaterialRequirement).filter(
        models.MaterialRequirement.priority == priority
    ).all()
    return requirements
