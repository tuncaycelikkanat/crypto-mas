import React from 'react';
import { motion } from 'framer-motion';

const Decisions: React.FC = () => {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ marginBottom: 4 }}>
        <h1 style={{ marginBottom: 4 }}>Strategy Decisions</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>A detailed audit log of multi-agent execution rationale and signal barriers.</p>
      </div>

      <div className="card" style={{ padding: '22px 24px' }}>
        <table className="glass-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Symbol</th>
              <th>Action Decision</th>
              <th>Confidence</th>
              <th>Agent Reasoning Log</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="mono" style={{ color: 'var(--text-muted)' }}>10:00:00 AM</td>
              <td style={{ fontWeight: 600 }}>BTCUSDT</td>
              <td><span className="badge badge-success">CONSIDER_LONG</span></td>
              <td className="mono">85%</td>
              <td style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                Multi-agent consensus verified. Trend=Bullish, Momentum Score=0.85. Dynamic Risk=1.0x.
              </td>
            </tr>
            <tr>
              <td className="mono" style={{ color: 'var(--text-muted)' }}>09:00:00 AM</td>
              <td style={{ fontWeight: 600 }}>ETHUSDT</td>
              <td><span className="badge badge-danger">AVOID</span></td>
              <td className="mono">0%</td>
              <td style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                Regime=HIGH_VOLATILITY detected by RiskRegimeShield. All entry signals blocked to preserve equity.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </motion.div>
  );
};

export default Decisions;
