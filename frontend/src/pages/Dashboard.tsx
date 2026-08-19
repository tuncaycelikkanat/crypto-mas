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
  TrendingUp, BarChart3,
  Layers, RefreshCw, ArrowUpRight, ArrowDownRight, Wallet
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import RiskRegimeShield from '../components/RiskRegimeShield';

// ── Stat Card (Bento Spotlight Style) ────────────────────────
const StatCard: React.FC<{
  label: string;
  value: string | number;
  sub?: string;
  icon: React.FC<any>;
  positive?: boolean;
  delay?: number;
}> = ({ label, value, sub, icon: Icon, positive, delay = 0 }) => {
  const isNeutral = positive === undefined;
  const valueColor = isNeutral
    ? 'var(--text-primary)'
    : positive
    ? 'var(--success)'
    : 'var(--danger)';

  return (
    <motion.div
      className="card"
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ y: -2 }}
      style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span className="section-label">
          {label}
        </span>
        <div style={{
          width: 32, height: 32, borderRadius: 'var(--radius-sm)',
          background: 'var(--bg-raised)',
          border: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon size={16} color="var(--text-muted)" />
        </div>
      </div>

      <div>
        <div className="stat-value" style={{ color: valueColor, marginBottom: sub ? 4 : 0 }}>
          {value}
        </div>
        {sub && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{sub}</div>}
      </div>
    </motion.div>
  );
};

// ── Status Pill ───────────────────────────────────────────────
const StatusPill: React.FC<{ ok: boolean | null; label: string }> = ({ ok, label }) => (
  <div style={{
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '5px 10px', borderRadius: 'var(--radius-xs)',
    background: 'var(--bg-raised)',
    border: '1px solid var(--border)',
  }}>
    <motion.div
      animate={ok === true ? { opacity: [1, 0.4, 1] } : {}}
      transition={{ duration: 2, repeat: Infinity }}
      style={{
        width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
        background: ok === true ? 'var(--success)' : ok === false ? 'var(--danger)' : 'var(--text-muted)',
        boxShadow: ok === true ? '0 0 6px var(--success)' : 'none',
      }}
    />
    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>{label}</span>
  </div>
);

// ── Chart Tooltip ─────────────────────────────────────────────
const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="card" style={{ padding: '8px 12px', fontSize: '0.8rem', background: 'var(--bg-raised)', border: '1px solid var(--border-hover)' }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 2, fontSize: '0.72rem' }}>{label}</div>
      <div style={{ color: 'var(--text-primary)', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>
        ${Number(payload[0].value).toFixed(2)}
      </div>
    </div>
  );
};

// ── Dashboard Page ────────────────────────────────────────────
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

  useEffect(() => { 
    fetchAll(); 
    const iv = setInterval(fetchAll, 10000); 
    return () => clearInterval(iv); 
  }, [fetchAll]);

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

      {/* Header Bar */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}
      >
        <div>
          <h1 style={{ marginBottom: 4 }}>Overview</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Real-time multi-agent performance and portfolio intelligence
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <StatusPill ok={sysHealth?.status === 'ok'} label="API Status" />
          <StatusPill ok={dbHealth?.status === 'ok'} label="DB Online" />
          <StatusPill ok={activeBotCount > 0} label={activeBotCount > 0 ? `${activeBotCount} Bot Active` : 'Idle'} />
          <button onClick={handleReset} disabled={resetting} className="btn-danger" style={{ fontSize: '0.8rem', padding: '6px 12px' }}>
            <RefreshCw size={12} className={resetting ? 'animate-spin' : ''} />
            Reset Data
          </button>
        </div>
      </motion.div>

      {/* Live Risk & Market Regime Shield */}
      <RiskRegimeShield />

      {/* 4 Bento Stat Cards */}
      <div className="grid-cols-4">
        <StatCard
          label="Total Realized PnL"
          value={`${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}`}
          icon={totalPnl >= 0 ? ArrowUpRight : ArrowDownRight}
          positive={totalPnl >= 0}
          sub={`${summary?.total_trades ?? 0} closed positions`}
          delay={0.05}
        />
        <StatCard
          label="Win Rate"
          value={`${(summary?.win_rate ?? 0).toFixed(1)}%`}
          icon={BarChart3}
          sub="Profitable trade ratio"
          delay={0.1}
        />
        <StatCard
          label="Open Exposure"
          value={summary?.open_positions ?? 0}
          icon={Layers}
          sub="Active positions count"
          delay={0.15}
        />
        <StatCard
          label="Account Equity"
          value={`$${(summary?.equity ?? 0).toFixed(2)}`}
          icon={Wallet}
          sub={`Cash: $${(summary?.current_balance ?? 0).toFixed(2)}`}
          delay={0.2}
        />
      </div>

      {/* Equity Curve (Monochrome Glow) */}
      <motion.div
        className="card"
        style={{ padding: '22px 24px' }}
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.25 }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 28, height: 28, borderRadius: 8, background: 'var(--accent-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <TrendingUp size={15} color="var(--text-primary)" />
            </div>
            <h3 style={{ margin: 0 }}>Portfolio Equity Curve</h3>
          </div>
          <span className="mono text-muted" style={{ fontSize: '0.75rem' }}>
            {equityCurve.length} data samples
          </span>
        </div>

        <div style={{ width: '100%', height: 230 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={equityCurve} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="eq-grad-mono" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--text-primary)" stopOpacity={0.18} />
                  <stop offset="100%" stopColor="var(--text-primary)" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="time"
                tick={{ fill: 'var(--text-dim)', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(t) => {
                  try {
                    const d = new Date(t);
                    return isNaN(d.getTime()) ? t : `${d.getHours()}:${d.getMinutes().toString().padStart(2,'0')}`;
                  } catch { return t; }
                }}
              />
              <YAxis
                tick={{ fill: 'var(--text-dim)', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => `$${v}`}
                domain={['auto','auto']}
                width={60}
              />
              <Tooltip content={<ChartTooltip />} />
              <Area
                type="monotone"
                dataKey="value"
                stroke="var(--text-primary)"
                strokeWidth={2}
                fill="url(#eq-grad-mono)"
                dot={false}
                activeDot={{ r: 4, fill: 'var(--text-primary)', stroke: 'var(--bg-base)', strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </motion.div>

      {/* Recent Trades Table */}
      <motion.div
        className="card"
        style={{ padding: '22px 24px' }}
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.3 }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>Recent Executed Trades</h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Latest {tradeHistory.length} orders
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="glass-table">
            <thead>
              <tr>
                <th>Execution Time</th>
                <th>Pair</th>
                <th>Side</th>
                <th>Price</th>
                <th>Notional</th>
                <th>Realized PnL</th>
              </tr>
            </thead>
            <tbody>
              {tradeHistory.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '36px 16px' }}>
                    No recent trades recorded yet.
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
                      <td>
                        <span className={`badge badge-${t.side === 'BUY' ? 'success' : 'danger'}`}>
                          {t.side}
                        </span>
                      </td>
                      <td className="mono">${Number(t.price).toFixed(4)}</td>
                      <td className="mono">${Number(t.notional).toFixed(2)}</td>
                      <td className="mono" style={{
                        color: pnl == null ? 'var(--text-muted)' : pnl >= 0 ? 'var(--success)' : 'var(--danger)',
                        fontWeight: 700
                      }}>
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
