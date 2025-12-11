"""
Alerts API Routes
=================
Endpoints for alert management and notifications.

Supports:
- GET /alerts/feed - Get current alerts with severity
- POST /alerts/notify - Send notification via WhatsApp or Email
- POST /alerts/acknowledge - Acknowledge an alert
- GET /alerts/history - Get alert history
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from enum import Enum
import os
import uuid
import logging

from src.api.database import get_db
from src.api import db_models
from src.core.triggers_engine import TriggersEngine, Severity
from src.services.notification_service import (
    NotificationService, 
    NotificationChannel,
    NotificationResult
)
from src.services.osrm_service import OSRMService
from src.services.pdf_service import PDFService, ReportContent, get_pdf_service
from src.services.llm_service import LLMService, AlertContext, AlertType, get_llm_service

logger = logging.getLogger(__name__)

# IST Timezone
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    """Get current time in IST"""
    return datetime.now(IST)

router = APIRouter(prefix="/alerts", tags=["Alerts & Notifications"])


# =============================================================================
# SCHEMAS
# =============================================================================

class NotificationChannelEnum(str, Enum):
    whatsapp = "whatsapp"
    email = "email"


class AlertNotifyRequest(BaseModel):
    """Request to send an alert notification"""
    recipient: str = Field(..., description="Phone number (with country code) or email address")
    channel: NotificationChannelEnum = Field(
        NotificationChannelEnum.email, 
        description="Notification channel: 'whatsapp' or 'email'"
    )
    alert_ids: Optional[List[str]] = Field(
        None, 
        description="Specific alert IDs to notify about. If empty, sends all critical alerts."
    )
    custom_message: Optional[str] = Field(
        None,
        description="Custom message to append to the alert"
    )
    include_eta: bool = Field(
        False,
        description="Include ETA information for material delivery"
    )
    
    # Understock (UTR) thresholds for triggering alerts
    utr_email_threshold: float = Field(
        0.20, 
        description="Email alert threshold for UTR. Alert sent if UTR > this value."
    )
    utr_whatsapp_threshold: float = Field(
        0.50, 
        description="WhatsApp alert threshold for UTR. Alert sent if UTR > this value."
    )
    
    # Overstock (OTR) thresholds for triggering alerts
    otr_email_threshold: float = Field(
        0.50, 
        description="Email alert threshold for OTR. Alert sent if OTR > this value."
    )
    otr_whatsapp_threshold: float = Field(
        1.0, 
        description="WhatsApp alert threshold for OTR. Alert sent if OTR > this value."
    )
    
    # PDF options
    generate_pdf: bool = Field(
        True, 
        description="Generate PDF report for the alert"
    )
    attach_pdf_to_email: bool = Field(
        True, 
        description="Attach PDF to email notification"
    )
    send_pdf_via_whatsapp: bool = Field(
        True, 
        description="Send PDF via WhatsApp as document"
    )


class AlertNotifyResponse(BaseModel):
    """Response from alert notification"""
    success: bool
    channel: str
    recipient: str
    alerts_sent: int
    message_id: Optional[str] = None
    error: Optional[str] = None
    pdf_generated: Optional[bool] = None
    pdf_attached: Optional[bool] = None
    thresholds_applied: Optional[Dict[str, float]] = None


class AlertAcknowledgeRequest(BaseModel):
    """Request to acknowledge an alert"""
    alert_id: str
    acknowledged_by: str = Field(..., description="Name or ID of person acknowledging")
    action_taken: Optional[str] = Field(None, description="Description of action taken")


class BulkNotifyRequest(BaseModel):
    """Request for bulk notifications"""
    recipients: List[str]
    channel: NotificationChannelEnum
    severity_filter: Optional[str] = Field(None, description="Filter by severity: RED, AMBER, GREEN")
    warehouse_id: Optional[int] = Field(None, description="Filter by warehouse")


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/notify", response_model=AlertNotifyResponse)
def send_alert_notification(
    request: AlertNotifyRequest,
    db: Session = Depends(get_db)
):
    """
    📨 **SEND ALERT NOTIFICATION**
    
    Send critical inventory alerts via WhatsApp or Email with PDF attachment.
    
    **Channels:**
    - `whatsapp`: Sends to phone number (requires country code, e.g., "919343584820")
    - `email`: Sends to email address
    
    **Trigger Thresholds:**
    - **Understock (UTR):** Email if UTR > `utr_email_threshold`, WhatsApp if UTR > `utr_whatsapp_threshold`
    - **Overstock (OTR):** Email if OTR > `otr_email_threshold`, WhatsApp if OTR > `otr_whatsapp_threshold`
    
    **PDF Integration:**
    - PDF report is generated automatically when alerts are triggered
    - PDF is attached to email if `attach_pdf_to_email` is True
    - PDF is sent as WhatsApp document if `send_pdf_via_whatsapp` is True
    
    **Alert Selection:**
    - If `alert_ids` provided: Sends only specified alerts
    - If empty: Sends all items exceeding thresholds
    
    **Environment Variables Required:**
    - WhatsApp: `META_BEARER_TOKEN`, `PHONE_NUMBER_ID`
    - Email: `POSTMARK_SERVER_TOKEN`, `DEFAULT_SENDER_EMAIL`
    """
    
    # Initialize services
    notification_service = NotificationService()
    triggers_engine = TriggersEngine(db)
    llm_service = get_llm_service()
    pdf_service = get_pdf_service()
    
    # Get all inventory data
    all_inventory = db.query(
        db_models.InventoryStock,
        db_models.Material,
        db_models.Warehouse
    ).join(
        db_models.Material,
        db_models.InventoryStock.material_id == db_models.Material.id
    ).join(
        db_models.Warehouse,
        db_models.InventoryStock.warehouse_id == db_models.Warehouse.id
    ).filter(
        db_models.Warehouse.is_active == True
    ).all()
    
    # Compute triggers for all inventory and check UTR/OTR thresholds
    alerts_to_send = []
    alert_details = []  # For PDF generation
    
    for stock, material, warehouse in all_inventory:
        trigger = triggers_engine.compute_triggers(
            material_code=material.material_code or f"MAT-{material.id:03d}",
            material_name=material.name,
            warehouse_code=warehouse.warehouse_code or f"WH-{warehouse.id:03d}",
            warehouse_name=warehouse.name,
            current_stock=stock.quantity_available,
            min_stock_level=stock.min_stock_level,
            max_stock_level=stock.max_stock_level,
            lead_time_days=material.lead_time_days or 14,
            unit_price=material.unit_price or 50000
        )
        
        alert_id = f"{warehouse.id}-{material.id}"
        
        # If specific alert_ids provided, filter
        if request.alert_ids and alert_id not in request.alert_ids:
            continue
        
        # Check UTR/OTR thresholds based on channel
        utr = trigger.utr
        otr = trigger.otr
        
        # Determine if this item should trigger an alert
        if request.channel == NotificationChannelEnum.email:
            utr_triggers = utr > request.utr_email_threshold
            otr_triggers = otr > request.otr_email_threshold
        else:  # WhatsApp
            utr_triggers = utr > request.utr_whatsapp_threshold
            otr_triggers = otr > request.otr_whatsapp_threshold
        
        # Add to alerts if any threshold exceeded
        if utr_triggers or otr_triggers:
            alert_reason = "understock" if utr > otr else "overstock"
            
            alerts_to_send.append({
                "alert_id": alert_id,
                "material": material.name,
                "material_code": trigger.item_id,
                "warehouse": warehouse.name,
                "warehouse_code": trigger.warehouse_code,
                "current_stock": int(stock.quantity_available),
                "reorder_point": int(trigger.reorder_point),
                "safety_stock": int(trigger.safety_stock),
                "days_of_stock": round(trigger.days_of_stock, 1),
                "utr": round(utr, 4),
                "otr": round(otr, 4),
                "par": round(trigger.par, 4),
                "severity": trigger.severity.value,
                "action": trigger.action,
                "reason": alert_reason
            })
            
            # Store full details for PDF
            alert_details.append({
                "stock": stock,
                "material": material,
                "warehouse": warehouse,
                "trigger": trigger,
                "alert_reason": alert_reason
            })
    
    if not alerts_to_send:
        return AlertNotifyResponse(
            success=True,
            channel=request.channel.value,
            recipient=request.recipient,
            alerts_sent=0,
            message_id=None,
            error="No alerts exceed the configured thresholds",
            thresholds_applied={
                "utr_threshold": request.utr_email_threshold if request.channel == NotificationChannelEnum.email else request.utr_whatsapp_threshold,
                "otr_threshold": request.otr_email_threshold if request.channel == NotificationChannelEnum.email else request.otr_whatsapp_threshold
            }
        )
    
    # Generate PDF report if requested
    pdf_bytes = None
    pdf_base64 = None
    pdf_filename = None
    pdf_generated = False
    
    if request.generate_pdf and alert_details:
        try:
            # Use the first critical alert for PDF
            primary_alert = alert_details[0]
            stock = primary_alert["stock"]
            material = primary_alert["material"]
            warehouse = primary_alert["warehouse"]
            trigger = primary_alert["trigger"]
            alert_reason = primary_alert["alert_reason"]
            
            # Determine alert type for LLM
            if trigger.utr > trigger.otr and trigger.utr > 0.1:
                alert_type = AlertType.UNDERSTOCK if trigger.utr > 0.5 else AlertType.REORDER
            elif trigger.otr > trigger.utr and trigger.otr > 0.1:
                alert_type = AlertType.OVERSTOCK
            else:
                alert_type = AlertType.OK
            
            location = f"{warehouse.city}, {warehouse.state}" if warehouse.city else warehouse.state or "India"
            
            # Generate LLM alert
            alert_context = AlertContext(
                material_name=material.name,
                material_code=material.material_code,
                warehouse_name=warehouse.name,
                warehouse_code=warehouse.warehouse_code,
                location=location,
                current_stock=stock.quantity_available,
                reorder_point=trigger.reorder_point,
                safety_stock=trigger.safety_stock,
                max_stock_level=stock.max_stock_level or trigger.reorder_point * 2.5,
                utr=trigger.utr,
                otr=trigger.otr,
                par=trigger.par,
                days_of_stock=trigger.days_of_stock,
                lead_time_days=material.lead_time_days or 14,
                daily_demand=trigger.daily_demand,
                alert_type=alert_type,
                severity=trigger.severity.value
            )
            
            llm_alert = llm_service.generate_alert(alert_context)
            
            # Get transaction history for PDF
            history = db.query(db_models.InventoryTransaction).filter(
                db_models.InventoryTransaction.warehouse_id == warehouse.id,
                db_models.InventoryTransaction.material_id == material.id
            ).order_by(
                db_models.InventoryTransaction.transaction_date.desc()
            ).limit(10).all()
            
            history_list = [
                {
                    "date": h.transaction_date.isoformat() if h.transaction_date else None,
                    "type": h.transaction_type,
                    "quantity": h.quantity,
                    "remarks": h.remarks
                }
                for h in history
            ]
            
            # Generate PDF
            report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
            optimal_stock = trigger.reorder_point * 1.5
            
            report_content = ReportContent(
                title="NEXUS Inventory Alert Report",
                subtitle=f"{material.name} - {warehouse.name}",
                material_name=material.name,
                material_code=material.material_code or f"MAT-{material.id:03d}",
                warehouse_name=warehouse.name,
                warehouse_code=warehouse.warehouse_code or f"WH-{warehouse.id:03d}",
                location=location,
                current_stock=stock.quantity_available,
                optimal_stock=optimal_stock,
                reorder_point=trigger.reorder_point,
                safety_stock=trigger.safety_stock,
                max_stock_level=stock.max_stock_level or trigger.reorder_point * 2.5,
                utr=trigger.utr,
                otr=trigger.otr,
                par=trigger.par,
                days_of_stock=trigger.days_of_stock,
                daily_demand=trigger.daily_demand,
                severity=trigger.severity.value,
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
            pdf_filename = f"NEXUS_Alert_{material.material_code or material.id}_{get_ist_now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_generated = True
            
            logger.info(f"Generated PDF report: {pdf_filename} ({len(pdf_bytes)} bytes)")
            
        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}")
            pdf_generated = False
    
    # Build notification message
    message_lines = [
        "🚨 NEXUS INVENTORY ALERT 🚨",
        f"Time: {get_ist_now().strftime('%Y-%m-%d %H:%M')} IST",
        f"Critical Items: {len(alerts_to_send)}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    
    for i, alert in enumerate(alerts_to_send[:10], 1):
        reason_emoji = "📉" if alert['reason'] == "understock" else "📈"
        message_lines.extend([
            f"\n{i}. {alert['material']}",
            f"   📍 {alert['warehouse']}",
            f"   📦 Stock: {alert['current_stock']} (ROP: {alert['reorder_point']})",
            f"   ⏳ Days left: {alert['days_of_stock']}",
            f"   {reason_emoji} {alert['reason'].upper()} - UTR: {alert['utr']:.1%}, OTR: {alert['otr']:.1%}",
            f"   ⚡ {alert['action']}"
        ])
    
    if len(alerts_to_send) > 10:
        message_lines.append(f"\n... and {len(alerts_to_send) - 10} more alerts")
    
    if request.custom_message:
        message_lines.extend(["", f"📝 Note: {request.custom_message}"])
    
    message_lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━",
        "NEXUS Inventory Intelligence"
    ])
    
    full_message = "\n".join(message_lines)
    
    # Send notification based on channel
    channel = NotificationChannel.WHATSAPP if request.channel == NotificationChannelEnum.whatsapp else NotificationChannel.EMAIL
    pdf_attached = False
    
    if channel == NotificationChannel.WHATSAPP:
        # Send WhatsApp text message
        result = notification_service.send_whatsapp(request.recipient, full_message)
        
        # Send PDF as document if generated and requested
        if pdf_bytes and request.send_pdf_via_whatsapp and result.success:
            doc_result = notification_service.send_whatsapp_document(
                phone_number=request.recipient,
                document_bytes=pdf_bytes,
                filename=pdf_filename,
                caption=f"📊 NEXUS Alert Report - {len(alerts_to_send)} critical items"
            )
            pdf_attached = doc_result.success
            if doc_result.error:
                logger.warning(f"WhatsApp document send failed: {doc_result.error}")
    else:
        # Prepare email attachments if PDF generated
        email_attachments = None
        if pdf_base64 and request.attach_pdf_to_email:
            email_attachments = [{
                "Name": pdf_filename,
                "Content": pdf_base64,
                "ContentType": "application/pdf"
            }]
            pdf_attached = True
        
        # Send email
        result = notification_service.send_email(
            to_email=request.recipient,
            subject=f"🚨 NEXUS Alert: {len(alerts_to_send)} Critical Items",
            body=full_message,
            html_body=_generate_html_alert(alerts_to_send),
            attachments=email_attachments
        )
    
    return AlertNotifyResponse(
        success=result.success,
        channel=result.channel,
        recipient=result.recipient,
        alerts_sent=len(alerts_to_send),
        message_id=result.message_id,
        error=result.error,
        pdf_generated=pdf_generated,
        pdf_attached=pdf_attached,
        thresholds_applied={
            "utr_threshold": request.utr_email_threshold if channel == NotificationChannel.EMAIL else request.utr_whatsapp_threshold,
            "otr_threshold": request.otr_email_threshold if channel == NotificationChannel.EMAIL else request.otr_whatsapp_threshold
        }
    )


@router.post("/notify/bulk")
def send_bulk_notifications(
    request: BulkNotifyRequest,
    db: Session = Depends(get_db)
):
    """
    📨 **SEND BULK NOTIFICATIONS**
    
    Send alerts to multiple recipients.
    Useful for notifying entire team about critical shortages.
    """
    
    notification_service = NotificationService()
    results = []
    
    for recipient in request.recipients:
        # Create individual notify request
        notify_request = AlertNotifyRequest(
            recipient=recipient,
            channel=request.channel
        )
        
        # Send (reusing the main notify logic would be better, simplified here)
        if request.channel == NotificationChannelEnum.whatsapp:
            result = notification_service.send_whatsapp(
                recipient, 
                f"🚨 NEXUS Bulk Alert - Check the dashboard for critical inventory items"
            )
        else:
            result = notification_service.send_email(
                recipient,
                "🚨 NEXUS Inventory Alert",
                "Please check the NEXUS dashboard for critical inventory alerts."
            )
        
        results.append({
            "recipient": recipient,
            "success": result.success,
            "error": result.error
        })
    
    successful = sum(1 for r in results if r["success"])
    
    return {
        "status": "completed",
        "total_recipients": len(request.recipients),
        "successful": successful,
        "failed": len(request.recipients) - successful,
        "results": results
    }


@router.post("/acknowledge")
def acknowledge_alert(
    request: AlertAcknowledgeRequest,
    db: Session = Depends(get_db)
):
    """
    ✅ **ACKNOWLEDGE ALERT**
    
    Mark an alert as acknowledged and record who handled it.
    """
    
    # Parse alert_id (format: warehouse_id-material_id)
    try:
        parts = request.alert_id.split("-")
        warehouse_id = int(parts[0])
        material_id = int(parts[1])
    except:
        raise HTTPException(status_code=400, detail="Invalid alert_id format. Expected: warehouse_id-material_id")
    
    # Find the inventory record
    stock = db.query(db_models.InventoryStock).filter(
        db_models.InventoryStock.warehouse_id == warehouse_id,
        db_models.InventoryStock.material_id == material_id
    ).first()
    
    if not stock:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Record acknowledgment (in a real system, this would go to an alerts table)
    # For now, we'll add to notes or create a transaction record
    
    return {
        "status": "acknowledged",
        "alert_id": request.alert_id,
        "acknowledged_by": request.acknowledged_by,
        "acknowledged_at": datetime.now().isoformat(),
        "action_taken": request.action_taken,
        "message": "Alert acknowledged. Consider creating a purchase order to resolve."
    }


@router.get("/settings")
def get_notification_settings():
    """
    ⚙️ **GET NOTIFICATION SETTINGS**
    
    Returns current notification configuration status.
    Shows which channels are properly configured.
    """
    # Use the notification service to get configuration status
    notification_service = NotificationService()
    config = notification_service.get_configuration_status()
    
    whatsapp_configured = config["whatsapp"]["configured"]
    email_configured = config["email"]["configured"]
    
    return {
        "channels": {
            "whatsapp": {
                "configured": whatsapp_configured,
                "required_env_vars": config["whatsapp"]["required_env_vars"],
                "optional_env_vars": config["whatsapp"]["optional_env_vars"],
                "default_recipient": config["whatsapp"]["default_recipient"],
                "status": "ready" if whatsapp_configured else "not_configured"
            },
            "email": {
                "configured": email_configured,
                "required_env_vars": config["email"]["required_env_vars"],
                "sender_email": config["email"]["sender_email"],
                "status": "ready" if email_configured else "not_configured"
            }
        },
        "default_channel": "email" if email_configured else ("whatsapp" if whatsapp_configured else None),
        "message": "Notification channels configured via .env file"
    }


@router.get("/test/{channel}")
def test_notification_channel(
    channel: str,
    recipient: str = Query(..., description="Test recipient (phone or email)")
):
    """
    🧪 **TEST NOTIFICATION CHANNEL**
    
    Send a test message to verify channel configuration.
    """
    
    notification_service = NotificationService()
    
    test_message = f"""
🧪 NEXUS Test Notification

This is a test message to verify your notification setup.
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

If you received this, notifications are working! ✅
"""
    
    if channel == "whatsapp":
        result = notification_service.send_whatsapp(recipient, test_message)
    elif channel == "email":
        result = notification_service.send_email(
            recipient, 
            "🧪 NEXUS Test Notification",
            test_message
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid channel. Use 'whatsapp' or 'email'")
    
    return {
        "test_result": "success" if result.success else "failed",
        "channel": channel,
        "recipient": recipient,
        "message_id": result.message_id,
        "error": result.error
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _generate_html_alert(alerts: List[dict]) -> str:
    """Generate HTML email body for alerts"""
    
    rows = ""
    for alert in alerts[:20]:
        rows += f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{alert['material']}</td>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{alert['warehouse']}</td>
            <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">
                <span style="background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 4px;">
                    {alert['current_stock']}
                </span>
            </td>
            <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">{alert['reorder_point']}</td>
            <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">{alert['days_of_stock']} days</td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ background: linear-gradient(135deg, #dc3545, #c82333); color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background-color: #343a40; color: white; padding: 12px 8px; text-align: left; }}
            .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; color: #6c757d; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚨 NEXUS Inventory Alert</h1>
            <p>{len(alerts)} Critical Items Require Attention</p>
        </div>
        
        <div class="content">
            <p>The following items are critically low and need immediate action:</p>
            
            <table>
                <thead>
                    <tr>
                        <th>Material</th>
                        <th>Warehouse</th>
                        <th>Current Stock</th>
                        <th>Reorder Point</th>
                        <th>Days Left</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            
            <p style="margin-top: 20px;">
                <strong>Recommended Action:</strong> Create purchase orders for these items immediately.
            </p>
        </div>
        
        <div class="footer">
            <p>NEXUS Inventory Intelligence System</p>
            <p>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """
    
    return html
