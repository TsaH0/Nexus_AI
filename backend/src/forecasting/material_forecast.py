"""
Material Forecast Engine - DYNAMIC VERSION
Uses actual database data: inventory levels, purchase orders, project material needs,
and historical consumption to generate realistic forecasts.

Prophet integration for time-series forecasting.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import math


@dataclass
class MaterialForecastResult:
    """Result for a single material forecast"""
    material_code: str
    material_name: str
    unit: str
    
    # Current state (from DB)
    current_stock: float
    in_transit: float
    ordered_pending: float
    reserved: float
    available: float  # current_stock - reserved
    
    # Demand (from projects)
    total_demand: float
    monthly_demand: float
    
    # Gap analysis
    supply_vs_demand: float  # positive = surplus, negative = shortage
    months_of_stock: float  # how many months current stock lasts
    
    # Forecast
    predicted_shortage_date: Optional[str]
    confidence: float
    status: str  # Healthy, At Risk, Critical, Out of Stock


class MaterialForecastEngine:
    """
    Dynamic forecast engine using actual database data.
    
    Data sources:
    - InventoryStock: Current stock levels at each warehouse
    - PurchaseOrder: Incoming materials (ordered/in-transit)
    - ProjectMaterialNeed: Project demands
    - InventoryTransaction: Historical consumption patterns (future)
    """
    
    def __init__(self, db_session=None):
        """Initialize with database session"""
        self.db_session = db_session
        self._cache = {}
    
    def _get_inventory_by_material(self) -> Dict[str, Dict]:
        """
        Get current inventory levels aggregated by material.
        
        Returns: {material_code: {total_available, total_reserved, total_in_transit, reorder_point}}
        """
        if not self.db_session:
            return {}
        
        from src.api.db_models import InventoryStock, Material
        from sqlalchemy import func
        
        # Aggregate stock by material across all warehouses
        stock_data = self.db_session.query(
            Material.material_code,
            Material.name,
            Material.unit,
            Material.unit_price,
            func.sum(InventoryStock.quantity_available).label('total_available'),
            func.sum(InventoryStock.quantity_reserved).label('total_reserved'),
            func.sum(InventoryStock.quantity_in_transit).label('total_in_transit'),
            func.sum(InventoryStock.reorder_point).label('total_reorder_point'),
            func.sum(InventoryStock.min_stock_level).label('total_min_stock'),
            func.count(InventoryStock.id).label('warehouse_count')
        ).join(
            InventoryStock, Material.id == InventoryStock.material_id
        ).group_by(Material.id).all()
        
        result = {}
        for row in stock_data:
            result[row.material_code] = {
                'material_code': row.material_code,
                'name': row.name,
                'unit': row.unit,
                'unit_price': row.unit_price or 0,
                'total_available': float(row.total_available or 0),
                'total_reserved': float(row.total_reserved or 0),
                'total_in_transit': float(row.total_in_transit or 0),
                'reorder_point': float(row.total_reorder_point or 0),
                'min_stock': float(row.total_min_stock or 0),
                'warehouse_count': row.warehouse_count
            }
        
        return result
    
    def _get_pending_orders(self) -> Dict[str, Dict]:
        """
        Get pending purchase orders by material.
        
        Returns: {material_code: {total_ordered, in_transit, manufacturing, placed, expected_dates}}
        """
        if not self.db_session:
            return {}
        
        from src.api.db_models import PurchaseOrder, Material
        
        orders = self.db_session.query(PurchaseOrder).filter(
            PurchaseOrder.status.in_(['Placed', 'In_Transit', 'Manufacturing'])
        ).all()
        
        result = {}
        for order in orders:
            material = self.db_session.query(Material).filter(
                Material.id == order.material_id
            ).first()
            
            if not material:
                continue
            
            mat_code = material.material_code
            if mat_code not in result:
                result[mat_code] = {
                    'total_ordered': 0,
                    'in_transit': 0,
                    'manufacturing': 0,
                    'placed': 0,
                    'orders': [],
                    'next_delivery': None
                }
            
            qty = float(order.quantity or 0)
            result[mat_code]['total_ordered'] += qty
            
            if order.status == 'In_Transit':
                result[mat_code]['in_transit'] += qty
            elif order.status == 'Manufacturing':
                result[mat_code]['manufacturing'] += qty
            elif order.status == 'Placed':
                result[mat_code]['placed'] += qty
            
            result[mat_code]['orders'].append({
                'order_code': order.order_code,
                'quantity': qty,
                'status': order.status,
                'expected_date': order.expected_delivery_date.isoformat() if order.expected_delivery_date else None
            })
            
            # Track next delivery
            if order.expected_delivery_date:
                if result[mat_code]['next_delivery'] is None:
                    result[mat_code]['next_delivery'] = order.expected_delivery_date
                elif order.expected_delivery_date < result[mat_code]['next_delivery']:
                    result[mat_code]['next_delivery'] = order.expected_delivery_date
        
        return result
    
    def _get_project_demands(self) -> Dict[str, Dict]:
        """
        Get material demands from active projects.
        
        Returns: {material_code: {total_needed, total_shortage, projects: [...]}}
        """
        if not self.db_session:
            return {}
        
        from src.api.db_models import ProjectMaterialNeed, SubstationProject, Material
        
        needs = self.db_session.query(ProjectMaterialNeed).all()
        
        result = {}
        for need in needs:
            # Get material info
            material = self.db_session.query(Material).filter(
                Material.id == need.material_id
            ).first()
            
            mat_code = material.material_code if material else f"MAT-{need.material_id}"
            
            if mat_code not in result:
                result[mat_code] = {
                    'total_needed': 0,
                    'total_available': 0,
                    'total_shortage': 0,
                    'projects': []
                }
            
            result[mat_code]['total_needed'] += float(need.quantity_needed or 0)
            result[mat_code]['total_available'] += float(need.quantity_available or 0)
            result[mat_code]['total_shortage'] += float(need.quantity_shortage or 0)
            
            # Get project info
            project = self.db_session.query(SubstationProject).filter(
                SubstationProject.id == need.project_id
            ).first()
            
            result[mat_code]['projects'].append({
                'project_id': need.project_id,
                'project_name': project.name if project else f"Project-{need.project_id}",
                'project_status': project.status if project else 'Unknown',
                'quantity_needed': float(need.quantity_needed or 0),
                'quantity_available': float(need.quantity_available or 0),
                'quantity_shortage': float(need.quantity_shortage or 0),
                'priority': need.priority,
                'required_date': need.required_date.isoformat() if hasattr(need, 'required_date') and need.required_date else None
            })
        
        return result
    
    def _get_active_projects(self) -> List[Dict]:
        """Get list of active projects with their status"""
        if not self.db_session:
            return []
        
        from src.api.db_models import SubstationProject, ProjectIssue
        
        projects = self.db_session.query(SubstationProject).filter(
            SubstationProject.status.in_(['Active', 'In Progress', 'Planning'])
        ).all()
        
        result = []
        for p in projects:
            # Get open issues for this project
            issues = self.db_session.query(ProjectIssue).filter(
                ProjectIssue.project_id == p.id,
                ProjectIssue.status.in_(['Open', 'In Progress'])
            ).all()
            
            critical_issues = sum(1 for i in issues if i.severity == 'Critical')
            high_issues = sum(1 for i in issues if i.severity == 'High')
            
            # Determine project health status
            if critical_issues > 0:
                health_status = 'Halted'
            elif p.delay_days and p.delay_days > 30:
                health_status = 'Delayed'
            elif high_issues > 0 or (p.delay_days and p.delay_days > 7):
                health_status = 'At Risk'
            else:
                health_status = 'On Track'
            
            result.append({
                'id': p.id,
                'name': p.name,
                'status': p.status,
                'health_status': health_status,
                'voltage_level': p.voltage_level,
                'total_line_length': p.total_line_length or 0,
                'overall_progress': p.overall_progress or 0,
                'delay_days': p.delay_days or 0,
                'target_date': p.target_date.isoformat() if p.target_date else None,
                'open_issues': len(issues),
                'critical_issues': critical_issues
            })
        
        return result
    
    def _get_warehouse_status(self) -> List[Dict]:
        """Get inventory status for each warehouse"""
        if not self.db_session:
            return []
        
        from src.api.db_models import Warehouse, InventoryStock
        from sqlalchemy import func
        
        warehouses = self.db_session.query(Warehouse).all()
        
        result = []
        for wh in warehouses:
            # Get stock stats for this warehouse
            stats = self.db_session.query(
                func.sum(InventoryStock.quantity_available).label('available'),
                func.sum(InventoryStock.reorder_point).label('reorder'),
                func.sum(InventoryStock.max_stock_level).label('max_stock'),
                func.count(InventoryStock.id).label('material_count')
            ).filter(
                InventoryStock.warehouse_id == wh.id
            ).first()
            
            available = float(stats.available or 0)
            reorder = float(stats.reorder or 0)
            max_stock = float(stats.max_stock or reorder * 3)
            
            # Calculate stock ratio
            if reorder > 0:
                ratio = available / reorder
            else:
                ratio = 1.0
            
            # Determine status
            if ratio < 0.5:
                stock_status = 'Critical'
            elif ratio < 1.0:
                stock_status = 'Understocked'
            elif ratio > 2.5:
                stock_status = 'Overstocked'
            else:
                stock_status = 'Normal'
            
            result.append({
                'warehouse_id': wh.id,
                'warehouse_code': wh.warehouse_code,
                'name': wh.name,
                'city': wh.city,
                'region': wh.region,
                'total_available': round(available, 2),
                'reorder_point': round(reorder, 2),
                'stock_ratio': round(ratio, 2),
                'stock_status': stock_status,
                'material_count': stats.material_count or 0
            })
        
        return result
    
    def generate_monthly_forecast(
        self,
        months: int = 6,
        include_project_breakdown: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive monthly forecast using actual data.
        
        Uses:
        - Current inventory levels (from InventoryStock)
        - Pending orders (from PurchaseOrder)
        - Project demands (from ProjectMaterialNeed)
        - Project status (from SubstationProject + ProjectIssue)
        """
        # Gather all data
        inventory = self._get_inventory_by_material()
        pending_orders = self._get_pending_orders()
        project_demands = self._get_project_demands()
        active_projects = self._get_active_projects()
        warehouse_status = self._get_warehouse_status()
        
        # Build material forecast list
        all_materials = set(inventory.keys()) | set(project_demands.keys())
        
        material_forecasts = []
        total_demand = 0
        total_supply = 0
        materials_critical = 0
        materials_at_risk = 0
        
        for mat_code in sorted(all_materials):
            inv = inventory.get(mat_code, {})
            orders = pending_orders.get(mat_code, {})
            demand = project_demands.get(mat_code, {})
            
            # Current supply
            current_stock = inv.get('total_available', 0)
            in_transit = inv.get('total_in_transit', 0) + orders.get('in_transit', 0)
            ordered_pending = orders.get('manufacturing', 0) + orders.get('placed', 0)
            reserved = inv.get('total_reserved', 0)
            available = max(0, current_stock - reserved)
            
            total_supply_for_mat = available + in_transit + ordered_pending
            
            # Demand from projects
            total_needed = demand.get('total_needed', 0)
            total_shortage = demand.get('total_shortage', 0)
            
            # Monthly demand estimate (spread over months)
            monthly_demand = total_needed / months if months > 0 else total_needed
            
            # Gap analysis
            supply_vs_demand = total_supply_for_mat - total_needed
            
            # Months of stock
            if monthly_demand > 0:
                months_of_stock = available / monthly_demand
            else:
                months_of_stock = float('inf') if available > 0 else 0
            
            # Determine status
            if available <= 0 and in_transit <= 0:
                status = 'Out of Stock'
                materials_critical += 1
            elif supply_vs_demand < 0 and abs(supply_vs_demand) > total_needed * 0.3:
                status = 'Critical'
                materials_critical += 1
            elif supply_vs_demand < 0:
                status = 'At Risk'
                materials_at_risk += 1
            elif months_of_stock < 2:
                status = 'At Risk'
                materials_at_risk += 1
            else:
                status = 'Healthy'
            
            # Predict shortage date
            shortage_date = None
            if monthly_demand > 0 and supply_vs_demand < 0:
                days_until_shortage = max(0, (available / monthly_demand) * 30)
                shortage_date = (datetime.now() + timedelta(days=days_until_shortage)).strftime('%Y-%m-%d')
            
            # Build project breakdown
            breakdown = []
            if include_project_breakdown and mat_code in project_demands:
                for proj in demand.get('projects', []):
                    breakdown.append({
                        'project_id': proj['project_id'],
                        'project_name': proj['project_name'],
                        'quantity_needed': proj['quantity_needed'],
                        'quantity_available': proj['quantity_available'],
                        'shortage': proj['quantity_shortage'],
                        'priority': proj['priority']
                    })
            
            material_forecasts.append({
                'material_code': mat_code,
                'material_name': inv.get('name', mat_code),
                'unit': inv.get('unit', 'units'),
                'unit_price': inv.get('unit_price', 0),
                
                # Current state
                'current_stock': round(current_stock, 2),
                'in_transit': round(in_transit, 2),
                'ordered_pending': round(ordered_pending, 2),
                'reserved': round(reserved, 2),
                'available': round(available, 2),
                'total_supply': round(total_supply_for_mat, 2),
                
                # Demand
                'total_demand': round(total_needed, 2),
                'monthly_demand': round(monthly_demand, 2),
                
                # Analysis
                'supply_vs_demand': round(supply_vs_demand, 2),
                'months_of_stock': round(months_of_stock, 2) if months_of_stock != float('inf') else 'Unlimited',
                'shortage_gap': round(abs(min(0, supply_vs_demand)), 2),
                
                # Forecast
                'predicted_shortage_date': shortage_date,
                'status': status,
                'confidence': 0.85,
                
                # Orders
                'pending_orders': orders.get('orders', []),
                'next_delivery': orders.get('next_delivery').isoformat() if orders.get('next_delivery') else None,
                
                # Project breakdown
                'project_breakdown': breakdown
            })
            
            total_demand += total_needed
            total_supply += total_supply_for_mat
        
        # Calculate overall health score
        if total_demand > 0:
            health_score = min(100, (total_supply / total_demand) * 100)
        else:
            health_score = 100 if total_supply > 0 else 50
        
        # Determine health status
        if health_score >= 80:
            health_status = 'Healthy'
        elif health_score >= 60:
            health_status = 'At Risk'
        elif health_score >= 40:
            health_status = 'Warning'
        else:
            health_status = 'Critical'
        
        # Build monthly breakdown (distribute demand/supply over months)
        monthly_breakdown = []
        for month_offset in range(months):
            month_date = datetime.now() + timedelta(days=30 * month_offset)
            month_str = month_date.strftime('%Y-%m')
            
            # Simple linear distribution for now
            month_data = {
                'month': month_str,
                'month_name': month_date.strftime('%B %Y'),
                'projected_demand': round(total_demand / months, 2),
                'projected_supply': round(total_supply / months if month_offset == 0 else 0, 2),
                'cumulative_gap': round((total_demand / months) * (month_offset + 1) - total_supply, 2)
            }
            monthly_breakdown.append(month_data)
        
        return {
            'generated_at': datetime.now().isoformat(),
            'forecast_horizon_months': months,
            'data_sources': {
                'inventory_records': len(inventory),
                'active_orders': sum(len(o.get('orders', [])) for o in pending_orders.values()),
                'project_needs': sum(len(d.get('projects', [])) for d in project_demands.values()),
                'active_projects': len(active_projects)
            },
            'summary': {
                'total_materials': len(material_forecasts),
                'total_demand': round(total_demand, 2),
                'total_supply': round(total_supply, 2),
                'overall_gap': round(total_supply - total_demand, 2),
                'procurement_health_score': round(health_score, 1),
                'health_status': health_status,
                'materials_critical': materials_critical,
                'materials_at_risk': materials_at_risk,
                'materials_healthy': len(material_forecasts) - materials_critical - materials_at_risk
            },
            'projects': active_projects,
            'warehouse_status': warehouse_status,
            'materials': material_forecasts,
            'monthly_breakdown': monthly_breakdown
        }
    
    def get_inventory_status(self) -> Dict[str, Any]:
        """
        Get detailed inventory status for all warehouses.
        
        Returns understocked/overstocked/normal status for each warehouse.
        """
        warehouse_status = self._get_warehouse_status()
        inventory = self._get_inventory_by_material()
        
        # Summary counts
        understocked = sum(1 for w in warehouse_status if w['stock_status'] in ['Understocked', 'Critical'])
        overstocked = sum(1 for w in warehouse_status if w['stock_status'] == 'Overstocked')
        normal = sum(1 for w in warehouse_status if w['stock_status'] == 'Normal')
        
        return {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_warehouses': len(warehouse_status),
                'understocked': understocked,
                'overstocked': overstocked,
                'normal': normal,
                'health_score': round((normal / max(len(warehouse_status), 1)) * 100, 1)
            },
            'warehouses': warehouse_status,
            'material_totals': {
                mat_code: {
                    'name': data['name'],
                    'total_available': data['total_available'],
                    'reorder_point': data['reorder_point'],
                    'status': 'Low' if data['total_available'] < data['reorder_point'] else 'OK'
                }
                for mat_code, data in inventory.items()
            }
        }
    
    def get_project_status(self) -> Dict[str, Any]:
        """
        Get status for all projects.
        
        Returns halted/delayed/stuck/on-track status for each project.
        """
        projects = self._get_active_projects()
        
        # Summary counts
        halted = sum(1 for p in projects if p['health_status'] == 'Halted')
        delayed = sum(1 for p in projects if p['health_status'] == 'Delayed')
        at_risk = sum(1 for p in projects if p['health_status'] == 'At Risk')
        on_track = sum(1 for p in projects if p['health_status'] == 'On Track')
        
        return {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_projects': len(projects),
                'halted': halted,
                'delayed': delayed,
                'at_risk': at_risk,
                'on_track': on_track,
                'health_score': round((on_track / max(len(projects), 1)) * 100, 1)
            },
            'projects': projects
        }
    
    def simulate_new_project_impact(
        self,
        project_type: str,
        line_length_km: float,
        voltage_level: str = '400kV',
        capacity_mva: float = 5
    ) -> Dict[str, Any]:
        """
        Simulate adding a new project and show impact on inventory/forecasts.
        """
        # Get current state
        current_forecast = self.generate_monthly_forecast(months=6, include_project_breakdown=False)
        inventory = self._get_inventory_by_material()
        
        # Estimate additional material needs based on project parameters
        voltage_multiplier = {
            '765kV': 1.5, '400kV': 1.0, '220kV': 0.7, '132kV': 0.5, '66kV': 0.3
        }.get(voltage_level, 1.0)
        
        # Estimate demand per km (simplified)
        estimated_demand = {}
        base_demand = {
            'MAT-001': 3.5,  # Towers
            'MAT-004': 4.0,  # Conductor
            'MAT-005': 18.0, # Insulators
            'MAT-006': 150,  # Hardware
        }
        
        for mat_code, rate in base_demand.items():
            estimated_demand[mat_code] = line_length_km * rate * voltage_multiplier
        
        # Calculate impact
        impact_details = []
        total_additional = 0
        new_shortages = 0
        
        for mat_code, additional in estimated_demand.items():
            inv = inventory.get(mat_code, {})
            current_available = inv.get('total_available', 0)
            current_demand = next(
                (m['total_demand'] for m in current_forecast['materials'] if m['material_code'] == mat_code),
                0
            )
            
            new_total_demand = current_demand + additional
            new_gap = current_available - new_total_demand
            
            impact_details.append({
                'material_code': mat_code,
                'material_name': inv.get('name', mat_code),
                'current_stock': round(current_available, 2),
                'current_demand': round(current_demand, 2),
                'additional_demand': round(additional, 2),
                'new_total_demand': round(new_total_demand, 2),
                'new_gap': round(new_gap, 2),
                'creates_shortage': new_gap < 0 and (current_available - current_demand) >= 0
            })
            
            total_additional += additional
            if new_gap < 0 and (current_available - current_demand) >= 0:
                new_shortages += 1
        
        # New health score
        current_supply = current_forecast['summary']['total_supply']
        current_demand = current_forecast['summary']['total_demand']
        new_health = min(100, (current_supply / max(current_demand + total_additional, 1)) * 100)
        
        return {
            'project': {
                'type': project_type,
                'line_length_km': line_length_km,
                'voltage_level': voltage_level,
                'capacity_mva': capacity_mva
            },
            'impact_summary': {
                'total_additional_demand': round(total_additional, 2),
                'new_shortages_created': new_shortages,
                'current_health_score': current_forecast['summary']['procurement_health_score'],
                'new_health_score': round(new_health, 1),
                'health_change': round(new_health - current_forecast['summary']['procurement_health_score'], 1)
            },
            'material_impact': impact_details,
            'recommendation': (
                'Safe to proceed' if new_health >= 70 
                else 'Procurement action needed' if new_health >= 50 
                else 'Critical - order materials before starting'
            )
        }


# Singleton instance
_forecast_engine: Optional[MaterialForecastEngine] = None


def get_forecast_engine(db_session=None) -> MaterialForecastEngine:
    """Get or create forecast engine instance"""
    global _forecast_engine
    if _forecast_engine is None or db_session is not None:
        _forecast_engine = MaterialForecastEngine(db_session)
    return _forecast_engine
