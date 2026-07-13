import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { PlayCircle, RefreshCw, Square, CheckCircle2, XCircle, Activity } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import LiveConsole from '../components/LiveConsole';

const PaperTrading: React.FC = () => {
  const [account, setAccount] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [actionLog, setActionLog] = useState<any>(null);
  const [botStatus, setBotStatus] = useState<any>(null);
  const [editingSymbols, setEditingSymbols] = useState<Record<string, string>>({});
  const [editingRiskLevels, setEditingRiskLevels] = useState<Record<string, number>>({});
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [configSymbols, setConfigSymbols] = useState(() => typeof window !== 'undefined' && localStorage.getItem('configSymbols') ? localStorage.getItem('configSymbols')! : 'BTCUSDT, ETHUSDT, SOLUSDT');
  const [configInterval, setConfigInterval] = useState(() => typeof window !== 'undefined' && localStorage.getItem('configInterval') ? localStorage.getItem('configInterval')! : '120');
  const [configMode, setConfigMode] = useState(() => typeof window !== 'undefined' && localStorage.getItem('configMode') ? localStorage.getItem('configMode')! : 'swing');
  const [configExchange, setConfigExchange] = useState(() => typeof window !== 'undefined' && localStorage.getItem('configExchange') ? localStorage.getItem('configExchange')! : 'BINANCE');
  const [configSymbolSource, setConfigSymbolSource] = useState(() => typeof window !== 'undefined' && localStorage.getItem('configSymbolSource') ? localStorage.getItem('configSymbolSource')! : 'manual');
  const [configRiskLevel, setConfigRiskLevel] = useState(() => typeof window !== 'undefined' && localStorage.getItem('configRiskLevel') ? parseInt(localStorage.getItem('configRiskLevel')!, 10) : 50);

  const [favoriteCoins, setFavoriteCoins] = useState<string[]>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('favoriteCoins');
      if (saved) {
        try { return JSON.parse(saved); } catch (e) {}
      }
    }
    return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ZORAUSDT', 'HUMANUSDT'];
  });
  const [newFavorite, setNewFavorite] = useState('');

  useEffect(() => { localStorage.setItem('configSymbols', configSymbols); }, [configSymbols]);
  useEffect(() => { localStorage.setItem('configInterval', configInterval); }, [configInterval]);
  useEffect(() => { localStorage.setItem('configMode', configMode); }, [configMode]);
  useEffect(() => { localStorage.setItem('configExchange', configExchange); }, [configExchange]);
  useEffect(() => { localStorage.setItem('configSymbolSource', configSymbolSource); }, [configSymbolSource]);
  useEffect(() => { localStorage.setItem('configRiskLevel', configRiskLevel.toString()); }, [configRiskLevel]);
  useEffect(() => { localStorage.setItem('favoriteCoins', JSON.stringify(favoriteCoins)); }, [favoriteCoins]);

  const toggleFavoriteSelection = (coin: string) => {
    let currentSymbols = configSymbols.split(',').map(s => s.trim().toUpperCase()).filter(s => s);
    if (currentSymbols.includes(coin)) {
      currentSymbols = currentSymbols.filter(s => s !== coin);
    } else {
      currentSymbols.push(coin);
    }
    setConfigSymbols(currentSymbols.join(', '));
  };

  const handleAddFavorite = () => {
    const coin = newFavorite.trim().toUpperCase();
    if (coin && !favoriteCoins.includes(coin)) {
      setFavoriteCoins([...favoriteCoins, coin]);
    }
    setNewFavorite('');
  };

  const isCoinSelected = (coin: string) => {
    return configSymbols.split(',').map(s => s.trim().toUpperCase()).includes(coin);
  };

  const fetchAccount = async () => {
    try {
      const res = await axios.get('/api/v1/paper/mock/account');
      setAccount(res.data);
    } catch (e: any) {
      if (e.response && e.response.status === 404) {
        const initRes = await axios.post('/api/v1/paper/mock/account/init');
        setAccount(initRes.data);
      }
    }
  };

  useEffect(() => {
    const fetchBotStatus = async () => {
      try {
        const res = await axios.get('/api/v1/bot/status');
        setBotStatus(res.data);
      } catch (error) {
        console.error(error);
      }
    };
    fetchAccount();
    fetchBotStatus();
    const interval = setInterval(() => {
      fetchAccount();
      fetchBotStatus();
    }, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const handleStartBot = async () => {
    setLoading(true);
    try {
      const symbolsList = configSymbolSource === 'auto' 
        ? ['AUTO_GAINERS'] 
        : configSymbols.split(',').map(s => s.trim().toUpperCase()).filter(s => s);
      const bot_id = `bot-${Date.now()}`;
      const res = await axios.post('/api/v1/bot/start', { 
        bot_id: bot_id,
        interval_seconds: parseInt(configInterval, 10),
        symbols: symbolsList,
        mode: configMode,
        exchange: configExchange,
        risk_level: configRiskLevel
      });
      setBotStatus(res.data);
      setShowConfigModal(false);
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  const handleStopBot = async (bot_id: string) => {
    setLoading(true);
    try {
      const res = await axios.post(`/api/v1/bot/stop/${bot_id}`);
      setBotStatus(res.data);
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  const handleManualCycle = async () => {
    setLoading(true);
    setActionLog(null);
    try {
      const symbolsList = configSymbolSource === 'auto' 
        ? ['AUTO_GAINERS'] 
        : configSymbols.split(',').map(s => s.trim().toUpperCase()).filter(s => s);
        
      const res = await axios.post('/api/v1/cycle/run', {
        account_name: 'default-paper',
        exchange: configExchange,
        symbols: symbolsList,
        timeframe: configMode === 'scalping' ? '1m' : (configMode === 'swing' ? '4h' : '1d'),
        strategy_name: configMode === 'scalping' ? 'hft_momentum' : (configMode === 'swing' ? 'macd_cross' : 'ema_golden_cross'),
        trigger: 'MANUAL'
      });
      setActionLog(res.data);
      await fetchAccount(); // Refresh balances
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  const bots = botStatus?.bots || [];

  const normalizeSymbols = (str: string | string[]) => {
    if (Array.isArray(str)) return str.map(s => s.trim().toUpperCase()).filter(s => s).sort().join(',');
    return str.split(',').map(s => s.trim().toUpperCase()).filter(s => s).sort().join(',');
  };

  const handleUpdateSymbols = async (bot_id: string) => {
    setLoading(true);
    try {
      const symbolsStr = editingSymbols[bot_id] || '';
      const symbolsList = symbolsStr.split(',').map(s => s.trim().toUpperCase()).filter(s => s);
      await axios.put(`/api/v1/bot/symbols/${bot_id}`, { symbols: symbolsList });
      const res = await axios.get('/api/v1/bot/status');
      setBotStatus(res.data);
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  const handleRiskChange = async (bot_id: string, newRiskLevel: number) => {
    try {
      await axios.put(`/api/v1/bot/risk/${bot_id}`, { risk_level: newRiskLevel });
      setEditingRiskLevels((prev) => {
        const next = { ...prev };
        delete next[bot_id];
        return next;
      });
      setBotStatus((prev: any) => {
        if (!prev) return prev;
        return {
          ...prev,
          bots: prev.bots.map((b: any) => b.bot_id === bot_id ? { ...b, risk_level: newRiskLevel } : b)
        };
      });
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div>
      <div className="flex-between" style={{ marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>Live Paper Trading</h1>
          <p className="text-muted">Simulate live market operations with real-time decision making.</p>
        </div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <button className="btn-secondary" onClick={handleManualCycle} disabled={loading} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <PlayCircle size={18} />
            Force Cycle
          </button>
          
          <button 
            onClick={() => setShowConfigModal(true)} 
            disabled={loading} 
            style={{ 
              display: 'flex', alignItems: 'center', gap: '8px',
              padding: '12px 24px', borderRadius: '12px', fontWeight: 600,
              background: 'var(--primary)',
              color: 'white', border: 'none', cursor: 'pointer', transition: 'all 0.2s'
            }}>
            {loading ? <RefreshCw className="animate-spin" size={18} /> : <PlayCircle size={18} />}
            {loading ? 'Processing...' : 'Start Auto Trading'}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {showConfigModal && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
              background: 'rgba(0,0,0,0.8)', zIndex: 1000,
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
            <motion.div 
              initial={{ scale: 0.95, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 20 }}
              className="glass-card" style={{ padding: '32px', width: '540px', maxWidth: '90%' }}>
              <h2 style={{ marginBottom: '24px' }}>Bot Configuration</h2>

              {/* Exchange Selector */}
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', marginBottom: '12px', color: 'var(--text-muted)' }}>Exchange</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  {['BINANCE', 'MEXC'].map((ex) => (
                    <motion.div
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      key={ex}
                      onClick={() => setConfigExchange(ex)}
                      style={{
                        padding: '14px 10px',
                        borderRadius: '10px',
                        cursor: 'pointer',
                        textAlign: 'center',
                        transition: 'all 0.2s',
                        border: configExchange === ex ? '2px solid var(--primary)' : '1px solid var(--border-color)',
                        background: configExchange === ex ? 'var(--bg-gradient-1)' : 'var(--bg-card)',
                        fontWeight: 700,
                        fontSize: '1.05rem',
                        color: 'var(--text-main)'
                      }}
                    >
                      {ex}
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Trading Mode Selector */}
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', marginBottom: '12px', color: 'var(--text-muted)' }}>Trading Mode</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                  {[
                    { key: 'scalping', label: 'Scalping', timeframe: '15m', strategy: 'RSI / Bollinger', desc: 'Ani sıçramaları yakala', interval: '30' },
                    { key: 'swing',    label: 'Swing Trading', timeframe: '4h',  strategy: 'MACD Cross',     desc: 'Orta vadeli trendler',    interval: '120' },
                    { key: 'hodl',     label: 'Hodl',          timeframe: '1d',  strategy: 'EMA Golden Cross', desc: 'Uzun vadeli pozisyonlar', interval: '3600' },
                  ].map((m) => (
                    <motion.div
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      key={m.key}
                      onClick={() => { setConfigMode(m.key); setConfigInterval(m.interval); }}
                      style={{
                        padding: '14px 10px',
                        borderRadius: '10px',
                        cursor: 'pointer',
                        textAlign: 'center',
                        transition: 'all 0.2s',
                        border: configMode === m.key ? '2px solid var(--primary)' : '1px solid var(--border-color)',
                        background: configMode === m.key ? 'var(--bg-gradient-1)' : 'var(--bg-card)',
                      }}
                    >
                      <div style={{ fontWeight: 700, marginBottom: '4px', fontSize: '0.95rem', color: 'var(--text-main)' }}>{m.label}</div>
                      <div style={{ color: 'var(--primary)', fontSize: '0.75rem', marginBottom: '2px' }}>{m.timeframe} · {m.strategy}</div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>{m.desc}</div>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Risk Management Selector */}
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', marginBottom: '12px', color: 'var(--text-muted)' }}>Risk Level (0-100)</label>
                <input 
                  type="range" 
                  min="0" 
                  max="100" 
                  value={configRiskLevel} 
                  onChange={(e) => setConfigRiskLevel(parseInt(e.target.value, 10))}
                  style={{ width: '100%', marginBottom: '8px', cursor: 'pointer' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  <span>0 (Güvenli)</span>
                  <span>50 (Dengeli)</span>
                  <span>100 (Degen/Riskli)</span>
                </div>
                <div style={{ textAlign: 'center', marginTop: '8px', fontWeight: 'bold', color: 'var(--primary)' }}>
                  Current: {configRiskLevel}
                </div>
              </div>

              {/* Symbol Source Selector */}
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', marginBottom: '12px', color: 'var(--text-muted)' }}>Symbol Source</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  {[
                    { key: 'manual', label: 'Manual List', desc: 'Select coins manually' },
                    { key: 'auto', label: '🤖 Auto-Scanner', desc: 'Hunt Top Gainers live' },
                  ].map((src) => (
                    <motion.div
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      key={src.key}
                      onClick={() => setConfigSymbolSource(src.key)}
                      style={{
                        padding: '14px 10px',
                        borderRadius: '10px',
                        cursor: 'pointer',
                        textAlign: 'center',
                        transition: 'all 0.2s',
                        border: configSymbolSource === src.key ? '2px solid var(--primary)' : '1px solid var(--border-color)',
                        background: configSymbolSource === src.key ? 'var(--bg-gradient-1)' : 'var(--bg-card)',
                      }}
                    >
                      <div style={{ fontWeight: 700, marginBottom: '4px', fontSize: '1rem', color: 'var(--text-main)' }}>{src.label}</div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{src.desc}</div>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Trading Pairs */}
              {configSymbolSource === 'manual' && (
                <>
              <div style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <label style={{ color: 'var(--text-muted)', margin: 0 }}>Trading Pairs (comma separated)</label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button 
                      type="button"
                      onClick={() => setConfigSymbols('AUTO_GAINERS')}
                      style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--primary)', background: 'rgba(139,92,246,0.1)', color: 'var(--primary)', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}
                    >
                      + Auto Gainers
                    </button>
                    <button 
                      type="button"
                      onClick={() => setConfigSymbols('HIDDEN_GEMS')}
                      style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #3b82f6', background: 'rgba(59,130,246,0.1)', color: '#3b82f6', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}
                    >
                      + 💎 Hidden Gems (Uyuyanlar)
                    </button>
                  </div>
                </div>
                <textarea 
                  value={configSymbols}
                  onChange={(e) => setConfigSymbols(e.target.value)}
                  className="form-input"
                  style={{ minHeight: '80px' }}
                />
              </div>

              {/* Favorite Coins */}
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Favorite Coins</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                  {favoriteCoins.map(coin => {
                    const isSelected = isCoinSelected(coin);
                    return (
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        key={coin}
                        onClick={() => toggleFavoriteSelection(coin)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: '6px',
                          border: isSelected ? '1px solid var(--primary)' : '1px solid var(--border-color)',
                          background: isSelected ? 'var(--primary)' : 'var(--bg-card)',
                          color: isSelected ? 'white' : 'var(--text-main)',
                          cursor: 'pointer',
                          fontSize: '0.85rem',
                          transition: 'all 0.2s'
                        }}
                      >
                        {coin}
                      </motion.button>
                    );
                  })}
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input 
                    type="text" 
                    value={newFavorite} 
                    onChange={(e) => setNewFavorite(e.target.value)}
                    placeholder="Add coin (e.g. ADAUSDT)"
                    className="form-input"
                  />
                  <button 
                    onClick={handleAddFavorite}
                    className="btn-secondary"
                    style={{ whiteSpace: 'nowrap' }}
                  >
                    Add
                  </button>
                </div>
              </div>
              </>
              )}
              
              <div style={{ marginBottom: '32px' }}>
                {configMode === 'scalping' ? (
                  <div style={{
                    display: 'flex', alignItems: 'flex-start', gap: '12px',
                    padding: '16px', borderRadius: '12px',
                    background: 'var(--bg-card)',
                    border: '1px solid var(--primary)',
                  }}>
                    <Activity size={20} style={{ color: 'var(--primary)', marginTop: '2px', flexShrink: 0 }} />
                    <div style={{ fontSize: '0.9rem', lineHeight: '1.4', color: 'var(--text-muted)' }}>
                      <strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '4px' }}>HFT Scalping Mode is Event-Driven</strong>
                      It listens to live WebSocket streams for Volume Spikes. No interval required.
                    </div>
                  </div>
                ) : (
                  <>
                    <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Analysis Interval (Seconds)</label>
                    <input 
                      type="number"
                      value={configInterval}
                      onChange={(e) => setConfigInterval(e.target.value)}
                      className="form-input"
                    />
                  </>
                )}
              </div>
              
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button className="btn-secondary" onClick={() => setShowConfigModal(false)}>Cancel</button>
                <button className="btn-primary" onClick={handleStartBot} disabled={loading}>
                  {loading ? 'Starting...' : 'Start Trading'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {bots.length === 0 ? (
        <div className="glass-card" style={{ padding: '24px', marginBottom: '32px', borderLeft: '4px solid var(--text-muted)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ marginBottom: '8px' }}>Auto Trading Bot Status</h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)' }}>
                <XCircle size={18} />
                <span style={{ fontWeight: 500 }}>Offline (No active bots)</span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        bots.map((bot: any) => {
          const isRunning = bot.status === 'RUNNING';
          const currentEditingStr = editingSymbols[bot.bot_id] !== undefined ? editingSymbols[bot.bot_id] : bot.symbols?.join(', ') || '';
          const hasSymbolsChanged = normalizeSymbols(currentEditingStr) !== normalizeSymbols(bot.symbols || []);
          const currentRisk = editingRiskLevels[bot.bot_id] !== undefined ? editingRiskLevels[bot.bot_id] : (bot.risk_level ?? 50);

          return (
            <div key={bot.bot_id} className="glass-card" style={{ padding: '24px', marginBottom: '32px', borderLeft: isRunning ? '4px solid var(--success)' : '4px solid var(--text-muted)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ marginBottom: '8px' }}>Bot: {bot.bot_id}</h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: isRunning ? 'var(--success)' : 'var(--text-muted)' }}>
                    {isRunning ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
                    <span style={{ fontWeight: 500 }}>{isRunning ? 'Online & Running' : bot.status}</span>
                  </div>
                </div>
                {isRunning && (
                  <div style={{ display: 'flex', gap: '32px', alignItems: 'flex-end' }}>
                    {bot.mode && (
                      <div style={{ textAlign: 'right' }}>
                        <div className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '4px' }}>Configuration</div>
                        <div style={{ fontWeight: 600, color: 'var(--primary)' }}>
                          Mode: {bot.mode.toUpperCase()} (Risk: {bot.risk_level ?? 50}) | Exchange: {bot.exchange || 'BINANCE'}
                        </div>
                      </div>
                    )}
                    {bot.next_run_time && (
                      <div style={{ textAlign: 'right' }}>
                        {bot.mode === 'scalping' ? (
                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                            <div className="text-primary" style={{ fontSize: '0.85rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--primary)' }}>
                              <Activity size={14} /> WebSocket Radar Active
                            </div>
                            <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <motion.div
                                animate={{ scale: [1, 1.5, 1], opacity: [0.8, 0, 0.8] }}
                                transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                                style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--primary)', boxShadow: '0 0 10px var(--primary)' }}
                              />
                              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Listening for Volume Spikes...</span>
                            </div>
                          </div>
                        ) : (
                          <>
                            <div className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '4px' }}>Next Analysis In</div>
                            <div style={{ fontWeight: 600 }}>{new Date(bot.next_run_time).toLocaleTimeString()}</div>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              {isRunning && (
                <div style={{ marginTop: '24px', paddingTop: '24px', borderTop: '1px solid var(--border-color)' }}>
                  <div style={{ marginBottom: '24px' }}>
                    <label style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', color: 'var(--text-muted)' }}>
                      <span>Live Risk Level</span>
                      <span style={{ fontWeight: 'bold', color: 'var(--primary)' }}>{currentRisk}</span>
                    </label>
                    <input 
                      type="range" 
                      min="0" 
                      max="100" 
                      value={currentRisk}
                      onChange={(e) => setEditingRiskLevels({ ...editingRiskLevels, [bot.bot_id]: parseInt(e.target.value, 10) })}
                      onMouseUp={(e) => handleRiskChange(bot.bot_id, parseInt((e.target as HTMLInputElement).value, 10))}
                      onTouchEnd={(e) => handleRiskChange(bot.bot_id, parseInt((e.target as HTMLInputElement).value, 10))}
                      style={{ width: '100%', cursor: 'pointer' }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '8px' }}>
                      <span>0 (Güvenli)</span>
                      <span>50 (Dengeli)</span>
                      <span>100 (Degen/Riskli)</span>
                    </div>
                  </div>

                  {!bot.symbols?.includes('AUTO_GAINERS') && (
                    <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Trading Pairs (comma separated)</label>
                  )}
                  <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
                    {bot.symbols?.includes('AUTO_GAINERS') ? (
                      <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '12px', padding: '16px', background: 'rgba(139,92,246,0.1)', border: '1px solid var(--primary)', borderRadius: '8px' }}>
                        <Activity size={24} color="var(--primary)" />
                        <div>
                          <div style={{ fontWeight: 600, color: 'var(--primary)', fontSize: '1.05rem', marginBottom: '4px' }}>🤖 Auto-Scanner Active</div>
                          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Dynamically hunting top gainers and high-volume pump coins every cycle.</div>
                        </div>
                      </div>
                    ) : (
                      <textarea 
                        value={currentEditingStr}
                        onChange={(e) => setEditingSymbols({ ...editingSymbols, [bot.bot_id]: e.target.value })}
                        className="form-input"
                        style={{ flex: 1, minHeight: '80px' }}
                      />
                    )}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {!bot.symbols?.includes('AUTO_GAINERS') && hasSymbolsChanged && (
                        <button 
                          onClick={() => handleUpdateSymbols(bot.bot_id)} 
                          disabled={loading} 
                          style={{ 
                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                            padding: '12px 16px', borderRadius: '8px', fontWeight: 600,
                            background: 'var(--primary)',
                            color: 'white', border: 'none', cursor: 'pointer', transition: 'all 0.2s'
                          }}>
                          <RefreshCw className={loading ? "animate-spin" : ""} size={16} />
                          Update
                        </button>
                      )}
                      <button 
                        onClick={() => handleStopBot(bot.bot_id)} 
                        disabled={loading} 
                        style={{ 
                          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                          padding: '12px 16px', borderRadius: '8px', fontWeight: 600,
                          background: 'var(--danger)',
                          color: 'white', border: 'none', cursor: 'pointer', transition: 'all 0.2s'
                        }}>
                        <Square size={16} />
                        Stop Bot
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })
      )}

      <div className="grid-cols-3" style={{ marginBottom: '32px' }}>
        <div className="glass-card" style={{ padding: '24px' }}>
          <h3 className="text-muted" style={{ marginBottom: '8px', fontSize: '0.9rem' }}>Equity</h3>
          <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>
            ${account ? parseFloat(account.equity).toFixed(2) : '0.00'}
          </div>
        </div>
        <div className="glass-card" style={{ padding: '24px' }}>
          <h3 className="text-muted" style={{ marginBottom: '8px', fontSize: '0.9rem' }}>Cash Balance</h3>
          <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>
            ${account ? parseFloat(account.cash_balance).toFixed(2) : '0.00'}
          </div>
        </div>
        <div className="glass-card" style={{ padding: '24px' }}>
          <h3 className="text-muted" style={{ marginBottom: '8px', fontSize: '0.9rem' }}>Active Positions</h3>
          <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>
            {account && account.open_positions ? account.open_positions.length : 0}
          </div>
        </div>
      </div>

      {actionLog && (
        <div className="glass-card animate-fade-in" style={{ padding: '24px', marginBottom: '32px', borderLeft: actionLog.status === 'REJECTED' ? '4px solid var(--danger)' : '4px solid var(--success)' }}>
          <h3 style={{ marginBottom: '16px' }}>Last Cycle Result: {actionLog.status}</h3>
          {actionLog.status === 'REJECTED' ? (
            <p className="text-danger">{actionLog.reason}</p>
          ) : (
            <div className="text-success" style={{ display: 'flex', gap: '24px' }}>
              <div><strong>Symbols Processed:</strong> {actionLog.symbols_processed}</div>
              <div><strong>Decisions Made:</strong> {actionLog.decisions_made}</div>
              <div><strong>Trades Executed:</strong> {actionLog.trades_executed}</div>
            </div>
          )}
        </div>
      )}

      <div className="glass-card" style={{ padding: '24px' }}>
        <h3 style={{ marginBottom: '24px' }}>Open Positions</h3>
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
              account.open_positions.map((pos: any, i: number) => (
                <tr key={i}>
                  <td>{pos.symbol}</td>
                  <td>
                    <span className={`badge ${pos.side === 'LONG' ? 'badge-success' : 'badge-danger'}`}>
                      {pos.side}
                    </span>
                  </td>
                  <td>{parseFloat(pos.quantity).toFixed(4)}</td>
                  <td>${parseFloat(pos.entry_price).toFixed(2)}</td>
                  <td className={parseFloat(pos.unrealized_pnl) >= 0 ? 'text-success' : 'text-danger'}>
                    ${parseFloat(pos.unrealized_pnl).toFixed(2)}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                  No open positions.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <LiveConsole />
    </div>
  );
};

export default PaperTrading;
