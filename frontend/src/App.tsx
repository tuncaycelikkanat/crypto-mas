import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import { Welcome } from './pages/Welcome';
import Dashboard from './pages/Dashboard';
import MarketRadar from './pages/MarketRadar';
import Backtesting from './pages/Backtesting';
import Decisions from './pages/Decisions';
import PaperTrading from './pages/PaperTrading';
import LiveLogs from './pages/LiveLogs';
import { AutoOptimizer } from './pages/AutoOptimizer';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Welcome />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="radar" element={<MarketRadar />} />
          <Route path="paper" element={<PaperTrading />} />
          <Route path="backtesting" element={<Backtesting />} />
          <Route path="optimization" element={<AutoOptimizer />} />
          <Route path="logs" element={<LiveLogs />} />
          <Route path="decisions" element={<Decisions />} />
          {/* Fallback to Welcome */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
