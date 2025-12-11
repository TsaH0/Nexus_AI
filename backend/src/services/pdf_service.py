"""
PDF Document Service
=====================
Generates professional PDF reports for inventory alerts and status updates.

Uses ReportLab for PDF generation with a consistent template design
suitable for POWERGRID India's corporate communications.

Install: pip install reportlab
"""

import os
import io
import base64
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# IST Timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now() -> datetime:
    """Get current datetime in IST timezone"""
    return datetime.now(IST)

def to_ist(dt: datetime) -> datetime:
    """Convert a datetime to IST timezone"""
    if dt is None:
        return get_ist_now()
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, PageBreak, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)


@dataclass
class ReportContent:
    """Content for generating inventory report"""
    title: str
    subtitle: str
    material_name: str
    material_code: str
    warehouse_name: str
    warehouse_code: str
    location: str
    
    # Stock metrics
    current_stock: float
    optimal_stock: float
    reorder_point: float
    safety_stock: float
    max_stock_level: float
    
    # Ratios
    utr: float
    otr: float
    par: float
    days_of_stock: float
    daily_demand: float
    
    # Status
    severity: str  # RED, AMBER, GREEN
    alert_type: str  # understock, overstock, ok
    
    # History
    history: List[Dict[str, Any]]
    
    # LLM content
    summary: str
    recommendations: List[str]
    detailed_analysis: Optional[str] = None
    
    # Meta
    generated_at: datetime = None
    report_id: str = None


class PDFService:
    """
    Professional PDF Report Generator for NEXUS Inventory System.
    
    Usage:
        service = PDFService()
        
        content = ReportContent(
            title="Inventory Alert Report",
            material_name="Steel Tower Section",
            ...
        )
        
        # Get PDF as bytes
        pdf_bytes = service.generate_report(content)
        
        # Get PDF as base64 (for email attachment)
        pdf_base64 = service.generate_report_base64(content)
        
        # Save to file
        service.save_report(content, "/path/to/report.pdf")
    """
    
    # Brand colors for POWERGRID
    BRAND_PRIMARY = colors.HexColor("#1E3A5F")  # Navy blue
    BRAND_SECONDARY = colors.HexColor("#2E7D32")  # Green
    BRAND_ACCENT = colors.HexColor("#FFA000")  # Amber
    BRAND_DANGER = colors.HexColor("#C62828")  # Red
    
    # Severity colors
    SEVERITY_COLORS = {
        "RED": colors.HexColor("#C62828"),
        "AMBER": colors.HexColor("#FFA000"),
        "GREEN": colors.HexColor("#2E7D32")
    }
    
    def __init__(self, output_dir: str = None):
        """
        Initialize PDF service.
        
        Args:
            output_dir: Directory to save generated PDFs (default: data/outputs/reports)
        """
        if not REPORTLAB_AVAILABLE:
            logger.warning("ReportLab not installed. PDF generation will be limited.")
        
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "outputs", "reports"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize styles
        self.styles = self._create_styles()
    
    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create custom paragraph styles"""
        if not REPORTLAB_AVAILABLE:
            return {}
        
        base_styles = getSampleStyleSheet()
        
        styles = {
            "title": ParagraphStyle(
                "CustomTitle",
                parent=base_styles["Heading1"],
                fontSize=24,
                textColor=self.BRAND_PRIMARY,
                spaceAfter=12,
                alignment=TA_CENTER
            ),
            "subtitle": ParagraphStyle(
                "CustomSubtitle",
                parent=base_styles["Heading2"],
                fontSize=14,
                textColor=colors.grey,
                spaceAfter=20,
                alignment=TA_CENTER
            ),
            "heading": ParagraphStyle(
                "CustomHeading",
                parent=base_styles["Heading2"],
                fontSize=14,
                textColor=self.BRAND_PRIMARY,
                spaceBefore=16,
                spaceAfter=8,
                borderPadding=4
            ),
            "subheading": ParagraphStyle(
                "CustomSubheading",
                parent=base_styles["Heading3"],
                fontSize=12,
                textColor=self.BRAND_PRIMARY,
                spaceBefore=10,
                spaceAfter=6
            ),
            "body": ParagraphStyle(
                "CustomBody",
                parent=base_styles["Normal"],
                fontSize=10,
                leading=14,
                alignment=TA_JUSTIFY,
                spaceAfter=8
            ),
            "body_bold": ParagraphStyle(
                "CustomBodyBold",
                parent=base_styles["Normal"],
                fontSize=10,
                leading=14,
                fontName="Helvetica-Bold"
            ),
            "small": ParagraphStyle(
                "CustomSmall",
                parent=base_styles["Normal"],
                fontSize=8,
                textColor=colors.grey
            ),
            "alert_red": ParagraphStyle(
                "AlertRed",
                parent=base_styles["Normal"],
                fontSize=12,
                textColor=colors.white,
                backColor=self.BRAND_DANGER,
                alignment=TA_CENTER,
                borderPadding=8
            ),
            "alert_amber": ParagraphStyle(
                "AlertAmber",
                parent=base_styles["Normal"],
                fontSize=12,
                textColor=colors.black,
                backColor=self.BRAND_ACCENT,
                alignment=TA_CENTER,
                borderPadding=8
            ),
            "alert_green": ParagraphStyle(
                "AlertGreen",
                parent=base_styles["Normal"],
                fontSize=12,
                textColor=colors.white,
                backColor=self.BRAND_SECONDARY,
                alignment=TA_CENTER,
                borderPadding=8
            ),
            "metric_label": ParagraphStyle(
                "MetricLabel",
                parent=base_styles["Normal"],
                fontSize=9,
                textColor=colors.grey
            ),
            "metric_value": ParagraphStyle(
                "MetricValue",
                parent=base_styles["Normal"],
                fontSize=14,
                fontName="Helvetica-Bold",
                textColor=self.BRAND_PRIMARY
            )
        }
        
        return styles
    
    def generate_report(self, content: ReportContent) -> bytes:
        """
        Generate PDF report from content.
        
        Args:
            content: ReportContent with all report data
            
        Returns:
            PDF document as bytes
        """
        if not REPORTLAB_AVAILABLE:
            return self._generate_fallback_report(content)
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        # Build document elements
        elements = []
        
        # Header
        elements.extend(self._build_header(content))
        
        # Alert banner
        elements.extend(self._build_alert_banner(content))
        
        # Material and Location info
        elements.extend(self._build_info_section(content))
        
        # Metrics section
        elements.extend(self._build_metrics_section(content))
        
        # Stock status
        elements.extend(self._build_stock_status(content))
        
        # Summary and recommendations
        elements.extend(self._build_analysis_section(content))
        
        # Transaction history
        elements.extend(self._build_history_section(content))
        
        # Footer
        elements.extend(self._build_footer(content))
        
        # Build PDF
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"Generated PDF report: {len(pdf_bytes)} bytes")
        return pdf_bytes
    
    def generate_report_base64(self, content: ReportContent) -> str:
        """
        Generate PDF report and return as base64 string.
        
        Useful for email attachments and API responses.
        """
        pdf_bytes = self.generate_report(content)
        return base64.b64encode(pdf_bytes).decode('utf-8')
    
    def save_report(self, content: ReportContent, filepath: str = None) -> str:
        """
        Generate and save PDF report to file.
        
        Args:
            content: ReportContent with all report data
            filepath: Optional custom filepath
            
        Returns:
            Path to saved file
        """
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"inventory_report_{content.material_code}_{timestamp}.pdf"
            filepath = os.path.join(self.output_dir, filename)
        
        pdf_bytes = self.generate_report(content)
        
        with open(filepath, 'wb') as f:
            f.write(pdf_bytes)
        
        logger.info(f"Saved PDF report to: {filepath}")
        return filepath
    
    def _build_header(self, content: ReportContent) -> list:
        """Build document header"""
        elements = []
        
        # Title
        elements.append(Paragraph(content.title, self.styles["title"]))
        
        # Subtitle
        elements.append(Paragraph(content.subtitle, self.styles["subtitle"]))
        
        # Horizontal rule
        elements.append(HRFlowable(
            width="100%",
            thickness=2,
            color=self.BRAND_PRIMARY,
            spaceBefore=5,
            spaceAfter=15
        ))
        
        return elements
    
    def _build_alert_banner(self, content: ReportContent) -> list:
        """Build severity alert banner"""
        elements = []
        
        severity_text = {
            "RED": "🔴 CRITICAL ALERT - Immediate Action Required",
            "AMBER": "🟡 WARNING - Attention Needed",
            "GREEN": "🟢 STATUS OK - All Systems Normal"
        }
        
        style_map = {
            "RED": self.styles["alert_red"],
            "AMBER": self.styles["alert_amber"],
            "GREEN": self.styles["alert_green"]
        }
        
        banner_text = severity_text.get(content.severity, "INVENTORY ALERT")
        banner_style = style_map.get(content.severity, self.styles["body"])
        
        # Create banner as a table for better styling
        banner_data = [[Paragraph(banner_text, banner_style)]]
        banner_table = Table(banner_data, colWidths=["100%"])
        banner_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.SEVERITY_COLORS.get(content.severity, colors.grey)),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white if content.severity != "AMBER" else colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        elements.append(banner_table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_info_section(self, content: ReportContent) -> list:
        """Build material and location information section"""
        elements = []
        
        elements.append(Paragraph("📦 Material & Location", self.styles["heading"]))
        
        # Two-column layout for info
        info_data = [
            [
                Paragraph("<b>Material:</b>", self.styles["body"]),
                Paragraph(f"{content.material_name}", self.styles["body"]),
                Paragraph("<b>Material Code:</b>", self.styles["body"]),
                Paragraph(f"{content.material_code}", self.styles["body"])
            ],
            [
                Paragraph("<b>Warehouse:</b>", self.styles["body"]),
                Paragraph(f"{content.warehouse_name}", self.styles["body"]),
                Paragraph("<b>Warehouse Code:</b>", self.styles["body"]),
                Paragraph(f"{content.warehouse_code}", self.styles["body"])
            ],
            [
                Paragraph("<b>Location:</b>", self.styles["body"]),
                Paragraph(f"{content.location}", self.styles["body"]),
                Paragraph("<b>Report Date:</b>", self.styles["body"]),
                Paragraph(f"{(content.generated_at or get_ist_now()).strftime('%d %b %Y, %I:%M %p')} IST", self.styles["body"])
            ]
        ]
        
        info_table = Table(info_data, colWidths=[80, 140, 90, 140])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _build_metrics_section(self, content: ReportContent) -> list:
        """Build key metrics section with visual cards"""
        elements = []
        
        elements.append(Paragraph("📊 Key Metrics", self.styles["heading"]))
        
        # Metrics cards
        def create_metric_cell(label: str, value: str, color=None):
            cell_color = color or self.BRAND_PRIMARY
            return [
                Paragraph(f"<font color='grey'>{label}</font>", self.styles["small"]),
                Paragraph(f"<font color='{cell_color}'><b>{value}</b></font>", self.styles["metric_value"])
            ]
        
        # Determine UTR/OTR colors based on values
        utr_color = "#C62828" if content.utr > 0.5 else "#FFA000" if content.utr > 0.2 else "#2E7D32"
        otr_color = "#C62828" if content.otr > 0.5 else "#FFA000" if content.otr > 0.2 else "#2E7D32"
        par_color = "#C62828" if content.par < 0.3 else "#FFA000" if content.par < 0.6 else "#2E7D32"
        
        metrics_row1 = [
            create_metric_cell("Current Stock", f"{content.current_stock:,.0f} units"),
            create_metric_cell("Reorder Point", f"{content.reorder_point:,.0f} units"),
            create_metric_cell("Safety Stock", f"{content.safety_stock:,.0f} units"),
            create_metric_cell("Max Level", f"{content.max_stock_level:,.0f} units")
        ]
        
        metrics_row2 = [
            create_metric_cell("UTR (Understock)", f"{content.utr:.1%}", utr_color),
            create_metric_cell("OTR (Overstock)", f"{content.otr:.1%}", otr_color),
            create_metric_cell("PAR (Adequacy)", f"{content.par:.1%}", par_color),
            create_metric_cell("Days of Stock", f"{content.days_of_stock:.1f} days")
        ]
        
        # Flatten for table
        metrics_data = [
            [item for sublist in metrics_row1 for item in sublist],
            [item for sublist in metrics_row2 for item in sublist]
        ]
        
        # Restructure for proper display
        metrics_display = []
        for row in [metrics_row1, metrics_row2]:
            display_row = []
            for metric in row:
                # Combine label and value in one cell
                cell_content = f"{metric[0].text}<br/>{metric[1].text}"
                display_row.append(Paragraph(cell_content, self.styles["body"]))
            metrics_display.append(display_row)
        
        metrics_table = Table(metrics_display, colWidths=[112, 112, 112, 112])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F5F5F5")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#E0E0E0")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(metrics_table)
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _build_stock_status(self, content: ReportContent) -> list:
        """Build stock status comparison"""
        elements = []
        
        elements.append(Paragraph("📈 Stock Status", self.styles["heading"]))
        
        gap = content.optimal_stock - content.current_stock
        gap_pct = (gap / content.optimal_stock * 100) if content.optimal_stock > 0 else 0
        
        status_text = "UNDERSTOCKED" if gap > 0 else "OVERSTOCKED" if gap < 0 else "OPTIMAL"
        status_color = self.BRAND_DANGER if gap > 0 else self.BRAND_ACCENT if gap < 0 else self.BRAND_SECONDARY
        
        status_data = [
            ["Current Stock", "Optimal Level", "Gap", "Status"],
            [
                f"{content.current_stock:,.0f}",
                f"{content.optimal_stock:,.0f}",
                f"{abs(gap):,.0f} ({abs(gap_pct):.1f}%)",
                status_text
            ]
        ]
        
        status_table = Table(status_data, colWidths=[112, 112, 112, 112])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.BRAND_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (3, 1), (3, 1), status_color),
            ('TEXTCOLOR', (3, 1), (3, 1), colors.white),
            ('FONTNAME', (3, 1), (3, 1), 'Helvetica-Bold'),
            ('BOX', (0, 0), (-1, -1), 1, self.BRAND_PRIMARY),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
        ]))
        
        elements.append(status_table)
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _build_analysis_section(self, content: ReportContent) -> list:
        """Build summary and recommendations section"""
        elements = []
        
        # Summary
        elements.append(Paragraph("📝 Summary", self.styles["heading"]))
        elements.append(Paragraph(content.summary, self.styles["body"]))
        elements.append(Spacer(1, 10))
        
        # Detailed analysis if available
        if content.detailed_analysis:
            elements.append(Paragraph("🔍 Detailed Analysis", self.styles["subheading"]))
            elements.append(Paragraph(content.detailed_analysis, self.styles["body"]))
            elements.append(Spacer(1, 10))
        
        # Recommendations
        if content.recommendations:
            elements.append(Paragraph("✅ Recommended Actions", self.styles["heading"]))
            
            for i, rec in enumerate(content.recommendations, 1):
                elements.append(Paragraph(
                    f"<b>{i}.</b> {rec}",
                    self.styles["body"]
                ))
            
            elements.append(Spacer(1, 10))
        
        return elements
    
    def _build_history_section(self, content: ReportContent) -> list:
        """Build transaction history section"""
        elements = []
        
        if not content.history:
            return elements
        
        elements.append(Paragraph("📜 Recent Transaction History", self.styles["heading"]))
        
        # History table
        history_header = ["Date", "Type", "Quantity", "Remarks"]
        history_data = [history_header]
        
        for h in content.history[:10]:  # Last 10 transactions
            date_str = h.get("date", "N/A")
            if date_str and date_str != "N/A":
                try:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    date_str = dt.strftime("%d %b %Y")
                except:
                    pass
            
            history_data.append([
                date_str,
                h.get("type", "N/A"),
                f"{h.get('quantity', 0):,.0f}",
                (h.get("remarks", "")[:40] + "...") if len(h.get("remarks", "")) > 40 else h.get("remarks", "")
            ])
        
        history_table = Table(history_data, colWidths=[80, 80, 80, 200])
        history_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.BRAND_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 1, self.BRAND_PRIMARY),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F8F8")])
        ]))
        
        elements.append(history_table)
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _build_footer(self, content: ReportContent) -> list:
        """Build document footer"""
        elements = []
        
        elements.append(HRFlowable(
            width="100%",
            thickness=1,
            color=colors.grey,
            spaceBefore=20,
            spaceAfter=10
        ))
        
        footer_text = f"""
        <font size="8" color="grey">
        This report was automatically generated by NEXUS Inventory Management System.<br/>
        Report ID: {content.report_id or 'N/A'}<br/>
        Generated: {(content.generated_at or datetime.now()).strftime('%Y-%m-%d %H:%M:%S UTC')}<br/>
        <br/>
        POWERGRID Corporation of India Limited<br/>
        For queries, contact: inventory-support@powergrid.in
        </font>
        """
        
        elements.append(Paragraph(footer_text, self.styles["small"]))
        
        return elements
    
    def _generate_fallback_report(self, content: ReportContent) -> bytes:
        """Generate simple text-based report if ReportLab not available"""
        report_text = f"""
NEXUS INVENTORY ALERT REPORT
============================

{content.title}
{content.subtitle}

SEVERITY: {content.severity}
ALERT TYPE: {content.alert_type.upper()}

MATERIAL INFORMATION
--------------------
Name: {content.material_name}
Code: {content.material_code}

LOCATION
--------
Warehouse: {content.warehouse_name} ({content.warehouse_code})
Location: {content.location}

STOCK STATUS
------------
Current Stock: {content.current_stock:,.0f} units
Optimal Stock: {content.optimal_stock:,.0f} units
Gap: {content.optimal_stock - content.current_stock:,.0f} units

KEY METRICS
-----------
UTR (Understock Ratio): {content.utr:.1%}
OTR (Overstock Ratio): {content.otr:.1%}
PAR (Procurement Adequacy): {content.par:.1%}
Days of Stock: {content.days_of_stock:.1f}
Daily Demand: {content.daily_demand:.1f} units/day

SUMMARY
-------
{content.summary}

RECOMMENDED ACTIONS
-------------------
{chr(10).join(f'{i+1}. {rec}' for i, rec in enumerate(content.recommendations))}

---
Generated: {(content.generated_at or get_ist_now()).strftime('%Y-%m-%d %H:%M:%S')} IST
Report ID: {content.report_id or 'N/A'}
NEXUS Inventory Management System - POWERGRID India
"""
        return report_text.encode('utf-8')


def get_pdf_service() -> PDFService:
    """Get a configured PDF service instance"""
    return PDFService()
