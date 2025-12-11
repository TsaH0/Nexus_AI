"""
Material Transfer API Routes
==============================
Endpoints for managing material transfers between warehouses and substations,
including optimal procurement algorithm.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.api.database import get_db
from src.api.db_models import (
    MaterialTransfer, Warehouse, Substation, Material, InventoryStock
)
from src.api import schemas
from src.core.transfer_manager import TransferManager


router = APIRouter(prefix="/transfers", tags=["Transfers"])


# =============================================================================
# Optimal Procurement (MUST BE BEFORE /{transfer_id} routes)
# =============================================================================

@router.post("/optimal-procurement", response_model=schemas.OptimalProcurementResponse)
def find_optimal_procurement(
    request: schemas.OptimalProcurementRequest,
    db: Session = Depends(get_db)
):
    """
    Find optimal warehouses for procuring materials.
    
    Uses optimization algorithm considering:
    - Distance (35% weight)
    - Cost (35% weight)
    - Availability (20% weight)
    - Reliability (10% weight)
    
    Returns top N warehouse options sorted by optimization score.
    """
    manager = TransferManager(db)
    
    # Get substation and material info
    substation = db.query(Substation).filter(
        Substation.id == request.destination_substation_id
    ).first()
    
    if not substation:
        raise HTTPException(status_code=404, detail="Destination substation not found")
    
    material = db.query(Material).filter(
        Material.id == request.material_id
    ).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    # Find optimal warehouses
    options = manager.find_optimal_warehouses(
        destination_substation_id=request.destination_substation_id,
        material_id=request.material_id,
        quantity_needed=request.quantity_needed,
        max_options=request.max_options
    )
    
    if not options:
        return schemas.OptimalProcurementResponse(
            destination_substation_id=request.destination_substation_id,
            destination_substation_name=substation.name,
            material_id=request.material_id,
            material_name=material.name,
            quantity_needed=request.quantity_needed,
            options=[],
            recommended_option=None,
            split_recommendation=None
        )
    
    # Get recommendation
    best_option, split_plan = manager.recommend_procurement(
        destination_substation_id=request.destination_substation_id,
        material_id=request.material_id,
        quantity_needed=request.quantity_needed
    )
    
    return schemas.OptimalProcurementResponse(
        destination_substation_id=request.destination_substation_id,
        destination_substation_name=substation.name,
        material_id=request.material_id,
        material_name=material.name,
        quantity_needed=request.quantity_needed,
        options=[
            schemas.WarehouseOption(
                warehouse_id=opt.warehouse_id,
                warehouse_name=opt.warehouse_name,
                available_quantity=opt.available_quantity,
                distance_km=opt.distance_km,
                transport_cost=opt.transport_cost,
                unit_cost=opt.unit_cost,
                total_cost=opt.total_cost,
                eta_hours=opt.eta_hours,
                optimization_score=opt.optimization_score
            ) for opt in options
        ],
        recommended_option=schemas.WarehouseOption(
            warehouse_id=best_option.warehouse_id,
            warehouse_name=best_option.warehouse_name,
            available_quantity=best_option.available_quantity,
            distance_km=best_option.distance_km,
            transport_cost=best_option.transport_cost,
            unit_cost=best_option.unit_cost,
            total_cost=best_option.total_cost,
            eta_hours=best_option.eta_hours,
            optimization_score=best_option.optimization_score
        ) if best_option else None,
        split_recommendation=split_plan
    )


@router.get("/optimal-procurement/quick", response_model=dict)
def quick_optimal_lookup(
    destination_substation_id: int,
    material_id: int,
    quantity: float,
    db: Session = Depends(get_db)
):
    """
    Quick lookup for best warehouse for a material transfer.
    
    Returns the single best option without full analysis.
    """
    manager = TransferManager(db)
    
    options = manager.find_optimal_warehouses(
        destination_substation_id=destination_substation_id,
        material_id=material_id,
        quantity_needed=quantity,
        max_options=1
    )
    
    if not options:
        return {
            'found': False,
            'message': 'No warehouse found with sufficient stock'
        }
    
    best = options[0]
    return {
        'found': True,
        'warehouse_id': best.warehouse_id,
        'warehouse_name': best.warehouse_name,
        'distance_km': best.distance_km,
        'eta_hours': best.eta_hours,
        'total_cost': best.total_cost,
        'optimization_score': best.optimization_score
    }


# =============================================================================
# Distance Calculations
# =============================================================================

@router.get("/distance/calculate")
def calculate_distance(
    from_warehouse_id: int,
    to_substation_id: int,
    db: Session = Depends(get_db)
):
    """
    Calculate distance between a warehouse and substation.
    
    Uses Haversine formula for accurate great-circle distance.
    """
    manager = TransferManager(db)
    
    distance = manager.calculate_distance_between(from_warehouse_id, to_substation_id)
    
    if distance is None:
        raise HTTPException(
            status_code=400, 
            detail="Could not calculate distance - check warehouse and substation coordinates"
        )
    
    # Calculate additional info
    eta = manager.calculate_eta_hours(distance)
    
    return {
        'from_warehouse_id': from_warehouse_id,
        'to_substation_id': to_substation_id,
        'distance_km': round(distance, 2),
        'estimated_eta_hours': round(eta, 2),
        'estimated_eta_days': round(eta / 24, 2)
    }


@router.get("/distance/matrix", response_model=List[dict])
def get_distance_matrix(db: Session = Depends(get_db)):
    """
    Get distance matrix between all active warehouses.
    
    Useful for planning optimal routes.
    """
    manager = TransferManager(db)
    return manager.get_distance_matrix()


# =============================================================================
# Analytics
# =============================================================================

@router.get("/analytics/summary")
def get_transfer_analytics(db: Session = Depends(get_db)):
    """Get summary analytics for all transfers."""
    all_transfers = db.query(MaterialTransfer).all()
    
    if not all_transfers:
        return {
            'total_transfers': 0,
            'by_status': {},
            'total_distance_km': 0,
            'total_transport_cost': 0,
            'average_eta_hours': 0
        }
    
    by_status = {}
    total_distance = 0
    total_cost = 0
    total_eta = 0
    
    for t in all_transfers:
        status = t.status or 'Unknown'
        by_status[status] = by_status.get(status, 0) + 1
        total_distance += t.distance_km or 0
        total_cost += t.transport_cost or 0
        total_eta += t.estimated_eta_hours or 0
    
    return {
        'total_transfers': len(all_transfers),
        'by_status': by_status,
        'total_distance_km': round(total_distance, 2),
        'total_transport_cost': round(total_cost, 2),
        'average_eta_hours': round(total_eta / len(all_transfers), 2) if all_transfers else 0
    }


@router.get("/analytics/pending")
def get_pending_transfers(db: Session = Depends(get_db)):
    """Get all pending (planned) transfers."""
    transfers = db.query(MaterialTransfer).filter(
        MaterialTransfer.status == "Planned"
    ).all()
    
    return {
        'count': len(transfers),
        'transfers': [
            {
                'id': t.id,
                'transfer_code': t.transfer_code,
                'material_id': t.material_id,
                'quantity': t.quantity,
                'destination_substation_id': t.destination_substation_id,
                'dispatch_date': t.dispatch_date.isoformat() if t.dispatch_date else None
            }
            for t in transfers
        ]
    }


@router.get("/analytics/in-transit")
def get_in_transit_transfers(db: Session = Depends(get_db)):
    """Get all in-transit transfers."""
    transfers = db.query(MaterialTransfer).filter(
        MaterialTransfer.status == "In Transit"
    ).all()
    
    return {
        'count': len(transfers),
        'transfers': [
            {
                'id': t.id,
                'transfer_code': t.transfer_code,
                'material_id': t.material_id,
                'quantity': t.quantity,
                'expected_delivery': t.expected_delivery.isoformat() if t.expected_delivery else None
            }
            for t in transfers
        ]
    }


@router.get("/analytics/by-status")
def get_transfers_by_status(db: Session = Depends(get_db)):
    """Get transfer counts grouped by status."""
    all_transfers = db.query(MaterialTransfer).all()
    
    by_status = {}
    for t in all_transfers:
        status = t.status or 'Unknown'
        if status not in by_status:
            by_status[status] = {'count': 0, 'total_quantity': 0, 'total_cost': 0}
        by_status[status]['count'] += 1
        by_status[status]['total_quantity'] += t.quantity or 0
        by_status[status]['total_cost'] += t.transport_cost or 0
    
    return by_status


# =============================================================================
# Transfer CRUD
# =============================================================================

@router.get("/", response_model=List[schemas.MaterialTransferWithDetails])
def list_transfers(
    status: Optional[str] = None,
    source_warehouse_id: Optional[int] = None,
    destination_substation_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all material transfers with optional filtering.
    
    - **status**: Filter by status ("Planned", "In Transit", "Delivered", "Cancelled")
    - **source_warehouse_id**: Filter by source warehouse
    - **destination_substation_id**: Filter by destination substation
    """
    query = db.query(MaterialTransfer)
    
    if status:
        query = query.filter(MaterialTransfer.status == status)
    if source_warehouse_id:
        query = query.filter(MaterialTransfer.source_warehouse_id == source_warehouse_id)
    if destination_substation_id:
        query = query.filter(MaterialTransfer.destination_substation_id == destination_substation_id)
    
    transfers = query.order_by(MaterialTransfer.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for t in transfers:
        # Get related names
        warehouse = db.query(Warehouse).filter(Warehouse.id == t.source_warehouse_id).first()
        substation = db.query(Substation).filter(Substation.id == t.destination_substation_id).first()
        material = db.query(Material).filter(Material.id == t.material_id).first()
        
        result.append(schemas.MaterialTransferWithDetails(
            **{c.name: getattr(t, c.name) for c in t.__table__.columns},
            source_warehouse_name=warehouse.name if warehouse else None,
            destination_substation_name=substation.name if substation else None,
            material_name=material.name if material else None,
            project_name=None  # Add if needed
        ))
    
    return result


@router.get("/{transfer_id}", response_model=schemas.MaterialTransferWithDetails)
def get_transfer(transfer_id: int, db: Session = Depends(get_db)):
    """Get details of a specific transfer."""
    transfer = db.query(MaterialTransfer).filter(
        MaterialTransfer.id == transfer_id
    ).first()
    
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    warehouse = db.query(Warehouse).filter(Warehouse.id == transfer.source_warehouse_id).first()
    substation = db.query(Substation).filter(Substation.id == transfer.destination_substation_id).first()
    material = db.query(Material).filter(Material.id == transfer.material_id).first()
    
    return schemas.MaterialTransferWithDetails(
        **{c.name: getattr(transfer, c.name) for c in transfer.__table__.columns},
        source_warehouse_name=warehouse.name if warehouse else None,
        destination_substation_name=substation.name if substation else None,
        material_name=material.name if material else None,
        project_name=None
    )


@router.post("/", response_model=schemas.MaterialTransfer)
def create_transfer(
    transfer: schemas.MaterialTransferCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new material transfer.
    
    Automatically calculates:
    - Distance (using Haversine formula)
    - Transport cost
    - ETA
    - Optimization score
    """
    try:
        manager = TransferManager(db)
        new_transfer = manager.create_transfer(
            source_warehouse_id=transfer.source_warehouse_id,
            destination_substation_id=transfer.destination_substation_id,
            material_id=transfer.material_id,
            quantity=transfer.quantity,
            project_id=transfer.project_id
        )
        return new_transfer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{transfer_id}/dispatch", response_model=schemas.MaterialTransfer)
def dispatch_transfer(transfer_id: int, db: Session = Depends(get_db)):
    """
    Dispatch a planned transfer (mark as In Transit).
    
    This will:
    - Update status to "In Transit"
    - Set dispatch date
    - Reduce warehouse stock
    """
    try:
        manager = TransferManager(db)
        return manager.dispatch_transfer(transfer_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{transfer_id}/complete", response_model=schemas.MaterialTransfer)
def complete_transfer(transfer_id: int, db: Session = Depends(get_db)):
    """
    Mark a transfer as delivered/completed.
    """
    try:
        manager = TransferManager(db)
        return manager.complete_transfer(transfer_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{transfer_id}/cancel", response_model=schemas.MaterialTransfer)
def cancel_transfer(
    transfer_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Cancel a planned or in-transit transfer.
    
    - **reason**: Optional reason for cancellation
    """
    try:
        manager = TransferManager(db)
        return manager.cancel_transfer(transfer_id, reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
def calculate_distance(
    from_warehouse_id: int,
    to_substation_id: int,
    db: Session = Depends(get_db)
):
    """
    Calculate distance between a warehouse and substation.
    
    Uses Haversine formula for accurate great-circle distance.
    """
    manager = TransferManager(db)
    
    distance = manager.calculate_distance_between(from_warehouse_id, to_substation_id)
    
    if distance is None:
        raise HTTPException(
            status_code=400, 
            detail="Could not calculate distance - check warehouse and substation coordinates"
        )
    
    # Calculate additional info
    eta = manager.calculate_eta_hours(distance)
    
    return {
        'from_warehouse_id': from_warehouse_id,
        'to_substation_id': to_substation_id,
        'distance_km': round(distance, 2),
        'estimated_eta_hours': round(eta, 2),
        'estimated_eta_days': round(eta / 24, 2)
    }


@router.get("/distance/matrix", response_model=List[dict])
def get_distance_matrix(db: Session = Depends(get_db)):
    """
    Get distance matrix between all active warehouses.
    
    Useful for network optimization and visualization.
    """
    manager = TransferManager(db)
    return manager.get_warehouse_distance_matrix()


# =============================================================================
# Analytics
# =============================================================================

@router.get("/analytics/summary", response_model=dict)
def get_transfer_analytics(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get transfer analytics summary.
    
    - **days**: Number of days to analyze (default: 30)
    """
    from datetime import timedelta
    
    manager = TransferManager(db)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    return manager.get_transfer_summary(start_date=start_date)


@router.get("/analytics/by-status", response_model=dict)
def get_transfers_by_status(db: Session = Depends(get_db)):
    """Get count of transfers grouped by status."""
    transfers = db.query(MaterialTransfer).all()
    
    by_status = {}
    for t in transfers:
        by_status[t.status] = by_status.get(t.status, 0) + 1
    
    return by_status


@router.get("/analytics/pending", response_model=List[schemas.MaterialTransferWithDetails])
def get_pending_transfers(db: Session = Depends(get_db)):
    """Get all pending/planned transfers that need action."""
    transfers = db.query(MaterialTransfer).filter(
        MaterialTransfer.status == "Planned"
    ).order_by(MaterialTransfer.created_at).all()
    
    result = []
    for t in transfers:
        warehouse = db.query(Warehouse).filter(Warehouse.id == t.source_warehouse_id).first()
        substation = db.query(Substation).filter(Substation.id == t.destination_substation_id).first()
        material = db.query(Material).filter(Material.id == t.material_id).first()
        
        result.append(schemas.MaterialTransferWithDetails(
            **{c.name: getattr(t, c.name) for c in t.__table__.columns},
            source_warehouse_name=warehouse.name if warehouse else None,
            destination_substation_name=substation.name if substation else None,
            material_name=material.name if material else None,
            project_name=None
        ))
    
    return result


@router.get("/analytics/in-transit", response_model=List[schemas.MaterialTransferWithDetails])
def get_in_transit_transfers(db: Session = Depends(get_db)):
    """Get all transfers currently in transit."""
    transfers = db.query(MaterialTransfer).filter(
        MaterialTransfer.status == "In Transit"
    ).order_by(MaterialTransfer.dispatch_date).all()
    
    result = []
    for t in transfers:
        warehouse = db.query(Warehouse).filter(Warehouse.id == t.source_warehouse_id).first()
        substation = db.query(Substation).filter(Substation.id == t.destination_substation_id).first()
        material = db.query(Material).filter(Material.id == t.material_id).first()
        
        # Calculate if overdue
        is_overdue = False
        if t.expected_delivery and datetime.utcnow() > t.expected_delivery:
            is_overdue = True
        
        result.append(schemas.MaterialTransferWithDetails(
            **{c.name: getattr(t, c.name) for c in t.__table__.columns},
            source_warehouse_name=warehouse.name if warehouse else None,
            destination_substation_name=substation.name if substation else None,
            material_name=material.name if material else None,
            project_name=None
        ))
    
    return result
