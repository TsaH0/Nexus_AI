
const API_BASE_URL = 'http://localhost:8000/api/v1';

export interface ForecastSummary {
  total_forecast: number;
  total_ordered: number;
  total_variance: number;
  coverage_percent: number;
  regions_optimal: number;
  regions_under: number;
  regions_over: number;
  regions_inventory_adjusted: number;
}

export interface RegionalForecast {
  region_id: number;
  region_name: string;
  region_code: string;
  material_id: number;
  material_name: string;
  material_code: string;
  forecast_quantity: number;
  ordered_quantity: number;
  variance: number;
  variance_percent: number;
  existing_inventory: number;
  effective_shortage: number;
  order_status: 'optimal' | 'under_ordered' | 'over_ordered' | 'inventory_adjusted';
  reasoning: string;
}

export interface ForecastResponse {
  status: string;
  period: string;
  forecast_date: string;
  summary: ForecastSummary;
  forecasts: RegionalForecast[];
}

export interface Recommendation {
  warehouse: string;
  material: string;
  current_order: number;
  recommended_order: number | null;
  adjustment: string | null;
  priority: 'critical' | 'warning' | 'optimal' | 'surplus';
  reason: string;
}

export interface RecommendationsResponse {
  status: string;
  total_recommendations: number;
  priority_breakdown: {
    critical: number;
    warning: number;
    optimal: number;
    surplus: number;
  };
  recommendations: Recommendation[];
}

export interface InventoryImpactItem {
  warehouse: string;
  material: string;
  existing_inventory: number;
  forecast: number;
  ordered: number;
  units_not_ordered: number;
  inventory_utilization: string;
  benefit: string;
}

export interface InventoryImpactResponse {
  status: string;
  analysis: {
    total_warehouses_with_inventory: number;
    total_existing_inventory_units: number;
    total_units_order_reduced: number;
    items_with_inventory_adjustment: number;
  };
  message: string;
  details: InventoryImpactItem[];
}

export interface ComparisonItem {
    region: string;
    region_id?: number;
    material?: string;
    material_id?: number;
    material_code?: string;
    total_forecast: number;
    total_ordered: number;
    existing_inventory: number;
    variance: number;
    variance_percent: number;
    status: string;
    note?: string;
    material_count?: number;
    warehouse_count?: number;
}


class ForecastAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`);
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
    }
    return await response.json();
  }

  async getForecast(period: 'weekly' | 'monthly' | 'quarterly' = 'monthly'): Promise<ForecastResponse> {
    return this.fetch<ForecastResponse>(`/demand-forecast/?period=${period}`);
  }

  async getComparison(groupBy: 'warehouse' | 'material' = 'warehouse', period: 'weekly' | 'monthly' | 'quarterly' = 'monthly'): Promise<any> {
    return this.fetch<any>(`/demand-forecast/comparison?group_by=${groupBy}&period=${period}`);
  }

  async getRecommendations(severity: string = 'all'): Promise<RecommendationsResponse> {
    return this.fetch<RecommendationsResponse>(`/demand-forecast/recommendations?severity=${severity}`);
  }
  
  async getInventoryImpact(): Promise<InventoryImpactResponse> {
     return this.fetch<InventoryImpactResponse>('/demand-forecast/inventory-impact');
  }
}

export const forecastApi = new ForecastAPI();
export default forecastApi;
