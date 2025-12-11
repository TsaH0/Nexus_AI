
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  TrendingUp, AlertTriangle, 
  BarChart2, ArrowRight, Brain, 
  Layers, DollarSign,
  ShoppingCart
} from 'lucide-react';
import forecastApi from '../services/forecastApi';
import type { 
  ForecastResponse, 
  Recommendation, 
  InventoryImpactResponse 
} from '../services/forecastApi';

const Forecast = () => {
  const [activeTab, setActiveTab] = useState<'overview' | 'recommendations' | 'impact'>('overview');
  const [period, setPeriod] = useState<'weekly' | 'monthly' | 'quarterly'>('monthly');
  const [loading, setLoading] = useState(true);
  
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [impactData, setImpactData] = useState<InventoryImpactResponse | null>(null);

  useEffect(() => {
    fetchData();
  }, [period]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const forecast = await forecastApi.getForecast(period);
      setForecastData(forecast);
      
      const recs = await forecastApi.getRecommendations();
      setRecommendations(recs.recommendations);
      
      const impact = await forecastApi.getInventoryImpact();
      setImpactData(impact);
      
    } catch (error) {
      console.error("Failed to fetch forecast data", error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'optimal': return '#10B981'; // Emerald (Keep for data)
      case 'under_ordered': return '#EF4444'; // Red (Critical data)
      case 'over_ordered': return '#F59E0B'; // Amber (Warning data)
      case 'inventory_adjusted': return '#ffffff'; // White (instead of Blue/Purple)
      default: return '#fff';
    }
  };

  return (
    <div style={{ padding: '20px', color: '#fff', maxWidth: '1400px', margin: '0 auto', fontFamily: 'Inter, sans-serif' }}>
      
      {/* Header */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ marginBottom: '30px', display: 'flex', justifyContent: 'space-between', alignItems: 'end' }}
      >
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Brain size={32} color="#ffffff" />
            Demand AI & Forecasting
          </h1>
          <p style={{ color: '#aaa', marginTop: '8px' }}>
            Predictive analytics for smart supply chain orchestration.
          </p>
        </div>

        {/* Period Selector */}
        <div style={{ display: 'flex', background: 'rgba(255,255,255,0.05)', padding: '4px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
          {(['weekly', 'monthly', 'quarterly'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              style={{
                background: period === p ? 'rgba(255,255,255,0.1)' : 'transparent',
                border: 'none',
                color: period === p ? '#fff' : '#888',
                padding: '8px 16px',
                borderRadius: '6px',
                cursor: 'pointer',
                textTransform: 'capitalize',
                fontWeight: period === p ? 'bold' : 'normal',
                transition: 'all 0.2s',
                fontSize: '0.9rem'
              }}
            >
              {p}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Summary Cards */}
      {forecastData && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px', marginBottom: '30px' }}>
          {[
            { 
              label: 'Total Forecast', 
              value: forecastData.summary.total_forecast.toLocaleString(), 
              icon: <TrendingUp size={20} color="#ffffff" />,
              sub: 'Predicted Units'
            },
            { 
              label: 'Total Ordered', 
              value: forecastData.summary.total_ordered.toLocaleString(), 
              icon: <ShoppingCart size={20} color="#ffffff" />,
              sub: `${forecastData.summary.coverage_percent}% Coverage`
            },
            { 
              label: 'Under Ordered', 
              value: forecastData.summary.regions_under, 
              icon: <AlertTriangle size={20} color="#ffffff" />,
              sub: 'Regions at Risk'
            },
            { 
              label: 'Smart Adjusted', 
              value: forecastData.summary.regions_inventory_adjusted, 
              icon: <Layers size={20} color="#ffffff" />,
              sub: 'Using Existing Stock'
            }
          ].map((card, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              style={{
                background: 'rgba(20, 20, 22, 0.6)',
                border: '1px solid rgba(255,255,255,0.1)',
                padding: '20px',
                borderRadius: '12px',
                backdropFilter: 'blur(10px)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span style={{ color: '#888', fontSize: '0.9rem' }}>{card.label}</span>
                {card.icon}
              </div>
              <div style={{ fontSize: '1.8rem', fontWeight: 'bold' }}>{card.value}</div>
              <div style={{ color: '#666', fontSize: '0.8rem', marginTop: '4px' }}>{card.sub}</div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', marginBottom: '30px', display: 'flex', gap: '30px' }}>
        {[
          { id: 'overview', label: 'Overview & Comparison', icon: <BarChart2 size={18} /> },
          { id: 'recommendations', label: 'Smart Recommendations', icon: <Brain size={18} /> },
          { id: 'impact', label: 'Inventory Impact', icon: <DollarSign size={18} /> }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            style={{
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === tab.id ? '2px solid #ffffff' : '2px solid transparent',
              color: activeTab === tab.id ? '#fff' : '#666',
              padding: '12px 0',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '1rem',
              transition: 'all 0.2s'
            }}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>Running Predictive Models...</div>
      ) : (
        <div style={{ minHeight: '400px' }}>
          
          {/* OVERVIEW TAB */}
          {activeTab === 'overview' && forecastData && (
            <div style={{ display: 'grid', gap: '16px' }}>
              {forecastData.forecasts.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                   No forecast data available. Ensure database is seeded.
                </div>
              ) : (
                forecastData.forecasts.map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.05)',
                    padding: '16px 24px',
                    borderRadius: '8px',
                    display: 'grid',
                    gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr 1.5fr',
                    alignItems: 'center',
                    gap: '20px'
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 'bold', fontSize: '1rem' }}>{item.region_name}</div>
                    <div style={{ color: '#888', fontSize: '0.85rem' }}>{item.material_name}</div>
                  </div>
                  
                  <div>
                    <div style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase' }}>Forecast</div>
                    <div style={{ fontSize: '1.1rem' }}>{item.forecast_quantity}</div>
                  </div>
                  
                  <div>
                    <div style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase' }}>Ordered</div>
                    <div style={{ fontSize: '1.1rem', color: '#fff' }}>
                      {item.ordered_quantity}
                    </div>
                  </div>
                  
                  <div>
                    <div style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase' }}>Inventory</div>
                    <div style={{ fontSize: '1.1rem' }}>{item.existing_inventory}</div>
                  </div>

                  <div>
                     <div style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase' }}>Variance</div>
                     <div style={{ 
                       color: Math.abs(item.variance_percent) < 10 ? '#10B981' : 
                              item.variance_percent > 20 ? '#F59E0B' : 
                              item.variance_percent < -20 ? '#EF4444' : '#fff',
                       fontWeight: 'bold'
                     }}>
                       {item.variance_percent > 0 ? '+' : ''}{item.variance_percent.toFixed(1)}%
                     </div>
                     <div style={{ fontSize: '0.7rem', color: '#666' }}>
                       {item.variance > 0 ? `+${item.variance.toLocaleString()}` : item.variance.toLocaleString()} units
                     </div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ 
                      display: 'inline-block',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      background: `rgba(255,255,255,0.05)`,
                      color: item.order_status === 'optimal' ? '#fff' : getStatusColor(item.order_status),
                      fontSize: '0.75rem',
                      textAlign: 'center',
                      fontWeight: 'bold',
                      border: `1px solid rgba(255,255,255,0.1)`
                    }}>
                      {item.order_status.replace('_', ' ').toUpperCase()}
                    </div>
                  </div>

                </motion.div>
                ))
              )}
            </div>
          )}

          {/* RECOMMENDATIONS TAB */}
          {activeTab === 'recommendations' && (
             <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
               {recommendations.map((rec, i) => (
                 <motion.div
                   key={i}
                   initial={{ opacity: 0, scale: 0.95 }}
                   animate={{ opacity: 1, scale: 1 }}
                   transition={{ delay: i * 0.05 }}
                   style={{
                     background: 'rgba(20, 20, 22, 0.6)',
                     border: `1px solid ${rec.priority === 'critical' ? '#EF4444' : 'rgba(255,255,255,0.1)'}`,
                     borderRadius: '12px',
                     padding: '20px',
                     position: 'relative',
                     overflow: 'hidden'
                   }}
                 >
                   {rec.priority === 'critical' && (
                     <div style={{ position: 'absolute', top: 0, right: 0, background: '#EF4444', color: '#fff', fontSize: '0.7rem', padding: '2px 8px', borderBottomLeftRadius: '8px' }}>
                        CRITICAL
                     </div>
                   )}
                   
                   <div style={{ marginBottom: '16px' }}>
                     <div style={{ fontSize: '0.85rem', color: '#888' }}>{rec.warehouse}</div>
                     <div style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>{rec.material}</div>
                   </div>

                   <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px', background: 'rgba(255,255,255,0.05)', padding: '10px', borderRadius: '8px' }}>
                     <div>
                       <div style={{ fontSize: '0.7rem', color: '#888' }}>Current</div>
                       <div style={{ fontSize: '1rem', color: '#ccc' }}>{rec.current_order}</div>
                     </div>
                     <div style={{ textAlign: 'right' }}>
                       <div style={{ fontSize: '0.7rem', color: '#888' }}>Recommended</div>
                       <div style={{ fontSize: '1.2rem', color: '#fff', fontWeight: 'bold' }}>{rec.recommended_order}</div>
                     </div>
                   </div>

                   <div style={{ fontSize: '0.85rem', color: '#aaa', fontStyle: 'italic', marginBottom: '16px' }}>
                     "{rec.reason}"
                   </div>

                   <button style={{ 
                     width: '100%', 
                     padding: '10px', 
                     background: '#fff', 
                     color: '#000', 
                     border: 'none', 
                     borderRadius: '6px',
                     cursor: 'pointer',
                     fontWeight: 'bold',
                     display: 'flex',
                     justifyContent: 'center',
                     alignItems: 'center',
                     gap: '8px'
                   }}>
                     Accept Recommendation <ArrowRight size={16} />
                   </button>
                 </motion.div>
               ))}
             </div>
          )}

          {/* IMPACT TAB */}
          {activeTab === 'impact' && impactData && (
             <div>
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  style={{ 
                    background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    padding: '30px',
                    borderRadius: '16px',
                    marginBottom: '30px',
                    textAlign: 'center'
                  }}
                >
                   <h2 style={{ margin: '0 0 10px 0', fontSize: '1.5rem' }}>Inventory Optimization Impact</h2>
                   <p style={{ fontSize: '1.1rem', color: '#ddd' }}>{impactData.message}</p>
                   
                   <div style={{ display: 'flex', justifyContent: 'center', gap: '40px', marginTop: '20px' }}>
                      <div>
                         <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#fff' }}>
                           {impactData.analysis.total_units_order_reduced.toLocaleString()}
                         </div>
                         <div style={{ textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '1px', opacity: 0.7 }}>Units Reduced</div>
                      </div>
                      <div style={{ width: '1px', background: 'rgba(255,255,255,0.2)'}}></div>
                      <div>
                         <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#fff' }}>
                           {impactData.analysis.total_existing_inventory_units.toLocaleString()}
                         </div>
                         <div style={{ textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '1px', opacity: 0.7 }}>Inventory Utilized</div>
                      </div>
                   </div>
                </motion.div>

                <div style={{ display: 'grid', gap: '12px' }}>
                   {impactData.details.map((item, i) => (
                      <div key={i} style={{ 
                         background: 'rgba(255,255,255,0.03)', 
                         padding: '16px', 
                         borderRadius: '8px',
                         display: 'flex',
                         justifyContent: 'space-between',
                         alignItems: 'center',
                         borderLeft: '4px solid #ffffff'
                      }}>
                         <div>
                            <div style={{ fontWeight: 'bold' }}>{item.warehouse} - {item.material}</div>
                            <div style={{ fontSize: '0.85rem', color: '#aaa', marginTop: '4px' }}>{item.inventory_utilization}</div>
                         </div>
                         <div style={{ textAlign: 'right' }}>
                            <div style={{ color: '#fff', fontWeight: 'bold' }}>{item.benefit}</div>
                            <div style={{ fontSize: '0.8rem', color: '#666' }}>Instead of ordering {item.forecast} units</div>
                         </div>
                      </div>
                   ))}
                </div>
             </div>
          )}

        </div>
      )}
    </div>
  );
};

export default Forecast;
