import React, { useState, useEffect, useRef, useCallback } from 'react';
import { getAnalyticsLogs, deleteAnalyticsLogs } from '../services/api';
import type { LogEntry } from '../types/api';
import {
  Terminal, RefreshCw, Filter, Search, Copy, CheckCheck,
  ChevronRight, ChevronDown, Circle,
  Clock, X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// ── Helpers ────────────────────────────────────────────────────
const STAGE_META: Record<string, { label: string }> = {
  INIT:         { label: 'Init'       },
  STRATEGY:     { label: 'Strategy'   },
  PORTFOLIO:    { label: 'Portfolio'  },
  RISK:         { label: 'Risk'       },
  EXECUTION:    { label: 'Execution'  },
  PAPER_BROKER: { label: 'Broker'     },
  TRAILING_SL:  { label: 'Trail SL'   },
  COMPLETED:    { label: 'Completed'  },
  FAILED:       { label: 'Failed'     },
  MARKET_DATA:  { label: 'Market'     },
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
    return d.toLocaleTimeString('en-US', { hour12: false });
  } catch (e) {
    return iso;
  }
}

// ── Interactive JSON Tree Viewer ───────────────────────────────
const JsonNode: React.FC<{ data: any; depth?: number; label?: string }> = ({ data, depth = 0, label }) => {
  const [open, setOpen] = useState(depth < 2);
  const indent = depth * 14;

  if (data === null || data === undefined) {
    return (
      <div style={{ paddingLeft: indent }} className="mono">
        {label && <span className="text-muted">{label}: </span>}
        <span className="text-danger">null</span>
      </div>
    );
  }

  if (typeof data === 'boolean') {
    return (
      <div style={{ paddingLeft: indent }} className="mono">
        {label && <span className="text-muted">{label}: </span>}
        <span className="text-warning">{String(data)}</span>
      </div>
    );
  }

  if (typeof data === 'number') {
    return (
      <div style={{ paddingLeft: indent }} className="mono">
        {label && <span className="text-muted">{label}: </span>}
        <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{data}</span>
      </div>
    );
  }

  if (typeof data === 'string') {
    return (
      <div style={{ paddingLeft: indent }} className="mono">
        {label && <span className="text-muted">{label}: </span>}
        <span className="text-success">"{data}"</span>
      </div>
    );
  }

  if (Array.isArray(data)) {
    if (data.length === 0) {
      return (
        <div style={{ paddingLeft: indent }} className="mono">
          {label && <span className="text-muted">{label}: </span>}
          <span className="text-muted">[]</span>
        </div>
      );
    }
    return (
      <div style={{ paddingLeft: indent }} className="mono">
        <div
          onClick={() => setOpen(o => !o)}
          style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, userSelect: 'none' }}
        >
          {open ? <ChevronDown size={13} className="text-muted" /> : <ChevronRight size={13} className="text-muted" />}
          {label && <span className="text-muted">{label}</span>}
          <span className="text-muted">[{data.length}]</span>
        </div>
        <AnimatePresence>
          {open && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} style={{ overflow: 'hidden' }}>
              {data.map((item, i) => (
                <JsonNode key={i} data={item} depth={depth + 1} label={String(i)} />
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }

  if (typeof data === 'object') {
    const keys = Object.keys(data);
    if (keys.length === 0) {
      return (
        <div style={{ paddingLeft: indent }} className="mono">
          {label && <span className="text-muted">{label}: </span>}
          <span className="text-muted">{'{}'}</span>
        </div>
      );
    }
    return (
      <div style={{ paddingLeft: indent }} className="mono">
        <div
          onClick={() => setOpen(o => !o)}
          style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, userSelect: 'none' }}
        >
          {open ? <ChevronDown size={13} className="text-muted" /> : <ChevronRight size={13} className="text-muted" />}
          {label && <span className="text-muted">{label}</span>}
          {!open && <span className="text-muted" style={{ fontSize: '0.75rem' }}>{'{'}{keys.slice(0, 3).join(', ')}{keys.length > 3 ? '…' : ''}{'}'}</span>}
        </div>
        <AnimatePresence>
          {open && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} style={{ overflow: 'hidden' }}>
              {keys.map(key => (
                <JsonNode key={key} data={data[key]} depth={depth + 1} label={key} />
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }

  return <div style={{ paddingLeft: indent }} className="mono">{String(data)}</div>;
};

// ── Detail Panel ───────────────────────────────────────────────
const DetailPanel: React.FC<{ log: LogEntry | null }> = ({ log }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    if (!log?.payload) return;
    navigator.clipboard.writeText(JSON.stringify(log.payload, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [log]);

  if (!log) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', height: '100%', gap: 12, padding: 32, textAlign: 'center'
      }} className="text-muted">
        <Terminal size={40} opacity={0.25} />
        <p style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
          Detail Inspector
        </p>
        <p style={{ fontSize: '0.8rem', maxWidth: 280, margin: 0 }}>
          Select any log entry from the stream to inspect its execution context, state, and payload.
        </p>
      </div>
    );
  }

  const meta = STAGE_META[log.stage] || { label: log.stage };
  const badgeClass = `badge-${log.level.toLowerCase() === 'error' ? 'danger' : log.level.toLowerCase() === 'success' ? 'success' : log.level.toLowerCase().includes('warn') ? 'warning' : 'primary'}`;

  return (
    <motion.div
      key={log.id}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.15 }}
      style={{ display: 'flex', flexDirection: 'column', height: '100%' }}
    >
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ color: 'var(--text-primary)', fontWeight: 700, fontSize: '0.82rem' }} className="mono">
              [{meta.label}]
            </span>
            <span className={`badge ${badgeClass}`} style={{ fontSize: '0.68rem' }}>
              {log.level}
            </span>
            {log.cycle_id && (
              <span style={{ fontSize: '0.7rem' }} className="text-muted mono">Cycle #{log.cycle_id}</span>
            )}
          </div>
          <p className="text-primary" style={{ fontSize: '0.85rem', lineHeight: 1.4, margin: 0, fontWeight: 500 }}>
            {log.message}
          </p>
          <p className="text-muted mono" style={{ fontSize: '0.72rem', margin: '6px 0 0' }}>
            {new Date(log.created_at).toLocaleString('en-US')}
          </p>
        </div>
        {log.payload && (
          <button onClick={handleCopy} className="btn-secondary" style={{ padding: '5px 10px', fontSize: '0.75rem' }}>
            {copied ? <CheckCheck size={13} /> : <Copy size={13} />}
            {copied ? 'Copied' : 'Copy JSON'}
          </button>
        )}
      </div>

      {/* JSON Tree View */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '16px 20px',
        fontSize: '0.82rem', lineHeight: 1.6
      }}>
        {log.payload ? (
          <JsonNode data={log.payload} depth={0} />
        ) : (
          <div className="text-muted" style={{ fontStyle: 'italic', fontSize: '0.8rem' }}>No additional payload data for this execution step.</div>
        )}
      </div>
    </motion.div>
  );
};

// ── Log Row ────────────────────────────────────────────────────
const LogRow: React.FC<{
  log: LogEntry;
  selected: boolean;
  onClick: () => void;
}> = React.memo(({ log, selected, onClick }) => {
  const meta = STAGE_META[log.stage] || { label: log.stage };
  const levelColor = LEVEL_COLOR[log.level.toUpperCase()] || 'var(--text-muted)';
  const hasPayload = !!log.payload;

  return (
    <div
      onClick={onClick}
      style={{
        display: 'grid',
        gridTemplateColumns: '75px 95px 1fr 20px',
        gap: 12,
        alignItems: 'center',
        padding: '9px 16px',
        cursor: 'pointer',
        borderLeft: selected ? '3px solid var(--text-primary)' : '3px solid transparent',
        background: selected ? 'var(--accent-soft)' : 'transparent',
        transition: 'all 0.15s',
        borderBottom: '1px solid var(--border)'
      }}
      onMouseEnter={e => {
        if (!selected) (e.currentTarget as HTMLDivElement).style.background = 'var(--bg-raised)';
      }}
      onMouseLeave={e => {
        if (!selected) (e.currentTarget as HTMLDivElement).style.background = 'transparent';
      }}
    >
      <span className="text-muted mono" style={{ fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
        {formatTime(log.created_at)}
      </span>

      <span className="mono" style={{ color: 'var(--text-primary)', fontSize: '0.75rem', fontWeight: 600 }}>
        {meta.label}
      </span>

      <span style={{
        color: levelColor,
        fontSize: '0.82rem',
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {log.message}
      </span>

      <div style={{ display: 'flex', justifyContent: 'center' }}>
        {hasPayload && (
          <div style={{
            width: 6, height: 6, borderRadius: '50%',
            background: selected ? 'var(--text-primary)' : 'var(--border-strong)',
          }} />
        )}
      </div>
    </div>
  );
});

// ── Filter Constants ───────────────────────────────────────────
const ALL_STAGES = ['INIT', 'STRATEGY', 'PORTFOLIO', 'RISK', 'PAPER_BROKER', 'TRAILING_SL', 'COMPLETED', 'FAILED'];
const ALL_LEVELS = ['INFO', 'SUCCESS', 'WARN', 'ERROR'];

// ── Main Page ──────────────────────────────────────────────────
const LiveLogs: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'system' | 'debug'>('system');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [loading, setLoading] = useState(false);
  const [filterStage, setFilterStage] = useState<string>('');
  const [filterLevel, setFilterLevel] = useState<string>('');
  const [filterSymbol, setFilterSymbol] = useState<string>('');
  const [liveCount, setLiveCount] = useState(0);
  const [lastUpdated, setLastUpdated] = useState<string>('');
  const logsEndRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const fetchLogs = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: '300' });
      if (filterStage) params.set('stage', filterStage);
      if (filterLevel) params.set('level', filterLevel);
      if (filterSymbol) params.set('symbol', filterSymbol);

      const res = await getAnalyticsLogs(params);
      if (res.data?.logs) {
        setLogs(res.data.logs);
        setLiveCount(res.data.count);
        setLastUpdated(new Date().toLocaleTimeString('en-US'));
        setSelectedLog(prev => prev || (res.data.logs.length > 0 ? res.data.logs[0] : null));
      }
    } catch (err) {
      console.error('Error fetching logs:', err);
    }
  }, [filterStage, filterLevel, filterSymbol]);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 3000);
    return () => clearInterval(interval);
  }, [fetchLogs]);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const handleManualRefresh = async () => {
    setLoading(true);
    await fetchLogs();
    setLoading(false);
  };

  return (
    <motion.div 
      initial={{ opacity: 0 }} 
      animate={{ opacity: 1 }} 
      style={{ minHeight: 'calc(100vh - 160px)', height: '820px', display: 'flex', flexDirection: 'column', gap: 0 }}
    >
      {/* Top Header & Actions */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 0 18px 0', flexShrink: 0, flexWrap: 'wrap', gap: 12
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ background: 'var(--accent-soft)', border: '1px solid var(--accent-border)', padding: '8px', borderRadius: 'var(--radius-sm)' }}>
            <Terminal size={20} color="var(--text-primary)" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.4rem', margin: 0 }}>System Logs</h1>
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button
                onClick={() => setActiveTab('system')}
                className={activeTab === 'system' ? 'btn-primary' : 'btn-ghost'}
                style={{ padding: '4px 12px', fontSize: '0.75rem', borderRadius: 'var(--radius-full)' }}
              >
                System Log Stream
              </button>
              <button
                onClick={() => setActiveTab('debug')}
                className={activeTab === 'debug' ? 'btn-primary' : 'btn-ghost'}
                style={{ padding: '4px 12px', fontSize: '0.75rem', borderRadius: 'var(--radius-full)' }}
              >
                Raw JSON Debug
              </button>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem' }} className="text-muted mono">
            <Clock size={13} />
            <span>{lastUpdated || '—'}</span>
            <span>·</span>
            <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{liveCount} entries</span>
          </div>
          
          <button
            onClick={() => setAutoScroll(a => !a)}
            className={autoScroll ? 'btn-primary' : 'btn-secondary'}
            style={{ padding: '6px 12px', fontSize: '0.75rem' }}
          >
            <Circle size={8} style={{ fill: autoScroll ? 'currentColor' : 'none' }} />
            Auto-scroll
          </button>
          
          <button
            onClick={handleManualRefresh}
            className="btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.75rem' }}
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          
          <button
            onClick={async () => {
              if (window.confirm('Are you sure you want to clear all execution log history?')) {
                setLoading(true);
                try {
                  await deleteAnalyticsLogs();
                  await fetchLogs();
                } catch(e) { console.error(e) }
                setLoading(false);
              }
            }}
            className="btn-danger"
            style={{ padding: '6px 12px', fontSize: '0.75rem' }}
          >
            <X size={13} />
            Clear Logs
          </button>
        </div>
      </div>
      
      {/* Raw Debug View */}
      {activeTab === 'debug' && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="text-muted" style={{ fontSize: '0.82rem' }}>
              Raw JSON execution logs (Last {logs.length} entries). Copy for diagnostics and auditing.
            </span>
            <button
              onClick={() => {
                navigator.clipboard.writeText(JSON.stringify(logs, null, 2));
                alert("Debug logs copied to clipboard!");
              }}
              className="btn-primary"
              style={{ fontSize: '0.8rem' }}
            >
              <Copy size={14} /> Copy All
            </button>
          </div>
          <textarea
            readOnly
            value={JSON.stringify(logs, null, 2)}
            className="form-input mono"
            style={{
              flex: 1, width: '100%', resize: 'none',
              background: 'var(--bg-base)',
              color: 'var(--text-secondary)',
              fontSize: '0.8rem',
            }}
          />
        </div>
      )}

      {/* System Stream Split View */}
      {activeTab === 'system' && (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
          
          {/* Filter Bar */}
          <div style={{
            display: 'flex', gap: 10, alignItems: 'center', padding: '10px 18px',
            background: 'var(--bg-raised)', borderTopLeftRadius: 'var(--radius)', borderTopRightRadius: 'var(--radius)',
            border: '1px solid var(--border)', borderBottom: 'none',
            flexShrink: 0, flexWrap: 'wrap'
          }}>
            <Filter size={14} className="text-muted" />
            <span className="section-label" style={{ fontSize: '0.65rem' }}>Filters:</span>

            {/* Stages */}
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {ALL_STAGES.map(s => {
                const active = filterStage === s;
                return (
                  <button
                    key={s}
                    onClick={() => setFilterStage(active ? '' : s)}
                    className={active ? 'badge badge-primary' : 'badge badge-muted'}
                    style={{ cursor: 'pointer', fontSize: '0.68rem', border: active ? '1px solid var(--text-primary)' : '1px solid transparent' }}
                  >
                    {s}
                  </button>
                );
              })}
            </div>

            <div style={{ width: 1, height: 16, background: 'var(--border)' }} />

            {/* Levels */}
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {ALL_LEVELS.map(lv => {
                const active = filterLevel === lv;
                return (
                  <button
                    key={lv}
                    onClick={() => setFilterLevel(active ? '' : lv)}
                    className={active ? 'badge badge-primary' : 'badge badge-muted'}
                    style={{ cursor: 'pointer', fontSize: '0.68rem' }}
                  >
                    {lv}
                  </button>
                );
              })}
            </div>

            <div style={{ width: 1, height: 16, background: 'var(--border)' }} />

            {/* Symbol search */}
            <div style={{ display: 'flex', alignItems: 'center', position: 'relative' }}>
              <Search size={13} className="text-muted" style={{ position: 'absolute', left: 8 }} />
              <input
                value={filterSymbol}
                onChange={e => setFilterSymbol(e.target.value)}
                placeholder="Search symbol..."
                className="form-input mono"
                style={{ paddingLeft: '28px', width: '140px', height: '28px', fontSize: '0.75rem' }}
              />
              {filterSymbol && (
                <button
                  onClick={() => setFilterSymbol('')}
                  style={{ position: 'absolute', right: 6, background: 'none', border: 'none', cursor: 'pointer' }}
                  className="text-muted"
                >
                  <X size={12} />
                </button>
              )}
            </div>
          </div>

          {/* Split Content Box */}
          <div className="card" style={{
            display: 'grid',
            gridTemplateColumns: '1fr 420px',
            flex: 1,
            overflow: 'hidden',
            borderTopLeftRadius: 0,
            borderTopRightRadius: 0,
          }}>
            
            {/* Left Stream */}
            <div
              ref={listRef}
              onScroll={(e) => {
                const target = e.target as HTMLDivElement;
                const isAtBottom = target.scrollHeight - target.scrollTop <= target.clientHeight + 10;
                if (isAtBottom && !autoScroll) setAutoScroll(true);
                else if (!isAtBottom && autoScroll) setAutoScroll(false);
              }}
              style={{ overflowY: 'auto', borderRight: '1px solid var(--border)' }}
            >
              <div style={{
                display: 'grid', gridTemplateColumns: '75px 95px 1fr 20px',
                gap: 12, padding: '10px 16px',
                borderBottom: '1px solid var(--border)',
                position: 'sticky', top: 0, background: 'var(--bg-surface)', zIndex: 1,
                backdropFilter: 'blur(12px)'
              }}>
                {['Time', 'Stage', 'Message', ''].map(h => (
                  <span key={h} className="section-label" style={{ fontSize: '0.65rem' }}>
                    {h}
                  </span>
                ))}
              </div>

              {logs.length === 0 ? (
                <div style={{ padding: '80px 20px', textAlign: 'center' }} className="text-muted">
                  <Terminal size={40} opacity={0.2} style={{ marginBottom: 14 }} />
                  <p style={{ fontSize: '0.85rem' }}>No execution logs found.</p>
                </div>
              ) : (
                logs.map(log => (
                  <LogRow
                    key={log.id}
                    log={log}
                    selected={selectedLog?.id === log.id}
                    onClick={() => setSelectedLog(prev => prev?.id === log.id ? null : log)}
                  />
                ))
              )}
              <div ref={logsEndRef} />
            </div>

            {/* Right Details Panel */}
            <div style={{ overflowY: 'auto', background: 'var(--bg-base)' }}>
              <AnimatePresence mode="wait">
                <DetailPanel key={selectedLog?.id || 'empty'} log={selectedLog} />
              </AnimatePresence>
            </div>

          </div>
        </div>
      )}
    </motion.div>
  );
};

export default LiveLogs;
