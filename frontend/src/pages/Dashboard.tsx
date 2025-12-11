import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { 
  TrendingUp, 
  Zap, 
  Package, 
  AlertTriangle, 
  Calendar, 
  Activity, 
  Radio,
  MapPin,
  Building2,
  RefreshCw,
  Loader2,
  AlertCircle,
  Clock,
  ChevronRight
} from 'lucide-react';
import type { 
  DashboardSummary, 
  SubstationWithDetails, 
  StateStats,
  SubstationProject
} from '../services/substationsApi';
import substationsApi from '../services/substationsApi';

// Simple Pie Chart Component
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

// Progress Bar Component
const ProgressBar = ({ value, max, color = '#10B981' }: { value: number; max: number; color?: string }) => {
  const percentage = max > 0 ? (value / max) * 100 : 0;
  return (
    <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${percentage}%` }}
        transition={{ duration: 1, delay: 0.3 }}
        style={{ height: '100%', background: color, borderRadius: '4px' }}
      />
    </div>
  );
};

const Dashboard = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const targetName = searchParams.get('target');

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [understocked, setUnderstocked] = useState<SubstationWithDetails[]>([]);
  const [overstocked, setOverstocked] = useState<SubstationWithDetails[]>([]);
  const [byState, setByState] = useState<Record<string, StateStats>>({});
  const [projects, setProjects] = useState<SubstationProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [isLive, setIsLive] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [summaryData, understockedData, overstockedData, stateData] = await Promise.all([
        substationsApi.getDashboardSummary(),
        substationsApi.getUnderstockedSubstations(),
        substationsApi.getOverstockedSubstations(),
        substationsApi.getSubstationsByState()
      ]);
      
      setSummary(summaryData);
      setUnderstocked(understockedData);
      setOverstocked(overstockedData);
      setByState(stateData);
      
      // Fetch projects for substations
      const allProjects: SubstationProject[] = [];
      for (const sub of [...understockedData, ...overstockedData]) {
        try {
          const subProjects = await substationsApi.getSubstationProjects(sub.id);
          allProjects.push(...subProjects);
        } catch {
          // Skip if no projects
        }
      }
      setProjects(allProjects);
      setIsLive(true);
    } catch (err) {
      console.log('API not available:', err);
      setIsLive(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const stockStatusData = summary ? [
    { label: 'Normal', value: summary.stock_status.normal, color: '#10B981' },
    { label: 'Low', value: summary.stock_status.low, color: '#F59E0B' },
    { label: 'Understocked', value: summary.stock_status.understocked, color: '#EF4444' },
    { label: 'Overstocked', value: summary.stock_status.overstocked, color: '#3B82F6' },
  ].filter(d => d.value > 0) : [];

  const container = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
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
        <Loader2 size={40} style={{ animation: 'spin 1s linear infinite' }} />
        <div style={{ opacity: 0.7 }}>Loading dashboard data...</div>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

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
            <Activity size={28} />
            Substation Dashboard
          </h2>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            {/* Connection Status */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 12px',
              border: `1px solid ${isLive ? '#10B981' : '#F59E0B'}`,
              background: isLive ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
              fontSize: '0.75rem'
            }}>
              <div style={{ 
                width: '8px', 
                height: '8px', 
                borderRadius: '50%', 
                background: isLive ? '#10B981' : '#F59E0B',
                animation: isLive ? 'pulse 2s infinite' : 'none'
              }} />
              <span style={{ color: isLive ? '#10B981' : '#F59E0B' }}>
                {isLive ? 'LIVE' : 'OFFLINE'}
              </span>
            </div>
            
            {/* Refresh Button */}
            <button
              onClick={fetchData}
              disabled={loading}
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
          </div>
        </div>
        <div style={{ fontSize: '0.9rem', opacity: 0.7 }}>
          Overview of substation inventory status, projects, and critical alerts
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

      {/* Summary Stats Cards */}
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(6, 1fr)',
          gap: '16px',
          marginBottom: '30px'
        }}
      >
        {/* Total Substations */}
        <motion.div
          variants={item}
          style={{
            border: '1px solid rgba(255,255,255,0.2)',
            padding: '20px',
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(10,10,10,0.8) 100%)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', opacity: 0.7 }}>
            <Radio size={16} />
            <span style={{ fontSize: '0.8rem', letterSpacing: '0.5px' }}>TOTAL</span>
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#10B981' }}>
            {summary?.total_substations || 0}
          </div>
          <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>Substations</div>
        </motion.div>

        {/* Normal */}
        <motion.div
          variants={item}
          style={{
            border: '1px solid rgba(255,255,255,0.2)',
            padding: '20px',
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(10,10,10,0.8) 100%)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', opacity: 0.7 }}>
            <Zap size={16} color="#10B981" />
            <span style={{ fontSize: '0.8rem', letterSpacing: '0.5px' }}>NORMAL</span>
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#10B981' }}>
            {summary?.stock_status.normal || 0}
          </div>
          <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>Healthy stock</div>
        </motion.div>

        {/* Understocked */}
        <motion.div
          variants={item}
          style={{
            border: '1px solid rgba(239, 68, 68, 0.3)',
            padding: '20px',
            background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(10,10,10,0.8) 100%)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', opacity: 0.7 }}>
            <AlertTriangle size={16} color="#EF4444" />
            <span style={{ fontSize: '0.8rem', letterSpacing: '0.5px' }}>UNDERSTOCKED</span>
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#EF4444' }}>
            {summary?.stock_status.understocked || 0}
          </div>
          <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>Need attention</div>
        </motion.div>

        {/* Overstocked */}
        <motion.div
          variants={item}
          style={{
            border: '1px solid rgba(59, 130, 246, 0.3)',
            padding: '20px',
            background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(10,10,10,0.8) 100%)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', opacity: 0.7 }}>
            <Package size={16} color="#3B82F6" />
            <span style={{ fontSize: '0.8rem', letterSpacing: '0.5px' }}>OVERSTOCKED</span>
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#3B82F6' }}>
            {summary?.stock_status.overstocked || 0}
          </div>
          <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>Transfer ready</div>
        </motion.div>

        {/* Critical Alerts */}
        <motion.div
          variants={item}
          style={{
            border: '1px solid rgba(239, 68, 68, 0.3)',
            padding: '20px',
            background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(10,10,10,0.8) 100%)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', opacity: 0.7 }}>
            <AlertCircle size={16} color="#EF4444" />
            <span style={{ fontSize: '0.8rem', letterSpacing: '0.5px' }}>CRITICAL</span>
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#EF4444' }}>
            {summary?.critical_alerts || 0}
          </div>
          <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>Material alerts</div>
        </motion.div>

        {/* Active Projects */}
        <motion.div
          variants={item}
          style={{
            border: '1px solid rgba(139, 92, 246, 0.3)',
            padding: '20px',
            background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(10,10,10,0.8) 100%)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', opacity: 0.7 }}>
            <Calendar size={16} color="#8B5CF6" />
            <span style={{ fontSize: '0.8rem', letterSpacing: '0.5px' }}>PROJECTS</span>
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#8B5CF6' }}>
            {summary?.active_projects || 0}
          </div>
          <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>
            {summary?.delayed_projects || 0} delayed
          </div>
        </motion.div>
      </motion.div>

      {/* Main Content Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '24px', marginBottom: '30px' }}>
        
        {/* Stock Status Pie Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          style={{
            border: '1px solid rgba(255,255,255,0.2)',
            padding: '24px',
            background: 'rgba(10,10,10,0.8)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <h3 style={{ margin: '0 0 20px', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp size={18} />
            Stock Status Distribution
          </h3>
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            {stockStatusData.length > 0 ? (
              <SimplePieChart data={stockStatusData} size={150} />
            ) : (
              <div style={{ opacity: 0.5, padding: '40px 0' }}>No data</div>
            )}
          </div>
          {summary && (
            <div style={{ marginTop: '20px', padding: '12px', background: 'rgba(0,0,0,0.3)', textAlign: 'center' }}>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#10B981' }}>
                {summary.average_stock_level}%
              </div>
              <div style={{ fontSize: '0.7rem', opacity: 0.6 }}>Average Stock Level</div>
            </div>
          )}
        </motion.div>

        {/* By State */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          style={{
            border: '1px solid rgba(255,255,255,0.2)',
            padding: '24px',
            background: 'rgba(10,10,10,0.8)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <h3 style={{ margin: '0 0 20px', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <MapPin size={18} />
            Substations by State
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {Object.entries(byState).map(([state, stats]) => (
              <div key={state} style={{ padding: '12px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontWeight: '500' }}>{state}</span>
                  <span style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{stats.count}</span>
                </div>
                <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem' }}>
                  <span style={{ color: '#10B981' }}>✓ {stats.normal}</span>
                  <span style={{ color: '#EF4444' }}>↓ {stats.understocked}</span>
                  <span style={{ color: '#3B82F6' }}>↑ {stats.overstocked}</span>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Understocked Alert */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          style={{
            border: '1px solid rgba(239, 68, 68, 0.3)',
            padding: '24px',
            background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.05) 0%, rgba(10,10,10,0.8) 100%)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <h3 style={{ margin: '0 0 20px', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px', color: '#EF4444' }}>
            <AlertTriangle size={18} />
            Understocked Substations
          </h3>
          {(targetName ? understocked.filter(s => s.name === targetName) : understocked).length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {(targetName ? understocked.filter(s => s.name === targetName) : understocked).map(sub => (
                <div key={sub.id} style={{ padding: '12px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '8px' }}>
                    <div>
                      <div style={{ fontWeight: '500', marginBottom: '2px' }}>{sub.name}</div>
                      <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>{sub.city}, {sub.state}</div>
                    </div>
                    <div style={{ 
                      padding: '4px 8px', 
                      background: 'rgba(239, 68, 68, 0.2)', 
                      color: '#EF4444',
                      fontSize: '0.8rem',
                      fontWeight: '600'
                    }}>
                      {sub.stock_level_percentage}%
                    </div>
                  </div>
                  <ProgressBar value={sub.stock_level_percentage} max={100} color="#EF4444" />
                  {sub.critical_materials.length > 0 && (
                    <div style={{ marginTop: '8px', fontSize: '0.7rem', opacity: 0.7 }}>
                      Critical: {sub.critical_materials.map(m => m.material_name).join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ opacity: 0.5, textAlign: 'center', padding: '30px 0' }}>
              ✓ No understocked substations
            </div>
          )}
        </motion.div>
      </div>

      {/* Bottom Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        
        {/* Overstocked (Transfer Sources) */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          style={{
            border: '1px solid rgba(59, 130, 246, 0.3)',
            padding: '24px',
            background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(10,10,10,0.8) 100%)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <h3 style={{ margin: '0 0 20px', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px', color: '#3B82F6' }}>
            <Building2 size={18} />
            Overstocked (Transfer Sources)
          </h3>
          {(targetName ? overstocked.filter(s => s.name === targetName) : overstocked).length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {(targetName ? overstocked.filter(s => s.name === targetName) : overstocked).map(sub => (
                <div key={sub.id} style={{ padding: '12px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(59, 130, 246, 0.2)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: '500', marginBottom: '2px' }}>{sub.name}</div>
                    <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>{sub.city}, {sub.state}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ 
                      padding: '4px 8px', 
                      background: 'rgba(59, 130, 246, 0.2)', 
                      color: '#3B82F6',
                      fontSize: '0.8rem',
                      fontWeight: '600'
                    }}>
                      {sub.stock_level_percentage}%
                    </div>
                    <ChevronRight size={16} opacity={0.5} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ opacity: 0.5, textAlign: 'center', padding: '30px 0' }}>
              No overstocked substations
            </div>
          )}
        </motion.div>

        {/* Active Projects */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          style={{
            border: '1px solid rgba(139, 92, 246, 0.3)',
            padding: '24px',
            background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.05) 0%, rgba(10,10,10,0.8) 100%)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <h3 style={{ margin: '0 0 20px', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px', color: '#8B5CF6' }}>
            <Calendar size={18} />
            Active Projects
          </h3>
          {projects.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {projects.slice(0, 3).map(project => (
                <div key={project.id} style={{ padding: '16px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                    <div>
                      <div style={{ fontWeight: '500', marginBottom: '4px' }}>{project.name}</div>
                      <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>{project.developer}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ 
                        padding: '4px 8px', 
                        background: project.delay_days > 0 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                        color: project.delay_days > 0 ? '#EF4444' : '#10B981',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        marginBottom: '4px'
                      }}>
                        {project.status}
                      </div>
                      {project.delay_days > 0 && (
                        <div style={{ fontSize: '0.7rem', color: '#EF4444', display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'flex-end' }}>
                          <Clock size={10} />
                          {project.delay_days} days delay
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Progress */}
                  <div style={{ marginBottom: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                      <span style={{ opacity: 0.7 }}>Overall Progress</span>
                      <span style={{ fontWeight: '600', color: '#8B5CF6' }}>{project.overall_progress}%</span>
                    </div>
                    <ProgressBar value={project.overall_progress} max={100} color="#8B5CF6" />
                  </div>
                  
                  {/* Stats */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginTop: '12px', fontSize: '0.7rem' }}>
                    <div style={{ textAlign: 'center', padding: '6px', background: 'rgba(255,255,255,0.05)' }}>
                      <div style={{ fontWeight: '600' }}>{project.foundation_completed}/{project.foundation_total}</div>
                      <div style={{ opacity: 0.5 }}>Foundation</div>
                    </div>
                    <div style={{ textAlign: 'center', padding: '6px', background: 'rgba(255,255,255,0.05)' }}>
                      <div style={{ fontWeight: '600' }}>{project.tower_erected}/{project.tower_total}</div>
                      <div style={{ opacity: 0.5 }}>Towers</div>
                    </div>
                    <div style={{ textAlign: 'center', padding: '6px', background: 'rgba(255,255,255,0.05)' }}>
                      <div style={{ fontWeight: '600' }}>{project.stringing_completed_ckm}/{project.stringing_total_ckm}</div>
                      <div style={{ opacity: 0.5 }}>Stringing (CKM)</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ opacity: 0.5, textAlign: 'center', padding: '30px 0' }}>
              No active projects
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default Dashboard;
