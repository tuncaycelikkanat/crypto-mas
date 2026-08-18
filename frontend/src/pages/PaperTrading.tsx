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

// ── Helper ────────────────────────────────────────────────────
const OptionCard: React.FC<{
  selected: boolean;
  onClick: () => void;
  title: string;
  sub?: string;
  badge?: string;
}> = ({ selected, onClick, title, sub, badge }) => (
  <motion.div
    whileHover={{ scale: 1.02 }}
    whileTap={{ scale: 0.98 }}
    className={`option-card ${selected ? 'selected' : ''}`}
    onClick={onClick}
  >
    {badge && (
      <div style={{ marginBottom: 6 }}>
        <span className="badge badge-primary">{badge}</span>
      </div>
    )}
    <div className="option-card-title">{title}</div>
    {sub && <div className="option-card-sub">{sub}</div>}
  </motion.div>
);

// ── Page ─────────────────────────────────────────────────────
const PaperTrading: React.FC = () => {
  const [accounts, setAccounts]     = useState<PaperAccount[]>([]);
  const [selectedAccountName, setSelectedAccountName] = useState<string>('main');
  const account = accounts.find(a => a.name === selectedAccountName) || accounts[0] || null;
  const [loading, setLoading]       = useState(false);
  const [actionLog, setActionLog]   = useState<CycleResponse | { status: string; reason?: string } | null>(null);
  const [botStatus, setBotStatus]   = useState<BotStatusResponse | null>(null);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [editingSymbols, setEditingSymbols]   = useState<Record<string, string>>({});
  const [editingRiskLevels, setEditingRiskLevels] = useState<Record<string, number>>({});

  // ─ Config state ─
  const [configInterval,      setConfigInterval]      = useLocalStorage('configInterval', '30');
  const [configSymbols,       setConfigSymbols]       = useLocalStorage('configSymbols', 'BTCUSDT');
  const [configSymbolSource,  setConfigSymbolSource]  = useLocalStorage('configSymbolSource', 'auto');
  const [configExchanges,     setConfigExchanges]     = useLocalStorage<string[]>('configExchanges', ['BINANCE']);
  const [configMode,          setConfigMode]          = useLocalStorage('configMode', 'scalping');
  const [configBtcShield, setConfigBtcShield] = useLocalStorage('configBtcShield', true);
  const [configHtfShield, setConfigHtfShield] = useLocalStorage('configHtfShield', true);
  const [configRegimeShield, setConfigRegimeShield] = useLocalStorage('configRegimeShield', true);
  const [configRiskLevel,     setConfigRiskLevel]     = useLocalStorage('configRiskLevel', 50);
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
    try { const res = await getBotStatus(); setBotStatus(res.data); }
    catch { /* ignore */ }
  };

  useEffect(() => {
    fetchAccount(); fetchBotStatus();
    const iv = setInterval(() => { fetchAccount(); fetchBotStatus(); }, 5000);
    return () => clearInterval(iv);
  }, []);

  const handleStartBot = async () => {
    setLoading(true);
    try {
      const symbolsList = configSymbolSource === 'auto'
        ? ['AUTO_GAINERS']
        : configSymbols.split(',').map(s => s.trim().toUpperCase()).filter(s => s);
      
      // Start a single bot for this specific slot using the selectedAccountName as bot_id
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
    try { const res = await stopBot(bot_id); setBotStatus(res.data); }
    catch (err) { console.error(err); }
    setLoading(false);
  };

  const handleManualCycle = async () => {
    setLoading(true); setActionLog(null);
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
      setBotStatus((prev: BotStatusResponse | null) => prev ? { ...prev, bots: prev.bots.map((b: BotInfo) => b.bot_id === bot_id ? { ...b, risk_level: risk } : b) } : prev);
    } catch (err) { console.error(err); }
  };

  const normalizeSymbols = (s: string | string[]) => {
    const arr = Array.isArray(s) ? s : s.split(',');
    return arr.map(x => x.trim().toUpperCase()).filter(Boolean).sort().join(',');
  };

  const bots = botStatus?.bots || [];
  const riskLabel = (v: number) => v < 33 ? 'Conservative' : v < 66 ? 'Balanced' : 'Aggressive';
  const riskColor = (v: number) => v < 33 ? 'var(--success)' : v < 66 ? 'var(--warning)' : 'var(--danger)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
        <div>
          <h1 style={{ marginBottom: 4 }}>Paper Trading</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Simulate live market operations with real-time decision making.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button className="btn-secondary" onClick={handleManualCycle} disabled={loading}>
            <PlayCircle size={15} />
            Force Cycle
          </button>
          <button className="btn-primary" onClick={() => setShowConfigModal(true)} disabled={loading}>
            {loading ? <RefreshCw size={15} className="animate-spin" /> : <Bot size={15} />}
            {loading ? 'Processing…' : 'Start Trading'}
          </button>
        </div>
      </motion.div>

      {/* Account Tabs */}
      {accounts.length > 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ display: 'flex', gap: '10px', overflowX: 'auto', paddingBottom: '4px', borderBottom: '1px solid var(--border)' }}>
          {accounts.map(acc => (
            <button
              key={acc.name}
              className={selectedAccountName === acc.name ? 'btn-primary' : 'btn-ghost'}
              onClick={() => setSelectedAccountName(acc.name!)}
              style={{ whiteSpace: 'nowrap', borderRadius: '8px 8px 0 0', padding: '8px 16px' }}
            >
              <Bot size={14} style={{ marginRight: 6, display: 'inline-block', verticalAlign: 'text-bottom' }}/>
              {acc.name === 'main' ? 'Main Account' : acc.name === 'slot-2' ? 'Slot 2' : acc.name === 'slot-3' ? 'Slot 3' : acc.name === 'slot-4' ? 'Slot 4' : acc.name}
            </button>
          ))}
        </motion.div>
      )}

      {/* Account Summary */}
      <div className="grid-cols-3">
        {[
          { label: 'Equity', value: `$${account ? parseFloat(String(account.equity)).toFixed(2) : '0.00'}`, accent: true },
          { label: 'Cash Balance', value: `$${account ? parseFloat(String(account.cash_balance)).toFixed(2) : '0.00'}` },
          { label: 'Active Positions', value: account?.open_positions?.length ?? 0 },
        ].map((item, i) => (
          <motion.div key={item.label} className="card" style={{ padding: '20px 22px' }}
            initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }} whileHover={{ y: -2 }}>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 10 }}>
              {item.label}
            </div>
            <div className="stat-value" style={{ color: item.accent ? 'var(--accent)' : 'var(--text-primary)' }}>
              {item.value}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Action Log */}
      <AnimatePresence>
        {actionLog && (
          <motion.div className="card" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
            style={{ padding: '18px 22px', borderLeft: `3px solid ${actionLog.status === 'REJECTED' ? 'var(--danger)' : 'var(--success)'}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0 }}>Last Cycle — <span style={{ color: actionLog.status === 'REJECTED' ? 'var(--danger)' : 'var(--success)' }}>{actionLog.status}</span></h3>
              <button className="btn-ghost" style={{ padding: '4px 6px' }} onClick={() => setActionLog(null)}><X size={14} /></button>
            </div>
            {actionLog.status === 'REJECTED'
              ? <p className="text-danger" style={{ marginTop: 8 }}>{actionLog.reason}</p>
              : (
                <div style={{ display: 'flex', gap: 24, marginTop: 10 }}>
                  {[['Processed', (actionLog as any).symbols_processed], ['Decisions', (actionLog as any).decisions_made], ['Trades', (actionLog as any).trades_executed]].map(([k, v]) => (
                    <div key={k}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{k}</div>
                      <div style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--success)' }}>{v}</div>
                    </div>
                  ))}
                </div>
              )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bot Status */}
      {bots.filter((b: BotInfo) => b.bot_id === selectedAccountName).length === 0 ? (
        <motion.div className="card" style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: 14 }}
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div style={{ width: 40, height: 40, borderRadius: 12, background: 'var(--bg-raised)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <XCircle size={20} color="var(--text-muted)" />
          </div>
          <div>
            <div style={{ fontWeight: 600, marginBottom: 2 }}>No Active Bots</div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Click "Start Trading" to launch an automated bot.</div>
          </div>
        </motion.div>
      ) : (
        bots.filter((b: BotInfo) => b.bot_id === selectedAccountName).map((bot: BotInfo) => {
          const isRunning = bot.status === 'RUNNING';
          const currentEditingStr = editingSymbols[bot.bot_id] !== undefined ? editingSymbols[bot.bot_id] : (bot.symbols?.join(', ') || '');
          const hasChanged = normalizeSymbols(currentEditingStr) !== normalizeSymbols(bot.symbols || []);
          const currentRisk = editingRiskLevels[bot.bot_id] !== undefined ? editingRiskLevels[bot.bot_id] : (bot.risk_level ?? 50);

          return (
            <motion.div key={bot.bot_id} className="card" style={{ padding: '22px 24px', borderLeft: `3px solid ${isRunning ? 'var(--success)' : 'var(--border-strong)'}` }}
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              {/* Bot header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: isRunning ? 20 : 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  {isRunning ? (
                    <motion.div animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 2, repeat: Infinity }}
                      style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--success)', boxShadow: '0 0 8px var(--success)' }} />
                  ) : (
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--text-muted)' }} />
                  )}
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>Bot: <span className="mono">{bot.bot_id}</span></div>
                    <div style={{ fontSize: '0.78rem', color: isRunning ? 'var(--success)' : 'var(--text-muted)', marginTop: 2 }}>
                      {isRunning ? 'Online & Running' : bot.status}
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  {isRunning && bot.mode && (
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Mode</div>
                      <div style={{ fontWeight: 600, color: 'var(--accent)' }}>{bot.mode?.toUpperCase()} · {bot.exchange || 'BINANCE'}</div>
                    </div>
                  )}
                  {isRunning && (
                    <button className="btn-danger" onClick={() => handleStopBot(bot.bot_id)} disabled={loading}>
                      <Square size={13} /> Stop Bot
                    </button>
                  )}
                </div>
              </div>

              {/* Running details */}
              {isRunning && (
                <div style={{ paddingTop: 20, borderTop: '1px solid var(--border)' }}>
                  {/* Risk slider */}
                  <div style={{ marginBottom: 20 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                      <label style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Risk Level</label>
                      <span style={{ fontWeight: 700, fontSize: '0.85rem', color: riskColor(currentRisk) }}>
                        {currentRisk} — {riskLabel(currentRisk)}
                      </span>
                    </div>
                    <input type="range" min="0" max="100" value={currentRisk}
                      onChange={e => setEditingRiskLevels({ ...editingRiskLevels, [bot.bot_id]: +e.target.value })}
                      onMouseUp={e => handleRiskChange(bot.bot_id, +(e.target as HTMLInputElement).value)}
                      onTouchEnd={e => handleRiskChange(bot.bot_id, +(e.target as HTMLInputElement).value)}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.72rem', marginTop: 4 }}>
                      <span>Safe</span><span>Balanced</span><span>Aggressive</span>
                    </div>
                  </div>

                  {/* Symbol edit */}
                  {bot.symbols?.includes('AUTO_GAINERS') ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px', background: 'var(--accent-soft)', border: '1px solid var(--accent-border)', borderRadius: 10 }}>
                      <Activity size={20} color="var(--accent)" />
                      <div>
                        <div style={{ fontWeight: 600, color: 'var(--accent)', marginBottom: 2 }}>Auto-Scanner Active</div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Dynamically hunting top gainers every cycle.</div>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: 8 }}>Trading Pairs</label>
                      <div style={{ display: 'flex', gap: 10 }}>
                        <textarea className="form-input" style={{ flex: 1 }}
                          value={currentEditingStr}
                          onChange={e => setEditingSymbols({ ...editingSymbols, [bot.bot_id]: e.target.value })}
                        />
                        {hasChanged && (
                          <button className="btn-primary" onClick={() => handleUpdateSymbols(bot.bot_id)} disabled={loading} style={{ alignSelf: 'flex-end' }}>
                            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
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

      {/* Open Positions */}
      <motion.div className="card" style={{ padding: '22px 24px' }}
        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <h3 style={{ marginBottom: 18 }}>Open Positions</h3>
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
            {account?.open_positions && account.open_positions.length > 0 ? account.open_positions.map((pos: OpenPosition, i: number) => (
              <tr key={i}>
                <td style={{ fontWeight: 600 }}>{pos.symbol}</td>
                <td><span className={`badge badge-${pos.side === 'LONG' ? 'success' : 'danger'}`}>{pos.side}</span></td>
                <td className="mono">{parseFloat(String(pos.quantity)).toFixed(4)}</td>
                <td className="mono">${parseFloat(String(pos.entry_price)).toFixed(2)}</td>
                <td className="mono" style={{ color: parseFloat(String(pos.unrealized_pnl)) >= 0 ? 'var(--success)' : 'var(--danger)', fontWeight: 600 }}>
                  ${parseFloat(String(pos.unrealized_pnl)).toFixed(2)}
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '36px 16px' }}>
                  No open positions.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </motion.div>

      {/* Closed Positions */}
      <motion.div className="card" style={{ padding: '22px 24px', marginTop: '24px' }}
        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
        <h3 style={{ marginBottom: 18, display: 'flex', justifyContent: 'space-between' }}>
          <span>Closed Positions</span>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Total Closed: {account?.closed_positions?.length || 0}
          </span>
        </h3>
        <table className="glass-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Side</th>
              <th>Entry Price</th>
              <th>Exit Price</th>
              <th>Realized PnL</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {account?.closed_positions && account.closed_positions.length > 0 ? account.closed_positions.map((pos: any, i: number) => (
              <tr key={i}>
                <td style={{ fontWeight: 600 }}>{pos.symbol}</td>
                <td><span className={`badge badge-${pos.side === 'LONG' ? 'success' : 'danger'}`}>{pos.side}</span></td>
                <td className="mono">${parseFloat(String(pos.entry_price)).toFixed(4)}</td>
                <td className="mono">${parseFloat(String(pos.current_price)).toFixed(4)}</td>
                <td className="mono" style={{ color: parseFloat(String(pos.realized_pnl)) >= 0 ? 'var(--success)' : 'var(--danger)', fontWeight: 600 }}>
                  ${parseFloat(String(pos.realized_pnl)).toFixed(2)}
                </td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{pos.close_reason || '-'}</td>
              </tr>
            )) : (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '36px 16px' }}>
                  No closed positions.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </motion.div>

      {/* Live Console */}
      <LiveConsole />

      {/* ── Config Modal ──────────────────────────────────────── */}
      <AnimatePresence>
        {showConfigModal && (
          <motion.div className="modal-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <motion.div className="card"
              initial={{ scale: 0.95, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 20 }}
              style={{ padding: '32px', width: 560, maxWidth: '95vw', maxHeight: '90vh', overflowY: 'auto' }}>

              {/* Modal header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
                <h2 style={{ margin: 0 }}>Bot Configuration</h2>
                <button className="btn-ghost" style={{ padding: '6px 8px' }} onClick={() => setShowConfigModal(false)}>
                  <X size={16} />
                </button>
              </div>

              {/* Exchanges */}
              <div style={{ marginBottom: 22 }}>
                <div className="section-label" style={{ marginBottom: 10 }}>Exchange(s)</div>
                <div className="grid-cols-2">
                  {['BINANCE', 'MEXC'].map(ex => (
                    <OptionCard key={ex} 
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

              {/* Mode */}
              <div style={{ marginBottom: 22 }}>
                <div className="section-label" style={{ marginBottom: 10 }}>Trading Mode</div>
                <div className="grid-cols-3">
                  {[
                    { key: 'scalping', label: 'Scalping',     badge: '15m', sub: 'RSI · Bollinger', interval: '30' },
                    { key: 'swing',    label: 'Swing',        badge: '4h',  sub: 'MACD Cross',       interval: '120' },
                    { key: 'hodl',     label: 'HODL',         badge: '1d',  sub: 'EMA Golden',        interval: '3600' },
                  ].map(m => (
                    <OptionCard key={m.key} selected={configMode === m.key} badge={m.badge}
                      onClick={() => { setConfigMode(m.key); setConfigInterval(m.interval); }}
                      title={m.label} sub={m.sub} />
                  ))}
                </div>
              </div>

              {/* Risk */}
              <div style={{ marginBottom: 22 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                  <div className="section-label">Risk Level</div>
                  <span style={{ fontSize: '0.82rem', fontWeight: 700, color: riskColor(configRiskLevel) }}>
                    {configRiskLevel} — {riskLabel(configRiskLevel)}
                  </span>
                </div>
                <input type="range" min="0" max="100" value={configRiskLevel} onChange={e => setConfigRiskLevel(+e.target.value)} />
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.72rem', marginTop: 6 }}>
                  <span>Safe</span><span>Balanced</span><span>Aggressive</span>
                </div>
              </div>

              {/* Symbol source */}
              <div style={{ marginBottom: 22 }}>
                <div className="section-label" style={{ marginBottom: 10 }}>Symbol Source</div>
                <div className="grid-cols-2">
                  {[
                    { key: 'manual', label: 'Manual List',      sub: 'Select coins manually' },
                    { key: 'auto',   label: '🤖 Auto-Scanner', sub: 'Hunt top gainers live' },
                  ].map(s => (
                    <OptionCard key={s.key} selected={configSymbolSource === s.key}
                      onClick={() => setConfigSymbolSource(s.key as any)} title={s.label} sub={s.sub} />
                  ))}
                </div>
              </div>

              {/* Manual symbols */}
              {configSymbolSource === 'manual' && (
                <>
                  {/* Favorite coins */}
                  <div style={{ marginBottom: 16 }}>
                    <div className="section-label" style={{ marginBottom: 10 }}>Quick-select Coins</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
                      {favoriteCoins.map(coin => (
                        <motion.button key={coin} whileTap={{ scale: 0.95 }}
                          onClick={() => toggleCoin(coin)}
                          className={isCoinSelected(coin) ? 'btn-primary' : 'btn-secondary'}
                          style={{ padding: '5px 12px', fontSize: '0.8rem', fontWeight: 600 }}>
                          {coin}
                        </motion.button>
                      ))}
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input type="text" className="form-input" style={{ flex: 1 }}
                        value={newFavorite} onChange={e => setNewFavorite(e.target.value.toUpperCase())}
                        placeholder="Add coin (e.g. ADAUSDT)"
                        onKeyDown={e => { if (e.key === 'Enter') { const c = newFavorite.trim().toUpperCase(); if (c && !favoriteCoins.includes(c)) setFavoriteCoins([...favoriteCoins, c]); setNewFavorite(''); } }}
                      />
                      <button className="btn-secondary" onClick={() => {
                        const c = newFavorite.trim().toUpperCase();
                        if (c && !favoriteCoins.includes(c)) setFavoriteCoins([...favoriteCoins, c]);
                        setNewFavorite('');
                      }}>Add</button>
                    </div>
                  </div>

                  {/* Manual text */}
                  <div style={{ marginBottom: 18 }}>
                    <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: 8 }}>
                      Trading Pairs (comma-separated)
                    </label>
                    <textarea className="form-input" value={configSymbols} onChange={e => setConfigSymbols(e.target.value)} />
                  </div>
                </>
              )}

              {/* Interval */}
              {configMode !== 'scalping' && (
                <div style={{ marginBottom: 22 }}>
                  <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: 8 }}>
                    Analysis Interval (seconds)
                  </label>
                  <input type="number" className="form-input" value={configInterval} onChange={e => setConfigInterval(e.target.value)} />
                </div>
              )}

              {configMode === 'scalping' && (
                <div style={{ display: 'flex', gap: 12, padding: '14px 16px', background: 'var(--accent-soft)', border: '1px solid var(--accent-border)', borderRadius: 10, marginBottom: 22 }}>
                  <Activity size={18} color="var(--accent)" style={{ flexShrink: 0, marginTop: 2 }} />
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--accent)', marginBottom: 3 }}>HFT Scalping Mode</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Event-driven — listens to WebSocket volume spikes. No interval needed.</div>
                  </div>
                </div>
              )}

              {/* Shields */}
              <div style={{ marginBottom: 26, padding: '16px', background: 'var(--bg-raised)', borderRadius: '10px' }}>
                <div className="section-label" style={{ marginBottom: 12 }}>Safety Shields</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                    <input type="checkbox" checked={configBtcShield} onChange={(e) => setConfigBtcShield(e.target.checked)} style={{ accentColor: 'var(--accent)' }} />
                    BTC Crash Shield <span className="text-muted">(Ani BTC çöküşlerinde durdurur)</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                    <input type="checkbox" checked={configHtfShield} onChange={(e) => setConfigHtfShield(e.target.checked)} style={{ accentColor: 'var(--accent)' }} />
                    HTF Trend Shield <span className="text-muted">(Üst zaman dilimiyle uyumlu)</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                    <input type="checkbox" checked={configRegimeShield} onChange={(e) => setConfigRegimeShield(e.target.checked)} style={{ accentColor: 'var(--accent)' }} />
                    Market Regime Shield <span className="text-muted">(Yüksek volatilite engeli)</span>
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
