import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import Logo from '../components/Logo';
import ColorBar from '../components/ColorBar';

const Landing = () => {
  const navigate = useNavigate();

  return (
    <div style={{ 
      flex: 1,
      display: 'flex', 
      flexDirection: 'column', 
      justifyContent: 'center', 
      alignItems: 'center',
      textAlign: 'center',
      padding: '80px 40px',
      gap: '50px',
      position: 'relative'
    }}>
      {/* Color Bar - Material Distribution Legend (Upper Right) */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        style={{
          position: 'absolute',
          top: '20px',
          right: '20px',
          zIndex: 100
        }}
      >
        <ColorBar width={120} height={15} showValues={false} leftLabel="Fe" rightLabel="Cu" />
      </motion.div>

      {/* Hero Section */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '24px'
        }}
      >
        {/* Main Heading with Logo Icon */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '20px',
          marginBottom: '8px'
        }}>
          <Logo size={50} showText={false} />
          <h1 style={{ 
            fontSize: 'clamp(2.5rem, 8vw, 4.5rem)', 
            fontWeight: '900', 
            letterSpacing: '-0.02em', 
            margin: 0,
            color: '#ffffff',
            textShadow: '0 0 40px rgba(255,255,255,0.3)'
          }}>
            NEXUS AI
          </h1>
        </div>

        {/* Subheading */}
        <h2 style={{
          fontSize: 'clamp(1.3rem, 4vw, 2.2rem)',
          fontWeight: '700',
          letterSpacing: '-0.01em',
          margin: 0,
          background: 'linear-gradient(to right, rgba(255,255,255,0.9), rgba(255,255,255,0.6))',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent'
        }}>
          Transform Supply Chain Intelligence
        </h2>

        {/* Description */}
        <p style={{ 
          fontSize: '0.95rem', 
          maxWidth: '700px', 
          margin: '8px auto 0', 
          color: 'rgba(255,255,255,0.7)',
          lineHeight: '1.7',
          fontWeight: '400'
        }}>
          NEXUS is an intelligent orchestration engine that transforms POWERGRID's supply chain from reactive to proactive — preventing crises, optimizing costs, and ensuring operational excellence.
        </p>
      </motion.div>

      {/* CTA Buttons */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.3, duration: 0.5 }}
        style={{ 
          display: 'flex', 
          gap: '20px',
          flexWrap: 'wrap',
          justifyContent: 'center'
        }}
      >
        <motion.button 
          className="box-button" 
          onClick={() => navigate('/dashboard')}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '12px',
            fontSize: '1.1rem',
            padding: '18px 36px',
            background: 'rgba(255,255,255,0.95)',
            color: '#0a0a0a',
            border: '1px solid rgba(255,255,255,0.2)',
            fontWeight: '600',
            cursor: 'pointer'
          }}
        >
          Launch Dashboard <ArrowRight size={22} />
        </motion.button>

        <motion.button 
          onClick={() => {
            // Scroll to stats or show more info
            const statsSection = document.getElementById('stats-section');
            if (statsSection) {
              statsSection.scrollIntoView({ behavior: 'smooth' });
            }
          }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '12px',
            fontSize: '1.1rem',
            padding: '18px 36px',
            background: 'rgba(255,255,255,0.05)',
            color: 'rgba(255,255,255,0.9)',
            border: '1px solid rgba(255,255,255,0.3)',
            fontWeight: '600',
            cursor: 'pointer',
            backdropFilter: 'blur(10px)'
          }}
        >
          Learn More
        </motion.button>
      </motion.div>

      {/* Stats Section */}
      <motion.div
        id="stats-section"
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.8 }}
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '40px',
          maxWidth: '900px',
          width: '100%',
          marginTop: '20px'
        }}
      >
        {/* Stat 1 */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '8px'
        }}>
          <div style={{
            fontSize: 'clamp(2.5rem, 6vw, 4rem)',
            fontWeight: '900',
            background: 'linear-gradient(135deg, #ffffff, #888888)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            lineHeight: '1'
          }}>
            30%
          </div>
          <div style={{
            fontSize: '1rem',
            color: 'rgba(255,255,255,0.6)',
            fontWeight: '500',
            letterSpacing: '0.5px'
          }}>
            Reduced Delays
          </div>
        </div>

        {/* Stat 2 */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '8px'
        }}>
          <div style={{
            fontSize: 'clamp(2.5rem, 6vw, 4rem)',
            fontWeight: '900',
            background: 'linear-gradient(135deg, #ffffff, #888888)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            lineHeight: '1'
          }}>
            286+
          </div>
          <div style={{
            fontSize: '1rem',
            color: 'rgba(255,255,255,0.6)',
            fontWeight: '500',
            letterSpacing: '0.5px'
          }}>
            Substations
          </div>
        </div>

        {/* Stat 3 */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '8px'
        }}>
          <div style={{
            fontSize: 'clamp(2.5rem, 6vw, 4rem)',
            fontWeight: '900',
            background: 'linear-gradient(135deg, #ffffff, #888888)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            lineHeight: '1'
          }}>
            5-10%
          </div>
          <div style={{
            fontSize: '1rem',
            color: 'rgba(255,255,255,0.6)',
            fontWeight: '500',
            letterSpacing: '0.5px'
          }}>
            Cost Savings
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default Landing;
