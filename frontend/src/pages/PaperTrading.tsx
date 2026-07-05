import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { PlayCircle, RefreshCw, Square, CheckCircle2, XCircle } from 'lucide-react';
import LiveConsole from '../components/LiveConsole';

const PaperTrading: React.FC = () => {
  const [account, setAccount] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [actionLog, setActionLog] = useState<any>(null);
  const [botStatus, setBotStatus] = useState<any>(null);
  const [editingSymbols, setEditingSymbols] = useState<Record<string, string>>({});
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [configSymbols, setConfigSymbols] = useState(() => typeof window !== 'undefined' && localStorage.getItem('configSymbols') ? localStorage.getItem('configSymbols')! : 'BTCUSDT, ETHUSDT, SOLUSDT');
  const [configInterval, setConfigInterval] = useState(() => typeof window !== 'undefined' && localStorage.getItem('configInterval') ? localStorage.getItem('configInterval')! : '120');
  const [configMode, setConfigMode] = useState(() => typeof window !== 'undefined' && localStorage.getItem('configMode') ? localStorage.getItem('configMode')! : 'swing');
  const [configExchange, setConfigExchange] = useState(() => typeof window !== 'undefined' && localStorage.getItem('configExchange') ? localStorage.getItem('configExchange')! : 'BINANCE');

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
      const symbolsList = configSymbols.split(',').map(s => s.trim().toUpperCase()).filter(s => s);
      const bot_id = `bot-${Date.now()}`;
      const res = await axios.post('/api/v1/bot/start', { 
        bot_id: bot_id,
        interval_seconds: parseInt(configInterval, 10),
        symbols: symbolsList,
        mode: configMode,
        exchange: configExchange
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
      const res = await axios.post('/api/v1/cycle/run', {
        account_name: 'default-paper',
        exchange: 'BINANCE',
        symbols: ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT'],
        timeframe: '4h',
        strategy_name: 'macd_cross',
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

      {showConfigModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
          background: 'rgba(0,0,0,0.8)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <div className="glass-card" style={{ padding: '32px', width: '540px', maxWidth: '90%' }}>
            <h2 style={{ marginBottom: '24px' }}>Bot Configuration</h2>

            {/* Exchange Selector */}
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '12px', color: 'var(--text-muted)' }}>Exchange</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                {['BINANCE', 'MEXC'].map((ex) => (
                  <div
                    key={ex}
                    onClick={() => setConfigExchange(ex)}
                    style={{
                      padding: '14px 10px',
                      borderRadius: '10px',
                      cursor: 'pointer',
                      textAlign: 'center',
                      transition: 'all 0.2s',
                      border: configExchange === ex ? '2px solid var(--primary)' : '1px solid rgba(255,255,255,0.1)',
                      background: configExchange === ex ? 'rgba(139,92,246,0.15)' : 'rgba(255,255,255,0.03)',
                      fontWeight: 700,
                      fontSize: '1.05rem'
                    }}
                  >
                    {ex}
                  </div>
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
                  <div
                    key={m.key}
                    onClick={() => { setConfigMode(m.key); setConfigInterval(m.interval); }}
                    style={{
                      padding: '14px 10px',
                      borderRadius: '10px',
                      cursor: 'pointer',
                      textAlign: 'center',
                      transition: 'all 0.2s',
                      border: configMode === m.key ? '2px solid var(--primary)' : '1px solid rgba(255,255,255,0.1)',
                      background: configMode === m.key ? 'rgba(139,92,246,0.15)' : 'rgba(255,255,255,0.03)',
                    }}
                  >
                    <div style={{ fontWeight: 700, marginBottom: '4px', fontSize: '0.95rem' }}>{m.label}</div>
                    <div style={{ color: 'var(--primary)', fontSize: '0.75rem', marginBottom: '2px' }}>{m.timeframe} · {m.strategy}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>{m.desc}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Trading Pairs */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Trading Pairs (comma separated)</label>
              <textarea 
                value={configSymbols}
                onChange={(e) => setConfigSymbols(e.target.value)}
                style={{ width: '100%', padding: '12px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '8px', minHeight: '80px', boxSizing: 'border-box' }}
              />
            </div>

            {/* Favorite Coins */}
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Favorite Coins</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                {favoriteCoins.map(coin => {
                  const isSelected = isCoinSelected(coin);
                  return (
                    <button
                      key={coin}
                      onClick={() => toggleFavoriteSelection(coin)}
                      style={{
                        padding: '6px 12px',
                        borderRadius: '6px',
                        border: isSelected ? '1px solid var(--primary)' : '1px solid rgba(255,255,255,0.1)',
                        background: isSelected ? 'var(--primary)' : 'rgba(255,255,255,0.05)',
                        color: 'white',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                        transition: 'all 0.2s'
                      }}
                    >
                      {coin}
                    </button>
                  );
                })}
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input 
                  type="text" 
                  value={newFavorite} 
                  onChange={(e) => setNewFavorite(e.target.value)}
                  placeholder="Add coin (e.g. ADAUSDT)"
                  style={{ padding: '8px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.05)', color: 'white', flex: 1, boxSizing: 'border-box' }}
                />
                <button 
                  onClick={handleAddFavorite}
                  style={{ padding: '8px 16px', borderRadius: '6px', background: 'rgba(255,255,255,0.1)', color: 'white', border: 'none', cursor: 'pointer', transition: 'all 0.2s' }}
                >
                  Add to Favorites
                </button>
              </div>
            </div>
            
            <div style={{ marginBottom: '32px' }}>
              <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Analysis Interval (Seconds)</label>
              <input 
                type="number"
                value={configInterval}
                onChange={(e) => setConfigInterval(e.target.value)}
                style={{ width: '100%', padding: '12px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '8px', boxSizing: 'border-box' }}
              />
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button className="btn-secondary" onClick={() => setShowConfigModal(false)}>Cancel</button>
              <button 
                onClick={handleStartBot} 
                style={{ padding: '10px 24px', borderRadius: '8px', background: 'var(--primary)', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 600 }}
              >
                Start Trading
              </button>
            </div>
          </div>
        </div>
      )}

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
                          Mode: {bot.mode.toUpperCase()} | Exchange: {bot.exchange || 'BINANCE'}
                        </div>
                      </div>
                    )}
                    {bot.next_run_time && (
                      <div style={{ textAlign: 'right' }}>
                        <div className="text-muted" style={{ fontSize: '0.9rem', marginBottom: '4px' }}>Next Analysis In</div>
                        <div style={{ fontWeight: 600 }}>{new Date(bot.next_run_time).toLocaleTimeString()}</div>
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              {isRunning && (
                <div style={{ marginTop: '24px', paddingTop: '24px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                  <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Trading Pairs (comma separated)</label>
                  <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
                    <textarea 
                      value={currentEditingStr}
                      onChange={(e) => setEditingSymbols({ ...editingSymbols, [bot.bot_id]: e.target.value })}
                      style={{ flex: 1, padding: '12px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '8px', minHeight: '80px', boxSizing: 'border-box' }}
                    />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {hasSymbolsChanged && (
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
