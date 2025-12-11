"""
Budget routes for NEXUS API
CRUD operations for budget tracking
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import db_models as models
from .. import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.Budget])
def get_budgets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all budgets with pagination"""
    budgets = db.query(models.Budget).offset(skip).limit(limit).all()
    return budgets


@router.get("/{budget_id}", response_model=schemas.Budget)
def get_budget(budget_id: int, db: Session = Depends(get_db)):
    """Get a specific budget by ID"""
    budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget


@router.post("/", response_model=schemas.Budget, status_code=201)
def create_budget(budget: schemas.BudgetCreate, db: Session = Depends(get_db)):
    """Create a new budget"""
    # Calculate remaining amount if not provided
    budget_data = budget.model_dump()
    if budget_data.get('remaining_amount') is None:
        budget_data['remaining_amount'] = budget_data['allocated_amount'] - budget_data.get('spent_amount', 0)
    
    db_budget = models.Budget(**budget_data)
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget


@router.put("/{budget_id}", response_model=schemas.Budget)
def update_budget(budget_id: int, budget: schemas.BudgetUpdate, db: Session = Depends(get_db)):
    """Update an existing budget"""
    db_budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
    if not db_budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    update_data = budget.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_budget, key, value)
    
    # Recalculate remaining if spent or allocated changed
    if 'spent_amount' in update_data or 'allocated_amount' in update_data:
        db_budget.remaining_amount = db_budget.allocated_amount - db_budget.spent_amount
    
    db.commit()
    db.refresh(db_budget)
    return db_budget


@router.delete("/{budget_id}", status_code=204)
def delete_budget(budget_id: int, db: Session = Depends(get_db)):
    """Delete a budget"""
    db_budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
    if not db_budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    db.delete(db_budget)
    db.commit()
    return None


@router.get("/fiscal-year/{fiscal_year}", response_model=List[schemas.Budget])
def get_budgets_by_fiscal_year(fiscal_year: str, db: Session = Depends(get_db)):
    """Get all budgets for a fiscal year"""
    budgets = db.query(models.Budget).filter(models.Budget.fiscal_year == fiscal_year).all()
    return budgets


@router.get("/department/{department}", response_model=List[schemas.Budget])
def get_budgets_by_department(department: str, db: Session = Depends(get_db)):
    """Get all budgets for a department"""
    budgets = db.query(models.Budget).filter(models.Budget.department == department).all()
    return budgets


@router.get("/summary/{fiscal_year}")
def get_budget_summary(fiscal_year: str, db: Session = Depends(get_db)):
    """Get budget summary for a fiscal year"""
    budgets = db.query(models.Budget).filter(models.Budget.fiscal_year == fiscal_year).all()
    
    if not budgets:
        return {
            "fiscal_year": fiscal_year,
            "total_allocated": 0,
            "total_spent": 0,
            "total_remaining": 0,
            "utilization_percentage": 0
        }
    
    total_allocated = sum(b.allocated_amount or 0 for b in budgets)
    total_spent = sum(b.spent_amount or 0 for b in budgets)
    total_remaining = sum(b.remaining_amount or 0 for b in budgets)
    
    utilization = (total_spent / total_allocated * 100) if total_allocated > 0 else 0
    
    return {
        "fiscal_year": fiscal_year,
        "total_allocated": total_allocated,
        "total_spent": total_spent,
        "total_remaining": total_remaining,
        "utilization_percentage": round(utilization, 2)
    }
