import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Calculator, 
  MapPin, 
  Zap, 
  DollarSign, 
  Search,
  ChevronDown,
  Package,
  AlertTriangle,
  Loader2,
  Building2,
  Cable
} from 'lucide-react';
import type { 
  QuoteResponse, 
  ProjectTypeInfo, 
  LineCost
} from '../services/quoteApi';
import quoteApi from '../services/quoteApi';

// Format currency in Indian format (Lakhs/Crores)
const formatINR = (amount: number): string => {
  if (amount >= 10000000) {
    return `₹${(amount / 10000000).toFixed(2)} Cr`;
  } else if (amount >= 100000) {
    return `₹${(amount / 100000).toFixed(2)} L`;
  }
  return `₹${amount.toLocaleString('en-IN')}`;
};

const CostCalculator = () => {
  // State
  const [projectTypes, setProjectTypes] = useState<ProjectTypeInfo[]>([]);
  const [selectedProjectType, setSelectedProjectType] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  
  // Location inputs
  const [fromLocation, setFromLocation] = useState({ lat: '', lng: '', name: 'Kota, Rajasthan' });
  const [toLocation, setToLocation] = useState({ lat: '', lng: '', name: 'Beawar, Rajasthan' });
  
  // Options
  const [terrain] = useState('normal');
  const [circuitType] = useState('single');
  const [voltageKv] = useState(400);
  
  // Results
  const [quote, setQuote] = useState<QuoteResponse | null>(null);
  const [lineCost, setLineCost] = useState<LineCost | null>(null);
  
  // Loading states
  const [loading, setLoading] = useState(false);
  const [loadingTypes, setLoadingTypes] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Preset locations for India
  const presetLocations = [
    { name: 'Kota, Rajasthan', lat: 25.18, lng: 75.8648 },
    { name: 'Beawar, Rajasthan', lat: 26.1011, lng: 74.3189 },
    { name: 'Jaipur, Rajasthan', lat: 26.9124, lng: 75.7873 },
    { name: 'Delhi', lat: 28.6139, lng: 77.209 },
    { name: 'Mumbai, Maharashtra', lat: 19.076, lng: 72.8777 },
    { name: 'Bangalore, Karnataka', lat: 12.9716, lng: 77.5946 },
    { name: 'Chennai, Tamil Nadu', lat: 13.0827, lng: 80.2707 },
    { name: 'Hyderabad, Telangana', lat: 17.385, lng: 78.4867 },
    { name: 'Kolkata, West Bengal', lat: 22.5726, lng: 88.3639 },
    { name: 'Ahmedabad, Gujarat', lat: 23.0225, lng: 72.5714 },
  ];

  // Fetch project types on mount
  useEffect(() => {
    const fetchTypes = async () => {
      setLoadingTypes(true);
      try {
        const types = await quoteApi.getProjectTypes({ limit: 100 });
        setProjectTypes(types);
        if (types.length > 0) {
          setSelectedProjectType(types[0].title);
        }
      } catch (err) {
        console.log('Could not fetch project types');
        // Use fallback types
        setProjectTypes([
          { title: '33/22 kV 1 X 5 MVA New S/S(Outdoor)', item_code: '0101', category: 'Substation', voltage_level: '33', capacity_mva: 5, total_cost: 50000000 },
          { title: '400 kV D/C Transmission Line', item_code: '0501', category: 'Transmission Line', voltage_level: '400', capacity_mva: null, total_cost: 150000000 },
          { title: '220 kV S/C Transmission Line', item_code: '0502', category: 'Transmission Line', voltage_level: '220', capacity_mva: null, total_cost: 80000000 },
        ]);
      } finally {
        setLoadingTypes(false);
      }
    };
    fetchTypes();
  }, []);

  // Filter project types based on search
  const filteredTypes = projectTypes.filter(t => 
    t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Calculate quote
  const calculateQuote = async () => {
    setLoading(true);
    setError(null);
    setQuote(null);
    setLineCost(null);
    
    try {
      const fromLat = fromLocation.lat ? parseFloat(fromLocation.lat) : undefined;
      const fromLng = fromLocation.lng ? parseFloat(fromLocation.lng) : undefined;
      const toLat = toLocation.lat ? parseFloat(toLocation.lat) : undefined;
      const toLng = toLocation.lng ? parseFloat(toLocation.lng) : undefined;
      
      const result = await quoteApi.getQuote({
        project_type: selectedProjectType,
        from_lat: fromLat,
        from_lng: fromLng,
        to_lat: toLat,
        to_lng: toLng,
        terrain,
        circuit_type: circuitType
      });
      
      setQuote(result);
      if (result.line_cost) {
        setLineCost(result.line_cost);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to calculate quote');
    } finally {
      setLoading(false);
    }
  };

  // Calculate line cost only
  const calculateLineCost = async () => {
    if (!fromLocation.lat || !fromLocation.lng || !toLocation.lat || !toLocation.lng) {
      setError('Please enter both From and To coordinates');
      return;
    }
    
    setLoading(true);
    setError(null);
    setQuote(null); // Clear previous quote to switch to Line Only mode
    
    try {
      const result = await quoteApi.getLineCost({
        from_lat: parseFloat(fromLocation.lat),
        from_lng: parseFloat(fromLocation.lng),
        to_lat: parseFloat(toLocation.lat),
        to_lng: parseFloat(toLocation.lng),
        voltage_kv: voltageKv,
        terrain,
        circuit_type: circuitType
      });
      
      setLineCost(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to calculate line cost');
    } finally {
      setLoading(false);
    }
  };

  // Set preset location
  const setPresetFrom = (preset: typeof presetLocations[0]) => {
    setFromLocation({ lat: preset.lat.toString(), lng: preset.lng.toString(), name: preset.name });
  };

  const setPresetTo = (preset: typeof presetLocations[0]) => {
    setToLocation({ lat: preset.lat.toString(), lng: preset.lng.toString(), name: preset.name });
  };

  return (
    <div style={{ padding: '40px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ marginBottom: '30px' }}
      >
        <h2 style={{ fontSize: '2rem', fontWeight: '300', margin: 0, display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Calculator size={28} />
          Project Cost Calculator
        </h2>
        <div style={{ fontSize: '0.9rem', opacity: 0.7, marginTop: '8px' }}>
          Calculate optimal costs for power grid projects between any two locations
        </div>
      </motion.div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
        {/* Input Panel */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          style={{
            border: '1px solid rgba(255,255,255,0.2)',
            padding: '24px',
            background: 'rgba(10,10,10,0.8)'
          }}
        >
          <h3 style={{ margin: '0 0 20px', fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Zap size={18} />
            Project Configuration
          </h3>

          {/* Project Type Selector */}
          <div style={{ marginBottom: '20px', position: 'relative' }}>
            <label style={{ fontSize: '0.8rem', opacity: 0.7, display: 'block', marginBottom: '6px' }}>
              PROJECT TYPE
            </label>
            <div 
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '12px',
                border: '1px solid rgba(255,255,255,0.2)',
                background: 'rgba(0,0,0,0.3)',
                cursor: 'pointer'
              }}
              onClick={() => setShowDropdown(!showDropdown)}
            >
              <Search size={16} style={{ opacity: 0.5, marginRight: '8px' }} />
              <input
                type="text"
                value={searchQuery || selectedProjectType.replace(/Cost (data )?for /i, '')}
                onChange={(e) => { setSearchQuery(e.target.value); setShowDropdown(true); }}
                placeholder="Search project types..."
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  color: 'white',
                  outline: 'none',
                  fontSize: '0.9rem'
                }}
              />
              <ChevronDown size={16} style={{ opacity: 0.5 }} />
            </div>
            
            <AnimatePresence>
              {showDropdown && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    maxHeight: '300px',
                    overflowY: 'auto',
                    background: 'rgba(20,20,20,0.98)',
                    border: '1px solid rgba(255,255,255,0.2)',
                    zIndex: 100
                  }}
                >
                  {loadingTypes ? (
                    <div style={{ padding: '20px', textAlign: 'center', opacity: 0.5 }}>
                      <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} />
                    </div>
                  ) : filteredTypes.length > 0 ? (
                    filteredTypes.map((type, idx) => (
                      <div
                        key={idx}
                        onClick={() => { setSelectedProjectType(type.title); setSearchQuery(''); setShowDropdown(false); }}
                        style={{
                          padding: '12px 16px',
                          cursor: 'pointer',
                          borderBottom: '1px solid rgba(255,255,255,0.1)',
                          transition: 'background 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      >
                        <div style={{ fontWeight: '500', fontSize: '0.85rem' }}>
                          {type.title.replace(/Cost (data )?for /i, '')}
                        </div>
                        <div style={{ fontSize: '0.75rem', opacity: 0.6, marginTop: '4px' }}>
                          {type.category} • {type.voltage_level}kV • {formatINR(type.total_cost)}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ padding: '20px', textAlign: 'center', opacity: 0.5 }}>
                      No project types found
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* From Location */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{ fontSize: '0.8rem', opacity: 0.7, display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <MapPin size={14} color="#10B981" />
              FROM LOCATION
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <input
                type="text"
                placeholder="Latitude"
                value={fromLocation.lat}
                onChange={(e) => setFromLocation({ ...fromLocation, lat: e.target.value })}
                style={{
                  padding: '10px',
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid rgba(255,255,255,0.2)',
                  color: 'white',
                  fontSize: '0.85rem'
                }}
              />
              <input
                type="text"
                placeholder="Longitude"
                value={fromLocation.lng}
                onChange={(e) => setFromLocation({ ...fromLocation, lng: e.target.value })}
                style={{
                  padding: '10px',
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid rgba(255,255,255,0.2)',
                  color: 'white',
                  fontSize: '0.85rem'
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: '6px', marginTop: '6px', flexWrap: 'wrap' }}>
              {presetLocations.slice(0, 5).map((preset, idx) => (
                <button
                  key={idx}
                  onClick={() => setPresetFrom(preset)}
                  style={{
                    padding: '4px 8px',
                    fontSize: '0.7rem',
                    background: fromLocation.name === preset.name ? 'rgba(255, 255, 255, 0.3)' : 'rgba(255,255,255,0.1)',
                    border: 'none',
                    color: 'white',
                    cursor: 'pointer'
                  }}
                >
                  {preset.name.split(',')[0]}
                </button>
              ))}
            </div>
          </div>

          {/* To Location */}
          <div style={{ marginBottom: '30px' }}>
            <label style={{ fontSize: '0.8rem', opacity: 0.7, display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <MapPin size={14} color="#EF4444" />
              TO LOCATION
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <input
                type="text"
                placeholder="Latitude"
                value={toLocation.lat}
                onChange={(e) => setToLocation({ ...toLocation, lat: e.target.value })}
                style={{
                  padding: '10px',
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid rgba(255,255,255,0.2)',
                  color: 'white',
                  fontSize: '0.85rem'
                }}
              />
              <input
                type="text"
                placeholder="Longitude"
                value={toLocation.lng}
                onChange={(e) => setToLocation({ ...toLocation, lng: e.target.value })}
                style={{
                  padding: '10px',
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid rgba(255,255,255,0.2)',
                  color: 'white',
                  fontSize: '0.85rem'
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: '6px', marginTop: '6px', flexWrap: 'wrap' }}>
              {presetLocations.slice(0, 5).map((preset, idx) => (
                <button
                  key={idx}
                  onClick={() => setPresetTo(preset)}
                  style={{
                    padding: '4px 8px',
                    fontSize: '0.7rem',
                    background: toLocation.name === preset.name ? 'rgba(255, 255, 255, 0.3)' : 'rgba(255,255,255,0.1)',
                    border: 'none',
                    color: 'white',
                    cursor: 'pointer'
                  }}
                >
                  {preset.name.split(',')[0]}
                </button>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={calculateQuote}
                disabled={loading || !selectedProjectType}
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  padding: '14px',
                  background: 'white',
                  border: 'none',
                  color: 'black',
                  fontWeight: '600',
                  cursor: loading ? 'wait' : 'pointer',
                  opacity: loading ? 0.7 : 1,
                  transition: 'transform 0.2s, box-shadow 0.2s'
                }}
                onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 4px 20px rgba(255,255,255,0.2)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = 'none'; }}
              >
                {loading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : <Calculator size={18} />}
                Calculate Full Quote
              </button>
            </div>
            
            {/* Transmission Line Only Section */}
            <div style={{ 
              padding: '16px', 
              background: 'rgba(255, 255, 255, 0.05)', 
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '4px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'white', fontWeight: '500' }}>
                    <Cable size={16} />
                    Transmission Line Cost Only
                  </div>
                  <div style={{ fontSize: '0.75rem', opacity: 0.6, marginTop: '4px' }}>
                    Calculate just the cost of building a transmission line between two locations
                  </div>
                </div>
                <button
                  onClick={calculateLineCost}
                  disabled={loading || !fromLocation.lat || !toLocation.lat}
                  style={{
                    padding: '10px 20px',
                    background: 'transparent',
                    border: '1px solid rgba(255,255,255,0.3)',
                    color: 'white',
                    fontWeight: '600',
                    cursor: (loading || !fromLocation.lat || !toLocation.lat) ? 'not-allowed' : 'pointer',
                    opacity: (loading || !fromLocation.lat || !toLocation.lat) ? 0.5 : 1,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    transition: 'background 0.2s'
                  }}
                  onMouseEnter={(e) => { if (!loading && fromLocation.lat && toLocation.lat) e.currentTarget.style.background = 'rgba(255,255,255,0.1)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                >
                  <Cable size={16} />
                  Calculate
                </button>
              </div>
            </div>
          </div>

          {error && (
            <div style={{ marginTop: '16px', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#EF4444', fontSize: '0.85rem' }}>
              <AlertTriangle size={14} style={{ display: 'inline', marginRight: '8px' }} />
              {error}
            </div>
          )}

          <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        </motion.div>

        {/* Results Panel */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          style={{
            border: '1px solid rgba(255,255,255,0.2)',
            padding: '24px',
            background: 'rgba(10,10,10,0.8)'
          }}
        >
          <h3 style={{ margin: '0 0 20px', fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <DollarSign size={18} />
            Cost Breakdown
          </h3>

          {!quote && !lineCost ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', opacity: 0.5 }}>
              <Calculator size={48} style={{ marginBottom: '16px', opacity: 0.3 }} />
              <div>Select a project type and locations to calculate costs</div>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
              
              {/* Total Cost - Spans Full Width */}
              {(quote || (lineCost && !quote)) && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  style={{ gridColumn: 'span 2' }}
                >
                  <div style={{
                    padding: '24px',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    textAlign: 'center',
                    borderRadius: '12px',
                    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)',
                    backdropFilter: 'blur(10px)',
                    transition: 'transform 0.3s ease, border-color 0.3s ease',
                    cursor: 'default'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-4px)';
                    e.currentTarget.style.borderColor = 'rgba(255,255,255,0.3)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
                  }}
                  >
                    <div style={{ fontSize: '0.8rem', opacity: 0.7, marginBottom: '8px', letterSpacing: '1px' }}>
                      {quote ? 'TOTAL PROJECT COST' : 'TOTAL LINE COST'}
                    </div>
                    <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'white', textShadow: '0 0 20px rgba(255,255,255,0.2)' }}>
                      {formatINR(quote ? quote.total_project_cost : (lineCost?.total_line_cost || 0))}
                    </div>
                    {quote && (
                      <div style={{ fontSize: '0.75rem', opacity: 0.6, marginTop: '4px' }}>
                        {quote.category} • {quote.voltage_level || 'N/A'}
                      </div>
                    )}
                    {lineCost && !quote && (
                      <div style={{ fontSize: '0.75rem', opacity: 0.6, marginTop: '4px' }}>
                        {lineCost.voltage_kv}kV Transmission Line • {lineCost.distance_km.toFixed(1)} km
                      </div>
                    )}
                  </div>
                </motion.div>
              )}

              {/* Substation Cost */}
              {quote?.substation_cost && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  style={{ 
                    gridColumn: lineCost ? 'span 1' : 'span 2',
                    padding: '20px', 
                    background: 'rgba(20, 20, 20, 0.6)', 
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '12px',
                    display: 'flex',
                    flexDirection: 'column'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', paddingBottom: '12px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                    <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.2)' }}>
                      <Building2 size={18} color="#10B981" />
                    </div>
                    <span style={{ fontWeight: '600' }}>Substation Cost</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: '12px', fontSize: '0.9rem', flex: 1 }}>
                    <div style={{ opacity: 0.7 }}>Material Cost</div>
                    <div style={{ textAlign: 'right', fontWeight: '500' }}>{formatINR(quote.substation_cost.cost_of_material)}</div>
                    
                    <div style={{ opacity: 0.7 }}>Service Cost</div>
                    <div style={{ textAlign: 'right', fontWeight: '500' }}>{formatINR(quote.substation_cost.service_cost)}</div>
                    
                    <div style={{ opacity: 0.7 }}>Turnkey Charges</div>
                    <div style={{ textAlign: 'right', fontWeight: '500' }}>{formatINR(quote.substation_cost.turnkey_charges)}</div>
                    
                    {quote.substation_cost.civil_works_cost && quote.substation_cost.civil_works_cost > 0 ? (
                      <>
                        <div style={{ color: '#EAB308', opacity: 0.9 }}>Civil Works</div>
                        <div style={{ textAlign: 'right', color: '#EAB308', fontWeight: '500' }}>{formatINR(quote.substation_cost.civil_works_cost)}</div>
                      </>
                    ) : null}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                    <div style={{ fontWeight: '600' }}>Total</div>
                    <div style={{ fontWeight: 'bold', color: '#10B981' }}>{formatINR(quote.substation_cost.total)}</div>
                  </div>
                </motion.div>
              )}

              {/* Line Cost */}
              {lineCost && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  style={{ 
                    gridColumn: quote?.substation_cost ? 'span 1' : 'span 2',
                    padding: '20px', 
                    background: 'rgba(20, 20, 20, 0.6)', 
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '12px',
                    display: 'flex',
                    flexDirection: 'column'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', paddingBottom: '12px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                    <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(245, 158, 11, 0.2)' }}>
                      <Cable size={18} color="#F59E0B" />
                    </div>
                    <span style={{ fontWeight: '600' }}>Line Cost</span>
                  </div>
                  
                  {/* Key Stats Grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '16px' }}>
                     <div style={{ padding: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '6px', textAlign: 'center' }}>
                        <div style={{ fontSize: '0.7rem', opacity: 0.6 }}>Distance</div>
                        <div style={{ fontWeight: '600', color: '#60A5FA' }}>{lineCost.distance_km.toFixed(1)} km</div>
                     </div>
                     <div style={{ padding: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '6px', textAlign: 'center' }}>
                        <div style={{ fontSize: '0.7rem', opacity: 0.6 }}>Towers</div>
                        <div style={{ fontWeight: '600' }}>{lineCost.total_towers}</div>
                     </div>
                     <div style={{ padding: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '6px', textAlign: 'center' }}>
                        <div style={{ fontSize: '0.7rem', opacity: 0.6 }}>Twrs/km</div>
                        <div style={{ fontWeight: '600' }}>{lineCost.towers_per_km.toFixed(1)}</div>
                     </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: '8px', fontSize: '0.85rem' }}>
                    <div style={{ opacity: 0.7 }}>Tower Cost</div>
                    <div style={{ textAlign: 'right' }}>{formatINR(lineCost.breakdown.tower_cost)}</div>
                    <div style={{ opacity: 0.7 }}>Conductor Cost</div>
                    <div style={{ textAlign: 'right' }}>{formatINR(lineCost.breakdown.conductor_cost)}</div>
                    <div style={{ opacity: 0.7 }}>Foundation Cost</div>
                    <div style={{ textAlign: 'right' }}>{formatINR(lineCost.breakdown.foundation_cost)}</div>
                  </div>
                  
                  <div style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between' }}>
                    <div style={{ fontWeight: '600' }}>Line Total</div>
                    <div style={{ fontWeight: 'bold', color: '#F59E0B' }}>{formatINR(lineCost.total_line_cost)}</div>
                  </div>
                </motion.div>
              )}

              {/* Materials Summary - Spans Full Width */}
              {quote && quote.materials.length > 0 && (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  style={{ 
                    gridColumn: 'span 2',
                    padding: '20px', 
                    background: 'rgba(20, 20, 20, 0.4)', 
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '12px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                    <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(139, 92, 246, 0.2)' }}>
                      <Package size={18} color="#8B5CF6" />
                    </div>
                    <span style={{ fontWeight: '600' }}>Top Materials ({quote.total_items} items)</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    {quote.materials.slice(0, 8).map((mat, idx) => (
                      <div key={idx} style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        padding: '10px',
                        marginBottom: '8px',
                        background: 'rgba(255,255,255,0.03)',
                        borderRadius: '6px',
                        border: '1px solid rgba(255,255,255,0.05)'
                      }}>
                        <div style={{ fontSize: '0.8rem', opacity: 0.9, paddingRight: '10px' }}>{mat.description.substring(0, 40)}{mat.description.length > 40 ? '...' : ''}</div>
                        <div style={{ color: '#8B5CF6', fontWeight: '500', fontSize: '0.85rem', whiteSpace: 'nowrap' }}>{formatINR(mat.cost)}</div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default CostCalculator;
