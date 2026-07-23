
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
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
          <Route index element={<Dashboard />} />
          <Route path="radar" element={<MarketRadar />} />
          <Route path="backtesting" element={<Backtesting />} />
          <Route path="paper" element={<PaperTrading />} />
          <Route path="decisions" element={<Decisions />} />
          <Route path="logs" element={<LiveLogs />} />
          <Route path="optimization" element={<AutoOptimizer />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
