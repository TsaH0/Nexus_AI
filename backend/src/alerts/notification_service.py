"""
NEXUS Alert & Notification Service
===================================

Handles all alerts and notifications for:
- Procurement alerts (material shortages, delays)
- Project timeline warnings
- Inventory level alerts

Alert Levels:
- Level 1: Email notification
- Level 2: WhatsApp notification (critical/urgent)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger("NEXUS.Alerts")


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    URGENT = "urgent"


class AlertType(Enum):
    """Types of alerts"""
    STOCK_LOW = "stock_low"
    STOCK_CRITICAL = "stock_critical"
    PROCUREMENT_DELAYED = "procurement_delayed"
    PROJECT_AT_RISK = "project_at_risk"
    PROJECT_DELAYED = "project_delayed"
    DELIVERY_DELAYED = "delivery_delayed"
    VENDOR_ISSUE = "vendor_issue"
    TIMELINE_WARNING = "timeline_warning"


@dataclass
class Alert:
    """Alert data structure"""
    alert_id: str
    alert_type: AlertType
    level: AlertLevel
    title: str
    message: str
    entity_type: str  # material, project, warehouse, vendor
    entity_id: str
    data: Dict[str, Any]
    created_at: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    sent_email: bool = False
    sent_whatsapp: bool = False


class NotificationService:
    """
    Notification service for sending alerts via Email and WhatsApp
    
    Current implementation: Placeholder functions
    Future: Integration with actual email/WhatsApp APIs
    """
    
    def __init__(self):
        self.alert_history: List[Alert] = []
        self.email_config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "sender_email": "alerts@nexus.powergrid.gov.in",
            "recipients": [
                "procurement@powergrid.gov.in",
                "project.manager@powergrid.gov.in"
            ]
        }
        self.whatsapp_config = {
            "api_url": "https://api.whatsapp.com/v1/messages",
            "api_key": "PLACEHOLDER_API_KEY",
            "recipients": [
                "+91-XXXXXXXXXX",  # Procurement Head
                "+91-XXXXXXXXXX",  # Project Manager
            ]
        }
        logger.info("NotificationService initialized")
    
    # ========================================================================
    # EMAIL NOTIFICATIONS (Level 1)
    # ========================================================================
    
    def send_email(
        self,
        subject: str,
        body: str,
        recipients: Optional[List[str]] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Send email notification
        
        PLACEHOLDER: This function simulates email sending.
        TODO: Integrate with actual SMTP or email service (SendGrid, AWS SES, etc.)
        
        Args:
            subject: Email subject
            body: Email body (HTML supported)
            recipients: List of email addresses (uses default if not provided)
            priority: Email priority (low, normal, high)
        
        Returns:
            Dict with status and message_id
        """
        recipients = recipients or self.email_config["recipients"]
        
        # PLACEHOLDER: Simulate email sending
        message_id = f"EMAIL-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.alert_history):04d}"
        
        logger.info(f"📧 EMAIL SENT (Placeholder)")
        logger.info(f"   To: {', '.join(recipients)}")
        logger.info(f"   Subject: {subject}")
        logger.info(f"   Priority: {priority}")
        logger.info(f"   Message ID: {message_id}")
        
        # Log the email content (in production, this would be sent to SMTP)
        email_log = {
            "status": "sent",
            "message_id": message_id,
            "timestamp": datetime.now().isoformat(),
            "recipients": recipients,
            "subject": subject,
            "body_preview": body[:200] + "..." if len(body) > 200 else body,
            "priority": priority,
            "is_placeholder": True  # Flag indicating this is a placeholder
        }
        
        return email_log
    
    def send_stock_alert_email(
        self,
        material_code: str,
        material_name: str,
        warehouse_code: str,
        current_stock: float,
        required_stock: float,
        shortage: float,
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send stock level alert email"""
        
        subject = f"🚨 NEXUS Alert: Low Stock - {material_name} at {warehouse_code}"
        
        body = f"""
        <html>
        <body>
            <h2>⚠️ Material Stock Alert</h2>
            <table border="1" cellpadding="10">
                <tr><td><b>Material Code</b></td><td>{material_code}</td></tr>
                <tr><td><b>Material Name</b></td><td>{material_name}</td></tr>
                <tr><td><b>Warehouse</b></td><td>{warehouse_code}</td></tr>
                <tr><td><b>Current Stock</b></td><td>{current_stock:.2f}</td></tr>
                <tr><td><b>Required Stock</b></td><td>{required_stock:.2f}</td></tr>
                <tr><td><b>Shortage</b></td><td style="color: red;"><b>{shortage:.2f}</b></td></tr>
                {f'<tr><td><b>Affected Project</b></td><td>{project_name}</td></tr>' if project_name else ''}
            </table>
            <p><b>Recommended Action:</b> Initiate procurement order immediately.</p>
            <p>Generated by NEXUS Procurement Intelligence System</p>
        </body>
        </html>
        """
        
        return self.send_email(subject, body, priority="high")
    
    def send_project_delay_email(
        self,
        project_code: str,
        project_name: str,
        delay_days: int,
        reason: str,
        impact_materials: List[Dict]
    ) -> Dict[str, Any]:
        """Send project delay alert email"""
        
        subject = f"⏰ NEXUS Alert: Project Delay - {project_name} ({delay_days} days)"
        
        materials_table = ""
        for mat in impact_materials:
            materials_table += f"""
                <tr>
                    <td>{mat.get('code', 'N/A')}</td>
                    <td>{mat.get('name', 'N/A')}</td>
                    <td>{mat.get('shortage', 0):.2f}</td>
                </tr>
            """
        
        body = f"""
        <html>
        <body>
            <h2>⏰ Project Delay Alert</h2>
            <table border="1" cellpadding="10">
                <tr><td><b>Project Code</b></td><td>{project_code}</td></tr>
                <tr><td><b>Project Name</b></td><td>{project_name}</td></tr>
                <tr><td><b>Delay Duration</b></td><td style="color: red;"><b>{delay_days} days</b></td></tr>
                <tr><td><b>Reason</b></td><td>{reason}</td></tr>
            </table>
            
            <h3>Affected Materials:</h3>
            <table border="1" cellpadding="5">
                <tr><th>Code</th><th>Material</th><th>Shortage</th></tr>
                {materials_table}
            </table>
            
            <p>Generated by NEXUS Procurement Intelligence System</p>
        </body>
        </html>
        """
        
        return self.send_email(subject, body, priority="high")
    
    # ========================================================================
    # WHATSAPP NOTIFICATIONS (Level 2 - Critical/Urgent)
    # ========================================================================
    
    def send_whatsapp(
        self,
        message: str,
        recipients: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send WhatsApp notification
        
        PLACEHOLDER: This function simulates WhatsApp message sending.
        TODO: Integrate with WhatsApp Business API or Twilio
        
        Args:
            message: WhatsApp message text
            recipients: List of phone numbers (uses default if not provided)
        
        Returns:
            Dict with status and message_id
        """
        recipients = recipients or self.whatsapp_config["recipients"]
        
        # PLACEHOLDER: Simulate WhatsApp sending
        message_id = f"WA-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.alert_history):04d}"
        
        logger.warning(f"📱 WHATSAPP SENT (Placeholder)")
        logger.warning(f"   To: {', '.join(recipients)}")
        logger.warning(f"   Message: {message[:100]}...")
        logger.warning(f"   Message ID: {message_id}")
        
        whatsapp_log = {
            "status": "sent",
            "message_id": message_id,
            "timestamp": datetime.now().isoformat(),
            "recipients": recipients,
            "message": message,
            "is_placeholder": True
        }
        
        return whatsapp_log
    
    def send_critical_stock_whatsapp(
        self,
        material_code: str,
        material_name: str,
        warehouse_code: str,
        shortage: float,
        days_until_stockout: int
    ) -> Dict[str, Any]:
        """Send critical stock alert via WhatsApp"""
        
        message = f"""🚨 *NEXUS CRITICAL ALERT*

⚠️ *Material Shortage*
📦 {material_name} ({material_code})
🏭 Warehouse: {warehouse_code}
📉 Shortage: {shortage:.0f} units
⏰ Stockout in: {days_until_stockout} days

*IMMEDIATE ACTION REQUIRED*
Initiate emergency procurement now.

- NEXUS System"""
        
        return self.send_whatsapp(message)
    
    def send_project_halt_whatsapp(
        self,
        project_code: str,
        project_name: str,
        reason: str
    ) -> Dict[str, Any]:
        """Send project halt alert via WhatsApp"""
        
        message = f"""🔴 *NEXUS URGENT ALERT*

🚧 *PROJECT HALTED*
📋 {project_name}
🔖 Code: {project_code}
❌ Reason: {reason}

*ESCALATION REQUIRED*
Contact Project Manager immediately.

- NEXUS System"""
        
        return self.send_whatsapp(message)
    
    # ========================================================================
    # UNIFIED ALERT SYSTEM
    # ========================================================================
    
    def create_alert(
        self,
        alert_type: AlertType,
        level: AlertLevel,
        title: str,
        message: str,
        entity_type: str,
        entity_id: str,
        data: Dict[str, Any]
    ) -> Alert:
        """Create and process an alert"""
        
        alert_id = f"ALT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.alert_history):04d}"
        
        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            level=level,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            data=data,
            created_at=datetime.now()
        )
        
        # Process based on level
        if level in [AlertLevel.INFO, AlertLevel.WARNING]:
            # Level 1: Email only
            email_result = self.send_email(
                subject=f"NEXUS {level.value.upper()}: {title}",
                body=message,
                priority="normal" if level == AlertLevel.INFO else "high"
            )
            alert.sent_email = True
            
        elif level in [AlertLevel.CRITICAL, AlertLevel.URGENT]:
            # Level 2: Email + WhatsApp
            email_result = self.send_email(
                subject=f"🚨 NEXUS {level.value.upper()}: {title}",
                body=message,
                priority="high"
            )
            alert.sent_email = True
            
            whatsapp_result = self.send_whatsapp(
                message=f"🚨 NEXUS {level.value.upper()}\n\n{title}\n\n{message[:200]}..."
            )
            alert.sent_whatsapp = True
        
        self.alert_history.append(alert)
        logger.info(f"Alert created: {alert_id} - {title}")
        
        return alert
    
    def get_pending_alerts(self) -> List[Alert]:
        """Get all unresolved alerts"""
        return [a for a in self.alert_history if not a.resolved]
    
    def resolve_alert(self, alert_id: str) -> Optional[Alert]:
        """Mark an alert as resolved"""
        for alert in self.alert_history:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                return alert
        return None
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of all alerts"""
        pending = [a for a in self.alert_history if not a.resolved]
        
        return {
            "total_alerts": len(self.alert_history),
            "pending_alerts": len(pending),
            "resolved_alerts": len(self.alert_history) - len(pending),
            "by_level": {
                "info": len([a for a in pending if a.level == AlertLevel.INFO]),
                "warning": len([a for a in pending if a.level == AlertLevel.WARNING]),
                "critical": len([a for a in pending if a.level == AlertLevel.CRITICAL]),
                "urgent": len([a for a in pending if a.level == AlertLevel.URGENT]),
            },
            "by_type": {
                t.value: len([a for a in pending if a.alert_type == t])
                for t in AlertType
            }
        }


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get singleton instance of notification service"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
