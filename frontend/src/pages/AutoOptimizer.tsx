import React, { useEffect, useState } from 'react';

interface OptimizationRun {
  id: number;
  status: string;
  triggered_by: string;
  strategy_name: string;
  lookback_months: number;
  best_params_json: Record<string, number> | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export const AutoOptimizer: React.FC = () => {
  const [history, setHistory] = useState<OptimizationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/v1/optimization/history');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) setHistory(data);
      }
    } catch (e) {} finally { setLoading(false); }
  };

  useEffect(() => {
    fetchHistory(); const interval = setInterval(fetchHistory, 10000); return () => clearInterval(interval);
  }, []);

  const handleForceOptimize = async () => {
    if (history.some(h => h.status === 'RUNNING') && !window.confirm("A RUNNING process exists. Force trigger?")) return;
    if (!window.confirm("Trigger heavy Optuna process?")) return;
    setTriggering(true);
    try {
      const res = await fetch('/api/v1/optimization/force', { method: 'POST' });
      if (res.ok) { alert("Triggered!"); await fetchHistory(); }
    } catch (e) {} finally { setTriggering(false); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      
      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '1px solid var(--border)', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '1.5rem', marginBottom: '8px' }}>[AUTO_OPTIMIZER]</h1>
          <p style={{ margin: 0, fontSize: '0.85rem' }}>AI hyperparameter tuning engine</p>
        </div>
        <button onClick={handleForceOptimize} disabled={triggering} className="btn-primary">
          {triggering ? "TRIGGERING..." : "FORCE_OPTIMIZE"}
        </button>
      </div>

      {/* ── Instructions ── */}
      <div style={{ border: '1px solid var(--border)', padding: '20px', background: 'var(--bg-raised)', fontFamily: '"JetBrains Mono", monospace', fontSize: '0.8rem', lineHeight: '1.6' }}>
        <div style={{ color: 'var(--accent)', marginBottom: '8px', fontWeight: 600 }}>&gt; SYSTEM_INFO</div>
        <div style={{ color: 'var(--text-muted)' }}>
          - ML engine constantly evaluates best (TP/SL) parameters.<br/>
          - Runs asynchronously via Optuna.<br/>
          - Best parameters automatically applied to active bots.
        </div>
      </div>

      {/* ── History Table ── */}
      <div>
        <h3 style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '1rem', marginBottom: '16px' }}>&gt; OPTIMIZATION_RUNS</h3>
        <table className="glass-table">
          <thead>
            <tr style={{ background: '#050505' }}>
              <th>ID</th>
              <th>TIMESTAMP</th>
              <th>TRIGGER</th>
              <th>LOOKBACK</th>
              <th>STATUS</th>
              <th>BEST_PARAMS</th>
            </tr>
          </thead>
          <tbody>
            {loading && history.length === 0 ? (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>[ LOADING ]</td></tr>
            ) : history.length === 0 ? (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>[ NO DATA ]</td></tr>
            ) : history.map(run => (
              <tr key={run.id}>
                <td style={{ color: 'var(--text-muted)' }}>#{run.id}</td>
                <td>{new Date(run.created_at).toLocaleString('en-US', { hour12: false })}</td>
                <td><span style={{ color: 'var(--accent)' }}>{run.triggered_by}</span></td>
                <td>{run.lookback_months}m</td>
                <td style={{ color: run.status === 'COMPLETED' ? 'var(--success)' : run.status === 'RUNNING' ? 'var(--warning)' : 'var(--danger)' }}>
                  [{run.status}]
                </td>
                <td>
                  {(() => {
                    let p = run.best_params_json;
                    if (typeof p === 'string') { try { p = JSON.parse(p); } catch { p = null; } }
                    if (p && typeof p === 'object') {
                      return (
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                          {Object.entries(p).map(([k, v]) => (
                            <span key={k}>
                              <span style={{ fontSize: '0.75rem', background: 'var(--bg-raised)', border: '1px solid var(--border-strong)', padding: '2px 6px', borderRadius: '4px' }}>
                                <span style={{ color: 'var(--text-muted)' }}>{k}:</span> <span style={{ color: 'var(--accent)' }}>{String(v)}</span>
                              </span>
                              {' '}
                            </span>
                          ))}
                        </div>
                      );
                    }
                    return <span style={{ color: 'var(--text-muted)' }}>-</span>;
                  })()}
                  {run.error_message && <div style={{ color: 'var(--danger)', fontSize: '0.75rem', marginTop: '4px' }}>ERR: {run.error_message}</div>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  );
};
