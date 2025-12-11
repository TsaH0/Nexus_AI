// ==============================================================================
// INVENTORY DATA - Based on Backend API Routes (src/api/routes/inventory.py)
// ==============================================================================

// InventoryStockWithDetails - from /inventory/stock endpoint
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
  // Extended details
  material_name: string;
  material_code: string;
  warehouse_name: string;
  warehouse_code: string;
  total_quantity: number;
  stock_status: 'OK' | 'LOW' | 'CRITICAL' | 'OUT_OF_STOCK';
}

// InventorySummary - from /inventory/analytics/summary endpoint
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

// WarehouseInventorySummary - from /inventory/analytics/warehouse/{warehouse_id} endpoint
export interface WarehouseInventorySummary {
  warehouse_id: number;
  warehouse_name: string;
  total_materials: number;
  total_stock_value: number;
  capacity_utilization: number | null;
  low_stock_count: number;
  out_of_stock_count: number;
}

// StockAlertWithDetails - from /inventory/alerts endpoint
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
  // Extended details
  material_name: string | null;
  warehouse_name: string | null;
}

// StockReservationWithDetails - from /inventory/reservations endpoint
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
  // Extended details
  material_name: string | null;
  material_code: string | null;
  warehouse_name: string | null;
  project_name: string | null;
  quantity_remaining: number | null;
}

// InventoryTransaction - from /inventory/transactions endpoint
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
  // Extended details
  material_name: string | null;
  warehouse_name: string | null;
  project_name: string | null;
  vendor_name: string | null;
}

// ==============================================================================
// SAMPLE DATA - Matching Backend Schema
// ==============================================================================

// Inventory Summary (from /inventory/analytics/summary)
export const inventorySummary: InventorySummary = {
  total_warehouses: 8,
  total_materials_tracked: 156,
  total_stock_value: 28500000,
  total_reserved_value: 4200000,
  low_stock_items: 12,
  out_of_stock_items: 3,
  overstock_items: 5,
  active_reservations: 24,
  pending_alerts: 8
};

// Warehouse Inventory Summaries (from /inventory/analytics/warehouse/{id})
export const warehouseSummaries: WarehouseInventorySummary[] = [
  {
    warehouse_id: 1,
    warehouse_name: 'Delhi Central Warehouse',
    total_materials: 45,
    total_stock_value: 8500000,
    capacity_utilization: 78,
    low_stock_count: 3,
    out_of_stock_count: 0
  },
  {
    warehouse_id: 2,
    warehouse_name: 'Mumbai Port Warehouse',
    total_materials: 38,
    total_stock_value: 6200000,
    capacity_utilization: 65,
    low_stock_count: 2,
    out_of_stock_count: 1
  },
  {
    warehouse_id: 3,
    warehouse_name: 'Bangalore Tech Hub',
    total_materials: 42,
    total_stock_value: 7100000,
    capacity_utilization: 82,
    low_stock_count: 4,
    out_of_stock_count: 1
  },
  {
    warehouse_id: 4,
    warehouse_name: 'Kolkata Eastern Depot',
    total_materials: 31,
    total_stock_value: 4700000,
    capacity_utilization: 55,
    low_stock_count: 3,
    out_of_stock_count: 1
  }
];

// Stock Items (from /inventory/stock)
export const stockItems: InventoryStockWithDetails[] = [
  {
    id: 1,
    warehouse_id: 1,
    material_id: 101,
    quantity_available: 450,
    quantity_reserved: 120,
    quantity_in_transit: 80,
    reorder_point: 200,
    max_stock_level: 1000,
    min_stock_level: 100,
    last_restocked_date: '2024-12-05',
    last_issued_date: '2024-12-08',
    updated_at: '2024-12-08T10:30:00Z',
    created_at: '2024-06-15T08:00:00Z',
    material_name: 'ACSR Conductor - Moose',
    material_code: 'ACSR-M-001',
    warehouse_name: 'Delhi Central Warehouse',
    warehouse_code: 'WH-DEL-01',
    total_quantity: 650,
    stock_status: 'OK'
  },
  {
    id: 2,
    warehouse_id: 1,
    material_id: 102,
    quantity_available: 85,
    quantity_reserved: 40,
    quantity_in_transit: 0,
    reorder_point: 100,
    max_stock_level: 500,
    min_stock_level: 50,
    last_restocked_date: '2024-11-28',
    last_issued_date: '2024-12-07',
    updated_at: '2024-12-07T14:20:00Z',
    created_at: '2024-06-15T08:00:00Z',
    material_name: '400kV Composite Insulator',
    material_code: 'INS-400-C01',
    warehouse_name: 'Delhi Central Warehouse',
    warehouse_code: 'WH-DEL-01',
    total_quantity: 125,
    stock_status: 'LOW'
  },
  {
    id: 3,
    warehouse_id: 2,
    material_id: 103,
    quantity_available: 12,
    quantity_reserved: 8,
    quantity_in_transit: 4,
    reorder_point: 20,
    max_stock_level: 100,
    min_stock_level: 10,
    last_restocked_date: '2024-11-15',
    last_issued_date: '2024-12-06',
    updated_at: '2024-12-06T09:45:00Z',
    created_at: '2024-07-01T10:00:00Z',
    material_name: '400kV Power Transformer',
    material_code: 'TRF-400-PT1',
    warehouse_name: 'Mumbai Port Warehouse',
    warehouse_code: 'WH-MUM-01',
    total_quantity: 24,
    stock_status: 'CRITICAL'
  },
  {
    id: 4,
    warehouse_id: 3,
    material_id: 104,
    quantity_available: 0,
    quantity_reserved: 0,
    quantity_in_transit: 50,
    reorder_point: 30,
    max_stock_level: 200,
    min_stock_level: 15,
    last_restocked_date: '2024-10-20',
    last_issued_date: '2024-12-01',
    updated_at: '2024-12-01T16:30:00Z',
    created_at: '2024-07-15T11:00:00Z',
    material_name: 'SF6 Circuit Breaker',
    material_code: 'CB-SF6-400',
    warehouse_name: 'Bangalore Tech Hub',
    warehouse_code: 'WH-BLR-01',
    total_quantity: 50,
    stock_status: 'OUT_OF_STOCK'
  },
  {
    id: 5,
    warehouse_id: 1,
    material_id: 105,
    quantity_available: 320,
    quantity_reserved: 50,
    quantity_in_transit: 0,
    reorder_point: 100,
    max_stock_level: 400,
    min_stock_level: 50,
    last_restocked_date: '2024-12-02',
    last_issued_date: '2024-12-08',
    updated_at: '2024-12-08T11:15:00Z',
    created_at: '2024-06-20T09:00:00Z',
    material_name: 'OPGW Cable',
    material_code: 'OPGW-24F',
    warehouse_name: 'Delhi Central Warehouse',
    warehouse_code: 'WH-DEL-01',
    total_quantity: 370,
    stock_status: 'OK'
  },
  {
    id: 6,
    warehouse_id: 2,
    material_id: 106,
    quantity_available: 180,
    quantity_reserved: 20,
    quantity_in_transit: 30,
    reorder_point: 50,
    max_stock_level: 300,
    min_stock_level: 25,
    last_restocked_date: '2024-11-30',
    last_issued_date: '2024-12-05',
    updated_at: '2024-12-05T13:00:00Z',
    created_at: '2024-07-10T08:30:00Z',
    material_name: 'Tower Steel Structure - Type A',
    material_code: 'TWR-STL-A1',
    warehouse_name: 'Mumbai Port Warehouse',
    warehouse_code: 'WH-MUM-01',
    total_quantity: 230,
    stock_status: 'OK'
  },
  {
    id: 7,
    warehouse_id: 3,
    material_id: 107,
    quantity_available: 45,
    quantity_reserved: 15,
    quantity_in_transit: 10,
    reorder_point: 60,
    max_stock_level: 250,
    min_stock_level: 30,
    last_restocked_date: '2024-11-25',
    last_issued_date: '2024-12-04',
    updated_at: '2024-12-04T10:45:00Z',
    created_at: '2024-08-01T09:00:00Z',
    material_name: 'Lightning Arrester 400kV',
    material_code: 'LA-400-ZnO',
    warehouse_name: 'Bangalore Tech Hub',
    warehouse_code: 'WH-BLR-01',
    total_quantity: 70,
    stock_status: 'LOW'
  },
  {
    id: 8,
    warehouse_id: 4,
    material_id: 108,
    quantity_available: 560,
    quantity_reserved: 80,
    quantity_in_transit: 0,
    reorder_point: 150,
    max_stock_level: 600,
    min_stock_level: 75,
    last_restocked_date: '2024-12-01',
    last_issued_date: '2024-12-07',
    updated_at: '2024-12-07T15:30:00Z',
    created_at: '2024-06-25T10:30:00Z',
    material_name: 'Hardware Fittings Kit',
    material_code: 'HW-FIT-K01',
    warehouse_name: 'Kolkata Eastern Depot',
    warehouse_code: 'WH-KOL-01',
    total_quantity: 640,
    stock_status: 'OK'
  }
];

// Stock Alerts (from /inventory/alerts)
export const stockAlerts: StockAlertWithDetails[] = [
  {
    id: 1,
    alert_type: 'OUT_OF_STOCK',
    severity: 'Critical',
    warehouse_id: 3,
    material_id: 104,
    current_quantity: 0,
    threshold_quantity: 15,
    message: 'SF6 Circuit Breaker is out of stock. 50 units in transit, expected arrival: Dec 15.',
    is_resolved: false,
    resolved_at: null,
    resolved_by: null,
    alert_date: '2024-12-01T16:30:00Z',
    created_at: '2024-12-01T16:30:00Z',
    material_name: 'SF6 Circuit Breaker',
    warehouse_name: 'Bangalore Tech Hub'
  },
  {
    id: 2,
    alert_type: 'LOW_STOCK',
    severity: 'High',
    warehouse_id: 2,
    material_id: 103,
    current_quantity: 12,
    threshold_quantity: 20,
    message: '400kV Power Transformer stock critically low. Only 12 units available against min level of 10.',
    is_resolved: false,
    resolved_at: null,
    resolved_by: null,
    alert_date: '2024-12-06T09:45:00Z',
    created_at: '2024-12-06T09:45:00Z',
    material_name: '400kV Power Transformer',
    warehouse_name: 'Mumbai Port Warehouse'
  },
  {
    id: 3,
    alert_type: 'LOW_STOCK',
    severity: 'Medium',
    warehouse_id: 1,
    material_id: 102,
    current_quantity: 85,
    threshold_quantity: 100,
    message: '400kV Composite Insulator below reorder point. Current: 85, Reorder Point: 100.',
    is_resolved: false,
    resolved_at: null,
    resolved_by: null,
    alert_date: '2024-12-07T14:20:00Z',
    created_at: '2024-12-07T14:20:00Z',
    material_name: '400kV Composite Insulator',
    warehouse_name: 'Delhi Central Warehouse'
  },
  {
    id: 4,
    alert_type: 'LOW_STOCK',
    severity: 'Medium',
    warehouse_id: 3,
    material_id: 107,
    current_quantity: 45,
    threshold_quantity: 60,
    message: 'Lightning Arrester 400kV below reorder point. Procurement action recommended.',
    is_resolved: false,
    resolved_at: null,
    resolved_by: null,
    alert_date: '2024-12-04T10:45:00Z',
    created_at: '2024-12-04T10:45:00Z',
    material_name: 'Lightning Arrester 400kV',
    warehouse_name: 'Bangalore Tech Hub'
  },
  {
    id: 5,
    alert_type: 'OVERSTOCK',
    severity: 'Low',
    warehouse_id: 4,
    material_id: 108,
    current_quantity: 560,
    threshold_quantity: 600,
    message: 'Hardware Fittings Kit nearing max capacity. Consider redistribution to other warehouses.',
    is_resolved: false,
    resolved_at: null,
    resolved_by: null,
    alert_date: '2024-12-07T15:30:00Z',
    created_at: '2024-12-07T15:30:00Z',
    material_name: 'Hardware Fittings Kit',
    warehouse_name: 'Kolkata Eastern Depot'
  }
];

// Stock Reservations (from /inventory/reservations)
export const stockReservations: StockReservationWithDetails[] = [
  {
    id: 1,
    warehouse_id: 1,
    material_id: 101,
    project_id: 1,
    quantity_reserved: 120,
    quantity_issued: 45,
    required_by_date: '2024-12-20',
    status: 'Active',
    priority: 'High',
    remarks: 'Reserved for Kota-Merta 400kV stringing phase',
    reservation_date: '2024-11-15T10:00:00Z',
    created_at: '2024-11-15T10:00:00Z',
    updated_at: '2024-12-08T09:00:00Z',
    material_name: 'ACSR Conductor - Moose',
    material_code: 'ACSR-M-001',
    warehouse_name: 'Delhi Central Warehouse',
    project_name: 'LILO Kota-Merta 400kV',
    quantity_remaining: 75
  },
  {
    id: 2,
    warehouse_id: 2,
    material_id: 103,
    project_id: 2,
    quantity_reserved: 8,
    quantity_issued: 2,
    required_by_date: '2024-12-25',
    status: 'Active',
    priority: 'Critical',
    remarks: 'Transformer for substation commissioning',
    reservation_date: '2024-11-20T14:30:00Z',
    created_at: '2024-11-20T14:30:00Z',
    updated_at: '2024-12-06T11:00:00Z',
    material_name: '400kV Power Transformer',
    material_code: 'TRF-400-PT1',
    warehouse_name: 'Mumbai Port Warehouse',
    project_name: 'Beawar Substation Augmentation',
    quantity_remaining: 6
  },
  {
    id: 3,
    warehouse_id: 1,
    material_id: 105,
    project_id: 1,
    quantity_reserved: 50,
    quantity_issued: 30,
    required_by_date: '2024-12-15',
    status: 'Active',
    priority: 'Medium',
    remarks: 'OPGW for communication backbone',
    reservation_date: '2024-11-25T09:00:00Z',
    created_at: '2024-11-25T09:00:00Z',
    updated_at: '2024-12-05T16:00:00Z',
    material_name: 'OPGW Cable',
    material_code: 'OPGW-24F',
    warehouse_name: 'Delhi Central Warehouse',
    project_name: 'LILO Kota-Merta 400kV',
    quantity_remaining: 20
  },
  {
    id: 4,
    warehouse_id: 3,
    material_id: 107,
    project_id: 3,
    quantity_reserved: 15,
    quantity_issued: 0,
    required_by_date: '2025-01-10',
    status: 'Active',
    priority: 'Medium',
    remarks: 'Protection equipment for tower locations',
    reservation_date: '2024-12-01T11:00:00Z',
    created_at: '2024-12-01T11:00:00Z',
    updated_at: '2024-12-01T11:00:00Z',
    material_name: 'Lightning Arrester 400kV',
    material_code: 'LA-400-ZnO',
    warehouse_name: 'Bangalore Tech Hub',
    project_name: 'Karnataka REZ Phase-II',
    quantity_remaining: 15
  }
];

// Recent Transactions (from /inventory/transactions)
export const recentTransactions: InventoryTransactionWithDetails[] = [
  {
    id: 1,
    transaction_type: 'OUT',
    warehouse_id: 1,
    material_id: 101,
    quantity: 25,
    unit_cost: 85000,
    total_cost: 2125000,
    reference_type: 'PROJECT',
    reference_id: 'PROJ-001-ISS-045',
    project_id: 1,
    vendor_id: null,
    source_warehouse_id: null,
    remarks: 'Issued for tower stringing T-45 to T-50',
    performed_by: 'Rajesh Kumar',
    transaction_date: '2024-12-08T10:30:00Z',
    created_at: '2024-12-08T10:30:00Z',
    material_name: 'ACSR Conductor - Moose',
    warehouse_name: 'Delhi Central Warehouse',
    project_name: 'LILO Kota-Merta 400kV',
    vendor_name: null
  },
  {
    id: 2,
    transaction_type: 'IN',
    warehouse_id: 2,
    material_id: 106,
    quantity: 30,
    unit_cost: 125000,
    total_cost: 3750000,
    reference_type: 'PO',
    reference_id: 'PO-2024-0892',
    project_id: null,
    vendor_id: 5,
    source_warehouse_id: null,
    remarks: 'Received against PO-2024-0892',
    performed_by: 'System',
    transaction_date: '2024-12-07T14:00:00Z',
    created_at: '2024-12-07T14:00:00Z',
    material_name: 'Tower Steel Structure - Type A',
    warehouse_name: 'Mumbai Port Warehouse',
    project_name: null,
    vendor_name: 'Tata Steel Ltd'
  },
  {
    id: 3,
    transaction_type: 'TRANSFER_OUT',
    warehouse_id: 1,
    material_id: 108,
    quantity: 50,
    unit_cost: 15000,
    total_cost: 750000,
    reference_type: 'TRANSFER',
    reference_id: 'TRF-2024-0156',
    project_id: null,
    vendor_id: null,
    source_warehouse_id: 4,
    remarks: 'Transfer to Kolkata for project requirement',
    performed_by: 'Amit Sharma',
    transaction_date: '2024-12-06T11:30:00Z',
    created_at: '2024-12-06T11:30:00Z',
    material_name: 'Hardware Fittings Kit',
    warehouse_name: 'Delhi Central Warehouse',
    project_name: null,
    vendor_name: null
  },
  {
    id: 4,
    transaction_type: 'ADJUSTMENT',
    warehouse_id: 3,
    material_id: 102,
    quantity: -5,
    unit_cost: 45000,
    total_cost: -225000,
    reference_type: 'ADJUSTMENT',
    reference_id: 'ADJ-2024-0089',
    project_id: null,
    vendor_id: null,
    source_warehouse_id: null,
    remarks: 'Stock correction - damaged items written off',
    performed_by: 'Inventory Audit',
    transaction_date: '2024-12-05T16:00:00Z',
    created_at: '2024-12-05T16:00:00Z',
    material_name: '400kV Composite Insulator',
    warehouse_name: 'Bangalore Tech Hub',
    project_name: null,
    vendor_name: null
  }
];
