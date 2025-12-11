"""
Data Models for NEXUS System
Defines core entities: Project, Vendor, Warehouse, Material, Order, etc.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class ProjectType(Enum):
    """Types of POWERGRID projects"""
    TRANSMISSION_LINE = "Transmission_Line"
    SUBSTATION = "Substation"
    HVDC_CORRIDOR = "HVDC_Corridor"


class ProjectStage(Enum):
    """Project lifecycle stages"""
    PLANNING = "Planning"
    FOUNDATION = "Foundation"
    CONSTRUCTION = "Construction"
    COMMISSIONING = "Commissioning"
    COMPLETED = "Completed"


class ProjectStatus(Enum):
    """Project execution status"""
    ACTIVE = "Active"
    ON_HOLD = "On_Hold"
    DELAYED = "Delayed"
    COMPLETED = "Completed"


class TerrainType(Enum):
    """Terrain classifications affecting cost"""
    PLAIN = "Plain"
    HILLY = "Hilly"
    MOUNTAIN = "Mountain"
    COASTAL = "Coastal"
    DESERT = "Desert"


@dataclass
class Material:
    """Represents a material/component in the BOM"""
    id: str
    name: str
    category: str  # Steel, Copper, Cement, etc.
    unit: str  # MT, Pieces, Liters, etc.
    base_price: float  # INR per unit
    shelf_life_days: Optional[int] = None
    is_perishable: bool = False
    weight_per_unit: float = 1.0  # kg
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class Vendor:
    """Represents a supplier/vendor"""
    id: str
    name: str
    region: str
    state: str
    specializations: List[str]  # Material categories they supply
    reliability_score: float  # 0.0 to 1.0
    max_delay_days: int  # Historical worst-case delay
    price_competitiveness: float  # 0.8 to 1.2 (multiplier on base price)
    min_order_value: float = 100000  # INR
    material_prices: Dict[str, float] = field(default_factory=dict)  # {material_id: price}
    avg_lead_time_days: int = 30  # Average lead time for deliveries
    latitude: float = 0.0  # Vendor location for transport cost calculation
    longitude: float = 0.0
    
    def __hash__(self):
        return hash(self.id)
    
    def can_supply(self, material_id: str) -> bool:
        """Check if vendor can supply a material"""
        return material_id in self.material_prices
    
    def get_price(self, material_id: str, base_price: float) -> float:
        """Get vendor's price for a material"""
        if material_id in self.material_prices:
            return self.material_prices[material_id]
        # Apply competitiveness multiplier to base price
        return base_price * self.price_competitiveness


@dataclass
class Warehouse:
    """Represents a storage facility"""
    id: str
    name: str
    region: str
    state: str
    city: str
    latitude: float
    longitude: float
    max_capacity: int  # Total units
    current_load: int = 0
    inventory: Dict[str, int] = field(default_factory=dict)  # {material_id: quantity}
    safety_stock: Dict[str, int] = field(default_factory=dict)  # {material_id: min_quantity}
    
    def __hash__(self):
        return hash(self.id)
    
    def available_capacity(self) -> int:
        """Returns remaining storage capacity"""
        return self.max_capacity - self.current_load
    
    def has_stock(self, material_id: str, quantity: int) -> bool:
        """Check if warehouse has sufficient stock"""
        return self.inventory.get(material_id, 0) >= quantity
    
    def add_stock(self, material_id: str, quantity: int) -> None:
        """Add stock to inventory"""
        current = self.inventory.get(material_id, 0)
        self.inventory[material_id] = current + quantity
        self.current_load += quantity
    
    def remove_stock(self, material_id: str, quantity: int) -> bool:
        """Remove stock from inventory"""
        if not self.has_stock(material_id, quantity):
            return False
        self.inventory[material_id] -= quantity
        self.current_load -= quantity
        return True


@dataclass
class Project:
    """Represents a POWERGRID project"""
    id: str
    name: str
    project_type: ProjectType
    region: str
    state: str
    stage: ProjectStage
    status: ProjectStatus
    start_date: datetime
    expected_end_date: datetime
    latitude: float
    longitude: float
    
    # Project specifications
    length_km: Optional[float] = None  # For transmission lines
    voltage_kv: Optional[int] = None
    capacity_mw: Optional[float] = None  # For substations
    terrain_type: TerrainType = TerrainType.PLAIN
    
    # BOM & Demand
    required_materials: Dict[str, int] = field(default_factory=dict)  # {material_id: quantity}
    fulfilled_materials: Dict[str, int] = field(default_factory=dict)
    
    # Risk factors
    row_status: str = "Clear"  # "Clear", "Pending", "Blocked"
    weather_risk_level: str = "Low"  # "Low", "Medium", "High"
    
    def __hash__(self):
        return hash(self.id)
    
    def is_active(self) -> bool:
        """Check if project is actively executing"""
        return self.status == ProjectStatus.ACTIVE
    
    def material_fulfillment_rate(self) -> float:
        """Calculate percentage of materials fulfilled"""
        if not self.required_materials:
            return 1.0
        
        total_required = sum(self.required_materials.values())
        total_fulfilled = sum(self.fulfilled_materials.values())
        
        return total_fulfilled / total_required if total_required > 0 else 0.0


@dataclass
class PurchaseOrder:
    """Represents a procurement order"""
    id: str
    material_id: str
    vendor_id: str
    quantity: int
    unit_price: float
    total_cost: float
    
    order_date: datetime
    expected_delivery_date: datetime
    
    # Optional cost components (calculated separately if needed)
    tax_amount: float = 0.0
    transport_cost: float = 0.0
    landed_cost: float = 0.0  # Total delivered cost
    
    actual_delivery_date: Optional[datetime] = None
    
    # Use delivery_warehouse_id for consistency across codebase
    delivery_warehouse_id: str = ""
    destination_project_id: Optional[str] = None
    
    status: str = "Placed"  # Placed, In_Transit, Delivered, Delayed
    
    # XAI
    reasoning: str = ""  # Explanation for why this order was placed
    
    def __hash__(self):
        return hash(self.id)
    
    def __post_init__(self):
        """Calculate landed cost if not provided"""
        if self.landed_cost == 0.0 and self.total_cost > 0:
            self.landed_cost = self.total_cost + self.tax_amount + self.transport_cost


@dataclass
class TransferOrder:
    """Represents an inter-warehouse transfer"""
    id: str
    material_id: str
    quantity: int
    from_warehouse_id: str
    to_warehouse_id: str
    
    transfer_date: datetime
    expected_arrival_date: datetime
    transport_cost: float
    distance_km: float
    
    actual_arrival_date: Optional[datetime] = None
    
    status: str = "Initiated"  # Initiated, In_Transit, Completed
    reasoning: str = ""
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class DemandForecast:
    """Represents forecasted demand for a material"""
    material_id: str
    region: str
    forecast_date: datetime
    forecast_horizon_days: int
    
    # Demand components
    capex_demand: int  # From active projects
    opex_demand: int  # From maintenance/spares
    safety_stock_buffer: int
    total_demand: int
    
    # Risk factors
    weather_multiplier: float = 1.0
    sentiment_multiplier: float = 1.0
    
    # XAI
    reasoning: str = ""


@dataclass
class ActionPlan:
    """Daily action plan for supply chain operations"""
    date: datetime
    region: str = ""
    
    purchase_orders: List[PurchaseOrder] = field(default_factory=list)
    transfer_orders: List[TransferOrder] = field(default_factory=list)
    project_holds: List['ProjectHold'] = field(default_factory=list)
    projects_on_hold: List[str] = field(default_factory=list)  # Project IDs (legacy)
    alerts: List[str] = field(default_factory=list)
    
    total_procurement_cost: float = 0.0
    total_transfer_cost: float = 0.0
    materials_to_procure: int = 0
    reasoning: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export"""
        return {
            "date": self.date.isoformat(),
            "region": self.region,
            "purchase_orders": [
                {
                    "id": po.id,
                    "material": po.material_id,
                    "vendor": po.vendor_id,
                    "quantity": po.quantity,
                    "landed_cost": po.landed_cost,
                    "reasoning": po.reasoning
                }
                for po in self.purchase_orders
            ],
            "transfer_orders": [
                {
                    "id": to.id,
                    "material": to.material_id,
                    "from": to.from_warehouse_id,
                    "to": to.to_warehouse_id,
                    "quantity": to.quantity,
                    "cost": to.transport_cost,
                    "reasoning": to.reasoning
                }
                for to in self.transfer_orders
            ],
            "project_holds": [
                ph.to_dict() if hasattr(ph, 'to_dict') else {"project_id": str(ph)}
                for ph in self.project_holds
            ],
            "projects_on_hold": self.projects_on_hold,
            "alerts": self.alerts,
            "total_procurement_cost": self.total_procurement_cost,
            "total_transfer_cost": self.total_transfer_cost,
            "materials_to_procure": self.materials_to_procure,
            "reasoning": self.reasoning
        }


@dataclass
class MarketSentiment:
    """Market intelligence data"""
    date: datetime
    region: str
    topic: str  # RoW_Issue, Labor_Strike, etc.
    severity: str  # Low, Medium, High, Critical
    affected_states: List[str]
    description: str
    recommended_action: str
    
    # Impact multipliers
    lead_time_buffer_days: int = 0
    price_multiplier: float = 1.0
    halt_projects: bool = False


@dataclass
class WeatherForecast:
    """Weather forecast data"""
    date: datetime
    region: str
    state: str
    condition: str  # Heavy_Rain, Clear, etc.
    temperature_c: float
    precipitation_mm: float
    
    # Impact on operations
    construction_delay_factor: float = 0.0  # 0.0 (no delay) to 1.0 (complete halt)
    spares_demand_multiplier: float = 1.0


@dataclass
class ProjectHold:
    """Represents a project placed on hold"""
    project_id: str
    hold_reason: str  # Weather, RoW, Labor_Strike, etc.
    hold_date: datetime
    expected_resume_date: Optional[datetime] = None
    impact_description: str = ""
    severity: str = "Medium"  # Low, Medium, High, Critical
    
    def __hash__(self):
        return hash(self.project_id + self.hold_date.isoformat())
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export"""
        return {
            "project_id": self.project_id,
            "hold_reason": self.hold_reason,
            "hold_date": self.hold_date.isoformat(),
            "expected_resume_date": self.expected_resume_date.isoformat() if self.expected_resume_date else None,
            "impact_description": self.impact_description,
            "severity": self.severity
        }
