import React from 'react';

const Decisions: React.FC = () => {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>Strategy Decisions</h1>
        <p className="text-muted">A detailed log of why the system took specific actions.</p>
      </div>

      <div className="glass-card" style={{ padding: '24px' }}>
        <table className="glass-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Symbol</th>
              <th>Action</th>
              <th>Confidence</th>
              <th>Reasoning Log</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>10:00:00 AM</td>
              <td>BTCUSDT</td>
              <td><span className="badge badge-success">CONSIDER_LONG</span></td>
              <td>85%</td>
              <td className="text-muted" style={{ fontSize: '0.85rem' }}>
                AI Agents consensus. Trend=Bullish, Score=0.85. Risk=1.0x.
              </td>
            </tr>
            <tr>
              <td>09:00:00 AM</td>
              <td>ETHUSDT</td>
              <td><span className="badge badge-danger">AVOID</span></td>
              <td>0%</td>
              <td className="text-muted" style={{ fontSize: '0.85rem' }}>
                Regime=HIGH_VOLATILITY. All signals blocked.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Decisions;
