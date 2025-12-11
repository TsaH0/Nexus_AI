"""
Quote API Routes
Generates project quotes based on BOQ templates and coordinates
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from src.core.boq_service import get_boq_service


router = APIRouter(tags=["Quote"])


class QuoteRequest(BaseModel):
    """Request body for project quote"""
    project_type: str
    from_lat: Optional[float] = None
    from_lng: Optional[float] = None
    to_lat: Optional[float] = None
    to_lng: Optional[float] = None
    terrain: str = "normal"  # normal, hilly, urban, coastal
    circuit_type: str = "single"  # single, double


class MaterialBreakdown(BaseModel):
    description: str
    quantity: float
    unit: str
    rate: float
    cost: float


class LineBreakdown(BaseModel):
    tower_cost: float
    conductor_cost: float
    foundation_cost: float
    stringing_cost: float
    subtotal: float
    contingency: float


class LineCost(BaseModel):
    distance_km: float
    voltage_kv: int
    terrain: str
    circuit_type: str
    total_towers: int
    towers_per_km: float
    breakdown: LineBreakdown
    total_line_cost: float


class SubstationCost(BaseModel):
    cost_of_material: float
    service_cost: float
    turnkey_charges: float
    total: float


class QuoteResponse(BaseModel):
    success: bool
    project_type: str
    item_code: str
    category: str
    voltage_level: Optional[str]
    capacity_mva: Optional[float]
    substation_cost: SubstationCost
    materials: List[MaterialBreakdown]
    total_items: int
    line_cost: Optional[LineCost]
    total_project_cost: float


class ProjectTypeInfo(BaseModel):
    title: str
    item_code: str
    category: str
    voltage_level: Optional[str]
    capacity_mva: Optional[float]
    total_cost: float


@router.get("/", response_model=QuoteResponse)
async def get_quote(
    project_type: str = Query(..., description="Project type string, e.g., '33/22 kV 1 X 5 MVA New S/S(Outdoor)'"),
    from_lat: Optional[float] = Query(None, description="Starting latitude for transmission line"),
    from_lng: Optional[float] = Query(None, description="Starting longitude for transmission line"),
    to_lat: Optional[float] = Query(None, description="Ending latitude for transmission line"),
    to_lng: Optional[float] = Query(None, description="Ending longitude for transmission line"),
    terrain: str = Query("normal", description="Terrain type: normal, hilly, urban, coastal"),
    circuit_type: str = Query("single", description="Circuit type: single, double")
):
    """
    Generate a project quote based on project type and optional coordinates.
    
    - **project_type**: String matching a BOQ template (e.g., "33/22 kV 1 X 5 MVA New S/S(Outdoor)")
    - **from_lat/from_lng**: Starting coordinates for transmission line (optional)
    - **to_lat/to_lng**: Ending coordinates for transmission line (optional)
    - **terrain**: Affects tower count per km
    - **circuit_type**: Single or double circuit affects line cost
    
    Returns substation BOQ cost + transmission line cost (if coordinates provided)
    """
    boq_service = get_boq_service()
    
    quote = boq_service.generate_project_quote(
        project_type=project_type,
        from_lat=from_lat,
        from_lng=from_lng,
        to_lat=to_lat,
        to_lng=to_lng,
        terrain=terrain,
        circuit_type=circuit_type
    )
    
    if not quote.get('success'):
        raise HTTPException(
            status_code=404,
            detail={
                "error": quote.get('error'),
                "available_types": quote.get('available_types', [])
            }
        )
    
    return quote


@router.post("/calculate", response_model=QuoteResponse)
async def calculate_quote(request: QuoteRequest):
    """
    Generate a project quote using POST request body.
    
    Same as GET /quote but accepts parameters in request body.
    """
    boq_service = get_boq_service()
    
    quote = boq_service.generate_project_quote(
        project_type=request.project_type,
        from_lat=request.from_lat,
        from_lng=request.from_lng,
        to_lat=request.to_lat,
        to_lng=request.to_lng,
        terrain=request.terrain,
        circuit_type=request.circuit_type
    )
    
    if not quote.get('success'):
        raise HTTPException(
            status_code=404,
            detail={
                "error": quote.get('error'),
                "available_types": quote.get('available_types', [])
            }
        )
    
    return quote


@router.get("/line-cost")
async def calculate_line_cost(
    from_lat: float = Query(..., description="Starting latitude"),
    from_lng: float = Query(..., description="Starting longitude"),
    to_lat: float = Query(..., description="Ending latitude"),
    to_lng: float = Query(..., description="Ending longitude"),
    voltage_kv: int = Query(400, description="Voltage level in kV"),
    terrain: str = Query("normal", description="Terrain type"),
    circuit_type: str = Query("single", description="Circuit type")
):
    """
    Calculate only the transmission line cost between two coordinates.
    
    Useful for estimating line extension costs independently.
    """
    boq_service = get_boq_service()
    
    return boq_service.calculate_line_cost(
        from_lat=from_lat,
        from_lng=from_lng,
        to_lat=to_lat,
        to_lng=to_lng,
        voltage_kv=voltage_kv,
        terrain=terrain,
        circuit_type=circuit_type
    )


@router.get("/project-types", response_model=List[ProjectTypeInfo])
async def list_project_types(
    category: Optional[str] = Query(None, description="Filter by category: Substation, Switching Station, etc."),
    voltage: Optional[str] = Query(None, description="Filter by voltage level, e.g., '33'"),
    limit: int = Query(50, description="Maximum number of results")
):
    """
    List available project types from BOQ templates.
    
    Use this to discover what project types are available for quotes.
    """
    boq_service = get_boq_service()
    
    templates = boq_service.get_all_templates()
    
    # Apply filters
    if category:
        templates = [t for t in templates if category.lower() in t.project_category.lower()]
    
    if voltage:
        templates = [t for t in templates if voltage in (t.voltage_level or '')]
    
    # Sort by total cost descending
    templates.sort(key=lambda t: t.summary.total_cost_of_estimate, reverse=True)
    
    # Limit results
    templates = templates[:limit]
    
    return [
        ProjectTypeInfo(
            title=t.title,
            item_code=t.item_code,
            category=t.project_category,
            voltage_level=t.voltage_level,
            capacity_mva=t.capacity_mva,
            total_cost=t.summary.total_cost_of_estimate
        )
        for t in templates
    ]


@router.get("/search")
async def search_project_types(
    q: str = Query(..., description="Search query for project types"),
    limit: int = Query(10, description="Maximum results")
):
    """
    Search for project types matching a query string.
    
    Returns partial matches sorted by relevance.
    """
    boq_service = get_boq_service()
    
    query_lower = q.lower()
    results = []
    
    for template in boq_service.get_all_templates():
        # Calculate simple relevance score
        title_lower = template.title.lower()
        if query_lower in title_lower:
            # Exact substring match
            score = 1.0
        else:
            # Word overlap
            query_words = set(query_lower.split())
            title_words = set(title_lower.split())
            overlap = len(query_words & title_words)
            score = overlap / max(len(query_words), 1)
        
        if score > 0.2:  # Minimum 20% match
            results.append({
                'title': template.title,
                'item_code': template.item_code,
                'category': template.project_category,
                'voltage_level': template.voltage_level,
                'total_cost': template.summary.total_cost_of_estimate,
                'relevance_score': round(score, 2)
            })
    
    # Sort by relevance
    results.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    return results[:limit]


# =============================================================================
# TOWER CALCULATION ENDPOINT
# =============================================================================

class TowerCalculationRequest(BaseModel):
    """Request to calculate tower count for a transmission line"""
    distance_km: float
    voltage_kv: str = "400"
    terrain: str = "normal"  # normal, hilly, urban, coastal, forest


class TowerCalculationResponse(BaseModel):
    """Response with tower calculation details"""
    distance_km: float
    voltage_kv: str
    terrain: str
    span_distance_m: int
    num_towers: int
    num_spans: int
    avg_span_actual_m: float
    formula: str
    
    # Cost estimates
    estimated_tower_cost: float
    estimated_conductor_cost: float
    estimated_foundation_cost: float
    estimated_stringing_cost: float
    estimated_total_cost: float


@router.get("/tower-calculation")
async def calculate_tower_count(
    distance_km: float = Query(..., description="Line distance in kilometers"),
    voltage_kv: str = Query("400", description="Voltage level: 765, 400, 220, 132, 66, 33, 22, 11"),
    terrain: str = Query("normal", description="Terrain: normal, hilly, urban, coastal, forest")
):
    """
    🗼 **TOWER CALCULATION**
    
    Calculate the number of towers needed for a transmission line using 
    realistic span-based engineering calculations.
    
    Based on POWERGRID/CEA standards:
    - **765kV**: ~450m span (normal terrain) → ~2.2 towers/km
    - **400kV**: ~400m span (normal terrain) → ~2.5 towers/km
    - **220kV**: ~350m span (normal terrain) → ~2.9 towers/km
    - **132kV**: ~300m span (normal terrain) → ~3.3 towers/km
    - **33kV**: ~150m span (normal terrain) → ~6.7 towers/km
    
    Formula: num_towers = (distance_km × 1000 / span_distance) + 1
    """
    boq_service = get_boq_service()
    
    result = boq_service.calculate_tower_count(distance_km, voltage_kv, terrain)
    
    # Also get cost estimates
    cost_rates = boq_service.TOWER_COSTS_PER_KM.get(
        result["voltage_kv"], 
        boq_service.TOWER_COSTS_PER_KM['400']
    )
    
    num_towers = result["num_towers"]
    tower_cost = num_towers * cost_rates['tower']
    conductor_cost = distance_km * cost_rates['conductor']
    foundation_cost = num_towers * cost_rates['foundation']
    stringing_cost = distance_km * cost_rates['stringing']
    total_cost = tower_cost + conductor_cost + foundation_cost + stringing_cost
    
    return {
        **result,
        "estimated_costs": {
            "tower_cost": round(tower_cost, 2),
            "conductor_cost": round(conductor_cost, 2),
            "foundation_cost": round(foundation_cost, 2),
            "stringing_cost": round(stringing_cost, 2),
            "total_cost": round(total_cost, 2),
            "total_formatted": f"₹{total_cost/10000000:.2f} Cr" if total_cost >= 10000000 else f"₹{total_cost/100000:.2f} L"
        }
    }


@router.get("/span-standards")
async def get_span_standards():
    """
    📏 **SPAN DISTANCE STANDARDS**
    
    Returns the standard span distances (distance between towers) 
    for different voltage levels and terrain types.
    
    These are based on POWERGRID/CEA standards for the Indian power grid.
    """
    boq_service = get_boq_service()
    
    return {
        "title": "Tower Span Distance Standards (meters)",
        "source": "POWERGRID/CEA Design Standards",
        "note": "Span = distance between two consecutive towers",
        "standards": boq_service.TOWER_SPAN_METERS,
        "example": {
            "description": "For a 100km 400kV line in normal terrain:",
            "span_distance": "400 meters",
            "calculation": "(100 × 1000) / 400 + 1 = 251 towers",
            "towers_per_km": "~2.5 towers/km"
        }
    }
