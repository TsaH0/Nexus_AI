"""
Tower Type routes for NEXUS API
CRUD operations for transmission tower types
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import db_models as models
from .. import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.TowerType])
def get_tower_types(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all tower types with pagination"""
    tower_types = db.query(models.TowerType).offset(skip).limit(limit).all()
    return tower_types


@router.get("/{tower_type_id}", response_model=schemas.TowerType)
def get_tower_type(tower_type_id: int, db: Session = Depends(get_db)):
    """Get a specific tower type by ID"""
    tower_type = db.query(models.TowerType).filter(models.TowerType.id == tower_type_id).first()
    if not tower_type:
        raise HTTPException(status_code=404, detail="Tower type not found")
    return tower_type


@router.post("/", response_model=schemas.TowerType, status_code=201)
def create_tower_type(tower_type: schemas.TowerTypeCreate, db: Session = Depends(get_db)):
    """Create a new tower type"""
    existing = db.query(models.TowerType).filter(models.TowerType.name == tower_type.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tower type with this name already exists")
    
    db_tower_type = models.TowerType(**tower_type.model_dump())
    db.add(db_tower_type)
    db.commit()
    db.refresh(db_tower_type)
    return db_tower_type


@router.put("/{tower_type_id}", response_model=schemas.TowerType)
def update_tower_type(tower_type_id: int, tower_type: schemas.TowerTypeUpdate, db: Session = Depends(get_db)):
    """Update an existing tower type"""
    db_tower_type = db.query(models.TowerType).filter(models.TowerType.id == tower_type_id).first()
    if not db_tower_type:
        raise HTTPException(status_code=404, detail="Tower type not found")
    
    update_data = tower_type.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_tower_type, key, value)
    
    db.commit()
    db.refresh(db_tower_type)
    return db_tower_type


@router.delete("/{tower_type_id}", status_code=204)
def delete_tower_type(tower_type_id: int, db: Session = Depends(get_db)):
    """Delete a tower type"""
    db_tower_type = db.query(models.TowerType).filter(models.TowerType.id == tower_type_id).first()
    if not db_tower_type:
        raise HTTPException(status_code=404, detail="Tower type not found")
    
    db.delete(db_tower_type)
    db.commit()
    return None


@router.get("/voltage/{voltage_rating}", response_model=List[schemas.TowerType])
def get_tower_types_by_voltage(voltage_rating: str, db: Session = Depends(get_db)):
    """Get all tower types for a specific voltage rating"""
    tower_types = db.query(models.TowerType).filter(
        models.TowerType.voltage_rating == voltage_rating
    ).all()
    return tower_types
