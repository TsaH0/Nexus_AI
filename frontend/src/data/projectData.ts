// ==============================================================================
// PROJECT MASTER DATA
// ==============================================================================

export const sampleProject = {
  // Basic Project Information
  id: "PROJ-RAJ-2024-001",
  name: "LILO of Kota-Merta 400kV D/C at Beawar",
  fullName: "LILO of Kota – Merta 400 kV D/c at Beawar (Transmission System for Evacuation of Power from REZ in Rajasthan (20GW) under Phase-III Part F)",
  
  // Project Classification
  projectType: "Transmission Line",
  category: "ISTS", // Inter-State Transmission System
  developer: "Sterlite",
  developerType: "Private Developer",
  state: "Rajasthan",
  
  // Technical Specifications
  specifications: {
    circuitType: "D/C", // Double Circuit
    voltageLevel: 400, // kV
    totalLineLength: 66, // ckm (circuit kilometers)
    totalTowerLocations: 90,
    conductorType: "ACSR Moose",
    earthWireType: "OPGW",
    insulatorType: "Composite Long Rod",
  },
  
  // Timeline
  timeline: {
    targetDate: "2026-01-31",
    anticipatedCOD: "2026-03-31", // Commercial Operation Date
    projectStartDate: "2024-06-01",
    currentPhase: "Construction",
    delayDays: 60,
  },
};

// ==============================================================================
// PROGRESS METRICS
// ==============================================================================

export const progressMetrics = {
  // Physical Progress
  foundation: {
    total: 90,
    completed: 86,
    inProgress: 3,
    pending: 1,
    percentage: 95.56,
    trend: "up",
    weeklyProgress: 2,
  },
  
  towerErection: {
    total: 90,
    completed: 78,
    inProgress: 5,
    pending: 7,
    percentage: 86.67,
    trend: "up",
    weeklyProgress: 3,
  },
  
  stringing: {
    totalCkm: 66,
    completedCkm: 26,
    inProgressCkm: 8,
    pendingCkm: 32,
    percentage: 39.39,
    trend: "up",
    weeklyProgress: 2.5,
  },
  
  // Overall Progress
  overall: {
    percentage: 73.87,
    status: "On Track with Delays",
    healthScore: 72,
    riskLevel: "Medium",
  },
  
  // Monthly Progress Trend
  monthlyTrend: [
    { month: "Jul 2024", foundation: 45, tower: 30, stringing: 5 },
    { month: "Aug 2024", foundation: 58, tower: 42, stringing: 8 },
    { month: "Sep 2024", foundation: 70, tower: 55, stringing: 12 },
    { month: "Oct 2024", foundation: 78, tower: 65, stringing: 18 },
    { month: "Nov 2024", foundation: 84, tower: 72, stringing: 22 },
    { month: "Dec 2024", foundation: 86, tower: 78, stringing: 26 },
  ],
};

// ==============================================================================
// INVENTORY REQUIREMENTS (BOM - Bill of Materials)
// ==============================================================================

export const inventoryRequirements = {
  summary: {
    totalItems: 156,
    totalValue: 285000000, // ₹28.5 Crores
    criticalItems: 12,
    lowStockItems: 8,
    onOrderItems: 23,
  },
  
  // Critical Items Alert
  criticalAlerts: [
    {
      materialId: "MAT-003",
      materialName: "400kV D/C Tower - Type C (Dead End)",
      alertType: "Low Stock",
      currentStock: 8,
      required: 12,
      shortfall: 4,
      expectedDelivery: "2025-01-15",
      priority: "High",
    },
    {
      materialId: "MAT-008",
      materialName: "Tension Clamp Assembly",
      alertType: "Low Stock",
      currentStock: 180,
      required: 288,
      shortfall: 108,
      expectedDelivery: "2024-12-28",
      priority: "Medium",
    },
  ],
};

// ==============================================================================
// DELAY ANALYSIS
// ==============================================================================

export const delayAnalysis = {
  totalDelayDays: 60,
  delayReasons: [
    {
      id: 1,
      category: "Regulatory",
      description: "PLC Approval pending with M/s Shree Cement",
      duration: "10+ months",
      impact: "Critical",
      status: "Pending",
      affectedTowers: [85, 86, 87, 88],
    },
    {
      id: 2,
      category: "Technical Dependency",
      description: "Delay in replacement of existing earth wire with OPGW",
      duration: "3 months",
      impact: "High",
      status: "In Progress",
      affectedTowers: [1, 2, 3, 4, 5],
    },
  ],
};

// ==============================================================================
// FINANCIAL METRICS
// ==============================================================================

export const financialMetrics = {
  budget: {
    sanctioned: 320000000, // ₹32 Crores
    spent: 245000000,
    remaining: 75000000,
    utilizationPercentage: 76.56,
  },
};

// ==============================================================================
// DASHBOARD SUMMARY
// ==============================================================================

export const dashboardSummary = {
  overallProgress: 73.87,
  foundation: { completed: 86, total: 90, percentage: 95.56 },
  towerErection: { completed: 78, total: 90, percentage: 86.67 },
  stringing: { completed: 26, total: 66, percentage: 39.39 },
  budgetUtilization: 76.56,
  materialReadiness: 87.5,
  lowStockItems: 8,
  criticalIssues: 2,
  daysToCOD: 113,
};

export default {
  project: sampleProject,
  progress: progressMetrics,
  inventory: inventoryRequirements,
  delays: delayAnalysis,
  financials: financialMetrics,
  dashboard: dashboardSummary,
};
