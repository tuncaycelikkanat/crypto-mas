import React from 'react';
import { TrendingUp, Activity, BarChart2, DollarSign } from 'lucide-react';

const StatCard = ({ title, value, change, icon: Icon, isPositive }: any) => (
  <div className="glass-card" style={{ padding: '24px' }}>
    <div className="flex-between" style={{ marginBottom: '16px' }}>
      <h3 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 500, margin: 0 }}>{title}</h3>
      <div style={{ background: 'rgba(255,255,255,0.05)', padding: '8px', borderRadius: '8px' }}>
        <Icon size={20} color="var(--primary)" />
      </div>
    </div>
    <div style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '8px' }}>{value}</div>
    {change && (
      <div style={{ fontSize: '0.85rem', color: isPositive ? 'var(--success)' : 'var(--danger)', display: 'flex', alignItems: 'center', gap: '4px' }}>
        <TrendingUp size={14} style={{ transform: isPositive ? 'none' : 'rotate(180deg)' }} />
        <span>{change} this week</span>
      </div>
    )}
  </div>
);

const Dashboard: React.FC = () => {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>Dashboard Overview</h1>
        <p className="text-muted">Welcome back. Here's how your strategies are performing.</p>
      </div>

      <div className="grid-cols-3" style={{ marginBottom: '32px' }}>
        <StatCard title="Total PnL" value="$12,450.00" change="+14.5%" icon={DollarSign} isPositive={true} />
        <StatCard title="Win Rate" value="68.4%" change="+2.1%" icon={Activity} isPositive={true} />
        <StatCard title="Active Positions" value="4" icon={BarChart2} />
      </div>

      <div className="glass-card" style={{ padding: '24px' }}>
        <h3 style={{ marginBottom: '24px' }}>Recent Trading Cycles</h3>
        <table className="glass-table">
          <thead>
            <tr>
              <th>Cycle ID</th>
              <th>Account</th>
              <th>Status</th>
              <th>Strategy</th>
              <th>PnL</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>#1024</td>
              <td>live-binance-1</td>
              <td><span className="badge badge-success">COMPLETED</span></td>
              <td>multi_agent</td>
              <td className="text-success">+$124.50</td>
            </tr>
            <tr>
              <td>#1023</td>
              <td>live-binance-1</td>
              <td><span className="badge badge-success">COMPLETED</span></td>
              <td>macd_cross</td>
              <td className="text-danger">-$45.20</td>
            </tr>
            <tr>
              <td>#1022</td>
              <td>backtest-job-9a</td>
              <td><span className="badge badge-primary">RUNNING</span></td>
              <td>multi_agent</td>
              <td className="text-muted">--</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Dashboard;
