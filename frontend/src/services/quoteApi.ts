// Quote API Service
const API_BASE_URL = 'http://localhost:8000/api/v1';

// ========== TYPES ==========

export interface MaterialBreakdown {
  description: string;
  quantity: number;
  unit: string;
  rate: number;
  cost: number;
}

export interface LineBreakdown {
  tower_cost: number;
  conductor_cost: number;
  foundation_cost: number;
  stringing_cost: number;
  subtotal: number;
  contingency: number;
}

export interface LineCost {
  distance_km: number;
  voltage_kv: number;
  terrain: string;
  circuit_type: string;
  total_towers: number;
  towers_per_km: number;
  breakdown: LineBreakdown;
  total_line_cost: number;
}

export interface SubstationCost {
  cost_of_material: number;
  service_cost: number;
  turnkey_charges: number;
  civil_works_cost?: number;
  total: number;
}

export interface QuoteResponse {
  success: boolean;
  project_type: string;
  item_code: string;
  category: string;
  voltage_level: string | null;
  capacity_mva: number | null;
  substation_cost: SubstationCost;
  materials: MaterialBreakdown[];
  total_items: number;
  line_cost: LineCost | null;
  total_project_cost: number;
}

export interface ProjectTypeInfo {
  title: string;
  item_code: string;
  category: string;
  voltage_level: string | null;
  capacity_mva: number | null;
  total_cost: number;
}

export interface AddProjectRequest {
  project_type: string;
  project_name: string;
  description?: string;
  from_lat?: number;
  from_lng?: number;
  to_lat?: number;
  to_lng?: number;
  substation_id?: number;
  state: string;
  city: string;
  terrain?: string;
  circuit_type?: string;
  developer?: string;
  developer_type?: string;
  target_date?: string;
  auto_generate_orders?: boolean;
}

export interface AddProjectResponse {
  success: boolean;
  project_id: number;
  project_code: string;
  project_name: string;
  total_cost: number;
  forecast_impact: {
    additional_materials: number;
    new_shortages_created: number;
    health_change: number;
    risk_level: string;
  };
  material_requirements: Array<{
    material: string;
    quantity: number;
    unit: string;
    cost: number;
    status: string;
  }>;
  shortage_risk: string;
  procurement_health_before: number;
  procurement_health_after: number;
}

// ========== API CLASS ==========

class QuoteAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, options);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || error.error || `HTTP error! status: ${response.status}`);
    }
    return await response.json();
  }

  // Get quote for a project type with optional line coordinates
  async getQuote(params: {
    project_type: string;
    from_lat?: number;
    from_lng?: number;
    to_lat?: number;
    to_lng?: number;
    terrain?: string;
    circuit_type?: string;
  }): Promise<QuoteResponse> {
    const queryParams = new URLSearchParams();
    queryParams.append('project_type', params.project_type);
    if (params.from_lat !== undefined) queryParams.append('from_lat', params.from_lat.toString());
    if (params.from_lng !== undefined) queryParams.append('from_lng', params.from_lng.toString());
    if (params.to_lat !== undefined) queryParams.append('to_lat', params.to_lat.toString());
    if (params.to_lng !== undefined) queryParams.append('to_lng', params.to_lng.toString());
    if (params.terrain) queryParams.append('terrain', params.terrain);
    if (params.circuit_type) queryParams.append('circuit_type', params.circuit_type);
    
    return this.fetch<QuoteResponse>(`/quote/?${queryParams.toString()}`);
  }

  // Calculate line cost only
  async getLineCost(params: {
    from_lat: number;
    from_lng: number;
    to_lat: number;
    to_lng: number;
    voltage_kv?: number;
    terrain?: string;
    circuit_type?: string;
  }): Promise<LineCost> {
    const queryParams = new URLSearchParams();
    queryParams.append('from_lat', params.from_lat.toString());
    queryParams.append('from_lng', params.from_lng.toString());
    queryParams.append('to_lat', params.to_lat.toString());
    queryParams.append('to_lng', params.to_lng.toString());
    if (params.voltage_kv) queryParams.append('voltage_kv', params.voltage_kv.toString());
    if (params.terrain) queryParams.append('terrain', params.terrain);
    if (params.circuit_type) queryParams.append('circuit_type', params.circuit_type);
    
    return this.fetch<LineCost>(`/quote/line-cost?${queryParams.toString()}`);
  }

  // List available project types
  async getProjectTypes(params?: {
    category?: string;
    voltage?: string;
    limit?: number;
  }): Promise<ProjectTypeInfo[]> {
    const queryParams = new URLSearchParams();
    if (params?.category) queryParams.append('category', params.category);
    if (params?.voltage) queryParams.append('voltage', params.voltage);
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    
    const queryString = queryParams.toString();
    return this.fetch<ProjectTypeInfo[]>(`/quote/project-types${queryString ? `?${queryString}` : ''}`);
  }

  // Search project types
  async searchProjectTypes(query: string, limit: number = 10): Promise<ProjectTypeInfo[]> {
    return this.fetch<ProjectTypeInfo[]>(`/quote/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  }

  // Add project from quote
  async addProjectFromQuote(request: AddProjectRequest): Promise<AddProjectResponse> {
    return this.fetch<AddProjectResponse>('/projects/add-from-quote', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
  }
}

// Export singleton instance
export const quoteApi = new QuoteAPI();
export default quoteApi;
