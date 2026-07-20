import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import {
  Terminal, RefreshCw, Filter, Search, Copy, CheckCheck,
  ChevronRight, ChevronDown, Circle, Zap, Shield,
  TrendingUp, Package, CheckCircle, XCircle,
  BarChart2, Clock, Layers, X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// ── Types ──────────────────────────────────────────────────────
interface LogEntry {
  id: number;
  cycle_id: number | null;
  level: string;
  stage: string;
  message: string;
  created_at: string;
  payload: any;
}

// ── Helpers ────────────────────────────────────────────────────
const STAGE_META: Record<string, { icon: React.FC<any>; colorVar: string; label: string }> = {
  INIT:         { icon: Zap,          colorVar: 'var(--accent)', label: 'Init'       },
  STRATEGY:     { icon: TrendingUp,   colorVar: 'var(--purple-400)', label: 'Strategy'   },
  PORTFOLIO:    { icon: Package,      colorVar: 'var(--success)', label: 'Portfolio'  },
  RISK:         { icon: Shield,       colorVar: 'var(--warning)', label: 'Risk'       },
  EXECUTION:    { icon: BarChart2,    colorVar: 'var(--danger)', label: 'Execution'  },
  PAPER_BROKER: { icon: BarChart2,    colorVar: 'var(--danger)', label: 'Broker'     },
  TRAILING_SL:  { icon: TrendingUp,   colorVar: 'var(--warning)', label: 'Trail SL'   },
  COMPLETED:    { icon: CheckCircle,  colorVar: 'var(--success)', label: 'Completed'  },
  FAILED:       { icon: XCircle,      colorVar: 'var(--danger)', label: 'Failed'     },
  MARKET_DATA:  { icon: Layers,       colorVar: 'var(--text-muted)', label: 'Market'     },
};

const LEVEL_CLASS: Record<string, string> = {
  INFO:    'badge-muted',
  SUCCESS: 'badge-success',
  WARN:    'badge-warning',
  WARNING: 'badge-warning',
  ERROR:   'badge-danger',
};

const LEVEL_COLOR: Record<string, string> = {
  INFO:    'var(--text-muted)',
  SUCCESS: 'var(--success)',
  WARN:    'var(--warning)',
  WARNING: 'var(--warning)',
  ERROR:   'var(--danger)',
};

function formatTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleTimeString('tr-TR', { hour12: false });
}

// ── JSON Viewer ───────────────────────────────────────────────
const JsonNode: React.FC<{ data: any; depth?: number; label?: string }> = ({ data, depth = 0, label }) => {
  const [open, setOpen] = useState(depth < 2);
  const indent = depth * 16;

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
        <span className="text-accent">{data}</span>
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
          {open ? <ChevronDown size={14} className="text-muted" /> : <ChevronRight size={14} className="text-muted" />}
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
          {open ? <ChevronDown size={14} className="text-muted" /> : <ChevronRight size={14} className="text-muted" />}
          {label && <span className="text-muted">{label}</span>}
          {!open && <span className="text-muted" style={{ fontSize: '0.75rem' }}>{'{'}{keys.slice(0, 3).join(', ')}{keys.length > 3 ? '...' : ''}{'}'}</span>}
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
        justifyContent: 'center', height: '100%', gap: 12
      }} className="text-muted">
        <Terminal size={40} opacity={0.3} />
        <p style={{ fontSize: '0.9rem' }}>Detay görmek için bir log satırına tıkla</p>
      </div>
    );
  }

  const meta = STAGE_META[log.stage] || { icon: Circle, colorVar: 'var(--text-muted)', label: log.stage };
  const Icon = meta.icon;
  const badgeClass = LEVEL_CLASS[log.level.toUpperCase()] || 'badge-muted';

  return (
    <motion.div
      key={log.id}
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.2 }}
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
            <Icon size={16} color={meta.colorVar} />
            <span style={{ color: meta.colorVar, fontWeight: 600, fontSize: '0.85rem' }} className="mono">
              {log.stage}
            </span>
            <span className={`badge ${badgeClass}`}>
              {log.level}
            </span>
            {log.cycle_id && (
              <span style={{ fontSize: '0.7rem' }} className="text-muted">Cycle #{log.cycle_id}</span>
            )}
          </div>
          <p className="text-primary" style={{ fontSize: '0.9rem', lineHeight: 1.5, margin: 0 }}>
            {log.message}
          </p>
          <p className="text-muted mono" style={{ fontSize: '0.75rem', margin: '8px 0 0' }}>
            {new Date(log.created_at).toLocaleString('tr-TR')}
          </p>
        </div>
        {log.payload && (
          <button onClick={handleCopy} className={copied ? "btn-primary" : "btn-secondary"} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
            {copied ? <CheckCheck size={14} /> : <Copy size={14} />}
            {copied ? 'Kopyalandı' : 'JSON Kopyala'}
          </button>
        )}
      </div>

      {/* JSON Body */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '16px 20px',
        fontSize: '0.85rem', lineHeight: 1.7
      }}>
        {log.payload ? (
          <JsonNode data={log.payload} depth={0} />
        ) : (
          <div className="text-muted" style={{ fontStyle: 'italic' }}>Bu log için ek veri (payload) yok.</div>
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
  const meta = STAGE_META[log.stage] || { icon: Circle, colorVar: 'var(--text-muted)', label: log.stage };
  const Icon = meta.icon;
  const levelColor = LEVEL_COLOR[log.level.toUpperCase()] || 'var(--text-muted)';
  const hasPayload = !!log.payload;

  return (
    <div
      onClick={onClick}
      style={{
        display: 'grid',
        gridTemplateColumns: '75px 100px 1fr 24px',
        gap: 12,
        alignItems: 'center',
        padding: '10px 16px',
        cursor: 'pointer',
        borderLeft: selected ? `3px solid ${meta.colorVar}` : '3px solid transparent',
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
      {/* Time */}
      <span className="text-muted mono" style={{ fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
        {formatTime(log.created_at)}
      </span>

      {/* Stage badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <Icon size={14} color={meta.colorVar} />
        <span className="mono" style={{ color: meta.colorVar, fontSize: '0.75rem', fontWeight: 600 }}>
          {meta.label}
        </span>
      </div>

      {/* Message */}
      <span style={{
        color: levelColor,
        fontSize: '0.85rem',
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {log.message}
      </span>

      {/* Payload indicator */}
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        {hasPayload && (
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: selected ? meta.colorVar : 'var(--border-strong)',
          }} />
        )}
      </div>
    </div>
  );
});

// ── Filter Bar ─────────────────────────────────────────────────
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

      const res = await axios.get(`/api/v1/analytics/logs?${params}`);
      if (res.data?.logs) {
        setLogs(res.data.logs);
        setLiveCount(res.data.count);
        setLastUpdated(new Date().toLocaleTimeString('tr-TR'));
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
      exit={{ opacity: 0 }} 
      style={{ height: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column', gap: 0 }}
    >
      {/* Top bar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 0 20px 0', flexShrink: 0, flexWrap: 'wrap', gap: 12
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ background: 'var(--accent-soft)', padding: '10px', borderRadius: 'var(--radius)' }}>
            <Terminal size={24} className="text-accent" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.5rem', margin: 0, lineHeight: 1.2 }}>Live Logs</h1>
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <button
                onClick={() => setActiveTab('system')}
                className={activeTab === 'system' ? 'btn-primary' : 'btn-ghost'}
                style={{ padding: '6px 14px', fontSize: '0.8rem', borderRadius: '99px' }}
              >
                System Logs
              </button>
              <button
                onClick={() => setActiveTab('debug')}
                className={activeTab === 'debug' ? 'btn-primary' : 'btn-ghost'}
                style={{ padding: '6px 14px', fontSize: '0.8rem', borderRadius: '99px' }}
              >
                Debug Log
              </button>
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem' }} className="text-muted">
            <Clock size={14} />
            <span>{lastUpdated || '—'}</span>
            <span>·</span>
            <span className="text-accent" style={{ fontWeight: 600 }}>{liveCount} log</span>
          </div>
          
          <button
            onClick={() => setAutoScroll(a => !a)}
            className={autoScroll ? 'btn-primary' : 'btn-secondary'}
            style={{ padding: '8px 14px' }}
          >
            <Circle size={10} style={{ fill: autoScroll ? 'currentColor' : 'none' }} />
            Auto-scroll
          </button>
          
          <button
            onClick={handleManualRefresh}
            className="btn-secondary"
            style={{ padding: '8px 14px' }}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Yenile
          </button>
          
          <button
            onClick={async () => {
              if (window.confirm('Tüm geçmiş logları silmek istediğinize emin misiniz?')) {
                setLoading(true);
                try {
                  await axios.delete('/api/v1/analytics/logs');
                  await fetchLogs();
                } catch(e) { console.error(e) }
                setLoading(false);
              }
            }}
            className="btn-danger"
            style={{ padding: '8px 14px' }}
          >
            <X size={14} />
            Temizle
          </button>
        </div>
      </div>
      
      {activeTab === 'debug' && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
          style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16, paddingBottom: '20px' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="text-muted" style={{ fontSize: '0.9rem' }}>
              Aşağıdaki tüm logları kopyalayıp sisteme veya asistana gönderebilirsiniz. Sadece son {logs.length} işlem kaydını içerir.
            </span>
            <button
              onClick={() => {
                navigator.clipboard.writeText(JSON.stringify(logs, null, 2));
                alert("Debug log kopyalandı!");
              }}
              className="btn-primary"
            >
              <Copy size={16} /> Tümünü Kopyala
            </button>
          </div>
          <textarea
            readOnly
            value={JSON.stringify(logs, null, 2)}
            className="form-input mono"
            style={{
              flex: 1, width: '100%', resize: 'none',
              background: 'var(--bg-surface)',
              color: 'var(--success)',
              fontSize: '0.85rem',
            }}
          />
        </motion.div>
      )}

      {activeTab === 'system' && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
          style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}
        >
          {/* Filter Bar */}
          <div style={{
            display: 'flex', gap: 12, alignItems: 'center', padding: '12px 20px',
            background: 'var(--bg-raised)', borderTopLeftRadius: 'var(--radius-lg)', borderTopRightRadius: 'var(--radius-lg)',
            border: '1px solid var(--border)', borderBottom: 'none',
            flexShrink: 0, flexWrap: 'wrap'
          }}>
            <Filter size={16} className="text-muted" />
            <span className="section-label">Filtreler:</span>

            {/* Stage pills */}
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {ALL_STAGES.map(s => {
                const active = filterStage === s;
                return (
                  <button
                    key={s}
                    onClick={() => setFilterStage(active ? '' : s)}
                    className={active ? 'badge badge-primary' : 'badge badge-muted'}
                    style={{ cursor: 'pointer', border: active ? '1px solid var(--accent)' : '1px solid transparent' }}
                  >
                    {s}
                  </button>
                );
              })}
            </div>

            <div style={{ width: 1, height: 20, background: 'var(--border-strong)' }} />

            {/* Level pills */}
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {ALL_LEVELS.map(lv => {
                const active = filterLevel === lv;
                const badgeClass = active ? (LEVEL_CLASS[lv] || 'badge-primary') : 'badge-muted';
                return (
                  <button
                    key={lv}
                    onClick={() => setFilterLevel(active ? '' : lv)}
                    className={`badge ${badgeClass}`}
                    style={{ cursor: 'pointer', border: active ? '1px solid currentColor' : '1px solid transparent' }}
                  >
                    {lv}
                  </button>
                );
              })}
            </div>

            <div style={{ width: 1, height: 20, background: 'var(--border-strong)' }} />

            {/* Symbol search */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, position: 'relative' }}>
              <Search size={14} className="text-muted" style={{ position: 'absolute', left: 10 }} />
              <input
                value={filterSymbol}
                onChange={e => setFilterSymbol(e.target.value)}
                placeholder="Sembol ara..."
                className="form-input mono"
                style={{ paddingLeft: '32px', width: '160px', paddingRight: '28px' }}
              />
              {filterSymbol && (
                <button
                  onClick={() => setFilterSymbol('')}
                  style={{ position: 'absolute', right: 8, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                  className="text-muted"
                >
                  <X size={14} />
                </button>
              )}
            </div>

            {(filterStage || filterLevel || filterSymbol) && (
              <button
                onClick={() => { setFilterStage(''); setFilterLevel(''); setFilterSymbol(''); }}
                className="btn-ghost text-danger"
                style={{ padding: '4px 8px', fontSize: '0.8rem', height: 'auto' }}
              >
                Temizle
              </button>
            )}
          </div>

          {/* Main content: log list + detail panel */}
          <div className="card" style={{
            display: 'grid',
            gridTemplateColumns: '1fr 450px',
            flex: 1,
            overflow: 'hidden',
            borderTopLeftRadius: 0,
            borderTopRightRadius: 0,
          }}>
            {/* Left: Log list */}
            <div
              ref={listRef}
              onScroll={(e) => {
                const target = e.target as HTMLDivElement;
                const isAtBottom = target.scrollHeight - target.scrollTop <= target.clientHeight + 10;
                if (isAtBottom && !autoScroll) {
                  setAutoScroll(true);
                } else if (!isAtBottom && autoScroll) {
                  setAutoScroll(false);
                }
              }}
              style={{ overflowY: 'auto', borderRight: '1px solid var(--border)' }}
            >
              {/* Column header */}
              <div style={{
                display: 'grid', gridTemplateColumns: '75px 100px 1fr 24px',
                gap: 12, padding: '12px 16px',
                borderBottom: '1px solid var(--border-strong)',
                position: 'sticky', top: 0, background: 'var(--bg-surface)', zIndex: 1,
                backdropFilter: 'blur(12px)'
              }}>
                {['Saat', 'Aşama', 'Mesaj', ''].map(h => (
                  <span key={h} className="section-label">
                    {h}
                  </span>
                ))}
              </div>

              {logs.length === 0 ? (
                <div style={{ padding: '80px 20px', textAlign: 'center' }} className="text-muted">
                  <Terminal size={48} opacity={0.2} style={{ marginBottom: 16 }} />
                  <p style={{ fontSize: '0.95rem' }}>Henüz log yok. Bot'u başlatınca burası dolmaya başlar.</p>
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

            {/* Right: Detail panel */}
            <div style={{ overflowY: 'auto', background: 'var(--bg-base)' }}>
              <AnimatePresence mode="wait">
                <DetailPanel key={selectedLog?.id || 'empty'} log={selectedLog} />
              </AnimatePresence>
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
};

export default LiveLogs;
