import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Play, Terminal as TerminalIcon, CheckCircle, XCircle, Activity, History } from 'lucide-react';
import { motion } from 'framer-motion';
import { BacktestHistory } from './BacktestHistory';

const STAGE_META: Record<string, { color: string; label: string }> = {
  INIT:       { color: 'var(--accent)', label: 'Init'       },
  STRATEGY:   { color: '#a78bfa', label: 'Strategy'   },
  PORTFOLIO:  { color: 'var(--success)', label: 'Portfolio'  },
  RISK:       { color: 'var(--warning)', label: 'Risk'       },
  EXECUTION:  { color: '#f472b6', label: 'Execution'  },
  PAPER_BROKER:{color: '#f472b6', label: 'Broker'     },
  TRAILING_SL:{ color: '#fb923c', label: 'Trail SL'   },
  COMPLETED:  { color: 'var(--success)', label: 'Completed'  },
  FAILED:     { color: 'var(--danger)', label: 'Failed'     },
  MARKET_DATA:{ color: 'var(--text-muted)', label: 'Market'     },
};

const LEVEL_COLOR: Record<string, string> = {
  INFO:    'var(--text-muted)',
  SUCCESS: 'var(--success)',
  WARN:    'var(--warning)',
  WARNING: 'var(--warning)',
  ERROR:   'var(--danger)',
};

function formatTime(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString('tr-TR', { hour12: false });
  } catch (e) {
    return iso;
  }
}

const Backtesting: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [jobs, setJobs] = useState<any[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'run' | 'history'>('run');
  
  const [exchange, setExchange] = useState(() => localStorage.getItem('bt_exchange') || "BINANCE");
  const [configMode, setConfigMode] = useState<'scalping' | 'swing' | 'hodl'>(() => (localStorage.getItem('bt_configMode') as any) || 'swing');
  const [symbolSource, setSymbolSource] = useState<'manual' | 'auto'>(() => (localStorage.getItem('bt_symbolSource') as any) || 'manual');
  const [manualSymbols, setManualSymbols] = useState(() => localStorage.getItem('bt_manualSymbols') || "BTCUSDT, ETHUSDT");
  const [autoScroll, setAutoScroll] = useState(false);
  const [startDate, setStartDate] = useState(() => localStorage.getItem('bt_startDate') || new Date(Date.now() - 3 * 86400000).toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(() => localStorage.getItem('bt_endDate') || new Date().toISOString().split('T')[0]);
  const [initialBalance, setInitialBalance] = useState(() => parseInt(localStorage.getItem('bt_initialBalance') || "10000", 10));
  const [riskLevel, setRiskLevel] = useState(() => parseInt(localStorage.getItem('bt_riskLevel') || "100", 10));
  const [useBtcShield, setUseBtcShield] = useState(() => localStorage.getItem('bt_useBtcShield') !== 'false');
  const [useHtfShield, setUseHtfShield] = useState(() => localStorage.getItem('bt_useHtfShield') !== 'false');
  const [useRegimeShield, setUseRegimeShield] = useState(() => localStorage.getItem('bt_useRegimeShield') !== 'false');

  useEffect(() => {
    localStorage.setItem('bt_exchange', exchange);
    localStorage.setItem('bt_configMode', configMode);
    localStorage.setItem('bt_symbolSource', symbolSource);
    localStorage.setItem('bt_manualSymbols', manualSymbols);
    localStorage.setItem('bt_startDate', startDate);
    localStorage.setItem('bt_endDate', endDate);
    localStorage.setItem('bt_initialBalance', initialBalance.toString());
    localStorage.setItem('bt_riskLevel', riskLevel.toString());
    localStorage.setItem('bt_useBtcShield', useBtcShield.toString());
    localStorage.setItem('bt_useHtfShield', useHtfShield.toString());
    localStorage.setItem('bt_useRegimeShield', useRegimeShield.toString());
  }, [exchange, configMode, symbolSource, manualSymbols, startDate, endDate, initialBalance, riskLevel, useBtcShield, useHtfShield, useRegimeShield]);

  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await axios.get('/api/v1/backtest');
        setJobs(res.data);
      } catch (e) {
        console.error(e);
      }
    };
    fetchJobs();
    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!selectedJobId) {
      const runningJobs = jobs.filter(j => j.status === 'RUNNING');
      if (runningJobs.length === 1) {
        setSelectedJobId(runningJobs[0].job_id);
      } else if (jobs.length > 0) {
        setSelectedJobId(jobs[0].job_id);
      }
    }
  }, [jobs, selectedJobId]);

  useEffect(() => {
    if (!selectedJobId) return;

    const fetchLogs = async () => {
      try {
        const res = await axios.get(`/api/v1/logs/recent?account_name=backtest-${selectedJobId}&limit=100`);
        setLogs(res.data);
      } catch (e) {
        console.error(e);
      }
    };
    
    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, [selectedJobId]);

  useEffect(() => {
    if (autoScroll) {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [logs, autoScroll]);

  const handleRunBacktest = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const symbolsList = symbolSource === 'auto' 
        ? ['AUTO_GAINERS'] 
        : manualSymbols.split(',').map(s => s.trim().toUpperCase()).filter(s => s);
        
      const payload = {
        exchange,
        symbols: symbolsList,
        timeframe: configMode === 'scalping' ? '15m' : (configMode === 'swing' ? '4h' : '1d'),
        strategy_name: configMode === 'scalping' ? 'hft_momentum' : (configMode === 'swing' ? 'macd_cross' : 'ema_golden_cross'),
        start_time: new Date(startDate).toISOString(),
        end_time: new Date(endDate).toISOString(),
        initial_balance: Number(initialBalance),
        risk_level: riskLevel,
        use_btc_shield: useBtcShield,
        use_htf_shield: useHtfShield,
        use_regime_shield: useRegimeShield,
      };

      const res = await axios.post('/api/v1/backtest/run', payload);
      setSelectedJobId(res.data.job_id);
      setLogs([]); 
      
      const jobsRes = await axios.get('/api/v1/backtest');
      setJobs(jobsRes.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelJob = async (jobId: string) => {
    try {
      await axios.post(`/api/v1/backtest/${jobId}/cancel`);
      const res = await axios.get('/api/v1/backtest');
      setJobs(res.data);
    } catch(e) {
      console.error(e);
    }
  };

  const handleClearAll = async () => {
    if(!window.confirm("Çalışan testler iptal edilecek ve ekran temizlenecek. Geçmiş kayıtlar silinmeyecektir. Onaylıyor musunuz?")) return;
    try {
      const runningJobs = jobs.filter(j => j.status === 'RUNNING' || j.status === 'PENDING');
      for (const job of runningJobs) {
        await axios.post(`/api/v1/backtest/${job.job_id}/cancel`);
      }
      setSelectedJobId(null);
      setLogs([]);
      const res = await axios.get('/api/v1/backtest');
      setJobs(res.data);
    } catch(e) {
      console.error(e);
    }
  };

  const selectedJob = jobs.find(j => j.job_id === selectedJobId);

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '2rem', marginBottom: '8px', color: 'var(--text-primary)' }}>Backtesting Engine</h1>
          <p className="text-muted">Simulate your strategies against historical data.</p>
        </div>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <div style={{ display: 'flex', background: 'var(--bg-surface)', padding: '4px', borderRadius: '8px', border: '1px solid var(--border)' }}>
            <button 
              className={activeTab === 'run' ? 'btn-primary' : 'btn-ghost'}
              style={{ border: 'none' }}
              onClick={() => setActiveTab('run')}
            >
              Run Test
            </button>
            <button 
              className={activeTab === 'history' ? 'btn-primary' : 'btn-ghost'}
              style={{ border: 'none', display: 'flex', alignItems: 'center', gap: '8px' }}
              onClick={() => setActiveTab('history')}
            >
              <History size={16} /> History
            </button>
          </div>
          <button onClick={handleClearAll} className="btn-danger" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <XCircle size={16} /> Clear All
          </button>
        </div>
      </div>

      {activeTab === 'history' ? (
        <BacktestHistory />
      ) : (
      <div className="grid-cols-3" style={{ alignItems: 'start', gap: '24px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', gridColumn: 'span 1' }}>
          <motion.div className="card" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h3 style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
              <Play size={18} /> New Backtest
            </h3>
            <form onSubmit={handleRunBacktest} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label className="section-label">Exchange</label>
                <select className="form-input" value={exchange} onChange={(e) => setExchange(e.target.value)}>
                  <option value="BINANCE">Binance</option>
                  <option value="MEXC">MEXC</option>
                </select>
              </div>
              <div>
                <label className="section-label">Trading Mode</label>
                <select className="form-input" value={configMode} onChange={(e) => setConfigMode(e.target.value as any)}>
                  <option value="scalping">Scalping (15m - Micro Pullback)</option>
                  <option value="swing">Swing Trading (4h - MACD Cross)</option>
                  <option value="hodl">Hodl (1d - EMA Golden Cross)</option>
                </select>
              </div>
              
              <div>
                <label className="section-label">Coin Source</label>
                <select className="form-input" value={symbolSource} onChange={(e) => setSymbolSource(e.target.value as any)}>
                  <option value="manual">Manual Entry</option>
                  <option value="auto">Auto-Scanner (Top Gainers)</option>
                </select>
              </div>

              {symbolSource === 'auto' && (
                <div style={{ fontSize: '0.8rem', color: 'var(--warning)', background: 'rgba(251, 191, 36, 0.1)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(251, 191, 36, 0.3)' }}>
                  ⚠️ Uyarı: Auto-Scanner, geçmiş tarihteki değil BUGÜNÜN en çok yükselen coinlerini çeker. Geçmiş tarihlerde backtest yaparken bugünün yükselenlerini kullanmak "Look-Ahead Bias" yaratır ve yanıltıcı kârlar gösterebilir.
                </div>
              )}

              {symbolSource === 'manual' && (
                <div>
                  <label className="section-label">Symbols (comma separated)</label>
                  <input type="text" className="form-input" value={manualSymbols} onChange={(e) => setManualSymbols(e.target.value)} placeholder="BTCUSDT, ETHUSDT" required />
                </div>
              )}
              <div className="grid-cols-2" style={{ gap: '16px' }}>
                <div>
                  <label className="section-label">Start Date</label>
                  <input type="date" className="form-input" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
                </div>
                <div>
                  <label className="section-label">End Date</label>
                  <input type="date" className="form-input" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
                </div>
              </div>
              <div>
                <label className="section-label">Initial Balance ($)</label>
                <input type="number" className="form-input" value={initialBalance} onChange={(e) => setInitialBalance(Number(e.target.value))} required />
              </div>

              <div>
                <label className="section-label">Risk Level (0-200)</label>
                <input 
                  type="range" 
                  min="0" 
                  max="200" 
                  value={riskLevel} 
                  onChange={(e) => setRiskLevel(parseInt(e.target.value, 10))}
                  style={{ width: '100%', marginBottom: '8px', cursor: 'pointer', accentColor: 'var(--accent)' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                  <span>0 (Güvenli)</span>
                  <span>100 (Degen)</span>
                  <span>200 (Max Risk)</span>
                </div>
                <div style={{ textAlign: 'center', marginTop: '8px', fontWeight: 'bold', color: 'var(--accent)', fontSize: '0.9rem' }}>
                  Current: {riskLevel}
                </div>
              </div>

              <div style={{ background: 'var(--bg-surface)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                <label className="section-label" style={{ marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  🛡️ Risk Filters
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                    <input type="checkbox" checked={useBtcShield} onChange={(e) => setUseBtcShield(e.target.checked)} style={{ accentColor: 'var(--accent)' }} />
                    BTC Crash Shield <span className="text-muted">(Ani BTC çöküşlerinde durdurur)</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                    <input type="checkbox" checked={useHtfShield} onChange={(e) => setUseHtfShield(e.target.checked)} style={{ accentColor: 'var(--accent)' }} />
                    HTF Trend Shield <span className="text-muted">(Üst zaman dilimiyle uyumlu)</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                    <input type="checkbox" checked={useRegimeShield} onChange={(e) => setUseRegimeShield(e.target.checked)} style={{ accentColor: 'var(--accent)' }} />
                    Market Regime Shield <span className="text-muted">(Yüksek volatilite engeli)</span>
                  </label>
                </div>
              </div>
              <button type="submit" className="btn-primary" disabled={loading} style={{ marginTop: '8px', padding: '12px' }}>
                {loading ? 'Starting...' : 'Run Simulation'}
              </button>
            </form>
          </motion.div>

          <motion.div className="card" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
              <Activity size={18} /> Active / Recent
            </h3>
            {jobs.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', textAlign: 'center', padding: '16px' }}>
                No backtests found.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '300px', overflowY: 'auto', paddingRight: '4px' }}>
                {jobs.map(job => (
                  <div key={job.job_id} 
                       onClick={() => setSelectedJobId(job.job_id)}
                       style={{ 
                         padding: '12px', 
                         cursor: 'pointer', 
                         border: selectedJobId === job.job_id ? '1px solid var(--accent)' : '1px solid var(--border)', 
                         borderRadius: '8px', 
                         background: selectedJobId === job.job_id ? 'var(--bg-raised)' : 'var(--bg-surface)',
                         transition: 'all 0.2s'
                       }}>
                     <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                       <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>{job.strategy_name}</strong>
                       <span className={`badge-${job.status === 'COMPLETED' ? 'success' : job.status === 'FAILED' ? 'danger' : 'primary'}`} style={{ fontSize: '0.7rem' }}>
                         {job.status}
                       </span>
                     </div>
                     <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                       {job.symbols.join(', ')} • {new Date(job.start_time).toLocaleDateString()}
                     </div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </div>

        <motion.div className="card" style={{ gridColumn: 'span 2', display: 'flex', flexDirection: 'column', height: '100%' }} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
          <h3 style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
            <TerminalIcon size={18} /> Backtest Details & Logs
          </h3>
          
          {selectedJob ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', flex: 1 }}>
              
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', background: 'var(--bg-surface)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                <div style={{ flex: 1, minWidth: '120px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>Status</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {selectedJob.status === 'COMPLETED' ? <CheckCircle size={16} color="var(--success)" /> : selectedJob.status === 'FAILED' || selectedJob.status === 'CANCELLED' ? <XCircle size={16} color="var(--danger)" /> : <Activity size={16} color="var(--accent)" />}
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{selectedJob.status}</span>
                    </div>
                    {selectedJob.status === 'RUNNING' && (
                      <button onClick={() => handleCancelJob(selectedJob.job_id)} className="btn-danger" style={{ fontSize: '0.75rem', padding: '4px 8px' }}>
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
                
                {selectedJob.status === 'COMPLETED' && selectedJob.final_equity !== null && (
                  <>
                    <div style={{ flex: 1, minWidth: '120px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>Final Equity</div>
                      <div className="stat-value" style={{ color: 'var(--success)' }}>${selectedJob.final_equity.toFixed(2)}</div>
                    </div>
                    <div style={{ flex: 1, minWidth: '120px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>Cycle PnL</div>
                      <div className="stat-value" style={{ color: (selectedJob.final_equity - selectedJob.initial_balance) >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                        ${(selectedJob.final_equity - selectedJob.initial_balance).toFixed(2)}
                      </div>
                    </div>
                    <div style={{ flex: 1, minWidth: '120px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>Win Rate</div>
                      <div className="stat-value" style={{ color: 'var(--text-primary)' }}>{(selectedJob.win_rate * 100).toFixed(2)}%</div>
                    </div>
                    <div style={{ flex: 1, minWidth: '120px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>Max Drawdown</div>
                      <div className="stat-value" style={{ color: 'var(--danger)' }}>{(selectedJob.max_drawdown * 100).toFixed(2)}%</div>
                    </div>
                    <div style={{ flex: 1, minWidth: '120px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>Total Trades</div>
                      <div className="stat-value" style={{ color: 'var(--text-primary)' }}>{selectedJob.total_trades}</div>
                    </div>
                  </>
                )}
              </div>

              <div style={{ 
                flex: 1, 
                height: '500px',
                maxHeight: '500px',
                background: 'var(--bg-base)', 
                border: '1px solid var(--border-strong)', 
                borderRadius: '8px', 
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column'
              }}>
                <div style={{ background: 'var(--bg-surface)', padding: '12px 16px', fontSize: '0.8rem', color: 'var(--text-muted)', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="mono">Engine Output</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                      <input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} style={{ accentColor: 'var(--accent)' }} />
                      Auto-Scroll
                    </label>
                    <span className="mono">Job ID: {selectedJob.job_id.substring(0, 8)}...</span>
                  </div>
                </div>
                <div style={{ flex: 1, overflowY: 'auto', padding: '16px', fontFamily: '"Fira Code", monospace' }}>
                  {logs.length === 0 ? (
                    <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.85rem' }}>Waiting for logs...</div>
                  ) : (
                    logs.map(log => {
                      const meta = STAGE_META[log.stage] || { color: 'var(--text-muted)', label: log.stage };
                      const levelColor = LEVEL_COLOR[log.level?.toUpperCase()] || 'var(--text-muted)';
                      return (
                        <div key={log.id} style={{ display: 'flex', gap: '16px', fontSize: '0.85rem', marginBottom: '8px', lineHeight: 1.5 }}>
                          <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>[{formatTime(log.created_at)}]</span>
                          <span style={{ color: meta.color, width: '90px', flexShrink: 0, fontWeight: 600 }}>[{meta.label}]</span>
                          <span style={{ color: levelColor, width: '70px', flexShrink: 0 }}>[{log.level}]</span>
                          <span style={{ color: 'var(--text-primary)', wordBreak: 'break-word' }}>{log.message}</span>
                        </div>
                      );
                    })
                  )}
                  <div ref={logsEndRef} />
                </div>
              </div>

            </div>
          ) : (
            <div style={{ padding: '80px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <TerminalIcon size={64} opacity={0.2} style={{ margin: '0 auto 24px' }} />
              <p style={{ fontSize: '1.1rem' }}>Select a backtest from the list to view details and logs.</p>
            </div>
          )}
        </motion.div>
      </div>
      )}
    </motion.div>
  );
};

export default Backtesting;
