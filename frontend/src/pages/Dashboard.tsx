import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  TrendingUp, TrendingDown, DollarSign, BarChart2,
  Layers, RefreshCw
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

// ── Stat Card ──────────────────────────────────────────────────
const StatCard: React.FC<{
  label: string;
  value: string | number;
  sub?: string;
  icon: React.FC<any>;
  positive?: boolean;
  accent?: boolean;
}> = ({ label, value, sub, icon: Icon, positive, accent }) => (
  <div className="card" style={{ padding: '20px 22px' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
      <span style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </span>
      <div style={{
        width: 32, height: 32, borderRadius: 8,
        background: accent ? 'var(--accent-soft)' : 'var(--bg-raised)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Icon size={16} color={accent ? 'var(--accent)' : 'var(--text-muted)'} />
      </div>
    </div>
    <div className="stat-value" style={{
      color: positive === undefined ? 'var(--text-primary)' : positive ? 'var(--success)' : 'var(--danger)'
    }}>
      {value}
    </div>
    {sub && <div style={{ marginTop: 6, fontSize: '0.78rem', color: 'var(--text-muted)' }}>{sub}</div>}
  </div>
);

// ── Status Pill ────────────────────────────────────────────────
const StatusPill: React.FC<{ ok: boolean | null; label: string }> = ({ ok, label }) => (
  <div style={{
    display: 'flex', alignItems: 'center', gap: 7,
    padding: '6px 12px', borderRadius: 6,
    background: ok === true ? 'var(--success-soft)' : ok === false ? 'var(--danger-soft)' : 'var(--bg-raised)',
    border: `1px solid ${ok === true ? 'rgba(74,222,128,0.2)' : ok === false ? 'rgba(248,113,113,0.2)' : 'var(--border)'}`,
  }}>
    <span style={{
      width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
      background: ok === true ? 'var(--success)' : ok === false ? 'var(--danger)' : 'var(--text-muted)',
    }} />
    <span style={{ fontSize: '0.78rem', fontWeight: 500, color: 'var(--text-secondary)' }}>{label}</span>
  </div>
);

// ── Custom Tooltip ─────────────────────────────────────────────
const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '8px 12px',
      fontSize: '0.8rem',
    }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      <div style={{ color: 'var(--accent)', fontWeight: 600 }}>
        ${Number(payload[0].value).toFixed(2)}
      </div>
    </div>
  );
};

// ── Page ───────────────────────────────────────────────────────
const Dashboard: React.FC = () => {
  const [sysHealth, setSysHealth] = useState<any>(null);
  const [dbHealth, setDbHealth] = useState<any>(null);
  const [botStatus, setBotStatus] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [equityCurve, setEquityCurve] = useState<any[]>([]);
  const [tradeHistory, setTradeHistory] = useState<any[]>([]);
  const [resetting, setResetting] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      const [healthRes, dbRes, botRes, sumRes, eqRes, histRes] = await Promise.all([
        axios.get('/api/v1/health').catch(() => ({ data: { status: 'error' } })),
        axios.get('/api/v1/health/db').catch(() => ({ data: { status: 'error' } })),
        axios.get('/api/v1/bot/status').catch(() => ({ data: { status: 'STOPPED' } })),
        axios.get('/api/v1/analytics/summary').catch(() => ({ data: null })),
        axios.get('/api/v1/analytics/equity-curve').catch(() => ({ data: { data: [] } })),
        axios.get('/api/v1/analytics/trade-history').catch(() => ({ data: { history: [] } })),
      ]);
      setSysHealth(healthRes.data);
      setDbHealth(dbRes.data);
      setBotStatus(botRes.data);
      if (sumRes.data) setSummary(sumRes.data);
      if (eqRes.data?.data) setEquityCurve(eqRes.data.data);
      if (histRes.data?.history) setTradeHistory(histRes.data.history);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const iv = setInterval(fetchAll, 10000);
    return () => clearInterval(iv);
  }, [fetchAll]);

  const handleReset = async () => {
    if (!window.confirm('Tüm işlem geçmişi ve PnL sıfırlanacak. Onaylıyor musunuz?')) return;
    setResetting(true);
    await axios.post('/api/v1/analytics/reset').catch(console.error);
    await fetchAll();
    setResetting(false);
  };

  const totalPnl = summary?.total_pnl ?? 0;
  const bots = botStatus?.bots || [];
  const activeBotCount = bots.filter((b: any) => b.status === 'RUNNING').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* ── Header ────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
        <div>
          <h1 style={{ marginBottom: 4 }}>Overview</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Real-time performance and system health
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <StatusPill ok={sysHealth?.status === 'ok'} label="API" />
          <StatusPill ok={dbHealth?.status === 'ok'} label="Database" />
          <StatusPill ok={activeBotCount > 0} label={activeBotCount > 0 ? `${activeBotCount} Bot Active` : 'No Bots'} />
          <button
            onClick={handleReset}
            disabled={resetting}
            className="btn-danger"
            style={{ marginLeft: 8 }}
          >
            <RefreshCw size={13} style={{ animation: resetting ? 'spin 0.8s linear infinite' : 'none' }} />
            Reset Data
          </button>
        </div>
      </div>

      {/* ── Stat Cards ────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
        <StatCard
          label="Total PnL"
          value={`${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}`}
          icon={totalPnl >= 0 ? TrendingUp : TrendingDown}
          positive={totalPnl >= 0}
          sub={`${summary?.total_trades ?? 0} closed trades`}
        />
        <StatCard
          label="Win Rate"
          value={`${(summary?.win_rate ?? 0).toFixed(1)}%`}
          icon={BarChart2}
          accent
          sub="Profitable trades"
        />
        <StatCard
          label="Open Positions"
          value={summary?.open_positions ?? 0}
          icon={Layers}
          sub="Active long exposure"
        />
        <StatCard
          label="Account Equity"
          value={`$${(summary?.equity ?? 0).toFixed(2)}`}
          icon={DollarSign}
          accent
          sub={`Balance: $${(summary?.current_balance ?? 0).toFixed(2)}`}
        />
      </div>

      {/* ── Equity Curve ──────────────────────────────────── */}
      <div className="card" style={{ padding: '20px 24px' }}>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3>Equity Curve</h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {equityCurve.length} data points
          </span>
        </div>
        <div style={{ width: '100%', height: 240 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={equityCurve} margin={{ top: 5, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="eq-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="var(--accent)" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="var(--accent)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="time"
                tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(t) => {
                  try {
                    const d = new Date(t);
                    return isNaN(d.getTime()) ? t : `${d.getHours()}:${d.getMinutes().toString().padStart(2, '0')}`;
                  } catch { return t; }
                }}
              />
              <YAxis
                tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => `$${v}`}
                domain={['auto', 'auto']}
                width={60}
              />
              <Tooltip content={<ChartTooltip />} />
              <Area
                type="monotone"
                dataKey="value"
                stroke="var(--accent)"
                strokeWidth={1.5}
                fill="url(#eq-grad)"
                dot={false}
                activeDot={{ r: 4, fill: 'var(--accent)', strokeWidth: 0 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Trade History ──────────────────────────────────── */}
      <div className="card" style={{ padding: '20px 24px' }}>
        <h3 style={{ marginBottom: 16 }}>Recent Trades</h3>
        <div style={{ overflowX: 'auto' }}>
          <table className="glass-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Symbol</th>
                <th>Side</th>
                <th>Price</th>
                <th>Amount</th>
                <th>PnL</th>
              </tr>
            </thead>
            <tbody>
              {tradeHistory.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '32px 16px' }}>
                    No trades yet
                  </td>
                </tr>
              ) : (
                tradeHistory.map((t: any) => {
                  const pnl = t.realized_pnl;
                  return (
                    <tr key={t.id}>
                      <td className="mono" style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        {new Date(t.executed_at).toLocaleString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </td>
                      <td style={{ fontWeight: 600 }}>{t.symbol}</td>
                      <td>
                        <span className={`badge badge-${t.side === 'BUY' ? 'success' : 'danger'}`}>
                          {t.side}
                        </span>
                      </td>
                      <td className="mono">${Number(t.price).toFixed(4)}</td>
                      <td className="mono">${Number(t.notional).toFixed(2)}</td>
                      <td className="mono" style={{ color: pnl == null ? 'var(--text-muted)' : pnl >= 0 ? 'var(--success)' : 'var(--danger)', fontWeight: 500 }}>
                        {pnl == null ? '—' : `${pnl >= 0 ? '+' : ''}$${Number(pnl).toFixed(4)}`}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>



      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default Dashboard;
