import { MapContainer, TileLayer, Marker, Popup, Tooltip } from 'react-leaflet';
import { Icon } from 'leaflet';
import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Radio, MapPin, Zap, Package, Loader2, RefreshCw, Warehouse, ArrowRight, Activity } from 'lucide-react';
import type { SubstationMapData, WarehouseMapData } from '../services/inventoryApi';
import inventoryApi from '../services/inventoryApi';
import 'leaflet/dist/leaflet.css';

// Create SUBSTATION icon (lightning bolt / transformer style)
const createSubstationIcon = (stockStatus: 'Normal' | 'Understocked' | 'Overstocked') => {
  const colorMap = {
    Normal: '#10B981',      // Emerald green
    Understocked: '#EF4444', // Red
    Overstocked: '#3B82F6',  // Blue
  };
  
  const color = colorMap[stockStatus];
  
  // Lightning bolt / power substation icon
  return new Icon({
    iconUrl: `data:image/svg+xml;base64,${btoa(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 50" width="40" height="50">
        <!-- Pin shape -->
        <path d="M20 48 C20 48 4 28 4 18 C4 9.2 11.2 2 20 2 C28.8 2 36 9.2 36 18 C36 28 20 48 20 48Z" 
              fill="${color}" stroke="white" stroke-width="2"/>
        <!-- Lightning bolt -->
        <path d="M22 8 L14 20 L18 20 L16 30 L26 17 L21 17 L24 8 Z" 
              fill="white" stroke="none"/>
      </svg>
    `)}`,
    iconSize: [32, 40],
    iconAnchor: [16, 40],
    popupAnchor: [0, -40],
    tooltipAnchor: [16, -20],
  });
};

// Create WAREHOUSE icon (box/building style)
const createWarehouseIcon = (stockStatus: 'Normal' | 'Low' | 'Critical') => {
  const colorMap = {
    Normal: '#8B5CF6',   // Purple
    Low: '#F59E0B',      // Amber
    Critical: '#DC2626', // Dark red
  };
  
  const color = colorMap[stockStatus];
  
  // Warehouse / box icon
  return new Icon({
    iconUrl: `data:image/svg+xml;base64,${btoa(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 50" width="40" height="50">
        <!-- Pin shape -->
        <path d="M20 48 C20 48 4 28 4 18 C4 9.2 11.2 2 20 2 C28.8 2 36 9.2 36 18 C36 28 20 48 20 48Z" 
              fill="${color}" stroke="white" stroke-width="2"/>
        <!-- Warehouse building -->
        <rect x="10" y="14" width="20" height="14" fill="white" stroke="none" rx="1"/>
        <!-- Roof -->
        <path d="M8 15 L20 8 L32 15 Z" fill="white" stroke="none"/>
        <!-- Door -->
        <rect x="17" y="20" width="6" height="8" fill="${color}" stroke="none"/>
        <!-- Windows -->
        <rect x="11" y="16" width="4" height="3" fill="${color}" stroke="none"/>
        <rect x="25" y="16" width="4" height="3" fill="${color}" stroke="none"/>
      </svg>
    `)}`,
    iconSize: [32, 40],
    iconAnchor: [16, 40],
    popupAnchor: [0, -40],
    tooltipAnchor: [16, -20],
  });
};

// Get status color
const getStatusColor = (status: string) => {
  switch (status) {
    case 'CRITICAL':
    case 'Critical':
    case 'OUT_OF_STOCK': return '#DC2626';
    case 'LOW':
    case 'Low': return '#F59E0B';
    case 'OK':
    case 'Normal': return '#10B981';
    case 'Understocked': return '#EF4444';
    case 'Overstocked': return '#3B82F6';
    default: return '#ffffff';
  }
};

const Substations = () => {
  const navigate = useNavigate();
  const [substations, setSubstations] = useState<SubstationMapData[]>([]);
  const [warehouses, setWarehouses] = useState<WarehouseMapData[]>([]);
  const [loading, setLoading] = useState(true);
  const [isLive, setIsLive] = useState(false);

  const indiaCenter: [number, number] = [22.5, 78.9629];


  // Fetch data from API
  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch both substations and warehouses
      const [substationData, warehouseData] = await Promise.all([
        inventoryApi.getSubstationsMapData(),
        inventoryApi.getWarehousesWithStock()
      ]);
      
      setSubstations(substationData);
      setWarehouses(warehouseData);
      setIsLive(true);
    } catch (err) {
      console.log('API not available:', err);
      setIsLive(false);
      setSubstations([]);
      setWarehouses([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Calculate counts
  const substationCounts = {
    normal: substations.filter(s => s.stock_status === 'Normal').length,
    understocked: substations.filter(s => s.stock_status === 'Understocked').length,
    overstocked: substations.filter(s => s.stock_status === 'Overstocked').length,
  };

  const warehouseCounts = {
    normal: warehouses.filter(w => w.stockStatus === 'Normal').length,
    low: warehouses.filter(w => w.stockStatus === 'Low').length,
    critical: warehouses.filter(w => w.stockStatus === 'Critical').length,
  };

  const totalStockItems = warehouses.reduce((acc, w) => acc + w.stockItems.length, 0);

  return (
    <div style={{ height: 'calc(100vh - 62px)', display: 'flex', flexDirection: 'column', position: 'relative' }}>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          padding: '16px 40px',
          background: 'rgba(0,0,0,0.95)',
          borderBottom: '1px solid rgba(255,255,255,0.2)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          zIndex: 1000
        }}
      >
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 'bold', margin: 0, letterSpacing: '2px' }}>
            <Radio size={22} style={{ display: 'inline', marginRight: '10px', verticalAlign: 'middle' }} />
            Network Inventory Map
          </h2>
          <p style={{ margin: '4px 0 0', opacity: 0.6, fontSize: '0.85rem' }}>
            {substations.length} Substations • {warehouses.length} Warehouses • {totalStockItems} Stock Items
          </p>
        </div>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          {/* Connection Status */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '5px 10px',
            border: `1px solid ${isLive ? '#10B981' : '#F59E0B'}`,
            background: isLive ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
            fontSize: '0.7rem'
          }}>
            <div style={{ 
              width: '6px', 
              height: '6px', 
              borderRadius: '50%', 
              background: isLive ? '#10B981' : '#F59E0B',
              animation: isLive ? 'pulse 2s infinite' : 'none'
            }} />
            <span style={{ color: isLive ? '#10B981' : '#F59E0B' }}>
              {isLive ? 'LIVE' : 'OFFLINE'}
            </span>
          </div>
          
          {/* Refresh */}
          <button
            onClick={fetchData}
            disabled={loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              padding: '5px 10px',
              border: '1px solid rgba(255,255,255,0.3)',
              background: 'transparent',
              color: 'white',
              cursor: 'pointer',
              fontSize: '0.7rem'
            }}
          >
            <RefreshCw size={12} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>
          
          {/* Substation Stats */}
          <div style={{ display: 'flex', gap: '12px', paddingLeft: '12px', borderLeft: '1px solid rgba(255,255,255,0.2)' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: '#10B981' }}>
                {substationCounts.normal}
              </div>
              <div style={{ fontSize: '0.6rem', opacity: 0.6, letterSpacing: '0.5px' }}>SS NORMAL</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: '#EF4444' }}>
                {substationCounts.understocked}
              </div>
              <div style={{ fontSize: '0.6rem', opacity: 0.6, letterSpacing: '0.5px' }}>SS LOW</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: '#3B82F6' }}>
                {substationCounts.overstocked}
              </div>
              <div style={{ fontSize: '0.6rem', opacity: 0.6, letterSpacing: '0.5px' }}>SS OVER</div>
            </div>
          </div>

          {/* Warehouse Stats */}
          <div style={{ display: 'flex', gap: '12px', paddingLeft: '12px', borderLeft: '1px solid rgba(255,255,255,0.2)' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: '#8B5CF6' }}>
                {warehouseCounts.normal}
              </div>
              <div style={{ fontSize: '0.6rem', opacity: 0.6, letterSpacing: '0.5px' }}>WH OK</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: '#F59E0B' }}>
                {warehouseCounts.low}
              </div>
              <div style={{ fontSize: '0.6rem', opacity: 0.6, letterSpacing: '0.5px' }}>WH LOW</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: '#DC2626' }}>
                {warehouseCounts.critical}
              </div>
              <div style={{ fontSize: '0.6rem', opacity: 0.6, letterSpacing: '0.5px' }}>WH CRIT</div>
            </div>
          </div>
        </div>
      </motion.div>

      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        
        /* Dark Mode Popup Styles */
        .leaflet-popup-content-wrapper, .leaflet-popup-tip {
          background: rgba(10, 10, 10, 0.95) !important;
          color: white !important;
          border: 1px solid rgba(255, 255, 255, 0.2);
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5) !important;
          padding: 0 !important; /* Remove wrapper padding to let inner div control it */
          overflow: hidden; /* Ensure content doesn't bleed out of rounded corners */
        }
        .leaflet-popup-content {
          margin: 0 !important;
          width: auto !important;
          line-height: 1.5;
        }
        .leaflet-container a.leaflet-popup-close-button {
          color: rgba(255, 255, 255, 0.7) !important;
          top: 12px !important;
          right: 12px !important;
          font-size: 18px !important;
          text-shadow: none !important;
        }
        .leaflet-container a.leaflet-popup-close-button:hover {
          color: white !important;
          background: rgba(255,255,255,0.1);
          border-radius: 50%;
        }
      `}</style>

      {/* Map Container */}
      <div style={{ flex: 1, position: 'relative' }}>
        {loading && (
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 1001,
            background: 'rgba(0,0,0,0.9)',
            padding: '20px 30px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            border: '1px solid rgba(255,255,255,0.2)'
          }}>
            <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} />
            <span>Loading map data...</span>
          </div>
        )}
        
        <MapContainer
          center={indiaCenter}
          zoom={5}
          style={{ height: '100%', width: '100%' }}
          zoomControl={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          {/* ============ SUBSTATION MARKERS ============ */}
          {substations.map((substation) => (
            <Marker
              key={`ss-${substation.id}`}
              position={[substation.lat, substation.lng]}
              icon={createSubstationIcon(substation.stock_status)}
            >
              <Popup autoPan={true} autoPanPaddingTopLeft={[50, 200]}>
                <div style={{ padding: '20px', minWidth: '300px' }}>
                  <h3 style={{ 
                    margin: '0 0 10px', 
                    fontSize: '1rem', 
                    borderBottom: '1px solid rgba(255,255,255,0.3)',
                    paddingBottom: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <Zap size={16} color={getStatusColor(substation.stock_status)} />
                    {substation.name}
                    <span style={{ 
                      fontSize: '0.6rem', 
                      padding: '2px 6px', 
                      background: 'rgba(16, 185, 129, 0.2)', 
                      border: '1px solid #10B981',
                      marginLeft: 'auto'
                    }}>SUBSTATION</span>
                  </h3>
                  <div style={{ fontSize: '0.85rem', lineHeight: '1.6' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ opacity: 0.7 }}>Code:</span>
                      <strong>{substation.code}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ opacity: 0.7 }}>Capacity:</span>
                      <strong>{substation.capacity}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ opacity: 0.7 }}>Location:</span>
                      <strong>{substation.city}, {substation.state}</strong>
                    </div>
                    
                    {/* Stock Status */}
                    <div style={{ 
                      marginTop: '10px', 
                      padding: '10px', 
                      background: 'rgba(0,0,0,0.3)',
                      border: `1px solid ${getStatusColor(substation.stock_status)}`
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ fontSize: '0.8rem', fontWeight: '600' }}>Stock Status</span>
                        <span style={{ 
                          padding: '2px 8px',
                          fontSize: '0.7rem',
                          fontWeight: '600',
                          background: `${getStatusColor(substation.stock_status)}30`,
                          color: getStatusColor(substation.stock_status),
                          border: `1px solid ${getStatusColor(substation.stock_status)}`
                        }}>
                          {substation.stock_status.toUpperCase()}
                        </span>
                      </div>
                      <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px' }}>
                        <div style={{ 
                          width: `${Math.min(substation.stock_level, 100)}%`, 
                          height: '100%', 
                          background: getStatusColor(substation.stock_status),
                          borderRadius: '3px'
                        }} />
                      </div>
                      <div style={{ fontSize: '0.7rem', opacity: 0.7, marginTop: '4px', textAlign: 'right' }}>
                        {substation.stock_level}%
                      </div>
                    </div>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '12px' }}>
                    <button
                      onClick={() => navigate(`/dashboard?target=${encodeURIComponent(substation.name)}`)}
                      style={{
                        padding: '8px',
                        background: 'rgba(59, 130, 246, 0.2)',
                        border: '1px solid #3B82F6',
                        color: 'white',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.8rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px'
                      }}
                    >
                      <Activity size={14} /> Dashboard
                    </button>
                    <button
                      onClick={() => navigate(`/inventory?target=${encodeURIComponent(substation.name)}`)}
                      style={{
                        width: '100%',
                        padding: '8px',
                        background: 'rgba(16, 185, 129, 0.2)',
                        border: '1px solid #10B981',
                        color: 'white',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.8rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px'
                      }}
                    >
                      View Inventory <ArrowRight size={14} />
                    </button>
                    </div>
                  </div>
                </div>
              </Popup>
              
              <Tooltip direction="top" offset={[0, -20]} opacity={1}>
                <div style={{ 
                  padding: '8px 12px', 
                  background: 'rgba(0, 0, 0, 0.95)',
                  border: `2px solid ${getStatusColor(substation.stock_status)}`,
                  borderRadius: '6px'
                }}>
                  <div style={{ fontWeight: '600', fontSize: '0.85rem', color: '#fff', marginBottom: '4px' }}>
                    ⚡ {substation.name}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: getStatusColor(substation.stock_status) }}>
                    {substation.stock_status} • {substation.stock_level}%
                  </div>
                </div>
              </Tooltip>
            </Marker>
          ))}

          {/* ============ WAREHOUSE MARKERS ============ */}
          {warehouses.map((warehouse) => (
            <Marker
              key={`wh-${warehouse.id}`}
              position={[warehouse.lat, warehouse.lng]}
              icon={createWarehouseIcon(warehouse.stockStatus)}
            >
              <Popup autoPan={true} autoPanPaddingTopLeft={[50, 200]}>
                <div style={{ padding: '20px', minWidth: '340px' }}>
                  <h3 style={{ 
                    margin: '0 0 10px', 
                    fontSize: '1rem', 
                    borderBottom: '1px solid rgba(255,255,255,0.3)',
                    paddingBottom: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <Warehouse size={16} color="#8B5CF6" />
                    {warehouse.name}
                    <span style={{ 
                      fontSize: '0.6rem', 
                      padding: '2px 6px', 
                      background: 'rgba(139, 92, 246, 0.2)', 
                      border: '1px solid #8B5CF6',
                      marginLeft: 'auto'
                    }}>WAREHOUSE</span>
                  </h3>
                  <div style={{ fontSize: '0.85rem', lineHeight: '1.6' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ opacity: 0.7 }}>Code:</span>
                      <strong>{warehouse.code}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ opacity: 0.7 }}>State:</span>
                      <strong>{warehouse.state}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ opacity: 0.7 }}>Total Stock:</span>
                      <strong>{warehouse.totalStock.toLocaleString()} units</strong>
                    </div>
                    
                    {/* Status Summary */}
                    <div style={{ 
                      marginTop: '10px', 
                      padding: '10px', 
                      background: 'rgba(0,0,0,0.3)',
                      border: `1px solid ${getStatusColor(warehouse.stockStatus)}`,
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr 1fr',
                      gap: '8px'
                    }}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#10B981' }}>
                          {warehouse.stockItems.filter(i => i.stock_status === 'OK').length}
                        </div>
                        <div style={{ fontSize: '0.6rem', opacity: 0.7 }}>OK</div>
                      </div>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#F59E0B' }}>
                          {warehouse.lowStockCount}
                        </div>
                        <div style={{ fontSize: '0.6rem', opacity: 0.7 }}>LOW</div>
                      </div>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#DC2626' }}>
                          {warehouse.outOfStockCount}
                        </div>
                        <div style={{ fontSize: '0.6rem', opacity: 0.7 }}>OUT</div>
                      </div>
                    </div>

                    {/* Stock Items List */}
                    <div style={{ 
                      marginTop: '10px', 
                      padding: '10px', 
                      background: 'rgba(0,0,0,0.3)',
                      border: '1px solid rgba(255,255,255,0.1)'
                    }}>
                      <div style={{ 
                        fontSize: '0.75rem', 
                        fontWeight: '600', 
                        marginBottom: '8px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}>
                        <Package size={12} />
                        Stock Items ({warehouse.stockItems.length})
                      </div>
                      <div style={{ maxHeight: '180px', overflowY: 'auto' }}>
                        {warehouse.stockItems.slice(0, 10).map((item) => (
                          <div 
                            key={item.id}
                            style={{ 
                              padding: '6px 8px',
                              marginBottom: '4px',
                              background: 'rgba(255,255,255,0.03)',
                              borderLeft: `2px solid ${getStatusColor(item.stock_status)}`,
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center'
                            }}
                          >
                            <div>
                              <div style={{ fontSize: '0.75rem', fontWeight: '500' }}>{item.material_name}</div>
                              <div style={{ fontSize: '0.6rem', opacity: 0.5 }}>{item.material_code}</div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <div style={{ fontSize: '0.75rem', fontWeight: '600' }}>
                                {item.quantity_available.toLocaleString()}
                              </div>
                              <div style={{ 
                                fontSize: '0.55rem',
                                color: getStatusColor(item.stock_status)
                              }}>
                                {item.stock_status}
                              </div>
                            </div>
                          </div>
                        ))}
                        {warehouse.stockItems.length > 10 && (
                          <div style={{ fontSize: '0.7rem', opacity: 0.5, textAlign: 'center', padding: '6px' }}>
                            +{warehouse.stockItems.length - 10} more items
                          </div>
                        )}
                      </div>
                    </div>
                    
                    <button
                      onClick={() => navigate(`/inventory?target=${encodeURIComponent(warehouse.name)}`)}
                      style={{
                        width: '100%',
                        marginTop: '12px',
                        padding: '8px',
                        background: 'rgba(139, 92, 246, 0.2)',
                        border: '1px solid #8B5CF6',
                        color: 'white',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.8rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px'
                      }}
                    >
                      View Inventory <ArrowRight size={14} />
                    </button>
                  </div>
                </div>
              </Popup>
              
              <Tooltip direction="top" offset={[0, -20]} opacity={1}>
                <div style={{ 
                  padding: '8px 12px', 
                  background: 'rgba(0, 0, 0, 0.95)',
                  border: `2px solid ${getStatusColor(warehouse.stockStatus)}`,
                  borderRadius: '6px'
                }}>
                  <div style={{ fontWeight: '600', fontSize: '0.85rem', color: '#fff', marginBottom: '4px' }}>
                    🏭 {warehouse.name}
                  </div>
                  <div style={{ fontSize: '0.7rem', opacity: 0.8 }}>
                    {warehouse.stockItems.length} items • {warehouse.totalStock.toLocaleString()} units
                  </div>
                  {(warehouse.lowStockCount > 0 || warehouse.outOfStockCount > 0) && (
                    <div style={{ fontSize: '0.65rem', color: '#F59E0B', marginTop: '3px' }}>
                      ⚠️ {warehouse.lowStockCount} low, {warehouse.outOfStockCount} out
                    </div>
                  )}
                </div>
              </Tooltip>
            </Marker>
          ))}
        </MapContainer>

        {/* Legend */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          style={{
            position: 'absolute',
            bottom: '20px',
            right: '20px',
            background: 'rgba(0,0,0,0.95)',
            padding: '16px',
            border: '1px solid rgba(255,255,255,0.3)',
            zIndex: 1000,
            minWidth: '200px'
          }}
        >
          <h4 style={{ margin: '0 0 12px', fontSize: '0.8rem', letterSpacing: '1px', opacity: 0.8 }}>
            <MapPin size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
            MAP LEGEND
          </h4>
          
          {/* Substations */}
          <div style={{ marginBottom: '12px' }}>
            <div style={{ fontSize: '0.7rem', opacity: 0.6, marginBottom: '6px', letterSpacing: '0.5px' }}>
              ⚡ SUBSTATIONS
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <div style={{ width: '10px', height: '10px', background: '#10B981', borderRadius: '50%' }} />
              <span style={{ fontSize: '0.75rem' }}>Normal ({substationCounts.normal})</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <div style={{ width: '10px', height: '10px', background: '#EF4444', borderRadius: '50%' }} />
              <span style={{ fontSize: '0.75rem' }}>Understocked ({substationCounts.understocked})</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '10px', height: '10px', background: '#3B82F6', borderRadius: '50%' }} />
              <span style={{ fontSize: '0.75rem' }}>Overstocked ({substationCounts.overstocked})</span>
            </div>
          </div>
          
          {/* Warehouses */}
          <div style={{ paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
            <div style={{ fontSize: '0.7rem', opacity: 0.6, marginBottom: '6px', letterSpacing: '0.5px' }}>
              🏭 WAREHOUSES
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <div style={{ width: '10px', height: '10px', background: '#8B5CF6', borderRadius: '2px' }} />
              <span style={{ fontSize: '0.75rem' }}>Normal ({warehouseCounts.normal})</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <div style={{ width: '10px', height: '10px', background: '#F59E0B', borderRadius: '2px' }} />
              <span style={{ fontSize: '0.75rem' }}>Low Stock ({warehouseCounts.low})</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '10px', height: '10px', background: '#DC2626', borderRadius: '2px' }} />
              <span style={{ fontSize: '0.75rem' }}>Critical ({warehouseCounts.critical})</span>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Substations;
