"""
Tax routes for NEXUS API
CRUD operations for tax rates and rules
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import db_models as models
from .. import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.Tax])
def get_taxes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all taxes with pagination"""
    taxes = db.query(models.Tax).offset(skip).limit(limit).all()
    return taxes


@router.get("/active", response_model=List[schemas.Tax])
def get_active_taxes(db: Session = Depends(get_db)):
    """Get all active taxes"""
    taxes = db.query(models.Tax).filter(models.Tax.is_active == True).all()
    return taxes


@router.get("/{tax_id}", response_model=schemas.Tax)
def get_tax(tax_id: int, db: Session = Depends(get_db)):
    """Get a specific tax by ID"""
    tax = db.query(models.Tax).filter(models.Tax.id == tax_id).first()
    if not tax:
        raise HTTPException(status_code=404, detail="Tax not found")
    return tax


@router.post("/", response_model=schemas.Tax, status_code=201)
def create_tax(tax: schemas.TaxCreate, db: Session = Depends(get_db)):
    """Create a new tax"""
    existing = db.query(models.Tax).filter(models.Tax.name == tax.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tax with this name already exists")
    
    db_tax = models.Tax(**tax.model_dump())
    db.add(db_tax)
    db.commit()
    db.refresh(db_tax)
    return db_tax


@router.put("/{tax_id}", response_model=schemas.Tax)
def update_tax(tax_id: int, tax: schemas.TaxUpdate, db: Session = Depends(get_db)):
    """Update an existing tax"""
    db_tax = db.query(models.Tax).filter(models.Tax.id == tax_id).first()
    if not db_tax:
        raise HTTPException(status_code=404, detail="Tax not found")
    
    update_data = tax.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_tax, key, value)
    
    db.commit()
    db.refresh(db_tax)
    return db_tax


@router.delete("/{tax_id}", status_code=204)
def delete_tax(tax_id: int, db: Session = Depends(get_db)):
    """Delete a tax"""
    db_tax = db.query(models.Tax).filter(models.Tax.id == tax_id).first()
    if not db_tax:
        raise HTTPException(status_code=404, detail="Tax not found")
    
    db.delete(db_tax)
    db.commit()
    return None


@router.get("/state/{state}", response_model=List[schemas.Tax])
def get_taxes_by_state(state: str, db: Session = Depends(get_db)):
    """Get all taxes for a specific state"""
    taxes = db.query(models.Tax).filter(
        models.Tax.state == state,
        models.Tax.is_active == True
    ).all()
    return taxes


@router.post("/calculate")
def calculate_tax(
    amount: float,
    state: str = None,
    category: str = None,
    db: Session = Depends(get_db)
):
    """Calculate total tax for an amount"""
    query = db.query(models.Tax).filter(models.Tax.is_active == True)
    
    if state:
        query = query.filter(
            (models.Tax.state == state) | (models.Tax.state == None)
        )
    
    if category:
        query = query.filter(models.Tax.applicable_on == category)
    
    taxes = query.all()
    
    total_tax = 0
    tax_breakdown = []
    
    for tax in taxes:
        tax_amount = amount * (tax.rate_percentage / 100)
        total_tax += tax_amount
        tax_breakdown.append({
            "name": tax.name,
            "rate": tax.rate_percentage,
            "amount": round(tax_amount, 2)
        })
    
    return {
        "base_amount": amount,
        "total_tax": round(total_tax, 2),
        "final_amount": round(amount + total_tax, 2),
        "breakdown": tax_breakdown
    }
