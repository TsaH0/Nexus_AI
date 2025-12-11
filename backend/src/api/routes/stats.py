"""
System Stats API Routes
Provides overall system health, procurement metrics, and shortage analysis

Key Distinctions:
- WAREHOUSES/INVENTORY have stock status: understocked, overstocked, normal, critical
- PROJECTS/SUBSTATIONS have operational status: halted, delayed, at-risk, on-track
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ..database import get_db
from .. import db_models as models


router = APIRouter(tags=["System Stats"])


@router.get("/")
def get_system_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get comprehensive system statistics using dynamic data.
    
    Returns:
    - Procurement health score (0-100) based on actual inventory & orders
    - Inventory status: warehouses that are understocked/overstocked
    - Project status: projects that are halted/delayed/at-risk
    - Material shortage risks from actual demand data
    - Orders in transit summary
    - Open issues count
    """
    from src.forecasting.material_forecast import MaterialForecastEngine
    
    # Use forecast engine for consistent data
    engine = MaterialForecastEngine(db_session=db)
    warehouse_status = engine._get_warehouse_status()
    active_projects = engine._get_active_projects()
    
    # Warehouse/Inventory status (NOT substations - warehouses have stock)
    total_warehouses = len(warehouse_status)
    understocked = sum(1 for w in warehouse_status if w['stock_status'] in ['Understocked', 'Critical'])
    overstocked = sum(1 for w in warehouse_status if w['stock_status'] == 'Overstocked')
    normal_stock = sum(1 for w in warehouse_status if w['stock_status'] == 'Normal')
    critical_stock = sum(1 for w in warehouse_status if w['stock_status'] == 'Critical')
    
    # Project status (projects have halted/delayed status, NOT stock)
    total_projects = len(active_projects)
    halted_projects = sum(1 for p in active_projects if p['health_status'] == 'Halted')
    delayed_projects = sum(1 for p in active_projects if p['health_status'] == 'Delayed')
    at_risk_projects = sum(1 for p in active_projects if p['health_status'] == 'At Risk')
    on_track_projects = sum(1 for p in active_projects if p['health_status'] == 'On Track')
    
    # Order metrics
    total_orders = db.query(models.PurchaseOrder).count()
    orders_in_transit = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.status == 'In_Transit'
    ).count()
    orders_delayed = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.status == 'Delayed'
    ).count()
    orders_pending = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.status.in_(['Placed', 'Manufacturing'])
    ).count()
    
    # Material shortage metrics
    material_needs = db.query(models.ProjectMaterialNeed).filter(
        models.ProjectMaterialNeed.quantity_shortage > 0
    ).all()
    
    materials_at_risk = sum(1 for m in material_needs if m.priority == 'Medium')
    materials_critical = sum(1 for m in material_needs if m.priority in ['High', 'Critical'])
    total_shortage_value = sum(
        (m.quantity_shortage or 0) * (m.unit_price or 0) 
        for m in material_needs
    )
    
    # Project issues
    open_issues = db.query(models.ProjectIssue).filter(
        models.ProjectIssue.status.in_(['Open', 'In Progress'])
    ).count() if hasattr(models, 'ProjectIssue') else 0
    
    critical_issues = db.query(models.ProjectIssue).filter(
        models.ProjectIssue.status.in_(['Open', 'In Progress']),
        models.ProjectIssue.severity == 'Critical'
    ).count() if hasattr(models, 'ProjectIssue') else 0
    
    # Calculate procurement health score
    # Factors: orders on time, stock levels, shortage gaps
    health_factors = []
    
    # Order health (40% weight)
    if total_orders > 0:
        order_health = ((total_orders - orders_delayed) / total_orders) * 100
        health_factors.append(order_health * 0.4)
    else:
        health_factors.append(40)  # No orders = assume healthy
    
    # Inventory health (30% weight) - using warehouse status
    if total_warehouses > 0:
        inventory_health = ((total_warehouses - understocked) / total_warehouses) * 100
        health_factors.append(inventory_health * 0.3)
    else:
        health_factors.append(30)
    
    # Shortage health (30% weight)
    total_material_needs = db.query(models.ProjectMaterialNeed).count()
    if total_material_needs > 0:
        shortage_health = ((total_material_needs - materials_critical - materials_at_risk) / total_material_needs) * 100
        health_factors.append(max(0, shortage_health) * 0.3)
    else:
        health_factors.append(30)
    
    procurement_health_score = sum(health_factors)
    
    # Determine health status
    if procurement_health_score >= 80:
        health_status = "Healthy"
    elif procurement_health_score >= 60:
        health_status = "At Risk"
    elif procurement_health_score >= 40:
        health_status = "Warning"
    else:
        health_status = "Critical"
    
    return {
        "generated_at": datetime.now().isoformat(),
        "procurement_health": {
            "score": round(procurement_health_score, 1),
            "status": health_status,
            "factors": {
                "order_fulfillment": round(health_factors[0] / 0.4, 1) if health_factors else 0,
                "inventory_levels": round(health_factors[1] / 0.3, 1) if len(health_factors) > 1 else 0,
                "shortage_management": round(health_factors[2] / 0.3, 1) if len(health_factors) > 2 else 0
            }
        },
        # Projects have operational status (halted/delayed), NOT stock status
        "projects": {
            "total": total_projects,
            "halted": halted_projects,
            "delayed": delayed_projects,
            "at_risk": at_risk_projects,
            "on_track": on_track_projects
        },
        # Inventory/Warehouses have stock status (understocked/overstocked)
        "inventory": {
            "total_warehouses": total_warehouses,
            "understocked": understocked,
            "overstocked": overstocked,
            "normal": normal_stock,
            "critical": critical_stock
        },
        "orders": {
            "total": total_orders,
            "pending": orders_pending,
            "in_transit": orders_in_transit,
            "delayed": orders_delayed
        },
        "material_risks": {
            "at_risk": materials_at_risk,
            "critical": materials_critical,
            "total_shortage_value": round(total_shortage_value, 2)
        },
        "issues": {
            "open": open_issues,
            "critical": critical_issues
        }
    }


@router.get("/orders/in-transit")
def get_orders_in_transit(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Get all orders currently in transit.
    
    Returns detailed information about each order including:
    - Material details
    - Vendor information
    - Expected delivery date
    - Current status
    """
    orders = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.status.in_(['In_Transit', 'Manufacturing', 'Placed'])
    ).order_by(models.PurchaseOrder.expected_delivery_date).all()
    
    result = []
    for order in orders:
        material = db.query(models.Material).filter(
            models.Material.id == order.material_id
        ).first()
        
        vendor = db.query(models.Vendor).filter(
            models.Vendor.id == order.vendor_id
        ).first() if order.vendor_id else None
        
        warehouse = db.query(models.Warehouse).filter(
            models.Warehouse.id == order.warehouse_id
        ).first() if order.warehouse_id else None
        
        # Calculate days until expected delivery
        days_remaining = None
        if order.expected_delivery_date:
            delta = order.expected_delivery_date - datetime.now()
            days_remaining = delta.days
        
        result.append({
            "order_code": order.order_code,
            "material": {
                "id": material.id if material else None,
                "code": material.material_code if material else None,
                "name": material.name if material else "Unknown"
            },
            "quantity": order.quantity,
            "unit_price": order.unit_price,
            "total_cost": order.total_cost,
            "vendor": {
                "name": vendor.name if vendor else "Unknown",
                "reliability_score": vendor.reliability_score if vendor else None
            },
            "destination_warehouse": warehouse.name if warehouse else None,
            "status": order.status,
            "order_date": order.order_date.isoformat() if order.order_date else None,
            "expected_delivery": order.expected_delivery_date.isoformat() if order.expected_delivery_date else None,
            "days_remaining": days_remaining,
            "is_delayed": days_remaining is not None and days_remaining < 0
        })
    
    return result


@router.get("/material-shortages")
def get_material_shortages(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get detailed material shortage analysis.
    
    Shows which materials are in short supply and their impact on projects.
    """
    needs = db.query(models.ProjectMaterialNeed).filter(
        models.ProjectMaterialNeed.quantity_shortage > 0
    ).all()
    
    # Group by material
    shortage_by_material = {}
    
    for need in needs:
        mat_id = need.material_id
        if mat_id not in shortage_by_material:
            material = db.query(models.Material).filter(
                models.Material.id == mat_id
            ).first()
            shortage_by_material[mat_id] = {
                "material_code": material.material_code if material else f"MAT-{mat_id}",
                "material_name": need.material_name or (material.name if material else "Unknown"),
                "total_shortage": 0,
                "total_value": 0,
                "affected_projects": [],
                "priority": "Medium"
            }
        
        shortage_by_material[mat_id]["total_shortage"] += need.quantity_shortage or 0
        shortage_by_material[mat_id]["total_value"] += (need.quantity_shortage or 0) * (need.unit_price or 0)
        
        # Get project info
        project = db.query(models.SubstationProject).filter(
            models.SubstationProject.id == need.project_id
        ).first()
        
        if project:
            shortage_by_material[mat_id]["affected_projects"].append({
                "project_id": project.id,
                "project_name": project.name,
                "shortage": need.quantity_shortage,
                "priority": need.priority
            })
        
        # Upgrade priority if any project has high priority
        if need.priority in ['High', 'Critical']:
            shortage_by_material[mat_id]["priority"] = need.priority
    
    # Sort by priority and total shortage
    priority_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
    sorted_shortages = sorted(
        shortage_by_material.values(),
        key=lambda x: (priority_order.get(x['priority'], 2), -x['total_shortage'])
    )
    
    return {
        "total_materials_short": len(sorted_shortages),
        "total_shortage_value": sum(s['total_value'] for s in sorted_shortages),
        "critical_count": sum(1 for s in sorted_shortages if s['priority'] == 'Critical'),
        "shortages": sorted_shortages
    }


# =============================================================================
# INVENTORY STATUS ENDPOINT
# Warehouses have: understocked / overstocked / normal / critical status
# =============================================================================

@router.get("/inventory-status")
def get_inventory_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get inventory status for all warehouses.
    
    Warehouses can be:
    - **Critical**: Stock ratio < 0.5 (50% of reorder point)
    - **Understocked**: Stock ratio < 1.0 (below reorder point)
    - **Normal**: Stock ratio 1.0 - 2.5
    - **Overstocked**: Stock ratio > 2.5
    
    Returns warehouse-by-warehouse breakdown with status.
    """
    from src.forecasting.material_forecast import MaterialForecastEngine
    
    engine = MaterialForecastEngine(db_session=db)
    return engine.get_inventory_status()


# =============================================================================
# PROJECT STATUS ENDPOINT
# Projects/Substations have: halted / delayed / at-risk / on-track status
# =============================================================================

@router.get("/project-status")
def get_project_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get health status for all active projects.
    
    Projects can be:
    - **Halted**: Has critical open issues
    - **Delayed**: delay_days > 30 days
    - **At Risk**: Has high severity issues or delay_days > 7
    - **On Track**: No issues, on schedule
    
    Returns project-by-project breakdown with status.
    """
    from src.forecasting.material_forecast import MaterialForecastEngine
    
    engine = MaterialForecastEngine(db_session=db)
    return engine.get_project_status()


@router.get("/project-issues")
def get_project_issues(
    status: str = None,
    severity: str = None,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get all project issues affecting operations.
    
    - **status**: Filter by status (Open, In Progress, Resolved)
    - **severity**: Filter by severity (Low, Medium, High, Critical)
    """
    query = db.query(models.ProjectIssue)
    
    if status:
        query = query.filter(models.ProjectIssue.status == status)
    if severity:
        query = query.filter(models.ProjectIssue.severity == severity)
    
    issues = query.order_by(
        models.ProjectIssue.severity.desc(),
        models.ProjectIssue.reported_at.desc()
    ).all()
    
    result = []
    for issue in issues:
        project = db.query(models.SubstationProject).filter(
            models.SubstationProject.id == issue.project_id
        ).first()
        
        result.append({
            "issue_code": issue.issue_code,
            "title": issue.title,
            "issue_type": issue.issue_type,
            "severity": issue.severity,
            "status": issue.status,
            "project": {
                "id": project.id if project else None,
                "name": project.name if project else "Unknown"
            },
            "impact_on_timeline": issue.impact_on_timeline,
            "impact_on_budget": issue.impact_on_budget,
            "description": issue.description,
            "reported_at": issue.reported_at.isoformat() if issue.reported_at else None,
            "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None
        })
    
    return result

