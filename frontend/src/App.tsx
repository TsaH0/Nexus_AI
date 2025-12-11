
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import Layout from './components/Layout';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Substations from './pages/Substations';
import Inventory from './pages/Inventory';
import CostCalculator from './pages/CostCalculator';
import Forecast from './pages/Forecast';
import Scene from './components/Scene';
import VideoBackground from './components/VideoBackground';
import DotsBackground from './components/DotsBackground';

function BackgroundSelector() {
  const location = useLocation();
  
  if (location.pathname === '/') {
    return <VideoBackground />;
  } else if (location.pathname === '/inventory' || location.pathname === '/calculator' || location.pathname === '/forecast') {
    return <DotsBackground />;
  } else {
    return <Scene />;
  }
}

function App() {
  return (
    <Router>
      <BackgroundSelector />
      <Layout>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/substations" element={<Substations />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/forecast" element={<Forecast />} />
          <Route path="/calculator" element={<CostCalculator />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
