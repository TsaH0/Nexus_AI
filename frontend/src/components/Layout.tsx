import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Github, Radio, Home, LayoutDashboard, Warehouse, Calculator, Brain } from 'lucide-react';
import Logo from './Logo';

interface LayoutProps {
  children: ReactNode;
  showNav?: boolean;
}

const Layout = ({ children, showNav = true }: LayoutProps) => {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <div style={{ position: 'relative', zIndex: 1, minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {showNav && (
        <nav style={{ 
          padding: '20px 40px', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          backdropFilter: 'blur(5px)',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          background: 'rgba(0,0,0,0.5)',
          gap: '60px'
        }}>
          <Link to="/" style={{ textDecoration: 'none', color: 'white', display: 'flex', alignItems: 'center' }}>
            <Logo size={32} showText={true} />
          </Link>
          <div style={{ display: 'flex', gap: '30px', alignItems: 'center', marginLeft: 'auto' }}>
            <Link 
                to="/" 
                style={{ 
                    color: 'white', 
                    textDecoration: 'none', 
                    opacity: isActive('/') ? 1 : 0.6,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    transition: 'opacity 0.2s',
                    fontWeight: 'bold'
                }}
            >
                <Home size={18} />
                <span>Home</span>
            </Link>
            <Link 
                to="/dashboard" 
                style={{ 
                    color: 'white', 
                    textDecoration: 'none', 
                    opacity: isActive('/dashboard') ? 1 : 0.6,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    transition: 'opacity 0.2s',
                    fontWeight: 'bold'
                }}
            >
                <LayoutDashboard size={18} />
                <span>Dashboard</span>
            </Link>
            <Link 
                to="/substations" 
                style={{ 
                    color: 'white', 
                    textDecoration: 'none', 
                    opacity: isActive('/substations') ? 1 : 0.6,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    transition: 'opacity 0.2s',
                    fontWeight: 'bold'
                }}
            >
                <Radio size={18} />
                <span>Substations</span>
            </Link>

            <Link 
                to="/inventory" 
                style={{ 
                    color: 'white', 
                    textDecoration: 'none', 
                    opacity: isActive('/inventory') ? 1 : 0.6,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    transition: 'opacity 0.2s',
                    fontWeight: 'bold'
                }}
            >
                <Warehouse size={18} />
                <span>Inventory</span>
            </Link>
            <Link 
                to="/forecast" 
                style={{ 
                    color: 'white', 
                    textDecoration: 'none', 
                    opacity: isActive('/forecast') ? 1 : 0.6,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    transition: 'opacity 0.2s',
                    fontWeight: 'bold'
                }}
            >
                <Brain size={18} />
                <span>Forecast</span>
            </Link>
            <Link 
                to="/calculator" 
                style={{ 
                    color: 'white', 
                    textDecoration: 'none', 
                    opacity: isActive('/calculator') ? 1 : 0.6,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    transition: 'opacity 0.2s',
                    fontWeight: 'bold'
                }}
            >
                <Calculator size={18} />
                <span>Calculator</span>
            </Link>
             <a href="https://github.com" target="_blank" rel="noreferrer" style={{ color: 'white', opacity: 0.6, transition: 'opacity 0.2s' }}>
                <Github size={20}/>
             </a>
          </div>
        </nav>
      )}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {children}
      </main>
    </div>
  );
};

export default Layout;
