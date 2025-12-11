"""
Geospatial Utilities
Functions for distance calculation, logistics cost estimation, etc.
"""

import math
from typing import Tuple

#TODO: Integrate with real-world mapping APIs for accurate distances like google Routes API client libraries


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth
    
    Args:
        lat1, lon1: Latitude and longitude of first point (in degrees)
        lat2, lon2: Latitude and longitude of second point (in degrees)
    
    Returns:
        Distance in kilometers
    
    Note: For production, consider using actual road network distances via 
    Google Maps API or OSRM for more accurate logistics calculations.
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth's radius in kilometers
    earth_radius = 6371
    
    distance = earth_radius * c
    return round(distance, 2)


def calculate_transport_cost(distance_km: float, 
                             quantity: int, 
                             cost_per_km: float = 25.0,
                             loading_cost: float = 5000.0) -> float:
    """
    Calculate total transport cost for moving materials
    
    Args:
        distance_km: Distance to transport
        quantity: Number of units
        cost_per_km: Cost per kilometer (default from config)
        loading_cost: Fixed loading/unloading cost
    
    Returns:
        Total transport cost in INR
    """
    # Base transport cost
    transport_cost = distance_km * cost_per_km
    
    # Add loading/unloading
    total_cost = transport_cost + loading_cost
    
    # Scale slightly with quantity (more trucks needed)
    if quantity > 1000:
        total_cost *= (1 + (quantity - 1000) / 10000)
    
    return round(total_cost, 2)


def calculate_warehouse_distance_matrix(warehouses: list) -> dict:
    """
    Pre-calculate distances between all warehouse pairs
    
    Args:
        warehouses: List of Warehouse objects
    
    Returns:
        Dictionary with (wh1_id, wh2_id): distance mapping
    """
    distance_matrix = {}
    
    for i, wh1 in enumerate(warehouses):
        for wh2 in warehouses[i+1:]:
            dist = haversine_distance(wh1.latitude, wh1.longitude, 
                                     wh2.latitude, wh2.longitude)
            distance_matrix[(wh1.id, wh2.id)] = dist
            distance_matrix[(wh2.id, wh1.id)] = dist  # Symmetric
    
    return distance_matrix


def find_nearest_warehouse(project_lat: float, 
                          project_lon: float, 
                          warehouses: list,
                          region_filter: str = None) -> Tuple[object, float]:
    """
    Find the nearest warehouse to a project location
    
    Args:
        project_lat, project_lon: Project coordinates
        warehouses: List of Warehouse objects
        region_filter: Optional region constraint
    
    Returns:
        Tuple of (nearest_warehouse, distance_km)
    """
    nearest_wh = None
    min_distance = float('inf')
    
    for wh in warehouses:
        if region_filter and wh.region != region_filter:
            continue
        
        dist = haversine_distance(project_lat, project_lon, 
                                 wh.latitude, wh.longitude)
        
        if dist < min_distance:
            min_distance = dist
            nearest_wh = wh
    
    return nearest_wh, round(min_distance, 2)


def estimate_delivery_time(distance_km: float, 
                           base_lead_time_days: int = 0) -> int:
    """
    Estimate delivery time based on distance
    
    Args:
        distance_km: Transport distance
        base_lead_time_days: Base procurement lead time
    
    Returns:
        Total estimated days for delivery
    """
    travel_days = math.ceil(distance_km / (50 * 8))
    
    buffer_days = 2
    
    return base_lead_time_days + travel_days + buffer_days
