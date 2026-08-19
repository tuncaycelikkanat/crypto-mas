import React, { useState, useEffect } from 'react';
import { 
  getPaperAccount, getBotStatus, 
  startBot, stopBot, runCycle, updateBotSymbols, updateBotRisk 
} from '../services/api';
import type { PaperAccount, BotStatusResponse, BotInfo, CycleResponse, OpenPosition } from '../types/api';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { PlayCircle, RefreshCw, Square, XCircle, Activity, X, Bot, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import LiveConsole from '../components/LiveConsole';

// ── Option Card (for modal choices) ──────────────────────────
const OptionCard: React.FC<{
  selected: boolean;
  onClick: () => void;
  title: string;
  sub?: string;
  badge?: string;
}> = ({ selected, onClick, title, sub, badge }) => (
  <div
    className={`option-card ${selected ? 'selected' : ''}`}
    onClick={onClick}
  >
    {badge && (
      <div style={{ marginBottom: 6 }}>
        <span className="badge badge-primary" style={{ fontSize: '0.65rem' }}>{badge}</span>
      </div>
    )}
    <div className="option-card-title">{title}</div>
    {sub && <div className="option-card-sub">{sub}</div>}
  </div>
);

// ── Paper Trading Page ───────────────────────────────────────
const PaperTrading: React.FC = () => {
  const [accounts, setAccounts] = useState<PaperAccount[]>([]);
  const [selectedAccountName, setSelectedAccountName] = useState<string>('main');
  const account = accounts.find(a => a.name === selectedAccountName) || accounts[0] || null;
  const [loading, setLoading] = useState(false);
  const [actionLog, setActionLog] = useState<CycleResponse | { status: string; reason?: string } | null>(null);
  const [botStatus, setBotStatus] = useState<BotStatusResponse | null>(null);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [editingSymbols, setEditingSymbols] = useState<Record<string, string>>({});
  const [editingRiskLevels, setEditingRiskLevels] = useState<Record<string, number>>({});

  // ─ Config state ─
  const [configInterval, setConfigInterval] = useLocalStorage('configInterval', '30');
  const [configSymbols, setConfigSymbols] = useLocalStorage('configSymbols', 'BTCUSDT');
  const [configSymbolSource, setConfigSymbolSource] = useLocalStorage('configSymbolSource', 'auto');
  const [configExchanges, setConfigExchanges] = useLocalStorage<string[]>('configExchanges', ['BINANCE']);
  const [configMode, setConfigMode] = useLocalStorage('configMode', 'scalping');
  const [configBtcShield, setConfigBtcShield] = useLocalStorage('configBtcShield', true);
  const [configHtfShield, setConfigHtfShield] = useLocalStorage('configHtfShield', true);
  const [configRegimeShield, setConfigRegimeShield] = useLocalStorage('configRegimeShield', true);
  const [configRiskLevel, setConfigRiskLevel] = useLocalStorage('configRiskLevel', 50);
  const [favoriteCoins, setFavoriteCoins] = useLocalStorage<string[]>('favoriteCoins', ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','ADAUSDT']);
  const [newFavorite, setNewFavorite] = useState('');

  const isCoinSelected = (coin: string) =>
    configSymbols.split(',').map(s => s.trim().toUpperCase()).includes(coin);

  const toggleCoin = (coin: string) => {
    let list = configSymbols.split(',').map(s => s.trim().toUpperCase()).filter(s => s);
    list = list.includes(coin) ? list.filter(s => s !== coin) : [...list, coin];
    setConfigSymbols(list.join(', '));
  };

  const fetchAccount = async () => {
    try {
      const res = await getPaperAccount();
      const data = res.data;
      if (Array.isArray(data) && data.length > 0) {
        setAccounts(data);
        if (!data.find(a => a.name === selectedAccountName)) {
          setSelectedAccountName(data[0].name || 'main');
        }
      } else if (data && typeof data === 'object' && 'name' in data) {
        setAccounts([data as PaperAccount]);
        setSelectedAccountName((data as PaperAccount).name || 'main');
      }
    } catch (e: unknown) {
      console.error("Failed to fetch accounts:", e);
    }
  };

  const fetchBotStatus = async () => {
    try { 
      const res = await getBotStatus(); 
      setBotStatus(res.data); 
    } catch { /* ignore */ }
  };

  useEffect(() => {
    fetchAccount(); 
    fetchBotStatus();
    const iv = setInterval(() => { fetchAccount(); fetchBotStatus(); }, 5000);
    return () => clearInterval(iv);
  }, []);

  const handleStartBot = async () => {
    setLoading(true);
    try {
      const symbolsList = configSymbolSource === 'auto'
        ? ['AUTO_GAINERS']
        : configSymbols.split(',').map(s => s.trim().toUpperCase()).filter(s => s);
      
      await startBot({
        bot_id: selectedAccountName,
        interval_seconds: parseInt(configInterval, 10),
        symbols: symbolsList,
        mode: configMode,
        exchange: configExchanges[0] || 'BINANCE',
        risk_level: configRiskLevel,
        use_btc_shield: configBtcShield,
        use_htf_shield: configHtfShield,
        use_regime_shield: configRegimeShield,
      });
      const res = await getBotStatus();
      setBotStatus(res.data);
      setShowConfigModal(false);
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const handleStopBot = async (bot_id: string) => {
    setLoading(true);
    try { 
      const res = await stopBot(bot_id); 
      setBotStatus(res.data); 
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const handleManualCycle = async () => {
    setLoading(true); 
    setActionLog(null);
    try {
      const symbolsList = configSymbolSource === 'auto'
        ? ['AUTO_GAINERS']
        : configSymbols.split(',').map(s => s.trim().toUpperCase()).filter(s => s);
      let lastRes = null;
      for (const ex of configExchanges) {
        lastRes = await runCycle({
          account_name: selectedAccountName,
          exchange: ex,
          symbols: symbolsList,
          timeframe: configMode === 'scalping' ? '1m' : configMode === 'swing' ? '4h' : '1d',
          strategy_name: configMode === 'scalping' ? 'hft_momentum' : configMode === 'swing' ? 'macd_cross' : 'ema_golden_cross',
          trigger: 'MANUAL',
        });
      }
      setActionLog(lastRes?.data || { status: "no exchange selected" });
      await fetchAccount();
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const handleUpdateSymbols = async (bot_id: string) => {
    setLoading(true);
    try {
      const symbolsList = (editingSymbols[bot_id] || '').split(',').map(s => s.trim().toUpperCase()).filter(s => s);
      await updateBotSymbols(bot_id, { symbols: symbolsList });
      await fetchBotStatus();
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const handleRiskChange = async (bot_id: string, risk: number) => {
    try {
      await updateBotRisk(bot_id, { risk_level: risk });
      setEditingRiskLevels(prev => { const n = { ...prev }; delete n[bot_id]; return n; });
      setBotStatus((prev: BotStatusResponse | null) => 
        prev ? { ...prev, bots: prev.bots.map((b: BotInfo) => b.bot_id === bot_id ? { ...b, risk_level: risk } : b) } : prev
      );
    } catch (err) { console.error(err); }
  };

  const normalizeSymbols = (s: string | string[]) => {
    const arr = Array.isArray(s) ? s : s.split(',');
    return arr.map(x => x.trim().toUpperCase()).filter(Boolean).sort().join(',');
  };

  const bots = botStatus?.bots || [];
  const riskLabel = (v: number) => v < 33 ? 'Conservative' : v < 66 ? 'Balanced' : 'Aggressive';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Header Bar */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}
      >
        <div>
          <h1 style={{ marginBottom: 4 }}>Paper Trading</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Simulate live multi-agent execution with real-time risk controls
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button className="btn-secondary" onClick={handleManualCycle} disabled={loading}>
            <PlayCircle size={14} />
            Force Cycle
          </button>
          <button className="btn-primary" onClick={() => setShowConfigModal(true)} disabled={loading}>
            {loading ? <RefreshCw size={14} className="animate-spin" /> : <Bot size={14} />}
            {loading ? 'Processing…' : 'Start Trading'}
          </button>
        </div>
      </motion.div>

      {/* Account Tabs (Sliding Bar) */}
      {accounts.length > 0 && (
        <div style={{
          display: 'flex', gap: '8px', overflowX: 'auto',
          paddingBottom: '4px', borderBottom: '1px solid var(--border)'
        }}>
          {accounts.map(acc => {
            const isSelected = selectedAccountName === acc.name;
            return (
              <button
                key={acc.name}
                className={isSelected ? 'btn-primary' : 'btn-ghost'}
                onClick={() => setSelectedAccountName(acc.name!)}
                style={{
                  whiteSpace: 'nowrap',
                  borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0',
                  padding: '8px 16px',
                  fontSize: '0.82rem',
                }}
              >
                <Bot size={14} style={{ marginRight: 6 }} />
                {acc.name === 'main' ? 'Main Account' : acc.name === 'slot-2' ? 'Slot 2' : acc.name === 'slot-3' ? 'Slot 3' : acc.name}
              </button>
            );
          })}
        </div>
      )}

      {/* 3 Account Metric Cards */}
      <div className="grid-cols-3">
        {[
          { label: 'Account Equity', value: `$${account ? parseFloat(String(account.equity)).toFixed(2) : '0.00'}` },
          { label: 'Cash Balance', value: `$${account ? parseFloat(String(account.cash_balance)).toFixed(2) : '0.00'}` },
          { label: 'Active Positions', value: account?.open_positions?.length ?? 0 },
        ].map((item, i) => (
          <motion.div
            key={item.label}
            className="card"
            style={{ padding: '20px 22px' }}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
          >
            <div className="section-label" style={{ marginBottom: 8 }}>
              {item.label}
            </div>
            <div className="stat-value" style={{ color: 'var(--text-primary)' }}>
              {item.value}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Action Log Card */}
      <AnimatePresence>
        {actionLog && (
          <motion.div
            className="card"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{
              padding: '18px 22px',
              borderLeft: `3px solid ${actionLog.status === 'REJECTED' ? 'var(--danger)' : 'var(--success)'}`
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: '0.95rem' }}>
                Last Cycle Result — <span style={{ color: actionLog.status === 'REJECTED' ? 'var(--danger)' : 'var(--success)' }}>{actionLog.status}</span>
              </h3>
              <button className="btn-ghost" style={{ padding: '4px' }} onClick={() => setActionLog(null)}>
                <X size={14} />
              </button>
            </div>
            {actionLog.status === 'REJECTED' ? (
              <p className="text-danger" style={{ marginTop: 8, fontSize: '0.85rem' }}>{actionLog.reason}</p>
            ) : (
              <div style={{ display: 'flex', gap: 28, marginTop: 12 }}>
                {[
                  ['Processed', (actionLog as any).symbols_processed],
                  ['Decisions', (actionLog as any).decisions_made],
                  ['Trades', (actionLog as any).trades_executed]
                ].map(([k, v]) => (
                  <div key={k}>
                    <div className="section-label" style={{ fontSize: '0.68rem' }}>{k}</div>
                    <div className="stat-value" style={{ fontSize: '1.25rem', color: 'var(--text-primary)', marginTop: 2 }}>{v}</div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bot Status & Management Card */}
      {bots.filter((b: BotInfo) => b.bot_id === selectedAccountName).length === 0 ? (
        <div className="card" style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 'var(--radius-sm)',
            background: 'var(--bg-raised)', border: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <XCircle size={20} color="var(--text-muted)" />
          </div>
          <div>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>No Active Bots in this Slot</div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Click "Start Trading" above to launch an automated multi-agent bot.</div>
          </div>
        </div>
      ) : (
        bots.filter((b: BotInfo) => b.bot_id === selectedAccountName).map((bot: BotInfo) => {
          const isRunning = bot.status === 'RUNNING';
          const currentEditingStr = editingSymbols[bot.bot_id] !== undefined ? editingSymbols[bot.bot_id] : (bot.symbols?.join(', ') || '');
          const hasChanged = normalizeSymbols(currentEditingStr) !== normalizeSymbols(bot.symbols || []);
          const currentRisk = editingRiskLevels[bot.bot_id] !== undefined ? editingRiskLevels[bot.bot_id] : (bot.risk_level ?? 50);

          return (
            <motion.div
              key={bot.bot_id}
              className="card"
              style={{
                padding: '22px 24px',
                borderLeft: `3px solid ${isRunning ? 'var(--success)' : 'var(--border-strong)'}`
              }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {/* Bot Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: isRunning ? 20 : 0, flexWrap: 'wrap', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  {isRunning ? (
                    <motion.div
                      animate={{ opacity: [1, 0.3, 1] }}
                      transition={{ duration: 2, repeat: Infinity }}
                      style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--success)', boxShadow: '0 0 8px var(--success)' }}
                    />
                  ) : (
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--text-muted)' }} />
                  )}
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-primary)' }}>
                      Bot Slot: <span className="mono">{bot.bot_id}</span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: isRunning ? 'var(--success)' : 'var(--text-muted)', marginTop: 2 }}>
                      {isRunning ? 'Online & Actively Trading' : bot.status}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  {isRunning && bot.mode && (
                    <span className="badge badge-primary" style={{ fontSize: '0.72rem' }}>
                      {bot.mode.toUpperCase()} · {bot.exchange || 'BINANCE'}
                    </span>
                  )}
                  {isRunning && (
                    <button className="btn-danger" onClick={() => handleStopBot(bot.bot_id)} disabled={loading} style={{ fontSize: '0.8rem', padding: '6px 12px' }}>
                      <Square size={12} /> Stop Bot
                    </button>
                  )}
                </div>
              </div>

              {/* Running Bot Controls */}
              {isRunning && (
                <div style={{ paddingTop: 18, borderTop: '1px solid var(--border)' }}>
                  
                  {/* Live Risk Slider */}
                  <div style={{ marginBottom: 18 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                      <label className="section-label">Risk Level Setting</label>
                      <span className="mono" style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                        {currentRisk} / 100 — {riskLabel(currentRisk)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={currentRisk}
                      onChange={e => setEditingRiskLevels({ ...editingRiskLevels, [bot.bot_id]: +e.target.value })}
                      onMouseUp={e => handleRiskChange(bot.bot_id, +(e.target as HTMLInputElement).value)}
                      onTouchEnd={e => handleRiskChange(bot.bot_id, +(e.target as HTMLInputElement).value)}
                    />
                  </div>

                  {/* Symbol Management */}
                  {bot.symbols?.includes('AUTO_GAINERS') ? (
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: 12,
                      padding: '12px 16px', background: 'var(--bg-raised)',
                      border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)'
                    }}>
                      <Activity size={18} color="var(--text-primary)" />
                      <div>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.85rem' }}>Auto-Scanner Active</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Dynamically hunting top gainers every cycle.</div>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <label className="section-label" style={{ display: 'block', marginBottom: 8 }}>Configured Trading Pairs</label>
                      <div style={{ display: 'flex', gap: 10 }}>
                        <textarea
                          className="form-input mono"
                          style={{ flex: 1, fontSize: '0.82rem', minHeight: '60px' }}
                          value={currentEditingStr}
                          onChange={e => setEditingSymbols({ ...editingSymbols, [bot.bot_id]: e.target.value })}
                        />
                        {hasChanged && (
                          <button
                            className="btn-primary"
                            onClick={() => handleUpdateSymbols(bot.bot_id)}
                            disabled={loading}
                            style={{ alignSelf: 'flex-end', fontSize: '0.8rem', padding: '8px 14px' }}
                          >
                            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
                            Update
                          </button>
                        )}
                      </div>
                    </div>
                  )}

                </div>
              )}
            </motion.div>
          );
        })
      )}

      {/* Open Positions Table */}
      <motion.div
        className="card"
        style={{ padding: '22px 24px' }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>Open Positions</h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {account?.open_positions?.length || 0} active
          </span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="glass-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side</th>
                <th>Quantity</th>
                <th>Entry Price</th>
                <th>Unrealized PnL</th>
              </tr>
            </thead>
            <tbody>
              {account?.open_positions && account.open_positions.length > 0 ? (
                account.open_positions.map((pos: OpenPosition, i: number) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600 }}>{pos.symbol}</td>
                    <td>
                      <span className={`badge badge-${pos.side === 'LONG' ? 'success' : 'danger'}`}>
                        {pos.side}
                      </span>
                    </td>
                    <td className="mono">{parseFloat(String(pos.quantity)).toFixed(4)}</td>
                    <td className="mono">${parseFloat(String(pos.entry_price)).toFixed(2)}</td>
                    <td className="mono" style={{
                      color: parseFloat(String(pos.unrealized_pnl)) >= 0 ? 'var(--success)' : 'var(--danger)',
                      fontWeight: 700
                    }}>
                      ${parseFloat(String(pos.unrealized_pnl)).toFixed(2)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '32px 16px' }}>
                    No open positions currently active.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Closed Positions Table */}
      <motion.div
        className="card"
        style={{ padding: '22px 24px' }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>Closed Trade History</h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Total: {account?.closed_positions?.length || 0}
          </span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="glass-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side</th>
                <th>Entry Price</th>
                <th>Exit Price</th>
                <th>Realized PnL</th>
                <th>Close Reason</th>
              </tr>
            </thead>
            <tbody>
              {account?.closed_positions && account.closed_positions.length > 0 ? (
                account.closed_positions.map((pos: any, i: number) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600 }}>{pos.symbol}</td>
                    <td>
                      <span className={`badge badge-${pos.side === 'LONG' ? 'success' : 'danger'}`}>
                        {pos.side}
                      </span>
                    </td>
                    <td className="mono">${parseFloat(String(pos.entry_price)).toFixed(4)}</td>
                    <td className="mono">${parseFloat(String(pos.current_price)).toFixed(4)}</td>
                    <td className="mono" style={{
                      color: parseFloat(String(pos.realized_pnl)) >= 0 ? 'var(--success)' : 'var(--danger)',
                      fontWeight: 700
                    }}>
                      ${parseFloat(String(pos.realized_pnl)).toFixed(2)}
                    </td>
                    <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {pos.close_reason || '—'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '32px 16px' }}>
                    No closed positions in history yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Live Console */}
      <LiveConsole />

      {/* ── Spring-Animated Config Modal ──────────────────────── */}
      <AnimatePresence>
        {showConfigModal && (
          <motion.div
            className="modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="card"
              initial={{ scale: 0.95, y: 16 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 16 }}
              transition={{ type: 'spring', stiffness: 350, damping: 30 }}
              style={{
                padding: '30px',
                width: 560,
                maxWidth: '95vw',
                maxHeight: '90vh',
                overflowY: 'auto',
                border: '1px solid var(--border-strong)',
                boxShadow: 'var(--shadow-md)',
              }}
            >
              {/* Modal Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Launch Trading Bot</h2>
                <button className="btn-ghost" style={{ padding: '6px' }} onClick={() => setShowConfigModal(false)}>
                  <X size={16} />
                </button>
              </div>

              {/* Exchanges */}
              <div style={{ marginBottom: 20 }}>
                <div className="section-label" style={{ marginBottom: 8 }}>Exchanges</div>
                <div className="grid-cols-2">
                  {['BINANCE', 'MEXC'].map(ex => (
                    <OptionCard
                      key={ex}
                      selected={configExchanges.includes(ex)}
                      onClick={() => {
                        if (configExchanges.includes(ex)) {
                          if (configExchanges.length > 1) {
                            setConfigExchanges(configExchanges.filter(e => e !== ex));
                          }
                        } else {
                          setConfigExchanges([...configExchanges, ex]);
                        }
                      }}
                      title={ex}
                    />
                  ))}
                </div>
              </div>

              {/* Trading Mode */}
              <div style={{ marginBottom: 20 }}>
                <div className="section-label" style={{ marginBottom: 8 }}>Strategy Mode</div>
                <div className="grid-cols-3">
                  {[
                    { key: 'scalping', label: 'Scalping', badge: '15m', sub: 'RSI · Bollinger', interval: '30' },
                    { key: 'swing',    label: 'Swing',    badge: '4h',  sub: 'MACD Cross',      interval: '120' },
                    { key: 'hodl',     label: 'HODL',     badge: '1d',  sub: 'EMA Golden',       interval: '3600' },
                  ].map(m => (
                    <OptionCard
                      key={m.key}
                      selected={configMode === m.key}
                      badge={m.badge}
                      onClick={() => { setConfigMode(m.key); setConfigInterval(m.interval); }}
                      title={m.label}
                      sub={m.sub}
                    />
                  ))}
                </div>
              </div>

              {/* Risk Slider */}
              <div style={{ marginBottom: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <div className="section-label">Risk Level Setting</div>
                  <span className="mono" style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {configRiskLevel} — {riskLabel(configRiskLevel)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={configRiskLevel}
                  onChange={e => setConfigRiskLevel(+e.target.value)}
                />
              </div>

              {/* Symbol Source */}
              <div style={{ marginBottom: 20 }}>
                <div className="section-label" style={{ marginBottom: 8 }}>Symbol Selection Mode</div>
                <div className="grid-cols-2">
                  {[
                    { key: 'manual', label: 'Manual List', sub: 'Hand-picked coins' },
                    { key: 'auto',   label: '🤖 Auto-Scanner', sub: 'Hunt top gainers live' },
                  ].map(s => (
                    <OptionCard
                      key={s.key}
                      selected={configSymbolSource === s.key}
                      onClick={() => setConfigSymbolSource(s.key as any)}
                      title={s.label}
                      sub={s.sub}
                    />
                  ))}
                </div>
              </div>

              {/* Manual symbols */}
              {configSymbolSource === 'manual' && (
                <>
                  <div style={{ marginBottom: 16 }}>
                    <div className="section-label" style={{ marginBottom: 8 }}>Quick-Select Coins</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
                      {favoriteCoins.map(coin => (
                        <button
                          key={coin}
                          type="button"
                          onClick={() => toggleCoin(coin)}
                          className={isCoinSelected(coin) ? 'btn-primary' : 'btn-secondary'}
                          style={{ padding: '4px 10px', fontSize: '0.75rem', fontFamily: 'JetBrains Mono, monospace' }}
                        >
                          {coin}
                        </button>
                      ))}
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input
                        type="text"
                        className="form-input mono"
                        style={{ flex: 1, fontSize: '0.8rem' }}
                        value={newFavorite}
                        onChange={e => setNewFavorite(e.target.value.toUpperCase())}
                        placeholder="Add coin (e.g. ADAUSDT)"
                        onKeyDown={e => {
                          if (e.key === 'Enter') {
                            const c = newFavorite.trim().toUpperCase();
                            if (c && !favoriteCoins.includes(c)) setFavoriteCoins([...favoriteCoins, c]);
                            setNewFavorite('');
                          }
                        }}
                      />
                      <button
                        type="button"
                        className="btn-secondary"
                        style={{ fontSize: '0.8rem' }}
                        onClick={() => {
                          const c = newFavorite.trim().toUpperCase();
                          if (c && !favoriteCoins.includes(c)) setFavoriteCoins([...favoriteCoins, c]);
                          setNewFavorite('');
                        }}
                      >
                        Add
                      </button>
                    </div>
                  </div>

                  <div style={{ marginBottom: 18 }}>
                    <label className="section-label" style={{ display: 'block', marginBottom: 6 }}>
                      Trading Pairs (comma-separated)
                    </label>
                    <textarea
                      className="form-input mono"
                      style={{ fontSize: '0.8rem' }}
                      value={configSymbols}
                      onChange={e => setConfigSymbols(e.target.value)}
                    />
                  </div>
                </>
              )}

              {/* Safety Shields */}
              <div style={{
                marginBottom: 24,
                padding: '16px',
                background: 'var(--bg-raised)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)'
              }}>
                <div className="section-label" style={{ marginBottom: 10 }}>Safety Shield Controls</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.82rem', color: 'var(--text-primary)', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={configBtcShield}
                      onChange={e => setConfigBtcShield(e.target.checked)}
                      style={{ accentColor: 'var(--text-primary)' }}
                    />
                    BTC Crash Shield <span className="text-muted">(Downtrend protection)</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.82rem', color: 'var(--text-primary)', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={configHtfShield}
                      onChange={e => setConfigHtfShield(e.target.checked)}
                      style={{ accentColor: 'var(--text-primary)' }}
                    />
                    HTF Trend Shield <span className="text-muted">(Higher timeframe alignment)</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.82rem', color: 'var(--text-primary)', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={configRegimeShield}
                      onChange={e => setConfigRegimeShield(e.target.checked)}
                      style={{ accentColor: 'var(--text-primary)' }}
                    />
                    Market Regime Shield <span className="text-muted">(High-volatility barrier)</span>
                  </label>
                </div>
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                <button className="btn-secondary" onClick={() => setShowConfigModal(false)}>Cancel</button>
                <button className="btn-primary" onClick={handleStartBot} disabled={loading}>
                  {loading ? <RefreshCw size={14} className="animate-spin" /> : <ChevronRight size={14} />}
                  {loading ? 'Starting…' : 'Launch Bot'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
};

export default PaperTrading;
