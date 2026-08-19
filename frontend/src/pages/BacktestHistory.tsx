import React, { useState, useEffect } from 'react';
import { getBacktestJobs, deleteBacktestJob, getBacktestCompareData } from '../services/api';
import type { BacktestJob, EquityCurvePoint } from '../types/api';
import { motion } from 'framer-motion';
import { ResponsiveContainer, LineChart, CartesianGrid, XAxis, YAxis, Tooltip as RechartsTooltip, Line } from 'recharts';
import { ArrowRight, ChevronUp, ChevronDown, Trash2, ArrowLeft } from 'lucide-react';

export const BacktestHistory: React.FC = () => {
  const [jobs, setJobs] = useState<BacktestJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [compareData, setCompareData] = useState<Record<string, any[]>>({});
  const [compareMode, setCompareMode] = useState(false);

  const fetchJobs = async () => {
    try {
      setLoading(true);
      const res = await getBacktestJobs();
      setJobs(res.data.filter((j: BacktestJob) => j.status !== 'RUNNING'));
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const toggleSelect = (job_id: string) => {
    if (selectedIds.includes(job_id)) {
      setSelectedIds(selectedIds.filter(id => id !== job_id));
    } else {
      if (selectedIds.length >= 2) {
        alert("You can only compare up to 2 tests at a time.");
        return;
      }
      setSelectedIds([...selectedIds, job_id]);
    }
  };

  const toggleExpand = (job_id: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(job_id)) {
      newExpanded.delete(job_id);
    } else {
      newExpanded.add(job_id);
    }
    setExpandedRows(newExpanded);
  };

  const handleDelete = async (job_id: string) => {
    if (!window.confirm("Bu testi silmek istediğinize emin misiniz?")) return;
    try {
      await deleteBacktestJob(job_id);
      setJobs(jobs.filter(j => j.job_id !== job_id));
      setSelectedIds(selectedIds.filter(id => id !== job_id));
    } catch (e) {
      console.error("Failed to delete job", e);
    }
  };

  const handleCompare = async () => {
    if (selectedIds.length !== 2) {
      alert("Please select exactly 2 tests to compare.");
      return;
    }
    setCompareMode(true);
    const dataMap: Record<string, EquityCurvePoint[]> = {};
    for (const id of selectedIds) {
      try {
        const res = await getBacktestCompareData(id);
        dataMap[id] = res.data.equity_curve.map((point: EquityCurvePoint) => ({
          time: new Date(point.time).toLocaleString(),
          equity: point.equity
        }));
      } catch (e) {
        console.error(`Failed to load data for ${id}`);
      }
    }
    setCompareData(dataMap);
  };

  if (compareMode) {
    const jobA = jobs.find(j => j.job_id === selectedIds[0]);
    const jobB = jobs.find(j => j.job_id === selectedIds[1]);

    return (
      <motion.div className="card" initial={{ opacity: 0, scale: 0.99 }} animate={{ opacity: 1, scale: 1 }} style={{ padding: '24px' }}>
        <button onClick={() => setCompareMode(false)} className="btn-secondary" style={{ marginBottom: '20px' }}>
          <ArrowLeft size={14} /> Back to History
        </button>
        <h2 style={{ marginBottom: '24px', fontSize: '1.3rem' }}>Compare Backtest Runs</h2>

        <div className="grid-cols-2" style={{ gap: '20px' }}>
          
          {/* Test A */}
          <div style={{ background: 'var(--bg-raised)', padding: '20px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
            <h3 style={{ color: 'var(--text-primary)', marginBottom: '4px' }}>Test A: {jobA?.strategy_name}</h3>
            <div className="mono text-muted" style={{ fontSize: '0.75rem', marginBottom: '16px' }}>{jobA?.job_id}</div>
            
            <div className="grid-cols-2" style={{ gap: '12px', marginBottom: '20px' }}>
              <div><span className="section-label">Win Rate</span> <div className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--text-primary)', marginTop: 2 }}>{((jobA?.win_rate || 0) * 100).toFixed(1)}%</div></div>
              <div><span className="section-label">Max Drawdown</span> <div className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--danger)', marginTop: 2 }}>{((jobA?.max_drawdown || 0) * 100).toFixed(1)}%</div></div>
              <div><span className="section-label">Final Equity</span> <div className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--text-primary)', marginTop: 2 }}>${jobA?.final_equity?.toFixed(2)}</div></div>
              <div><span className="section-label">Trades</span> <div className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--text-primary)', marginTop: 2 }}>{jobA?.total_trades}</div></div>
            </div>
            
            <div style={{ height: '260px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={compareData[jobA!.job_id] || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="time" hide />
                  <YAxis domain={['auto', 'auto']} stroke="var(--text-dim)" fontSize={11} tickFormatter={(val: any) => `$${val}`} />
                  <RechartsTooltip contentStyle={{ background: 'var(--bg-raised)', border: '1px solid var(--border-hover)', borderRadius: '8px', color: 'var(--text-primary)' }} />
                  <Line type="monotone" dataKey="equity" stroke="var(--text-primary)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Test B */}
          <div style={{ background: 'var(--bg-raised)', padding: '20px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
            <h3 style={{ color: 'var(--text-primary)', marginBottom: '4px' }}>Test B: {jobB?.strategy_name}</h3>
            <div className="mono text-muted" style={{ fontSize: '0.75rem', marginBottom: '16px' }}>{jobB?.job_id}</div>
            
            <div className="grid-cols-2" style={{ gap: '12px', marginBottom: '20px' }}>
              <div><span className="section-label">Win Rate</span> <div className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--text-primary)', marginTop: 2 }}>{((jobB?.win_rate || 0) * 100).toFixed(1)}%</div></div>
              <div><span className="section-label">Max Drawdown</span> <div className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--danger)', marginTop: 2 }}>{((jobB?.max_drawdown || 0) * 100).toFixed(1)}%</div></div>
              <div><span className="section-label">Final Equity</span> <div className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--text-primary)', marginTop: 2 }}>${jobB?.final_equity?.toFixed(2)}</div></div>
              <div><span className="section-label">Trades</span> <div className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--text-primary)', marginTop: 2 }}>{jobB?.total_trades}</div></div>
            </div>

            <div style={{ height: '260px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={compareData[jobB!.job_id] || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="time" hide />
                  <YAxis domain={['auto', 'auto']} stroke="var(--text-dim)" fontSize={11} tickFormatter={(val: any) => `$${val}`} />
                  <RechartsTooltip contentStyle={{ background: 'var(--bg-raised)', border: '1px solid var(--border-hover)', borderRadius: '8px', color: 'var(--text-primary)' }} />
                  <Line type="monotone" dataKey="equity" stroke="var(--success)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      </motion.div>
    );
  }

  return (
    <div className="card" style={{ padding: '22px 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', marginBottom: 2 }}>Test Archive & History</h2>
          <p className="text-muted" style={{ fontSize: '0.8rem' }}>Review and compare historical simulation results</p>
        </div>
        <div>
          <button 
            onClick={handleCompare}
            disabled={selectedIds.length !== 2}
            className={selectedIds.length === 2 ? 'btn-primary' : 'btn-secondary'}
            style={{ fontSize: '0.8rem', padding: '8px 14px' }}
          >
            <ArrowRight size={14} /> Compare Selected ({selectedIds.length}/2)
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>Loading history…</div>
      ) : jobs.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>No completed backtests found in database.</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="glass-table">
            <thead>
              <tr>
                <th style={{ width: '40px' }}>Select</th>
                <th>Date Range & Symbols</th>
                <th>Strategy</th>
                <th>Risk</th>
                <th>Net PnL</th>
                <th>Win Rate</th>
                <th>Trades</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => {
                const netPnL = (job.final_equity || 0) - (job.initial_balance || 0);
                const totalFees = job.total_fees_paid || 0;
                const grossPnL = netPnL + totalFees;
                const isExpanded = expandedRows.has(job.job_id);

                return (
                  <React.Fragment key={job.job_id}>
                    <tr style={{ background: selectedIds.includes(job.job_id) ? 'var(--accent-soft)' : 'transparent', cursor: 'pointer' }} onClick={() => toggleExpand(job.job_id)}>
                      <td onClick={(e) => e.stopPropagation()}>
                        <input 
                          type="checkbox" 
                          checked={selectedIds.includes(job.job_id)} 
                          onChange={() => toggleSelect(job.job_id)}
                          style={{ cursor: 'pointer', accentColor: 'var(--text-primary)' }}
                        />
                      </td>
                      <td>
                        <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                          {new Date(job.start_time).toLocaleDateString()} - {new Date(job.end_time).toLocaleDateString()}
                        </div>
                        <div className="text-muted mono" style={{ fontSize: '0.75rem', marginTop: '2px' }}>
                          {job.symbols.join(', ')}
                        </div>
                      </td>
                      <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{job.strategy_name}</td>
                      <td className="mono">{job.config_json?.risk_level ?? '-'}</td>
                      <td className="mono" style={{ color: netPnL >= 0 ? 'var(--success)' : 'var(--danger)', fontWeight: 700 }}>
                        ${netPnL.toFixed(2)}
                      </td>
                      <td className="mono">{((job.win_rate || 0) * 100).toFixed(1)}%</td>
                      <td className="mono">{job.total_trades || 0}</td>
                      <td onClick={(e) => e.stopPropagation()} style={{ textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '6px' }}>
                          <button 
                            onClick={() => toggleExpand(job.job_id)}
                            className="btn-ghost"
                            style={{ padding: '6px' }}
                            title="Details"
                          >
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </button>
                          <button 
                            onClick={() => handleDelete(job.job_id)}
                            className="btn-ghost"
                            style={{ color: 'var(--danger)', padding: '6px' }}
                            title="Delete"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr style={{ background: 'var(--bg-raised)' }}>
                        <td colSpan={8} style={{ padding: '14px 20px', borderTop: 'none' }}>
                          <motion.div 
                            initial={{ opacity: 0, height: 0 }} 
                            animate={{ opacity: 1, height: 'auto' }} 
                            exit={{ opacity: 0, height: 0 }}
                            className="grid-cols-4" 
                            style={{ gap: '14px', background: 'var(--bg-base)', padding: '14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}
                          >
                            <div>
                              <div className="section-label" style={{ marginBottom: 4 }}>Gross PnL (Brüt)</div>
                              <div className="stat-value" style={{ fontSize: '1.15rem', color: grossPnL >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                                ${grossPnL.toFixed(2)}
                              </div>
                            </div>
                            <div>
                              <div className="section-label" style={{ marginBottom: 4 }}>Total Fees (Komisyon)</div>
                              <div className="stat-value" style={{ fontSize: '1.15rem', color: 'var(--warning)' }}>
                                -${totalFees.toFixed(2)}
                              </div>
                            </div>
                            <div>
                              <div className="section-label" style={{ marginBottom: 4 }}>Net Realized PnL</div>
                              <div className="stat-value" style={{ fontSize: '1.15rem', color: netPnL >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                                ${netPnL.toFixed(2)}
                              </div>
                            </div>
                            <div>
                              <div className="section-label" style={{ marginBottom: 4 }}>Max Drawdown</div>
                              <div className="stat-value" style={{ fontSize: '1.15rem', color: 'var(--danger)' }}>
                                -{((job.max_drawdown || 0) * 100).toFixed(2)}%
                              </div>
                            </div>
                          </motion.div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
