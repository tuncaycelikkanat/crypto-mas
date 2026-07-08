import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { TrendingUp, Activity, BarChart2, DollarSign, Server, Database, Bot, ShieldCheck, Wallet } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { CoinDetails } from '../components/CoinDetails';

const StatCard = ({ title, value, change, icon: Icon, isPositive, valueColor }: any) => (
  <div className="glass-card" style={{ padding: '24px' }}>
    <div className="flex-between" style={{ marginBottom: '16px' }}>
      <h3 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 500, margin: 0 }}>{title}</h3>
      <div style={{ background: 'rgba(255,255,255,0.05)', padding: '8px', borderRadius: '8px' }}>
        <Icon size={20} color="var(--primary)" />
      </div>
    </div>
    <div style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '8px', color: valueColor || 'inherit' }}>{value}</div>
    {change && (
      <div style={{ fontSize: '0.85rem', color: isPositive ? 'var(--success)' : 'var(--danger)', display: 'flex', alignItems: 'center', gap: '4px' }}>
        <TrendingUp size={14} style={{ transform: isPositive ? 'none' : 'rotate(180deg)' }} />
        <span>{change}</span>
      </div>
    )}
  </div>
);

const Dashboard: React.FC = () => {
  const [sysHealth, setSysHealth] = useState<any>(null);
  const [dbHealth, setDbHealth] = useState<any>(null);
  const [botStatus, setBotStatus] = useState<any>(null);
  
  const [analyticsSummary, setAnalyticsSummary] = useState<any>(null);
  const [equityCurve, setEquityCurve] = useState<any[]>([]);
  const [tradeHistory, setTradeHistory] = useState<any[]>([]);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [healthRes, dbRes, botRes, summaryRes, equityRes, historyRes] = await Promise.all([
          axios.get('/api/v1/health').catch(() => ({ data: { status: 'error' } })),
          axios.get('/api/v1/health/db').catch(() => ({ data: { status: 'error' } })),
          axios.get('/api/v1/bot/status').catch(() => ({ data: { status: 'STOPPED' } })),
          axios.get('/api/v1/analytics/summary').catch(() => ({ data: null })),
          axios.get('/api/v1/analytics/equity-curve').catch(() => ({ data: { data: [] } })),
          axios.get('/api/v1/analytics/trade-history').catch(() => ({ data: { history: [] } }))
        ]);
        setSysHealth(healthRes.data);
        setDbHealth(dbRes.data);
        setBotStatus(botRes.data);
        
        if (summaryRes.data) setAnalyticsSummary(summaryRes.data);
        if (equityRes.data?.data) setEquityCurve(equityRes.data.data);
        if (historyRes.data?.history) setTradeHistory(historyRes.data.history);
      } catch (err) {
        console.error("Error fetching system info:", err);
      }
    };
    
    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>Dashboard Overview</h1>
        <p className="text-muted">Welcome back. Here's how your strategies are performing.</p>
      </div>

      <div className="glass-card animate-fade-in" style={{ padding: '24px', marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
          <Server size={24} color="var(--primary)" />
          <h3 style={{ margin: 0 }}>System Intelligence & Health</h3>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
          <div style={{ padding: '16px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '16px' }}>
            <ShieldCheck size={28} color={sysHealth?.status === 'ok' ? 'var(--success)' : 'var(--danger)'} />
            <div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Trading Mode</div>
              <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>{sysHealth?.mode || 'Unknown'}</div>
            </div>
          </div>
          
          <div style={{ padding: '16px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '16px' }}>
            <Activity size={28} color="var(--warning)" />
            <div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Data Provider</div>
              <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>BINANCE</div>
            </div>
          </div>
          
          <div style={{ padding: '16px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '16px' }}>
            <Bot size={28} color={botStatus?.status === 'RUNNING' ? 'var(--success)' : 'var(--text-muted)'} />
            <div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Auto Trading Bot</div>
              <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>{botStatus?.status === 'RUNNING' ? 'Active' : 'Offline'}</div>
            </div>
          </div>

          <div style={{ padding: '16px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '16px' }}>
            <Database size={28} color={dbHealth?.status === 'ok' ? 'var(--success)' : 'var(--danger)'} />
            <div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Database State</div>
              <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>{dbHealth?.status === 'ok' ? 'Connected' : 'Error'}</div>
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '24px', marginBottom: '32px' }}>
        <StatCard 
          title="Total PnL" 
          value={analyticsSummary ? `$${analyticsSummary.total_pnl.toFixed(2)}` : '$0.00'} 
          icon={DollarSign} 
          valueColor={analyticsSummary?.total_pnl >= 0 ? 'var(--success)' : 'var(--danger)'} 
        />
        <StatCard 
          title="Win Rate" 
          value={analyticsSummary ? `${analyticsSummary.win_rate.toFixed(1)}%` : '0.0%'} 
          icon={Activity} 
        />
        <StatCard 
          title="Active Trades" 
          value={analyticsSummary ? analyticsSummary.open_positions : 0} 
          icon={BarChart2} 
        />
        <StatCard 
          title="Account Equity" 
          value={analyticsSummary ? `$${analyticsSummary.equity.toFixed(2)}` : '$0.00'} 
          icon={Wallet} 
        />
      </div>

      <div className="glass-card" style={{ padding: '24px', marginBottom: '32px' }}>
        <h3 style={{ marginBottom: '24px' }}>Equity Curve</h3>
        <div style={{ width: '100%', height: '300px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={equityCurve} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
              <XAxis 
                dataKey="time" 
                stroke="var(--text-muted)" 
                tickFormatter={(tick) => {
                  try {
                    const d = new Date(tick);
                    if (isNaN(d.getTime())) return tick;
                    return `${d.getHours()}:${d.getMinutes().toString().padStart(2, '0')}`;
                  } catch {
                    return tick;
                  }
                }} 
              />
              <YAxis stroke="var(--text-muted)" domain={['auto', 'auto']} tickFormatter={(tick) => `$${tick}`} />
              <Tooltip 
                contentStyle={{ backgroundColor: 'var(--bg-card)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}
                itemStyle={{ color: '#fff' }}
              />
              <Area type="monotone" dataKey="value" stroke="#8b5cf6" fillOpacity={1} fill="url(#colorValue)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="glass-card" style={{ padding: '24px' }}>
        <h3 style={{ marginBottom: '24px' }}>Recent Trades</h3>
        <div style={{ overflowX: 'auto' }}>
          <table className="glass-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Symbol</th>
                <th>Type</th>
                <th>Price</th>
                <th>Amount</th>
                <th>PnL</th>
              </tr>
            </thead>
            <tbody>
              {tradeHistory.map((trade: any) => (
                <tr key={trade.id}>
                  <td>{new Date(trade.executed_at).toLocaleString()}</td>
                  <td style={{ fontWeight: 600 }}>{trade.symbol}</td>
                  <td>
                    <span className={`badge ${trade.side === 'BUY' ? 'badge-success' : 'badge-danger'}`}>
                      {trade.side}
                    </span>
                  </td>
                  <td>${Number(trade.price).toFixed(2)}</td>
                  <td>${Number(trade.notional).toFixed(2)}</td>
                  <td className={trade.realized_pnl >= 0 ? 'text-success' : 'text-danger'}>
                    {trade.realized_pnl >= 0 ? '+' : ''}${Number(trade.realized_pnl).toFixed(2)}
                  </td>
                </tr>
              ))}
              {(!tradeHistory || tradeHistory.length === 0) && (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                    No recent trades
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <CoinDetails />
    </div>
  );
};

export default Dashboard;
