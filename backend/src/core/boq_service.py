"""
BOQ (Bill of Quantity) Data Service
Loads and provides access to standardized project cost data from JSON files.
Used for project quotes and material forecasting.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from math import radians, sin, cos, sqrt, atan2
import re


@dataclass
class BOQItem:
    """Individual item in a Bill of Quantity"""
    serial_number: int
    description: str
    unit: str
    quantity: float
    rate_per_unit: float
    total_cost: float
    components: Optional[List[Dict]] = None


@dataclass
class BOQSummary:
    """Cost summary for a BOQ"""
    cost_of_material: float = 0.0
    service_cost: float = 0.0
    sub_total: float = 0.0
    turnkey_charges: float = 0.0
    total_cost_of_estimate: float = 0.0
    civil_works_cost: Optional[float] = None


@dataclass
class BOQTemplate:
    """Complete BOQ template for a project type"""
    title: str
    item_code: str
    items: List[BOQItem]
    summary: BOQSummary
    file_path: str
    
    @property
    def voltage_level(self) -> Optional[str]:
        """Extract voltage level from title"""
        match = re.search(r'(\d+/\d+)\s*[kK][vV]', self.title)
        if match:
            return match.group(1) + " kV"
        match = re.search(r'(\d+)\s*[kK][vV]', self.title)
        if match:
            return match.group(1) + " kV"
        return None
    
    @property
    def capacity_mva(self) -> Optional[float]:
        """Extract MVA capacity from title"""
        match = re.search(r'(\d+(?:\.\d+)?)\s*MVA', self.title, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None
    
    @property
    def project_category(self) -> str:
        """Determine project category from title"""
        title_lower = self.title.lower()
        if 'substation' in title_lower or 's/s' in title_lower:
            return 'Substation'
        elif 'switching' in title_lower:
            return 'Switching Station'
        elif 'augmentation' in title_lower:
            return 'Augmentation'
        elif 'transformer' in title_lower:
            return 'Transformer'
        elif 'feeder' in title_lower:
            return 'Feeder'
        elif 'line' in title_lower or 'transmission' in title_lower:
            return 'Transmission Line'
        return 'Other'


class BOQService:
    """Service for loading and querying BOQ templates"""
    
    # Tower cost estimates per km based on voltage level
    TOWER_COSTS_PER_KM = {
        '765': {'tower': 2500000, 'conductor': 800000, 'foundation': 500000, 'stringing': 300000},
        '400': {'tower': 1800000, 'conductor': 600000, 'foundation': 400000, 'stringing': 250000},
        '220': {'tower': 1200000, 'conductor': 400000, 'foundation': 300000, 'stringing': 200000},
        '132': {'tower': 800000, 'conductor': 300000, 'foundation': 200000, 'stringing': 150000},
        '66': {'tower': 500000, 'conductor': 200000, 'foundation': 150000, 'stringing': 100000},
        '33': {'tower': 300000, 'conductor': 150000, 'foundation': 100000, 'stringing': 80000},
        '22': {'tower': 250000, 'conductor': 120000, 'foundation': 80000, 'stringing': 60000},
        '11': {'tower': 150000, 'conductor': 80000, 'foundation': 50000, 'stringing': 40000},
    }
    
    # ==========================================================================
    # TOWER SPACING (SPAN DISTANCE) - REALISTIC ENGINEERING VALUES
    # ==========================================================================
    # Based on actual POWERGRID/CEA standards for Indian power grid
    # Span = distance between two consecutive towers
    # Higher voltage = larger towers = longer spans
    
    # Average SPAN DISTANCE in METERS by voltage level and terrain
    TOWER_SPAN_METERS = {
        # Format: voltage_level -> terrain -> span_in_meters
        # Source: POWERGRID Design Standards / CEA Manual
        '765': {'normal': 450, 'hilly': 350, 'urban': 380, 'coastal': 400, 'forest': 320},
        '400': {'normal': 400, 'hilly': 300, 'urban': 350, 'coastal': 380, 'forest': 280},
        '220': {'normal': 350, 'hilly': 250, 'urban': 300, 'coastal': 330, 'forest': 230},
        '132': {'normal': 300, 'hilly': 200, 'urban': 250, 'coastal': 280, 'forest': 180},
        '66':  {'normal': 200, 'hilly': 150, 'urban': 180, 'coastal': 190, 'forest': 140},
        '33':  {'normal': 150, 'hilly': 100, 'urban': 130, 'coastal': 140, 'forest': 90},
        '22':  {'normal': 120, 'hilly': 80,  'urban': 100, 'coastal': 110, 'forest': 70},
        '11':  {'normal': 80,  'hilly': 60,  'urban': 70,  'coastal': 75,  'forest': 55},
    }
    
    # Deprecated - kept for backward compatibility
    # Use TOWER_SPAN_METERS instead and calculate: towers = (distance_km * 1000) / span + 1
    TOWERS_PER_KM = {
        # Format: voltage_level -> terrain -> towers_per_km
        # These values are calculated as: 1000 / span_meters
        '765': {'normal': 2.22, 'hilly': 2.86, 'urban': 2.63, 'coastal': 2.50},
        '400': {'normal': 2.50, 'hilly': 3.33, 'urban': 2.86, 'coastal': 2.63},
        '220': {'normal': 2.86, 'hilly': 4.00, 'urban': 3.33, 'coastal': 3.03},
        '132': {'normal': 3.33, 'hilly': 5.00, 'urban': 4.00, 'coastal': 3.57},
        '66':  {'normal': 5.00, 'hilly': 6.67, 'urban': 5.56, 'coastal': 5.26},
        '33':  {'normal': 6.67, 'hilly': 10.0, 'urban': 7.69, 'coastal': 7.14},
        '22':  {'normal': 8.33, 'hilly': 12.5, 'urban': 10.0, 'coastal': 9.09},
        '11':  {'normal': 12.5, 'hilly': 16.7, 'urban': 14.3, 'coastal': 13.3},
    }
    
    @classmethod
    def calculate_tower_count(cls, distance_km: float, voltage_kv: str, terrain: str = 'normal') -> dict:
        """
        Calculate the number of towers needed for a transmission line.
        
        Formula: num_towers = (distance_in_meters / span) + 1
        The +1 accounts for the terminal tower at each end.
        
        Args:
            distance_km: Line distance in kilometers
            voltage_kv: Voltage level (e.g., '400', '220', '132')
            terrain: Terrain type ('normal', 'hilly', 'urban', 'coastal', 'forest')
            
        Returns:
            dict with tower count, span distance, and details
        """
        # Get span distance for voltage and terrain
        voltage_key = str(voltage_kv).replace('kV', '').replace('KV', '').strip()
        
        if voltage_key not in cls.TOWER_SPAN_METERS:
            # Default to 220kV if not found
            voltage_key = '220'
        
        terrain_spans = cls.TOWER_SPAN_METERS[voltage_key]
        span_meters = terrain_spans.get(terrain, terrain_spans.get('normal', 300))
        
        # Calculate number of towers
        distance_meters = distance_km * 1000
        num_towers = int(distance_meters / span_meters) + 1
        
        # Also calculate number of spans (always towers - 1)
        num_spans = num_towers - 1
        
        return {
            "distance_km": distance_km,
            "voltage_kv": voltage_key,
            "terrain": terrain,
            "span_distance_m": span_meters,
            "num_towers": num_towers,
            "num_spans": num_spans,
            "avg_span_actual_m": round(distance_meters / num_spans, 1) if num_spans > 0 else span_meters,
            "formula": f"({distance_km} km × 1000) / {span_meters}m + 1 = {num_towers} towers"
        }
    
    def __init__(self, boq_directory: str = None):
        """Initialize BOQ service with directory path"""
        if boq_directory is None:
            # Default path relative to project root
            boq_directory = Path(__file__).parent.parent.parent / "data" / "BOQ_files"
        
        self.boq_directory = Path(boq_directory)
        self.templates: Dict[str, BOQTemplate] = {}
        self.templates_by_code: Dict[str, BOQTemplate] = {}
        self._load_all_templates()
    
    def _load_all_templates(self):
        """Load all BOQ JSON files from directory"""
        if not self.boq_directory.exists():
            print(f"Warning: BOQ directory not found: {self.boq_directory}")
            return
        
        for json_file in self.boq_directory.glob("*_structured.json"):
            try:
                template = self._parse_json_file(json_file)
                if template:
                    # Store by title (normalized)
                    key = self._normalize_title(template.title)
                    self.templates[key] = template
                    # Also store by item code
                    self.templates_by_code[template.item_code] = template
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
        
        print(f"Loaded {len(self.templates)} BOQ templates")
    
    def _parse_json_file(self, file_path: Path) -> Optional[BOQTemplate]:
        """Parse a single BOQ JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data.get('title') or not data.get('items'):
            return None
        
        items = []
        for item in data.get('items', []):
            items.append(BOQItem(
                serial_number=item.get('serial_number', 0),
                description=item.get('description', ''),
                unit=item.get('unit', ''),
                quantity=float(item.get('quantity', 0) or 0),
                rate_per_unit=float(item.get('rate_per_unit', 0) or 0),
                total_cost=float(item.get('total_cost', 0) or 0),
                components=item.get('components')
            ))
        
        summary_data = data.get('summary', {}) or {}
        summary = BOQSummary(
            cost_of_material=float(summary_data.get('cost_of_material', 0) or 0),
            service_cost=float(summary_data.get('service_cost', 0) or 0),
            sub_total=float(summary_data.get('sub_total', 0) or 0),
            turnkey_charges=float(summary_data.get('turnkey_charges', 0) or 0),
            total_cost_of_estimate=float(summary_data.get('total_cost_of_estimate', 0) or 0),
            civil_works_cost=summary_data.get('civil_works_cost')
        )
        
        return BOQTemplate(
            title=data['title'],
            item_code=data.get('item_code', ''),
            items=items,
            summary=summary,
            file_path=str(file_path)
        )
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for matching"""
        # Remove extra spaces, convert to lowercase
        normalized = ' '.join(title.lower().split())
        # Remove special chars but keep essential ones
        normalized = re.sub(r'[^\w\s/\-]', '', normalized)
        return normalized
    
    def find_template(self, query: str) -> Optional[BOQTemplate]:
        """Find a BOQ template matching the query string"""
        # Try exact match on item code first
        if query in self.templates_by_code:
            return self.templates_by_code[query]
        
        # Try normalized title match
        normalized_query = self._normalize_title(query)
        if normalized_query in self.templates:
            return self.templates[normalized_query]
        
        # Try fuzzy matching - find best match
        best_match = None
        best_score = 0
        
        for key, template in self.templates.items():
            # Calculate match score based on common words
            query_words = set(normalized_query.split())
            key_words = set(key.split())
            common = len(query_words & key_words)
            score = common / max(len(query_words), 1)
            
            if score > best_score and score > 0.5:  # At least 50% match
                best_score = score
                best_match = template
        
        return best_match
    
    def get_all_templates(self) -> List[BOQTemplate]:
        """Get all loaded BOQ templates"""
        return list(self.templates.values())
    
    def get_templates_by_category(self, category: str) -> List[BOQTemplate]:
        """Get templates filtered by category"""
        return [t for t in self.templates.values() if t.project_category.lower() == category.lower()]
    
    def get_templates_by_voltage(self, voltage: str) -> List[BOQTemplate]:
        """Get templates filtered by voltage level"""
        return [t for t in self.templates.values() if voltage.lower() in (t.voltage_level or '').lower()]
    
    @staticmethod
    def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in km between two coordinates"""
        R = 6371  # Earth's radius in km
        
        lat1_rad, lat2_rad = radians(lat1), radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lng = radians(lng2 - lng1)
        
        a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def calculate_line_cost(
        self,
        from_lat: float,
        from_lng: float,
        to_lat: float,
        to_lng: float,
        voltage_kv: int = 400,
        terrain: str = 'normal',
        circuit_type: str = 'single'
    ) -> Dict[str, Any]:
        """
        Calculate transmission line cost based on coordinates
        
        Uses realistic span-based tower calculation:
        - Tower count = (distance_in_meters / span_distance) + 1
        - Span distances based on POWERGRID/CEA standards
        
        Returns detailed breakdown of tower, conductor, foundation, stringing costs
        """
        distance_km = self.haversine_distance(from_lat, from_lng, to_lat, to_lng)
        
        # Get cost rates for voltage level
        voltage_str = str(voltage_kv)
        cost_rates = self.TOWER_COSTS_PER_KM.get(voltage_str, self.TOWER_COSTS_PER_KM['400'])
        
        # Calculate number of towers using span-based method
        tower_calc = self.calculate_tower_count(distance_km, voltage_str, terrain)
        total_towers = tower_calc['num_towers']
        span_distance = tower_calc['span_distance_m']
        towers_per_km = 1000 / span_distance  # For backward compatibility
        
        # Circuit multiplier
        circuit_multiplier = 2.0 if circuit_type == 'double' else 1.0
        
        # Calculate costs
        tower_cost = total_towers * cost_rates['tower'] * circuit_multiplier
        conductor_cost = distance_km * cost_rates['conductor'] * circuit_multiplier
        foundation_cost = total_towers * cost_rates['foundation']
        stringing_cost = distance_km * cost_rates['stringing'] * circuit_multiplier
        
        subtotal = tower_cost + conductor_cost + foundation_cost + stringing_cost
        contingency = subtotal * 0.05  # 5% contingency
        total = subtotal + contingency
        
        return {
            'distance_km': round(distance_km, 2),
            'voltage_kv': voltage_kv,
            'terrain': terrain,
            'circuit_type': circuit_type,
            'total_towers': total_towers,
            'span_distance_m': span_distance,
            'towers_per_km': round(towers_per_km, 2),
            'tower_calculation': tower_calc['formula'],
            'breakdown': {
                'tower_cost': round(tower_cost, 2),
                'conductor_cost': round(conductor_cost, 2),
                'foundation_cost': round(foundation_cost, 2),
                'stringing_cost': round(stringing_cost, 2),
                'subtotal': round(subtotal, 2),
                'contingency': round(contingency, 2),
            },
            'total_line_cost': round(total, 2)
        }
    
    def generate_project_quote(
        self,
        project_type: str,
        from_lat: Optional[float] = None,
        from_lng: Optional[float] = None,
        to_lat: Optional[float] = None,
        to_lng: Optional[float] = None,
        include_line: bool = True,
        terrain: str = 'normal',
        circuit_type: str = 'single'
    ) -> Dict[str, Any]:
        """
        Generate a complete project quote
        
        Combines substation BOQ cost with transmission line cost (if coordinates provided)
        """
        # Find matching BOQ template
        template = self.find_template(project_type)
        
        if not template:
            return {
                'success': False,
                'error': f"No BOQ template found for project type: {project_type}",
                'available_types': [t.title for t in list(self.templates.values())[:10]]
            }
        
        # Extract voltage from template
        voltage_kv = 400  # default
        if template.voltage_level:
            # Extract primary voltage (e.g., "33/11 kV" -> 33)
            match = re.search(r'(\d+)', template.voltage_level)
            if match:
                voltage_kv = int(match.group(1))
        
        # Build quote response
        quote = {
            'success': True,
            'project_type': template.title,
            'item_code': template.item_code,
            'category': template.project_category,
            'voltage_level': template.voltage_level,
            'capacity_mva': template.capacity_mva,
            'substation_cost': {
                'cost_of_material': template.summary.cost_of_material,
                'service_cost': template.summary.service_cost,
                'turnkey_charges': template.summary.turnkey_charges,
                'total': template.summary.total_cost_of_estimate
            },
            'materials': [
                {
                    'description': item.description,
                    'quantity': item.quantity,
                    'unit': item.unit,
                    'rate': item.rate_per_unit,
                    'cost': item.total_cost
                }
                for item in template.items
            ],
            'total_items': len(template.items)
        }
        
        # Add line cost if coordinates provided
        if include_line and all([from_lat, from_lng, to_lat, to_lng]):
            line_cost = self.calculate_line_cost(
                from_lat, from_lng, to_lat, to_lng,
                voltage_kv=voltage_kv,
                terrain=terrain,
                circuit_type=circuit_type
            )
            quote['line_cost'] = line_cost
            quote['total_project_cost'] = round(
                template.summary.total_cost_of_estimate + line_cost['total_line_cost'], 2
            )
        else:
            quote['line_cost'] = None
            quote['total_project_cost'] = template.summary.total_cost_of_estimate
        
        return quote


# Singleton instance
_boq_service: Optional[BOQService] = None


def get_boq_service() -> BOQService:
    """Get singleton instance of BOQ service"""
    global _boq_service
    if _boq_service is None:
        _boq_service = BOQService()
    return _boq_service
