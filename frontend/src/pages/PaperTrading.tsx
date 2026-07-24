import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import LiveConsole from '../components/LiveConsole';

const OptionBox: React.FC<{ selected: boolean; onClick: () => void; label: string; sub?: string }> = ({ selected, onClick, label, sub }) => (
  <div onClick={onClick} style={{ border: `1px solid ${selected ? 'var(--accent)' : 'var(--border)'}`, background: selected ? 'var(--accent-soft)' : 'transparent', padding: '12px 16px', cursor: 'pointer', fontFamily: '"JetBrains Mono", monospace' }}>
    <div style={{ color: selected ? 'var(--accent)' : 'var(--text-primary)', fontWeight: selected ? 600 : 400 }}>{label}</div>
    {sub && <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>{sub}</div>}
  </div>
);

const PaperTrading: React.FC = () => {
  const [account, setAccount]       = useState<any>(null);
  const [loading, setLoading]       = useState(false);
  const [actionLog, setActionLog]   = useState<any>(null);
  const [botStatus, setBotStatus]   = useState<any>(null);
  const [showConfig, setShowConfig] = useState(false);

  const get = (k: string, def: string) => typeof window !== 'undefined' && localStorage.getItem(k) ? localStorage.getItem(k)! : def;
  const [configSymbols, setConfigSymbols] = useState(() => get('configSymbols', 'BTCUSDT, ETHUSDT'));
  const [configMode, setConfigMode]       = useState(() => get('configMode', 'regime_adaptive'));
  const [configInterval, setConfigInterval] = useState(() => get('configInterval', '120'));
  const [configExchange, setConfigExchange] = useState(() => get('configExchange', 'BINANCE'));
  const [configRiskLevel, setConfigRiskLevel] = useState(() => get('configRiskLevel', '100'));
  const [configSymbolSource, setConfigSymbolSource] = useState<'manual' | 'auto'>(() => (get('configSymbolSource', 'manual') as any));

  useEffect(() => { localStorage.setItem('configSymbols', configSymbols); }, [configSymbols]);
  useEffect(() => { localStorage.setItem('configMode', configMode); }, [configMode]);
  useEffect(() => { localStorage.setItem('configInterval', configInterval); }, [configInterval]);
  useEffect(() => { localStorage.setItem('configExchange', configExchange); }, [configExchange]);
  useEffect(() => { localStorage.setItem('configRiskLevel', configRiskLevel); }, [configRiskLevel]);
  useEffect(() => { localStorage.setItem('configSymbolSource', configSymbolSource); }, [configSymbolSource]);

  const fetchAccount = async () => {
    try {
      const res = await axios.get('/api/v1/paper/mock/account');
      setAccount(res.data);
    } catch (e: any) {
      if (e.response?.status === 404) {
        const initRes = await axios.post('/api/v1/paper/mock/account/init');
        setAccount(initRes.data);
      }
    }
  };

  const fetchBotStatus = async () => {
    try { const res = await axios.get('/api/v1/bot/status'); setBotStatus(res.data); }
    catch {}
  };

  useEffect(() => {
    fetchAccount(); fetchBotStatus();
    const iv = setInterval(() => { fetchAccount(); fetchBotStatus(); }, 5000);
    return () => clearInterval(iv);
  }, []);

  const handleStartBot = async () => {
    setLoading(true);
    try {
      const symbolsList = configSymbolSource === 'auto' ? ['AUTO_GAINERS'] : configSymbols.split(',').map(s => s.trim().toUpperCase()).filter(s => s);
      const res = await axios.post('/api/v1/bot/start', {
        bot_id: `bot-${Date.now()}`,
        interval_seconds: parseInt(configInterval, 10),
        symbols: symbolsList,
        mode: configMode,
        exchange: configExchange,
        risk_level: parseInt(configRiskLevel, 10),
      });
      setBotStatus(res.data);
      setShowConfig(false);
    } catch (err) {}
    setLoading(false);
  };

  const handleStopBot = async (bot_id: string) => {
    setLoading(true);
    try { const res = await axios.post(`/api/v1/bot/stop/${bot_id}`); setBotStatus(res.data); }
    catch {}
    setLoading(false);
  };

  const handleForceCycle = async () => {
    setLoading(true);
    try {
      const symbolsList = configSymbols.split(',').map(s => s.trim().toUpperCase()).filter(s => s);
      const res = await axios.post('/api/v1/cycle/run', {
        account_name: 'default-paper', exchange: 'BINANCE', symbols: symbolsList,
        timeframe: configMode === 'scalping' ? '1m' : '4h',
        strategy_name: configMode === 'scalping' ? 'hft_momentum' : 'macd_cross',
        trigger: 'MANUAL',
      });
      setActionLog(res.data);
      await fetchAccount();
    } catch {}
    setLoading(false);
  };

  const bots = botStatus?.bots || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      
      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '1px solid var(--border)', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '1.5rem', marginBottom: '8px' }}>[EXECUTION_BOTS]</h1>
          <p style={{ margin: 0, fontSize: '0.85rem' }}>Paper trading simulation & bot management</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn-secondary" onClick={handleForceCycle} disabled={loading}>FORCE_CYCLE</button>
          <button className="btn-primary" onClick={() => setShowConfig(true)} disabled={loading}>DEPLOY_BOT</button>
        </div>
      </div>

      {/* ── Account Summary ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
        {[
          { label: 'EQUITY', value: `$${account ? parseFloat(account.equity).toFixed(2) : '0.00'}`, color: 'var(--accent)' },
          { label: 'CASH_BALANCE', value: `$${account ? parseFloat(account.cash_balance).toFixed(2) : '0.00'}` },
          { label: 'ACTIVE_POSITIONS', value: account?.open_positions?.length ?? 0 },
        ].map(item => (
          <div key={item.label} style={{ border: '1px solid var(--border)', padding: '16px 20px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: '"JetBrains Mono", monospace' }}>{item.label}</div>
            <div style={{ fontSize: '1.5rem', color: item.color || 'var(--text-primary)', fontFamily: '"JetBrains Mono", monospace', marginTop: '8px' }}>{item.value}</div>
          </div>
        ))}
      </div>

      {/* ── Action Log ── */}
      {actionLog && (
        <div style={{ border: `1px solid ${actionLog.status === 'REJECTED' ? 'var(--danger)' : 'var(--success)'}`, padding: '16px 20px', background: 'var(--bg-raised)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontFamily: '"JetBrains Mono", monospace', color: actionLog.status === 'REJECTED' ? 'var(--danger)' : 'var(--success)' }}>CYCLE: {actionLog.status}</span>
            <button className="btn-ghost" onClick={() => setActionLog(null)} style={{ padding: '0 8px' }}>[X]</button>
          </div>
          {actionLog.status === 'REJECTED' ? (
            <div style={{ color: 'var(--danger)', fontSize: '0.85rem' }}>{actionLog.reason}</div>
          ) : (
            <div style={{ display: 'flex', gap: '32px', fontFamily: '"JetBrains Mono", monospace' }}>
              <div><span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>PROCESSED</span><br/>{actionLog.symbols_processed}</div>
              <div><span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>DECISIONS</span><br/>{actionLog.decisions_made}</div>
              <div><span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>TRADES</span><br/>{actionLog.trades_executed}</div>
            </div>
          )}
        </div>
      )}

      {/* ── Bot Status ── */}
      <div>
        <h3 style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '1rem', marginBottom: '16px' }}>&gt; ACTIVE_PROCESSES</h3>
        {bots.length === 0 ? (
          <div style={{ border: '1px dashed var(--border)', padding: '32px', textAlign: 'center', color: 'var(--text-muted)', fontFamily: '"JetBrains Mono", monospace' }}>[ NO BOTS RUNNING ]</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {bots.map((bot: any) => (
              <div key={bot.bot_id} style={{ border: '1px solid var(--border)', padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-raised)' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                    <div style={{ width: 8, height: 8, background: bot.status === 'RUNNING' ? 'var(--success)' : 'var(--danger)' }} />
                    <span style={{ fontFamily: '"JetBrains Mono", monospace', fontWeight: 600 }}>{bot.bot_id}</span>
                    <span style={{ fontSize: '0.75rem', color: bot.status === 'RUNNING' ? 'var(--success)' : 'var(--danger)' }}>[{bot.status}]</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: '"JetBrains Mono", monospace' }}>
                    MODE: {bot.mode?.toUpperCase()} | PAIRS: {bot.symbols?.join(', ')}
                  </div>
                </div>
                {bot.status === 'RUNNING' && (
                  <button className="btn-danger" onClick={() => handleStopBot(bot.bot_id)}>TERMINATE</button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Open Positions ── */}
      <div>
        <h3 style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '1rem', marginBottom: '16px' }}>&gt; OPEN_POSITIONS</h3>
        <table className="glass-table">
          <thead>
            <tr style={{ background: '#050505' }}>
              <th>SYMBOL</th>
              <th>SIDE</th>
              <th>QUANTITY</th>
              <th>ENTRY_PRICE</th>
              <th>UNREALIZED_PNL</th>
            </tr>
          </thead>
          <tbody>
            {account?.open_positions?.length > 0 ? account.open_positions.map((pos: any, i: number) => (
              <tr key={i}>
                <td>{pos.symbol}</td>
                <td><span style={{ color: pos.side === 'LONG' ? 'var(--success)' : 'var(--danger)' }}>{pos.side}</span></td>
                <td>{parseFloat(pos.quantity).toFixed(4)}</td>
                <td>${parseFloat(pos.entry_price).toFixed(2)}</td>
                <td style={{ color: parseFloat(pos.unrealized_pnl) >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                  ${parseFloat(pos.unrealized_pnl).toFixed(2)}
                </td>
              </tr>
            )) : (
              <tr><td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>[ EMPTY ]</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <LiveConsole />

      {/* ── Config Overlay ── */}
      <AnimatePresence>
        {showConfig && (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.9)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }} style={{ width: '500px', background: 'var(--bg-base)', border: '1px solid var(--accent)', padding: '32px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
                <h2 style={{ margin: 0, fontFamily: '"JetBrains Mono", monospace', fontSize: '1.25rem', color: 'var(--accent)' }}>DEPLOY_PARAMETERS</h2>
                <button className="btn-ghost" onClick={() => setShowConfig(false)}>[X]</button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                <div>
                  <div className="section-label" style={{ marginBottom: '8px' }}>EXCHANGE</div>
                  <select className="form-input" value={configExchange} onChange={e => setConfigExchange(e.target.value)} style={{ background: 'var(--bg-base)', border: '1px solid var(--border)' }}>
                    <option value="BINANCE">BINANCE</option>
                    <option value="MEXC">MEXC</option>
                  </select>
                </div>

                <div>
                  <div className="section-label" style={{ marginBottom: '8px' }}>STRATEGY_MODE</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    <OptionBox selected={configMode === 'regime_adaptive'} onClick={() => setConfigMode('regime_adaptive')} label="REGIME ADAPTIVE" sub="AI driven" />
                    <OptionBox selected={configMode === 'scalping'} onClick={() => setConfigMode('scalping')} label="SCALPING" sub="High frequency" />
                    <OptionBox selected={configMode === 'swing'} onClick={() => setConfigMode('swing')} label="SWING" sub="Momentum based" />
                    <OptionBox selected={configMode === 'hodl'} onClick={() => setConfigMode('hodl')} label="HODL" sub="Long term" />
                  </div>
                </div>

                <div>
                  <div className="section-label" style={{ marginBottom: '8px' }}>SYMBOL SOURCE</div>
                  <select className="form-input" value={configSymbolSource} onChange={e => setConfigSymbolSource(e.target.value as any)} style={{ background: 'var(--bg-base)', border: '1px solid var(--border)' }}>
                    <option value="manual">MANUAL (CSV)</option>
                    <option value="auto">AUTO GAINERS (LIVE)</option>
                  </select>
                </div>

                {configSymbolSource === 'manual' && (
                  <div>
                    <div className="section-label" style={{ marginBottom: '8px' }}>TARGET_SYMBOLS</div>
                    <input type="text" className="form-input" value={configSymbols} onChange={e => setConfigSymbols(e.target.value)} placeholder="BTCUSDT, ETHUSDT" style={{ background: 'var(--bg-base)', border: '1px solid var(--border)' }} />
                  </div>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  {configMode !== 'scalping' && (
                    <div>
                      <div className="section-label" style={{ marginBottom: '8px' }}>INTERVAL_SEC</div>
                      <input type="number" className="form-input" value={configInterval} onChange={e => setConfigInterval(e.target.value)} style={{ background: '#000', border: '1px solid var(--border)' }} />
                    </div>
                  )}
                  <div>
                    <div className="section-label" style={{ marginBottom: '8px' }}>RISK_LEVEL: {configRiskLevel}%</div>
                    <input type="range" min="1" max="100" className="form-input" style={{ padding: '0', cursor: 'pointer' }} value={configRiskLevel} onChange={e => setConfigRiskLevel(e.target.value)} />
                  </div>
                </div>
              </div>

              <div style={{ marginTop: '32px', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button className="btn-secondary" onClick={() => setShowConfig(false)}>CANCEL</button>
                <button className="btn-primary" onClick={handleStartBot} disabled={loading}>EXECUTE_DEPLOYMENT</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
};

export default PaperTrading;
