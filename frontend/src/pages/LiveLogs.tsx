import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import {
  Terminal, RefreshCw, Filter, Search, Copy, CheckCheck,
  ChevronRight, ChevronDown, Circle, Zap, Shield,
  TrendingUp, Package, AlertTriangle, CheckCircle, XCircle,
  BarChart2, Clock, Layers, X
} from 'lucide-react';

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
const STAGE_META: Record<string, { icon: React.FC<any>; color: string; label: string }> = {
  INIT:       { icon: Zap,          color: '#60a5fa', label: 'Init'       },
  STRATEGY:   { icon: TrendingUp,   color: '#a78bfa', label: 'Strategy'   },
  PORTFOLIO:  { icon: Package,      color: '#34d399', label: 'Portfolio'  },
  RISK:       { icon: Shield,       color: '#fbbf24', label: 'Risk'       },
  EXECUTION:  { icon: BarChart2,    color: '#f472b6', label: 'Execution'  },
  PAPER_BROKER:{ icon: BarChart2,   color: '#f472b6', label: 'Broker'     },
  TRAILING_SL:{ icon: TrendingUp,   color: '#fb923c', label: 'Trail SL'   },
  COMPLETED:  { icon: CheckCircle,  color: '#10b981', label: 'Completed'  },
  FAILED:     { icon: XCircle,      color: '#ef4444', label: 'Failed'     },
  MARKET_DATA:{ icon: Layers,       color: '#94a3b8', label: 'Market'     },
};

const LEVEL_COLOR: Record<string, string> = {
  INFO:    '#94a3b8',
  SUCCESS: '#10b981',
  WARN:    '#fbbf24',
  WARNING: '#fbbf24',
  ERROR:   '#ef4444',
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
      <div style={{ paddingLeft: indent }}>
        {label && <span style={{ color: '#94a3b8' }}>{label}: </span>}
        <span style={{ color: '#ef4444' }}>null</span>
      </div>
    );
  }

  if (typeof data === 'boolean') {
    return (
      <div style={{ paddingLeft: indent }}>
        {label && <span style={{ color: '#94a3b8' }}>{label}: </span>}
        <span style={{ color: '#fb923c' }}>{String(data)}</span>
      </div>
    );
  }

  if (typeof data === 'number') {
    return (
      <div style={{ paddingLeft: indent }}>
        {label && <span style={{ color: '#94a3b8' }}>{label}: </span>}
        <span style={{ color: '#60a5fa' }}>{data}</span>
      </div>
    );
  }

  if (typeof data === 'string') {
    return (
      <div style={{ paddingLeft: indent }}>
        {label && <span style={{ color: '#94a3b8' }}>{label}: </span>}
        <span style={{ color: '#34d399' }}>"{data}"</span>
      </div>
    );
  }

  if (Array.isArray(data)) {
    if (data.length === 0) {
      return (
        <div style={{ paddingLeft: indent }}>
          {label && <span style={{ color: '#94a3b8' }}>{label}: </span>}
          <span style={{ color: '#94a3b8' }}>[]</span>
        </div>
      );
    }
    return (
      <div style={{ paddingLeft: indent }}>
        <div
          onClick={() => setOpen(o => !o)}
          style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, userSelect: 'none' }}
        >
          {open ? <ChevronDown size={12} color="#94a3b8" /> : <ChevronRight size={12} color="#94a3b8" />}
          {label && <span style={{ color: '#94a3b8' }}>{label}</span>}
          <span style={{ color: '#94a3b8' }}>[{data.length}]</span>
        </div>
        {open && data.map((item, i) => (
          <JsonNode key={i} data={item} depth={depth + 1} label={String(i)} />
        ))}
      </div>
    );
  }

  if (typeof data === 'object') {
    const keys = Object.keys(data);
    if (keys.length === 0) {
      return (
        <div style={{ paddingLeft: indent }}>
          {label && <span style={{ color: '#94a3b8' }}>{label}: </span>}
          <span style={{ color: '#94a3b8' }}>{'{}'}</span>
        </div>
      );
    }
    return (
      <div style={{ paddingLeft: indent }}>
        <div
          onClick={() => setOpen(o => !o)}
          style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, userSelect: 'none' }}
        >
          {open ? <ChevronDown size={12} color="#94a3b8" /> : <ChevronRight size={12} color="#94a3b8" />}
          {label && <span style={{ color: '#94a3b8' }}>{label}</span>}
          {!open && <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>{'{'}{keys.slice(0, 3).join(', ')}{keys.length > 3 ? '...' : ''}{'}'}</span>}
        </div>
        {open && keys.map(key => (
          <JsonNode key={key} data={data[key]} depth={depth + 1} label={key} />
        ))}
      </div>
    );
  }

  return <div style={{ paddingLeft: indent }}>{String(data)}</div>;
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
        justifyContent: 'center', height: '100%', gap: 12, color: 'var(--text-muted)'
      }}>
        <Terminal size={40} opacity={0.3} />
        <p style={{ fontSize: '0.9rem' }}>Detay görmek için bir log satırına tıkla</p>
      </div>
    );
  }

  const meta = STAGE_META[log.stage] || { icon: Circle, color: '#94a3b8', label: log.stage };
  const Icon = meta.icon;
  const levelColor = LEVEL_COLOR[log.level.toUpperCase()] || '#94a3b8';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <Icon size={16} color={meta.color} />
            <span style={{ color: meta.color, fontWeight: 600, fontSize: '0.85rem', fontFamily: 'monospace' }}>
              {log.stage}
            </span>
            <span style={{
              fontSize: '0.7rem', padding: '2px 8px', borderRadius: 4,
              background: levelColor + '22', color: levelColor, fontWeight: 600
            }}>
              {log.level}
            </span>
            {log.cycle_id && (
              <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Cycle #{log.cycle_id}</span>
            )}
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-main)', lineHeight: 1.5, margin: 0 }}>
            {log.message}
          </p>
          <p style={{ fontSize: '0.75rem', color: '#64748b', margin: '6px 0 0', fontFamily: 'monospace' }}>
            {new Date(log.created_at).toLocaleString('tr-TR')}
          </p>
        </div>
        {log.payload && (
          <button
            onClick={handleCopy}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
              color: copied ? '#10b981' : 'var(--text-muted)',
              padding: '6px 12px', borderRadius: 6, cursor: 'pointer',
              fontSize: '0.8rem', whiteSpace: 'nowrap', flexShrink: 0,
              transition: 'all 0.2s'
            }}
          >
            {copied ? <CheckCheck size={14} /> : <Copy size={14} />}
            {copied ? 'Kopyalandı' : 'JSON Kopyala'}
          </button>
        )}
      </div>

      {/* JSON Body */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '16px 20px',
        fontFamily: '"Fira Code", "JetBrains Mono", monospace', fontSize: '0.82rem', lineHeight: 1.7
      }}>
        {log.payload ? (
          <JsonNode data={log.payload} depth={0} />
        ) : (
          <div style={{ color: '#64748b', fontStyle: 'italic' }}>Bu log için ek veri (payload) yok.</div>
        )}
      </div>
    </div>
  );
};

// ── Log Row ────────────────────────────────────────────────────
const LogRow: React.FC<{
  log: LogEntry;
  selected: boolean;
  onClick: () => void;
}> = React.memo(({ log, selected, onClick }) => {
  const meta = STAGE_META[log.stage] || { icon: Circle, color: '#94a3b8', label: log.stage };
  const Icon = meta.icon;
  const levelColor = LEVEL_COLOR[log.level.toUpperCase()] || '#94a3b8';
  const hasPayload = !!log.payload;

  return (
    <div
      onClick={onClick}
      style={{
        display: 'grid',
        gridTemplateColumns: '70px 90px 1fr 24px',
        gap: 8,
        alignItems: 'center',
        padding: '6px 12px',
        cursor: 'pointer',
        borderLeft: selected ? `2px solid ${meta.color}` : '2px solid transparent',
        background: selected ? 'rgba(139,92,246,0.08)' : 'transparent',
        transition: 'background 0.1s',
      }}
      onMouseEnter={e => {
        if (!selected) (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.03)';
      }}
      onMouseLeave={e => {
        if (!selected) (e.currentTarget as HTMLDivElement).style.background = 'transparent';
      }}
    >
      {/* Time */}
      <span style={{ color: '#475569', fontSize: '0.75rem', fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
        {formatTime(log.created_at)}
      </span>

      {/* Stage badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
        <Icon size={11} color={meta.color} />
        <span style={{ color: meta.color, fontSize: '0.72rem', fontFamily: 'monospace', fontWeight: 600 }}>
          {meta.label}
        </span>
      </div>

      {/* Message */}
      <span style={{
        color: levelColor,
        fontSize: '0.8rem',
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {log.message}
      </span>

      {/* Payload indicator */}
      <div>
        {hasPayload && (
          <div style={{
            width: 7, height: 7, borderRadius: '50%',
            background: selected ? meta.color : '#334155',
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
    <div style={{ height: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column', gap: 0 }}>

      {/* Top bar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 0 20px 0', flexShrink: 0, flexWrap: 'wrap', gap: 12
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Terminal size={28} color="var(--primary)" />
          <div>
            <h1 style={{ fontSize: '1.6rem', margin: 0, lineHeight: 1.1 }}>Live Logs</h1>
            <div style={{ display: 'flex', gap: 16, marginTop: 10 }}>
              <button
                onClick={() => setActiveTab('system')}
                style={{
                  background: 'none', border: 'none', padding: '0 0 4px 0',
                  color: activeTab === 'system' ? 'var(--primary)' : 'var(--text-muted)',
                  borderBottom: activeTab === 'system' ? '2px solid var(--primary)' : '2px solid transparent',
                  cursor: 'pointer', fontWeight: 600, fontSize: '0.85rem'
                }}
              >System Logs</button>
              <button
                onClick={() => setActiveTab('debug')}
                style={{
                  background: 'none', border: 'none', padding: '0 0 4px 0',
                  color: activeTab === 'debug' ? 'var(--primary)' : 'var(--text-muted)',
                  borderBottom: activeTab === 'debug' ? '2px solid var(--primary)' : '2px solid transparent',
                  cursor: 'pointer', fontWeight: 600, fontSize: '0.85rem'
                }}
              >Debug Log</button>
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.78rem', color: '#64748b' }}>
            <Clock size={12} />
            <span>{lastUpdated || '—'}</span>
            <span>·</span>
            <span style={{ color: 'var(--primary)' }}>{liveCount} log</span>
          </div>
          <button
            onClick={() => setAutoScroll(a => !a)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px',
              borderRadius: 6, border: '1px solid rgba(255,255,255,0.1)',
              background: autoScroll ? 'rgba(139,92,246,0.15)' : 'transparent',
              color: autoScroll ? 'var(--primary)' : 'var(--text-muted)',
              cursor: 'pointer', fontSize: '0.78rem',
            }}
          >
            <Circle size={8} style={{ fill: autoScroll ? 'var(--primary)' : 'none' }} />
            Auto-scroll
          </button>
          <button
            onClick={handleManualRefresh}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px',
              borderRadius: 6, border: '1px solid rgba(255,255,255,0.1)',
              background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.78rem'
            }}
          >
            <RefreshCw size={13} style={{ animation: loading ? 'spin 0.8s linear infinite' : 'none' }} />
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
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px',
              borderRadius: 6, border: '1px solid rgba(239,68,68,0.2)',
              background: 'rgba(239,68,68,0.1)', color: '#ef4444', cursor: 'pointer', fontSize: '0.78rem'
            }}
          >
            <X size={13} />
            Temizle
          </button>
        </div>
      </div>
      {activeTab === 'debug' && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12, paddingBottom: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Aşağıdaki tüm logları kopyalayıp sisteme veya asistana gönderebilirsiniz. Sadece son {logs.length} işlem kaydını içerir.
            </span>
            <button
              onClick={() => {
                navigator.clipboard.writeText(JSON.stringify(logs, null, 2));
                alert("Debug log kopyalandı!");
              }}
              style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '6px 16px',
                borderRadius: 6, background: 'var(--primary)', color: 'white',
                border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: '0.85rem'
              }}
            >
              <Copy size={14} /> Tümünü Kopyala
            </button>
          </div>
          <textarea
            readOnly
            value={JSON.stringify(logs, null, 2)}
            style={{
              flex: 1, width: '100%', resize: 'none',
              background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8, padding: 16, color: '#34d399',
              fontFamily: '"Fira Code", monospace', fontSize: '0.8rem',
              outline: 'none'
            }}
          />
        </div>
      )}

      {activeTab === 'system' && (
        <>
          {/* Filter Bar */}
      <div style={{
        display: 'flex', gap: 8, alignItems: 'center', padding: '10px 16px',
        background: 'rgba(0,0,0,0.2)', borderRadius: '8px 8px 0 0',
        border: '1px solid rgba(255,255,255,0.06)', borderBottom: 'none',
        flexShrink: 0, flexWrap: 'wrap'
      }}>
        <Filter size={14} color="#64748b" />
        <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Filtre:</span>

        {/* Stage pills */}
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {ALL_STAGES.map(s => {
            const meta = STAGE_META[s] || { color: '#94a3b8' };
            const active = filterStage === s;
            return (
              <button
                key={s}
                onClick={() => setFilterStage(active ? '' : s)}
                style={{
                  fontSize: '0.7rem', padding: '3px 8px', borderRadius: 4,
                  border: `1px solid ${active ? meta.color : 'rgba(255,255,255,0.08)'}`,
                  background: active ? meta.color + '22' : 'transparent',
                  color: active ? meta.color : '#64748b',
                  cursor: 'pointer', fontFamily: 'monospace', fontWeight: active ? 700 : 400,
                }}
              >
                {s}
              </button>
            );
          })}
        </div>

        <div style={{ width: 1, height: 16, background: 'rgba(255,255,255,0.1)' }} />

        {/* Level pills */}
        {ALL_LEVELS.map(lv => {
          const col = LEVEL_COLOR[lv];
          const active = filterLevel === lv;
          return (
            <button
              key={lv}
              onClick={() => setFilterLevel(active ? '' : lv)}
              style={{
                fontSize: '0.7rem', padding: '3px 8px', borderRadius: 4,
                border: `1px solid ${active ? col : 'rgba(255,255,255,0.08)'}`,
                background: active ? col + '22' : 'transparent',
                color: active ? col : '#64748b',
                cursor: 'pointer', fontFamily: 'monospace',
              }}
            >
              {lv}
            </button>
          );
        })}

        <div style={{ width: 1, height: 16, background: 'rgba(255,255,255,0.1)' }} />

        {/* Symbol search */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, position: 'relative' }}>
          <Search size={12} color="#64748b" style={{ position: 'absolute', left: 8 }} />
          <input
            value={filterSymbol}
            onChange={e => setFilterSymbol(e.target.value)}
            placeholder="Sembol ara..."
            style={{
              background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 4, color: 'var(--text-main)', fontSize: '0.75rem',
              padding: '4px 8px 4px 26px', width: 140, outline: 'none', fontFamily: 'monospace'
            }}
          />
          {filterSymbol && (
            <button
              onClick={() => setFilterSymbol('')}
              style={{ position: 'absolute', right: 6, background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', padding: 0 }}
            >
              <X size={11} />
            </button>
          )}
        </div>

        {(filterStage || filterLevel || filterSymbol) && (
          <button
            onClick={() => { setFilterStage(''); setFilterLevel(''); setFilterSymbol(''); }}
            style={{
              fontSize: '0.7rem', padding: '3px 8px', borderRadius: 4,
              border: '1px solid rgba(239,68,68,0.4)', background: 'rgba(239,68,68,0.1)',
              color: '#ef4444', cursor: 'pointer'
            }}
          >
            Temizle
          </button>
        )}
      </div>

      {/* Main content: log list + detail panel */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 420px',
        flex: 1,
        overflow: 'hidden',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '0 0 12px 12px',
        background: '#0a0f1a',
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
          style={{ overflowY: 'auto', borderRight: '1px solid rgba(255,255,255,0.06)' }}
        >
          {/* Column header */}
          <div style={{
            display: 'grid', gridTemplateColumns: '70px 90px 1fr 24px',
            gap: 8, padding: '8px 12px',
            borderBottom: '1px solid rgba(255,255,255,0.04)',
            position: 'sticky', top: 0, background: '#0d1117', zIndex: 1
          }}>
            {['Saat', 'Aşama', 'Mesaj', ''].map(h => (
              <span key={h} style={{ fontSize: '0.68rem', color: '#334155', textTransform: 'uppercase', fontFamily: 'monospace' }}>
                {h}
              </span>
            ))}
          </div>

          {logs.length === 0 ? (
            <div style={{ padding: '60px 20px', textAlign: 'center', color: '#334155' }}>
              <Terminal size={32} opacity={0.3} style={{ marginBottom: 12 }} />
              <p style={{ fontSize: '0.85rem' }}>Henüz log yok. Bot'u başlatınca burası dolmaya başlar.</p>
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
        <div style={{ overflowY: 'auto', background: '#0d1117' }}>
          <DetailPanel log={selectedLog} />
        </div>
      </div>
      </>
      )}
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default LiveLogs;
