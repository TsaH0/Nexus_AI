// API Service for connecting to the backend
const API_BASE_URL = 'http://localhost:8000/api/v1';

// ========== INVENTORY API TYPES (matching backend schemas) ==========

export interface StockAdjustmentRequest {
  warehouse_id: number;
  material_id: number;
  quantity_adjustment: number;
  remarks: string;
}

export interface InventoryStockWithDetails {
  id: number;
  warehouse_id: number;
  material_id: number;
  quantity_available: number;
  quantity_reserved: number;
  quantity_in_transit: number;
  reorder_point: number | null;
  max_stock_level: number | null;
  min_stock_level: number;
  last_restocked_date: string | null;
  last_issued_date: string | null;
  updated_at: string;
  created_at: string;
  material_name: string;
  material_code: string;
  warehouse_name: string;
  warehouse_code: string;
  total_quantity: number;
  stock_status: 'OK' | 'LOW' | 'CRITICAL' | 'OUT_OF_STOCK';
}

export interface InventorySummary {
  total_warehouses: number;
  total_materials_tracked: number;
  total_stock_value: number;
  total_reserved_value: number;
  low_stock_items: number;
  out_of_stock_items: number;
  overstock_items: number;
  active_reservations: number;
  pending_alerts: number;
}

export interface WarehouseInventorySummary {
  warehouse_id: number;
  warehouse_name: string;
  total_materials: number;
  total_stock_value: number;
  capacity_utilization: number | null;
  low_stock_count: number;
  out_of_stock_count: number;
}

export interface StockAlertWithDetails {
  id: number;
  alert_type: 'LOW_STOCK' | 'OUT_OF_STOCK' | 'EXPIRING_SOON' | 'OVERSTOCK';
  severity: 'Low' | 'Medium' | 'High' | 'Critical';
  warehouse_id: number | null;
  material_id: number | null;
  current_quantity: number | null;
  threshold_quantity: number | null;
  message: string;
  is_resolved: boolean;
  resolved_at: string | null;
  resolved_by: string | null;
  alert_date: string;
  created_at: string;
  material_name: string | null;
  warehouse_name: string | null;
}

export interface StockReservationWithDetails {
  id: number;
  warehouse_id: number;
  material_id: number;
  project_id: number;
  quantity_reserved: number;
  quantity_issued: number;
  required_by_date: string | null;
  status: 'Active' | 'Fulfilled' | 'Cancelled' | 'Expired';
  priority: 'Low' | 'Medium' | 'High' | 'Critical';
  remarks: string | null;
  reservation_date: string;
  created_at: string;
  updated_at: string;
  material_name: string | null;
  material_code: string | null;
  warehouse_name: string | null;
  project_name: string | null;
  quantity_remaining: number | null;
}

export interface InventoryTransactionWithDetails {
  id: number;
  transaction_type: 'IN' | 'OUT' | 'TRANSFER_OUT' | 'TRANSFER_IN' | 'ADJUSTMENT';
  warehouse_id: number;
  material_id: number;
  quantity: number;
  unit_cost: number;
  total_cost: number;
  reference_type: string | null;
  reference_id: string | null;
  project_id: number | null;
  vendor_id: number | null;
  source_warehouse_id: number | null;
  remarks: string | null;
  performed_by: string;
  transaction_date: string;
  created_at: string;
  material_name: string | null;
  warehouse_name: string | null;
  project_name: string | null;
  vendor_name: string | null;
}

// Warehouse basic info
export interface Warehouse {
  id: number;
  name: string;
  warehouse_code: string;
  location: string;
}

// Location with coordinates (warehouses are at locations)
export interface Location {
  id: number;
  name: string;
  state: string;
  region: string;
  latitude: number;
  longitude: number;
  created_at: string;
}

// Warehouse with location data for map display
export interface WarehouseMapData {
  id: number;
  name: string;
  code: string;
  lat: number;
  lng: number;
  state: string;
  stockItems: InventoryStockWithDetails[];
  totalStock: number;
  lowStockCount: number;
  outOfStockCount: number;
  stockStatus: 'Normal' | 'Low' | 'Critical';
}

// Material with price info
export interface Material {
  id: number;
  material_code: string;
  name: string;
  category: string;
  unit: string;
  unit_price: number;
  lead_time_days: number;
  min_order_quantity: number;
  safety_stock_days: number;
  description: string;
  created_at: string;
}


// API Functions
class InventoryAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, options);
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`API Error: ${response.status} - ${errorText}`);
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  }

  // Get all stock items - matches GET /inventory/stock
  async getStockItems(params?: {
    warehouse_id?: number;
    material_id?: number;
    low_stock_only?: boolean;
    include_zero?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<InventoryStockWithDetails[]> {
    const queryParams = new URLSearchParams();
    if (params?.warehouse_id) queryParams.append('warehouse_id', params.warehouse_id.toString());
    if (params?.material_id) queryParams.append('material_id', params.material_id.toString());
    if (params?.low_stock_only) queryParams.append('low_stock_only', 'true');
    if (params?.include_zero) queryParams.append('include_zero', 'true');
    if (params?.skip) queryParams.append('skip', params.skip.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    
    const queryString = queryParams.toString();
    return this.fetch<InventoryStockWithDetails[]>(`/inventory/stock${queryString ? `?${queryString}` : ''}`);
  }

  // Get inventory summary - matches GET /inventory/analytics/summary
  async getSummary(): Promise<InventorySummary> {
    return this.fetch<InventorySummary>('/inventory/analytics/summary');
  }

  // Get specific warehouse summary - matches GET /inventory/analytics/warehouse/{warehouse_id}
  async getWarehouseSummary(warehouseId: number): Promise<WarehouseInventorySummary> {
    return this.fetch<WarehouseInventorySummary>(`/inventory/analytics/warehouse/${warehouseId}`);
  }

  // Get warehouse summaries - fetches for multiple warehouses
  // First gets unique warehouses from stock items, then fetches their summaries
  async getWarehouseSummaries(): Promise<WarehouseInventorySummary[]> {
    try {
      // Get all stock items to find unique warehouses
      const stockItems = await this.getStockItems({ include_zero: true, limit: 1000 });
      
      // Extract unique warehouse IDs
      const warehouseIds = [...new Set(stockItems.map(s => s.warehouse_id))];
      
      // Fetch summary for each warehouse
      const summaries = await Promise.all(
        warehouseIds.map(id => this.getWarehouseSummary(id).catch(() => null))
      );
      
      // Filter out failed requests
      return summaries.filter((s): s is WarehouseInventorySummary => s !== null);
    } catch (error) {
      console.error('Failed to fetch warehouse summaries:', error);
      throw error;
    }
  }

  // Get stock alerts - matches GET /inventory/alerts
  async getAlerts(params?: {
    warehouse_id?: number;
    material_id?: number;
    alert_type?: string;
    severity?: string;
    is_resolved?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<StockAlertWithDetails[]> {
    const queryParams = new URLSearchParams();
    if (params?.warehouse_id) queryParams.append('warehouse_id', params.warehouse_id.toString());
    if (params?.material_id) queryParams.append('material_id', params.material_id.toString());
    if (params?.alert_type) queryParams.append('alert_type', params.alert_type);
    if (params?.severity) queryParams.append('severity', params.severity);
    if (params?.is_resolved !== undefined) queryParams.append('is_resolved', params.is_resolved.toString());
    if (params?.skip) queryParams.append('skip', params.skip.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    
    const queryString = queryParams.toString();
    return this.fetch<StockAlertWithDetails[]>(`/inventory/alerts${queryString ? `?${queryString}` : ''}`);
  }

  // Get stock reservations - matches GET /inventory/reservations
  async getReservations(params?: {
    warehouse_id?: number;
    material_id?: number;
    project_id?: number;
    status?: string;
    skip?: number;
    limit?: number;
  }): Promise<StockReservationWithDetails[]> {
    const queryParams = new URLSearchParams();
    if (params?.warehouse_id) queryParams.append('warehouse_id', params.warehouse_id.toString());
    if (params?.material_id) queryParams.append('material_id', params.material_id.toString());
    if (params?.project_id) queryParams.append('project_id', params.project_id.toString());
    if (params?.status) queryParams.append('status', params.status);
    if (params?.skip) queryParams.append('skip', params.skip.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    
    const queryString = queryParams.toString();
    return this.fetch<StockReservationWithDetails[]>(`/inventory/reservations${queryString ? `?${queryString}` : ''}`);
  }

  // Get transactions - matches GET /inventory/transactions
  async getTransactions(params?: {
    warehouse_id?: number;
    material_id?: number;
    transaction_type?: string;
    start_date?: string;
    end_date?: string;
    skip?: number;
    limit?: number;
  }): Promise<InventoryTransactionWithDetails[]> {
    const queryParams = new URLSearchParams();
    if (params?.warehouse_id) queryParams.append('warehouse_id', params.warehouse_id.toString());
    if (params?.material_id) queryParams.append('material_id', params.material_id.toString());
    if (params?.transaction_type) queryParams.append('transaction_type', params.transaction_type);
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    if (params?.skip) queryParams.append('skip', params.skip.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    
    const queryString = queryParams.toString();
    return this.fetch<InventoryTransactionWithDetails[]>(`/inventory/transactions${queryString ? `?${queryString}` : ''}`);
  }

  // Get stock items grouped by warehouse for map display
  async getStockByWarehouse(): Promise<Map<number, InventoryStockWithDetails[]>> {
    const stockItems = await this.getStockItems({ include_zero: true, limit: 1000 });
    
    const stockByWarehouse = new Map<number, InventoryStockWithDetails[]>();
    
    stockItems.forEach(item => {
      if (!stockByWarehouse.has(item.warehouse_id)) {
        stockByWarehouse.set(item.warehouse_id, []);
      }
      stockByWarehouse.get(item.warehouse_id)!.push(item);
    });
    
    return stockByWarehouse;
  }

  // Get substation map data - matches GET /substations/map/data
  async getSubstationsMapData(): Promise<SubstationMapData[]> {
    return this.fetch<SubstationMapData[]>('/substations/map/data');
  }

  // Get all locations with coordinates - matches GET /locations/
  async getLocations(): Promise<Location[]> {
    return this.fetch<Location[]>('/locations/');
  }

  // Get warehouses with stock data for map display
  async getWarehousesWithStock(): Promise<WarehouseMapData[]> {
    try {
      // Fetch both locations and stock data
      const [locations, stockItems] = await Promise.all([
        this.getLocations(),
        this.getStockItems({ include_zero: true, limit: 1000 })
      ]);

      // Group stock by warehouse
      const stockByWarehouse = new Map<number, InventoryStockWithDetails[]>();
      stockItems.forEach(item => {
        if (!stockByWarehouse.has(item.warehouse_id)) {
          stockByWarehouse.set(item.warehouse_id, []);
        }
        stockByWarehouse.get(item.warehouse_id)!.push(item);
      });

      // Build warehouse map data by matching warehouses with locations
      const warehouses: WarehouseMapData[] = [];
      
      stockByWarehouse.forEach((items, warehouseId) => {
        // Find matching location (warehouse ID corresponds to location ID in this case)
        const location = locations.find(l => l.id === warehouseId);
        if (location && items.length > 0) {
          const lowStockCount = items.filter(i => i.stock_status === 'LOW' || i.stock_status === 'CRITICAL').length;
          const outOfStockCount = items.filter(i => i.stock_status === 'OUT_OF_STOCK').length;
          const criticalCount = items.filter(i => i.stock_status === 'CRITICAL').length;
          const totalStock = items.reduce((sum, i) => sum + i.total_quantity, 0);
          
          // Determine status based on ACTUAL stock data
          let stockStatus: 'Normal' | 'Low' | 'Critical' = 'Normal';
          
          if (outOfStockCount > 0 || criticalCount > 0) {
            // Critical: has out of stock items OR critical stock items
            stockStatus = 'Critical';
          } else if (lowStockCount > 0) {
            // Low: has low stock items but no critical/out of stock
            stockStatus = 'Low';
          } else {
            // Normal: all items are OK
            stockStatus = 'Normal';
          }

          warehouses.push({
            id: warehouseId,
            name: items[0].warehouse_name,
            code: items[0].warehouse_code,
            lat: location.latitude,
            lng: location.longitude,
            state: location.state,
            stockItems: items,
            totalStock: Math.round(totalStock),
            lowStockCount,
            outOfStockCount,
            stockStatus
          });
        }
      });

      return warehouses;
    } catch (error) {
      console.error('Failed to fetch warehouses with stock:', error);
      throw error;
    }
  }

  // Get all materials with prices - matches GET /materials/
  async getMaterials(): Promise<Material[]> {
    return this.fetch<Material[]>('/materials/');
  }

  // Get inventory triggers
  async getInventoryTriggers(warehouseId?: number): Promise<InventoryTriggerResponse> {
    const query = warehouseId ? `?warehouse_id=${warehouseId}` : '';
    return this.fetch<InventoryTriggerResponse>(`/inventory/triggers${query}`);
  }

  // Simulate Trigger Logic
  async simulateTrigger(data: TriggerSimulationRequest): Promise<{ status: string; data: InventoryTriggerItem }> {
    return this.fetch<{ status: string; data: InventoryTriggerItem }>('/inventory/triggers', {
      method: 'POST',
      body: JSON.stringify(data),
      headers: { 'Content-Type': 'application/json' }
    });
  }


  // Adjust stock level (Simple)
  async adjustStock(data: StockAdjustmentRequest): Promise<InventoryStockWithDetails> {
    return this.fetch<InventoryStockWithDetails>('/inventory/operations/adjust', {
      method: 'POST',
      body: JSON.stringify(data),
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Update Inventory with Alert Logic - matches POST /inventory/update-and-alert
  async updateAndAlert(data: {
    warehouse_id: number;
    material_id: number;
    quantity_change?: number; // Optional if using set logic (handled by backend or simple delta)
    new_quantity?: number;    // Optional, if SET operation
    operation?: 'SET' | 'ADD' | 'SUBTRACT';
    remarks?: string;
    email_recipient?: string;
    whatsapp_recipient?: string;
    utr_email_threshold?: number;
    utr_whatsapp_threshold?: number;
    otr_email_threshold?: number;
    otr_whatsapp_threshold?: number;
    generate_pdf?: boolean;
  }): Promise<any> {
    return this.fetch<any>('/inventory/update-and-alert', {
      method: 'POST',
      body: JSON.stringify(data),
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Substation map data from backend
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
  stock_status: 'Normal' | 'Understocked' | 'Overstocked';
  stock_level: number;
  color: string;
}

// Export singleton instance
export const inventoryApi = new InventoryAPI();

export default inventoryApi;

// ========== TRIGGER ENGINE TYPES ==========

export interface TriggerMetrics {
  safety_stock: number;
  reorder_point: number;
  utr: number;
  otr: number;
  par: number;
}

export interface TriggerStatus {
  severity: 'GREEN' | 'AMBER' | 'RED';
  label: string;
  action: string;
}

export interface TriggerContext {
  daily_demand: number;
  lead_time_days: number;
  days_of_stock: number;
  nearby_substations: number;
  demand_multiplier: number;
}

export interface InventoryTriggerItem {
  item_id: string;
  item_name: string;
  warehouse_code?: string;
  warehouse_name?: string;
  current_stock: number;
  metrics: TriggerMetrics;
  status: TriggerStatus;
  context?: TriggerContext;
  simulation?: {
    is_simulation: boolean;
    input: {
      item_name: string;
      current_stock: number;
      safety_stock: number;
      reorder_point: number;
      max_stock_level: number;
      lead_time_days: number;
      daily_demand_used: number;
    };
  };
}

export interface InventoryTriggerResponse {
  status: string;
  total_items?: number;
  summary?: { red: number; amber: number; green: number };
  data: InventoryTriggerItem[];
}

// Add to the default export object
// functionality will be merged in the existing object if used as 'inventoryApi.getTriggers'
// But since the default export is an object literal at the end of the file, appending won't work easily.
// I need to use replace_file_content to insert it into the object.

export interface TriggerSimulationRequest {
  item_name?: string;
  current_stock: number;
  safety_stock: number;
  reorder_point: number;
  item_type?: string;
}
