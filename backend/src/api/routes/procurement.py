"""
Procurement Monitoring API Routes
==================================

Endpoints for:
- Material shortage monitoring
- Project timeline tracking
- Procurement alerts and notifications
- Future procurement planning
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
from pathlib import Path

from src.api.database import get_db
from src.api import db_models as models
from src.alerts.notification_service import (
    get_notification_service, 
    AlertLevel, 
    AlertType
)


router = APIRouter(tags=["Procurement Monitoring"])


# ============================================================================
# SHORTAGE MONITORING
# ============================================================================

@router.get("/shortages")
async def get_material_shortages(
    project_code: Optional[str] = None,
    voltage_level: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get material shortages across all projects or for a specific project
    
    Returns:
    - Materials that are understocked for project completion
    - Shortage quantity and value
    - Impact on project timeline
    """
    
    query = db.query(models.ProjectMaterialNeed).join(
        models.SubstationProject
    ).join(
        models.Material
    )
    
    if project_code:
        query = query.filter(models.SubstationProject.project_code == project_code)
    
    if priority:
        query = query.filter(models.ProjectMaterialNeed.priority == priority)
    
    # Only get items with shortages
    needs = query.filter(models.ProjectMaterialNeed.quantity_shortage > 0).all()
    
    shortages = []
    total_shortage_value = 0.0
    
    for need in needs:
        project = need.project
        material = need.material
        
        # Check if voltage filter applies
        if voltage_level:
            mat_code = material.material_code if material else ""
            if voltage_level.replace("kV", "") not in mat_code:
                continue
        
        shortage_value = need.quantity_shortage * (need.unit_price or 0)
        total_shortage_value += shortage_value
        
        # Calculate days until project target
        days_to_target = None
        if project and project.target_date:
            days_to_target = (project.target_date - datetime.now()).days
        
        shortages.append({
            "project_code": project.project_code if project else None,
            "project_name": project.name if project else None,
            "material_code": material.material_code if material else None,
            "material_name": need.material_name or (material.name if material else None),
            "category": material.category if material else None,
            "unit": need.unit,
            "quantity_needed": need.quantity_needed,
            "quantity_available": need.quantity_available,
            "quantity_shortage": need.quantity_shortage,
            "unit_price": need.unit_price,
            "shortage_value": shortage_value,
            "priority": need.priority,
            "status": need.status,
            "days_to_project_target": days_to_target,
            "lead_time_days": material.lead_time_days if material else None,
            "is_critical": days_to_target is not None and material and days_to_target < (material.lead_time_days or 30)
        })
    
    # Sort by criticality
    shortages.sort(key=lambda x: (
        not x.get("is_critical", False),
        x.get("days_to_project_target") or 999,
        -x.get("shortage_value", 0)
    ))
    
    return {
        "total_shortages": len(shortages),
        "total_shortage_value": total_shortage_value,
        "total_shortage_value_formatted": f"₹{total_shortage_value/10000000:.2f} Cr",
        "critical_count": len([s for s in shortages if s.get("is_critical")]),
        "shortages": shortages
    }


@router.get("/inventory-status")
async def get_inventory_status(
    warehouse_code: Optional[str] = None,
    material_code: Optional[str] = None,
    status_filter: Optional[str] = Query(None, description="understocked, overstocked, normal, critical"),
    db: Session = Depends(get_db)
):
    """
    Get detailed inventory status by warehouse and material
    
    Status definitions:
    - critical: Below safety stock (< min_stock_level)
    - understocked: Below reorder point but above safety stock
    - normal: Between reorder and max stock
    - overstocked: Above max stock level
    """
    
    query = db.query(models.InventoryStock).join(
        models.Warehouse
    ).join(
        models.Material
    )
    
    if warehouse_code:
        query = query.filter(models.Warehouse.warehouse_code == warehouse_code)
    
    if material_code:
        query = query.filter(models.Material.material_code == material_code)
    
    stocks = query.all()
    
    inventory_items = []
    summary = {
        "critical": 0,
        "understocked": 0,
        "normal": 0,
        "overstocked": 0
    }
    
    for stock in stocks:
        warehouse = stock.warehouse
        material = stock.material
        
        qty_available = stock.quantity_available or 0
        min_stock = stock.min_stock_level or 0
        reorder_point = stock.reorder_point or 0
        max_stock = stock.max_stock_level or float('inf')
        
        # Determine status
        if qty_available <= min_stock:
            status = "critical"
        elif qty_available < reorder_point:
            status = "understocked"
        elif qty_available > max_stock:
            status = "overstocked"
        else:
            status = "normal"
        
        summary[status] += 1
        
        if status_filter and status != status_filter:
            continue
        
        # Calculate stock ratio
        stock_ratio = qty_available / reorder_point if reorder_point > 0 else 1.0
        
        # Days of stock remaining (based on average daily consumption)
        # For now, estimate based on 30-day consumption
        days_of_stock = (qty_available / (reorder_point / 30)) if reorder_point > 0 else 999
        
        inventory_items.append({
            "warehouse_code": warehouse.warehouse_code if warehouse else None,
            "warehouse_name": warehouse.name if warehouse else None,
            "material_code": material.material_code if material else None,
            "material_name": material.name if material else None,
            "category": material.category if material else None,
            "quantity_available": qty_available,
            "quantity_reserved": stock.quantity_reserved or 0,
            "quantity_in_transit": stock.quantity_in_transit or 0,
            "total_quantity": qty_available + (stock.quantity_in_transit or 0),
            "min_stock_level": min_stock,
            "reorder_point": reorder_point,
            "max_stock_level": max_stock if max_stock != float('inf') else None,
            "stock_ratio": round(stock_ratio, 2),
            "days_of_stock": round(days_of_stock, 1),
            "status": status,
            "last_restocked": stock.last_restocked_date.isoformat() if stock.last_restocked_date else None,
            "needs_reorder": qty_available < reorder_point,
            "unit_price": material.unit_price if material else 0,
            "stock_value": qty_available * (material.unit_price if material else 0)
        })
    
    # Sort by status priority and stock ratio
    status_priority = {"critical": 0, "understocked": 1, "normal": 2, "overstocked": 3}
    inventory_items.sort(key=lambda x: (
        status_priority.get(x["status"], 4),
        x.get("stock_ratio", 999)
    ))
    
    total_value = sum(item.get("stock_value", 0) for item in inventory_items)
    
    return {
        "summary": summary,
        "total_items": len(inventory_items),
        "total_stock_value": total_value,
        "total_stock_value_formatted": f"₹{total_value/10000000:.2f} Cr",
        "health_score": round((summary["normal"] + summary["overstocked"]) / max(len(stocks), 1) * 100, 1),
        "items": inventory_items
    }


# ============================================================================
# PROJECT TIMELINE TRACKING
# ============================================================================

@router.get("/project-timeline")
async def get_project_timeline(
    project_code: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Track project timelines and material impact
    
    Returns:
    - Project progress vs target
    - Material bottlenecks
    - Risk assessment
    """
    
    query = db.query(models.SubstationProject)
    
    if project_code:
        query = query.filter(models.SubstationProject.project_code == project_code)
    
    projects = query.all()
    
    timelines = []
    
    for project in projects:
        # Get material needs
        needs = db.query(models.ProjectMaterialNeed).filter(
            models.ProjectMaterialNeed.project_id == project.id
        ).all()
        
        total_materials = len(needs)
        shortage_materials = len([n for n in needs if n.quantity_shortage > 0])
        
        # Calculate days to target
        days_to_target = None
        is_delayed = False
        if project.target_date:
            days_to_target = (project.target_date - datetime.now()).days
            is_delayed = days_to_target < 0
        
        # Get issues
        issues = db.query(models.ProjectIssue).filter(
            models.ProjectIssue.project_id == project.id,
            models.ProjectIssue.status != "Resolved"
        ).all()
        
        critical_issues = [i for i in issues if i.severity == "Critical"]
        
        # Determine project status
        if len(critical_issues) > 0:
            project_health = "halted"
        elif is_delayed:
            project_health = "delayed"
        elif shortage_materials > total_materials * 0.3:
            project_health = "at_risk"
        else:
            project_health = "on_track"
        
        # Material bottlenecks
        bottlenecks = []
        for need in sorted(needs, key=lambda x: -x.quantity_shortage):
            if need.quantity_shortage > 0:
                material = need.material
                lead_time = material.lead_time_days if material else 30
                
                # Can we get the material in time?
                can_fulfill = days_to_target and (days_to_target > lead_time)
                
                bottlenecks.append({
                    "material_code": material.material_code if material else None,
                    "material_name": need.material_name,
                    "shortage": need.quantity_shortage,
                    "lead_time_days": lead_time,
                    "can_fulfill_in_time": can_fulfill,
                    "days_short": (lead_time - days_to_target) if days_to_target and not can_fulfill else 0
                })
        
        timelines.append({
            "project_code": project.project_code,
            "project_name": project.name,
            "status": project.status,
            "health": project_health,
            "progress": project.overall_progress,
            "target_date": project.target_date.isoformat() if project.target_date else None,
            "days_to_target": days_to_target,
            "is_delayed": is_delayed,
            "delay_days": project.delay_days or 0,
            "total_materials": total_materials,
            "shortage_materials": shortage_materials,
            "shortage_percentage": round(shortage_materials / max(total_materials, 1) * 100, 1),
            "open_issues": len(issues),
            "critical_issues": len(critical_issues),
            "bottlenecks": bottlenecks[:5],  # Top 5 bottlenecks
            "can_complete_on_time": project_health == "on_track" and shortage_materials == 0
        })
    
    # Sort by urgency
    timelines.sort(key=lambda x: (
        x["health"] == "halted",
        x["health"] == "delayed",
        x["health"] == "at_risk",
        -(x.get("days_to_target") or 999)
    ), reverse=True)
    
    return {
        "total_projects": len(timelines),
        "on_track": len([t for t in timelines if t["health"] == "on_track"]),
        "at_risk": len([t for t in timelines if t["health"] == "at_risk"]),
        "delayed": len([t for t in timelines if t["health"] == "delayed"]),
        "halted": len([t for t in timelines if t["health"] == "halted"]),
        "projects": timelines
    }


# ============================================================================
# FUTURE PROCUREMENTS
# ============================================================================

@router.get("/future-procurements")
async def get_future_procurements(
    priority: Optional[str] = Query(None, description="CRITICAL, HIGH, NORMAL"),
    project_code: Optional[str] = None,
    limit: int = 50
):
    """
    Get planned future procurements
    
    Reads from the generated procurement plan file
    """
    
    proc_file = Path(__file__).parent.parent.parent.parent / "data" / "outputs" / "future_procurements.json"
    
    if not proc_file.exists():
        return {
            "message": "No procurement plans found. Run seed_enhanced_data.py first.",
            "procurements": []
        }
    
    with open(proc_file, 'r') as f:
        procurements = json.load(f)
    
    # Filter
    if priority:
        procurements = [p for p in procurements if p.get("priority") == priority]
    
    if project_code:
        procurements = [p for p in procurements if p.get("project_code") == project_code]
    
    # Sort by urgency
    procurements.sort(key=lambda x: (
        x.get("priority") != "CRITICAL",
        x.get("priority") != "HIGH",
        x.get("days_to_target", 999)
    ))
    
    total_value = sum(p.get("total_value", 0) for p in procurements)
    
    return {
        "total_procurements": len(procurements),
        "total_value": total_value,
        "total_value_formatted": f"₹{total_value/10000000:.2f} Cr",
        "by_priority": {
            "CRITICAL": len([p for p in procurements if p.get("priority") == "CRITICAL"]),
            "HIGH": len([p for p in procurements if p.get("priority") == "HIGH"]),
            "NORMAL": len([p for p in procurements if p.get("priority") == "NORMAL"]),
        },
        "procurements": procurements[:limit]
    }


# ============================================================================
# ALERT MANAGEMENT
# ============================================================================

@router.get("/alerts")
async def get_procurement_alerts(db: Session = Depends(get_db)):
    """
    Get all active procurement alerts
    
    Analyzes current inventory and project status to generate alerts
    """
    
    notification_service = get_notification_service()
    
    alerts = []
    
    # Check for critical stock levels
    critical_stocks = db.query(models.InventoryStock).join(
        models.Material
    ).join(
        models.Warehouse
    ).filter(
        models.InventoryStock.quantity_available <= models.InventoryStock.min_stock_level
    ).all()
    
    for stock in critical_stocks:
        alerts.append({
            "type": "STOCK_CRITICAL",
            "level": "critical",
            "notification_level": 2,  # WhatsApp
            "entity_type": "inventory",
            "entity_id": f"{stock.warehouse.warehouse_code}-{stock.material.material_code}",
            "title": f"Critical Stock: {stock.material.name}",
            "message": f"Stock at {stock.warehouse.name} is below safety level. Current: {stock.quantity_available}, Min: {stock.min_stock_level}",
            "data": {
                "warehouse_code": stock.warehouse.warehouse_code,
                "material_code": stock.material.material_code,
                "current_stock": stock.quantity_available,
                "min_stock": stock.min_stock_level,
                "shortage": stock.min_stock_level - stock.quantity_available
            }
        })
    
    # Check for low stock levels
    low_stocks = db.query(models.InventoryStock).join(
        models.Material
    ).join(
        models.Warehouse
    ).filter(
        and_(
            models.InventoryStock.quantity_available > models.InventoryStock.min_stock_level,
            models.InventoryStock.quantity_available < models.InventoryStock.reorder_point
        )
    ).all()
    
    for stock in low_stocks:
        alerts.append({
            "type": "STOCK_LOW",
            "level": "warning",
            "notification_level": 1,  # Email only
            "entity_type": "inventory",
            "entity_id": f"{stock.warehouse.warehouse_code}-{stock.material.material_code}",
            "title": f"Low Stock: {stock.material.name}",
            "message": f"Stock at {stock.warehouse.name} below reorder point. Current: {stock.quantity_available}, Reorder Point: {stock.reorder_point}",
            "data": {
                "warehouse_code": stock.warehouse.warehouse_code,
                "material_code": stock.material.material_code,
                "current_stock": stock.quantity_available,
                "reorder_point": stock.reorder_point
            }
        })
    
    # Check for project material shortages
    project_shortages = db.query(models.ProjectMaterialNeed).join(
        models.SubstationProject
    ).filter(
        models.ProjectMaterialNeed.quantity_shortage > 0,
        models.ProjectMaterialNeed.priority == "High"
    ).all()
    
    for need in project_shortages:
        project = need.project
        alerts.append({
            "type": "PROJECT_SHORTAGE",
            "level": "warning",
            "notification_level": 1,
            "entity_type": "project",
            "entity_id": project.project_code if project else "unknown",
            "title": f"Project Shortage: {need.material_name}",
            "message": f"Project {project.name if project else 'Unknown'} needs {need.quantity_shortage} units of {need.material_name}",
            "data": {
                "project_code": project.project_code if project else None,
                "material_name": need.material_name,
                "shortage": need.quantity_shortage,
                "shortage_value": need.quantity_shortage * (need.unit_price or 0)
            }
        })
    
    # Sort by severity
    level_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda x: level_order.get(x.get("level", "info"), 3))
    
    return {
        "total_alerts": len(alerts),
        "critical": len([a for a in alerts if a["level"] == "critical"]),
        "warning": len([a for a in alerts if a["level"] == "warning"]),
        "requires_whatsapp": len([a for a in alerts if a["notification_level"] == 2]),
        "requires_email": len([a for a in alerts if a["notification_level"] == 1]),
        "alerts": alerts
    }


@router.post("/alerts/send")
async def send_procurement_alert(
    alert_type: str,
    entity_id: str,
    force_level: Optional[int] = Query(None, description="1=Email, 2=WhatsApp"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger an alert notification
    
    - Level 1: Email notification
    - Level 2: Email + WhatsApp notification
    """
    
    notification_service = get_notification_service()
    
    # Find the alert data
    if alert_type == "STOCK_CRITICAL":
        parts = entity_id.split("-")
        if len(parts) >= 2:
            wh_code = parts[0] + "-" + parts[1]
            mat_code = "-".join(parts[2:])
            
            stock = db.query(models.InventoryStock).join(
                models.Warehouse
            ).join(
                models.Material
            ).filter(
                models.Warehouse.warehouse_code == wh_code,
                models.Material.material_code == mat_code
            ).first()
            
            if stock:
                level = force_level or 2  # Default to WhatsApp for critical
                
                # Send email
                email_result = notification_service.send_stock_alert_email(
                    material_code=stock.material.material_code,
                    material_name=stock.material.name,
                    warehouse_code=stock.warehouse.warehouse_code,
                    current_stock=stock.quantity_available,
                    required_stock=stock.reorder_point,
                    shortage=stock.reorder_point - stock.quantity_available
                )
                
                results = {"email": email_result}
                
                # Send WhatsApp if level 2
                if level >= 2:
                    wa_result = notification_service.send_critical_stock_whatsapp(
                        material_code=stock.material.material_code,
                        material_name=stock.material.name,
                        warehouse_code=stock.warehouse.warehouse_code,
                        shortage=stock.reorder_point - stock.quantity_available,
                        days_until_stockout=5  # Estimate
                    )
                    results["whatsapp"] = wa_result
                
                return {
                    "success": True,
                    "alert_type": alert_type,
                    "entity_id": entity_id,
                    "notification_level": level,
                    "results": results
                }
    
    raise HTTPException(status_code=404, detail="Alert entity not found")


@router.get("/project-completion-forecast")
async def get_project_completion_forecast(
    project_code: str,
    db: Session = Depends(get_db)
):
    """
    Forecast whether a project can complete on time
    
    Analyzes:
    - Current progress
    - Material availability
    - Open issues
    - Lead times for missing materials
    """
    
    project = db.query(models.SubstationProject).filter(
        models.SubstationProject.project_code == project_code
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get material needs
    needs = db.query(models.ProjectMaterialNeed).filter(
        models.ProjectMaterialNeed.project_id == project.id
    ).all()
    
    # Get open issues
    issues = db.query(models.ProjectIssue).filter(
        models.ProjectIssue.project_id == project.id,
        models.ProjectIssue.status != "Resolved"
    ).all()
    
    # Calculate timeline
    days_to_target = (project.target_date - datetime.now()).days if project.target_date else None
    
    # Analyze materials
    material_analysis = []
    max_lead_time = 0
    total_shortage_value = 0
    
    for need in needs:
        if need.quantity_shortage > 0:
            material = need.material
            lead_time = material.lead_time_days if material else 30
            max_lead_time = max(max_lead_time, lead_time)
            
            can_fulfill = days_to_target and (days_to_target > lead_time)
            shortage_value = need.quantity_shortage * (need.unit_price or 0)
            total_shortage_value += shortage_value
            
            material_analysis.append({
                "material_code": material.material_code if material else None,
                "material_name": need.material_name,
                "shortage": need.quantity_shortage,
                "lead_time_days": lead_time,
                "can_fulfill_in_time": can_fulfill,
                "procurement_deadline": (datetime.now() + timedelta(days=days_to_target - lead_time)).isoformat() if days_to_target and can_fulfill else None,
                "shortage_value": shortage_value
            })
    
    # Determine forecast
    can_complete = True
    blocking_factors = []
    
    # Check critical issues
    critical_issues = [i for i in issues if i.severity == "Critical"]
    if critical_issues:
        can_complete = False
        blocking_factors.append({
            "factor": "critical_issues",
            "description": f"{len(critical_issues)} critical issue(s) blocking progress",
            "details": [{"title": i.title, "status": i.status} for i in critical_issues]
        })
    
    # Check material lead times
    unfulfillable = [m for m in material_analysis if not m.get("can_fulfill_in_time")]
    if unfulfillable:
        can_complete = False
        blocking_factors.append({
            "factor": "material_lead_time",
            "description": f"{len(unfulfillable)} material(s) cannot be procured in time",
            "details": unfulfillable
        })
    
    # Calculate recommended target date
    recommended_target = None
    if not can_complete and days_to_target:
        additional_days = max_lead_time - days_to_target + 30  # Add 30 day buffer
        recommended_target = (datetime.now() + timedelta(days=additional_days)).isoformat()
    
    return {
        "project_code": project.project_code,
        "project_name": project.name,
        "current_progress": project.overall_progress,
        "target_date": project.target_date.isoformat() if project.target_date else None,
        "days_to_target": days_to_target,
        "can_complete_on_time": can_complete,
        "confidence_level": "high" if can_complete else "low",
        "blocking_factors": blocking_factors,
        "material_shortages": len(material_analysis),
        "total_shortage_value": total_shortage_value,
        "max_lead_time_required": max_lead_time,
        "recommended_target_date": recommended_target,
        "material_analysis": material_analysis,
        "open_issues": len(issues),
        "critical_issues": len(critical_issues),
        "recommendations": [
            "Order all shortage materials immediately" if material_analysis else None,
            f"Resolve {len(critical_issues)} critical issues" if critical_issues else None,
            f"Consider extending target date to {recommended_target}" if recommended_target else None
        ]
    }
