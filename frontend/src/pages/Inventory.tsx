import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { 
  Warehouse, 
  Package, 
  AlertTriangle, 
  TrendingDown,
  TrendingUp,
  ArrowRightLeft,
  Clock,
  AlertCircle,
  FileText,
  Building2,
  PieChart,
  Loader2,
  RefreshCw,
  Zap
} from 'lucide-react';
import { 
  warehouseSummaries as staticWarehouseSummaries,
  stockItems as staticStockItems, 
  stockAlerts as staticStockAlerts,
  stockReservations as staticStockReservations,
  recentTransactions as staticRecentTransactions
} from '../data/inventoryData';
import type {
  WarehouseInventorySummary,
  InventoryStockWithDetails,
  StockAlertWithDetails,
  StockReservationWithDetails,
  InventoryTransactionWithDetails,
  Material,
  InventoryTriggerItem
} from '../services/inventoryApi';
import inventoryApi from '../services/inventoryApi';
import { simulateTrigger as localSimulateTrigger } from '../services/triggerEngine';
import type { TriggerSimulationResult } from '../services/triggerEngine';


// Simple SVG Pie Chart Component
const SimplePieChart = ({ 
  data, 
  size = 120,
}: { 
  data: { label: string; value: number; color: string }[];
  size?: number;
}) => {
  const total = data.reduce((sum, item) => sum + item.value, 0);
  if (total === 0) return null;
  
  let currentAngle = 0;
  const center = size / 2;
  const radius = size / 2 - 10;
  
  const createArcPath = (startAngle: number, endAngle: number) => {
    const start = {
      x: center + radius * Math.cos(startAngle),
      y: center + radius * Math.sin(startAngle)
    };
    const end = {
      x: center + radius * Math.cos(endAngle),
      y: center + radius * Math.sin(endAngle)
    };
    const largeArcFlag = endAngle - startAngle > Math.PI ? 1 : 0;
    
    return `M ${center} ${center} L ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${end.x} ${end.y} Z`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        {data.map((item, index) => {
          const angle = (item.value / total) * 2 * Math.PI;
          const startAngle = currentAngle;
          const endAngle = currentAngle + angle;
          currentAngle = endAngle;
          
          return (
            <motion.path
              key={index}
              d={createArcPath(startAngle, endAngle)}
              fill={item.color}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.3 + index * 0.1 }}
              style={{ cursor: 'pointer' }}
            />
          );
        })}
        <circle cx={center} cy={center} r={radius * 0.5} fill="rgba(10,10,10,0.95)" />
      </svg>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', width: '100%' }}>
        {data.map((item, index) => (
          <div key={index} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '10px', height: '10px', background: item.color, borderRadius: '2px' }} />
              <span style={{ opacity: 0.7 }}>{item.label}</span>
            </div>
            <span style={{ fontWeight: '600' }}>{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const Inventory = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const targetName = searchParams.get('target');

  // State for API data
  const [warehouseSummaries, setWarehouseSummaries] = useState<WarehouseInventorySummary[]>(staticWarehouseSummaries);
  const [stockItems, setStockItems] = useState<InventoryStockWithDetails[]>(staticStockItems);
  const [stockAlerts, setStockAlerts] = useState<StockAlertWithDetails[]>(staticStockAlerts);
  const [stockReservations, setStockReservations] = useState<StockReservationWithDetails[]>(staticStockReservations);
  const [recentTransactions, setRecentTransactions] = useState<InventoryTransactionWithDetails[]>(staticRecentTransactions);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [isLive, setIsLive] = useState(false);
  const [_triggerItems, setTriggerItems] = useState<InventoryTriggerItem[]>([]);
  const [viewMode, setViewMode] = useState<'dashboard' | 'triggers'>('dashboard');
  
  // Simplified Simulation State - just item selection and stock slider
  const [adjWarehouseId, setAdjWarehouseId] = useState<number | ''>('');
  const [adjMaterialId, setAdjMaterialId] = useState<number | ''>('');
  const [simulatedStock, setSimulatedStock] = useState<number>(0); // The simulated stock level
  const [simResult, setSimResult] = useState<TriggerSimulationResult | null>(null);
  const [isAdjusting, setIsAdjusting] = useState(false);

  // Derived state for selection
  const availableMaterials = adjWarehouseId 
    ? stockItems.filter(s => s.warehouse_id === Number(adjWarehouseId))
    : [];
    
  const selectedStockItem = adjWarehouseId && adjMaterialId
    ? stockItems.find(s => s.warehouse_id === Number(adjWarehouseId) && s.material_id === Number(adjMaterialId))
    : null;



  // Handle permanent stock adjustment submission
  const handleAdjustmentSubmit = async () => {
    if (!selectedStockItem) return;
    
    const stockDelta = simulatedStock - selectedStockItem.quantity_available;
    if (stockDelta === 0) return;
    
    setIsAdjusting(true);
    try {
        // Use update-and-alert endpoint
        await inventoryApi.updateAndAlert({
            warehouse_id: selectedStockItem.warehouse_id,
            material_id: selectedStockItem.material_id,
            new_quantity: Math.abs(stockDelta),
            operation: stockDelta > 0 ? 'ADD' : 'SUBTRACT',
            remarks: 'Manual adjustment via Trigger Simulator',
            utr_email_threshold: 0.20,
            utr_whatsapp_threshold: 0.50,
            otr_email_threshold: 0.50,
            otr_whatsapp_threshold: 1.0,
            email_recipient: "f20231128@hyderabad.bits-pilani.ac.in",
            generate_pdf: true
        });

        // Refresh data
        await fetchData();
    } catch (error) {
        console.error("Adjustment failed", error);
        alert('Failed to update stock');
    } finally {
        setIsAdjusting(false);
    }
  };

  // When an item is selected, initialize simulated stock to actual stock
  useEffect(() => {
    if (selectedStockItem) {
      setSimulatedStock(selectedStockItem.quantity_available);
    }
  }, [selectedStockItem]);

  // Run trigger simulation whenever simulated stock or selected item changes
  // Uses LOCAL frontend calculation for INSTANTANEOUS updates!
  useEffect(() => {
    if (viewMode !== 'triggers' || !selectedStockItem) {
      setSimResult(null);
      return;
    }
    
    // Use the item's REAL thresholds from the database
    const reorderPoint = selectedStockItem.reorder_point || 100;
    const safetyStock = selectedStockItem.min_stock_level || 50;
    const maxStock = selectedStockItem.max_stock_level || reorderPoint * 2;
    
    // Run simulation locally - instant results!
    const result = localSimulateTrigger({
      current_stock: simulatedStock,
      safety_stock: safetyStock,
      reorder_point: reorderPoint,
      max_stock_level: maxStock,
      item_name: selectedStockItem.material_name,
      lead_time_days: 14
    });
    
    setSimResult(result);
  }, [simulatedStock, selectedStockItem, viewMode]);

  // Fetch data from API
  const fetchData = async () => {
    setLoading(true);
    
    try {
      const [warehouses, stock, alerts, reservations, transactions, mats, triggers] = await Promise.all([
        inventoryApi.getWarehouseSummaries(),
        inventoryApi.getStockItems(),
        inventoryApi.getAlerts(),
        inventoryApi.getReservations(),
        inventoryApi.getTransactions(),
        inventoryApi.getMaterials(),
        inventoryApi.getInventoryTriggers()
      ]);
      
      setWarehouseSummaries(warehouses);
      setStockItems(stock);
      setStockAlerts(alerts);
      setStockReservations(reservations);
      setRecentTransactions(transactions);
      setMaterials(mats);
      setTriggerItems(triggers.data || []);
      setIsLive(true);
    } catch (err) {
      console.log('API not available, using static data');
      // Keep static data as fallback
      setWarehouseSummaries(staticWarehouseSummaries);
      setStockItems(staticStockItems);
      setStockAlerts(staticStockAlerts);
      setStockReservations(staticStockReservations);
      setRecentTransactions(staticRecentTransactions);
      setMaterials([]);
      setIsLive(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  };

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'CRITICAL':
      case 'Critical':
      case 'OUT_OF_STOCK': return '#ef4444';
      case 'LOW':
      case 'LOW_STOCK':
      case 'High': return '#fb923c';
      case 'OK':
      case 'Medium': return '#4ade80';
      case 'OVERSTOCK':
      case 'Low': return '#60a5fa';
      default: return '#ffffff';
    }
  };

  const getTransactionIcon = (type: string) => {
    switch (type) {
      case 'IN': return <TrendingUp size={14} color="#4ade80" />;
      case 'OUT': return <TrendingDown size={14} color="#fb923c" />;
      case 'TRANSFER_OUT':
      case 'TRANSFER_IN': return <ArrowRightLeft size={14} color="#60a5fa" />;
      case 'ADJUSTMENT': return <FileText size={14} color="#a78bfa" />;
      default: return <Package size={14} />;
    }
  };

  const formatCurrency = (value: number) => {
    if (value >= 10000000) return `₹${(value / 10000000).toFixed(2)} Cr`;
    if (value >= 100000) return `₹${(value / 100000).toFixed(2)} L`;
    return `₹${value.toLocaleString()}`;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-IN', { 
      day: '2-digit', 
      month: 'short',
      year: 'numeric'
    });
  };

  const getWarehouseStockItems = (warehouseId: number) => {
    return stockItems.filter(s => s.warehouse_id === warehouseId);
  };

  const getWarehouseAlerts = (warehouseId: number) => {
    return stockAlerts.filter(a => a.warehouse_id === warehouseId && !a.is_resolved);
  };

  const getWarehouseReservations = (warehouseId: number) => {
    return stockReservations.filter(r => r.warehouse_id === warehouseId && r.status === 'Active');
  };

  const getStockStatusDistribution = (warehouseId: number) => {
    const items = getWarehouseStockItems(warehouseId);
    return [
      { label: 'OK', value: items.filter(i => i.stock_status === 'OK').length, color: '#4ade80' },
      { label: 'Low Stock', value: items.filter(i => i.stock_status === 'LOW').length, color: '#fb923c' },
      { label: 'Critical', value: items.filter(i => i.stock_status === 'CRITICAL').length, color: '#ef4444' },
      { label: 'Out of Stock', value: items.filter(i => i.stock_status === 'OUT_OF_STOCK').length, color: '#a855f7' },
    ].filter(d => d.value > 0);
  };

  // Get value distribution by material for a warehouse (using unit prices)
  const getValueDistribution = (warehouseId: number) => {
    const items = getWarehouseStockItems(warehouseId);
    const colors = ['#8B5CF6', '#06B6D4', '#F59E0B', '#EF4444', '#10B981', '#6366F1', '#EC4899', '#84CC16', '#F97316', '#14B8A6'];
    
    // Create a map of material_id to unit_price
    const priceMap = new Map<number, number>();
    materials.forEach(m => priceMap.set(m.id, m.unit_price));
    
    // Calculate value for each item and get top items
    const itemsWithValue = items.map(item => ({
      ...item,
      value: item.total_quantity * (priceMap.get(item.material_id) || 0)
    }))
    .filter(item => item.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 6); // Top 6 items

    return itemsWithValue.map((item, idx) => ({
      label: item.material_name.split(' ').slice(0, 2).join(' '),
      value: Math.round(item.value / 100000), // In lakhs
      color: colors[idx % colors.length]
    }));
  };

  if (loading) {
    return (
      <div style={{ 
        height: 'calc(100vh - 62px)', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        flexDirection: 'column',
        gap: '16px'
      }}>
        <Loader2 size={40} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
        <div style={{ opacity: 0.7 }}>Loading inventory data...</div>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  // Filter warehouses based on target param
  const filteredWarehouses = targetName
    ? warehouseSummaries.filter(w => w.warehouse_name.toLowerCase() === targetName.toLowerCase())
    : warehouseSummaries;

  return (
    <div style={{ padding: '40px', maxWidth: '1600px', margin: '0 auto', width: '100%' }}>
      {/* Header */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ marginBottom: '30px' }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
          <h2 style={{ fontSize: '2rem', fontWeight: 'bold', margin: 0, display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Warehouse size={32} />
            Inventory Management
          </h2>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            {/* Connection Status */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 12px',
              border: `1px solid ${isLive ? '#4ade80' : '#fb923c'}`,
              background: isLive ? 'rgba(74, 222, 128, 0.1)' : 'rgba(251, 146, 60, 0.1)',
              fontSize: '0.75rem'
            }}>
              <div style={{ 
                width: '8px', 
                height: '8px', 
                borderRadius: '50%', 
                background: isLive ? '#4ade80' : '#fb923c',
                animation: isLive ? 'pulse 2s infinite' : 'none'
              }} />
              <span style={{ color: isLive ? '#4ade80' : '#fb923c' }}>
                {isLive ? 'LIVE' : 'OFFLINE'}
              </span>
            </div>
            
            {/* Refresh Button */}
            <button
              onClick={fetchData}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                border: '1px solid rgba(255,255,255,0.3)',
                background: 'transparent',
                color: 'white',
                cursor: 'pointer',
                fontSize: '0.75rem'
              }}
            >
              <RefreshCw size={14} />
              Refresh
            </button>
            
            {stockAlerts.filter(a => !a.is_resolved).length > 0 && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 16px',
                  border: '1px solid #ef4444',
                  background: 'rgba(239, 68, 68, 0.1)',
                  fontSize: '0.85rem'
                }}
              >
                <AlertTriangle size={16} color="#ef4444" />
                <span style={{ color: '#ef4444', fontWeight: '600' }}>
                  {stockAlerts.filter(a => !a.is_resolved).length} ACTIVE ALERTS
                </span>
              </motion.div>
            )}
          </div>
        </div>
        <div style={{ fontSize: '0.9rem', opacity: 0.7 }}>
          Individual warehouse inventory status, stock distribution, and active problems
        </div>
        
        {targetName && (
            <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ 
                    padding: '6px 12px', 
                    background: 'rgba(59, 130, 246, 0.2)', 
                    border: '1px solid #3b82f6', 
                    borderRadius: '4px',
                    fontSize: '0.85rem',
                    color: '#60a5fa',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                }}>
                    Filtered by: <strong>{targetName}</strong>
                    <button 
                        onClick={() => setSearchParams({})}
                        style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', opacity: 0.7, padding: 0 }}
                    >
                        ✕
                    </button>
                </div>
            </div>
        )}

        <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }`}</style>
      </motion.div>



      {/* View Switcher */}
      <div style={{ display: 'flex', gap: '4px', background: 'rgba(255,255,255,0.05)', padding: '4px', borderRadius: '8px', width: 'fit-content', marginBottom: '24px' }}>
        <button
          onClick={() => setViewMode('dashboard')}
          style={{
            padding: '8px 24px',
            borderRadius: '6px',
            border: 'none',
            background: viewMode === 'dashboard' ? 'rgba(255,255,255,0.1)' : 'transparent',
            color: viewMode === 'dashboard' ? 'white' : 'rgba(255,255,255,0.6)',
            fontWeight: viewMode === 'dashboard' ? '600' : '400',
            cursor: 'pointer',
            transition: 'all 0.2s'
          }}
        >
          Overview
        </button>
        <button
          onClick={() => setViewMode('triggers')}
          style={{
            padding: '8px 24px',
            borderRadius: '6px',
            border: 'none',
            background: viewMode === 'triggers' ? 'rgba(255,255,255,0.1)' : 'transparent',
            color: viewMode === 'triggers' ? '#f472b6' : 'rgba(255,255,255,0.6)',
            fontWeight: viewMode === 'triggers' ? '600' : '400',
            cursor: 'pointer',
            transition: 'all 0.2s',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Zap size={16} />
          Trigger Engine
        </button>
      </div>

      {viewMode === 'dashboard' ? (
      <>
      {/* Individual Warehouse Cards */}
      <motion.div 
        variants={container}
        initial="hidden"
        animate="show"
        style={{ display: 'flex', flexDirection: 'column', gap: '24px', marginBottom: '30px' }}
      >

        {filteredWarehouses.length === 0 && targetName && (
            <div style={{ padding: '40px', textAlign: 'center', opacity: 0.7 }}>
                No inventory found for references matching "{targetName}"
            </div>
        )}
        {filteredWarehouses.map((warehouse) => {
          const warehouseStock = getWarehouseStockItems(warehouse.warehouse_id);
          const warehouseAlerts = getWarehouseAlerts(warehouse.warehouse_id);
          const warehouseReservations = getWarehouseReservations(warehouse.warehouse_id);
          const stockDistribution = getStockStatusDistribution(warehouse.warehouse_id);
          
          return (
            <motion.div 
              key={warehouse.warehouse_id}
              variants={item}
              style={{ 
                border: '1px solid rgba(255,255,255,0.2)', 
                padding: '30px', 
                background: 'rgba(10,10,10,0.8)',
                backdropFilter: 'blur(10px)'
              }}
            >
              {/* Warehouse Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '24px' }}>
                <div>
                  <h3 style={{ margin: '0 0 8px', fontSize: '1.3rem', fontWeight: '500', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Building2 size={24} color="#60a5fa" />
                    {warehouse.warehouse_name}
                  </h3>
                  <div style={{ fontSize: '0.85rem', opacity: 0.6 }}>
                    {warehouse.total_materials} materials tracked
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#4ade80' }}>
                    {formatCurrency(warehouse.total_stock_value)}
                  </div>
                  <div style={{ fontSize: '0.75rem', opacity: 0.5, marginTop: '4px' }}>Total Stock Value</div>
                </div>
              </div>

              {/* Main Content Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '30px' }}>
                
                {/* Pie Charts Section */}
                <div style={{ 
                  padding: '20px', 
                  background: 'rgba(0,0,0,0.3)', 
                  border: '1px solid rgba(255,255,255,0.1)',
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '20px'
                }}>
                  {/* Stock Status Pie Chart */}
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '16px' }}>
                      <PieChart size={14} color="#60a5fa" />
                      <span style={{ fontSize: '0.75rem', opacity: 0.7, letterSpacing: '0.5px' }}>STOCK STATUS</span>
                    </div>
                    {stockDistribution.length > 0 ? (
                      <SimplePieChart data={stockDistribution} size={90} />
                    ) : (
                      <div style={{ opacity: 0.5, fontSize: '0.8rem', padding: '30px 0' }}>No data</div>
                    )}
                  </div>
                  
                  {/* Value Distribution Pie Chart */}
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '16px' }}>
                      <PieChart size={14} color="#8B5CF6" />
                      <span style={{ fontSize: '0.75rem', opacity: 0.7, letterSpacing: '0.5px' }}>VALUE (₹L)</span>
                    </div>
                    {getValueDistribution(warehouse.warehouse_id).length > 0 ? (
                      <SimplePieChart data={getValueDistribution(warehouse.warehouse_id)} size={90} />
                    ) : (
                      <div style={{ opacity: 0.5, fontSize: '0.8rem', padding: '30px 0', textAlign: 'center' }}>
                        {materials.length === 0 ? 'No price data' : 'No stock'}
                      </div>
                    )}
                  </div>
                </div>

                {/* Quick Stats */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <h4 style={{ margin: '0 0 8px', fontSize: '0.85rem', opacity: 0.7, letterSpacing: '1px' }}>STATISTICS</h4>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div style={{ 
                      padding: '16px', 
                      background: warehouse.low_stock_count > 0 ? 'rgba(251, 146, 60, 0.1)' : 'rgba(0,0,0,0.3)', 
                      border: `1px solid ${warehouse.low_stock_count > 0 ? 'rgba(251, 146, 60, 0.3)' : 'rgba(255,255,255,0.1)'}`,
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#fb923c' }}>
                        {warehouse.low_stock_count}
                      </div>
                      <div style={{ fontSize: '0.7rem', opacity: 0.7, marginTop: '4px' }}>Low Stock</div>
                    </div>
                    <div style={{ 
                      padding: '16px', 
                      background: warehouse.out_of_stock_count > 0 ? 'rgba(239, 68, 68, 0.1)' : 'rgba(0,0,0,0.3)', 
                      border: `1px solid ${warehouse.out_of_stock_count > 0 ? 'rgba(239, 68, 68, 0.3)' : 'rgba(255,255,255,0.1)'}`,
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#ef4444' }}>
                        {warehouse.out_of_stock_count}
                      </div>
                      <div style={{ fontSize: '0.7rem', opacity: 0.7, marginTop: '4px' }}>Out of Stock</div>
                    </div>
                  </div>

                  <div style={{ 
                    padding: '16px', 
                    background: 'rgba(96, 165, 250, 0.1)', 
                    border: '1px solid rgba(96, 165, 250, 0.3)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Clock size={16} color="#60a5fa" />
                      <span style={{ fontSize: '0.85rem', opacity: 0.7 }}>Active Reservations</span>
                    </div>
                    <span style={{ fontSize: '1.2rem', fontWeight: '600', color: '#60a5fa' }}>
                      {warehouseReservations.length}
                    </span>
                  </div>
                </div>

                {/* Problems / Alerts Section */}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <h4 style={{ margin: 0, fontSize: '0.85rem', opacity: 0.7, letterSpacing: '1px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <AlertCircle size={16} color="#ef4444" />
                      ACTIVE PROBLEMS
                    </h4>
                    {warehouseAlerts.length > 0 && (
                      <span style={{
                        padding: '2px 8px',
                        background: 'rgba(239, 68, 68, 0.2)',
                        border: '1px solid #ef4444',
                        fontSize: '0.7rem',
                        color: '#ef4444',
                        fontWeight: '600'
                      }}>
                        {warehouseAlerts.length}
                      </span>
                    )}
                  </div>
                  
                  {warehouseAlerts.length > 0 ? (
                    <div style={{ 
                      display: 'flex', 
                      flexDirection: 'column', 
                      gap: '8px',
                      maxHeight: '200px',
                      overflowY: 'auto',
                      paddingRight: '8px'
                    }}>
                      {warehouseAlerts.map((alert) => (
                        <div 
                          key={alert.id}
                          style={{
                            padding: '12px',
                            background: 'rgba(239, 68, 68, 0.05)',
                            border: '1px solid rgba(239, 68, 68, 0.2)',
                            borderLeft: `3px solid ${getStatusColor(alert.severity)}`
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '6px' }}>
                            <span style={{ fontSize: '0.85rem', fontWeight: '600' }}>{alert.material_name}</span>
                            <span style={{
                              padding: '2px 6px',
                              background: `${getStatusColor(alert.severity)}20`,
                              color: getStatusColor(alert.severity),
                              fontSize: '0.6rem',
                              fontWeight: '600'
                            }}>
                              {alert.severity.toUpperCase()}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.75rem', opacity: 0.7, marginBottom: '6px' }}>{alert.message}</div>
                          <div style={{ fontSize: '0.7rem', opacity: 0.5 }}>
                            Current: {alert.current_quantity} • Threshold: {alert.threshold_quantity}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ 
                      padding: '40px 20px', 
                      background: 'rgba(74, 222, 128, 0.05)', 
                      border: '1px solid rgba(74, 222, 128, 0.2)',
                      textAlign: 'center'
                    }}>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                        <div style={{ 
                          width: '40px', 
                          height: '40px', 
                          borderRadius: '50%', 
                          background: 'rgba(74, 222, 128, 0.2)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}>
                          <span style={{ fontSize: '1.2rem' }}>✓</span>
                        </div>
                        <span style={{ fontSize: '0.85rem', color: '#4ade80' }}>No Active Problems</span>
                        <span style={{ fontSize: '0.75rem', opacity: 0.5 }}>All stock levels are healthy</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Stock Items Table for this Warehouse */}
              {warehouseStock.length > 0 && (
                <div style={{ marginTop: '24px', paddingTop: '24px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                  <h4 style={{ margin: '0 0 16px', fontSize: '0.85rem', opacity: 0.7, letterSpacing: '1px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Package size={16} />
                    STOCK ITEMS ({warehouseStock.length})
                  </h4>
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.15)' }}>
                          <th style={{ padding: '10px 12px', textAlign: 'left', fontSize: '0.7rem', opacity: 0.6, letterSpacing: '0.5px' }}>MATERIAL</th>
                          <th style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.7rem', opacity: 0.6, letterSpacing: '0.5px' }}>AVAILABLE</th>
                          <th style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.7rem', opacity: 0.6, letterSpacing: '0.5px' }}>RESERVED</th>
                          <th style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.7rem', opacity: 0.6, letterSpacing: '0.5px' }}>IN TRANSIT</th>
                          <th style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.7rem', opacity: 0.6, letterSpacing: '0.5px' }}>TOTAL</th>
                          <th style={{ padding: '10px 12px', textAlign: 'center', fontSize: '0.7rem', opacity: 0.6, letterSpacing: '0.5px' }}>STATUS</th>
                        </tr>
                      </thead>
                      <tbody>
                        {warehouseStock.map((stock) => (
                          <tr key={stock.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                            <td style={{ padding: '12px' }}>
                              <div style={{ fontSize: '0.85rem', fontWeight: '500' }}>{stock.material_name}</div>
                              <div style={{ fontSize: '0.7rem', opacity: 0.5 }}>{stock.material_code}</div>
                            </td>
                            <td style={{ padding: '12px', textAlign: 'right', fontSize: '0.85rem', fontWeight: '500' }}>
                              {stock.quantity_available.toLocaleString()}
                            </td>
                            <td style={{ padding: '12px', textAlign: 'right', fontSize: '0.8rem', opacity: 0.7 }}>
                              {stock.quantity_reserved.toLocaleString()}
                            </td>
                            <td style={{ padding: '12px', textAlign: 'right', fontSize: '0.8rem', opacity: 0.7 }}>
                              {stock.quantity_in_transit.toLocaleString()}
                            </td>
                            <td style={{ padding: '12px', textAlign: 'right', fontSize: '0.85rem', fontWeight: '600' }}>
                              {stock.total_quantity.toLocaleString()}
                            </td>
                            <td style={{ padding: '12px', textAlign: 'center' }}>
                              <span style={{
                                padding: '3px 8px',
                                background: `${getStatusColor(stock.stock_status)}15`,
                                border: `1px solid ${getStatusColor(stock.stock_status)}`,
                                color: getStatusColor(stock.stock_status),
                                fontSize: '0.65rem',
                                letterSpacing: '0.5px',
                                fontWeight: '600'
                              }}>
                                {stock.stock_status.replace('_', ' ')}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </motion.div>
          );
        })}
      </motion.div>

      {/* Recent Transactions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
        style={{
          border: '1px solid rgba(255,255,255,0.2)',
          padding: '30px',
          background: 'rgba(10,10,10,0.8)',
          backdropFilter: 'blur(10px)'
        }}
      >
        <h3 style={{ margin: '0 0 20px', fontSize: '1.1rem', letterSpacing: '1px', opacity: 0.9, display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ArrowRightLeft size={20} />
          RECENT TRANSACTIONS
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {recentTransactions.map((transaction, idx) => (
            <motion.div
              key={transaction.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 1.0 + idx * 0.05 }}
              style={{
                padding: '16px 20px',
                background: 'rgba(0,0,0,0.4)',
                border: '1px solid rgba(255,255,255,0.1)',
                display: 'flex',
                alignItems: 'center',
                gap: '20px'
              }}
            >
              <div style={{ 
                width: '36px', 
                height: '36px', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.1)'
              }}>
                {getTransactionIcon(transaction.transaction_type)}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                  <span style={{ fontSize: '0.9rem', fontWeight: '600' }}>{transaction.material_name}</span>
                  <span style={{
                    padding: '2px 8px',
                    background: transaction.transaction_type === 'IN' ? 'rgba(74, 222, 128, 0.2)' : 
                               transaction.transaction_type === 'OUT' ? 'rgba(251, 146, 60, 0.2)' :
                               'rgba(96, 165, 250, 0.2)',
                    color: transaction.transaction_type === 'IN' ? '#4ade80' : 
                           transaction.transaction_type === 'OUT' ? '#fb923c' :
                           '#60a5fa',
                    fontSize: '0.65rem',
                    fontWeight: '600'
                  }}>
                    {transaction.transaction_type.replace('_', ' ')}
                  </span>
                </div>
                <div style={{ fontSize: '0.8rem', opacity: 0.6 }}>
                  {transaction.warehouse_name} • {transaction.remarks}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ 
                  fontSize: '1rem', 
                  fontWeight: '600',
                  color: transaction.transaction_type === 'IN' ? '#4ade80' : 
                         transaction.quantity < 0 ? '#ef4444' : '#fb923c'
                }}>
                  {transaction.transaction_type === 'IN' ? '+' : ''}{transaction.quantity.toLocaleString()}
                </div>
                <div style={{ fontSize: '0.75rem', opacity: 0.5 }}>{formatDate(transaction.transaction_date)}</div>
              </div>
              <div style={{ textAlign: 'right', minWidth: '100px' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: '500' }}>{formatCurrency(Math.abs(transaction.total_cost))}</div>
                <div style={{ fontSize: '0.7rem', opacity: 0.5 }}>{transaction.performed_by}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>
      </>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
            {/* Simplified Trigger Engine */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                    padding: '24px',
                    background: 'rgba(59, 130, 246, 0.05)',
                    border: '1px solid rgba(59, 130, 246, 0.2)',
                    borderRadius: '8px'
                }}
            >
                <h3 style={{ margin: '0 0 20px', fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Zap size={20} color="#f472b6" />
                    Real-Time Understock & Overstock Trigger Engine
                </h3>
                
                <div style={{ fontSize: '0.85rem', opacity: 0.7, marginBottom: '24px' }}>
                    Select an inventory item and adjust the stock level to see how UTR (Understock Trigger Ratio) 
                    and OTR (Overstock Trigger Ratio) change in real-time.
                </div>
                
                {/* Warehouse and Item Selection */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
                    {/* Warehouse Selector */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <label style={{ fontSize: '0.85rem', opacity: 0.7 }}>1. Select Warehouse</label>
                        <select 
                            value={adjWarehouseId} 
                            onChange={(e) => {
                                setAdjWarehouseId(Number(e.target.value) || '');
                                setAdjMaterialId('');
                            }}
                            style={{
                                padding: '10px',
                                background: 'rgba(0,0,0,0.3)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                color: 'white',
                                borderRadius: '4px'
                            }}
                        >
                            <option value="">-- Choose --</option>
                            {warehouseSummaries.map(w => (
                                <option key={w.warehouse_id} value={w.warehouse_id}>{w.warehouse_name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Material Selector */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <label style={{ fontSize: '0.85rem', opacity: 0.7 }}>2. Select Item</label>
                        <select 
                            value={adjMaterialId} 
                            onChange={(e) => setAdjMaterialId(Number(e.target.value) || '')}
                            disabled={!adjWarehouseId}
                            style={{
                                padding: '10px',
                                background: 'rgba(0,0,0,0.3)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                color: 'white',
                                borderRadius: '4px',
                                opacity: !adjWarehouseId ? 0.5 : 1
                            }}
                        >
                            <option value="">-- Choose Item --</option>
                            {availableMaterials.map(s => (
                                <option key={s.material_id} value={s.material_id}>{s.material_name}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Stock Simulation Section - only shown when item is selected */}
                {selectedStockItem && (
                    <motion.div 
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        style={{
                            padding: '20px',
                            background: 'rgba(0,0,0,0.3)',
                            borderRadius: '8px',
                            border: '1px solid rgba(255,255,255,0.1)',
                            marginTop: '20px'
                        }}
                    >
                        {/* Item Info Header */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                            <div>
                                <div style={{ fontSize: '1rem', fontWeight: '600' }}>{selectedStockItem.material_name}</div>
                                <div style={{ fontSize: '0.75rem', opacity: 0.5 }}>
                                    {selectedStockItem.warehouse_name} • Code: {selectedStockItem.material_code}
                                </div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                                <div style={{ fontSize: '0.75rem', opacity: 0.5 }}>Current Real Stock</div>
                                <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#4ade80' }}>
                                    {selectedStockItem.quantity_available.toLocaleString()} units
                                </div>
                            </div>
                        </div>

                        {/* Thresholds Display */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '20px' }}>
                            <div style={{ padding: '12px', background: 'rgba(251, 146, 60, 0.1)', borderRadius: '6px', textAlign: 'center' }}>
                                <div style={{ fontSize: '0.7rem', opacity: 0.6, marginBottom: '4px' }}>Safety Stock</div>
                                <div style={{ fontSize: '1rem', fontWeight: '600', color: '#fb923c' }}>
                                    {selectedStockItem.min_stock_level || 50}
                                </div>
                            </div>
                            <div style={{ padding: '12px', background: 'rgba(96, 165, 250, 0.1)', borderRadius: '6px', textAlign: 'center' }}>
                                <div style={{ fontSize: '0.7rem', opacity: 0.6, marginBottom: '4px' }}>Reorder Point</div>
                                <div style={{ fontSize: '1rem', fontWeight: '600', color: '#60a5fa' }}>
                                    {selectedStockItem.reorder_point || 100}
                                </div>
                            </div>
                            <div style={{ padding: '12px', background: 'rgba(168, 85, 247, 0.1)', borderRadius: '6px', textAlign: 'center' }}>
                                <div style={{ fontSize: '0.7rem', opacity: 0.6, marginBottom: '4px' }}>Max Stock</div>
                                <div style={{ fontSize: '1rem', fontWeight: '600', color: '#a855f7' }}>
                                    {selectedStockItem.max_stock_level || (selectedStockItem.reorder_point || 100) * 2}
                                </div>
                            </div>
                        </div>

                        {/* THE SINGLE STOCK SLIDER */}
                        <div style={{ marginBottom: '20px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                <label style={{ fontSize: '0.9rem', fontWeight: '600' }}>
                                    3. Simulate Stock Level
                                </label>
                                <div style={{ 
                                    padding: '6px 16px', 
                                    background: simulatedStock < (selectedStockItem.reorder_point || 100) 
                                        ? 'rgba(239, 68, 68, 0.2)' 
                                        : simulatedStock > (selectedStockItem.max_stock_level || (selectedStockItem.reorder_point || 100) * 2)
                                            ? 'rgba(245, 158, 11, 0.2)'
                                            : 'rgba(74, 222, 128, 0.2)', 
                                    borderRadius: '20px',
                                    fontSize: '1rem',
                                    fontWeight: 'bold',
                                    color: simulatedStock < (selectedStockItem.reorder_point || 100) 
                                        ? '#ef4444' 
                                        : simulatedStock > (selectedStockItem.max_stock_level || (selectedStockItem.reorder_point || 100) * 2)
                                            ? '#f59e0b'
                                            : '#4ade80'
                                }}>
                                    {simulatedStock.toLocaleString()} units
                                </div>
                            </div>
                            
                            <input 
                                type="range"
                                min={0}
                                max={Math.max((selectedStockItem.max_stock_level || 500) * 1.5, selectedStockItem.quantity_available * 2, 500)}
                                value={simulatedStock}
                                onChange={(e) => setSimulatedStock(Number(e.target.value))}
                                style={{
                                    width: '100%',
                                    accentColor: '#f472b6',
                                    height: '8px',
                                    borderRadius: '4px',
                                    cursor: 'pointer'
                                }}
                            />
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', opacity: 0.4, marginTop: '6px' }}>
                                <span>0 (Empty)</span>
                                <span style={{ color: '#60a5fa' }}>ROP: {selectedStockItem.reorder_point || 100}</span>
                                <span style={{ color: '#a855f7' }}>Max: {selectedStockItem.max_stock_level || (selectedStockItem.reorder_point || 100) * 2}</span>
                            </div>
                        </div>

                        {/* Apply Changes Button */}
                        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                            <button
                                onClick={() => setSimulatedStock(selectedStockItem.quantity_available)}
                                style={{
                                    padding: '10px 20px',
                                    background: 'rgba(255,255,255,0.1)',
                                    border: '1px solid rgba(255,255,255,0.2)',
                                    borderRadius: '6px',
                                    color: 'white',
                                    cursor: 'pointer',
                                    fontSize: '0.85rem'
                                }}
                            >
                                Reset to Actual
                            </button>
                            <button
                                onClick={handleAdjustmentSubmit}
                                disabled={isAdjusting || simulatedStock === selectedStockItem.quantity_available}
                                style={{
                                    padding: '10px 24px',
                                    background: simulatedStock !== selectedStockItem.quantity_available ? '#3b82f6' : 'rgba(255,255,255,0.1)',
                                    border: 'none',
                                    borderRadius: '6px',
                                    color: 'white',
                                    fontWeight: '600',
                                    cursor: simulatedStock !== selectedStockItem.quantity_available ? 'pointer' : 'not-allowed',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    opacity: simulatedStock !== selectedStockItem.quantity_available ? 1 : 0.5,
                                    fontSize: '0.85rem'
                                }}
                            >
                                {isAdjusting ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                                Apply to Database
                            </button>
                        </div>
                    </motion.div>
                )}
            </motion.div>

        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
            style={{ width: '100%' }} 
        >
            {/* Result Panel */}
            <div style={{ height: '100%' }}>
                 {simResult && simResult.status && simResult.metrics ? (
                    <div style={{
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '16px',

                        padding: '30px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '24px',
                        height: '100%'
                    }}>
                        {/* Header Status */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{simResult.item_name}</div>
                                <div style={{ fontSize: '0.7rem', opacity: 0.5 }}>
                                    Simulated Stock: {simulatedStock} | ROP: {simResult.metrics.reorder_point} | Max: {simResult.simulation?.input.max_stock_level}
                                </div>
                            </div>
                             <div style={{
                                padding: '8px 16px',
                                borderRadius: '20px',
                                fontSize: '0.85rem',
                                fontWeight: 'bold',
                                background: simResult.status.severity === 'RED' ? 'rgba(239, 68, 68, 0.2)' : 
                                          simResult.status.severity === 'AMBER' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(74, 222, 128, 0.2)',
                                color: simResult.status.severity === 'RED' ? '#ef4444' : 
                                       simResult.status.severity === 'AMBER' ? '#f59e0b' : '#4ade80',
                                border: `1px solid ${simResult.status.severity === 'RED' ? '#ef4444' : 
                                                   simResult.status.severity === 'AMBER' ? '#f59e0b' : '#4ade80'}`
                            }}>
                                {simResult.status.label}
                            </div>
                        </div>

                        {/* Metrics */}
                         <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', flex: 1, alignItems: 'center' }}>
                            <div style={{ padding: '24px 16px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px', textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                <div style={{ opacity: 0.6, fontSize: '0.85rem' }}>UTR</div>
                                <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: simResult.metrics.utr > 0 ? '#ef4444' : '#4ade80' }}>
                                    {simResult.metrics.utr}
                                </div>
                                <div style={{ fontSize: '0.7rem', opacity: 0.4 }}>Understock Ratio</div>
                            </div>
                            <div style={{ padding: '24px 16px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px', textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                <div style={{ opacity: 0.6, fontSize: '0.85rem' }}>OTR</div>
                                <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: simResult.metrics.otr > 0.5 ? '#f59e0b' : '#4ade80' }}>
                                    {simResult.metrics.otr}
                                </div>
                                <div style={{ fontSize: '0.7rem', opacity: 0.4 }}>Overstock Ratio</div>
                            </div>
                            <div style={{ padding: '24px 16px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px', textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                <div style={{ opacity: 0.6, fontSize: '0.85rem' }}>PAR</div>
                                <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#60a5fa' }}>
                                    {simResult.metrics.par}
                                </div>
                                <div style={{ fontSize: '0.7rem', opacity: 0.4 }}>Procurement Ratio</div>
                            </div>
                         </div>

                         {/* Action */}
                         {simResult.status.action && (
                             <div style={{ 
                                 padding: '20px', 
                                 background: 'rgba(255,255,255,0.05)', 
                                 borderRadius: '12px', 
                                 textAlign: 'center', 
                                 fontSize: '1rem',
                                 fontWeight: '600',
                                 display: 'flex',
                                 alignItems: 'center',
                                 justifyContent: 'center',
                                 gap: '12px'
                             }}>
                                 <AlertTriangle size={24} color="#fb923c" />
                                 <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', textAlign: 'left' }}>
                                      <span style={{ fontSize: '0.8rem', opacity: 0.6 }}>Recommended Action</span>
                                      <span>{simResult.status.action}</span>
                                 </div>
                             </div>
                        )}
                    </div>
                 ) : (
                     <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.5, background: 'rgba(255,255,255,0.02)', borderRadius: '16px', border: '1px dashed rgba(255,255,255,0.1)' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
                            <Loader2 size={32} className="animate-spin" />
                            <span>Initializing Simulation...</span>
                        </div>
                     </div>
                 )}
            </div>
        </motion.div>
        </div>
      )}
    </div>
  );
};

export default Inventory;
