"""
Inventory Manager - Core Business Logic for Inventory Operations
Handles stock management, reservations, transactions, and alerts
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from src.api import db_models
from src.utils.logger import setup_logger

logger = setup_logger("InventoryManager")


class InventoryManager:
    """
    Robust inventory management system handling:
    - Stock tracking across warehouses
    - Stock in/out operations
    - Inter-warehouse transfers
    - Stock reservations for projects
    - Reorder point monitoring
    - Alert generation
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # =========================================================================
    # Stock Query Operations
    # =========================================================================
    
    def get_stock(self, warehouse_id: int, material_id: int) -> Optional[db_models.InventoryStock]:
        """Get current stock level for a material at a warehouse"""
        return self.db.query(db_models.InventoryStock).filter(
            db_models.InventoryStock.warehouse_id == warehouse_id,
            db_models.InventoryStock.material_id == material_id
        ).first()
    
    def get_or_create_stock(self, warehouse_id: int, material_id: int) -> db_models.InventoryStock:
        """Get existing stock record or create new one"""
        stock = self.get_stock(warehouse_id, material_id)
        if not stock:
            # Get material details for setting reorder points
            material = self.db.query(db_models.Material).filter(
                db_models.Material.id == material_id
            ).first()
            
            if not material:
                raise ValueError(f"Material {material_id} not found")
            
            # Calculate default reorder point (30 days of safety stock)
            reorder_point = material.min_order_quantity or 100
            
            stock = db_models.InventoryStock(
                warehouse_id=warehouse_id,
                material_id=material_id,
                quantity_available=0.0,
                quantity_reserved=0.0,
                quantity_in_transit=0.0,
                reorder_point=reorder_point,
                min_stock_level=reorder_point * 0.5,
                max_stock_level=reorder_point * 5
            )
            self.db.add(stock)
            self.db.commit()
            self.db.refresh(stock)
        
        return stock
    
    def get_total_available_stock(self, material_id: int) -> float:
        """Get total available quantity across all warehouses"""
        result = self.db.query(
            func.sum(db_models.InventoryStock.quantity_available)
        ).filter(
            db_models.InventoryStock.material_id == material_id
        ).scalar()
        
        return result or 0.0
    
    def get_warehouse_stock_list(self, warehouse_id: int, 
                                 include_zero: bool = False) -> List[db_models.InventoryStock]:
        """Get all stock items at a warehouse"""
        query = self.db.query(db_models.InventoryStock).filter(
            db_models.InventoryStock.warehouse_id == warehouse_id
        )
        
        if not include_zero:
            query = query.filter(db_models.InventoryStock.quantity_available > 0)
        
        return query.all()
    
    def get_material_stock_across_warehouses(self, material_id: int) -> List[db_models.InventoryStock]:
        """Get stock levels for a material across all warehouses"""
        return self.db.query(db_models.InventoryStock).filter(
            db_models.InventoryStock.material_id == material_id
        ).all()
    
    # =========================================================================
    # Stock In/Out Operations
    # =========================================================================
    
    def stock_in(self, warehouse_id: int, material_id: int, quantity: float,
                 unit_cost: float = 0.0, vendor_id: Optional[int] = None,
                 reference_type: str = "PO", reference_id: Optional[str] = None,
                 remarks: Optional[str] = None, performed_by: str = "system") -> db_models.InventoryStock:
        """
        Add stock to warehouse (purchase, return, etc.)
        
        Args:
            warehouse_id: Destination warehouse
            material_id: Material to add
            quantity: Quantity to add
            unit_cost: Cost per unit
            vendor_id: Vendor supplying the material
            reference_type: Type of transaction (PO, RETURN, etc.)
            reference_id: Reference document ID
            remarks: Additional notes
            performed_by: User performing the operation
            
        Returns:
            Updated stock record
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        # Get or create stock record
        stock = self.get_or_create_stock(warehouse_id, material_id)
        
        # Update stock level
        stock.quantity_available += quantity
        stock.last_restocked_date = datetime.utcnow()
        stock.updated_at = datetime.utcnow()
        
        # Create transaction record
        transaction = db_models.InventoryTransaction(
            transaction_type="IN",
            warehouse_id=warehouse_id,
            material_id=material_id,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=quantity * unit_cost,
            reference_type=reference_type,
            reference_id=reference_id,
            vendor_id=vendor_id,
            remarks=remarks,
            performed_by=performed_by,
            transaction_date=datetime.utcnow()
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(stock)
        
        logger.info(f"Stock IN: {quantity} units of material {material_id} to warehouse {warehouse_id}")
        
        # Check if this resolves any alerts
        self._check_and_resolve_alerts(warehouse_id, material_id)
        
        # Check for overstock
        self._check_overstock(stock)
        
        return stock
    
    def stock_out(self, warehouse_id: int, material_id: int, quantity: float,
                  project_id: Optional[int] = None, reference_type: str = "PROJECT",
                  reference_id: Optional[str] = None, remarks: Optional[str] = None,
                  performed_by: str = "system") -> db_models.InventoryStock:
        """
        Remove stock from warehouse (issue to project, sale, etc.)
        
        Args:
            warehouse_id: Source warehouse
            material_id: Material to remove
            quantity: Quantity to remove
            project_id: Project receiving the material
            reference_type: Type of transaction (PROJECT, SALE, etc.)
            reference_id: Reference document ID
            remarks: Additional notes
            performed_by: User performing the operation
            
        Returns:
            Updated stock record
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        # Get stock record
        stock = self.get_stock(warehouse_id, material_id)
        if not stock:
            raise ValueError(f"No stock found for material {material_id} at warehouse {warehouse_id}")
        
        # Check availability
        if stock.quantity_available < quantity:
            raise ValueError(
                f"Insufficient stock. Available: {stock.quantity_available}, Required: {quantity}"
            )
        
        # Get unit cost (use average cost from recent transactions)
        unit_cost = self._get_average_unit_cost(material_id, warehouse_id)
        
        # Update stock level
        stock.quantity_available -= quantity
        stock.last_issued_date = datetime.utcnow()
        stock.updated_at = datetime.utcnow()
        
        # Create transaction record
        transaction = db_models.InventoryTransaction(
            transaction_type="OUT",
            warehouse_id=warehouse_id,
            material_id=material_id,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=quantity * unit_cost,
            reference_type=reference_type,
            reference_id=reference_id,
            project_id=project_id,
            remarks=remarks,
            performed_by=performed_by,
            transaction_date=datetime.utcnow()
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(stock)
        
        logger.info(f"Stock OUT: {quantity} units of material {material_id} from warehouse {warehouse_id}")
        
        # Check if low stock alert needed
        self._check_low_stock(stock)
        
        return stock
    
    def adjust_stock(self, warehouse_id: int, material_id: int, 
                    adjustment: float, remarks: str, performed_by: str = "system") -> db_models.InventoryStock:
        """
        Adjust stock level (for corrections, damage, etc.)
        
        Args:
            warehouse_id: Warehouse to adjust
            material_id: Material to adjust
            adjustment: Quantity to adjust (positive or negative)
            remarks: Reason for adjustment (required)
            performed_by: User performing the operation
            
        Returns:
            Updated stock record
        """
        if not remarks:
            raise ValueError("Remarks are required for stock adjustments")
        
        stock = self.get_or_create_stock(warehouse_id, material_id)
        
        # Update stock level
        old_quantity = stock.quantity_available
        stock.quantity_available += adjustment
        
        if stock.quantity_available < 0:
            raise ValueError(f"Adjustment would result in negative stock: {stock.quantity_available}")
        
        stock.updated_at = datetime.utcnow()
        
        # Create transaction record
        transaction = db_models.InventoryTransaction(
            transaction_type="ADJUSTMENT",
            warehouse_id=warehouse_id,
            material_id=material_id,
            quantity=abs(adjustment),
            unit_cost=0.0,
            total_cost=0.0,
            reference_type="ADJUSTMENT",
            reference_id=None,
            remarks=f"Adjusted from {old_quantity} to {stock.quantity_available}. Reason: {remarks}",
            performed_by=performed_by,
            transaction_date=datetime.utcnow()
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(stock)
        
        logger.info(f"Stock ADJUSTMENT: {adjustment} units of material {material_id} at warehouse {warehouse_id}")
        
        # Check for alerts
        if adjustment < 0:
            self._check_low_stock(stock)
        else:
            self._check_and_resolve_alerts(warehouse_id, material_id)
        
        return stock
    
    # =========================================================================
    # Stock Transfer Operations
    # =========================================================================
    
    def transfer_stock(self, material_id: int, source_warehouse_id: int,
                      destination_warehouse_id: int, quantity: float,
                      remarks: Optional[str] = None, performed_by: str = "system") -> Tuple[db_models.InventoryStock, db_models.InventoryStock]:
        """
        Transfer stock between warehouses
        
        Args:
            material_id: Material to transfer
            source_warehouse_id: Source warehouse
            destination_warehouse_id: Destination warehouse
            quantity: Quantity to transfer
            remarks: Additional notes
            performed_by: User performing the operation
            
        Returns:
            Tuple of (source_stock, destination_stock)
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if source_warehouse_id == destination_warehouse_id:
            raise ValueError("Source and destination warehouses cannot be the same")
        
        # Get source stock
        source_stock = self.get_stock(source_warehouse_id, material_id)
        if not source_stock:
            raise ValueError(f"No stock found for material {material_id} at warehouse {source_warehouse_id}")
        
        # Check availability
        if source_stock.quantity_available < quantity:
            raise ValueError(
                f"Insufficient stock at source. Available: {source_stock.quantity_available}, Required: {quantity}"
            )
        
        # Get unit cost
        unit_cost = self._get_average_unit_cost(material_id, source_warehouse_id)
        
        # Update source stock
        source_stock.quantity_available -= quantity
        source_stock.last_issued_date = datetime.utcnow()
        source_stock.updated_at = datetime.utcnow()
        
        # Get or create destination stock
        dest_stock = self.get_or_create_stock(destination_warehouse_id, material_id)
        dest_stock.quantity_available += quantity
        dest_stock.last_restocked_date = datetime.utcnow()
        dest_stock.updated_at = datetime.utcnow()
        
        # Create transaction records (OUT from source, IN to destination)
        transfer_id = f"TRF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        transaction_out = db_models.InventoryTransaction(
            transaction_type="TRANSFER_OUT",
            warehouse_id=source_warehouse_id,
            material_id=material_id,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=quantity * unit_cost,
            reference_type="TRANSFER",
            reference_id=transfer_id,
            source_warehouse_id=destination_warehouse_id,
            remarks=remarks,
            performed_by=performed_by,
            transaction_date=datetime.utcnow()
        )
        
        transaction_in = db_models.InventoryTransaction(
            transaction_type="TRANSFER_IN",
            warehouse_id=destination_warehouse_id,
            material_id=material_id,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=quantity * unit_cost,
            reference_type="TRANSFER",
            reference_id=transfer_id,
            source_warehouse_id=source_warehouse_id,
            remarks=remarks,
            performed_by=performed_by,
            transaction_date=datetime.utcnow()
        )
        
        self.db.add(transaction_out)
        self.db.add(transaction_in)
        self.db.commit()
        self.db.refresh(source_stock)
        self.db.refresh(dest_stock)
        
        logger.info(f"Stock TRANSFER: {quantity} units of material {material_id} from warehouse {source_warehouse_id} to {destination_warehouse_id}")
        
        # Check for alerts at source
        self._check_low_stock(source_stock)
        
        # Check if this resolves alerts at destination
        self._check_and_resolve_alerts(destination_warehouse_id, material_id)
        
        return source_stock, dest_stock
    
    # =========================================================================
    # Stock Reservation Operations
    # =========================================================================
    
    def reserve_stock(self, warehouse_id: int, material_id: int, project_id: int,
                     quantity: float, required_by_date: Optional[datetime] = None,
                     priority: str = "Medium", remarks: Optional[str] = None) -> db_models.StockReservation:
        """
        Reserve stock for a project
        
        Args:
            warehouse_id: Warehouse to reserve from
            material_id: Material to reserve
            project_id: Project requiring the material
            quantity: Quantity to reserve
            required_by_date: When the material is needed
            priority: Priority level (Low, Medium, High, Critical)
            remarks: Additional notes
            
        Returns:
            Stock reservation record
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        # Get stock record
        stock = self.get_stock(warehouse_id, material_id)
        if not stock:
            raise ValueError(f"No stock found for material {material_id} at warehouse {warehouse_id}")
        
        # Check availability (available - already reserved)
        available_for_reservation = stock.quantity_available - stock.quantity_reserved
        if available_for_reservation < quantity:
            raise ValueError(
                f"Insufficient stock for reservation. Available: {available_for_reservation}, Required: {quantity}"
            )
        
        # Update stock reservation
        stock.quantity_reserved += quantity
        stock.updated_at = datetime.utcnow()
        
        # Create reservation record
        reservation = db_models.StockReservation(
            warehouse_id=warehouse_id,
            material_id=material_id,
            project_id=project_id,
            quantity_reserved=quantity,
            quantity_issued=0.0,
            reservation_date=datetime.utcnow(),
            required_by_date=required_by_date,
            status="Active",
            priority=priority,
            remarks=remarks
        )
        
        self.db.add(reservation)
        self.db.commit()
        self.db.refresh(reservation)
        
        logger.info(f"Stock RESERVED: {quantity} units of material {material_id} at warehouse {warehouse_id} for project {project_id}")
        
        # Check if this creates low stock situation
        self._check_low_stock(stock)
        
        return reservation
    
    def issue_reserved_stock(self, reservation_id: int, quantity_to_issue: float,
                           remarks: Optional[str] = None, performed_by: str = "system") -> db_models.StockReservation:
        """
        Issue stock against a reservation
        
        Args:
            reservation_id: Reservation to fulfill
            quantity_to_issue: Quantity to issue
            remarks: Additional notes
            performed_by: User performing the operation
            
        Returns:
            Updated reservation record
        """
        if quantity_to_issue <= 0:
            raise ValueError("Quantity must be positive")
        
        # Get reservation
        reservation = self.db.query(db_models.StockReservation).filter(
            db_models.StockReservation.id == reservation_id
        ).first()
        
        if not reservation:
            raise ValueError(f"Reservation {reservation_id} not found")
        
        if reservation.status not in ["Active", "Partially_Fulfilled"]:
            raise ValueError(f"Cannot issue stock for reservation in status: {reservation.status}")
        
        # Check quantity
        remaining_quantity = reservation.quantity_reserved - reservation.quantity_issued
        if quantity_to_issue > remaining_quantity:
            raise ValueError(
                f"Issue quantity exceeds remaining reservation. Remaining: {remaining_quantity}, Requested: {quantity_to_issue}"
            )
        
        # Get stock record
        stock = self.get_stock(reservation.warehouse_id, reservation.material_id)
        if not stock:
            raise ValueError(f"Stock record not found")
        
        # Check stock availability
        if stock.quantity_available < quantity_to_issue:
            raise ValueError(
                f"Insufficient stock. Available: {stock.quantity_available}, Required: {quantity_to_issue}"
            )
        
        # Get unit cost
        unit_cost = self._get_average_unit_cost(reservation.material_id, reservation.warehouse_id)
        
        # Update stock
        stock.quantity_available -= quantity_to_issue
        stock.quantity_reserved -= quantity_to_issue
        stock.last_issued_date = datetime.utcnow()
        stock.updated_at = datetime.utcnow()
        
        # Update reservation
        reservation.quantity_issued += quantity_to_issue
        if reservation.quantity_issued >= reservation.quantity_reserved:
            reservation.status = "Fulfilled"
        else:
            reservation.status = "Partially_Fulfilled"
        reservation.updated_at = datetime.utcnow()
        
        # Create transaction record
        transaction = db_models.InventoryTransaction(
            transaction_type="OUT",
            warehouse_id=reservation.warehouse_id,
            material_id=reservation.material_id,
            quantity=quantity_to_issue,
            unit_cost=unit_cost,
            total_cost=quantity_to_issue * unit_cost,
            reference_type="RESERVATION",
            reference_id=str(reservation_id),
            project_id=reservation.project_id,
            remarks=remarks or f"Issued against reservation {reservation_id}",
            performed_by=performed_by,
            transaction_date=datetime.utcnow()
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(reservation)
        
        logger.info(f"Stock ISSUED: {quantity_to_issue} units against reservation {reservation_id}")
        
        # Check for low stock
        self._check_low_stock(stock)
        
        return reservation
    
    def cancel_reservation(self, reservation_id: int, remarks: Optional[str] = None) -> db_models.StockReservation:
        """
        Cancel a stock reservation
        
        Args:
            reservation_id: Reservation to cancel
            remarks: Reason for cancellation
            
        Returns:
            Updated reservation record
        """
        # Get reservation
        reservation = self.db.query(db_models.StockReservation).filter(
            db_models.StockReservation.id == reservation_id
        ).first()
        
        if not reservation:
            raise ValueError(f"Reservation {reservation_id} not found")
        
        if reservation.status == "Fulfilled":
            raise ValueError("Cannot cancel a fulfilled reservation")
        
        # Get stock record
        stock = self.get_stock(reservation.warehouse_id, reservation.material_id)
        if stock:
            # Release reserved quantity
            unreleased_quantity = reservation.quantity_reserved - reservation.quantity_issued
            stock.quantity_reserved -= unreleased_quantity
            stock.updated_at = datetime.utcnow()
        
        # Update reservation status
        reservation.status = "Cancelled"
        reservation.remarks = (reservation.remarks or "") + f" | CANCELLED: {remarks}"
        reservation.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(reservation)
        
        logger.info(f"Reservation {reservation_id} CANCELLED")
        
        return reservation
    
    # =========================================================================
    # Alert Management
    # =========================================================================
    
    def _check_low_stock(self, stock: db_models.InventoryStock) -> None:
        """Check and create low stock alerts if needed"""
        if stock.quantity_available <= 0:
            # Out of stock
            self._create_alert(
                alert_type="OUT_OF_STOCK",
                severity="Critical",
                warehouse_id=stock.warehouse_id,
                material_id=stock.material_id,
                current_quantity=stock.quantity_available,
                threshold_quantity=stock.min_stock_level,
                message=f"Material out of stock at warehouse"
            )
        elif stock.quantity_available <= stock.min_stock_level:
            # Critical low stock
            self._create_alert(
                alert_type="LOW_STOCK",
                severity="High",
                warehouse_id=stock.warehouse_id,
                material_id=stock.material_id,
                current_quantity=stock.quantity_available,
                threshold_quantity=stock.min_stock_level,
                message=f"Stock critically low: {stock.quantity_available} units (minimum: {stock.min_stock_level})"
            )
        elif stock.reorder_point and stock.quantity_available <= stock.reorder_point:
            # Below reorder point
            self._create_alert(
                alert_type="LOW_STOCK",
                severity="Medium",
                warehouse_id=stock.warehouse_id,
                material_id=stock.material_id,
                current_quantity=stock.quantity_available,
                threshold_quantity=stock.reorder_point,
                message=f"Stock below reorder point: {stock.quantity_available} units (reorder at: {stock.reorder_point})"
            )
    
    def _check_overstock(self, stock: db_models.InventoryStock) -> None:
        """Check and create overstock alerts if needed"""
        if stock.max_stock_level and stock.quantity_available > stock.max_stock_level:
            self._create_alert(
                alert_type="OVERSTOCK",
                severity="Low",
                warehouse_id=stock.warehouse_id,
                material_id=stock.material_id,
                current_quantity=stock.quantity_available,
                threshold_quantity=stock.max_stock_level,
                message=f"Stock level exceeds maximum: {stock.quantity_available} units (max: {stock.max_stock_level})"
            )
    
    def _check_and_resolve_alerts(self, warehouse_id: int, material_id: int) -> None:
        """Check and auto-resolve alerts if conditions are met"""
        stock = self.get_stock(warehouse_id, material_id)
        if not stock:
            return
        
        # Get unresolved alerts
        alerts = self.db.query(db_models.StockAlert).filter(
            db_models.StockAlert.warehouse_id == warehouse_id,
            db_models.StockAlert.material_id == material_id,
            db_models.StockAlert.is_resolved == False
        ).all()
        
        for alert in alerts:
            should_resolve = False
            
            if alert.alert_type == "OUT_OF_STOCK" and stock.quantity_available > 0:
                should_resolve = True
            elif alert.alert_type == "LOW_STOCK" and stock.quantity_available > stock.reorder_point:
                should_resolve = True
            elif alert.alert_type == "OVERSTOCK" and stock.quantity_available <= stock.max_stock_level:
                should_resolve = True
            
            if should_resolve:
                alert.is_resolved = True
                alert.resolved_at = datetime.utcnow()
                alert.resolved_by = "system"
                logger.info(f"Alert {alert.id} auto-resolved")
    
    def _create_alert(self, alert_type: str, severity: str, warehouse_id: int,
                     material_id: int, current_quantity: float, threshold_quantity: float,
                     message: str) -> None:
        """Create a stock alert if it doesn't already exist"""
        # Check if similar unresolved alert already exists
        existing = self.db.query(db_models.StockAlert).filter(
            db_models.StockAlert.alert_type == alert_type,
            db_models.StockAlert.warehouse_id == warehouse_id,
            db_models.StockAlert.material_id == material_id,
            db_models.StockAlert.is_resolved == False
        ).first()
        
        if not existing:
            alert = db_models.StockAlert(
                alert_type=alert_type,
                severity=severity,
                warehouse_id=warehouse_id,
                material_id=material_id,
                current_quantity=current_quantity,
                threshold_quantity=threshold_quantity,
                message=message,
                is_resolved=False,
                alert_date=datetime.utcnow()
            )
            self.db.add(alert)
            self.db.commit()
            logger.warning(f"Alert created: {alert_type} - {message}")
    
    # =========================================================================
    # Analytics & Reporting
    # =========================================================================
    
    def get_inventory_summary(self) -> Dict:
        """Get overall inventory summary"""
        total_warehouses = self.db.query(db_models.Warehouse).filter(
            db_models.Warehouse.is_active == True
        ).count()
        
        total_materials = self.db.query(db_models.InventoryStock).filter(
            db_models.InventoryStock.quantity_available > 0
        ).count()
        
        # Calculate total stock value
        stock_value_query = self.db.query(
            func.sum(db_models.InventoryStock.quantity_available * db_models.Material.unit_price)
        ).join(
            db_models.Material,
            db_models.InventoryStock.material_id == db_models.Material.id
        ).scalar()
        
        total_stock_value = stock_value_query or 0.0
        
        # Count alerts
        low_stock = self.db.query(db_models.StockAlert).filter(
            db_models.StockAlert.alert_type == "LOW_STOCK",
            db_models.StockAlert.is_resolved == False
        ).count()
        
        out_of_stock = self.db.query(db_models.StockAlert).filter(
            db_models.StockAlert.alert_type == "OUT_OF_STOCK",
            db_models.StockAlert.is_resolved == False
        ).count()
        
        overstock = self.db.query(db_models.StockAlert).filter(
            db_models.StockAlert.alert_type == "OVERSTOCK",
            db_models.StockAlert.is_resolved == False
        ).count()
        
        active_reservations = self.db.query(db_models.StockReservation).filter(
            db_models.StockReservation.status.in_(["Active", "Partially_Fulfilled"])
        ).count()
        
        pending_alerts = self.db.query(db_models.StockAlert).filter(
            db_models.StockAlert.is_resolved == False
        ).count()
        
        return {
            "total_warehouses": total_warehouses,
            "total_materials_tracked": total_materials,
            "total_stock_value": round(total_stock_value, 2),
            "low_stock_items": low_stock,
            "out_of_stock_items": out_of_stock,
            "overstock_items": overstock,
            "active_reservations": active_reservations,
            "pending_alerts": pending_alerts
        }
    
    def _get_average_unit_cost(self, material_id: int, warehouse_id: int) -> float:
        """Calculate average unit cost from recent transactions"""
        # Get recent IN transactions
        recent_transactions = self.db.query(db_models.InventoryTransaction).filter(
            db_models.InventoryTransaction.material_id == material_id,
            db_models.InventoryTransaction.warehouse_id == warehouse_id,
            db_models.InventoryTransaction.transaction_type == "IN",
            db_models.InventoryTransaction.unit_cost > 0
        ).order_by(
            db_models.InventoryTransaction.transaction_date.desc()
        ).limit(5).all()
        
        if recent_transactions:
            avg_cost = sum(t.unit_cost for t in recent_transactions) / len(recent_transactions)
            return avg_cost
        
        # Fallback to material's unit price
        material = self.db.query(db_models.Material).filter(
            db_models.Material.id == material_id
        ).first()
        
        return material.unit_price if material and material.unit_price else 0.0
