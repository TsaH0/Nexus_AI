"""
Inventory Management API Routes
Comprehensive REST API endpoints for inventory operations
"""

import os
import uuid
import pytz
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from src.api.database import get_db
from src.api import db_models, schemas
from src.core.inventory_manager import InventoryManager
from src.core.triggers_engine import (
    TriggersEngine, 
    MaterialTriggers, 
    Severity,
    calculate_distance_km,
    estimate_delivery_eta,
    get_nearest_warehouse
)
from src.utils.logger import setup_logger
from src.services.llm_service import LLMService, AlertContext, AlertType, get_llm_service
from src.services.notification_service import NotificationService
from src.services.pdf_service import PDFService, ReportContent, get_pdf_service

# IST timezone helper
IST = pytz.timezone('Asia/Kolkata')

def get_ist_now():
    """Get current time in IST"""
    return datetime.now(IST)

logger = setup_logger("InventoryAPI")
router = APIRouter(prefix="/inventory", tags=["Inventory Management"])


# =============================================================================
# Pydantic Models for Triggers API
# =============================================================================



class TriggerMetrics(BaseModel):
    safety_stock: float
    reorder_point: float
    utr: float
    otr: float
    par: float

class TriggerStatus(BaseModel):
    severity: str
    label: str
    action: str

class TriggerContext(BaseModel):
    daily_demand: float
    lead_time_days: int
    days_of_stock: float
    nearby_substations: int
    demand_multiplier: float

class InventoryTriggerItem(BaseModel):
    item_id: str
    item_name: str
    warehouse_code: str
    warehouse_name: str
    current_stock: float
    metrics: TriggerMetrics
    status: TriggerStatus
    context: TriggerContext

class InventoryTriggersResponse(BaseModel):
    status: str
    total_items: int
    summary: Dict[str, int]
    data: List[Dict[str, Any]]

class AlertBadge(BaseModel):
    color: str
    bg: str
    text: str

class AlertMaterial(BaseModel):
    code: str
    name: str

class AlertSite(BaseModel):
    code: str
    name: str

class AlertFeedItemResponse(BaseModel):
    alert_id: str
    material: AlertMaterial
    site: AlertSite
    utr: float
    par: float
    severity: str
    severity_badge: AlertBadge
    message: str
    recommended_action: str
    created_at: str

class AlertsFeedResponse(BaseModel):
    status: str
    total_alerts: int
    critical_count: int
    warning_count: int
    data: List[Dict[str, Any]]

class SavingsFormatted(BaseModel):
    expedite_savings: str
    holding_savings: str
    total_savings: str

class SavingsBreakdown(BaseModel):
    rush_orders_avoided: int
    overstock_units_reduced: float
    optimal_orders_placed: int

class ProfitSummaryResponse(BaseModel):
    status: str
    expedite_savings: float
    holding_savings: float
    total_savings: float
    currency: str
    formatted: SavingsFormatted
    breakdown: SavingsBreakdown
    forecasted_daily_consumption: float
    consumption_unit: str

class InventoryUpdateRequest(BaseModel):
    """Request model for inventory update"""
    warehouse_id: int
    material_id: int
    new_quantity: float
    operation: str = "SET"  # SET (replace), ADD (increase), SUBTRACT (decrease)
    remarks: Optional[str] = None
    performed_by: str = "system"


class InventoryUpdateResponse(BaseModel):
    """Response model for inventory update"""
    status: str
    updated_stock: Dict[str, Any]
    metrics: Dict[str, Any]
    severity: str


class UpdateAndAlertRequest(BaseModel):
    """Request model for update with alert"""
    warehouse_id: int
    material_id: int
    new_quantity: float
    operation: str = "SET"  # SET, ADD, SUBTRACT
    remarks: Optional[str] = None
    performed_by: str = "system"
    
    # Notification settings
    email_recipient: Optional[str] = None
    whatsapp_recipient: Optional[str] = None
    
    # Understock (UTR) thresholds
    utr_email_threshold: float = 0.20  # Email if UTR > 0.20
    utr_whatsapp_threshold: float = 0.50  # WhatsApp if UTR > 0.50
    
    # Overstock (OTR) thresholds  
    otr_email_threshold: float = 0.50  # Email if OTR > 0.50
    otr_whatsapp_threshold: float = 1.0  # WhatsApp if OTR > 1.0
    
    # Include report in notification
    include_report: bool = True
    
    # PDF options
    generate_pdf: bool = True  # Generate PDF report
    attach_pdf_to_email: bool = True  # Attach PDF to email
    send_pdf_via_whatsapp: bool = True  # Send PDF via WhatsApp


class UpdateAndAlertResponse(BaseModel):
    """Response model for update with alert"""
    status: str
    updated_stock: Dict[str, Any]
    metrics: Dict[str, Any]
    severity: str
    alerts_triggered: Dict[str, Any]
    notifications_sent: Dict[str, Any]
    report: Optional[Dict[str, Any]] = None
    pdf_report: Optional[Dict[str, Any]] = None  # PDF info if generated


# =============================================================================
# Stock Level Endpoints
# =============================================================================

@router.get("/stock", response_model=List[schemas.InventoryStockWithDetails])
def get_all_stock(
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse"),
    material_id: Optional[int] = Query(None, description="Filter by material"),
    low_stock_only: bool = Query(False, description="Show only low stock items"),
    include_zero: bool = Query(False, description="Include zero stock items"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get inventory stock levels with filtering options"""
    query = db.query(
        db_models.InventoryStock,
        db_models.Material.name.label("material_name"),
        db_models.Material.material_code.label("material_code"),
        db_models.Warehouse.name.label("warehouse_name"),
        db_models.Warehouse.warehouse_code.label("warehouse_code")
    ).join(
        db_models.Material,
        db_models.InventoryStock.material_id == db_models.Material.id
    ).join(
        db_models.Warehouse,
        db_models.InventoryStock.warehouse_id == db_models.Warehouse.id
    )
    
    # Apply filters
    if warehouse_id:
        query = query.filter(db_models.InventoryStock.warehouse_id == warehouse_id)
    
    if material_id:
        query = query.filter(db_models.InventoryStock.material_id == material_id)
    
    if not include_zero:
        query = query.filter(db_models.InventoryStock.quantity_available > 0)
    
    if low_stock_only:
        query = query.filter(
            db_models.InventoryStock.quantity_available <= db_models.InventoryStock.reorder_point
        )
    
    stocks = query.offset(skip).limit(limit).all()
    
    # Format response
    result = []
    for stock, material_name, material_code, warehouse_name, warehouse_code in stocks:
        total_quantity = stock.quantity_available + stock.quantity_reserved + stock.quantity_in_transit
        
        # Determine stock status
        if stock.quantity_available <= 0:
            status = "OUT_OF_STOCK"
        elif stock.quantity_available <= stock.min_stock_level:
            status = "CRITICAL"
        elif stock.reorder_point and stock.quantity_available <= stock.reorder_point:
            status = "LOW"
        else:
            status = "OK"
        
        result.append(schemas.InventoryStockWithDetails(
            **stock.__dict__,
            material_name=material_name,
            material_code=material_code,
            warehouse_name=warehouse_name,
            warehouse_code=warehouse_code,
            total_quantity=total_quantity,
            stock_status=status
        ))
    
    return result


@router.get("/stock/{warehouse_id}/{material_id}", response_model=schemas.InventoryStockWithDetails)
def get_stock_detail(
    warehouse_id: int,
    material_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed stock information for a specific material at a warehouse"""
    result = db.query(
        db_models.InventoryStock,
        db_models.Material.name.label("material_name"),
        db_models.Material.material_code.label("material_code"),
        db_models.Warehouse.name.label("warehouse_name"),
        db_models.Warehouse.warehouse_code.label("warehouse_code")
    ).join(
        db_models.Material,
        db_models.InventoryStock.material_id == db_models.Material.id
    ).join(
        db_models.Warehouse,
        db_models.InventoryStock.warehouse_id == db_models.Warehouse.id
    ).filter(
        db_models.InventoryStock.warehouse_id == warehouse_id,
        db_models.InventoryStock.material_id == material_id
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    stock, material_name, material_code, warehouse_name, warehouse_code = result
    
    total_quantity = stock.quantity_available + stock.quantity_reserved + stock.quantity_in_transit
    
    if stock.quantity_available <= 0:
        status = "OUT_OF_STOCK"
    elif stock.quantity_available <= stock.min_stock_level:
        status = "CRITICAL"
    elif stock.reorder_point and stock.quantity_available <= stock.reorder_point:
        status = "LOW"
    else:
        status = "OK"
    
    return schemas.InventoryStockWithDetails(
        **stock.__dict__,
        material_name=material_name,
        material_code=material_code,
        warehouse_name=warehouse_name,
        warehouse_code=warehouse_code,
        total_quantity=total_quantity,
        stock_status=status
    )


@router.post("/stock", response_model=schemas.InventoryStock)
def create_stock_record(
    stock: schemas.InventoryStockCreate,
    db: Session = Depends(get_db)
):
    """Create a new inventory stock record"""
    # Check if already exists
    existing = db.query(db_models.InventoryStock).filter(
        db_models.InventoryStock.warehouse_id == stock.warehouse_id,
        db_models.InventoryStock.material_id == stock.material_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Stock record already exists")
    
    # Verify warehouse and material exist
    warehouse = db.query(db_models.Warehouse).filter(db_models.Warehouse.id == stock.warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    material = db.query(db_models.Material).filter(db_models.Material.id == stock.material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    db_stock = db_models.InventoryStock(**stock.dict())
    db.add(db_stock)
    db.commit()
    db.refresh(db_stock)
    
    logger.info(f"Created stock record for material {stock.material_id} at warehouse {stock.warehouse_id}")
    return db_stock


@router.patch("/stock/{warehouse_id}/{material_id}", response_model=schemas.InventoryStock)
def update_stock_settings(
    warehouse_id: int,
    material_id: int,
    stock_update: schemas.InventoryStockUpdate,
    db: Session = Depends(get_db)
):
    """Update stock settings (reorder points, limits, etc.)"""
    manager = InventoryManager(db)
    stock = manager.get_stock(warehouse_id, material_id)
    
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    # Update fields
    update_data = stock_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stock, field, value)
    
    stock.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(stock)
    
    logger.info(f"Updated stock settings for material {material_id} at warehouse {warehouse_id}")
    return stock


# =============================================================================
# Stock Operations Endpoints
# =============================================================================

@router.post("/operations/stock-in", response_model=schemas.InventoryStock)
def stock_in_operation(
    request: schemas.StockInRequest,
    db: Session = Depends(get_db)
):
    """Add stock to warehouse (purchase receipt, return, etc.)"""
    try:
        manager = InventoryManager(db)
        stock = manager.stock_in(
            warehouse_id=request.warehouse_id,
            material_id=request.material_id,
            quantity=request.quantity,
            unit_cost=request.unit_cost,
            vendor_id=request.vendor_id,
            reference_type=request.reference_type,
            reference_id=request.reference_id,
            remarks=request.remarks
        )
        return stock
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stock IN operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Stock IN operation failed")


@router.post("/operations/stock-out", response_model=schemas.InventoryStock)
def stock_out_operation(
    request: schemas.StockOutRequest,
    db: Session = Depends(get_db)
):
    """Remove stock from warehouse (issue to project, sale, etc.)"""
    try:
        manager = InventoryManager(db)
        stock = manager.stock_out(
            warehouse_id=request.warehouse_id,
            material_id=request.material_id,
            quantity=request.quantity,
            project_id=request.project_id,
            reference_type=request.reference_type,
            reference_id=request.reference_id,
            remarks=request.remarks
        )
        return stock
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stock OUT operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Stock OUT operation failed")


@router.post("/operations/transfer", response_model=dict)
def transfer_stock_operation(
    request: schemas.StockTransferRequest,
    db: Session = Depends(get_db)
):
    """Transfer stock between warehouses"""
    try:
        manager = InventoryManager(db)
        source_stock, dest_stock = manager.transfer_stock(
            material_id=request.material_id,
            source_warehouse_id=request.source_warehouse_id,
            destination_warehouse_id=request.destination_warehouse_id,
            quantity=request.quantity,
            remarks=request.remarks
        )
        return {
            "source_stock": schemas.InventoryStock.from_orm(source_stock),
            "destination_stock": schemas.InventoryStock.from_orm(dest_stock),
            "message": "Stock transferred successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stock TRANSFER operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Stock TRANSFER operation failed")


@router.post("/operations/adjust", response_model=schemas.InventoryStock)
def adjust_stock_operation(
    request: schemas.StockAdjustmentRequest,
    db: Session = Depends(get_db)
):
    """Adjust stock level (for corrections, damage, etc.)"""
    try:
        manager = InventoryManager(db)
        stock = manager.adjust_stock(
            warehouse_id=request.warehouse_id,
            material_id=request.material_id,
            adjustment=request.quantity_adjustment,
            remarks=request.remarks
        )
        return stock
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stock ADJUSTMENT operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Stock ADJUSTMENT operation failed")


# =============================================================================
# Transaction History Endpoints
# =============================================================================

@router.get("/transactions", response_model=List[schemas.InventoryTransactionWithDetails])
def get_transactions(
    warehouse_id: Optional[int] = None,
    material_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get inventory transaction history with filters"""
    query = db.query(
        db_models.InventoryTransaction,
        db_models.Material.name.label("material_name"),
        db_models.Warehouse.name.label("warehouse_name"),
        db_models.Project.name.label("project_name"),
        db_models.Vendor.name.label("vendor_name")
    ).join(
        db_models.Material,
        db_models.InventoryTransaction.material_id == db_models.Material.id
    ).join(
        db_models.Warehouse,
        db_models.InventoryTransaction.warehouse_id == db_models.Warehouse.id
    ).outerjoin(
        db_models.Project,
        db_models.InventoryTransaction.project_id == db_models.Project.id
    ).outerjoin(
        db_models.Vendor,
        db_models.InventoryTransaction.vendor_id == db_models.Vendor.id
    )
    
    # Apply filters
    if warehouse_id:
        query = query.filter(db_models.InventoryTransaction.warehouse_id == warehouse_id)
    
    if material_id:
        query = query.filter(db_models.InventoryTransaction.material_id == material_id)
    
    if transaction_type:
        query = query.filter(db_models.InventoryTransaction.transaction_type == transaction_type)
    
    if start_date:
        query = query.filter(db_models.InventoryTransaction.transaction_date >= start_date)
    
    if end_date:
        query = query.filter(db_models.InventoryTransaction.transaction_date <= end_date)
    
    query = query.order_by(desc(db_models.InventoryTransaction.transaction_date))
    transactions = query.offset(skip).limit(limit).all()
    
    result = []
    for txn, material_name, warehouse_name, project_name, vendor_name in transactions:
        result.append(schemas.InventoryTransactionWithDetails(
            **txn.__dict__,
            material_name=material_name,
            warehouse_name=warehouse_name,
            project_name=project_name,
            vendor_name=vendor_name
        ))
    
    return result


@router.get("/transactions/{transaction_id}", response_model=schemas.InventoryTransactionWithDetails)
def get_transaction_detail(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific transaction"""
    result = db.query(
        db_models.InventoryTransaction,
        db_models.Material.name.label("material_name"),
        db_models.Warehouse.name.label("warehouse_name"),
        db_models.Project.name.label("project_name"),
        db_models.Vendor.name.label("vendor_name")
    ).join(
        db_models.Material,
        db_models.InventoryTransaction.material_id == db_models.Material.id
    ).join(
        db_models.Warehouse,
        db_models.InventoryTransaction.warehouse_id == db_models.Warehouse.id
    ).outerjoin(
        db_models.Project,
        db_models.InventoryTransaction.project_id == db_models.Project.id
    ).outerjoin(
        db_models.Vendor,
        db_models.InventoryTransaction.vendor_id == db_models.Vendor.id
    ).filter(
        db_models.InventoryTransaction.id == transaction_id
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    txn, material_name, warehouse_name, project_name, vendor_name = result
    
    return schemas.InventoryTransactionWithDetails(
        **txn.__dict__,
        material_name=material_name,
        warehouse_name=warehouse_name,
        project_name=project_name,
        vendor_name=vendor_name
    )


# =============================================================================
# Stock Reservation Endpoints
# =============================================================================

@router.post("/reservations", response_model=schemas.StockReservation)
def create_reservation(
    request: schemas.ReserveStockRequest,
    db: Session = Depends(get_db)
):
    """Reserve stock for a project"""
    try:
        manager = InventoryManager(db)
        reservation = manager.reserve_stock(
            warehouse_id=request.warehouse_id,
            material_id=request.material_id,
            project_id=request.project_id,
            quantity=request.quantity,
            required_by_date=request.required_by_date,
            priority=request.priority,
            remarks=request.remarks
        )
        return reservation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stock RESERVATION failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Stock RESERVATION failed")


@router.get("/reservations", response_model=List[schemas.StockReservationWithDetails])
def get_reservations(
    warehouse_id: Optional[int] = None,
    material_id: Optional[int] = None,
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get stock reservations with filters"""
    query = db.query(
        db_models.StockReservation,
        db_models.Material.name.label("material_name"),
        db_models.Material.material_code.label("material_code"),
        db_models.Warehouse.name.label("warehouse_name"),
        db_models.Project.name.label("project_name")
    ).join(
        db_models.Material,
        db_models.StockReservation.material_id == db_models.Material.id
    ).join(
        db_models.Warehouse,
        db_models.StockReservation.warehouse_id == db_models.Warehouse.id
    ).join(
        db_models.Project,
        db_models.StockReservation.project_id == db_models.Project.id
    )
    
    # Apply filters
    if warehouse_id:
        query = query.filter(db_models.StockReservation.warehouse_id == warehouse_id)
    
    if material_id:
        query = query.filter(db_models.StockReservation.material_id == material_id)
    
    if project_id:
        query = query.filter(db_models.StockReservation.project_id == project_id)
    
    if status:
        query = query.filter(db_models.StockReservation.status == status)
    
    query = query.order_by(desc(db_models.StockReservation.reservation_date))
    reservations = query.offset(skip).limit(limit).all()
    
    result = []
    for res, material_name, material_code, warehouse_name, project_name in reservations:
        quantity_remaining = res.quantity_reserved - res.quantity_issued
        result.append(schemas.StockReservationWithDetails(
            **res.__dict__,
            material_name=material_name,
            material_code=material_code,
            warehouse_name=warehouse_name,
            project_name=project_name,
            quantity_remaining=quantity_remaining
        ))
    
    return result


@router.post("/reservations/{reservation_id}/issue", response_model=schemas.StockReservation)
def issue_reserved_stock(
    reservation_id: int,
    request: schemas.IssueStockRequest,
    db: Session = Depends(get_db)
):
    """Issue stock against a reservation"""
    try:
        manager = InventoryManager(db)
        reservation = manager.issue_reserved_stock(
            reservation_id=reservation_id,
            quantity_to_issue=request.quantity_to_issue,
            remarks=request.remarks
        )
        return reservation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Issue reserved stock failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Issue reserved stock failed")


@router.post("/reservations/{reservation_id}/cancel", response_model=schemas.StockReservation)
def cancel_reservation(
    reservation_id: int,
    remarks: str = Query(..., description="Reason for cancellation"),
    db: Session = Depends(get_db)
):
    """Cancel a stock reservation"""
    try:
        manager = InventoryManager(db)
        reservation = manager.cancel_reservation(
            reservation_id=reservation_id,
            remarks=remarks
        )
        return reservation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Cancel reservation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Cancel reservation failed")


# =============================================================================
# Alert Endpoints
# =============================================================================

@router.get("/alerts", response_model=List[schemas.StockAlertWithDetails])
def get_alerts(
    alert_type: Optional[str] = None,
    severity: Optional[str] = None,
    warehouse_id: Optional[int] = None,
    material_id: Optional[int] = None,
    is_resolved: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get stock alerts with filters"""
    query = db.query(
        db_models.StockAlert,
        db_models.Material.name.label("material_name"),
        db_models.Warehouse.name.label("warehouse_name")
    ).outerjoin(
        db_models.Material,
        db_models.StockAlert.material_id == db_models.Material.id
    ).outerjoin(
        db_models.Warehouse,
        db_models.StockAlert.warehouse_id == db_models.Warehouse.id
    )
    
    # Apply filters
    if alert_type:
        query = query.filter(db_models.StockAlert.alert_type == alert_type)
    
    if severity:
        query = query.filter(db_models.StockAlert.severity == severity)
    
    if warehouse_id:
        query = query.filter(db_models.StockAlert.warehouse_id == warehouse_id)
    
    if material_id:
        query = query.filter(db_models.StockAlert.material_id == material_id)
    
    if is_resolved is not None:
        query = query.filter(db_models.StockAlert.is_resolved == is_resolved)
    
    query = query.order_by(desc(db_models.StockAlert.alert_date))
    alerts = query.offset(skip).limit(limit).all()
    
    result = []
    for alert, material_name, warehouse_name in alerts:
        result.append(schemas.StockAlertWithDetails(
            **alert.__dict__,
            material_name=material_name,
            warehouse_name=warehouse_name
        ))
    
    return result


@router.patch("/alerts/{alert_id}/resolve", response_model=schemas.StockAlert)
def resolve_alert(
    alert_id: int,
    resolved_by: str = Query(..., description="User resolving the alert"),
    db: Session = Depends(get_db)
):
    """Manually resolve a stock alert"""
    alert = db.query(db_models.StockAlert).filter(
        db_models.StockAlert.id == alert_id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = resolved_by
    
    db.commit()
    db.refresh(alert)
    
    logger.info(f"Alert {alert_id} resolved by {resolved_by}")
    return alert


# =============================================================================
# Analytics Endpoints
# =============================================================================

@router.get("/analytics/summary", response_model=schemas.InventorySummary)
def get_inventory_summary(db: Session = Depends(get_db)):
    """Get overall inventory summary and statistics"""
    manager = InventoryManager(db)
    summary = manager.get_inventory_summary()
    
    # Add reserved value
    reserved_value = db.query(
        func.sum(db_models.InventoryStock.quantity_reserved * db_models.Material.unit_price)
    ).join(
        db_models.Material,
        db_models.InventoryStock.material_id == db_models.Material.id
    ).scalar() or 0.0
    
    summary["total_reserved_value"] = round(reserved_value, 2)
    
    return schemas.InventorySummary(**summary)


@router.get("/analytics/warehouse/{warehouse_id}", response_model=schemas.WarehouseInventorySummary)
def get_warehouse_inventory_summary(
    warehouse_id: int,
    db: Session = Depends(get_db)
):
    """Get inventory summary for a specific warehouse"""
    warehouse = db.query(db_models.Warehouse).filter(
        db_models.Warehouse.id == warehouse_id
    ).first()
    
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Count materials
    total_materials = db.query(db_models.InventoryStock).filter(
        db_models.InventoryStock.warehouse_id == warehouse_id,
        db_models.InventoryStock.quantity_available > 0
    ).count()
    
    # Calculate total value
    stock_value = db.query(
        func.sum(db_models.InventoryStock.quantity_available * db_models.Material.unit_price)
    ).join(
        db_models.Material,
        db_models.InventoryStock.material_id == db_models.Material.id
    ).filter(
        db_models.InventoryStock.warehouse_id == warehouse_id
    ).scalar() or 0.0
    
    # Count alerts
    low_stock_count = db.query(db_models.InventoryStock).filter(
        db_models.InventoryStock.warehouse_id == warehouse_id,
        db_models.InventoryStock.quantity_available <= db_models.InventoryStock.reorder_point,
        db_models.InventoryStock.quantity_available > 0
    ).count()
    
    out_of_stock_count = db.query(db_models.InventoryStock).filter(
        db_models.InventoryStock.warehouse_id == warehouse_id,
        db_models.InventoryStock.quantity_available <= 0
    ).count()
    
    return schemas.WarehouseInventorySummary(
        warehouse_id=warehouse_id,
        warehouse_name=warehouse.name,
        total_materials=total_materials,
        total_stock_value=round(stock_value, 2),
        capacity_utilization=None,  # Can be calculated if warehouse capacity is tracked
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count
    )


@router.get("/analytics/material/{material_id}", response_model=schemas.MaterialInventorySummary)
def get_material_inventory_summary(
    material_id: int,
    db: Session = Depends(get_db)
):
    """Get inventory summary for a specific material across all warehouses"""
    material = db.query(db_models.Material).filter(
        db_models.Material.id == material_id
    ).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    # Get aggregated data
    stock_data = db.query(
        func.sum(db_models.InventoryStock.quantity_available).label("total_available"),
        func.sum(db_models.InventoryStock.quantity_reserved).label("total_reserved"),
        func.sum(db_models.InventoryStock.quantity_in_transit).label("total_in_transit"),
        func.count(db_models.InventoryStock.id).label("warehouse_count"),
        func.avg(db_models.InventoryStock.quantity_available).label("avg_stock")
    ).filter(
        db_models.InventoryStock.material_id == material_id
    ).first()
    
    total_available = stock_data.total_available or 0.0
    total_reserved = stock_data.total_reserved or 0.0
    total_in_transit = stock_data.total_in_transit or 0.0
    warehouses_with_stock = stock_data.warehouse_count or 0
    avg_stock = stock_data.avg_stock or 0.0
    
    # Determine status
    if total_available <= 0:
        status = "OUT_OF_STOCK"
    elif total_available < avg_stock * 0.3:
        status = "CRITICAL"
    elif total_available < avg_stock * 0.5:
        status = "LOW"
    else:
        status = "OK"
    
    return schemas.MaterialInventorySummary(
        material_id=material_id,
        material_name=material.name,
        material_code=material.material_code or f"MAT-{material_id:03d}",
        total_available=round(total_available, 2),
        total_reserved=round(total_reserved, 2),
        total_in_transit=round(total_in_transit, 2),
        warehouses_with_stock=warehouses_with_stock,
        avg_stock_level=round(avg_stock, 2),
        status=status
    )


# =============================================================================
# INVENTORY TRIGGERS API - The Mathematical Brain
# =============================================================================

@router.get("/triggers", response_model=InventoryTriggersResponse)
def get_inventory_triggers(
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse"),
    severity_filter: Optional[str] = Query(None, description="Filter by severity: RED, AMBER, GREEN"),
    include_green: bool = Query(False, description="Include GREEN (optimal) items"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    🧠 **INVENTORY TRIGGERS - The Mathematical Brain**
    
    Computes dynamic inventory metrics for all materials:
    - **Safety Stock (SS)**: Minimum buffer stock needed
    - **Reorder Point (ROP)**: When to trigger reorder
    - **UTR (Understock Ratio)**: 0-1, higher = more understocked
    - **OTR (Overstock Ratio)**: 0-1, higher = more overstocked  
    - **PAR (Procurement Adequacy Ratio)**: 0-1, higher = better stocked
    
    Severity Levels:
    - **RED**: Critical, immediate action required
    - **AMBER**: Warning, monitor closely
    - **GREEN**: Optimal, no action needed
    
    All calculations are DYNAMIC based on nearby substations and demand patterns.
    """
    
    engine = TriggersEngine(db)
    triggers_list = []
    
    # Query inventory stocks with material and warehouse info
    query = db.query(
        db_models.InventoryStock,
        db_models.Material,
        db_models.Warehouse
    ).join(
        db_models.Material,
        db_models.InventoryStock.material_id == db_models.Material.id
    ).join(
        db_models.Warehouse,
        db_models.InventoryStock.warehouse_id == db_models.Warehouse.id
    )
    
    if warehouse_id:
        query = query.filter(db_models.InventoryStock.warehouse_id == warehouse_id)
    
    stocks = query.all()
    
    # Get all substations for demand calculation
    all_substations = db.query(db_models.Substation).all()
    
    for stock, material, warehouse in stocks:
        # Find nearby substations (within 200km)
        nearby_substations = []
        if warehouse.latitude and warehouse.longitude:
            for sub in all_substations:
                if sub.latitude and sub.longitude:
                    distance = calculate_distance_km(
                        warehouse.latitude, warehouse.longitude,
                        sub.latitude, sub.longitude
                    )
                    if distance <= 200:  # Within 200km
                        nearby_substations.append({
                            "substation_code": sub.substation_code,
                            "name": sub.name,
                            "capacity": sub.capacity or "33kV",
                            "distance_km": distance
                        })
        
        # Calculate daily demand from recent transactions
        thirty_days_ago = datetime.now() - timedelta(days=30)
        consumption = db.query(
            func.sum(db_models.InventoryTransaction.quantity)
        ).filter(
            db_models.InventoryTransaction.warehouse_id == warehouse.id,
            db_models.InventoryTransaction.material_id == material.id,
            db_models.InventoryTransaction.transaction_type == "OUT",
            db_models.InventoryTransaction.transaction_date >= thirty_days_ago
        ).scalar() or 0
        
        historical_daily_demand = consumption / 30 if consumption > 0 else None
        
        # Compute triggers
        trigger = engine.compute_triggers(
            material_code=material.material_code or f"MAT-{material.id:03d}",
            material_name=material.name,
            warehouse_code=warehouse.warehouse_code or f"WH-{warehouse.id:03d}",
            warehouse_name=warehouse.name,
            current_stock=stock.quantity_available,
            lead_time_days=material.lead_time_days or 14,
            unit_price=material.unit_price or 50000,
            nearby_substations=nearby_substations,
            historical_daily_demand=historical_daily_demand,
            max_stock_level=stock.max_stock_level,
            min_stock_level=stock.min_stock_level
        )
        
        triggers_list.append(trigger)
    
    # Filter by severity if requested
    if severity_filter:
        try:
            sev = Severity(severity_filter.upper())
            triggers_list = [t for t in triggers_list if t.severity == sev]
        except ValueError:
            pass
    
    # Remove GREEN unless include_green is True
    if not include_green:
        triggers_list = [t for t in triggers_list if t.severity != Severity.GREEN]
    
    # Sort by severity (RED first)
    severity_order = {Severity.RED: 0, Severity.AMBER: 1, Severity.GREEN: 2}
    triggers_list.sort(key=lambda x: (severity_order[x.severity], -x.utr))
    
    # Paginate
    total = len(triggers_list)
    triggers_list = triggers_list[skip:skip + limit]
    
    # Summary counts
    summary = {
        "red": sum(1 for t in triggers_list if t.severity == Severity.RED),
        "amber": sum(1 for t in triggers_list if t.severity == Severity.AMBER),
        "green": sum(1 for t in triggers_list if t.severity == Severity.GREEN)
    }
    
    return InventoryTriggersResponse(
        status="success",
        total_items=total,
        summary=summary,
        data=[t.to_dict() for t in triggers_list]
    )


@router.get("/triggers/{warehouse_id}/{material_id}")
def compute_single_trigger(
    warehouse_id: int,
    material_id: int,
    db: Session = Depends(get_db)
):
    """
    Compute triggers for a specific material at a specific warehouse.
    Returns detailed metrics including SS, ROP, UTR, OTR, PAR.
    """
    
    # Get stock record
    stock = db.query(db_models.InventoryStock).filter(
        db_models.InventoryStock.warehouse_id == warehouse_id,
        db_models.InventoryStock.material_id == material_id
    ).first()
    
    if not stock:
        raise HTTPException(status_code=404, detail="Stock record not found")
    
    material = db.query(db_models.Material).filter(db_models.Material.id == material_id).first()
    warehouse = db.query(db_models.Warehouse).filter(db_models.Warehouse.id == warehouse_id).first()
    
    if not material or not warehouse:
        raise HTTPException(status_code=404, detail="Material or warehouse not found")
    
    # Find nearby substations
    nearby_substations = []
    if warehouse.latitude and warehouse.longitude:
        substations = db.query(db_models.Substation).all()
        for sub in substations:
            if sub.latitude and sub.longitude:
                distance = calculate_distance_km(
                    warehouse.latitude, warehouse.longitude,
                    sub.latitude, sub.longitude
                )
                if distance <= 200:
                    nearby_substations.append({
                        "substation_code": sub.substation_code,
                        "name": sub.name,
                        "capacity": sub.capacity or "33kV",
                        "distance_km": round(distance, 2)
                    })
    
    # Calculate historical demand
    thirty_days_ago = datetime.now() - timedelta(days=30)
    consumption = db.query(
        func.sum(db_models.InventoryTransaction.quantity)
    ).filter(
        db_models.InventoryTransaction.warehouse_id == warehouse_id,
        db_models.InventoryTransaction.material_id == material_id,
        db_models.InventoryTransaction.transaction_type == "OUT",
        db_models.InventoryTransaction.transaction_date >= thirty_days_ago
    ).scalar() or 0
    
    historical_daily_demand = consumption / 30 if consumption > 0 else None
    
    engine = TriggersEngine(db)
    trigger = engine.compute_triggers(
        material_code=material.material_code or f"MAT-{material.id:03d}",
        material_name=material.name,
        warehouse_code=warehouse.warehouse_code or f"WH-{warehouse.id:03d}",
        warehouse_name=warehouse.name,
        current_stock=stock.quantity_available,
        lead_time_days=material.lead_time_days or 14,
        unit_price=material.unit_price or 50000,
        nearby_substations=nearby_substations,
        historical_daily_demand=historical_daily_demand,
        max_stock_level=stock.max_stock_level,
        min_stock_level=stock.min_stock_level
    )
    
    result = trigger.to_dict()
    result["nearby_substations_detail"] = nearby_substations
    
    return {
        "status": "success",
        "data": result
    }


# =============================================================================
# TRIGGER SIMULATION API
# =============================================================================

class TriggerSimulationRequest(BaseModel):
    """Request model for trigger simulation"""
    item_name: str = Field("Simulated Item", description="Name of the item")
    current_stock: float = Field(..., description="Current stock level")
    safety_stock: float = Field(..., description="Safety stock level")
    reorder_point: float = Field(..., description="Reorder point")
    item_type: str = Field("General", description="Type of item (for demand multiplier)")
    lead_time_days: int = Field(14, description="Lead time in days")
    max_stock_level: Optional[float] = Field(None, description="Maximum stock level")
    daily_demand: Optional[float] = Field(None, description="Historical daily demand")


@router.post("/triggers/simulate")
def simulate_trigger(
    request: TriggerSimulationRequest,
    db: Session = Depends(get_db)
):
    """
    🧪 **SIMULATE TRIGGER CALCULATION**
    
    Simulates trigger calculations with custom values.
    Does NOT modify any data - purely for testing/simulation.
    
    Returns computed metrics:
    - UTR (Understock Ratio): 0-1, higher = more understocked
    - OTR (Overstock Ratio): 0-1, higher = more overstocked
    - PAR (Procurement Adequacy Ratio): 0-1, higher = better stocked
    - Severity (RED/AMBER/GREEN) and recommended action
    """
    
    current_stock = request.current_stock
    safety_stock = request.safety_stock
    reorder_point = request.reorder_point
    max_stock_level = request.max_stock_level or (reorder_point * 2.5)
    lead_time_days = request.lead_time_days
    
    # Use provided daily demand or estimate
    if request.daily_demand:
        daily_demand = request.daily_demand
    else:
        demand_estimates = {
            "Transformer": 0.5,
            "Tower": 2.0,
            "Conductor": 10.0,
            "Insulator": 5.0,
            "Hardware": 20.0,
            "General": 5.0
        }
        daily_demand = demand_estimates.get(request.item_type, 5.0)
    
    # ===== DIRECT CALCULATIONS (no engine override) =====
    
    # UTR (Understock Ratio): How understocked are we?
    # UTR = max(0, (Reorder Point - Current Stock) / Reorder Point)
    if reorder_point > 0:
        utr = max(0.0, (reorder_point - current_stock) / reorder_point)
    else:
        utr = 0.0
    utr = min(utr, 1.0)  # Cap at 1
    
    # OTR (Overstock Ratio): How overstocked are we?
    # OTR = max(0, (Current Stock - Max Stock) / Max Stock)
    if max_stock_level > 0:
        otr = max(0.0, (current_stock - max_stock_level) / max_stock_level)
    else:
        otr = 0.0
    
    # PAR (Procurement Adequacy Ratio): How adequate is our stock?
    # PAR = Current Stock / (Reorder Point + Buffer)
    buffer = daily_demand * 7  # 7 days buffer
    denominator = reorder_point + buffer
    if denominator > 0:
        par = current_stock / denominator
    else:
        par = 1.0
    par = min(par, 2.0)  # Cap at 2.0
    
    # Days of stock
    if daily_demand > 0:
        days_of_stock = current_stock / daily_demand
    else:
        days_of_stock = 999
    
    # Determine severity based on metrics
    if utr > 0.5 or days_of_stock < lead_time_days or par < 0.3:
        severity = "RED"
        label = "CRITICAL UNDERSTOCK"
        action = "Immediate Procurement Required"
    elif otr > 0.5:
        severity = "AMBER"
        label = "OVERSTOCK WARNING"
        action = "Review Ordering Patterns"
    elif utr > 0.3 or days_of_stock < lead_time_days * 1.2 or par < 0.6:
        severity = "AMBER"
        label = "LOW STOCK WARNING"
        action = "Plan Procurement Soon"
    elif otr > 0.2:
        severity = "GREEN"
        label = "SLIGHT OVERSTOCK"
        action = "Monitor Consumption"
    else:
        severity = "GREEN"
        label = "OPTIMAL STOCK"
        action = "No Action Required"
    
    # Build response
    result = {
        "item_id": "SIM-001",
        "item_name": request.item_name,
        "warehouse_code": "SIM-WH",
        "warehouse_name": "Simulation Warehouse",
        "current_stock": current_stock,
        "metrics": {
            "safety_stock": round(safety_stock, 2),
            "reorder_point": round(reorder_point, 2),
            "utr": round(utr, 4),
            "otr": round(otr, 4),
            "par": round(par, 4)
        },
        "status": {
            "severity": severity,
            "label": label,
            "action": action
        },
        "context": {
            "daily_demand": round(daily_demand, 2),
            "lead_time_days": lead_time_days,
            "days_of_stock": round(days_of_stock, 2),
            "nearby_substations": 0,
            "demand_multiplier": 1.0
        },
        "simulation": {
            "is_simulation": True,
            "input": {
                "item_name": request.item_name,
                "current_stock": current_stock,
                "safety_stock": safety_stock,
                "reorder_point": reorder_point,
                "max_stock_level": max_stock_level,
                "lead_time_days": lead_time_days,
                "daily_demand_used": daily_demand
            }
        }
    }
    
    return {
        "status": "success",
        "data": result
    }


# Also support POST to /triggers for backwards compatibility with frontend
@router.post("/triggers")
def simulate_trigger_compat(
    request: TriggerSimulationRequest,
    db: Session = Depends(get_db)
):
    """
    🧪 **TRIGGER SIMULATION (Compatibility)**
    
    Same as POST /triggers/simulate - simulates trigger calculations.
    """
    return simulate_trigger(request, db)


# =============================================================================
# ALERTS FEED API
# =============================================================================

@router.get("/alerts/feed", response_model=AlertsFeedResponse)
def get_alerts_feed(
    severity: Optional[str] = Query(None, description="Filter: RED, AMBER, or ALL"),
    warehouse_id: Optional[int] = Query(None, description="Filter by warehouse"),
    limit: int = Query(50, description="Max alerts to return"),
    db: Session = Depends(get_db)
):
    """
    🚨 **ALERTS FEED**
    
    Returns an array of computed alerts for materials that need attention.
    Each alert includes:
    - Material info (code, name)
    - Site info (code, name)
    - UTR and PAR values
    - Severity badge (RED/AMBER/GREEN)
    - Recommended action
    
    Perfect for displaying in a monitoring dashboard with severity badges.
    """
    
    engine = TriggersEngine(db)
    
    # Get all triggers first
    query = db.query(
        db_models.InventoryStock,
        db_models.Material,
        db_models.Warehouse
    ).join(
        db_models.Material,
        db_models.InventoryStock.material_id == db_models.Material.id
    ).join(
        db_models.Warehouse,
        db_models.InventoryStock.warehouse_id == db_models.Warehouse.id
    )
    
    if warehouse_id:
        query = query.filter(db_models.InventoryStock.warehouse_id == warehouse_id)
    
    stocks = query.all()
    all_substations = db.query(db_models.Substation).all()
    
    triggers_list = []
    
    for stock, material, warehouse in stocks:
        # Find nearby substations
        nearby_substations = []
        if warehouse.latitude and warehouse.longitude:
            for sub in all_substations:
                if sub.latitude and sub.longitude:
                    distance = calculate_distance_km(
                        warehouse.latitude, warehouse.longitude,
                        sub.latitude, sub.longitude
                    )
                    if distance <= 200:
                        nearby_substations.append({
                            "capacity": sub.capacity or "33kV"
                        })
        
        trigger = engine.compute_triggers(
            material_code=material.material_code or f"MAT-{material.id:03d}",
            material_name=material.name,
            warehouse_code=warehouse.warehouse_code or f"WH-{warehouse.id:03d}",
            warehouse_name=warehouse.name,
            current_stock=stock.quantity_available,
            min_stock_level=stock.min_stock_level,
            lead_time_days=material.lead_time_days or 14,
            unit_price=material.unit_price or 50000,
            nearby_substations=nearby_substations
        )
        
        triggers_list.append(trigger)
    
    # Filter by severity
    severity_filter = None
    if severity and severity.upper() != "ALL":
        try:
            sev = Severity(severity.upper())
            severity_filter = [sev]
        except ValueError:
            pass
    
    # Generate alerts feed
    alerts = engine.generate_alerts_feed(triggers_list, severity_filter)
    
    # Limit results
    alerts = alerts[:limit]
    
    # Count by severity
    critical_count = sum(1 for a in alerts if a.severity == Severity.RED)
    warning_count = sum(1 for a in alerts if a.severity == Severity.AMBER)
    
    return AlertsFeedResponse(
        status="success",
        total_alerts=len(alerts),
        critical_count=critical_count,
        warning_count=warning_count,
        data=[a.to_dict() for a in alerts]
    )


# =============================================================================
# PROFIT SUMMARY API
# =============================================================================

@router.get("/profit/summary", response_model=ProfitSummaryResponse)
def get_profit_summary(
    db: Session = Depends(get_db)
):
    """
    💰 **PROFIT SUMMARY**
    
    Returns cost savings from inventory optimization:
    - **Expedite Savings**: Money saved by avoiding rush orders
    - **Holding Savings**: Money saved by reducing overstock
    - **Total Savings**: Combined savings
    
    Also includes:
    - Forecasted daily consumption
    - Breakdown of optimizations
    """
    
    engine = TriggersEngine(db)
    
    # Get all inventory data
    stocks = db.query(
        db_models.InventoryStock,
        db_models.Material,
        db_models.Warehouse
    ).join(
        db_models.Material,
        db_models.InventoryStock.material_id == db_models.Material.id
    ).join(
        db_models.Warehouse,
        db_models.InventoryStock.warehouse_id == db_models.Warehouse.id
    ).all()
    
    all_substations = db.query(db_models.Substation).all()
    triggers_list = []
    total_daily_consumption = 0.0
    unit_prices = {}
    
    for stock, material, warehouse in stocks:
        # Find nearby substations
        nearby_substations = []
        if warehouse.latitude and warehouse.longitude:
            for sub in all_substations:
                if sub.latitude and sub.longitude:
                    distance = calculate_distance_km(
                        warehouse.latitude, warehouse.longitude,
                        sub.latitude, sub.longitude
                    )
                    if distance <= 200:
                        nearby_substations.append({
                            "capacity": sub.capacity or "33kV"
                        })
        
        trigger = engine.compute_triggers(
            material_code=material.material_code or f"MAT-{material.id:03d}",
            material_name=material.name,
            warehouse_code=warehouse.warehouse_code or f"WH-{warehouse.id:03d}",
            warehouse_name=warehouse.name,
            current_stock=stock.quantity_available,
            min_stock_level=stock.min_stock_level,
            lead_time_days=material.lead_time_days or 14,
            unit_price=material.unit_price or 50000,
            nearby_substations=nearby_substations
        )
        
        triggers_list.append(trigger)
        total_daily_consumption += trigger.daily_demand
        unit_prices[trigger.item_id] = material.unit_price or 50000
    
    # Compute profit summary
    profit = engine.compute_profit_summary(triggers_list, unit_prices)
    profit_dict = profit.to_dict()
    
    return ProfitSummaryResponse(
        status="success",
        expedite_savings=profit_dict["expedite_savings"],
        holding_savings=profit_dict["holding_savings"],
        total_savings=profit_dict["total_savings"],
        currency=profit_dict["currency"],
        formatted=SavingsFormatted(**profit_dict["formatted"]),
        breakdown=SavingsBreakdown(**profit_dict["breakdown"]),
        forecasted_daily_consumption=round(total_daily_consumption, 2),
        consumption_unit="units/day"
    )


# =============================================================================
# MOCK PURCHASE ORDER WITH ETA
# =============================================================================

class CreatePORequest(BaseModel):
    """Request to create a purchase order"""
    material_id: int
    warehouse_id: int
    quantity: int
    vendor_id: Optional[int] = None
    user_latitude: Optional[float] = None
    user_longitude: Optional[float] = None
    transport_mode: str = "road"

class POCreatedResponse(BaseModel):
    """Response after creating a purchase order"""
    status: str
    message: str
    order_code: str
    material_name: str
    warehouse_name: str
    quantity: int
    eta: Dict[str, Any]
    inventory_updated: bool
    new_stock_in_transit: float


@router.post("/purchase-order/create", response_model=POCreatedResponse)
def create_purchase_order(
    request: CreatePORequest,
    db: Session = Depends(get_db)
):
    """
    🛒 **CREATE PURCHASE ORDER**
    
    Creates a mock purchase order that:
    1. Updates inventory (adds to in_transit quantity)
    2. Calculates ETA based on distance from vendor/warehouse
    3. Returns a success response with order details
    
    Provide user coordinates to calculate distance and ETA.
    This is a PLACEHOLDER - actual logistics API integration coming later.
    """
    
    # Validate material and warehouse
    material = db.query(db_models.Material).filter(
        db_models.Material.id == request.material_id
    ).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    warehouse = db.query(db_models.Warehouse).filter(
        db_models.Warehouse.id == request.warehouse_id
    ).first()
    
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Calculate distance and ETA
    distance_km = 0.0
    if request.user_latitude and request.user_longitude:
        # Calculate from user location to warehouse
        if warehouse.latitude and warehouse.longitude:
            distance_km = calculate_distance_km(
                request.user_latitude, request.user_longitude,
                warehouse.latitude, warehouse.longitude
            )
    else:
        # Default distance based on lead time
        distance_km = (material.lead_time_days or 14) * 40  # Assume 40 km/day
    
    eta = estimate_delivery_eta(distance_km, request.transport_mode)
    
    # Generate order code
    order_code = f"PO-{datetime.now().strftime('%Y%m%d%H%M%S')}-{material.id:03d}"
    
    # Update inventory - add to in_transit
    stock = db.query(db_models.InventoryStock).filter(
        db_models.InventoryStock.warehouse_id == request.warehouse_id,
        db_models.InventoryStock.material_id == request.material_id
    ).first()
    
    inventory_updated = False
    new_in_transit = request.quantity
    
    if stock:
        stock.quantity_in_transit = (stock.quantity_in_transit or 0) + request.quantity
        stock.updated_at = datetime.now()
        new_in_transit = stock.quantity_in_transit
        inventory_updated = True
    else:
        # Create new stock record
        new_stock = db_models.InventoryStock(
            warehouse_id=request.warehouse_id,
            material_id=request.material_id,
            quantity_available=0,
            quantity_reserved=0,
            quantity_in_transit=request.quantity,
            reorder_point=100,
            max_stock_level=1000,
            min_stock_level=50
        )
        db.add(new_stock)
        inventory_updated = True
    
    # Create transaction record
    transaction = db_models.InventoryTransaction(
        transaction_type="IN_TRANSIT",
        warehouse_id=request.warehouse_id,
        material_id=request.material_id,
        quantity=request.quantity,
        unit_cost=material.unit_price or 50000,
        total_cost=(material.unit_price or 50000) * request.quantity,
        reference_type="PO",
        reference_id=order_code,
        vendor_id=request.vendor_id,
        remarks=f"Purchase order created. ETA: {eta['estimated_days']} days",
        performed_by="SYSTEM",
        transaction_date=datetime.now()
    )
    db.add(transaction)
    
    # Create purchase order record
    po = db_models.PurchaseOrder(
        order_code=order_code,
        material_id=request.material_id,
        vendor_id=request.vendor_id,
        warehouse_id=request.warehouse_id,
        quantity=request.quantity,
        unit_price=material.unit_price or 50000,
        total_cost=(material.unit_price or 50000) * request.quantity,
        tax_amount=0,
        transport_cost=eta.get("distance_km", 0) * 50,  # ₹50 per km
        landed_cost=(material.unit_price or 50000) * request.quantity + eta.get("distance_km", 0) * 50,
        order_date=datetime.now(),
        expected_delivery_date=datetime.now() + timedelta(days=eta["estimated_days"]),
        status="Placed",
        reasoning=f"Auto-generated PO via API. Distance: {eta['distance_km']:.2f} km"
    )
    db.add(po)
    
    db.commit()
    
    logger.info(f"Created PO {order_code} for {request.quantity} units of {material.name}")
    
    return POCreatedResponse(
        status="success",
        message=f"PO Created Successfully 🎉",
        order_code=order_code,
        material_name=material.name,
        warehouse_name=warehouse.name,
        quantity=request.quantity,
        eta=eta,
        inventory_updated=inventory_updated,
        new_stock_in_transit=new_in_transit
    )


@router.get("/delivery-eta")
def calculate_delivery_eta_endpoint(
    from_lat: float = Query(..., description="Origin latitude"),
    from_lon: float = Query(..., description="Origin longitude"),
    to_lat: float = Query(..., description="Destination latitude"),
    to_lon: float = Query(..., description="Destination longitude"),
    transport_mode: str = Query("road", description="Transport mode: road, rail, air, express"),
    use_osrm: bool = Query(True, description="Use OSRM for real road distance (set False for Haversine)")
):
    """
    📍 **CALCULATE DELIVERY ETA**
    
    Calculate estimated delivery time between two coordinates using OSRM.
    
    **Features:**
    - Uses OSRM (Open Source Routing Machine) for real road distances
    - Falls back to Haversine calculation if OSRM unavailable
    - Supports multiple transport modes with speed adjustments
    
    **Transport Modes:**
    - `road`: Standard road transport (~40 km/h average)
    - `express`: Express/priority transport (~60 km/h)
    - `rail`: Rail transport (~80 km/h)
    - `air`: Air freight (for long distances)
    
    **Environment Variables (optional):**
    - `OSRM_URL`: Custom OSRM server URL (default: public OSRM)
    - `OSRM_API_KEY`: API key for private OSRM servers
    """
    from src.services.osrm_service import OSRMService
    
    if use_osrm:
        # Use OSRM for real road-based routing
        osrm = OSRMService()
        result = osrm.get_route(from_lat, from_lon, to_lat, to_lon, transport_mode)
        
        return {
            "status": "success",
            "from": {"latitude": from_lat, "longitude": from_lon},
            "to": {"latitude": to_lat, "longitude": to_lon},
            "distance_km": result.distance_km,
            "eta": {
                "duration_minutes": round(result.duration_minutes, 2),
                "readable": result.eta_readable,
                "transport_mode": transport_mode
            },
            "calculation_source": result.source,
            "note": "OSRM provides real road-based routing" if result.source == "osrm" else "Fallback to Haversine estimation"
        }
    else:
        # Use simple Haversine (legacy behavior)
        distance = calculate_distance_km(from_lat, from_lon, to_lat, to_lon)
        eta = estimate_delivery_eta(distance, transport_mode)
        
        return {
            "status": "success",
            "from": {"latitude": from_lat, "longitude": from_lon},
            "to": {"latitude": to_lat, "longitude": to_lon},
            "distance_km": distance,
            "eta": eta,
            "calculation_source": "haversine"
        }


@router.get("/nearest-warehouse")
def find_nearest_warehouse(
    latitude: float = Query(..., description="User latitude"),
    longitude: float = Query(..., description="User longitude"),
    material_id: Optional[int] = Query(None, description="Filter warehouses with this material"),
    db: Session = Depends(get_db)
):
    """
    📍 **FIND NEAREST WAREHOUSE**
    
    Find the nearest warehouse to given coordinates.
    Optionally filter by warehouses that have a specific material in stock.
    Always shows total stock count for each warehouse.
    """
    
    query = db.query(db_models.Warehouse).filter(db_models.Warehouse.is_active == True)
    
    warehouses = query.all()
    warehouse_list = []
    
    for wh in warehouses:
        if wh.latitude and wh.longitude:
            distance = calculate_distance_km(latitude, longitude, wh.latitude, wh.longitude)
            
            # Always get total stock for warehouse
            total_stock = db.query(
                func.sum(db_models.InventoryStock.quantity_available)
            ).filter(
                db_models.InventoryStock.warehouse_id == wh.id
            ).scalar() or 0
            
            # Get material count
            material_count = db.query(
                func.count(db_models.InventoryStock.id)
            ).filter(
                db_models.InventoryStock.warehouse_id == wh.id,
                db_models.InventoryStock.quantity_available > 0
            ).scalar() or 0
            
            # Check specific material if filter applied
            has_material = True
            specific_stock = None
            if material_id:
                stock = db.query(db_models.InventoryStock).filter(
                    db_models.InventoryStock.warehouse_id == wh.id,
                    db_models.InventoryStock.material_id == material_id
                ).first()
                has_material = stock is not None and stock.quantity_available > 0
                specific_stock = stock.quantity_available if stock else 0
            
            if not material_id or has_material:
                warehouse_list.append({
                    "warehouse_id": wh.id,
                    "warehouse_code": wh.warehouse_code,
                    "name": wh.name,
                    "city": wh.city,
                    "state": wh.state,
                    "latitude": wh.latitude,
                    "longitude": wh.longitude,
                    "distance_km": round(distance, 2),
                    "total_stock_units": round(total_stock, 2),
                    "materials_in_stock": material_count,
                    "specific_material_stock": specific_stock if material_id else None
                })
    
    # Sort by distance
    warehouse_list.sort(key=lambda x: x["distance_km"])
    
    nearest = warehouse_list[0] if warehouse_list else None
    eta = None
    
    if nearest:
        eta = estimate_delivery_eta(nearest["distance_km"])
    
    return {
        "status": "success",
        "user_location": {"latitude": latitude, "longitude": longitude},
        "nearest_warehouse": nearest,
        "delivery_eta": eta,
        "all_warehouses": warehouse_list[:5]  # Top 5 nearest
    }



@router.put("/update")
def update_inventory_stock(
    request: InventoryUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    📦 **UPDATE INVENTORY STOCK**
    
    Update the quantity of a material at a specific warehouse.
    Returns updated stock with computed UTR/OTR/PAR metrics.
    
    Operations:
    - SET: Replace current quantity with new_quantity
    - ADD: Increase current quantity by new_quantity
    - SUBTRACT: Decrease current quantity by new_quantity
    """
    
    # Get warehouse and material
    warehouse = db.query(db_models.Warehouse).filter(
        db_models.Warehouse.id == request.warehouse_id
    ).first()
    
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    material = db.query(db_models.Material).filter(
        db_models.Material.id == request.material_id
    ).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    # Get or create stock record
    manager = InventoryManager(db)
    stock = manager.get_or_create_stock(request.warehouse_id, request.material_id)
    
    old_quantity = stock.quantity_available
    
    # Apply operation
    if request.operation.upper() == "SET":
        new_quantity = request.new_quantity
    elif request.operation.upper() == "ADD":
        new_quantity = stock.quantity_available + request.new_quantity
    elif request.operation.upper() == "SUBTRACT":
        new_quantity = stock.quantity_available - request.new_quantity
        if new_quantity < 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot subtract {request.new_quantity}. Current stock is {stock.quantity_available}"
            )
    else:
        raise HTTPException(status_code=400, detail="Invalid operation. Use SET, ADD, or SUBTRACT")
    
    # Update stock
    stock.quantity_available = new_quantity
    stock.updated_at = datetime.utcnow()
    
    # Create transaction record
    change = new_quantity - old_quantity
    transaction_type = "IN" if change > 0 else "OUT" if change < 0 else "ADJUSTMENT"
    
    transaction = db_models.InventoryTransaction(
        transaction_type=transaction_type,
        warehouse_id=request.warehouse_id,
        material_id=request.material_id,
        quantity=abs(change),
        reference_type="MANUAL_UPDATE",
        remarks=request.remarks or f"Stock updated via API: {request.operation} {request.new_quantity}",
        performed_by=request.performed_by,
        transaction_date=datetime.utcnow()
    )
    db.add(transaction)
    db.commit()
    db.refresh(stock)
    
    # Calculate triggers/metrics
    triggers_engine = TriggersEngine(db)
    triggers = triggers_engine.compute_triggers(
        material_code=material.material_code,
        material_name=material.name,
        warehouse_code=warehouse.warehouse_code,
        warehouse_name=warehouse.name,
        current_stock=stock.quantity_available,
        lead_time_days=material.lead_time_days or 14,
        unit_price=material.unit_price or 0,
        max_stock_level=stock.max_stock_level,
        min_stock_level=stock.min_stock_level
    )
    
    return {
        "status": "success",
        "updated_stock": {
            "warehouse_id": warehouse.id,
            "warehouse_code": warehouse.warehouse_code,
            "warehouse_name": warehouse.name,
            "material_id": material.id,
            "material_code": material.material_code,
            "material_name": material.name,
            "old_quantity": old_quantity,
            "new_quantity": stock.quantity_available,
            "change": change
        },
        "metrics": {
            "safety_stock": round(triggers.safety_stock, 2),
            "reorder_point": round(triggers.reorder_point, 2),
            "utr": round(triggers.utr, 4),
            "otr": round(triggers.otr, 4),
            "par": round(triggers.par, 4),
            "days_of_stock": round(triggers.days_of_stock, 1)
        },
        "severity": triggers.severity.value
    }


@router.post("/update-and-alert")
def update_inventory_with_alert(
    request: UpdateAndAlertRequest,
    db: Session = Depends(get_db)
):
    """
    🚨 **UPDATE INVENTORY WITH SMART ALERTS**
    
    Updates inventory and automatically sends alerts based on UTR/OTR thresholds:
    
    **Understock (UTR) thresholds:**
    - Email: Sent if UTR > 0.20 (low stock warning)
    - WhatsApp: Sent if UTR > 0.50 (critical stock alert)
    
    **Overstock (OTR) thresholds:**
    - Email: Sent if OTR > 0.50 (low overstock warning)
    - WhatsApp: Sent if OTR > 1.0 (severe overstock alert)
    
    Alert messages are generated using AI (Groq LLM) for contextual,
    human-readable notifications about understocking or overstocking.
    
    Includes optional report with:
    - Transaction history
    - Optimal stock levels
    - Current status and recommendations
    """
    
    # Get warehouse and material
    warehouse = db.query(db_models.Warehouse).filter(
        db_models.Warehouse.id == request.warehouse_id
    ).first()
    
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    material = db.query(db_models.Material).filter(
        db_models.Material.id == request.material_id
    ).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    # Get or create stock record
    manager = InventoryManager(db)
    stock = manager.get_or_create_stock(request.warehouse_id, request.material_id)
    
    old_quantity = stock.quantity_available
    
    # Apply operation
    if request.operation.upper() == "SET":
        new_quantity = request.new_quantity
    elif request.operation.upper() == "ADD":
        new_quantity = stock.quantity_available + request.new_quantity
    elif request.operation.upper() == "SUBTRACT":
        new_quantity = stock.quantity_available - request.new_quantity
        if new_quantity < 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot subtract {request.new_quantity}. Current stock is {stock.quantity_available}"
            )
    else:
        raise HTTPException(status_code=400, detail="Invalid operation. Use SET, ADD, or SUBTRACT")
    
    # Update stock
    stock.quantity_available = new_quantity
    stock.updated_at = datetime.utcnow()
    
    # Create transaction record
    change = new_quantity - old_quantity
    transaction_type = "IN" if change > 0 else "OUT" if change < 0 else "ADJUSTMENT"
    
    transaction = db_models.InventoryTransaction(
        transaction_type=transaction_type,
        warehouse_id=request.warehouse_id,
        material_id=request.material_id,
        quantity=abs(change),
        reference_type="MANUAL_UPDATE",
        remarks=request.remarks or f"Stock updated via API: {request.operation} {request.new_quantity}",
        performed_by=request.performed_by,
        transaction_date=datetime.utcnow()
    )
    db.add(transaction)
    db.commit()
    db.refresh(stock)
    
    # Calculate triggers/metrics
    triggers_engine = TriggersEngine(db)
    triggers = triggers_engine.compute_triggers(
        material_code=material.material_code,
        material_name=material.name,
        warehouse_code=warehouse.warehouse_code,
        warehouse_name=warehouse.name,
        current_stock=stock.quantity_available,
        lead_time_days=material.lead_time_days or 14,
        unit_price=material.unit_price or 0,
        max_stock_level=stock.max_stock_level,
        min_stock_level=stock.min_stock_level
    )
    
    # Determine alert type based on metrics
    utr = triggers.utr
    otr = triggers.otr
    max_ratio = max(utr, otr)
    
    if utr > otr and utr > 0.1:
        alert_type = AlertType.UNDERSTOCK if utr > 0.5 else AlertType.REORDER
    elif otr > utr and otr > 0.1:
        alert_type = AlertType.OVERSTOCK
    else:
        alert_type = AlertType.OK
    
    # Determine if alerts should be triggered based on separate UTR/OTR thresholds
    # Understock: UTR > 0.20 for email, UTR > 0.50 for WhatsApp
    # Overstock: OTR > 0.50 for email, OTR > 1.0 for WhatsApp
    utr_triggers_email = utr > request.utr_email_threshold
    utr_triggers_whatsapp = utr > request.utr_whatsapp_threshold
    otr_triggers_email = otr > request.otr_email_threshold
    otr_triggers_whatsapp = otr > request.otr_whatsapp_threshold
    
    should_alert_email = utr_triggers_email or otr_triggers_email
    should_alert_whatsapp = utr_triggers_whatsapp or otr_triggers_whatsapp
    
    # Determine reason for alert
    if utr > otr:
        alert_reason = "understock"
        active_ratio = utr
    elif otr > utr:
        alert_reason = "overstock"
        active_ratio = otr
    else:
        alert_reason = None
        active_ratio = 0
    
    # Initialize response
    alerts_triggered = {
        "email_triggered": False,
        "whatsapp_triggered": False,
        "reason": alert_reason,
        "utr": round(utr, 4),
        "otr": round(otr, 4),
        "thresholds": {
            "utr_email": request.utr_email_threshold,
            "utr_whatsapp": request.utr_whatsapp_threshold,
            "otr_email": request.otr_email_threshold,
            "otr_whatsapp": request.otr_whatsapp_threshold
        }
    }
    
    notifications_sent = {
        "email": {"sent": False, "recipient": None, "error": None},
        "whatsapp": {"sent": False, "recipient": None, "error": None}
    }
    
    report = None
    llm_alert = None
    
    if should_alert_email or should_alert_whatsapp:
        # Build alert context for LLM
        location = f"{warehouse.city}, {warehouse.state}" if warehouse.city else warehouse.state or "India"
        
        alert_context = AlertContext(
            material_name=material.name,
            material_code=material.material_code,
            warehouse_name=warehouse.name,
            warehouse_code=warehouse.warehouse_code,
            location=location,
            current_stock=stock.quantity_available,
            reorder_point=triggers.reorder_point,
            safety_stock=triggers.safety_stock,
            max_stock_level=stock.max_stock_level or triggers.reorder_point * 2.5,
            utr=utr,
            otr=otr,
            par=triggers.par,
            days_of_stock=triggers.days_of_stock,
            lead_time_days=material.lead_time_days or 14,
            daily_demand=triggers.daily_demand,
            alert_type=alert_type,
            severity=triggers.severity.value
        )
        
        # Generate alert using LLM
        llm_service = get_llm_service()
        llm_alert = llm_service.generate_alert(alert_context)
        
        history = db.query(db_models.InventoryTransaction).filter(
            db_models.InventoryTransaction.warehouse_id == request.warehouse_id,
            db_models.InventoryTransaction.material_id == request.material_id
        ).order_by(
            db_models.InventoryTransaction.transaction_date.desc()
        ).limit(10).all()
        
        history_list = [
            {
                "date": h.transaction_date.isoformat() if h.transaction_date else None,
                "type": h.transaction_type,
                "quantity": h.quantity,
                "remarks": h.remarks,
                "performed_by": h.performed_by
            }
            for h in history
        ]
        
        # Generate PDF if requested
        pdf_bytes = None
        pdf_base64 = None
        pdf_filename = None
        
        if request.generate_pdf:
            try:
                pdf_service = get_pdf_service()
                report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
                optimal_stock = triggers.reorder_point * 1.5
                
                report_content = ReportContent(
                    title="NEXUS Inventory Alert Report",
                    subtitle=f"{material.name} - {warehouse.name}",
                    material_name=material.name,
                    material_code=material.material_code,
                    warehouse_name=warehouse.name,
                    warehouse_code=warehouse.warehouse_code,
                    location=location,
                    current_stock=stock.quantity_available,
                    optimal_stock=optimal_stock,
                    reorder_point=triggers.reorder_point,
                    safety_stock=triggers.safety_stock,
                    max_stock_level=stock.max_stock_level or triggers.reorder_point * 2.5,
                    utr=utr,
                    otr=otr,
                    par=triggers.par,
                    days_of_stock=triggers.days_of_stock,
                    daily_demand=triggers.daily_demand,
                    severity=triggers.severity.value,
                    alert_type=alert_type.value,
                    history=history_list,
                    summary=llm_alert.summary,
                    recommendations=llm_alert.recommended_actions,
                    detailed_analysis=llm_alert.message,
                    generated_at=get_ist_now(),
                    report_id=report_id
                )
                
                pdf_bytes = pdf_service.generate_report(report_content)
                pdf_base64 = pdf_service.generate_report_base64(report_content)
                pdf_filename = f"NEXUS_Alert_{material.material_code}_{get_ist_now().strftime('%Y%m%d_%H%M%S')}.pdf"
                
                logger.info(f"Generated PDF report: {pdf_filename} ({len(pdf_bytes)} bytes)")
            except Exception as e:
                logger.error(f"PDF generation failed: {str(e)}")
        
        # Initialize notification service
        notification_service = NotificationService()
        
        # Send Email if threshold exceeded
        if should_alert_email:
            alerts_triggered["email_triggered"] = True
            email_recipient = request.email_recipient or os.getenv("DEFAULT_ALERT_EMAIL")
            
            if email_recipient:
                try:
                    # Prepare attachments if PDF is generated and should be attached
                    email_attachments = None
                    if pdf_base64 and request.attach_pdf_to_email:
                        email_attachments = [{
                            "Name": pdf_filename,
                            "Content": pdf_base64,
                            "ContentType": "application/pdf"
                        }]
                    
                    result = notification_service.send_email(
                        to_email=email_recipient,
                        subject=llm_alert.subject,
                        body=llm_alert.message,
                        attachments=email_attachments
                    )
                    notifications_sent["email"] = {
                        "sent": result.success,
                        "recipient": email_recipient,
                        "message_id": result.message_id,
                        "pdf_attached": bool(email_attachments),
                        "error": result.error
                    }
                except Exception as e:
                    logger.error(f"Email sending failed: {str(e)}")
                    notifications_sent["email"]["error"] = str(e)
        
        # Send WhatsApp if threshold exceeded
        if should_alert_whatsapp:
            alerts_triggered["whatsapp_triggered"] = True
            whatsapp_recipient = request.whatsapp_recipient or os.getenv("WHATSAPP_BUSINESS_NUMBER")
            
            if whatsapp_recipient:
                try:
                    # First send the text message
                    result = notification_service.send_whatsapp(
                        phone_number=whatsapp_recipient,
                        message=llm_alert.whatsapp_message
                    )
                    notifications_sent["whatsapp"] = {
                        "sent": result.success,
                        "recipient": whatsapp_recipient,
                        "message_id": result.message_id,
                        "error": result.error
                    }
                    
                    # Then send PDF document if generated and requested
                    if pdf_bytes and request.send_pdf_via_whatsapp:
                        doc_result = notification_service.send_whatsapp_document(
                            phone_number=whatsapp_recipient,
                            document_bytes=pdf_bytes,
                            filename=pdf_filename,
                            caption=f"📊 {llm_alert.summary}"
                        )
                        notifications_sent["whatsapp"]["document_sent"] = doc_result.success
                        notifications_sent["whatsapp"]["document_message_id"] = doc_result.message_id
                        if doc_result.error:
                            notifications_sent["whatsapp"]["document_error"] = doc_result.error
                            
                except Exception as e:
                    logger.error(f"WhatsApp sending failed: {str(e)}")
                    notifications_sent["whatsapp"]["error"] = str(e)
    
    # Prepare pdf_report info for response
    pdf_report = None
    if request.generate_pdf and 'pdf_bytes' in dir() and pdf_bytes:
        pdf_report = {
            "generated": True,
            "filename": pdf_filename,
            "size_bytes": len(pdf_bytes),
            "attached_to_email": request.attach_pdf_to_email and should_alert_email,
            "sent_via_whatsapp": request.send_pdf_via_whatsapp and should_alert_whatsapp
        }
    
    # Generate report if requested
    report = None
    if request.include_report:
        # Get transaction history (if not already fetched for PDF)
        if 'history_list' not in dir() or not history_list:
            history = db.query(db_models.InventoryTransaction).filter(
                db_models.InventoryTransaction.warehouse_id == request.warehouse_id,
                db_models.InventoryTransaction.material_id == request.material_id
            ).order_by(
                db_models.InventoryTransaction.transaction_date.desc()
            ).limit(10).all()
            
            history_list = [
                {
                    "date": h.transaction_date.isoformat() if h.transaction_date else None,
                    "type": h.transaction_type,
                    "quantity": h.quantity,
                    "remarks": h.remarks,
                    "performed_by": h.performed_by
                }
                for h in history
            ]
        
        # Calculate optimal values
        optimal_stock = triggers.reorder_point * 1.5  # Midpoint between ROP and max
        stock_gap = optimal_stock - stock.quantity_available
        
        report = {
            "material": {
                "id": material.id,
                "code": material.material_code,
                "name": material.name,
                "category": material.category,
                "unit": material.unit,
                "unit_price": material.unit_price,
                "lead_time_days": material.lead_time_days
            },
            "warehouse": {
                "id": warehouse.id,
                "code": warehouse.warehouse_code,
                "name": warehouse.name,
                "city": warehouse.city,
                "state": warehouse.state,
                "region": warehouse.region
            },
            "stock_status": {
                "current_quantity": stock.quantity_available,
                "optimal_quantity": round(optimal_stock, 2),
                "gap": round(stock_gap, 2),
                "gap_percentage": round((stock_gap / optimal_stock) * 100, 1) if optimal_stock > 0 else 0,
                "status": "understocked" if stock_gap > 0 else "overstocked" if stock_gap < 0 else "optimal"
            },
            "metrics": {
                "safety_stock": round(triggers.safety_stock, 2),
                "reorder_point": round(triggers.reorder_point, 2),
                "max_stock_level": round(stock.max_stock_level or triggers.reorder_point * 2.5, 2),
                "utr": round(utr, 4),
                "otr": round(otr, 4),
                "par": round(triggers.par, 4),
                "days_of_stock": round(triggers.days_of_stock, 1),
                "daily_demand": round(triggers.daily_demand, 2)
            },
            "history": history_list,
            "recommendations": llm_alert.recommended_actions if llm_alert else [],
            "generated_at": get_ist_now().isoformat()
        }
    
    return {
        "status": "success",
        "updated_stock": {
            "warehouse_id": warehouse.id,
            "warehouse_code": warehouse.warehouse_code,
            "warehouse_name": warehouse.name,
            "material_id": material.id,
            "material_code": material.material_code,
            "material_name": material.name,
            "old_quantity": old_quantity,
            "new_quantity": stock.quantity_available,
            "change": change
        },
        "metrics": {
            "safety_stock": round(triggers.safety_stock, 2),
            "reorder_point": round(triggers.reorder_point, 2),
            "utr": round(utr, 4),
            "otr": round(otr, 4),
            "par": round(triggers.par, 4),
            "days_of_stock": round(triggers.days_of_stock, 1)
        },
        "severity": triggers.severity.value,
        "alerts_triggered": alerts_triggered,
        "notifications_sent": notifications_sent,
        "report": report,
        "pdf_report": pdf_report
    }


@router.get("/report/{warehouse_id}/{material_id}")
def get_inventory_report(
    warehouse_id: int,
    material_id: int,
    include_llm_analysis: bool = Query(False, description="Include AI-generated analysis"),
    db: Session = Depends(get_db)
):
    """
    📊 **GET INVENTORY REPORT**
    
    Generate a comprehensive report for a specific material at a warehouse.
    
    Includes:
    - Current stock status
    - Optimal stock levels
    - Transaction history
    - UTR/OTR/PAR metrics
    - Optional AI-generated analysis and recommendations
    """
    
    # Get warehouse and material
    warehouse = db.query(db_models.Warehouse).filter(
        db_models.Warehouse.id == warehouse_id
    ).first()
    
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    material = db.query(db_models.Material).filter(
        db_models.Material.id == material_id
    ).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    # Get stock record
    stock = db.query(db_models.InventoryStock).filter(
        db_models.InventoryStock.warehouse_id == warehouse_id,
        db_models.InventoryStock.material_id == material_id
    ).first()
    
    if not stock:
        raise HTTPException(status_code=404, detail="No stock record found for this material at this warehouse")
    
    # Calculate triggers/metrics
    triggers_engine = TriggersEngine(db)
    triggers = triggers_engine.compute_triggers(
        material_code=material.material_code,
        material_name=material.name,
        warehouse_code=warehouse.warehouse_code,
        warehouse_name=warehouse.name,
        current_stock=stock.quantity_available,
        lead_time_days=material.lead_time_days or 14,
        unit_price=material.unit_price or 0,
        max_stock_level=stock.max_stock_level,
        min_stock_level=stock.min_stock_level
    )
    
    # Get transaction history
    history = db.query(db_models.InventoryTransaction).filter(
        db_models.InventoryTransaction.warehouse_id == warehouse_id,
        db_models.InventoryTransaction.material_id == material_id
    ).order_by(
        db_models.InventoryTransaction.transaction_date.desc()
    ).limit(20).all()
    
    history_list = [
        {
            "id": h.id,
            "date": h.transaction_date.isoformat() if h.transaction_date else None,
            "type": h.transaction_type,
            "quantity": h.quantity,
            "reference_type": h.reference_type,
            "reference_id": h.reference_id,
            "remarks": h.remarks,
            "performed_by": h.performed_by
        }
        for h in history
    ]
    
    # Calculate optimal values
    optimal_stock = triggers.reorder_point * 1.5
    stock_gap = optimal_stock - stock.quantity_available
    
    report = {
        "material": {
            "id": material.id,
            "code": material.material_code,
            "name": material.name,
            "category": material.category,
            "unit": material.unit,
            "unit_price": material.unit_price,
            "lead_time_days": material.lead_time_days,
            "min_order_quantity": material.min_order_quantity
        },
        "warehouse": {
            "id": warehouse.id,
            "code": warehouse.warehouse_code,
            "name": warehouse.name,
            "city": warehouse.city,
            "state": warehouse.state,
            "region": warehouse.region,
            "latitude": warehouse.latitude,
            "longitude": warehouse.longitude
        },
        "stock_status": {
            "current_quantity": stock.quantity_available,
            "reserved_quantity": stock.quantity_reserved,
            "in_transit_quantity": stock.quantity_in_transit,
            "total_quantity": stock.quantity_available + stock.quantity_reserved + stock.quantity_in_transit,
            "optimal_quantity": round(optimal_stock, 2),
            "gap": round(stock_gap, 2),
            "gap_percentage": round((stock_gap / optimal_stock) * 100, 1) if optimal_stock > 0 else 0,
            "status": "understocked" if stock_gap > 0 else "overstocked" if stock_gap < 0 else "optimal",
            "last_restocked": stock.last_restocked_date.isoformat() if stock.last_restocked_date else None,
            "last_issued": stock.last_issued_date.isoformat() if stock.last_issued_date else None
        },
        "metrics": {
            "safety_stock": round(triggers.safety_stock, 2),
            "reorder_point": round(triggers.reorder_point, 2),
            "max_stock_level": round(stock.max_stock_level or triggers.reorder_point * 2.5, 2),
            "min_stock_level": round(stock.min_stock_level or 0, 2),
            "utr": round(triggers.utr, 4),
            "otr": round(triggers.otr, 4),
            "par": round(triggers.par, 4),
            "days_of_stock": round(triggers.days_of_stock, 1),
            "daily_demand": round(triggers.daily_demand, 2)
        },
        "severity": triggers.severity.value,
        "history": {
            "total_transactions": len(history_list),
            "recent_transactions": history_list
        },
        "generated_at": get_ist_now().isoformat()
    }
    
    # Optional LLM analysis
    if include_llm_analysis:
        llm_service = get_llm_service()
        
        # Determine alert type
        if triggers.utr > triggers.otr and triggers.utr > 0.1:
            alert_type = AlertType.UNDERSTOCK if triggers.utr > 0.5 else AlertType.REORDER
        elif triggers.otr > triggers.utr and triggers.otr > 0.1:
            alert_type = AlertType.OVERSTOCK
        else:
            alert_type = AlertType.OK
        
        location = f"{warehouse.city}, {warehouse.state}" if warehouse.city else warehouse.state or "India"
        
        analysis_content = llm_service.generate_report_content(
            material_name=material.name,
            material_code=material.material_code,
            warehouse_name=warehouse.name,
            current_stock=stock.quantity_available,
            optimal_stock=optimal_stock,
            history=history_list,
            metrics={
                "utr": triggers.utr,
                "otr": triggers.otr,
                "days_of_stock": triggers.days_of_stock
            }
        )
        
        report["ai_analysis"] = {
            "content": analysis_content,
            "alert_type": alert_type.value,
            "generated_by": "Groq LLM (Llama 3.3)"
        }
    
    return {
        "status": "success",
        "report": report
    }


