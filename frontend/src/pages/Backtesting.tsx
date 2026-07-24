import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

import { BacktestHistory } from './BacktestHistory';

const Backtesting: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [jobs, setJobs] = useState<any[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'run' | 'history'>('run');
  const [autoScroll, setAutoScroll] = useState(false);
  
  const [exchange, setExchange] = useState(() => localStorage.getItem('bt_exchange') || "BINANCE");
  const [configMode, setConfigMode] = useState<'scalping' | 'swing' | 'hodl' | 'regime_adaptive'>(() => (localStorage.getItem('bt_configMode') as any) || 'regime_adaptive');
  const [timeframe, setTimeframe] = useState(() => localStorage.getItem('bt_timeframe') || "15m");
  const [symbolSource, setSymbolSource] = useState<'manual' | 'auto'>(() => (localStorage.getItem('bt_symbolSource') as any) || 'manual');
  const [manualSymbols, setManualSymbols] = useState(() => localStorage.getItem('bt_manualSymbols') || "BTCUSDT, ETHUSDT");
  const [startDate, setStartDate] = useState(() => localStorage.getItem('bt_startDate') || new Date(Date.now() - 3 * 86400000).toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(() => localStorage.getItem('bt_endDate') || new Date().toISOString().split('T')[0]);
  const [initialBalance, setInitialBalance] = useState(() => parseInt(localStorage.getItem('bt_initialBalance') || "10000", 10));
  const [riskLevel, setRiskLevel] = useState(() => parseInt(localStorage.getItem('bt_riskLevel') || "100", 10));

  useEffect(() => {
    localStorage.setItem('bt_exchange', exchange); localStorage.setItem('bt_configMode', configMode);
    localStorage.setItem('bt_timeframe', timeframe); localStorage.setItem('bt_symbolSource', symbolSource);
    localStorage.setItem('bt_manualSymbols', manualSymbols); localStorage.setItem('bt_startDate', startDate);
    localStorage.setItem('bt_endDate', endDate); localStorage.setItem('bt_initialBalance', initialBalance.toString());
    localStorage.setItem('bt_riskLevel', riskLevel.toString());
  }, [exchange, configMode, timeframe, symbolSource, manualSymbols, startDate, endDate, initialBalance, riskLevel]);

  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchJobs = async () => {
      try { const res = await axios.get('/api/v1/backtest'); setJobs(res.data); } catch (e) {}
    };
    fetchJobs(); const iv = setInterval(fetchJobs, 3000); return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    if (!selectedJobId && jobs.length > 0) setSelectedJobId(jobs[0].job_id);
  }, [jobs, selectedJobId]);

  useEffect(() => {
    if (!selectedJobId) return;
    const fetchLogs = async () => {
      try { const res = await axios.get(`/api/v1/logs/recent?account_name=backtest-${selectedJobId}&limit=100`); setLogs(res.data); } catch (e) {}
    };
    fetchLogs(); const iv = setInterval(fetchLogs, 2000); return () => clearInterval(iv);
  }, [selectedJobId]);

  useEffect(() => { if(autoScroll) logsEndRef.current?.scrollIntoView(); }, [logs, autoScroll]);

  const handleRunBacktest = async (e: React.FormEvent) => {
    e.preventDefault(); setLoading(true);
    try {
      const symbolsList = symbolSource === 'auto' ? ['AUTO_GAINERS'] : manualSymbols.split(',').map(s => s.trim().toUpperCase()).filter(s => s);
      const payload = {
        exchange, symbols: symbolsList, timeframe,
        strategy_name: configMode === 'scalping' ? 'hft_momentum' : (configMode === 'swing' ? 'macd_cross' : (configMode === 'regime_adaptive' ? 'regime_adaptive' : 'ema_golden_cross')),
        start_time: new Date(startDate).toISOString(), end_time: new Date(endDate).toISOString(),
        initial_balance: Number(initialBalance), risk_level: riskLevel,
        use_btc_shield: true, use_htf_shield: true, use_regime_shield: true,
      };
      const res = await axios.post('/api/v1/backtest/run', payload);
      setSelectedJobId(res.data.job_id); setLogs([]); 
      const jobsRes = await axios.get('/api/v1/backtest'); setJobs(jobsRes.data);
    } catch (error) {} finally { setLoading(false); }
  };

  const handleClearAll = async () => {
    if(!window.confirm("Abort running tests?")) return;
    try {
      for (const job of jobs.filter(j => j.status === 'RUNNING' || j.status === 'PENDING')) await axios.post(`/api/v1/backtest/${job.job_id}/cancel`);
      setSelectedJobId(null); setLogs([]);
      const res = await axios.get('/api/v1/backtest'); setJobs(res.data);
    } catch(e) {}
  };

  const selectedJob = jobs.find(j => j.job_id === selectedJobId);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '1px solid var(--border)', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '1.5rem', marginBottom: '8px' }}>[BACKTESTING_ENGINE]</h1>
          <p style={{ margin: 0, fontSize: '0.85rem' }}>Historical strategy simulation</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className={activeTab === 'run' ? 'btn-primary' : 'btn-secondary'} onClick={() => setActiveTab('run')}>SIMULATION</button>
          <button className={activeTab === 'history' ? 'btn-primary' : 'btn-secondary'} onClick={() => setActiveTab('history')}>HISTORY</button>
          <button className="btn-danger" onClick={handleClearAll}>ABORT_ALL</button>
        </div>
      </div>

      {activeTab === 'history' ? (
        <BacktestHistory />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
          
          {/* ── Configuration Panel ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div style={{ border: '1px solid var(--border)', padding: '24px' }}>
              <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '1rem', color: 'var(--accent)', marginBottom: '16px' }}>&gt; PARAMETERS</div>
              <form onSubmit={handleRunBacktest} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div><label className="section-label" style={{display:'block', marginBottom:'8px'}}>EXCHANGE</label><select className="form-input" value={exchange} onChange={e => setExchange(e.target.value)}><option value="BINANCE">BINANCE</option><option value="MEXC">MEXC</option></select></div>
                <div><label className="section-label" style={{display:'block', marginBottom:'8px'}}>STRATEGY</label><select className="form-input" value={configMode} onChange={e => setConfigMode(e.target.value as any)}><option value="regime_adaptive">REGIME ADAPTIVE</option><option value="scalping">SCALPING</option><option value="swing">SWING</option><option value="hodl">HODL</option></select></div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div><label className="section-label" style={{display:'block', marginBottom:'8px'}}>TIMEFRAME</label><select className="form-input" value={timeframe} onChange={e => setTimeframe(e.target.value)}><option value="1m">1m</option><option value="15m">15m</option><option value="1h">1h</option><option value="4h">4h</option><option value="1d">1d</option></select></div>
                  <div><label className="section-label" style={{display:'block', marginBottom:'8px'}}>RISK_LEVEL: {riskLevel}%</label><input type="range" min="1" max="100" className="form-input" style={{ padding: '0', cursor: 'pointer' }} value={riskLevel} onChange={e => setRiskLevel(Number(e.target.value))} required /></div>
                </div>
                <div><label className="section-label" style={{display:'block', marginBottom:'8px'}}>SYMBOL SOURCE</label><select className="form-input" value={symbolSource} onChange={e => setSymbolSource(e.target.value as any)}><option value="manual">MANUAL (CSV)</option><option value="auto">AUTO GAINERS (LIVE)</option></select></div>
                {symbolSource === 'manual' && <div><label className="section-label" style={{display:'block', marginBottom:'8px'}}>SYMBOLS</label><input type="text" className="form-input" value={manualSymbols} onChange={e => setManualSymbols(e.target.value)} required /></div>}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div><label className="section-label" style={{display:'block', marginBottom:'8px'}}>START_DATE</label><input type="date" className="form-input" value={startDate} onChange={e => setStartDate(e.target.value)} required /></div>
                  <div><label className="section-label" style={{display:'block', marginBottom:'8px'}}>END_DATE</label><input type="date" className="form-input" value={endDate} onChange={e => setEndDate(e.target.value)} required /></div>
                </div>
                <div><label className="section-label" style={{display:'block', marginBottom:'8px'}}>BALANCE ($)</label><input type="number" className="form-input" value={initialBalance} onChange={e => setInitialBalance(Number(e.target.value))} required /></div>
                <button type="submit" className="btn-primary" disabled={loading} style={{ marginTop: '16px' }}>{loading ? 'INITIALIZING...' : 'START_SIMULATION'}</button>
              </form>
            </div>

            <div style={{ border: '1px solid var(--border)', padding: '16px' }}>
              <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '12px' }}>ACTIVE_SESSIONS</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '200px', overflowY: 'auto' }}>
                {jobs.map(job => (
                  <div key={job.job_id} onClick={() => setSelectedJobId(job.job_id)} style={{ padding: '8px 12px', border: selectedJobId === job.job_id ? '1px solid var(--accent)' : '1px solid var(--border)', cursor: 'pointer', fontFamily: '"JetBrains Mono", monospace', fontSize: '0.75rem', background: selectedJobId === job.job_id ? 'var(--accent-soft)' : 'transparent' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: selectedJobId === job.job_id ? 'var(--accent)' : 'var(--text-primary)' }}>
                      <span>{job.strategy_name}</span>
                      <span style={{ color: job.status === 'RUNNING' ? 'var(--success)' : job.status === 'COMPLETED' ? 'var(--accent)' : 'var(--danger)' }}>[{job.status}]</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* ── Console / Results ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {selectedJob && selectedJob.status === 'COMPLETED' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px' }}>
                {[{l:'FINAL_EQ', v:`$${selectedJob.final_equity?.toFixed(2)}`, c:'var(--accent)'}, {l:'PNL', v:`$${(selectedJob.final_equity - selectedJob.initial_balance)?.toFixed(2)}`, c: (selectedJob.final_equity - selectedJob.initial_balance) >= 0 ? 'var(--success)' : 'var(--danger)'}, {l:'WIN_RATE', v:`${(selectedJob.win_rate*100).toFixed(1)}%`, c:'var(--text-primary)'}, {l:'MAX_DD', v:`${(selectedJob.max_drawdown*100).toFixed(1)}%`, c:'var(--danger)'}, {l:'TRADES', v:selectedJob.total_trades, c:'var(--text-primary)'}].map(st => (
                  <div key={st.l} style={{ border: '1px solid var(--border)', padding: '12px', textAlign: 'center', background: 'var(--bg-raised)' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: '"JetBrains Mono", monospace', marginBottom: '4px' }}>{st.l}</div>
                    <div style={{ fontSize: '1.1rem', color: st.c, fontFamily: '"JetBrains Mono", monospace' }}>{st.v}</div>
                  </div>
                ))}
              </div>
            )}
            
            <div style={{ flex: 1, border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', background: 'var(--bg-base)' }}>
              <div style={{ padding: '8px 16px', background: 'var(--bg-raised)', borderBottom: '1px solid var(--border)', fontSize: '0.75rem', fontFamily: '"JetBrains Mono", monospace', color: 'var(--accent)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>&gt; SIMULATION_LOGS</span>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', color: 'var(--text-primary)' }}>
                  <input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} />
                  AUTO_SCROLL
                </label>
              </div>
              <div style={{ flex: 1, height: '400px', overflowY: 'auto', padding: '16px', fontFamily: '"JetBrains Mono", monospace', fontSize: '0.75rem', lineHeight: '1.6' }}>
                {logs.length === 0 ? <div style={{ color: 'var(--text-muted)' }}>[ NO LOGS ]</div> : logs.map(log => (
                  <div key={log.id} style={{ display: 'flex', gap: '12px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>{new Date(log.created_at).toLocaleTimeString([], {hour12:false})}</span>
                    <span style={{ color: log.level === 'ERROR' ? 'var(--danger)' : log.level === 'WARNING' ? 'var(--warning)' : 'var(--accent)', minWidth: '70px' }}>[{log.level}]</span>
                    <span style={{ color: 'var(--text-primary)' }}>{log.message}</span>
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            </div>
          </div>
          
        </div>
      )}
    </div>
  );
};

export default Backtesting;
