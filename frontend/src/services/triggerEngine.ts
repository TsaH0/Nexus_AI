/**
 * Frontend Trigger Engine
 * 
 * Performs all UTR, OTR, PAR calculations locally for instantaneous updates.
 * This replicates the backend trigger logic for real-time simulation without network latency.
 */

// ========== Types ==========

export interface TriggerMetrics {
  safety_stock: number;
  reorder_point: number;
  utr: number;  // Understock Trigger Ratio
  otr: number;  // Overstock Trigger Ratio
  par: number;  // Procurement Adequacy Ratio
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

export interface TriggerSimulationInput {
  item_name?: string;
  current_stock: number;
  safety_stock: number;
  reorder_point: number;
  max_stock_level?: number;
  lead_time_days?: number;
  daily_demand?: number;
  item_type?: string;
}

export interface TriggerSimulationResult {
  item_id: string;
  item_name: string;
  warehouse_code: string;
  warehouse_name: string;
  current_stock: number;
  metrics: TriggerMetrics;
  status: TriggerStatus;
  context: TriggerContext;
  simulation: {
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

// ========== Demand Estimates by Item Type ==========

const DEMAND_ESTIMATES: Record<string, number> = {
  "Transformer": 0.5,
  "Tower": 2.0,
  "Conductor": 10.0,
  "Insulator": 5.0,
  "Hardware": 20.0,
  "General": 5.0
};

// ========== Core Calculation Functions ==========

/**
 * Calculate Understock Trigger Ratio (UTR)
 * UTR = max(0, (Reorder Point - Current Stock) / Reorder Point)
 * Capped at 1.0
 */
export function calculateUTR(currentStock: number, reorderPoint: number): number {
  if (reorderPoint <= 0) return 0;
  const utr = Math.max(0, (reorderPoint - currentStock) / reorderPoint);
  return Math.min(utr, 1.0);
}

/**
 * Calculate Overstock Trigger Ratio (OTR)
 * OTR = max(0, (Current Stock - Max Stock) / Max Stock)
 */
export function calculateOTR(currentStock: number, maxStockLevel: number): number {
  if (maxStockLevel <= 0) return 0;
  return Math.max(0, (currentStock - maxStockLevel) / maxStockLevel);
}

/**
 * Calculate Procurement Adequacy Ratio (PAR)
 * PAR = Current Stock / (Reorder Point + Buffer)
 * Buffer = daily_demand * 7 days
 * Capped at 2.0
 */
export function calculatePAR(
  currentStock: number, 
  reorderPoint: number, 
  dailyDemand: number
): number {
  const buffer = dailyDemand * 7; // 7 days buffer
  const denominator = reorderPoint + buffer;
  if (denominator <= 0) return 1.0;
  const par = currentStock / denominator;
  return Math.min(par, 2.0);
}

/**
 * Calculate Days of Stock
 * Days of Stock = Current Stock / Daily Demand
 */
export function calculateDaysOfStock(currentStock: number, dailyDemand: number): number {
  if (dailyDemand <= 0) return 999;
  return currentStock / dailyDemand;
}

/**
 * Determine trigger severity based on metrics
 */
export function determineSeverity(
  utr: number,
  otr: number,
  par: number,
  daysOfStock: number,
  leadTimeDays: number
): TriggerStatus {
  // Critical Understock
  if (utr > 0.5 || daysOfStock < leadTimeDays || par < 0.3) {
    return {
      severity: 'RED',
      label: 'CRITICAL UNDERSTOCK',
      action: 'Immediate Procurement Required'
    };
  }
  
  // Overstock Warning
  if (otr > 0.5) {
    return {
      severity: 'AMBER',
      label: 'OVERSTOCK WARNING',
      action: 'Review Ordering Patterns'
    };
  }
  
  // Low Stock Warning
  if (utr > 0.3 || daysOfStock < leadTimeDays * 1.2 || par < 0.6) {
    return {
      severity: 'AMBER',
      label: 'LOW STOCK WARNING',
      action: 'Plan Procurement Soon'
    };
  }
  
  // Slight Overstock
  if (otr > 0.2) {
    return {
      severity: 'GREEN',
      label: 'SLIGHT OVERSTOCK',
      action: 'Monitor Consumption'
    };
  }
  
  // Optimal
  return {
    severity: 'GREEN',
    label: 'OPTIMAL STOCK',
    action: 'No Action Required'
  };
}

/**
 * Get daily demand estimate based on item type
 */
export function getDailyDemandEstimate(itemType?: string): number {
  if (!itemType) return DEMAND_ESTIMATES.General;
  return DEMAND_ESTIMATES[itemType] || DEMAND_ESTIMATES.General;
}

// ========== Main Simulation Function ==========

/**
 * Run complete trigger simulation locally
 * This is the main function that replicates backend logic for instantaneous results
 */
export function simulateTrigger(input: TriggerSimulationInput): TriggerSimulationResult {
  const {
    item_name = 'Simulation Target',
    current_stock,
    safety_stock,
    reorder_point,
    max_stock_level = reorder_point * 2, // Default max is 2x reorder point
    lead_time_days = 14,
    daily_demand,
    item_type
  } = input;

  // Determine daily demand
  const actualDailyDemand = daily_demand ?? getDailyDemandEstimate(item_type);

  // Calculate all metrics
  const utr = calculateUTR(current_stock, reorder_point);
  const otr = calculateOTR(current_stock, max_stock_level);
  const par = calculatePAR(current_stock, reorder_point, actualDailyDemand);
  const daysOfStock = calculateDaysOfStock(current_stock, actualDailyDemand);

  // Determine severity and status
  const status = determineSeverity(utr, otr, par, daysOfStock, lead_time_days);

  // Build result
  return {
    item_id: 'SIM-001',
    item_name,
    warehouse_code: 'SIM-WH',
    warehouse_name: 'Simulation Warehouse',
    current_stock,
    metrics: {
      safety_stock: round(safety_stock, 2),
      reorder_point: round(reorder_point, 2),
      utr: round(utr, 4),
      otr: round(otr, 4),
      par: round(par, 4)
    },
    status,
    context: {
      daily_demand: round(actualDailyDemand, 2),
      lead_time_days,
      days_of_stock: round(daysOfStock, 2),
      nearby_substations: 0,
      demand_multiplier: 1.0
    },
    simulation: {
      is_simulation: true,
      input: {
        item_name,
        current_stock,
        safety_stock,
        reorder_point,
        max_stock_level,
        lead_time_days,
        daily_demand_used: actualDailyDemand
      }
    }
  };
}

// ========== Utility Functions ==========

function round(value: number, decimals: number): number {
  const factor = Math.pow(10, decimals);
  return Math.round(value * factor) / factor;
}

// ========== Quick Metric Calculation (for inline use) ==========

export interface QuickMetrics {
  utr: number;
  otr: number;
  par: number;
  daysOfStock: number;
  severity: 'GREEN' | 'AMBER' | 'RED';
  label: string;
  action: string;
}

/**
 * Quick calculation for inline usage
 * Returns all key metrics in a single call
 */
export function calculateQuickMetrics(
  currentStock: number,
  _safetyStock: number,  // Kept for API compatibility, may be used in future enhancements
  reorderPoint: number,
  maxStockLevel?: number,
  dailyDemand: number = 5,
  leadTimeDays: number = 14
): QuickMetrics {
  const actualMaxStock = maxStockLevel ?? reorderPoint * 2;
  
  const utr = calculateUTR(currentStock, reorderPoint);
  const otr = calculateOTR(currentStock, actualMaxStock);
  const par = calculatePAR(currentStock, reorderPoint, dailyDemand);
  const daysOfStock = calculateDaysOfStock(currentStock, dailyDemand);
  
  const status = determineSeverity(utr, otr, par, daysOfStock, leadTimeDays);
  
  return {
    utr: round(utr, 4),
    otr: round(otr, 4),
    par: round(par, 4),
    daysOfStock: round(daysOfStock, 2),
    severity: status.severity,
    label: status.label,
    action: status.action
  };
}

export default {
  simulateTrigger,
  calculateUTR,
  calculateOTR,
  calculatePAR,
  calculateDaysOfStock,
  determineSeverity,
  calculateQuickMetrics,
  getDailyDemandEstimate
};
