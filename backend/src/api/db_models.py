"""
SQLAlchemy Database Models for NEXUS API
These are the database table definitions, separate from the dataclass models used in the core logic.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Location(Base):
    """Geographic locations for projects and warehouses"""
    __tablename__ = "locations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    state = Column(String, nullable=False)
    region = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    projects = relationship("Project", back_populates="location")


class Project(Base):
    """Power grid infrastructure projects"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text)
    location_id = Column(Integer, ForeignKey("locations.id"))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    status = Column(String, default="Planning")
    budget = Column(Float)
    project_type = Column(String)  # Transmission, Substation
    voltage_level = Column(String)
    priority = Column(String, default="Medium")
    row_status = Column(String, default="Clear")  # Right-of-Way status
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    location = relationship("Location", back_populates="projects")
    material_requirements = relationship("MaterialRequirement", back_populates="project")


class Material(Base):
    """Materials and equipment used in projects"""
    __tablename__ = "materials"
    
    id = Column(Integer, primary_key=True, index=True)
    material_code = Column(String, unique=True, index=True)  # e.g., "MAT-001"
    name = Column(String, unique=True, index=True, nullable=False)
    category = Column(String)
    unit = Column(String)
    unit_price = Column(Float)
    lead_time_days = Column(Integer)
    min_order_quantity = Column(Integer)
    safety_stock_days = Column(Integer, default=30)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    requirements = relationship("MaterialRequirement", back_populates="material")


class MaterialRequirement(Base):
    """Material requirements for specific projects"""
    __tablename__ = "material_requirements"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    material_id = Column(Integer, ForeignKey("materials.id"))
    quantity_required = Column(Float)
    priority = Column(String, default="Medium")
    required_by = Column(DateTime)
    status = Column(String, default="Pending")  # Pending, Ordered, Delivered
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="material_requirements")
    material = relationship("Material", back_populates="requirements")


class TowerType(Base):
    """Types of transmission towers"""
    __tablename__ = "tower_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    voltage_rating = Column(String)  # e.g., "765kV", "400kV"
    height_meters = Column(Float)
    base_width_meters = Column(Float)
    weight_tons = Column(Float)
    circuit_type = Column(String)  # Single, Double, Multi
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class SubstationType(Base):
    """Types of substations"""
    __tablename__ = "substation_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    voltage_level = Column(String)  # e.g., "765/400kV", "400/220kV"
    capacity_mva = Column(Float)
    transformer_count = Column(Integer)
    bay_count = Column(Integer)
    type_category = Column(String)  # AIS, GIS, Hybrid
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Budget(Base):
    """Budget allocations and tracking"""
    __tablename__ = "budgets"
    
    id = Column(Integer, primary_key=True, index=True)
    fiscal_year = Column(String, nullable=False)
    category = Column(String)  # CapEx, OpEx
    allocated_amount = Column(Float)
    spent_amount = Column(Float, default=0.0)
    remaining_amount = Column(Float)
    department = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Tax(Base):
    """Tax rates and rules"""
    __tablename__ = "taxes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    rate_percentage = Column(Float)
    applicable_on = Column(String)  # Materials, Transport, Services
    state = Column(String)  # For state-specific taxes
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Forecast(Base):
    """Demand forecasts generated by Prophet"""
    __tablename__ = "forecasts"
    
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"))
    location_id = Column(Integer, ForeignKey("locations.id"))
    forecast_date = Column(DateTime)
    predicted_demand = Column(Float)
    confidence_level = Column(Float)
    lower_bound = Column(Float)
    upper_bound = Column(Float)
    method = Column(String, default="Prophet")
    created_at = Column(DateTime, default=datetime.utcnow)


class Vendor(Base):
    """Supplier/Vendor information"""
    __tablename__ = "vendors"
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_code = Column(String, unique=True, index=True)  # e.g., "VEN-001"
    name = Column(String, unique=True, index=True, nullable=False)
    state = Column(String)
    city = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    reliability_score = Column(Float, default=0.9)
    avg_lead_time_days = Column(Integer, default=14)
    contact_email = Column(String)
    contact_phone = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Warehouse(Base):
    """Warehouse/storage locations"""
    __tablename__ = "warehouses"
    
    id = Column(Integer, primary_key=True, index=True)
    warehouse_code = Column(String, unique=True, index=True)  # e.g., "WH-001"
    name = Column(String, nullable=False)
    state = Column(String)
    city = Column(String)
    region = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    capacity_tons = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PurchaseOrder(Base):
    """Purchase orders for materials"""
    __tablename__ = "purchase_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_code = Column(String, unique=True, index=True)  # e.g., "PO-20251208-0001"
    material_id = Column(Integer, ForeignKey("materials.id"))
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    quantity = Column(Integer)
    unit_price = Column(Float)
    total_cost = Column(Float)
    tax_amount = Column(Float, default=0.0)
    transport_cost = Column(Float, default=0.0)
    landed_cost = Column(Float)
    order_date = Column(DateTime)
    expected_delivery_date = Column(DateTime)
    actual_delivery_date = Column(DateTime)
    status = Column(String, default="Placed")  # Placed, In_Transit, Delivered, Delayed
    reasoning = Column(Text)  # XAI explanation
    created_at = Column(DateTime, default=datetime.utcnow)


class TransferOrder(Base):
    """Internal transfers between warehouses"""
    __tablename__ = "transfer_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_code = Column(String, unique=True, index=True)  # e.g., "TO-20251208-0001"
    material_id = Column(Integer, ForeignKey("materials.id"))
    source_warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    destination_warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    quantity = Column(Integer)
    transport_cost = Column(Float)
    order_date = Column(DateTime)
    expected_delivery_date = Column(DateTime)
    actual_delivery_date = Column(DateTime)
    status = Column(String, default="Pending")
    reasoning = Column(Text)  # XAI explanation
    created_at = Column(DateTime, default=datetime.utcnow)


class InventoryStock(Base):
    """Real-time inventory stock levels at warehouses"""
    __tablename__ = "inventory_stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    quantity_available = Column(Float, default=0.0)  # Available for use
    quantity_reserved = Column(Float, default=0.0)  # Reserved for projects
    quantity_in_transit = Column(Float, default=0.0)  # In transit to this warehouse
    reorder_point = Column(Float)  # When to reorder
    max_stock_level = Column(Float)  # Maximum stock level
    min_stock_level = Column(Float, default=0.0)  # Safety stock level
    last_restocked_date = Column(DateTime)
    last_issued_date = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    warehouse = relationship("Warehouse")
    material = relationship("Material")


class InventoryTransaction(Base):
    """Tracks all inventory movements (in/out/transfer/adjustment)"""
    __tablename__ = "inventory_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(String, nullable=False)  # IN, OUT, TRANSFER_OUT, TRANSFER_IN, ADJUSTMENT
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    
    # Reference documents
    reference_type = Column(String)  # PO, TO, PROJECT, ADJUSTMENT
    reference_id = Column(String)  # PO ID, Project ID, etc.
    
    # Additional details
    project_id = Column(Integer, ForeignKey("projects.id"))
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    source_warehouse_id = Column(Integer, ForeignKey("warehouses.id"))  # For transfers
    
    # Metadata
    remarks = Column(Text)
    performed_by = Column(String)  # User ID or system
    transaction_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])
    material = relationship("Material")
    project = relationship("Project")
    vendor = relationship("Vendor")


class StockReservation(Base):
    """Material reservations for projects"""
    __tablename__ = "stock_reservations"
    
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    quantity_reserved = Column(Float, nullable=False)
    quantity_issued = Column(Float, default=0.0)
    reservation_date = Column(DateTime, default=datetime.utcnow)
    required_by_date = Column(DateTime)
    status = Column(String, default="Active")  # Active, Partially_Fulfilled, Fulfilled, Cancelled
    priority = Column(String, default="Medium")  # Low, Medium, High, Critical
    remarks = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    warehouse = relationship("Warehouse")
    material = relationship("Material")
    project = relationship("Project")


class StockAlert(Base):
    """Inventory alerts for low stock, expiry, etc."""
    __tablename__ = "stock_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String, nullable=False)  # LOW_STOCK, OUT_OF_STOCK, EXPIRING_SOON, OVERSTOCK
    severity = Column(String, default="Medium")  # Low, Medium, High, Critical
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    material_id = Column(Integer, ForeignKey("materials.id"))
    current_quantity = Column(Float)
    threshold_quantity = Column(Float)
    message = Column(Text)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolved_by = Column(String)
    alert_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    warehouse = relationship("Warehouse")
    material = relationship("Material")


# ==============================================================================
# SUBSTATION & PROJECT TRACKING MODELS
# ==============================================================================

class Substation(Base):
    """Power substations that are served by inventory warehouses"""
    __tablename__ = "substations"
    
    id = Column(Integer, primary_key=True, index=True)
    substation_code = Column(String, unique=True, index=True)  # e.g., "SUB-RAJ-001"
    name = Column(String, nullable=False)
    substation_type = Column(String)  # 33/11kV, 220/132kV, 400/220kV, etc.
    capacity = Column(String)  # e.g., "400kV", "220kV", "132kV"
    state = Column(String, nullable=False)
    city = Column(String)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String, default="Active")  # Active, Maintenance, Planned, Decommissioned
    
    # Associated warehouse for inventory
    primary_warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    
    # Stock status (calculated based on inventory)
    stock_status = Column(String, default="Normal")  # Normal, Understocked, Overstocked
    stock_level_percentage = Column(Float, default=100.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    primary_warehouse = relationship("Warehouse", foreign_keys=[primary_warehouse_id])
    projects = relationship("SubstationProject", back_populates="substation")
    critical_materials = relationship("SubstationCriticalMaterial", back_populates="substation")


class SubstationCriticalMaterial(Base):
    """Materials that are critical/low at a substation"""
    __tablename__ = "substation_critical_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    substation_id = Column(Integer, ForeignKey("substations.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    material_name = Column(String)  # Denormalized for quick access
    current_quantity = Column(Float)
    required_quantity = Column(Float)
    shortage_percentage = Column(Float)
    priority = Column(String, default="Medium")  # Low, Medium, High, Critical
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    substation = relationship("Substation", back_populates="critical_materials")
    material = relationship("Material")


class SubstationProject(Base):
    """Active projects at/near substations"""
    __tablename__ = "substation_projects"
    
    id = Column(Integer, primary_key=True, index=True)
    project_code = Column(String, unique=True, index=True)  # e.g., "PROJ-RAJ-2024-001"
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Project details
    substation_id = Column(Integer, ForeignKey("substations.id"))
    developer = Column(String)
    developer_type = Column(String)  # Private Developer, CPSU, State Transco
    category = Column(String)  # ISTS, Intra-state
    
    # Technical specs
    project_type = Column(String)  # Transmission Line, Substation, HVDC
    circuit_type = Column(String)  # S/C, D/C, M/C
    voltage_level = Column(Integer)  # in kV
    total_line_length = Column(Float)  # in ckm
    total_tower_locations = Column(Integer)
    
    # Timeline
    target_date = Column(DateTime)
    anticipated_cod = Column(DateTime)  # Commercial Operation Date
    delay_days = Column(Integer, default=0)
    
    # Progress tracking
    foundation_completed = Column(Integer, default=0)
    foundation_total = Column(Integer)
    tower_erected = Column(Integer, default=0)
    tower_total = Column(Integer)
    stringing_completed_ckm = Column(Float, default=0.0)
    stringing_total_ckm = Column(Float)
    overall_progress = Column(Float, default=0.0)  # percentage
    
    # Status
    status = Column(String, default="Active")  # Active, On Hold, Completed, Delayed
    delay_reason = Column(Text)
    
    # Financial
    budget_sanctioned = Column(Float)
    budget_spent = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    substation = relationship("Substation", back_populates="projects")
    material_needs = relationship("ProjectMaterialNeed", back_populates="project")


class ProjectMaterialNeed(Base):
    """Materials needed for a project (understocked items)"""
    __tablename__ = "project_material_needs"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("substation_projects.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    material_name = Column(String)  # Denormalized for quick access
    quantity_needed = Column(Float)
    quantity_available = Column(Float, default=0.0)
    quantity_shortage = Column(Float)
    unit = Column(String)
    unit_price = Column(Float)
    total_value = Column(Float)
    priority = Column(String, default="Medium")
    status = Column(String, default="Pending")  # Pending, Ordered, Fulfilled
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("SubstationProject", back_populates="material_needs")
    material = relationship("Material")


class MaterialTransfer(Base):
    """Track material transfers between warehouses for projects"""
    __tablename__ = "material_transfers"
    
    id = Column(Integer, primary_key=True, index=True)
    transfer_code = Column(String, unique=True, index=True)  # e.g., "TRF-20251209-0001"
    
    # Source and destination
    source_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    destination_substation_id = Column(Integer, ForeignKey("substations.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("substation_projects.id"))
    
    # Material details
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_cost = Column(Float)
    total_material_cost = Column(Float)
    
    # Distance and transport
    distance_km = Column(Float)
    transport_cost = Column(Float)
    estimated_eta_hours = Column(Float)
    
    # Total cost
    total_cost = Column(Float)  # material + transport
    
    # Status tracking
    status = Column(String, default="Planned")  # Planned, In Transit, Delivered, Cancelled
    dispatch_date = Column(DateTime)
    expected_delivery = Column(DateTime)
    actual_delivery = Column(DateTime)
    
    # Algorithm tracking
    optimization_score = Column(Float)  # Score from procurement algorithm
    selected_reason = Column(Text)  # Why this warehouse was selected
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    source_warehouse = relationship("Warehouse", foreign_keys=[source_warehouse_id])
    destination_substation = relationship("Substation")
    project = relationship("SubstationProject")
    material = relationship("Material")


class ProjectIssue(Base):
    """
    Track issues affecting projects at substations.
    Unlike inventory stock levels, these are operational/external issues.
    """
    __tablename__ = "project_issues"
    
    id = Column(Integer, primary_key=True, index=True)
    issue_code = Column(String, unique=True, index=True)  # e.g., "ISS-2024-001"
    
    # Linked entities
    project_id = Column(Integer, ForeignKey("substation_projects.id"), nullable=False)
    substation_id = Column(Integer, ForeignKey("substations.id"))
    
    # Issue details
    issue_type = Column(String, nullable=False)  
    # Types: MATERIAL_SHORTAGE, ROW_CLEARANCE, LAND_ACQUISITION, FOREST_CLEARANCE,
    #        WEATHER_DELAY, VENDOR_DELAY, REGULATORY_APPROVAL, MANPOWER_SHORTAGE,
    #        EQUIPMENT_FAILURE, OTHER
    
    severity = Column(String, default="Medium")  # Low, Medium, High, Critical
    status = Column(String, default="Open")  # Open, In Progress, Resolved, Escalated
    
    title = Column(String, nullable=False)
    description = Column(Text)
    
    # Impact assessment
    impact_on_timeline = Column(Integer, default=0)  # Days of delay
    impact_on_budget = Column(Float, default=0.0)  # Additional cost
    affected_activities = Column(Text)  # JSON list of activities affected
    
    # Resolution
    resolution_notes = Column(Text)
    resolved_at = Column(DateTime)
    resolved_by = Column(String)
    
    # Escalation
    escalated_to = Column(String)  # Department/person escalated to
    escalation_date = Column(DateTime)
    
    # Audit
    reported_by = Column(String)
    reported_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("SubstationProject")
    substation = relationship("Substation")


class OrderTracking(Base):
    """
    Detailed tracking for purchase orders - shows order lifecycle.
    Complements PurchaseOrder with status history and ETA updates.
    """
    __tablename__ = "order_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    
    # Status progression
    status = Column(String, nullable=False)
    # Statuses: Placed, Confirmed, Manufacturing, Quality_Check, Ready_for_Dispatch,
    #          In_Transit, Customs (if import), At_Warehouse, Delivered
    
    status_timestamp = Column(DateTime, default=datetime.utcnow)
    location = Column(String)  # Current location if in transit
    location_lat = Column(Float)
    location_lng = Column(Float)
    
    # Updates
    notes = Column(Text)
    updated_by = Column(String)  # Vendor, Transporter, System
    
    # ETA
    revised_eta = Column(DateTime)
    delay_reason = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemStats(Base):
    """
    Daily snapshot of system health metrics.
    Used for dashboard and trend analysis.
    """
    __tablename__ = "system_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Project metrics
    total_projects = Column(Integer, default=0)
    active_projects = Column(Integer, default=0)
    delayed_projects = Column(Integer, default=0)
    projects_on_track = Column(Integer, default=0)
    
    # Inventory metrics
    total_warehouses = Column(Integer, default=0)
    understocked_warehouses = Column(Integer, default=0)
    overstocked_warehouses = Column(Integer, default=0)
    total_inventory_value = Column(Float, default=0.0)
    
    # Procurement metrics
    procurement_health_score = Column(Float, default=100.0)  # 0-100
    total_orders_pending = Column(Integer, default=0)
    total_orders_in_transit = Column(Integer, default=0)
    orders_delayed = Column(Integer, default=0)
    
    # Material metrics
    materials_at_risk = Column(Integer, default=0)
    materials_critical = Column(Integer, default=0)
    total_shortage_value = Column(Float, default=0.0)
    
    # Forecast gap
    forecast_demand = Column(Float, default=0.0)
    ordered_quantity = Column(Float, default=0.0)
    shortage_gap = Column(Float, default=0.0)
    
    # Issues
    open_issues = Column(Integer, default=0)
    critical_issues = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
