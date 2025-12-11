"""
Notification Service
====================
Unified notification service supporting multiple channels:
- WhatsApp (via Meta Graph API)
- Email (via Postmark API)

Environment Variables Required:
- META_BEARER_TOKEN: Meta Graph API token for WhatsApp
- PHONE_NUMBER_ID: WhatsApp Business phone number ID
- POSTMARK_SERVER_TOKEN: Postmark API token for email
- DEFAULT_SENDER_EMAIL: Default sender email address
"""

import requests
import json
import logging
import os
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Supported notification channels"""
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"


@dataclass
class NotificationResult:
    """Result of a notification attempt"""
    success: bool
    channel: str
    recipient: str
    message_id: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "channel": self.channel,
            "recipient": self.recipient,
            "message_id": self.message_id,
            "error": self.error
        }


class NotificationService:
    """
    Unified Notification Service for NEXUS alerts.
    
    Usage:
        service = NotificationService()
        
        # Send WhatsApp
        result = service.send_whatsapp("919343584820", "Alert: Low stock!")
        
        # Send Email via Postmark
        result = service.send_email("user@example.com", "Alert", "Low stock details...")
        
        # Send based on preference
        result = service.send_alert(
            recipient="919343584820",
            subject="Stock Alert",
            message="Critical: Tower material low",
            channel=NotificationChannel.WHATSAPP
        )
    """
    
    # Meta Graph API version
    GRAPH_API_VERSION = "v22.0"
    
    # Postmark API URL
    POSTMARK_API_URL = "https://api.postmarkapp.com/email"
    
    def __init__(
        self,
        whatsapp_token: str = None,
        whatsapp_phone_id: str = None,
        postmark_token: str = None,
        sender_email: str = None,
        default_whatsapp_recipient: str = None
    ):
        """
        Initialize notification service with credentials.
        
        Falls back to environment variables if not provided.
        """
        # WhatsApp credentials (Meta Graph API)
        self.whatsapp_token = whatsapp_token or os.getenv("META_BEARER_TOKEN")
        self.whatsapp_phone_id = whatsapp_phone_id or os.getenv("PHONE_NUMBER_ID")
        self.default_whatsapp_recipient = default_whatsapp_recipient or os.getenv("WHATSAPP_BUSINESS_NUMBER")
        
        # Postmark credentials
        self.postmark_token = postmark_token or os.getenv("POSTMARK_SERVER_TOKEN")
        self.sender_email = sender_email or os.getenv("DEFAULT_SENDER_EMAIL")
    
    # =========================================================================
    # WHATSAPP (Meta Graph API)
    # =========================================================================
    
    def send_whatsapp(
        self, 
        phone_number: str = None, 
        message: str = "",
        template_name: str = None,
        template_params: Dict = None
    ) -> NotificationResult:
        """
        Send WhatsApp message using Meta Graph API.
        
        Args:
            phone_number: Recipient phone with country code (e.g., "919343584820")
                         If not provided, uses WHATSAPP_BUSINESS_NUMBER from env
            message: Text message to send (for direct messages)
            template_name: Optional WhatsApp template name
            template_params: Optional template parameters
        
        Returns:
            NotificationResult with success status
        """
        # Use default recipient if not provided
        recipient = phone_number or self.default_whatsapp_recipient
        
        if not self.whatsapp_token or not self.whatsapp_phone_id:
            return NotificationResult(
                success=False,
                channel="whatsapp",
                recipient=recipient or "unknown",
                error="WhatsApp credentials not configured. Set META_BEARER_TOKEN and PHONE_NUMBER_ID in .env"
            )
        
        if not recipient:
            return NotificationResult(
                success=False,
                channel="whatsapp",
                recipient="unknown",
                error="No recipient phone number provided. Set WHATSAPP_BUSINESS_NUMBER in .env or pass phone_number"
            )
        
        url = f"https://graph.facebook.com/{self.GRAPH_API_VERSION}/{self.whatsapp_phone_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.whatsapp_token}",
            "Content-Type": "application/json"
        }
        
        # Build payload
        if template_name:
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en"},
                    "components": []
                }
            }
            if template_params:
                payload["template"]["components"].append({
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": v} for v in template_params.values()
                    ]
                })
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "text",
                "text": {"body": message}
            }
        
        try:
            response = requests.post(
                url, 
                headers=headers, 
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id")
                logger.info(f"✔ WhatsApp sent to {recipient}: {message_id}")
                return NotificationResult(
                    success=True,
                    channel="whatsapp",
                    recipient=recipient,
                    message_id=message_id
                )
            else:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
                logger.error(f"❌ WhatsApp failed: {error_msg}")
                return NotificationResult(
                    success=False,
                    channel="whatsapp",
                    recipient=recipient,
                    error=error_msg
                )
                
        except Exception as e:
            logger.exception(f"❌ WhatsApp exception: {e}")
            return NotificationResult(
                success=False,
                channel="whatsapp",
                recipient=recipient,
                error=str(e)
            )
    
    def upload_whatsapp_media(
        self,
        file_bytes: bytes,
        mime_type: str = "application/pdf",
        filename: str = "document.pdf"
    ) -> Optional[str]:
        """
        Upload media to WhatsApp for sending as document.
        
        Args:
            file_bytes: File content as bytes
            mime_type: MIME type of the file
            filename: Name of the file
            
        Returns:
            Media ID if successful, None otherwise
        """
        if not self.whatsapp_token or not self.whatsapp_phone_id:
            logger.error("WhatsApp credentials not configured")
            return None
        
        url = f"https://graph.facebook.com/{self.GRAPH_API_VERSION}/{self.whatsapp_phone_id}/media"
        
        headers = {
            "Authorization": f"Bearer {self.whatsapp_token}"
        }
        
        files = {
            "file": (filename, file_bytes, mime_type),
            "messaging_product": (None, "whatsapp"),
            "type": (None, mime_type)
        }
        
        try:
            response = requests.post(url, headers=headers, files=files, timeout=60)
            
            if response.status_code in [200, 201]:
                data = response.json()
                media_id = data.get("id")
                logger.info(f"✔ WhatsApp media uploaded: {media_id}")
                return media_id
            else:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
                logger.error(f"❌ WhatsApp media upload failed: {error_msg}")
                return None
                
        except Exception as e:
            logger.exception(f"❌ WhatsApp media upload exception: {e}")
            return None
    
    def send_whatsapp_document(
        self,
        phone_number: str = None,
        document_bytes: bytes = None,
        document_url: str = None,
        filename: str = "report.pdf",
        caption: str = None,
        mime_type: str = "application/pdf"
    ) -> NotificationResult:
        """
        Send a document via WhatsApp.
        
        Args:
            phone_number: Recipient phone with country code
            document_bytes: Document content as bytes (will be uploaded first)
            document_url: OR a public URL to the document
            filename: Name of the document
            caption: Optional caption/message with the document
            mime_type: MIME type of the document
        
        Returns:
            NotificationResult with success status
        """
        recipient = phone_number or self.default_whatsapp_recipient
        
        if not self.whatsapp_token or not self.whatsapp_phone_id:
            return NotificationResult(
                success=False,
                channel="whatsapp",
                recipient=recipient or "unknown",
                error="WhatsApp credentials not configured"
            )
        
        if not recipient:
            return NotificationResult(
                success=False,
                channel="whatsapp",
                recipient="unknown",
                error="No recipient phone number provided"
            )
        
        # If we have bytes, upload first to get media_id
        media_id = None
        if document_bytes:
            media_id = self.upload_whatsapp_media(
                file_bytes=document_bytes,
                mime_type=mime_type,
                filename=filename
            )
            if not media_id:
                return NotificationResult(
                    success=False,
                    channel="whatsapp",
                    recipient=recipient,
                    error="Failed to upload document to WhatsApp"
                )
        
        url = f"https://graph.facebook.com/{self.GRAPH_API_VERSION}/{self.whatsapp_phone_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.whatsapp_token}",
            "Content-Type": "application/json"
        }
        
        # Build document payload
        document_payload = {"filename": filename}
        
        if media_id:
            document_payload["id"] = media_id
        elif document_url:
            document_payload["link"] = document_url
        else:
            return NotificationResult(
                success=False,
                channel="whatsapp",
                recipient=recipient,
                error="Either document_bytes or document_url must be provided"
            )
        
        if caption:
            document_payload["caption"] = caption
        
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "document",
            "document": document_payload
        }
        
        try:
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id")
                logger.info(f"✔ WhatsApp document sent to {recipient}: {message_id}")
                return NotificationResult(
                    success=True,
                    channel="whatsapp",
                    recipient=recipient,
                    message_id=message_id
                )
            else:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
                logger.error(f"❌ WhatsApp document failed: {error_msg}")
                return NotificationResult(
                    success=False,
                    channel="whatsapp",
                    recipient=recipient,
                    error=error_msg
                )
                
        except Exception as e:
            logger.exception(f"❌ WhatsApp document exception: {e}")
            return NotificationResult(
                success=False,
                channel="whatsapp",
                recipient=recipient,
                error=str(e)
            )
    
    # =========================================================================
    # EMAIL (Postmark API)
    # =========================================================================
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: str = None,
        cc: List[str] = None,
        bcc: List[str] = None,
        attachments: List[Dict] = None
    ) -> NotificationResult:
        """
        Send email via Postmark API.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            cc: Optional CC recipients
            bcc: Optional BCC recipients
            attachments: Optional list of attachments, each with:
                - Name: filename (e.g., "report.pdf")
                - Content: base64-encoded content
                - ContentType: MIME type (e.g., "application/pdf")
        
        Returns:
            NotificationResult with success status
        """
        if not self.postmark_token:
            return NotificationResult(
                success=False,
                channel="email",
                recipient=to_email,
                error="Postmark credentials not configured. Set POSTMARK_SERVER_TOKEN in .env"
            )
        
        if not self.sender_email:
            return NotificationResult(
                success=False,
                channel="email",
                recipient=to_email,
                error="Sender email not configured. Set DEFAULT_SENDER_EMAIL in .env"
            )
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Postmark-Server-Token": self.postmark_token
        }
        
        payload = {
            "From": self.sender_email,
            "To": to_email,
            "Subject": subject,
            "TextBody": body
        }
        
        if html_body:
            payload["HtmlBody"] = html_body
        
        if cc:
            payload["Cc"] = ", ".join(cc)
        
        if bcc:
            payload["Bcc"] = ", ".join(bcc)
        
        # Add attachments if provided
        if attachments:
            payload["Attachments"] = attachments
        
        try:
            response = requests.post(
                self.POSTMARK_API_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                message_id = data.get("MessageID")
                logger.info(f"✔ Email sent to {to_email}: {message_id}")
                return NotificationResult(
                    success=True,
                    channel="email",
                    recipient=to_email,
                    message_id=message_id
                )
            else:
                error_data = response.json()
                error_msg = error_data.get("Message", response.text)
                logger.error(f"❌ Email failed: {error_msg}")
                return NotificationResult(
                    success=False,
                    channel="email",
                    recipient=to_email,
                    error=error_msg
                )
                
        except Exception as e:
            logger.exception(f"❌ Email exception: {e}")
            return NotificationResult(
                success=False,
                channel="email",
                recipient=to_email,
                error=str(e)
            )
    
    # =========================================================================
    # UNIFIED ALERT SENDER
    # =========================================================================
    
    def send_alert(
        self,
        recipient: str,
        subject: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.EMAIL,
        fallback: bool = True,
        html_body: str = None
    ) -> NotificationResult:
        """
        Send alert via specified channel with optional fallback.
        
        Args:
            recipient: Phone number (for WhatsApp) or email address
            subject: Alert subject (used for email, prefixed to WhatsApp)
            message: Alert message body
            channel: Primary notification channel
            fallback: If True, try alternate channel on failure
            html_body: Optional HTML body for email
        
        Returns:
            NotificationResult
        """
        full_message = f"🚨 {subject}\n\n{message}"
        
        if channel == NotificationChannel.WHATSAPP:
            result = self.send_whatsapp(recipient, full_message)
            
            # Fallback to email if WhatsApp fails and recipient looks like email
            if not result.success and fallback and "@" in recipient:
                logger.info(f"WhatsApp failed, falling back to email")
                return self.send_email(recipient, subject, message, html_body)
            return result
        
        elif channel == NotificationChannel.EMAIL:
            result = self.send_email(recipient, subject, message, html_body)
            return result
        
        else:
            return NotificationResult(
                success=False,
                channel=channel.value,
                recipient=recipient,
                error=f"Channel {channel.value} not implemented"
            )
    
    def send_bulk_alerts(
        self,
        alerts: List[Dict],
        channel: NotificationChannel = NotificationChannel.EMAIL
    ) -> List[NotificationResult]:
        """
        Send multiple alerts.
        
        Args:
            alerts: List of dicts with 'recipient', 'subject', 'message'
            channel: Notification channel
        
        Returns:
            List of NotificationResults
        """
        results = []
        for alert in alerts:
            result = self.send_alert(
                recipient=alert["recipient"],
                subject=alert["subject"],
                message=alert["message"],
                channel=channel
            )
            results.append(result)
        return results
    
    def get_configuration_status(self) -> Dict:
        """
        Check which notification channels are properly configured.
        
        Returns:
            Dict with configuration status for each channel
        """
        return {
            "whatsapp": {
                "configured": bool(self.whatsapp_token and self.whatsapp_phone_id),
                "has_token": bool(self.whatsapp_token),
                "has_phone_id": bool(self.whatsapp_phone_id),
                "default_recipient": self.default_whatsapp_recipient,
                "required_env_vars": ["META_BEARER_TOKEN", "PHONE_NUMBER_ID"],
                "optional_env_vars": ["WHATSAPP_BUSINESS_NUMBER"]
            },
            "email": {
                "configured": bool(self.postmark_token and self.sender_email),
                "has_token": bool(self.postmark_token),
                "sender_email": self.sender_email,
                "required_env_vars": ["POSTMARK_SERVER_TOKEN", "DEFAULT_SENDER_EMAIL"]
            }
        }


# =========================================================================
# CONVENIENCE FUNCTIONS
# =========================================================================

def send_whatsapp(
    phone_number: str,
    message: str,
    token: str = None,
    phone_number_id: str = None
) -> Dict:
    """
    Simple function to send WhatsApp message.
    
    Returns dict with success status and message_id or error.
    """
    service = NotificationService(
        whatsapp_token=token,
        whatsapp_phone_id=phone_number_id
    )
    result = service.send_whatsapp(phone_number, message)
    return result.to_dict()


def send_email(
    to_email: str,
    subject: str,
    body: str,
    postmark_token: str = None,
    sender_email: str = None
) -> Dict:
    """
    Simple function to send email via Postmark.
    
    Returns dict with success status.
    """
    service = NotificationService(
        postmark_token=postmark_token,
        sender_email=sender_email
    )
    result = service.send_email(to_email, subject, body)
    return result.to_dict()
