import React, { useState, useEffect, useCallback } from 'react';
import { 
  getHealth, getDbHealth, getBotStatus, 
  getAnalyticsSummary, getEquityCurve, getTradeHistory, resetAnalytics 
} from '../services/api';
import type { 
  HealthStatus, DatabaseHealth, BotStatusResponse, 
  AnalyticsSummary, EquityCurvePoint, TradeRecord, BotInfo 
} from '../types/api';
import { motion } from 'framer-motion';
import {
  TrendingUp, TrendingDown, DollarSign, BarChart2,
  Layers, RefreshCw, Zap
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer
} from 'recharts';
import RiskRegimeShield from '../components/RiskRegimeShield';

// ── Stat Card ────────────────────────────────────────────────
const StatCard: React.FC<{
  label: string;
  value: string | number;
  sub?: string;
  icon: React.FC<any>;
  positive?: boolean;
  accent?: boolean;
  delay?: number;
}> = ({ label, value, sub, icon: Icon, positive, accent, delay = 0 }) => {
  const valueColor =
    positive === undefined
      ? 'var(--text-primary)'
      : positive
      ? 'var(--success)'
      : 'var(--danger)';

  return (
    <motion.div
      className="card"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
      whileHover={{ y: -3, boxShadow: 'var(--shadow-glow)' }}
      style={{ padding: '22px 22px' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
          {label}
        </span>
        <div style={{
          width: 34, height: 34, borderRadius: 10,
          background: accent ? 'var(--accent-soft)' : 'var(--bg-raised)',
          border: accent ? '1px solid var(--accent-border)' : '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon size={16} color={accent ? 'var(--accent)' : 'var(--text-muted)'} />
        </div>
      </div>
      <div className="stat-value" style={{ color: valueColor, marginBottom: sub ? 6 : 0 }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{sub}</div>}
    </motion.div>
  );
};

// ── Status Pill ───────────────────────────────────────────────
const StatusPill: React.FC<{ ok: boolean | null; label: string }> = ({ ok, label }) => (
  <div style={{
    display: 'flex', alignItems: 'center', gap: 7,
    padding: '6px 12px', borderRadius: 8,
    background: ok === true ? 'var(--success-soft)' : ok === false ? 'var(--danger-soft)' : 'var(--bg-raised)',
    border: `1px solid ${ok === true ? 'rgba(74,222,128,0.2)' : ok === false ? 'rgba(248,113,113,0.2)' : 'var(--border)'}`,
  }}>
    <motion.div
      animate={ok === true ? { opacity: [1, 0.3, 1] } : {}}
      transition={{ duration: 2, repeat: Infinity }}
      style={{
        width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
        background: ok === true ? 'var(--success)' : ok === false ? 'var(--danger)' : 'var(--text-muted)',
        boxShadow: ok === true ? '0 0 6px var(--success)' : 'none',
      }}
    />
    <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)' }}>{label}</span>
  </div>
);

// ── Chart Tooltip ─────────────────────────────────────────────
const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="card" style={{ padding: '10px 14px', fontSize: '0.8rem' }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      <div style={{ color: 'var(--accent)', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>
        ${Number(payload[0].value).toFixed(2)}
      </div>
    </div>
  );
};

// ── Page ───────────────────────────────────────────────────────
const Dashboard: React.FC = () => {
  const [sysHealth, setSysHealth] = useState<HealthStatus | null>(null);
  const [dbHealth, setDbHealth]   = useState<DatabaseHealth | null>(null);
  const [botStatus, setBotStatus] = useState<BotStatusResponse | null>(null);
  const [summary, setSummary]     = useState<AnalyticsSummary | null>(null);
  const [equityCurve, setEquityCurve] = useState<EquityCurvePoint[]>([]);
  const [tradeHistory, setTradeHistory] = useState<TradeRecord[]>([]);
  const [resetting, setResetting] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      const [healthRes, dbRes, botRes, sumRes, eqRes, histRes] = await Promise.all([
        getHealth().catch(() => ({ data: { status: 'error' } as HealthStatus })),
        getDbHealth().catch(() => ({ data: { status: 'error' } as DatabaseHealth })),
        getBotStatus().catch(() => ({ data: { bots: [] } as BotStatusResponse })),
        getAnalyticsSummary().catch(() => ({ data: null })),
        getEquityCurve().catch(() => ({ data: { data: [] } })),
        getTradeHistory().catch(() => ({ data: { history: [] } })),
      ]);
      setSysHealth(healthRes.data);
      setDbHealth(dbRes.data);
      setBotStatus(botRes.data);
      if (sumRes.data) setSummary(sumRes.data);
      if (eqRes.data?.data) setEquityCurve(eqRes.data.data);
      if (histRes.data?.history) setTradeHistory(histRes.data.history);
    } catch (err) { console.error(err); }
  }, []);

  useEffect(() => { fetchAll(); const iv = setInterval(fetchAll, 10000); return () => clearInterval(iv); }, [fetchAll]);

  const handleReset = async () => {
    if (!window.confirm('Tüm işlem geçmişi ve PnL sıfırlanacak. Onaylıyor musunuz?')) return;
    setResetting(true);
    await resetAnalytics().catch(console.error);
    await fetchAll();
    setResetting(false);
  };

  const totalPnl = summary?.total_pnl ?? 0;
  const bots = botStatus?.bots || [];
  const activeBotCount = bots.filter((b: BotInfo) => b.status === 'RUNNING').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}
      >
        <div>
          <h1 style={{ marginBottom: 4 }}>Overview</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Real-time performance and system health
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <StatusPill ok={sysHealth?.status === 'ok'} label="API" />
          <StatusPill ok={dbHealth?.status === 'ok'} label="Database" />
          <StatusPill ok={activeBotCount > 0} label={activeBotCount > 0 ? `${activeBotCount} Bot Active` : 'No Bots'} />
          <button onClick={handleReset} disabled={resetting} className="btn-danger">
            <RefreshCw size={13} className={resetting ? 'animate-spin' : ''} />
            Reset Data
          </button>
        </div>
      </motion.div>

      {/* Real-Time Risk & Regime Shield */}
      <RiskRegimeShield />

      {/* Stat Cards */}
      <div className="grid-cols-4">
        <StatCard label="Total PnL" value={`${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}`}
          icon={totalPnl >= 0 ? TrendingUp : TrendingDown} positive={totalPnl >= 0}
          sub={`${summary?.total_trades ?? 0} closed trades`} delay={0.1} />
        <StatCard label="Win Rate" value={`${(summary?.win_rate ?? 0).toFixed(1)}%`}
          icon={BarChart2} accent sub="Profitable trades" delay={0.15} />
        <StatCard label="Open Positions" value={summary?.open_positions ?? 0}
          icon={Layers} sub="Active long exposure" delay={0.2} />
        <StatCard label="Account Equity" value={`$${(summary?.equity ?? 0).toFixed(2)}`}
          icon={DollarSign} accent sub={`Balance: $${(summary?.current_balance ?? 0).toFixed(2)}`} delay={0.25} />
      </div>

      {/* Equity Curve */}
      <motion.div className="card" style={{ padding: '22px 24px' }}
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.35 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Zap size={16} color="var(--accent)" />
            <h3 style={{ margin: 0 }}>Equity Curve</h3>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {equityCurve.length} data points
          </span>
        </div>
        <div style={{ width: '100%', height: 220 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={equityCurve} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="eq-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="var(--accent)" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                tickLine={false} axisLine={false}
                tickFormatter={(t) => { try { const d = new Date(t); return isNaN(d.getTime()) ? t : `${d.getHours()}:${d.getMinutes().toString().padStart(2,'0')}`; } catch { return t; } }}
              />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickLine={false}
                axisLine={false} tickFormatter={v => `$${v}`} domain={['auto','auto']} width={60} />
              <Tooltip content={<ChartTooltip />} />
              <Area type="monotone" dataKey="value" stroke="var(--accent)" strokeWidth={2}
                fill="url(#eq-grad)" dot={false}
                activeDot={{ r: 5, fill: 'var(--accent)', stroke: 'var(--bg-base)', strokeWidth: 2 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </motion.div>

      {/* Recent Trades */}
      <motion.div className="card" style={{ padding: '22px 24px' }}
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.45 }}>
        <h3 style={{ marginBottom: 18 }}>Recent Trades</h3>
        <div style={{ overflowX: 'auto' }}>
          <table className="glass-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Symbol</th>
                <th>Side</th>
                <th>Price</th>
                <th>Notional</th>
                <th>PnL</th>
              </tr>
            </thead>
            <tbody>
              {tradeHistory.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '36px 16px' }}>
                    No trades yet
                  </td>
                </tr>
              ) : (
                tradeHistory.map((t: TradeRecord) => {
                  const pnl = t.realized_pnl;
                  return (
                    <tr key={t.id}>
                      <td className="mono" style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        {new Date(t.executed_at).toLocaleString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </td>
                      <td style={{ fontWeight: 600 }}>{t.symbol}</td>
                      <td><span className={`badge badge-${t.side === 'BUY' ? 'success' : 'danger'}`}>{t.side}</span></td>
                      <td className="mono">${Number(t.price).toFixed(4)}</td>
                      <td className="mono">${Number(t.notional).toFixed(2)}</td>
                      <td className="mono" style={{ color: pnl == null ? 'var(--text-muted)' : pnl >= 0 ? 'var(--success)' : 'var(--danger)', fontWeight: 600 }}>
                        {pnl == null ? '—' : `${pnl >= 0 ? '+' : ''}$${Number(pnl).toFixed(4)}`}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
};

export default Dashboard;
