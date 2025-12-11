"""
LLM Service - Groq API Integration
====================================
Generates contextual alert messages for inventory notifications.

Uses Groq's fast inference for generating:
- Understocking warnings (when UTR > threshold)
- Overstocking alerts (when OTR > threshold)
- Contextual recommendations based on inventory status

Environment Variables Required:
- GROQ_API_KEY: Groq API key for LLM access
"""

import os
import json
import logging
import httpx
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Types of inventory alerts"""
    UNDERSTOCK = "understock"
    OVERSTOCK = "overstock"
    CRITICAL = "critical"
    REORDER = "reorder"
    OK = "ok"


@dataclass
class AlertContext:
    """Context for generating alert messages"""
    material_name: str
    material_code: str
    warehouse_name: str
    warehouse_code: str
    location: str
    current_stock: float
    reorder_point: float
    safety_stock: float
    max_stock_level: float
    utr: float  # Understock ratio
    otr: float  # Overstock ratio
    par: float  # Procurement Adequacy Ratio
    days_of_stock: float
    lead_time_days: int
    daily_demand: float
    alert_type: AlertType
    severity: str  # RED, AMBER, GREEN
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "material": {
                "name": self.material_name,
                "code": self.material_code
            },
            "warehouse": {
                "name": self.warehouse_name,
                "code": self.warehouse_code,
                "location": self.location
            },
            "stock_levels": {
                "current": self.current_stock,
                "reorder_point": self.reorder_point,
                "safety_stock": self.safety_stock,
                "max_level": self.max_stock_level
            },
            "ratios": {
                "utr": round(self.utr, 4),
                "otr": round(self.otr, 4),
                "par": round(self.par, 4)
            },
            "metrics": {
                "days_of_stock": round(self.days_of_stock, 1),
                "lead_time_days": self.lead_time_days,
                "daily_demand": round(self.daily_demand, 2)
            },
            "alert": {
                "type": self.alert_type.value,
                "severity": self.severity
            }
        }


@dataclass
class LLMGeneratedAlert:
    """Generated alert message from LLM"""
    subject: str
    message: str
    whatsapp_message: str
    recommended_actions: list
    urgency_level: str
    summary: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "message": self.message,
            "whatsapp_message": self.whatsapp_message,
            "recommended_actions": self.recommended_actions,
            "urgency_level": self.urgency_level,
            "summary": self.summary
        }


class LLMService:
    """
    Groq-powered LLM Service for generating contextual inventory alerts.
    
    Usage:
        service = LLMService()
        
        context = AlertContext(
            material_name="Steel Tower Section",
            material_code="MAT-001",
            warehouse_name="North Region Warehouse",
            ...
        )
        
        alert = service.generate_alert(context)
        print(alert.message)
    """
    
    # Groq API configuration
    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"  # Fast and capable model
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize LLM service with Groq API credentials.
        
        Falls back to environment variable if not provided.
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or self.DEFAULT_MODEL
        
        if not self.api_key:
            logger.warning("GROQ_API_KEY not found - LLM service will use fallback messages")
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for inventory alert generation"""
        return """You are NEXUS, an AI-powered inventory management assistant for POWERGRID India, managing electrical grid infrastructure materials across warehouses and substations.

Your role is to generate clear, actionable, and professional alert messages for inventory status changes.

Guidelines:
1. Be concise but informative
2. Use professional tone suitable for operations managers
3. Include specific numbers and percentages
4. Provide actionable recommendations
5. Consider urgency based on severity (RED = Critical, AMBER = Warning, GREEN = OK)
6. For WhatsApp messages, keep them shorter (under 300 characters) with key info only
7. Use Indian English conventions where appropriate

For UNDERSTOCKING (high UTR):
- Emphasize risk of stockouts
- Mention lead time considerations
- Suggest immediate procurement actions

For OVERSTOCKING (high OTR):
- Highlight holding costs and capital lock-up
- Suggest redistribution to other warehouses
- Consider project pipeline utilization

Always respond with a valid JSON object."""

    def _build_user_prompt(self, context: AlertContext) -> str:
        """Build the user prompt with context"""
        alert_type_desc = {
            AlertType.UNDERSTOCK: "UNDERSTOCKING ALERT - Stock below reorder point",
            AlertType.OVERSTOCK: "OVERSTOCKING ALERT - Stock exceeds maximum level",
            AlertType.CRITICAL: "CRITICAL ALERT - Immediate action required",
            AlertType.REORDER: "REORDER ALERT - Time to replenish stock",
            AlertType.OK: "STATUS OK - Stock levels normal"
        }
        
        return f"""Generate an inventory alert message for the following situation:

ALERT TYPE: {alert_type_desc.get(context.alert_type, "INVENTORY ALERT")}
SEVERITY: {context.severity}

MATERIAL DETAILS:
- Name: {context.material_name}
- Code: {context.material_code}

LOCATION:
- Warehouse: {context.warehouse_name} ({context.warehouse_code})
- Location: {context.location}

STOCK STATUS:
- Current Stock: {context.current_stock:.0f} units
- Reorder Point: {context.reorder_point:.0f} units
- Safety Stock: {context.safety_stock:.0f} units
- Maximum Level: {context.max_stock_level:.0f} units
- Days of Stock: {context.days_of_stock:.1f} days
- Lead Time: {context.lead_time_days} days

KEY RATIOS:
- UTR (Understock Ratio): {context.utr:.2%} {"⚠️ HIGH" if context.utr > 0.3 else ""}
- OTR (Overstock Ratio): {context.otr:.2%} {"⚠️ HIGH" if context.otr > 0.3 else ""}
- PAR (Procurement Adequacy): {context.par:.2%}

Daily Demand: {context.daily_demand:.1f} units/day

Generate a response in this exact JSON format:
{{
    "subject": "Email subject line (max 80 chars)",
    "message": "Full email message body (2-3 paragraphs, professional tone)",
    "whatsapp_message": "Short WhatsApp message (max 280 chars with key info)",
    "recommended_actions": ["Action 1", "Action 2", "Action 3"],
    "urgency_level": "IMMEDIATE/HIGH/MEDIUM/LOW",
    "summary": "One sentence summary (max 100 chars)"
}}"""

    async def generate_alert_async(self, context: AlertContext) -> LLMGeneratedAlert:
        """
        Generate alert message using Groq API (async version).
        
        Args:
            context: AlertContext with all inventory details
            
        Returns:
            LLMGeneratedAlert with generated messages
        """
        if not self.api_key:
            return self._fallback_alert(context)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": self._build_system_prompt()},
                            {"role": "user", "content": self._build_user_prompt(context)}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1024,
                        "response_format": {"type": "json_object"}
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    
                    return LLMGeneratedAlert(
                        subject=parsed.get("subject", self._default_subject(context)),
                        message=parsed.get("message", self._default_message(context)),
                        whatsapp_message=parsed.get("whatsapp_message", self._default_whatsapp(context)),
                        recommended_actions=parsed.get("recommended_actions", []),
                        urgency_level=parsed.get("urgency_level", "MEDIUM"),
                        summary=parsed.get("summary", "Inventory alert generated")
                    )
                else:
                    logger.error(f"Groq API error: {response.status_code} - {response.text}")
                    return self._fallback_alert(context)
                    
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            return self._fallback_alert(context)
    
    def generate_alert(self, context: AlertContext) -> LLMGeneratedAlert:
        """
        Generate alert message using Groq API (sync version).
        
        Args:
            context: AlertContext with all inventory details
            
        Returns:
            LLMGeneratedAlert with generated messages
        """
        if not self.api_key:
            return self._fallback_alert(context)
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": self._build_system_prompt()},
                            {"role": "user", "content": self._build_user_prompt(context)}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1024,
                        "response_format": {"type": "json_object"}
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    
                    logger.info(f"LLM alert generated successfully for {context.material_code}")
                    
                    return LLMGeneratedAlert(
                        subject=parsed.get("subject", self._default_subject(context)),
                        message=parsed.get("message", self._default_message(context)),
                        whatsapp_message=parsed.get("whatsapp_message", self._default_whatsapp(context)),
                        recommended_actions=parsed.get("recommended_actions", []),
                        urgency_level=parsed.get("urgency_level", "MEDIUM"),
                        summary=parsed.get("summary", "Inventory alert generated")
                    )
                else:
                    logger.error(f"Groq API error: {response.status_code} - {response.text}")
                    return self._fallback_alert(context)
                    
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            return self._fallback_alert(context)
    
    def _fallback_alert(self, context: AlertContext) -> LLMGeneratedAlert:
        """Generate fallback alert when LLM is unavailable"""
        return LLMGeneratedAlert(
            subject=self._default_subject(context),
            message=self._default_message(context),
            whatsapp_message=self._default_whatsapp(context),
            recommended_actions=self._default_actions(context),
            urgency_level=self._default_urgency(context),
            summary=self._default_summary(context)
        )
    
    def _default_subject(self, context: AlertContext) -> str:
        """Generate default email subject"""
        severity_emoji = {"RED": "🔴", "AMBER": "🟡", "GREEN": "🟢"}.get(context.severity, "")
        alert_type = context.alert_type.value.upper()
        return f"{severity_emoji} NEXUS Alert: {alert_type} - {context.material_name} at {context.warehouse_code}"
    
    def _default_message(self, context: AlertContext) -> str:
        """Generate default email message"""
        if context.alert_type == AlertType.UNDERSTOCK:
            situation = f"Stock levels for {context.material_name} have fallen below the reorder point."
            risk = f"Current stock of {context.current_stock:.0f} units provides only {context.days_of_stock:.1f} days of coverage, while lead time is {context.lead_time_days} days."
            action = "Immediate procurement action is recommended to avoid stockout."
        elif context.alert_type == AlertType.OVERSTOCK:
            situation = f"Stock levels for {context.material_name} exceed the maximum recommended level."
            risk = f"Current stock of {context.current_stock:.0f} units is {((context.current_stock / context.max_stock_level) - 1) * 100:.1f}% above maximum, tying up capital and warehouse space."
            action = "Consider redistributing excess stock to other warehouses or accelerating project utilization."
        else:
            situation = f"Inventory status update for {context.material_name}."
            risk = f"Current stock: {context.current_stock:.0f} units with {context.days_of_stock:.1f} days of coverage."
            action = "Continue monitoring stock levels."
        
        return f"""NEXUS Inventory Alert

{situation}

Location: {context.warehouse_name} ({context.warehouse_code})
Material: {context.material_name} ({context.material_code})
Location: {context.location}

Stock Status:
- Current Stock: {context.current_stock:.0f} units
- Reorder Point: {context.reorder_point:.0f} units  
- Days of Stock: {context.days_of_stock:.1f} days
- UTR (Understock Ratio): {context.utr:.1%}
- OTR (Overstock Ratio): {context.otr:.1%}

{risk}

Recommended Action:
{action}

---
This is an automated alert from NEXUS Inventory Management System.
POWERGRID Corporation of India Limited"""

    def _default_whatsapp(self, context: AlertContext) -> str:
        """Generate default WhatsApp message"""
        severity_emoji = {"RED": "🔴", "AMBER": "🟡", "GREEN": "🟢"}.get(context.severity, "📦")
        alert_type = context.alert_type.value.upper()
        
        return f"""{severity_emoji} NEXUS {alert_type}
Material: {context.material_name}
Location: {context.warehouse_code}
Stock: {context.current_stock:.0f} units
Days left: {context.days_of_stock:.1f}
UTR: {context.utr:.1%} | OTR: {context.otr:.1%}"""

    def _default_actions(self, context: AlertContext) -> list:
        """Generate default recommended actions"""
        if context.alert_type == AlertType.UNDERSTOCK or context.utr > 0.3:
            return [
                f"Initiate purchase order for {context.reorder_point - context.current_stock:.0f} units",
                f"Check with nearby warehouses for emergency transfer",
                "Review upcoming project requirements",
                "Contact approved vendors for fastest delivery"
            ]
        elif context.alert_type == AlertType.OVERSTOCK or context.otr > 0.3:
            return [
                "Identify warehouses with low stock for transfer",
                "Review upcoming project pipeline for utilization",
                "Consider postponing incoming orders",
                "Evaluate storage optimization options"
            ]
        else:
            return [
                "Continue regular monitoring",
                "Review demand forecasts",
                "Maintain safety stock levels"
            ]
    
    def _default_urgency(self, context: AlertContext) -> str:
        """Determine default urgency level"""
        if context.severity == "RED" or context.utr > 0.7:
            return "IMMEDIATE"
        elif context.severity == "AMBER" or context.utr > 0.5:
            return "HIGH"
        elif context.utr > 0.2 or context.otr > 0.2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _default_summary(self, context: AlertContext) -> str:
        """Generate default summary"""
        if context.alert_type == AlertType.UNDERSTOCK:
            return f"{context.material_code} at {context.warehouse_code}: {context.days_of_stock:.0f} days of stock remaining"
        elif context.alert_type == AlertType.OVERSTOCK:
            return f"{context.material_code} at {context.warehouse_code}: {context.otr:.0%} overstocked"
        else:
            return f"{context.material_code} at {context.warehouse_code}: Stock level update"
    
    def generate_report_content(
        self,
        material_name: str,
        material_code: str,
        warehouse_name: str,
        current_stock: float,
        optimal_stock: float,
        history: list,
        metrics: dict
    ) -> str:
        """
        Generate a detailed report content using LLM.
        
        For creating comprehensive inventory reports with history analysis.
        """
        if not self.api_key:
            return self._fallback_report(material_name, current_stock, optimal_stock, metrics)
        
        try:
            history_summary = "\n".join([
                f"- {h.get('date', 'N/A')}: {h.get('action', 'N/A')} - {h.get('quantity', 0)} units"
                for h in (history[:10] if history else [])  # Last 10 entries
            ])
            
            prompt = f"""Generate a concise inventory report for:

Material: {material_name} ({material_code})
Warehouse: {warehouse_name}
Current Stock: {current_stock:.0f} units
Optimal Stock: {optimal_stock:.0f} units
Gap: {optimal_stock - current_stock:.0f} units

Metrics:
- UTR: {metrics.get('utr', 0):.2%}
- OTR: {metrics.get('otr', 0):.2%}
- Days of Stock: {metrics.get('days_of_stock', 0):.1f}

Recent History:
{history_summary if history_summary else "No recent transactions"}

Provide a 2-3 paragraph analysis with key findings and recommendations."""

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are NEXUS, an inventory management AI. Generate clear, professional inventory reports."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.5,
                        "max_tokens": 800
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return self._fallback_report(material_name, current_stock, optimal_stock, metrics)
                    
        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            return self._fallback_report(material_name, current_stock, optimal_stock, metrics)
    
    def _fallback_report(self, material_name: str, current_stock: float, optimal_stock: float, metrics: dict) -> str:
        """Generate fallback report when LLM is unavailable"""
        gap = optimal_stock - current_stock
        status = "understocked" if gap > 0 else "overstocked" if gap < 0 else "optimal"
        
        return f"""Inventory Report: {material_name}

Current Status: Stock is currently {status}.
- Current Stock: {current_stock:.0f} units
- Optimal Level: {optimal_stock:.0f} units
- Gap: {abs(gap):.0f} units {'needed' if gap > 0 else 'excess' if gap < 0 else ''}

Key Metrics:
- Understock Ratio (UTR): {metrics.get('utr', 0):.1%}
- Overstock Ratio (OTR): {metrics.get('otr', 0):.1%}
- Days of Stock: {metrics.get('days_of_stock', 0):.1f}

Recommendation: {'Initiate procurement to restore optimal levels.' if gap > 0 else 'Consider redistribution to balance inventory.' if gap < 0 else 'Maintain current stock management practices.'}"""


# Convenience function for quick access
def get_llm_service() -> LLMService:
    """Get a configured LLM service instance"""
    return LLMService()
