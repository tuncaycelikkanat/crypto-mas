import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';
import { ArrowRight, Trash2 } from 'lucide-react';

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
  total_trades: number | null;
  win_rate: number | null;
  max_drawdown: number | null;
  config_json: BacktestConfig | null;
}

export const BacktestHistory: React.FC = () => {
  const [jobs, setJobs] = useState<BacktestJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [compareData, setCompareData] = useState<Record<string, any[]>>({});
  const [compareMode, setCompareMode] = useState(false);

  const fetchJobs = async () => {
    try {
      setLoading(true);
      const res = await axios.get('/api/v1/backtest');
      // Only completed or failed jobs
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
      <div className="glass-card" style={{ padding: '24px' }}>
        <button onClick={() => setCompareMode(false)} className="btn primary" style={{ marginBottom: '16px' }}>
          &larr; Back to History
        </button>
        <h2 style={{ marginBottom: '24px' }}>Compare Tests</h2>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          {/* Card A */}
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
            <h3 style={{ color: '#a78bfa' }}>Test A: {jobA?.strategy_name}</h3>
            <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '12px' }}>{jobA?.job_id}</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
              <div><strong>Win Rate:</strong> {((jobA?.win_rate || 0) * 100).toFixed(1)}%</div>
              <div><strong>Drawdown:</strong> {((jobA?.max_drawdown || 0) * 100).toFixed(1)}%</div>
              <div><strong>Final Equity:</strong> ${jobA?.final_equity?.toFixed(2)}</div>
              <div><strong>Total Trades:</strong> {jobA?.total_trades}</div>
              <div style={{ gridColumn: 'span 2' }}>
                <strong>Config:</strong> Risk {jobA?.config_json?.risk_level} 
                | BTC {jobA?.config_json?.use_btc_shield ? 'On' : 'Off'} 
                | Regime {jobA?.config_json?.use_regime_shield ? 'On' : 'Off'}
              </div>
            </div>
            
            <div style={{ height: '300px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={compareData[jobA!.job_id] || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="time" hide />
                  <YAxis domain={['auto', 'auto']} stroke="#94a3b8" />
                  <RechartsTooltip contentStyle={{ background: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }} />
                  <Line type="monotone" dataKey="equity" stroke="#a78bfa" strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Card B */}
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
            <h3 style={{ color: '#34d399' }}>Test B: {jobB?.strategy_name}</h3>
            <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '12px' }}>{jobB?.job_id}</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
              <div><strong>Win Rate:</strong> {((jobB?.win_rate || 0) * 100).toFixed(1)}%</div>
              <div><strong>Drawdown:</strong> {((jobB?.max_drawdown || 0) * 100).toFixed(1)}%</div>
              <div><strong>Final Equity:</strong> ${jobB?.final_equity?.toFixed(2)}</div>
              <div><strong>Trades:</strong> {jobB?.total_trades}</div>
              <div style={{ gridColumn: 'span 2' }}>
                <strong>Config:</strong> Risk {jobB?.config_json?.risk_level} 
                | BTC {jobB?.config_json?.use_btc_shield ? 'On' : 'Off'} 
                | Regime {jobB?.config_json?.use_regime_shield ? 'On' : 'Off'}
              </div>
            </div>

            <div style={{ height: '300px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={compareData[jobB!.job_id] || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="time" hide />
                  <YAxis domain={['auto', 'auto']} stroke="#94a3b8" />
                  <RechartsTooltip contentStyle={{ background: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }} />
                  <Line type="monotone" dataKey="equity" stroke="#34d399" strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card" style={{ padding: '24px' }}>
      <div className="flex-between" style={{ marginBottom: '24px' }}>
        <h2>Test History</h2>
        <div>
          <button 
            onClick={handleCompare}
            disabled={selectedIds.length !== 2}
            className={`btn ${selectedIds.length === 2 ? 'primary' : 'secondary'}`}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '8px',
              opacity: selectedIds.length === 2 ? 1 : 0.4,
              cursor: selectedIds.length === 2 ? 'pointer' : 'not-allowed',
              transition: 'all 0.2s ease'
            }}
          >
            <ArrowRight size={16} /> Compare Selected ({selectedIds.length}/2)
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>Loading history...</div>
      ) : jobs.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>No past backtests found.</div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8' }}>
              <th style={{ padding: '12px' }}>Select</th>
              <th style={{ padding: '12px' }}>Date</th>
              <th style={{ padding: '12px' }}>Strategy</th>
              <th style={{ padding: '12px' }}>Risk</th>
              <th style={{ padding: '12px' }}>PnL</th>
              <th style={{ padding: '12px' }}>Win Rate</th>
              <th style={{ padding: '12px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.job_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: selectedIds.includes(job.job_id) ? 'rgba(139, 92, 246, 0.1)' : 'transparent' }}>
                <td style={{ padding: '12px' }}>
                  <input 
                    type="checkbox" 
                    checked={selectedIds.includes(job.job_id)} 
                    onChange={() => toggleSelect(job.job_id)}
                    style={{ cursor: 'pointer' }}
                  />
                </td>
                <td style={{ padding: '12px', fontSize: '0.85rem' }}>
                  {new Date(job.start_time).toLocaleDateString()} - {new Date(job.end_time).toLocaleDateString()}
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{job.symbols.join(', ')}</div>
                </td>
                <td style={{ padding: '12px' }}>{job.strategy_name}</td>
                <td style={{ padding: '12px' }}>
                  {job.config_json?.risk_level ?? '-'}
                </td>
                <td style={{ padding: '12px', color: (job.final_equity || 0) >= (job.initial_balance || 0) ? '#10b981' : '#ef4444' }}>
                  ${( (job.final_equity || 0) - (job.initial_balance || 0) ).toFixed(2)}
                </td>
                <td style={{ padding: '12px' }}>
                  {((job.win_rate || 0) * 100).toFixed(1)}%
                </td>
                <td style={{ padding: '12px' }}>
                  <button 
                    onClick={() => handleDelete(job.job_id)}
                    style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '4px', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                    title="Sil"
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
