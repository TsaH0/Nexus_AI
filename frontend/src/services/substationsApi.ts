// Substations API Service
const API_BASE_URL = 'http://localhost:8000/api/v1';

// ========== SUBSTATION TYPES ==========

export interface Substation {
  id: number;
  substation_code: string;
  name: string;
  substation_type: string;
  capacity: string;
  state: string;
  city: string;
  latitude: number;
  longitude: number;
  status: string;
  primary_warehouse_id: number | null;
  stock_status: 'Normal' | 'Low' | 'Understocked' | 'Overstocked';
  stock_level_percentage: number;
  created_at: string;
  updated_at: string;
}

export interface CriticalMaterial {
  substation_id: number;
  material_id: number;
  material_name: string;
  current_quantity: number;
  required_quantity: number;
  shortage_percentage: number;
  priority: 'Critical' | 'High' | 'Medium' | 'Low';
}

export interface SubstationWithDetails extends Substation {
  critical_materials: CriticalMaterial[];
  active_projects: number;
  warehouse_name: string | null;
}

export interface SubstationProject {
  id: number;
  project_code: string;
  name: string;
  description: string;
  substation_id: number;
  developer: string;
  developer_type: string;
  category: string;
  project_type: string;
  circuit_type: string;
  voltage_level: number;
  total_line_length: number;
  total_tower_locations: number;
  target_date: string;
  anticipated_cod: string;
  delay_days: number;
  foundation_completed: number;
  foundation_total: number;
  tower_erected: number;
  tower_total: number;
  stringing_completed_ckm: number;
  stringing_total_ckm: number;
  overall_progress: number;
  status: string;
  delay_reason: string;
  budget_sanctioned: number;
  budget_spent: number;
  created_at: string;
  updated_at: string;
}

export interface DashboardSummary {
  total_substations: number;
  stock_status: {
    normal: number;
    low: number;
    understocked: number;
    overstocked: number;
  };
  critical_alerts: number;
  active_projects: number;
  delayed_projects: number;
  average_stock_level: number;
}

export interface StateStats {
  count: number;
  understocked: number;
  overstocked: number;
  normal: number;
}

export interface SubstationMapData {
  id: number;
  name: string;
  code: string;
  lat: number;
  lng: number;
  state: string;
  city: string;
  type: string;
  capacity: string;
  stock_status: string;
  stock_level: number;
  color: string;
}

// ========== API CLASS ==========

class SubstationsAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  }

  // Get all substations
  async getSubstations(params?: {
    state?: string;
    stock_status?: string;
    status?: string;
    skip?: number;
    limit?: number;
  }): Promise<Substation[]> {
    const queryParams = new URLSearchParams();
    if (params?.state) queryParams.append('state', params.state);
    if (params?.stock_status) queryParams.append('stock_status', params.stock_status);
    if (params?.status) queryParams.append('status', params.status);
    if (params?.skip) queryParams.append('skip', params.skip.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    
    const queryString = queryParams.toString();
    return this.fetch<Substation[]>(`/substations/${queryString ? `?${queryString}` : ''}`);
  }

  // Get dashboard summary
  async getDashboardSummary(): Promise<DashboardSummary> {
    return this.fetch<DashboardSummary>('/substations/dashboard/summary');
  }

  // Get substations by state
  async getSubstationsByState(): Promise<Record<string, StateStats>> {
    return this.fetch<Record<string, StateStats>>('/substations/by-state');
  }

  // Get understocked substations
  async getUnderstockedSubstations(threshold?: number): Promise<SubstationWithDetails[]> {
    const query = threshold ? `?threshold=${threshold}` : '';
    return this.fetch<SubstationWithDetails[]>(`/substations/understocked${query}`);
  }

  // Get overstocked substations
  async getOverstockedSubstations(threshold?: number): Promise<SubstationWithDetails[]> {
    const query = threshold ? `?threshold=${threshold}` : '';
    return this.fetch<SubstationWithDetails[]>(`/substations/overstocked${query}`);
  }

  // Get substation details
  async getSubstation(id: number): Promise<SubstationWithDetails> {
    return this.fetch<SubstationWithDetails>(`/substations/${id}`);
  }

  // Get substation projects
  async getSubstationProjects(substationId: number, status?: string): Promise<SubstationProject[]> {
    const query = status ? `?status=${status}` : '';
    return this.fetch<SubstationProject[]>(`/substations/${substationId}/projects${query}`);
  }

  // Get critical materials for a substation
  async getCriticalMaterials(substationId: number, priority?: string): Promise<CriticalMaterial[]> {
    const query = priority ? `?priority=${priority}` : '';
    return this.fetch<CriticalMaterial[]>(`/substations/${substationId}/critical-materials${query}`);
  }

  // Get map data
  async getMapData(): Promise<SubstationMapData[]> {
    return this.fetch<SubstationMapData[]>('/substations/map/data');
  }
}

// Export singleton instance
export const substationsApi = new SubstationsAPI();
export default substationsApi;
