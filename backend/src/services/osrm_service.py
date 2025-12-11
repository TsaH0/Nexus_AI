"""
OSRM (Open Source Routing Machine) Service
===========================================
Provides real road-based distance and ETA calculations using OSRM API.

Supports:
- Public OSRM servers (no authentication)
- Private OSRM servers with API key/token authentication
- Fallback to Haversine distance calculation

Reference: http://project-osrm.org/docs/v5.5.1/api/
"""

import requests
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)


@dataclass
class RouteResult:
    """Result from OSRM route calculation"""
    distance_km: float
    duration_minutes: float
    eta_readable: str
    source: str  # 'osrm' or 'haversine_fallback'
    
    def to_dict(self) -> dict:
        return {
            "distance_km": round(self.distance_km, 2),
            "duration_minutes": round(self.duration_minutes, 2),
            "eta_readable": self.eta_readable,
            "source": self.source
        }


class OSRMService:
    """
    OSRM Service for road-based routing calculations.
    
    Usage:
        service = OSRMService()
        result = service.get_route(28.61, 77.20, 28.98, 77.70)
        print(result.eta_readable)  # "1 hr 23 min"
    """
    
    DEFAULT_OSRM_URL = "http://router.project-osrm.org"
    
    # Transport mode speed adjustments (road base)
    TRANSPORT_SPEED_MULTIPLIERS = {
        "road": 1.0,        # Normal road speed
        "express": 0.7,     # Faster (express highway/priority)
        "rail": 0.5,        # 2x faster than road
        "air": 0.1,         # 10x faster (for long distances)
    }
    
    def __init__(
        self, 
        osrm_url: str = None, 
        api_key: str = None,
        timeout: int = 10
    ):
        """
        Initialize OSRM Service.
        
        Args:
            osrm_url: OSRM server URL (uses public server if not provided)
            api_key: API key for private OSRM servers (optional)
            timeout: Request timeout in seconds
        """
        self.osrm_url = osrm_url or os.getenv("OSRM_URL", self.DEFAULT_OSRM_URL)
        self.api_key = api_key or os.getenv("OSRM_API_KEY")
        self.timeout = timeout
    
    def get_route(
        self,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
        transport_mode: str = "road"
    ) -> RouteResult:
        """
        Get route distance and ETA between two coordinates.
        
        Args:
            start_lat, start_lng: Origin coordinates
            end_lat, end_lng: Destination coordinates
            transport_mode: One of 'road', 'express', 'rail', 'air'
        
        Returns:
            RouteResult with distance, duration, and readable ETA
        """
        try:
            result = self._call_osrm(start_lat, start_lng, end_lat, end_lng)
            
            # Apply transport mode adjustment
            speed_multiplier = self.TRANSPORT_SPEED_MULTIPLIERS.get(transport_mode, 1.0)
            adjusted_duration = result["duration_minutes"] * speed_multiplier
            
            return RouteResult(
                distance_km=result["distance_km"],
                duration_minutes=adjusted_duration,
                eta_readable=self._format_duration(adjusted_duration),
                source="osrm"
            )
            
        except Exception as e:
            logger.warning(f"OSRM failed, using fallback: {e}")
            return self._haversine_fallback(
                start_lat, start_lng, end_lat, end_lng, transport_mode
            )
    
    def _call_osrm(
        self, 
        start_lat: float, 
        start_lng: float, 
        end_lat: float, 
        end_lng: float
    ) -> Dict:
        """
        Make OSRM API call.
        
        OSRM expects coordinates in <lng>,<lat> format!
        """
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # OSRM format: /route/v1/driving/{lng},{lat};{lng},{lat}
        url = (
            f"{self.osrm_url}/route/v1/driving/"
            f"{start_lng},{start_lat};{end_lng},{end_lat}"
            f"?overview=false"
        )
        
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != "Ok":
            raise ValueError(f"OSRM error: {data.get('message', 'Unknown error')}")
        
        route = data["routes"][0]
        
        return {
            "distance_km": route["distance"] / 1000,
            "duration_minutes": route["duration"] / 60
        }
    
    def _haversine_fallback(
        self,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
        transport_mode: str
    ) -> RouteResult:
        """
        Fallback calculation using Haversine distance with estimated road factor.
        """
        import math
        
        # Haversine formula
        lat1_rad = math.radians(start_lat)
        lon1_rad = math.radians(start_lng)
        lat2_rad = math.radians(end_lat)
        lon2_rad = math.radians(end_lng)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius
        straight_distance = 6371 * c
        
        # Road distance is typically 1.3x straight-line distance
        road_distance = straight_distance * 1.3
        
        # Estimate duration based on average speed
        # India average: 40 km/h for road transport
        base_speeds = {
            "road": 40,
            "express": 60,
            "rail": 80,
            "air": 500
        }
        speed = base_speeds.get(transport_mode, 40)
        duration_hours = road_distance / speed
        duration_minutes = duration_hours * 60
        
        return RouteResult(
            distance_km=road_distance,
            duration_minutes=duration_minutes,
            eta_readable=self._format_duration(duration_minutes),
            source="haversine_fallback"
        )
    
    def _format_duration(self, minutes: float) -> str:
        """Format duration in human-readable format"""
        if minutes < 60:
            return f"{int(minutes)} min"
        
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        
        if hours >= 24:
            days = hours // 24
            hours = hours % 24
            if hours > 0:
                return f"{days}d {hours}h {mins}m"
            return f"{days}d {mins}m"
        
        return f"{hours}h {mins}m"
    
    def get_distance_matrix(
        self, 
        origins: list[Tuple[float, float]], 
        destinations: list[Tuple[float, float]]
    ) -> Dict:
        """
        Get distance matrix between multiple origins and destinations.
        
        Args:
            origins: List of (lat, lng) tuples
            destinations: List of (lat, lng) tuples
        
        Returns:
            Matrix of distances and durations
        """
        # Build OSRM table request
        coords = origins + destinations
        coords_str = ";".join([f"{lng},{lat}" for lat, lng in coords])
        
        sources_indices = ";".join([str(i) for i in range(len(origins))])
        dest_indices = ";".join([str(i) for i in range(len(origins), len(coords))])
        
        url = (
            f"{self.osrm_url}/table/v1/driving/{coords_str}"
            f"?sources={sources_indices}&destinations={dest_indices}"
        )
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != "Ok":
                raise ValueError(f"OSRM error: {data.get('message')}")
            
            return {
                "durations": data["durations"],  # Matrix in seconds
                "sources": data.get("sources", []),
                "destinations": data.get("destinations", [])
            }
            
        except Exception as e:
            logger.warning(f"OSRM matrix failed: {e}")
            return {"error": str(e)}


# Convenience function for simple usage
def get_eta_osrm(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
    osrm_url: str = None,
    api_key: str = None,
    transport_mode: str = "road"
) -> Dict:
    """
    Simple function to get ETA between two points.
    
    Returns:
        Dict with distance_km, eta_minutes, eta_readable, source
    """
    service = OSRMService(osrm_url=osrm_url, api_key=api_key)
    result = service.get_route(start_lat, start_lng, end_lat, end_lng, transport_mode)
    return result.to_dict()
