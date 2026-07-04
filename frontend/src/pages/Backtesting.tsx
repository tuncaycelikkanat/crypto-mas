import React, { useState } from 'react';
import axios from 'axios';

const Backtesting: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<any>(null);

  const handleRunBacktest = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = {
        exchange: "MOCK",
        symbols: ["BTCUSDT"],
        timeframe: "1h",
        strategy_name: "multi_agent",
        start_time: "2024-01-01T00:00:00Z",
        end_time: "2024-01-07T00:00:00Z",
        initial_balance: 10000.0
      };
      
      const res = await axios.post('/api/v1/backtest/run', payload);
      
      // Auto-poll
      const interval = setInterval(async () => {
        try {
          const statusRes = await axios.get(`/api/v1/backtest/${res.data.job_id}/status`);
          setStatus(statusRes.data);
          if (statusRes.data.status === 'COMPLETED' || statusRes.data.status === 'FAILED') {
            clearInterval(interval);
            setLoading(false);
          }
        } catch (e) {
          console.error(e);
        }
      }, 2000);
      
    } catch (error) {
      console.error(error);
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>Backtesting Engine</h1>
        <p className="text-muted">Simulate your strategies against historical data.</p>
      </div>

      <div className="grid-cols-3">
        <div className="glass-card" style={{ padding: '24px', gridColumn: 'span 1' }}>
          <h3 style={{ marginBottom: '24px' }}>New Backtest</h3>
          <form onSubmit={handleRunBacktest} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Strategy</label>
              <select className="form-input">
                <option value="multi_agent">Multi-Agent AI</option>
                <option value="macd_cross">MACD Cross</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Date Range (Placeholder)</label>
              <input type="text" className="form-input" disabled value="2024-01-01 to 2024-01-07" />
            </div>
            <button type="submit" className="btn-primary" disabled={loading} style={{ marginTop: '16px' }}>
              {loading ? 'Running...' : 'Run Simulation'}
            </button>
          </form>
        </div>

        <div className="glass-card" style={{ padding: '24px', gridColumn: 'span 2' }}>
          <h3 style={{ marginBottom: '24px' }}>Current Job Status</h3>
          {status ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="flex-between">
                <span className="text-muted">Job ID:</span>
                <code>{status.job_id}</code>
              </div>
              <div className="flex-between">
                <span className="text-muted">Status:</span>
                <span className={`badge ${status.status === 'COMPLETED' ? 'badge-success' : 'badge-primary'}`}>
                  {status.status}
                </span>
              </div>
              {status.status === 'COMPLETED' && (
                <>
                  <div className="flex-between">
                    <span className="text-muted">Final Equity:</span>
                    <span className="text-success">${status.final_equity?.toFixed(2)}</span>
                  </div>
                  <div className="flex-between">
                    <span className="text-muted">Win Rate:</span>
                    <span>{(status.win_rate * 100).toFixed(2)}%</span>
                  </div>
                  <div className="flex-between">
                    <span className="text-muted">Max Drawdown:</span>
                    <span className="text-danger">{(status.max_drawdown * 100).toFixed(2)}%</span>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No active backtest job.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Backtesting;
