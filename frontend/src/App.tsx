
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Backtesting from './pages/Backtesting';
import Decisions from './pages/Decisions';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="backtesting" element={<Backtesting />} />
          <Route path="decisions" element={<Decisions />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
