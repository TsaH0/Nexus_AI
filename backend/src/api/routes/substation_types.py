"""
Substation Type routes for NEXUS API
CRUD operations for substation types
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import db_models as models
from .. import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.SubstationType])
def get_substation_types(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all substation types with pagination"""
    substation_types = db.query(models.SubstationType).offset(skip).limit(limit).all()
    return substation_types


@router.get("/{substation_type_id}", response_model=schemas.SubstationType)
def get_substation_type(substation_type_id: int, db: Session = Depends(get_db)):
    """Get a specific substation type by ID"""
    substation_type = db.query(models.SubstationType).filter(
        models.SubstationType.id == substation_type_id
    ).first()
    if not substation_type:
        raise HTTPException(status_code=404, detail="Substation type not found")
    return substation_type


@router.post("/", response_model=schemas.SubstationType, status_code=201)
def create_substation_type(substation_type: schemas.SubstationTypeCreate, db: Session = Depends(get_db)):
    """Create a new substation type"""
    existing = db.query(models.SubstationType).filter(
        models.SubstationType.name == substation_type.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Substation type with this name already exists")
    
    db_substation_type = models.SubstationType(**substation_type.model_dump())
    db.add(db_substation_type)
    db.commit()
    db.refresh(db_substation_type)
    return db_substation_type


@router.put("/{substation_type_id}", response_model=schemas.SubstationType)
def update_substation_type(
    substation_type_id: int, 
    substation_type: schemas.SubstationTypeUpdate, 
    db: Session = Depends(get_db)
):
    """Update an existing substation type"""
    db_substation_type = db.query(models.SubstationType).filter(
        models.SubstationType.id == substation_type_id
    ).first()
    if not db_substation_type:
        raise HTTPException(status_code=404, detail="Substation type not found")
    
    update_data = substation_type.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_substation_type, key, value)
    
    db.commit()
    db.refresh(db_substation_type)
    return db_substation_type


@router.delete("/{substation_type_id}", status_code=204)
def delete_substation_type(substation_type_id: int, db: Session = Depends(get_db)):
    """Delete a substation type"""
    db_substation_type = db.query(models.SubstationType).filter(
        models.SubstationType.id == substation_type_id
    ).first()
    if not db_substation_type:
        raise HTTPException(status_code=404, detail="Substation type not found")
    
    db.delete(db_substation_type)
    db.commit()
    return None


@router.get("/voltage/{voltage_level}", response_model=List[schemas.SubstationType])
def get_substation_types_by_voltage(voltage_level: str, db: Session = Depends(get_db)):
    """Get all substation types for a specific voltage level"""
    substation_types = db.query(models.SubstationType).filter(
        models.SubstationType.voltage_level == voltage_level
    ).all()
    return substation_types
