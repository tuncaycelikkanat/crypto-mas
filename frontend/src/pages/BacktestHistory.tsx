import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';
import { ArrowRight, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import { motion } from 'framer-motion';

interface BacktestConfig {
  risk_level: number;
  use_btc_shield: boolean;
  use_htf_shield: boolean;
  use_regime_shield: boolean;
}

interface BacktestJob {
  job_id: string;
  status: string;
  strategy_name: string;
  symbols: string[];
  start_time: string;
  end_time: string;
  initial_balance: number;
  final_equity: number | null;
  total_fees_paid: number | null;
  total_trades: number | null;
  win_rate: number | null;
  max_drawdown: number | null;
  config_json: BacktestConfig | null;
}

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
      const res = await axios.get('/api/v1/backtest');
      setJobs(res.data.filter((j: any) => j.status !== 'RUNNING'));
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
      await axios.delete(`/api/v1/backtest/${job_id}`);
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
    const dataMap: Record<string, any[]> = {};
    for (const id of selectedIds) {
      try {
        const res = await axios.get(`/api/v1/backtest/${id}/compare-data`);
        dataMap[id] = res.data.equity_curve.map((point: any) => ({
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
      <motion.div className="card" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.3 }}>
        <button onClick={() => setCompareMode(false)} className="btn-secondary" style={{ marginBottom: '24px' }}>
          &larr; Back to History
        </button>
        <h2 style={{ marginBottom: '24px', color: 'var(--text-primary)' }}>Compare Tests</h2>

        <div className="grid-cols-2" style={{ gap: '24px' }}>
          <div style={{ background: 'var(--bg-surface)', padding: '24px', borderRadius: '12px', border: '1px solid var(--border)' }}>
            <h3 style={{ color: 'var(--accent)', marginBottom: '8px' }}>Test A: {jobA?.strategy_name}</h3>
            <div className="mono" style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '16px' }}>{jobA?.job_id}</div>
            <div className="grid-cols-2" style={{ gap: '16px', marginBottom: '24px' }}>
              <div><strong className="text-muted">Win Rate:</strong> <span className="stat-value" style={{ fontSize: '1.2rem' }}>{((jobA?.win_rate || 0) * 100).toFixed(1)}%</span></div>
              <div><strong className="text-muted">Drawdown:</strong> <span className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--danger)' }}>{((jobA?.max_drawdown || 0) * 100).toFixed(1)}%</span></div>
              <div><strong className="text-muted">Final Equity:</strong> <span className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--success)' }}>${jobA?.final_equity?.toFixed(2)}</span></div>
              <div><strong className="text-muted">Total Trades:</strong> <span className="stat-value" style={{ fontSize: '1.2rem' }}>{jobA?.total_trades}</span></div>
              <div style={{ gridColumn: 'span 2', padding: '12px', background: 'var(--bg-base)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                <strong style={{ color: 'var(--text-primary)' }}>Config:</strong> Risk {jobA?.config_json?.risk_level} 
                <span className="text-muted" style={{ margin: '0 8px' }}>|</span> BTC {jobA?.config_json?.use_btc_shield ? 'On' : 'Off'} 
                <span className="text-muted" style={{ margin: '0 8px' }}>|</span> Regime {jobA?.config_json?.use_regime_shield ? 'On' : 'Off'}
              </div>
            </div>
            
            <div style={{ height: '300px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={compareData[jobA!.job_id] || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="time" hide />
                  <YAxis domain={['auto', 'auto']} stroke="var(--text-muted)" fontSize={12} tickFormatter={(val) => `$${val}`} />
                  <RechartsTooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)' }} />
                  <Line type="monotone" dataKey="equity" stroke="var(--accent)" strokeWidth={3} dot={false} isAnimationActive={true} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div style={{ background: 'var(--bg-surface)', padding: '24px', borderRadius: '12px', border: '1px solid var(--border)' }}>
            <h3 style={{ color: 'var(--success)', marginBottom: '8px' }}>Test B: {jobB?.strategy_name}</h3>
            <div className="mono" style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '16px' }}>{jobB?.job_id}</div>
            <div className="grid-cols-2" style={{ gap: '16px', marginBottom: '24px' }}>
              <div><strong className="text-muted">Win Rate:</strong> <span className="stat-value" style={{ fontSize: '1.2rem' }}>{((jobB?.win_rate || 0) * 100).toFixed(1)}%</span></div>
              <div><strong className="text-muted">Drawdown:</strong> <span className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--danger)' }}>{((jobB?.max_drawdown || 0) * 100).toFixed(1)}%</span></div>
              <div><strong className="text-muted">Final Equity:</strong> <span className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--success)' }}>${jobB?.final_equity?.toFixed(2)}</span></div>
              <div><strong className="text-muted">Trades:</strong> <span className="stat-value" style={{ fontSize: '1.2rem' }}>{jobB?.total_trades}</span></div>
              <div style={{ gridColumn: 'span 2', padding: '12px', background: 'var(--bg-base)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                <strong style={{ color: 'var(--text-primary)' }}>Config:</strong> Risk {jobB?.config_json?.risk_level} 
                <span className="text-muted" style={{ margin: '0 8px' }}>|</span> BTC {jobB?.config_json?.use_btc_shield ? 'On' : 'Off'} 
                <span className="text-muted" style={{ margin: '0 8px' }}>|</span> Regime {jobB?.config_json?.use_regime_shield ? 'On' : 'Off'}
              </div>
            </div>

            <div style={{ height: '300px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={compareData[jobB!.job_id] || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="time" hide />
                  <YAxis domain={['auto', 'auto']} stroke="var(--text-muted)" fontSize={12} tickFormatter={(val) => `$${val}`} />
                  <RechartsTooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)' }} />
                  <Line type="monotone" dataKey="equity" stroke="var(--success)" strokeWidth={3} dot={false} isAnimationActive={true} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div className="card" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ color: 'var(--text-primary)' }}>Test History</h2>
        <div>
          <button 
            onClick={handleCompare}
            disabled={selectedIds.length !== 2}
            className={selectedIds.length === 2 ? 'btn-primary' : 'btn-secondary'}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '8px',
              opacity: selectedIds.length === 2 ? 1 : 0.5,
              cursor: selectedIds.length === 2 ? 'pointer' : 'not-allowed',
            }}
          >
            <ArrowRight size={16} /> Compare Selected ({selectedIds.length}/2)
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>Loading history...</div>
      ) : jobs.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>No past backtests found.</div>
      ) : (
        <div className="glass-table-container">
          <table className="glass-table">
            <thead>
              <tr>
                <th>Select</th>
                <th>Date</th>
                <th>Strategy</th>
                <th>Risk</th>
                <th>PnL</th>
                <th>Win Rate</th>
                <th>Actions</th>
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
                    <tr style={{ background: selectedIds.includes(job.job_id) ? 'var(--bg-raised)' : 'transparent', cursor: 'pointer' }} onClick={() => toggleExpand(job.job_id)}>
                      <td onClick={(e) => e.stopPropagation()}>
                        <input 
                          type="checkbox" 
                          checked={selectedIds.includes(job.job_id)} 
                          onChange={() => toggleSelect(job.job_id)}
                          style={{ cursor: 'pointer', accentColor: 'var(--accent)' }}
                        />
                      </td>
                      <td>
                        <div style={{ color: 'var(--text-primary)' }}>
                          {new Date(job.start_time).toLocaleDateString()} - {new Date(job.end_time).toLocaleDateString()}
                        </div>
                        <div className="text-muted" style={{ fontSize: '0.8rem', marginTop: '4px' }}>
                          {job.symbols.join(', ')}
                        </div>
                      </td>
                      <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{job.strategy_name}</td>
                      <td>{job.config_json?.risk_level ?? '-'}</td>
                      <td style={{ color: netPnL >= 0 ? 'var(--success)' : 'var(--danger)', fontWeight: 600 }}>
                        ${netPnL.toFixed(2)}
                      </td>
                      <td style={{ color: 'var(--text-primary)' }}>
                        {((job.win_rate || 0) * 100).toFixed(1)}%
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button 
                            onClick={() => toggleExpand(job.job_id)}
                            className="btn-ghost"
                            style={{ color: 'var(--text-muted)', padding: '8px' }}
                            title="Details"
                          >
                            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                          </button>
                          <button 
                            onClick={() => handleDelete(job.job_id)}
                            className="btn-ghost"
                            style={{ color: 'var(--danger)', padding: '8px' }}
                            title="Delete"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr style={{ background: 'var(--bg-surface)' }}>
                        <td colSpan={7} style={{ padding: '16px 24px', borderTop: 'none' }}>
                          <motion.div 
                            initial={{ opacity: 0, height: 0 }} 
                            animate={{ opacity: 1, height: 'auto' }} 
                            exit={{ opacity: 0, height: 0 }}
                            className="grid-cols-3" 
                            style={{ gap: '16px', background: 'var(--bg-base)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)' }}
                          >
                            <div>
                              <div className="text-muted" style={{ fontSize: '0.8rem', marginBottom: '4px' }}>Gross PnL (Brüt)</div>
                              <div className="stat-value" style={{ color: grossPnL >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                                ${grossPnL.toFixed(2)}
                              </div>
                            </div>
                            <div>
                              <div className="text-muted" style={{ fontSize: '0.8rem', marginBottom: '4px' }}>Total Fees Paid (Komisyonlar)</div>
                              <div className="stat-value" style={{ color: 'var(--warning)' }}>
                                -${totalFees.toFixed(2)}
                              </div>
                            </div>
                            <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: '16px' }}>
                              <div className="text-muted" style={{ fontSize: '0.8rem', marginBottom: '4px' }}>Net PnL (Net)</div>
                              <div className="stat-value" style={{ color: netPnL >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                                ${netPnL.toFixed(2)}
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
    </motion.div>
  );
};
