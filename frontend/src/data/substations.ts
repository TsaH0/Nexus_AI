export interface Substation {
  id: number;
  name: string;
  lat: number;
  lng: number;
  capacity: string;
  status: 'Active' | 'Maintenance';
  stockStatus: 'Normal' | 'Understocked' | 'Overstocked';
  criticalMaterials?: string[];
  stockLevel?: number; // percentage
  type: 'Warehouse' | 'Supplier' | 'Towers';
}

// Sample substation locations across India (real approximate locations)
export const substations: Substation[] = [
  { id: 1, name: 'Delhi Hub Substation', lat: 28.6139, lng: 77.2090, capacity: '400kV', status: 'Active', stockStatus: 'Normal', stockLevel: 78, type: 'Warehouse' },
  { id: 2, name: 'Mumbai Coastal Substation', lat: 19.0760, lng: 72.8777, capacity: '220kV', status: 'Active', stockStatus: 'Normal', stockLevel: 85, type: 'Supplier' },
  { id: 3, name: 'Chennai Junction Substation', lat: 13.0827, lng: 80.2707, capacity: '220kV', status: 'Maintenance', stockStatus: 'Normal', stockLevel: 65, type: 'Towers' },
  { id: 4, name: 'Kolkata Power Substation', lat: 22.5726, lng: 88.3639, capacity: '400kV', status: 'Active', stockStatus: 'Normal', stockLevel: 72, type: 'Towers' },
  { id: 5, name: 'Hyderabad Central Substation', lat: 17.3850, lng: 78.4867, capacity: '220kV', status: 'Active', stockStatus: 'Normal', stockLevel: 82, type: 'Towers' },
  { id: 6, name: 'Pune Grid Substation', lat: 18.5204, lng: 73.8567, capacity: '132kV', status: 'Active', stockStatus: 'Normal', stockLevel: 88, type: 'Towers' },
  { id: 7, name: 'Ahmedabad West Substation', lat: 23.0225, lng: 72.5714, capacity: '400kV', status: 'Active', stockStatus: 'Normal', stockLevel: 71, type: 'Towers' },
  { id: 8, name: 'Jaipur Pink Substation', lat: 26.9124, lng: 75.7873, capacity: '220kV', status: 'Active', stockStatus: 'Normal', stockLevel: 76, type: 'Towers' },
  { id: 9, name: 'Lucknow North Substation', lat: 26.8467, lng: 80.9462, capacity: '132kV', status: 'Active', stockStatus: 'Normal', stockLevel: 88, type: 'Towers' },
  { id: 10, name: 'Chandigarh Regional Substation', lat: 30.7333, lng: 76.7794, capacity: '220kV', status: 'Active', stockStatus: 'Normal', stockLevel: 85, type: 'Towers' },
  
  // Himachal Pradesh - Overstocked (1)
  { id: 11, name: 'Kashmir  Substation', lat: 32.8, lng: 77.1734, capacity: '220kV', status: 'Active', stockStatus: 'Overstocked', criticalMaterials: ['Tower Structures', 'Insulators', 'Hardware', 'Steel Members'], stockLevel: 123, type: 'Towers' },
  
  { id: 12, name: 'Bhopal Central Substation', lat: 23.2599, lng: 77.4126, capacity: '132kV', status: 'Active', stockStatus: 'Normal', stockLevel: 76, type: 'Towers' },
  { id: 13, name: 'Indore Junction Substation', lat: 22.7196, lng: 75.8577, capacity: '220kV', status: 'Active', stockStatus: 'Normal', stockLevel: 68, type: 'Towers' },
  { id: 14, name: 'Kochi Coastal Substation', lat: 9.9312, lng: 76.2673, capacity: '132kV', status: 'Maintenance', stockStatus: 'Normal', stockLevel: 68, type: 'Towers' },
  { id: 15, name: 'Visakhapatnam Port Substation', lat: 17.6869, lng: 83.2185, capacity: '400kV', status: 'Active', stockStatus: 'Normal', stockLevel: 82, type: 'Towers' },
  { id: 16, name: 'Patna East Substation', lat: 25.5941, lng: 85.1376, capacity: '220kV', status: 'Active', stockStatus: 'Normal', stockLevel: 73, type: 'Towers' },
  { id: 17, name: 'Nagpur Hub Substation', lat: 21.1458, lng: 79.0882, capacity: '400kV', status: 'Active', stockStatus: 'Normal', stockLevel: 79, type: 'Warehouse' },
  { id: 18, name: 'Surat Industrial Substation', lat: 21.1702, lng: 72.8311, capacity: '220kV', status: 'Active', stockStatus: 'Normal', stockLevel: 79, type: 'Towers' },
  { id: 19, name: 'Coimbatore South Substation', lat: 11.0168, lng: 76.9558, capacity: '132kV', status: 'Active', stockStatus: 'Normal', stockLevel: 75, type: 'Towers' },
  { id: 20, name: 'Vadodara Grid Substation', lat: 22.3072, lng: 73.1812, capacity: '220kV', status: 'Active', stockStatus: 'Normal', stockLevel: 85, type: 'Towers' },
  
  // Karnataka - Understocked (1)
  { id: 21, name: 'Bangalore Tech Substation', lat: 12.9716, lng: 77.5946, capacity: '400kV', status: 'Active', stockStatus: 'Understocked', criticalMaterials: ['ACSR Conductors', 'Transformers', 'OPGW Cable', 'Breakers'], stockLevel: 40, type: 'Towers' },
];
