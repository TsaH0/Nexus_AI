"""
Material routes for NEXUS API
CRUD operations for materials and equipment
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import db_models as models
from .. import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.Material])
def get_materials(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all materials with pagination"""
    materials = db.query(models.Material).offset(skip).limit(limit).all()
    return materials


@router.get("/{material_id}", response_model=schemas.Material)
def get_material(material_id: int, db: Session = Depends(get_db)):
    """Get a specific material by ID"""
    material = db.query(models.Material).filter(models.Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material


@router.get("/code/{material_code}", response_model=schemas.Material)
def get_material_by_code(material_code: str, db: Session = Depends(get_db)):
    """Get a specific material by code (e.g., MAT-001)"""
    material = db.query(models.Material).filter(models.Material.material_code == material_code).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material


@router.post("/", response_model=schemas.Material, status_code=201)
def create_material(material: schemas.MaterialCreate, db: Session = Depends(get_db)):
    """Create a new material"""
    # Check for duplicate name
    existing = db.query(models.Material).filter(models.Material.name == material.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Material with this name already exists")
    
    db_material = models.Material(**material.model_dump())
    db.add(db_material)
    db.commit()
    db.refresh(db_material)
    return db_material


@router.put("/{material_id}", response_model=schemas.Material)
def update_material(material_id: int, material: schemas.MaterialUpdate, db: Session = Depends(get_db)):
    """Update an existing material"""
    db_material = db.query(models.Material).filter(models.Material.id == material_id).first()
    if not db_material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    update_data = material.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_material, key, value)
    
    db.commit()
    db.refresh(db_material)
    return db_material


@router.delete("/{material_id}", status_code=204)
def delete_material(material_id: int, db: Session = Depends(get_db)):
    """Delete a material"""
    db_material = db.query(models.Material).filter(models.Material.id == material_id).first()
    if not db_material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    db.delete(db_material)
    db.commit()
    return None


@router.get("/category/{category}", response_model=List[schemas.Material])
def get_materials_by_category(category: str, db: Session = Depends(get_db)):
    """Get all materials in a category"""
    materials = db.query(models.Material).filter(models.Material.category == category).all()
    return materials
