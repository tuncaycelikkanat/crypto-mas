import React, { useState, useEffect, useRef } from 'react';
import { getBacktestJobs, runBacktest, cancelBacktestJob, getRecentLogs } from '../services/api';
import type { BacktestJob, LogEntry } from '../types/api';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { Play, Terminal as TerminalIcon, CheckCircle, XCircle, Activity, History } from 'lucide-react';
import { motion } from 'framer-motion';
import { BacktestHistory } from './BacktestHistory';

const STAGE_META: Record<string, { label: string }> = {
  INIT:        { label: 'Init'       },
  STRATEGY:    { label: 'Strategy'   },
  PORTFOLIO:   { label: 'Portfolio'  },
  RISK:        { label: 'Risk'       },
  EXECUTION:   { label: 'Execution'  },
  PAPER_BROKER:{ label: 'Broker'     },
  TRAILING_SL: { label: 'Trail SL'   },
  COMPLETED:   { label: 'Completed'  },
  FAILED:      { label: 'Failed'     },
  MARKET_DATA: { label: 'Market'     },
};

const LEVEL_COLOR: Record<string, string> = {
  INFO:    'var(--text-secondary)',
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
  const [jobs, setJobs] = useState<BacktestJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [activeTab, setActiveTab] = useState<'rule-based' | 'llm-shadow' | 'history'>('rule-based');
  const [autoScroll, setAutoScroll] = useState(false);
  
  const [exchange, setExchange] = useLocalStorage('bt_exchange', "BINANCE");
  const [configMode, setConfigMode] = useLocalStorage<'scalping' | 'swing' | 'hodl' | 'regime_adaptive'>('bt_configMode', 'regime_adaptive');
  const [timeframe, setTimeframe] = useLocalStorage('bt_timeframe', "15m");
  const [symbolSource, setSymbolSource] = useLocalStorage<'manual' | 'auto'>('bt_symbolSource', 'manual');
  const [manualSymbols, setManualSymbols] = useLocalStorage('bt_manualSymbols', "BTCUSDT, ETHUSDT");
  const [startDate, setStartDate] = useLocalStorage('bt_startDate', new Date(Date.now() - 3 * 86400000).toISOString().split('T')[0]);
  const [endDate, setEndDate] = useLocalStorage('bt_endDate', new Date().toISOString().split('T')[0]);
  const [initialBalance, setInitialBalance] = useLocalStorage('bt_initialBalance', 10000);
  const [riskLevel, setRiskLevel] = useLocalStorage('bt_riskLevel', 100);
  const [useBtcShield, setUseBtcShield] = useLocalStorage('bt_useBtcShield', true);
  const [useHtfShield, setUseHtfShield] = useLocalStorage('bt_useHtfShield', true);
  const [useRegimeShield, setUseRegimeShield] = useLocalStorage('bt_useRegimeShield', true);
  const [configJsonText, setConfigJsonText] = useLocalStorage('bt_configJsonText', JSON.stringify({
    bull_tactic: { min_adx: 25.0, rsi_threshold: 42.0 },
    bear_tactic: { min_adx: 25.0, rsi_threshold: 58.0 },
    sideways_tactic: { rsi_oversold: 30.0, rsi_overbought: 70.0 }
  }, null, 2));

  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await getBacktestJobs();
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
        const res = await getRecentLogs(`backtest-${selectedJobId}`, 100);
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
        
      let parsedConfig = null;
      if (configMode === 'regime_adaptive') {
        try {
          parsedConfig = JSON.parse(configJsonText);
        } catch (err) {
          alert("Invalid JSON in Advanced Configuration");
          setLoading(false);
          return;
        }
      }

      const payload = {
        exchange,
        symbols: symbolsList,
        timeframe: timeframe,
        strategy_name: configMode === 'scalping' ? 'hft_momentum' : (configMode === 'swing' ? 'macd_cross' : (configMode === 'regime_adaptive' ? 'regime_adaptive' : 'ema_golden_cross')),
        start_time: new Date(startDate).toISOString(),
        end_time: new Date(endDate).toISOString(),
        initial_balance: Number(initialBalance),
        risk_level: riskLevel,
        use_btc_shield: useBtcShield,
        use_htf_shield: useHtfShield,
        use_regime_shield: useRegimeShield,
        config_json: parsedConfig,
        run_llm: activeTab === 'llm-shadow',
      };

      const res = await runBacktest(payload);
      setSelectedJobId(res.data.job_id);
      setLogs([]); 
      
      const jobsRes = await getBacktestJobs();
      setJobs(jobsRes.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelJob = async (jobId: string) => {
    try {
      await cancelBacktestJob(jobId);
      const res = await getBacktestJobs();
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
        await cancelBacktestJob(job.job_id);
      }
      setSelectedJobId(null);
      setLogs([]);
      const res = await getBacktestJobs();
      setJobs(res.data);
    } catch(e) {
      console.error(e);
    }
  };

  const selectedJob = jobs.find(j => j.job_id === selectedJobId);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      
      {/* Header & Tabs */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ marginBottom: 4 }}>Backtesting Engine</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Simulate dynamic multi-agent strategies against historical tick data</p>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <div style={{ display: 'flex', background: 'var(--bg-raised)', padding: '4px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
            <button 
              className={activeTab === 'rule-based' ? 'btn-primary' : 'btn-ghost'}
              style={{ fontSize: '0.8rem', padding: '6px 12px', height: 32 }}
              onClick={() => setActiveTab('rule-based')}
            >
              Rule-Based Run
            </button>
            <button 
              className={activeTab === 'llm-shadow' ? 'btn-primary' : 'btn-ghost'}
              style={{ fontSize: '0.8rem', padding: '6px 12px', height: 32 }}
              onClick={() => setActiveTab('llm-shadow')}
            >
              LLM Shadow Run
            </button>
            <button 
              className={activeTab === 'history' ? 'btn-primary' : 'btn-ghost'}
              style={{ fontSize: '0.8rem', padding: '6px 12px', height: 32, display: 'flex', alignItems: 'center', gap: '6px' }}
              onClick={() => setActiveTab('history')}
            >
              <History size={14} /> History
            </button>
          </div>
          <button onClick={handleClearAll} className="btn-danger" style={{ fontSize: '0.8rem', padding: '6px 12px', height: 40 }}>
            <XCircle size={14} /> Clear All
          </button>
        </div>
      </div>

      {activeTab === 'history' ? (
        <BacktestHistory />
      ) : (
      <div className="grid-cols-3" style={{ alignItems: 'start', gap: '20px' }}>
        
        {/* Left Column: Config Form & Job Queue */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', gridColumn: 'span 1' }}>
          
          <div className="card" style={{ padding: '22px' }}>
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Play size={16} /> {activeTab === 'llm-shadow' ? 'New LLM Shadow Backtest' : 'New Simulation Run'}
            </h3>
            
            {activeTab === 'llm-shadow' && (
              <div style={{ marginBottom: '18px', fontSize: '0.8rem', color: 'var(--warning)', background: 'var(--warning-soft)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                <strong>⚠️ LLM API Maliyet Uyarısı:</strong><br />
                LLM Shadow Run her üretilen sinyal için 3 ayrı ajan çalıştırır. Lütfen sadece <strong>kısa bir tarih aralığı (örn. 3-7 gün)</strong> ve <strong>belirli 1-2 coin</strong> seçin.
              </div>
            )}

            <form onSubmit={handleRunBacktest} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label className="section-label" style={{ display: 'block', marginBottom: 6 }}>Exchange</label>
                <select className="form-input" value={exchange} onChange={(e) => setExchange(e.target.value)}>
                  <option value="BINANCE">Binance</option>
                  <option value="MEXC">MEXC</option>
                </select>
              </div>

              <div>
                <label className="section-label" style={{ display: 'block', marginBottom: 6 }}>Trading Strategy Mode</label>
                <select className="form-input" value={configMode} onChange={(e) => setConfigMode(e.target.value as any)}>
                  <option value="regime_adaptive">Regime Adaptive (Dynamic Tactics)</option>
                  <option value="scalping">Scalping (Micro Pullback)</option>
                  <option value="swing">Swing Trading (MACD Cross)</option>
                  <option value="hodl">Hodl (EMA Golden Cross)</option>
                </select>
              </div>

              <div>
                <label className="section-label" style={{ display: 'block', marginBottom: 6 }}>Timeframe (Candle Interval)</label>
                <select className="form-input" value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
                  <option value="1m">1 Minute (1m)</option>
                  <option value="5m">5 Minutes (5m)</option>
                  <option value="15m">15 Minutes (15m)</option>
                  <option value="1h">1 Hour (1h)</option>
                  <option value="4h">4 Hours (4h)</option>
                  <option value="1d">1 Day (1d)</option>
                </select>
              </div>
              
              <div>
                <label className="section-label" style={{ display: 'block', marginBottom: 6 }}>Coin Source</label>
                <select className="form-input" value={symbolSource} onChange={(e) => setSymbolSource(e.target.value as any)}>
                  <option value="manual">Manual Entry</option>
                  <option value="auto">Auto-Scanner (Top Gainers)</option>
                </select>
              </div>

              {symbolSource === 'manual' && (
                <div>
                  <label className="section-label" style={{ display: 'block', marginBottom: 6 }}>Symbols (comma separated)</label>
                  <input type="text" className="form-input mono" value={manualSymbols} onChange={(e) => setManualSymbols(e.target.value)} placeholder="BTCUSDT, ETHUSDT" required />
                </div>
              )}

              <div className="grid-cols-2" style={{ gap: '10px' }}>
                <div>
                  <label className="section-label" style={{ display: 'block', marginBottom: 6 }}>Start Date</label>
                  <input type="date" className="form-input" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
                </div>
                <div>
                  <label className="section-label" style={{ display: 'block', marginBottom: 6 }}>End Date</label>
                  <input type="date" className="form-input" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
                </div>
              </div>

              <div>
                <label className="section-label" style={{ display: 'block', marginBottom: 6 }}>Initial Balance ($)</label>
                <input type="number" className="form-input mono" value={initialBalance} onChange={(e) => setInitialBalance(Number(e.target.value))} required />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <label className="section-label">Risk Level (0-200)</label>
                  <span className="mono" style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>{riskLevel}</span>
                </div>
                <input 
                  type="range" 
                  min="0" 
                  max="200" 
                  value={riskLevel} 
                  onChange={(e) => setRiskLevel(parseInt(e.target.value, 10))}
                />
              </div>

              {/* Safety Filters */}
              <div style={{ background: 'var(--bg-raised)', padding: '14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                <label className="section-label" style={{ marginBottom: '10px', display: 'block' }}>
                  Risk Shields
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                    <input type="checkbox" checked={useBtcShield} onChange={(e) => setUseBtcShield(e.target.checked)} style={{ accentColor: 'var(--text-primary)' }} />
                    BTC Crash Shield <span className="text-muted">(Crash breaker)</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                    <input type="checkbox" checked={useHtfShield} onChange={(e) => setUseHtfShield(e.target.checked)} style={{ accentColor: 'var(--text-primary)' }} />
                    HTF Trend Shield <span className="text-muted">(Trend filter)</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                    <input type="checkbox" checked={useRegimeShield} onChange={(e) => setUseRegimeShield(e.target.checked)} style={{ accentColor: 'var(--text-primary)' }} />
                    Market Regime Shield <span className="text-muted">(High-vol barrier)</span>
                  </label>
                </div>
              </div>

              {configMode === 'regime_adaptive' && (
                <div style={{ background: 'var(--bg-raised)', padding: '14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                  <label className="section-label" style={{ marginBottom: '8px', display: 'block' }}>
                    Tactic JSON Parameters
                  </label>
                  <textarea
                    className="form-input mono"
                    style={{ width: '100%', height: '120px', resize: 'vertical', fontSize: '0.75rem' }}
                    value={configJsonText}
                    onChange={(e) => setConfigJsonText(e.target.value)}
                  />
                </div>
              )}

              <button type="submit" className={activeTab === 'llm-shadow' ? 'btn-danger' : 'btn-primary'} disabled={loading} style={{ marginTop: '6px', padding: '10px' }}>
                {loading ? 'Simulating…' : (activeTab === 'llm-shadow' ? 'Run LLM Simulation' : 'Run Backtest Simulation')}
              </button>
            </form>
          </div>

          {/* Active / Recent Jobs */}
          <div className="card" style={{ padding: '20px' }}>
            <h3 style={{ marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.95rem' }}>
              <Activity size={16} /> Recent Test Queue
            </h3>
            {jobs.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '16px' }}>
                No active backtests found.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '280px', overflowY: 'auto' }}>
                {jobs.map(job => (
                  <div key={job.job_id} 
                    onClick={() => setSelectedJobId(job.job_id)}
                    style={{ 
                      padding: '10px 12px', 
                      cursor: 'pointer', 
                      border: selectedJobId === job.job_id ? '1px solid var(--text-primary)' : '1px solid var(--border)', 
                      borderRadius: 'var(--radius-sm)', 
                      background: selectedJobId === job.job_id ? 'var(--accent-soft)' : 'var(--bg-raised)',
                      transition: 'all 0.15s'
                    }}>
                     <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                       <strong style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>{job.strategy_name}</strong>
                       <span className={`badge badge-${job.status === 'COMPLETED' ? 'success' : job.status === 'FAILED' ? 'danger' : 'primary'}`} style={{ fontSize: '0.65rem' }}>
                         {job.status}
                       </span>
                     </div>
                     <div className="text-muted mono" style={{ fontSize: '0.72rem' }}>
                       {job.symbols.join(', ')} • {new Date(job.start_time).toLocaleDateString()}
                     </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Engine Details & Logs Stream */}
        <div className="card" style={{ gridColumn: 'span 2', display: 'flex', flexDirection: 'column', padding: '22px' }}>
          <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TerminalIcon size={16} /> Backtest Telemetry & Logs
          </h3>
          
          {selectedJob ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', flex: 1 }}>
              
              {/* Stat Indicators */}
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', background: 'var(--bg-raised)', padding: '14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                <div style={{ flex: 1, minWidth: '110px' }}>
                  <div className="section-label" style={{ marginBottom: '4px' }}>Status</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {selectedJob.status === 'COMPLETED' ? <CheckCircle size={15} color="var(--success)" /> : selectedJob.status === 'FAILED' || selectedJob.status === 'CANCELLED' ? <XCircle size={15} color="var(--danger)" /> : <Activity size={15} color="var(--text-primary)" />}
                    <span style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-primary)' }}>{selectedJob.status}</span>
                    {selectedJob.status === 'RUNNING' && (
                      <button onClick={() => handleCancelJob(selectedJob.job_id)} className="btn-danger" style={{ fontSize: '0.7rem', padding: '2px 6px', height: 'auto' }}>
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
                
                {selectedJob.status === 'COMPLETED' && selectedJob.final_equity !== null && (
                  <>
                    <div style={{ flex: 1, minWidth: '110px' }}>
                      <div className="section-label" style={{ marginBottom: '4px' }}>Final Equity</div>
                      <div className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--text-primary)' }}>${selectedJob.final_equity.toFixed(2)}</div>
                    </div>
                    <div style={{ flex: 1, minWidth: '110px' }}>
                      <div className="section-label" style={{ marginBottom: '4px' }}>Cycle Net PnL</div>
                      <div className="stat-value" style={{ fontSize: '1.2rem', color: (selectedJob.final_equity - selectedJob.initial_balance) >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                        ${(selectedJob.final_equity - selectedJob.initial_balance).toFixed(2)}
                      </div>
                    </div>
                    <div style={{ flex: 1, minWidth: '100px' }}>
                      <div className="section-label" style={{ marginBottom: '4px' }}>Win Rate</div>
                      <div className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--text-primary)' }}>{((selectedJob.win_rate || 0) * 100).toFixed(1)}%</div>
                    </div>
                    <div style={{ flex: 1, minWidth: '100px' }}>
                      <div className="section-label" style={{ marginBottom: '4px' }}>Drawdown</div>
                      <div className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--danger)' }}>{((selectedJob.max_drawdown || 0) * 100).toFixed(1)}%</div>
                    </div>
                    <div style={{ flex: 1, minWidth: '80px' }}>
                      <div className="section-label" style={{ marginBottom: '4px' }}>Trades</div>
                      <div className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--text-primary)' }}>{selectedJob.total_trades}</div>
                    </div>
                  </>
                )}
              </div>

              {/* Log Stream Window */}
              <div style={{ 
                flex: 1, 
                height: '450px',
                background: 'var(--bg-base)', 
                border: '1px solid var(--border)', 
                borderRadius: 'var(--radius-sm)', 
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column'
              }}>
                <div style={{ background: 'var(--bg-raised)', padding: '10px 16px', fontSize: '0.75rem', color: 'var(--text-muted)', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="mono" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Backtest Engine Log Stream</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                      <input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} style={{ accentColor: 'var(--text-primary)' }} />
                      Auto-Scroll
                    </label>
                    <span className="mono">ID: {selectedJob.job_id.substring(0, 8)}…</span>
                  </div>
                </div>
                <div style={{ flex: 1, overflowY: 'auto', padding: '14px', fontFamily: '"JetBrains Mono", monospace' }}>
                  {logs.length === 0 ? (
                    <div style={{ color: 'var(--text-dim)', fontStyle: 'italic', fontSize: '0.8rem' }}>Waiting for backtest signals…</div>
                  ) : (
                    logs.map(log => {
                      const meta = STAGE_META[log.stage] || { label: log.stage };
                      const levelColor = LEVEL_COLOR[log.level?.toUpperCase()] || 'var(--text-muted)';
                      return (
                        <div key={log.id} style={{ display: 'flex', gap: '12px', fontSize: '0.8rem', marginBottom: '6px', lineHeight: 1.5 }}>
                          <span style={{ color: 'var(--text-dim)', flexShrink: 0 }}>[{formatTime(log.created_at)}]</span>
                          <span style={{ color: 'var(--text-primary)', width: '80px', flexShrink: 0, fontWeight: 700 }}>[{meta.label}]</span>
                          <span style={{ color: levelColor, width: '60px', flexShrink: 0, fontWeight: 600 }}>[{log.level}]</span>
                          <span style={{ color: 'var(--text-secondary)', wordBreak: 'break-word' }}>{log.message}</span>
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
              <TerminalIcon size={48} opacity={0.2} style={{ margin: '0 auto 18px' }} />
              <p style={{ fontSize: '0.95rem' }}>Select a backtest job from the queue to view analytics and logs.</p>
            </div>
          )}
        </div>

      </div>
      )}
    </motion.div>
  );
};

export default Backtesting;
