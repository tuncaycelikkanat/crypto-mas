import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Play, Terminal as TerminalIcon, CheckCircle, XCircle, Activity, History } from 'lucide-react';
import { BacktestHistory } from './BacktestHistory';

const STAGE_META: Record<string, { color: string; label: string }> = {
  INIT:       { color: '#60a5fa', label: 'Init'       },
  STRATEGY:   { color: '#a78bfa', label: 'Strategy'   },
  PORTFOLIO:  { color: '#34d399', label: 'Portfolio'  },
  RISK:       { color: '#fbbf24', label: 'Risk'       },
  EXECUTION:  { color: '#f472b6', label: 'Execution'  },
  PAPER_BROKER:{color: '#f472b6', label: 'Broker'     },
  TRAILING_SL:{ color: '#fb923c', label: 'Trail SL'   },
  COMPLETED:  { color: '#10b981', label: 'Completed'  },
  FAILED:     { color: '#ef4444', label: 'Failed'     },
  MARKET_DATA:{ color: '#94a3b8', label: 'Market'     },
};

const LEVEL_COLOR: Record<string, string> = {
  INFO:    '#94a3b8',
  SUCCESS: '#10b981',
  WARN:    '#fbbf24',
  WARNING: '#fbbf24',
  ERROR:   '#ef4444',
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
  
  const [exchange, setExchange] = useState("BINANCE");
  const [configMode, setConfigMode] = useState<'scalping' | 'swing' | 'hodl'>('swing');
  const [symbolSource, setSymbolSource] = useState<'manual' | 'auto'>('manual');
  const [manualSymbols, setManualSymbols] = useState("BTCUSDT, ETHUSDT");
  const [autoScroll, setAutoScroll] = useState(false);
  const [startDate, setStartDate] = useState(new Date(Date.now() - 3 * 86400000).toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [initialBalance, setInitialBalance] = useState(10000);
  const [riskLevel, setRiskLevel] = useState(100);
  const [useBtcShield, setUseBtcShield] = useState(true);
  const [useHtfShield, setUseHtfShield] = useState(true);
  const [useRegimeShield, setUseRegimeShield] = useState(true);

  const logsEndRef = useRef<HTMLDivElement>(null);

  // Fetch Jobs every 3 seconds
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

  // Auto-select job if there's only 1 running job and none is selected
  useEffect(() => {
    if (!selectedJobId) {
      const runningJobs = jobs.filter(j => j.status === 'RUNNING');
      if (runningJobs.length === 1) {
        setSelectedJobId(runningJobs[0].job_id);
      } else if (jobs.length > 0) {
        setSelectedJobId(jobs[0].job_id); // default to first
      }
    }
  }, [jobs, selectedJobId]);

  // Poll Logs for selectedJobId every 2 seconds
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
        timeframe: configMode === 'scalping' ? '1m' : (configMode === 'swing' ? '4h' : '1d'),
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
      setLogs([]); // clear logs for new job
      
      // Fetch jobs immediately to show the new one
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
      // Find running jobs and cancel them
      const runningJobs = jobs.filter(j => j.status === 'RUNNING' || j.status === 'PENDING');
      for (const job of runningJobs) {
        await axios.post(`/api/v1/backtest/${job.job_id}/cancel`);
      }
      
      // Clear screen states
      setSelectedJobId(null);
      setLogs([]);
      
      // Refresh jobs
      const res = await axios.get('/api/v1/backtest');
      setJobs(res.data);
    } catch(e) {
      console.error(e);
    }
  };

  const selectedJob = jobs.find(j => j.job_id === selectedJobId);

  return (
    <div>
      <div className="flex-between" style={{ marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>Backtesting Engine</h1>
          <p className="text-muted">Simulate your strategies against historical data.</p>
        </div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <div style={{ display: 'flex', background: 'rgba(0,0,0,0.2)', padding: '4px', borderRadius: '8px' }}>
            <button 
              className={`btn ${activeTab === 'run' ? 'primary' : ''}`}
              style={{ background: activeTab === 'run' ? 'var(--primary)' : 'transparent', color: activeTab === 'run' ? '#fff' : '#94a3b8', border: 'none', boxShadow: 'none' }}
              onClick={() => setActiveTab('run')}
            >
              Run Test
            </button>
            <button 
              className={`btn ${activeTab === 'history' ? 'primary' : ''}`}
              style={{ background: activeTab === 'history' ? 'var(--primary)' : 'transparent', color: activeTab === 'history' ? '#fff' : '#94a3b8', border: 'none', boxShadow: 'none', display: 'flex', alignItems: 'center', gap: '8px' }}
              onClick={() => setActiveTab('history')}
            >
              <History size={16} /> History & Compare
            </button>
          </div>
          <button onClick={handleClearAll} className="btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '8px', border: '1px solid var(--danger)', color: 'var(--danger)' }}>
            <XCircle size={16} /> Tümünü Temizle
          </button>
        </div>
      </div>

      {activeTab === 'history' ? (
        <BacktestHistory />
      ) : (

      <div className="grid-cols-3" style={{ alignItems: 'start' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', gridColumn: 'span 1' }}>
          <div className="glass-card" style={{ padding: '24px' }}>
            <h3 style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Play size={18} /> New Backtest
            </h3>
            <form onSubmit={handleRunBacktest} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Exchange</label>
                <select className="form-input" value={exchange} onChange={(e) => setExchange(e.target.value)}>
                  <option value="BINANCE">Binance</option>
                  <option value="MEXC">MEXC</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Trading Mode</label>
                <select className="form-input" value={configMode} onChange={(e) => setConfigMode(e.target.value as any)}>
                  <option value="scalping">Scalping (1m - HFT Momentum)</option>
                  <option value="swing">Swing Trading (4h - MACD Cross)</option>
                  <option value="hodl">Hodl (1d - EMA Golden Cross)</option>
                </select>
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Coin Source</label>
                <select className="form-input" value={symbolSource} onChange={(e) => setSymbolSource(e.target.value as any)}>
                  <option value="manual">Manual Entry</option>
                  <option value="auto">Auto-Scanner (Top Gainers)</option>
                </select>
              </div>

              {symbolSource === 'auto' && (
                <div style={{ fontSize: '0.75rem', color: 'var(--warning)', background: 'rgba(251, 191, 36, 0.1)', padding: '8px', borderRadius: '4px', border: '1px solid rgba(251, 191, 36, 0.3)' }}>
                  ⚠️ Uyarı: Auto-Scanner, geçmiş tarihteki değil BUGÜNÜN en çok yükselen coinlerini çeker. Geçmiş tarihlerde backtest yaparken bugünün yükselenlerini kullanmak "Look-Ahead Bias" yaratır ve yanıltıcı kârlar gösterebilir.
                </div>
              )}

              {symbolSource === 'manual' && (
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Symbols (comma separated)</label>
                  <input type="text" className="form-input" value={manualSymbols} onChange={(e) => setManualSymbols(e.target.value)} placeholder="BTCUSDT, ETHUSDT" required />
                </div>
              )}
              <div style={{ display: 'flex', gap: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Start Date</label>
                  <input type="date" className="form-input" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>End Date</label>
                  <input type="date" className="form-input" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
                </div>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Initial Balance ($)</label>
                <input type="number" className="form-input" value={initialBalance} onChange={(e) => setInitialBalance(Number(e.target.value))} required />
              </div>

              {/* Risk Management Selector */}
              <div>
                <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)' }}>Risk Level (0-200)</label>
                <input 
                  type="range" 
                  min="0" 
                  max="200" 
                  value={riskLevel} 
                  onChange={(e) => setRiskLevel(parseInt(e.target.value, 10))}
                  style={{ width: '100%', marginBottom: '8px', cursor: 'pointer' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                  <span>0 (Güvenli)</span>
                  <span>100 (Degen)</span>
                  <span>200 (YOLO/Max Risk)</span>
                </div>
                <div style={{ textAlign: 'center', marginTop: '4px', fontWeight: 'bold', color: 'var(--primary)', fontSize: '0.9rem' }}>
                  Current: {riskLevel}
                </div>
              </div>

              {/* Shields (Kalkanlar) */}
              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <label style={{ display: 'block', marginBottom: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>🛡️ Kalkanlar (Risk Filtreleri)</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.85rem' }}>
                    <input type="checkbox" checked={useBtcShield} onChange={(e) => setUseBtcShield(e.target.checked)} />
                    BTC Crash Shield <span className="text-muted">(Ani BTC çöküşlerinde alımları durdurur)</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.85rem' }}>
                    <input type="checkbox" checked={useHtfShield} onChange={(e) => setUseHtfShield(e.target.checked)} />
                    HTF Trend Shield <span className="text-muted">(Üst zaman dilimi trendiyle uyumlu işlem açar)</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.85rem' }}>
                    <input type="checkbox" checked={useRegimeShield} onChange={(e) => setUseRegimeShield(e.target.checked)} />
                    Market Regime Shield <span className="text-muted">(Yüksek volatilitede işlemleri engeller)</span>
                  </label>
                </div>
              </div>
              <button type="submit" className="btn-primary" disabled={loading} style={{ marginTop: '16px' }}>
                {loading ? 'Starting...' : 'Run Simulation'}
              </button>
            </form>
          </div>

          <div className="glass-card" style={{ padding: '24px' }}>
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={18} /> Active / Recent
            </h3>
            {jobs.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', textAlign: 'center', padding: '16px' }}>
                No backtests found.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '300px', overflowY: 'auto' }}>
                {jobs.map(job => (
                  <div key={job.job_id} 
                       onClick={() => setSelectedJobId(job.job_id)}
                       style={{ 
                         padding: '12px', 
                         cursor: 'pointer', 
                         border: selectedJobId === job.job_id ? '1px solid var(--primary)' : '1px solid rgba(255,255,255,0.06)', 
                         borderRadius: '8px', 
                         background: selectedJobId === job.job_id ? 'rgba(139, 92, 246, 0.05)' : 'rgba(0,0,0,0.2)',
                         transition: 'all 0.2s'
                       }}>
                     <div className="flex-between" style={{ marginBottom: '4px' }}>
                       <strong style={{ fontSize: '0.9rem' }}>{job.strategy_name}</strong>
                       <span className={`badge ${job.status === 'COMPLETED' ? 'badge-success' : job.status === 'FAILED' ? 'badge-danger' : 'badge-primary'}`} style={{ fontSize: '0.7rem' }}>
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
          </div>
        </div>

        <div className="glass-card" style={{ padding: '24px', gridColumn: 'span 2', display: 'flex', flexDirection: 'column', height: '100%' }}>
          <h3 style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TerminalIcon size={18} /> Backtest Details & Logs
          </h3>
          
          {selectedJob ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', flex: 1 }}>
              
              {/* Job Stats Bar */}
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ flex: 1, minWidth: '120px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Status</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {selectedJob.status === 'COMPLETED' ? <CheckCircle size={14} color="var(--success)" /> : selectedJob.status === 'FAILED' || selectedJob.status === 'CANCELLED' ? <XCircle size={14} color="var(--danger)" /> : <Activity size={14} color="var(--primary)" />}
                      <span style={{ fontWeight: 600 }}>{selectedJob.status}</span>
                    </div>
                    {selectedJob.status === 'RUNNING' && (
                      <button onClick={() => handleCancelJob(selectedJob.job_id)} style={{ fontSize: '0.7rem', padding: '2px 8px', background: 'rgba(239, 68, 68, 0.2)', color: 'var(--danger)', border: '1px solid var(--danger)', borderRadius: '4px', cursor: 'pointer' }}>
                        İptal Et
                      </button>
                    )}
                  </div>
                </div>
                
                {selectedJob.status === 'COMPLETED' && selectedJob.final_equity !== null && (
                  <>
                    <div style={{ flex: 1, minWidth: '120px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Final Equity</div>
                      <div style={{ fontWeight: 600, color: 'var(--success)' }}>${selectedJob.final_equity.toFixed(2)}</div>
                    </div>
                    <div style={{ flex: 1, minWidth: '120px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Cycle PnL</div>
                      <div style={{ fontWeight: 600, color: (selectedJob.final_equity - selectedJob.initial_balance) >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                        ${(selectedJob.final_equity - selectedJob.initial_balance).toFixed(2)}
                      </div>
                    </div>
                    <div style={{ flex: 1, minWidth: '120px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Win Rate</div>
                      <div style={{ fontWeight: 600 }}>{(selectedJob.win_rate * 100).toFixed(2)}%</div>
                    </div>
                    <div style={{ flex: 1, minWidth: '120px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Max Drawdown</div>
                      <div style={{ fontWeight: 600, color: 'var(--danger)' }}>{(selectedJob.max_drawdown * 100).toFixed(2)}%</div>
                    </div>
                    <div style={{ flex: 1, minWidth: '120px' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Total Trades</div>
                      <div style={{ fontWeight: 600 }}>{selectedJob.total_trades}</div>
                    </div>
                  </>
                )}
              </div>

              {/* Terminal Logs */}
              <div style={{ 
                flex: 1, 
                height: '500px',
                maxHeight: '500px',
                background: '#0a0f1a', 
                border: '1px solid rgba(255,255,255,0.06)', 
                borderRadius: '8px', 
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column'
              }}>
                <div style={{ background: '#0d1117', padding: '8px 16px', fontSize: '0.75rem', color: '#64748b', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Engine Output</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                      <input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} />
                      Auto-Scroll
                    </label>
                    <span>Job ID: {selectedJob.job_id.substring(0, 8)}...</span>
                  </div>
                </div>
                <div style={{ flex: 1, overflowY: 'auto', padding: '16px', fontFamily: '"Fira Code", monospace' }}>
                  {logs.length === 0 ? (
                    <div style={{ color: '#475569', fontStyle: 'italic', fontSize: '0.8rem' }}>Waiting for logs...</div>
                  ) : (
                    logs.map(log => {
                      const meta = STAGE_META[log.stage] || { color: '#94a3b8', label: log.stage };
                      const levelColor = LEVEL_COLOR[log.level?.toUpperCase()] || '#94a3b8';
                      return (
                        <div key={log.id} style={{ display: 'flex', gap: '12px', fontSize: '0.8rem', marginBottom: '6px', lineHeight: 1.5 }}>
                          <span style={{ color: '#475569', flexShrink: 0 }}>[{formatTime(log.created_at)}]</span>
                          <span style={{ color: meta.color, width: '80px', flexShrink: 0, fontWeight: 600 }}>[{meta.label}]</span>
                          <span style={{ color: levelColor, width: '60px', flexShrink: 0 }}>[{log.level}]</span>
                          <span style={{ color: '#e2e8f0', wordBreak: 'break-word' }}>{log.message}</span>
                        </div>
                      );
                    })
                  )}
                  <div ref={logsEndRef} />
                </div>
              </div>

            </div>
          ) : (
            <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <TerminalIcon size={48} opacity={0.2} style={{ margin: '0 auto 16px' }} />
              <p>Select a backtest from the list to view details and logs.</p>
            </div>
          )}
        </div>
      </div>
      )}
    </div>
  );
};

export default Backtesting;
