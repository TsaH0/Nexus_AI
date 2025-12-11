"""
Transfer Manager - Material Transfer Optimization System
=========================================================
Handles material transfers between warehouses and substations with:
- Haversine distance calculations
- Transport cost estimation
- ETA calculations
- Optimal procurement algorithm
"""

from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.api.db_models import (
    Warehouse, Substation, Material, InventoryStock,
    MaterialTransfer
)


@dataclass
class WarehouseOption:
    """Represents a warehouse option for procurement."""
    warehouse_id: int
    warehouse_name: str
    latitude: float
    longitude: float
    available_quantity: float
    distance_km: float
    transport_cost: float
    unit_cost: float
    total_cost: float
    eta_hours: float
    optimization_score: float


@dataclass
class TransferPlan:
    """Represents a planned material transfer."""
    source_warehouse_id: int
    source_warehouse_name: str
    destination_substation_id: int
    destination_substation_name: str
    material_id: int
    material_name: str
    quantity: float
    distance_km: float
    transport_cost: float
    material_cost: float
    total_cost: float
    eta_hours: float
    optimization_score: float
    selected_reason: str


class TransferManager:
    """
    Manages material transfers between warehouses and substations.
    Uses Haversine formula for distance calculations and implements
    optimal procurement algorithm.
    """
    
    # Transport rates per km per unit (category-based)
    TRANSPORT_RATES = {
        'Transformer': 200.0,      # Heavy, requires special transport
        'Circuit Breaker': 120.0,  # Heavy equipment
        'Tower Structure': 100.0,  # Bulky materials
        'Control System': 80.0,
        'Current Transformer': 60.0,
        'Potential Transformer': 60.0,
        'Conductor': 30.0,         # Per km of cable
        'Insulator': 20.0,
        'Hardware': 15.0,
        'Foundation': 40.0,
        'Cable': 25.0,
        'Earthing': 20.0,
        'Arrester': 50.0,
        'Isolator': 45.0,
        'Protection': 55.0,
        'Battery System': 70.0,
        'General Equipment': 35.0
    }
    
    # Average transport speed in km/h
    TRANSPORT_SPEED = 45.0
    
    # Loading/unloading time in hours
    HANDLING_TIME = 4.0
    
    # Optimization weights
    DISTANCE_WEIGHT = 0.35
    COST_WEIGHT = 0.35
    AVAILABILITY_WEIGHT = 0.20
    RELIABILITY_WEIGHT = 0.10
    
    # Regions with restricted outbound transfers (strategic buffer zones)
    # These regions keep their stock for local/regional needs due to:
    # - Road blockages (weather, terrain)
    # - Accessibility issues
    # - Strategic importance for local grid stability
    RESTRICTED_SOURCE_REGIONS = {
        'Jammu & Kashmir',  # Road blockages due to snow/weather
        'Ladakh',           # Extreme terrain, limited connectivity
        'Arunachal Pradesh', # Remote northeastern region
        'Sikkim',           # Hilly terrain, limited road access
    }
    
    # Maximum distance for transfers from restricted regions (km)
    # They can only supply within their own region
    RESTRICTED_REGION_MAX_DISTANCE = 300.0
    
    def __init__(self, session: Session):
        self.session = session
    
    # =========================================================================
    # Distance Calculations
    # =========================================================================
    
    @staticmethod
    def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate the great-circle distance between two points on Earth.
        
        Args:
            lat1, lng1: Latitude and longitude of point 1 (degrees)
            lat2, lng2: Latitude and longitude of point 2 (degrees)
        
        Returns:
            Distance in kilometers
        """
        R = 6371.0  # Earth's radius in kilometers
        
        # Convert to radians
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lng = radians(lng2 - lng1)
        
        # Haversine formula
        a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c
    
    def get_warehouse_coordinates(self, warehouse_id: int) -> Optional[Tuple[float, float]]:
        """Get latitude and longitude of a warehouse."""
        warehouse = self.session.query(Warehouse).filter(
            Warehouse.id == warehouse_id
        ).first()
        
        if warehouse and warehouse.latitude and warehouse.longitude:
            return (warehouse.latitude, warehouse.longitude)
        return None
    
    def get_substation_coordinates(self, substation_id: int) -> Optional[Tuple[float, float]]:
        """Get latitude and longitude of a substation."""
        substation = self.session.query(Substation).filter(
            Substation.id == substation_id
        ).first()
        
        if substation:
            return (substation.latitude, substation.longitude)
        return None
    
    def calculate_distance_between(
        self, 
        warehouse_id: int, 
        substation_id: int
    ) -> Optional[float]:
        """Calculate distance between a warehouse and substation."""
        wh_coords = self.get_warehouse_coordinates(warehouse_id)
        sub_coords = self.get_substation_coordinates(substation_id)
        
        if wh_coords and sub_coords:
            return self.haversine_distance(
                wh_coords[0], wh_coords[1],
                sub_coords[0], sub_coords[1]
            )
        return None
    
    # =========================================================================
    # Cost Calculations
    # =========================================================================
    
    def calculate_transport_cost(
        self, 
        distance_km: float, 
        quantity: float, 
        material_category: str
    ) -> float:
        """
        Calculate transport cost based on distance, quantity, and material type.
        
        Formula: (distance * quantity * rate) / normalization_factor
        """
        rate = self.TRANSPORT_RATES.get(material_category, 35.0)
        
        # Normalize for bulk quantities
        if quantity > 1000:
            bulk_discount = 0.85  # 15% discount for bulk
        elif quantity > 500:
            bulk_discount = 0.92
        elif quantity > 100:
            bulk_discount = 0.97
        else:
            bulk_discount = 1.0
        
        # Base calculation
        base_cost = (distance_km * rate * bulk_discount)
        
        # Add per-unit cost for quantity
        quantity_factor = max(1, quantity / 100)  # Per 100 units
        
        return base_cost * quantity_factor
    
    def calculate_eta_hours(self, distance_km: float) -> float:
        """
        Calculate estimated time of arrival in hours.
        
        Includes:
        - Travel time at average speed
        - Loading/unloading time
        - Buffer for traffic/delays
        """
        travel_time = distance_km / self.TRANSPORT_SPEED
        buffer_time = travel_time * 0.15  # 15% buffer
        
        return travel_time + self.HANDLING_TIME + buffer_time
    
    def calculate_total_cost(
        self,
        transport_cost: float,
        unit_cost: float,
        quantity: float
    ) -> float:
        """Calculate total cost including transport and materials."""
        return transport_cost + (unit_cost * quantity)
    
    # =========================================================================
    # Optimization Scoring
    # =========================================================================
    
    def calculate_optimization_score(
        self,
        distance_km: float,
        max_distance: float,
        total_cost: float,
        max_cost: float,
        available_qty: float,
        required_qty: float,
        warehouse_reliability: float = 0.9
    ) -> float:
        """
        Calculate optimization score for a warehouse option.
        
        Higher score = better option
        
        Factors:
        - Distance (shorter is better)
        - Cost (lower is better)
        - Availability (more is better)
        - Reliability (historical performance)
        """
        # Normalize scores (0 to 1, where 1 is best)
        if max_distance > 0:
            distance_score = 1 - (distance_km / max_distance)
        else:
            distance_score = 1.0
        
        if max_cost > 0:
            cost_score = 1 - (total_cost / max_cost)
        else:
            cost_score = 1.0
        
        availability_score = min(1.0, available_qty / required_qty)
        
        # Weighted combination
        score = (
            self.DISTANCE_WEIGHT * distance_score +
            self.COST_WEIGHT * cost_score +
            self.AVAILABILITY_WEIGHT * availability_score +
            self.RELIABILITY_WEIGHT * warehouse_reliability
        )
        
        return round(score, 4)
    
    # =========================================================================
    # Optimal Procurement Algorithm
    # =========================================================================
    
    def find_optimal_warehouses(
        self,
        destination_substation_id: int,
        material_id: int,
        quantity_needed: float,
        max_options: int = 5
    ) -> List[WarehouseOption]:
        """
        Find optimal warehouses for procuring materials.
        
        Algorithm:
        1. Find all warehouses with the required material in stock
        2. Calculate distance, cost, and ETA for each
        3. Score each option using optimization algorithm
        4. Return top N options sorted by score
        """
        # Get destination substation
        substation = self.session.query(Substation).filter(
            Substation.id == destination_substation_id
        ).first()
        
        if not substation:
            return []
        
        dest_coords = (substation.latitude, substation.longitude)
        dest_warehouse_id = substation.primary_warehouse_id  # Exclude this from sources
        
        # Get material info
        material = self.session.query(Material).filter(
            Material.id == material_id
        ).first()
        
        if not material:
            return []
        
        # Find warehouses with stock (excluding destination's own warehouse)
        stock_query = self.session.query(
            InventoryStock, Warehouse
        ).join(
            Warehouse, InventoryStock.warehouse_id == Warehouse.id
        ).filter(
            and_(
                InventoryStock.material_id == material_id,
                InventoryStock.quantity_available > InventoryStock.quantity_reserved,
                Warehouse.is_active == True,
                Warehouse.id != dest_warehouse_id  # Exclude destination's own warehouse
            )
        ).all()
        
        if not stock_query:
            return []
        
        # Calculate metrics for each warehouse
        options = []
        all_distances = []
        all_costs = []
        
        for stock, warehouse in stock_query:
            available_qty = stock.quantity_available - stock.quantity_reserved
            
            if available_qty <= 0:
                continue
            
            # Calculate distance
            distance = self.haversine_distance(
                warehouse.latitude, warehouse.longitude,
                dest_coords[0], dest_coords[1]
            )
            
            # Check regional restrictions
            # Warehouses in restricted regions can only supply locally (within 300km)
            if warehouse.state in self.RESTRICTED_SOURCE_REGIONS:
                if distance > self.RESTRICTED_REGION_MAX_DISTANCE:
                    # Skip this warehouse - too far for restricted region
                    continue
            
            # Calculate costs
            transport_cost = self.calculate_transport_cost(
                distance, 
                min(available_qty, quantity_needed),
                material.category or 'General Equipment'
            )
            
            unit_cost = material.unit_price or 0
            total_cost = self.calculate_total_cost(
                transport_cost, unit_cost, min(available_qty, quantity_needed)
            )
            
            all_distances.append(distance)
            all_costs.append(total_cost)
            
            options.append({
                'stock': stock,
                'warehouse': warehouse,
                'available_qty': available_qty,
                'distance': distance,
                'transport_cost': transport_cost,
                'unit_cost': unit_cost,
                'total_cost': total_cost
            })
        
        if not options:
            return []
        
        # Calculate optimization scores
        max_distance = max(all_distances) if all_distances else 1
        max_cost = max(all_costs) if all_costs else 1
        
        warehouse_options = []
        for opt in options:
            eta = self.calculate_eta_hours(opt['distance'])
            score = self.calculate_optimization_score(
                opt['distance'], max_distance,
                opt['total_cost'], max_cost,
                opt['available_qty'], quantity_needed
            )
            
            warehouse_options.append(WarehouseOption(
                warehouse_id=opt['warehouse'].id,
                warehouse_name=opt['warehouse'].name,
                latitude=opt['warehouse'].latitude,
                longitude=opt['warehouse'].longitude,
                available_quantity=opt['available_qty'],
                distance_km=round(opt['distance'], 2),
                transport_cost=round(opt['transport_cost'], 2),
                unit_cost=round(opt['unit_cost'], 2),
                total_cost=round(opt['total_cost'], 2),
                eta_hours=round(eta, 2),
                optimization_score=score
            ))
        
        # Sort by optimization score (descending)
        warehouse_options.sort(key=lambda x: x.optimization_score, reverse=True)
        
        return warehouse_options[:max_options]
    
    def recommend_procurement(
        self,
        destination_substation_id: int,
        material_id: int,
        quantity_needed: float
    ) -> Tuple[Optional[WarehouseOption], Optional[List[Dict]]]:
        """
        Recommend optimal procurement strategy.
        
        Returns:
        - Single best option if one warehouse can fulfill the order
        - Split recommendation if order needs to be split across warehouses
        """
        options = self.find_optimal_warehouses(
            destination_substation_id, material_id, quantity_needed
        )
        
        if not options:
            return None, None
        
        # Check if best option can fulfill entire order
        best_option = options[0]
        if best_option.available_quantity >= quantity_needed:
            return best_option, None
        
        # Need to split order
        remaining_qty = quantity_needed
        split_plan = []
        
        for opt in options:
            if remaining_qty <= 0:
                break
            
            take_qty = min(opt.available_quantity, remaining_qty)
            split_plan.append({
                'warehouse_id': opt.warehouse_id,
                'warehouse_name': opt.warehouse_name,
                'quantity': take_qty,
                'distance_km': opt.distance_km,
                'cost': (opt.transport_cost / opt.available_quantity) * take_qty + (opt.unit_cost * take_qty)
            })
            remaining_qty -= take_qty
        
        if remaining_qty > 0:
            split_plan.append({
                'warning': f'Unable to fulfill {remaining_qty} units - insufficient stock across all warehouses'
            })
        
        return None, split_plan
    
    # =========================================================================
    # Transfer Operations
    # =========================================================================
    
    def create_transfer(
        self,
        source_warehouse_id: int,
        destination_substation_id: int,
        material_id: int,
        quantity: float,
        project_id: Optional[int] = None
    ) -> MaterialTransfer:
        """
        Create a new material transfer with all calculated fields.
        """
        # Get coordinates
        wh_coords = self.get_warehouse_coordinates(source_warehouse_id)
        sub_coords = self.get_substation_coordinates(destination_substation_id)
        
        if not wh_coords or not sub_coords:
            raise ValueError("Could not get coordinates for warehouse or substation")
        
        # Get material
        material = self.session.query(Material).filter(
            Material.id == material_id
        ).first()
        
        if not material:
            raise ValueError(f"Material {material_id} not found")
        
        # Get stock info
        stock = self.session.query(InventoryStock).filter(
            and_(
                InventoryStock.warehouse_id == source_warehouse_id,
                InventoryStock.material_id == material_id
            )
        ).first()
        
        if not stock or (stock.quantity_available - stock.quantity_reserved) < quantity:
            raise ValueError("Insufficient stock for transfer")
        
        # Calculate all metrics
        distance = self.haversine_distance(
            wh_coords[0], wh_coords[1],
            sub_coords[0], sub_coords[1]
        )
        
        transport_cost = self.calculate_transport_cost(
            distance, quantity, material.category or 'General Equipment'
        )
        
        unit_cost = material.unit_price or 0
        material_cost = unit_cost * quantity
        total_cost = transport_cost + material_cost
        
        eta_hours = self.calculate_eta_hours(distance)
        
        # Get optimization score
        options = self.find_optimal_warehouses(
            destination_substation_id, material_id, quantity, max_options=10
        )
        best_score = max((o.optimization_score for o in options), default=0)
        current_option = next(
            (o for o in options if o.warehouse_id == source_warehouse_id), 
            None
        )
        
        optimization_score = current_option.optimization_score if current_option else 0.5
        is_optimal = current_option and current_option.optimization_score == best_score
        
        # Generate transfer code
        transfer_code = f"TRF-{datetime.utcnow().strftime('%Y%m%d')}-{source_warehouse_id}-{destination_substation_id}"
        
        # Create transfer record
        transfer = MaterialTransfer(
            transfer_code=transfer_code,
            source_warehouse_id=source_warehouse_id,
            destination_substation_id=destination_substation_id,
            project_id=project_id,
            material_id=material_id,
            quantity=quantity,
            unit_cost=unit_cost,
            total_material_cost=material_cost,
            distance_km=round(distance, 2),
            transport_cost=round(transport_cost, 2),
            estimated_eta_hours=round(eta_hours, 2),
            total_cost=round(total_cost, 2),
            status="Planned",
            dispatch_date=datetime.utcnow() + timedelta(days=1),
            expected_delivery=datetime.utcnow() + timedelta(days=1, hours=eta_hours),
            optimization_score=optimization_score,
            selected_reason="Optimal warehouse" if is_optimal else "User selected"
        )
        
        self.session.add(transfer)
        
        # Reserve the stock
        stock.quantity_reserved += quantity
        
        self.session.commit()
        
        return transfer
    
    def dispatch_transfer(self, transfer_id: int) -> MaterialTransfer:
        """Mark a transfer as dispatched."""
        transfer = self.session.query(MaterialTransfer).filter(
            MaterialTransfer.id == transfer_id
        ).first()
        
        if not transfer:
            raise ValueError(f"Transfer {transfer_id} not found")
        
        if transfer.status != "Planned":
            raise ValueError(f"Transfer is already {transfer.status}")
        
        transfer.status = "In Transit"
        transfer.dispatch_date = datetime.utcnow()
        transfer.expected_delivery = datetime.utcnow() + timedelta(
            hours=transfer.estimated_eta_hours or 24
        )
        
        # Reduce stock
        stock = self.session.query(InventoryStock).filter(
            and_(
                InventoryStock.warehouse_id == transfer.source_warehouse_id,
                InventoryStock.material_id == transfer.material_id
            )
        ).first()
        
        if stock:
            stock.quantity_available -= transfer.quantity
            stock.quantity_reserved -= transfer.quantity
        
        self.session.commit()
        return transfer
    
    def complete_transfer(self, transfer_id: int) -> MaterialTransfer:
        """Mark a transfer as completed/delivered."""
        transfer = self.session.query(MaterialTransfer).filter(
            MaterialTransfer.id == transfer_id
        ).first()
        
        if not transfer:
            raise ValueError(f"Transfer {transfer_id} not found")
        
        if transfer.status != "In Transit":
            raise ValueError(f"Transfer must be In Transit to complete (current: {transfer.status})")
        
        transfer.status = "Delivered"
        transfer.actual_delivery = datetime.utcnow()
        
        self.session.commit()
        return transfer
    
    def cancel_transfer(self, transfer_id: int, reason: str = None) -> MaterialTransfer:
        """Cancel a planned transfer."""
        transfer = self.session.query(MaterialTransfer).filter(
            MaterialTransfer.id == transfer_id
        ).first()
        
        if not transfer:
            raise ValueError(f"Transfer {transfer_id} not found")
        
        if transfer.status not in ["Planned", "In Transit"]:
            raise ValueError(f"Cannot cancel transfer with status: {transfer.status}")
        
        # Release reserved stock if still planned
        if transfer.status == "Planned":
            stock = self.session.query(InventoryStock).filter(
                and_(
                    InventoryStock.warehouse_id == transfer.source_warehouse_id,
                    InventoryStock.material_id == transfer.material_id
                )
            ).first()
            
            if stock:
                stock.quantity_reserved -= transfer.quantity
        
        transfer.status = "Cancelled"
        if reason:
            transfer.selected_reason = f"Cancelled: {reason}"
        
        self.session.commit()
        return transfer
    
    # =========================================================================
    # Analytics
    # =========================================================================
    
    def get_transfer_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get transfer statistics for a period."""
        query = self.session.query(MaterialTransfer)
        
        if start_date:
            query = query.filter(MaterialTransfer.created_at >= start_date)
        if end_date:
            query = query.filter(MaterialTransfer.created_at <= end_date)
        
        transfers = query.all()
        
        if not transfers:
            return {
                'total_transfers': 0,
                'total_distance_km': 0,
                'total_transport_cost': 0,
                'total_material_cost': 0,
                'average_eta_hours': 0,
                'by_status': {}
            }
        
        by_status = {}
        for t in transfers:
            by_status[t.status] = by_status.get(t.status, 0) + 1
        
        return {
            'total_transfers': len(transfers),
            'total_distance_km': sum(t.distance_km or 0 for t in transfers),
            'total_transport_cost': sum(t.transport_cost or 0 for t in transfers),
            'total_material_cost': sum(t.total_material_cost or 0 for t in transfers),
            'average_eta_hours': sum(t.estimated_eta_hours or 0 for t in transfers) / len(transfers),
            'average_optimization_score': sum(t.optimization_score or 0 for t in transfers) / len(transfers),
            'by_status': by_status
        }
    
    def get_warehouse_distance_matrix(self) -> List[Dict]:
        """Get distance matrix between all warehouses."""
        warehouses = self.session.query(Warehouse).filter(
            Warehouse.is_active == True
        ).all()
        
        matrix = []
        for wh1 in warehouses:
            row = {
                'warehouse_id': wh1.id,
                'warehouse_name': wh1.name,
                'distances': []
            }
            for wh2 in warehouses:
                if wh1.id != wh2.id:
                    distance = self.haversine_distance(
                        wh1.latitude, wh1.longitude,
                        wh2.latitude, wh2.longitude
                    )
                    row['distances'].append({
                        'to_warehouse_id': wh2.id,
                        'to_warehouse_name': wh2.name,
                        'distance_km': round(distance, 2)
                    })
            matrix.append(row)
        
        return matrix
