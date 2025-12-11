"""
Pydantic Schemas for NEXUS API
Request/Response models for API validation and serialization
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================================================
# Location Schemas
# ============================================================================

class LocationBase(BaseModel):
    name: str
    state: str
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Location(LocationBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Project Schemas
# ============================================================================

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    location_id: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str = "Planning"
    budget: Optional[float] = None
    project_type: Optional[str] = None
    voltage_level: Optional[str] = None
    priority: str = "Medium"
    row_status: str = "Clear"


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None
    budget: Optional[float] = None
    project_type: Optional[str] = None
    voltage_level: Optional[str] = None
    priority: Optional[str] = None
    row_status: Optional[str] = None


class Project(ProjectBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Material Schemas
# ============================================================================

class MaterialBase(BaseModel):
    material_code: Optional[str] = None
    name: str
    category: Optional[str] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    lead_time_days: Optional[int] = None
    min_order_quantity: Optional[int] = None
    safety_stock_days: int = 30
    description: Optional[str] = None


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    material_code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    lead_time_days: Optional[int] = None
    min_order_quantity: Optional[int] = None
    safety_stock_days: Optional[int] = None
    description: Optional[str] = None


class Material(MaterialBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Material Requirement Schemas
# ============================================================================

class MaterialRequirementBase(BaseModel):
    project_id: int
    material_id: int
    quantity_required: float
    priority: str = "Medium"
    required_by: Optional[datetime] = None
    status: str = "Pending"


class MaterialRequirementCreate(MaterialRequirementBase):
    pass


class MaterialRequirementUpdate(BaseModel):
    project_id: Optional[int] = None
    material_id: Optional[int] = None
    quantity_required: Optional[float] = None
    priority: Optional[str] = None
    required_by: Optional[datetime] = None
    status: Optional[str] = None


class MaterialRequirement(MaterialRequirementBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Tower Type Schemas
# ============================================================================

class TowerTypeBase(BaseModel):
    name: str
    voltage_rating: Optional[str] = None
    height_meters: Optional[float] = None
    base_width_meters: Optional[float] = None
    weight_tons: Optional[float] = None
    circuit_type: Optional[str] = None
    description: Optional[str] = None


class TowerTypeCreate(TowerTypeBase):
    pass


class TowerTypeUpdate(BaseModel):
    name: Optional[str] = None
    voltage_rating: Optional[str] = None
    height_meters: Optional[float] = None
    base_width_meters: Optional[float] = None
    weight_tons: Optional[float] = None
    circuit_type: Optional[str] = None
    description: Optional[str] = None


class TowerType(TowerTypeBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Substation Type Schemas
# ============================================================================

class SubstationTypeBase(BaseModel):
    name: str
    voltage_level: Optional[str] = None
    capacity_mva: Optional[float] = None
    transformer_count: Optional[int] = None
    bay_count: Optional[int] = None
    type_category: Optional[str] = None
    description: Optional[str] = None


class SubstationTypeCreate(SubstationTypeBase):
    pass


class SubstationTypeUpdate(BaseModel):
    name: Optional[str] = None
    voltage_level: Optional[str] = None
    capacity_mva: Optional[float] = None
    transformer_count: Optional[int] = None
    bay_count: Optional[int] = None
    type_category: Optional[str] = None
    description: Optional[str] = None


class SubstationType(SubstationTypeBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Budget Schemas
# ============================================================================

class BudgetBase(BaseModel):
    fiscal_year: str
    category: Optional[str] = None
    allocated_amount: float
    spent_amount: float = 0.0
    remaining_amount: Optional[float] = None
    department: Optional[str] = None


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    fiscal_year: Optional[str] = None
    category: Optional[str] = None
    allocated_amount: Optional[float] = None
    spent_amount: Optional[float] = None
    remaining_amount: Optional[float] = None
    department: Optional[str] = None


class Budget(BudgetBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Tax Schemas
# ============================================================================

class TaxBase(BaseModel):
    name: str
    rate_percentage: float
    applicable_on: Optional[str] = None
    state: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class TaxCreate(TaxBase):
    pass


class TaxUpdate(BaseModel):
    name: Optional[str] = None
    rate_percentage: Optional[float] = None
    applicable_on: Optional[str] = None
    state: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class Tax(TaxBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Forecast Schemas
# ============================================================================

class ForecastBase(BaseModel):
    material_id: int
    location_id: int
    forecast_date: datetime
    predicted_demand: float
    confidence_level: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    method: str = "Prophet"


class ForecastCreate(ForecastBase):
    pass


class Forecast(ForecastBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ForecastGenerateRequest(BaseModel):
    weeks: int = Field(default=12, ge=1, le=52)
    material_ids: Optional[List[int]] = None
    location_ids: Optional[List[int]] = None


class ForecastSummary(BaseModel):
    total_forecasts: int
    avg_confidence: float
    materials_covered: int
    locations_covered: int


class ProcurementScheduleItem(BaseModel):
    week: str
    material_name: str
    planned_quantity: float
    status: str


# ============================================================================
# Vendor Schemas
# ============================================================================

class VendorBase(BaseModel):
    vendor_code: Optional[str] = None
    name: str
    state: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reliability_score: float = 0.9
    avg_lead_time_days: int = 14
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: bool = True


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    vendor_code: Optional[str] = None
    name: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reliability_score: Optional[float] = None
    avg_lead_time_days: Optional[int] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: Optional[bool] = None


class Vendor(VendorBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Warehouse Schemas
# ============================================================================

class WarehouseBase(BaseModel):
    warehouse_code: Optional[str] = None
    name: str
    state: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity_tons: Optional[float] = None
    is_active: bool = True


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    warehouse_code: Optional[str] = None
    name: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity_tons: Optional[float] = None
    is_active: Optional[bool] = None


class Warehouse(WarehouseBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Simulation Schemas
# ============================================================================

class SimulationRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=365)
    strategy: str = Field(default="balanced", pattern="^(cost_first|speed_first|balanced)$")
    start_date: Optional[datetime] = None


class SimulationSummary(BaseModel):
    total_days: int
    total_purchase_orders: int
    total_transfer_orders: int
    total_project_holds: int
    total_procurement_cost: float
    total_transfer_cost: float
    total_cost: float
    average_daily_cost: float


class ActionPlanResponse(BaseModel):
    date: datetime
    region: str
    purchase_orders: List[dict]
    transfer_orders: List[dict]
    project_holds: List[dict]
    total_procurement_cost: float
    total_transfer_cost: float
    reasoning: str


# ============================================================================
# Inventory Stock Schemas
# ============================================================================

class InventoryStockBase(BaseModel):
    warehouse_id: int
    material_id: int
    quantity_available: float = 0.0
    quantity_reserved: float = 0.0
    quantity_in_transit: float = 0.0
    reorder_point: Optional[float] = None
    max_stock_level: Optional[float] = None
    min_stock_level: float = 0.0
    last_restocked_date: Optional[datetime] = None
    last_issued_date: Optional[datetime] = None


class InventoryStockCreate(InventoryStockBase):
    pass


class InventoryStockUpdate(BaseModel):
    quantity_available: Optional[float] = None
    quantity_reserved: Optional[float] = None
    quantity_in_transit: Optional[float] = None
    reorder_point: Optional[float] = None
    max_stock_level: Optional[float] = None
    min_stock_level: Optional[float] = None


class InventoryStock(InventoryStockBase):
    id: int
    updated_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class InventoryStockWithDetails(InventoryStock):
    """Extended inventory stock with material and warehouse details"""
    material_name: Optional[str] = None
    material_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    warehouse_code: Optional[str] = None
    total_quantity: Optional[float] = None
    stock_status: Optional[str] = None  # OK, LOW, CRITICAL, OUT_OF_STOCK


# ============================================================================
# Inventory Transaction Schemas
# ============================================================================

class InventoryTransactionBase(BaseModel):
    transaction_type: str  # IN, OUT, TRANSFER_OUT, TRANSFER_IN, ADJUSTMENT
    warehouse_id: int
    material_id: int
    quantity: float
    unit_cost: float = 0.0
    total_cost: float = 0.0
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    project_id: Optional[int] = None
    vendor_id: Optional[int] = None
    source_warehouse_id: Optional[int] = None
    remarks: Optional[str] = None
    performed_by: Optional[str] = "system"
    transaction_date: Optional[datetime] = None


class InventoryTransactionCreate(InventoryTransactionBase):
    pass


class InventoryTransaction(InventoryTransactionBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class InventoryTransactionWithDetails(InventoryTransaction):
    """Extended transaction with material, warehouse, and project details"""
    material_name: Optional[str] = None
    warehouse_name: Optional[str] = None
    project_name: Optional[str] = None
    vendor_name: Optional[str] = None


# ============================================================================
# Stock Reservation Schemas
# ============================================================================

class StockReservationBase(BaseModel):
    warehouse_id: int
    material_id: int
    project_id: int
    quantity_reserved: float
    quantity_issued: float = 0.0
    required_by_date: Optional[datetime] = None
    status: str = "Active"
    priority: str = "Medium"
    remarks: Optional[str] = None


class StockReservationCreate(StockReservationBase):
    pass


class StockReservationUpdate(BaseModel):
    quantity_issued: Optional[float] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    remarks: Optional[str] = None


class StockReservation(StockReservationBase):
    id: int
    reservation_date: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class StockReservationWithDetails(StockReservation):
    """Extended reservation with material, warehouse, and project details"""
    material_name: Optional[str] = None
    material_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    project_name: Optional[str] = None
    quantity_remaining: Optional[float] = None


# ============================================================================
# Stock Alert Schemas
# ============================================================================

class StockAlertBase(BaseModel):
    alert_type: str  # LOW_STOCK, OUT_OF_STOCK, EXPIRING_SOON, OVERSTOCK
    severity: str = "Medium"
    warehouse_id: Optional[int] = None
    material_id: Optional[int] = None
    current_quantity: Optional[float] = None
    threshold_quantity: Optional[float] = None
    message: str
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


class StockAlertCreate(StockAlertBase):
    pass


class StockAlertUpdate(BaseModel):
    is_resolved: Optional[bool] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


class StockAlert(StockAlertBase):
    id: int
    alert_date: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class StockAlertWithDetails(StockAlert):
    """Extended alert with material and warehouse details"""
    material_name: Optional[str] = None
    warehouse_name: Optional[str] = None


# ============================================================================
# Inventory Operation Request Schemas
# ============================================================================

class StockInRequest(BaseModel):
    """Request to add stock to warehouse"""
    warehouse_id: int
    material_id: int
    quantity: float = Field(gt=0)
    unit_cost: float = Field(ge=0)
    vendor_id: Optional[int] = None
    reference_type: Optional[str] = "PO"
    reference_id: Optional[str] = None
    remarks: Optional[str] = None


class StockOutRequest(BaseModel):
    """Request to remove stock from warehouse"""
    warehouse_id: int
    material_id: int
    quantity: float = Field(gt=0)
    project_id: Optional[int] = None
    reference_type: Optional[str] = "PROJECT"
    reference_id: Optional[str] = None
    remarks: Optional[str] = None


class StockTransferRequest(BaseModel):
    """Request to transfer stock between warehouses"""
    material_id: int
    source_warehouse_id: int
    destination_warehouse_id: int
    quantity: float = Field(gt=0)
    remarks: Optional[str] = None


class StockAdjustmentRequest(BaseModel):
    """Request to adjust stock (for corrections)"""
    warehouse_id: int
    material_id: int
    quantity_adjustment: float  # Can be positive or negative
    remarks: str


class ReserveStockRequest(BaseModel):
    """Request to reserve stock for a project"""
    warehouse_id: int
    material_id: int
    project_id: int
    quantity: float = Field(gt=0)
    required_by_date: Optional[datetime] = None
    priority: str = "Medium"
    remarks: Optional[str] = None


class IssueStockRequest(BaseModel):
    """Request to issue reserved stock to a project"""
    reservation_id: int
    quantity_to_issue: float = Field(gt=0)
    remarks: Optional[str] = None


# ============================================================================
# Inventory Analytics Schemas
# ============================================================================

class InventorySummary(BaseModel):
    """Overall inventory summary"""
    total_warehouses: int
    total_materials_tracked: int
    total_stock_value: float
    total_reserved_value: float
    low_stock_items: int
    out_of_stock_items: int
    overstock_items: int
    active_reservations: int
    pending_alerts: int


class WarehouseInventorySummary(BaseModel):
    """Inventory summary for a specific warehouse"""
    warehouse_id: int
    warehouse_name: str
    total_materials: int
    total_stock_value: float
    capacity_utilization: Optional[float] = None
    low_stock_count: int
    out_of_stock_count: int


class MaterialInventorySummary(BaseModel):
    """Inventory summary for a specific material"""
    material_id: int
    material_name: str
    material_code: str
    total_available: float
    total_reserved: float
    total_in_transit: float
    warehouses_with_stock: int
    avg_stock_level: float
    status: str  # OK, LOW, CRITICAL


class StockMovementReport(BaseModel):
    """Stock movement report for a period"""
    material_id: int
    material_name: str
    warehouse_id: int
    warehouse_name: str
    opening_stock: float
    total_inward: float
    total_outward: float
    closing_stock: float
    period_start: datetime
    period_end: datetime


# ============================================================================
# Substation Schemas
# ============================================================================

class SubstationBase(BaseModel):
    substation_code: Optional[str] = None
    name: str
    substation_type: Optional[str] = None
    capacity: Optional[str] = None
    state: str
    city: Optional[str] = None
    latitude: float
    longitude: float
    status: str = "Active"
    primary_warehouse_id: Optional[int] = None
    stock_status: str = "Normal"
    stock_level_percentage: float = 100.0


class SubstationCreate(SubstationBase):
    pass


class SubstationUpdate(BaseModel):
    name: Optional[str] = None
    substation_type: Optional[str] = None
    capacity: Optional[str] = None
    status: Optional[str] = None
    stock_status: Optional[str] = None
    stock_level_percentage: Optional[float] = None


class Substation(SubstationBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SubstationCriticalMaterialBase(BaseModel):
    substation_id: int
    material_id: int
    material_name: Optional[str] = None
    current_quantity: float
    required_quantity: float
    shortage_percentage: float
    priority: str = "Medium"


class SubstationCriticalMaterial(SubstationCriticalMaterialBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class SubstationWithDetails(Substation):
    """Substation with critical materials and projects"""
    critical_materials: Optional[List[SubstationCriticalMaterialBase]] = []
    active_projects: Optional[int] = 0
    warehouse_name: Optional[str] = None


# ============================================================================
# Substation Project Schemas
# ============================================================================

class SubstationProjectBase(BaseModel):
    project_code: Optional[str] = None
    name: str
    description: Optional[str] = None
    substation_id: Optional[int] = None
    developer: Optional[str] = None
    developer_type: Optional[str] = None
    category: Optional[str] = None
    project_type: Optional[str] = None
    circuit_type: Optional[str] = None
    voltage_level: Optional[int] = None
    total_line_length: Optional[float] = None
    total_tower_locations: Optional[int] = None
    target_date: Optional[datetime] = None
    anticipated_cod: Optional[datetime] = None
    delay_days: int = 0
    foundation_completed: int = 0
    foundation_total: Optional[int] = None
    tower_erected: int = 0
    tower_total: Optional[int] = None
    stringing_completed_ckm: float = 0.0
    stringing_total_ckm: Optional[float] = None
    overall_progress: float = 0.0
    status: str = "Active"
    delay_reason: Optional[str] = None
    budget_sanctioned: Optional[float] = None
    budget_spent: float = 0.0


class SubstationProjectCreate(SubstationProjectBase):
    pass


class SubstationProjectUpdate(BaseModel):
    foundation_completed: Optional[int] = None
    tower_erected: Optional[int] = None
    stringing_completed_ckm: Optional[float] = None
    overall_progress: Optional[float] = None
    status: Optional[str] = None
    delay_days: Optional[int] = None
    delay_reason: Optional[str] = None
    budget_spent: Optional[float] = None


class SubstationProject(SubstationProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectProgress(BaseModel):
    """Progress details for a project"""
    foundation: dict  # {completed, total, percentage}
    tower_erection: dict
    stringing: dict
    overall: dict


class ProjectMaterialNeedBase(BaseModel):
    project_id: int
    material_id: int
    material_name: Optional[str] = None
    quantity_needed: float
    quantity_available: float = 0.0
    quantity_shortage: float
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    total_value: Optional[float] = None
    priority: str = "Medium"
    status: str = "Pending"


class ProjectMaterialNeed(ProjectMaterialNeedBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class SubstationProjectWithDetails(SubstationProject):
    """Project with progress and material needs"""
    progress: Optional[ProjectProgress] = None
    material_needs: Optional[List[ProjectMaterialNeedBase]] = []
    substation_name: Optional[str] = None


# ============================================================================
# Material Transfer Schemas
# ============================================================================

class MaterialTransferBase(BaseModel):
    transfer_code: Optional[str] = None
    source_warehouse_id: int
    destination_substation_id: int
    project_id: Optional[int] = None
    material_id: int
    quantity: float
    unit_cost: Optional[float] = None
    total_material_cost: Optional[float] = None
    distance_km: Optional[float] = None
    transport_cost: Optional[float] = None
    estimated_eta_hours: Optional[float] = None
    total_cost: Optional[float] = None
    status: str = "Planned"
    dispatch_date: Optional[datetime] = None
    expected_delivery: Optional[datetime] = None
    optimization_score: Optional[float] = None
    selected_reason: Optional[str] = None


class MaterialTransferCreate(BaseModel):
    source_warehouse_id: int
    destination_substation_id: int
    project_id: Optional[int] = None
    material_id: int
    quantity: float


class MaterialTransfer(MaterialTransferBase):
    id: int
    actual_delivery: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MaterialTransferWithDetails(MaterialTransfer):
    """Transfer with warehouse, substation, and material details"""
    source_warehouse_name: Optional[str] = None
    destination_substation_name: Optional[str] = None
    material_name: Optional[str] = None
    project_name: Optional[str] = None


# ============================================================================
# Optimal Procurement Schemas
# ============================================================================

class WarehouseOption(BaseModel):
    """A warehouse option for procurement"""
    warehouse_id: int
    warehouse_name: str
    available_quantity: float
    distance_km: float
    transport_cost: float
    unit_cost: float
    total_cost: float
    eta_hours: float
    optimization_score: float


class OptimalProcurementRequest(BaseModel):
    """Request to find optimal procurement options"""
    destination_substation_id: int
    material_id: int
    quantity_needed: float
    max_options: int = 5


class OptimalProcurementResponse(BaseModel):
    """Response with optimal procurement options"""
    destination_substation_id: int
    destination_substation_name: str
    material_id: int
    material_name: str
    quantity_needed: float
    options: List[WarehouseOption]
    recommended_option: Optional[WarehouseOption] = None
    split_recommendation: Optional[List[dict]] = None  # For split orders


class BulkTransferRequest(BaseModel):
    """Request to transfer multiple materials"""
    destination_substation_id: int
    project_id: Optional[int] = None
    materials: List[dict]  # [{material_id, quantity}]


class BulkTransferResponse(BaseModel):
    """Response for bulk transfer"""
    transfers: List[MaterialTransferWithDetails]
    total_distance_km: float
    total_transport_cost: float
    total_material_cost: float
    total_cost: float
    estimated_completion_hours: float
