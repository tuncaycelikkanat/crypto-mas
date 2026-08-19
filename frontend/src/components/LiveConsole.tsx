import React, { useEffect, useRef, useState, useCallback } from 'react';
import api from '../services/api';
import { Terminal, Play, Pause } from 'lucide-react';
import { motion } from 'framer-motion';

interface LogEntry {
  id: number;
  level: string;
  stage: string;
  message: string;
  created_at: string;
}

interface LiveConsoleProps {
  symbol?: string | null;
}

const levelColor: Record<string, string> = {
  ERROR:   'var(--danger)',
  WARNING: 'var(--warning)',
  WARN:    'var(--warning)',
  SUCCESS: 'var(--success)',
  INFO:    'var(--text-secondary)',
  DEBUG:   'var(--text-muted)',
};

const LiveConsole: React.FC<LiveConsoleProps> = ({ symbol }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [paused, setPaused] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const isAtBottom = useRef(true);

  const fetchLogs = useCallback(async () => {
    if (paused) return;
    try {
      const res = await api.get<LogEntry[]>('/logs/recent?limit=150');
      let fetched: LogEntry[] = Array.isArray(res.data) ? res.data : [];
      if (symbol) {
        fetched = fetched.filter(l => 
          (l.message && l.message.includes(symbol)) || 
          (l.stage && l.stage.includes(symbol))
        );
      }
      setLogs(fetched);
    } catch { /* ignore */ }
  }, [symbol, paused]);

  useEffect(() => {
    fetchLogs();
    const iv = setInterval(fetchLogs, 2000);
    return () => clearInterval(iv);
  }, [fetchLogs]);

  useEffect(() => {
    if (isAtBottom.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    isAtBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 30;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="card"
      style={{
        marginTop: 8,
        border: '1px solid var(--border)',
        boxShadow: 'var(--shadow)',
        borderRadius: 'var(--radius)',
        overflow: 'hidden',
      }}
    >
      {/* Terminal Title Bar */}
      <div style={{
        background: 'var(--bg-raised)',
        padding: '12px 18px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        {/* Left: macOS dots + title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <div style={{ width: 9, height: 9, borderRadius: '50%', background: 'rgba(255, 255, 255, 0.2)' }} />
            <div style={{ width: 9, height: 9, borderRadius: '50%', background: 'rgba(255, 255, 255, 0.2)' }} />
            <div style={{ width: 9, height: 9, borderRadius: '50%', background: 'rgba(255, 255, 255, 0.2)' }} />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Terminal size={14} color="var(--text-muted)" />
            <span style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              color: 'var(--text-primary)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              fontFamily: 'JetBrains Mono, monospace',
            }}>
              Execution Console {symbol ? `[${symbol}]` : ''}
            </span>
          </div>
        </div>

        {/* Right: Live pulse & Pause button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <motion.div
              animate={!paused ? { opacity: [1, 0.3, 1] } : {}}
              transition={{ duration: 1.8, repeat: Infinity }}
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: paused ? 'var(--text-muted)' : 'var(--success)',
                boxShadow: paused ? 'none' : '0 0 6px var(--success)',
              }}
            />
            <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              {paused ? 'PAUSED' : 'LIVE'}
            </span>
          </div>

          <button
            onClick={() => setPaused(p => !p)}
            className="btn-ghost"
            style={{
              padding: '3px 8px',
              height: 24,
              fontSize: '0.7rem',
              borderRadius: 'var(--radius-xs)',
              border: '1px solid var(--border)',
            }}
          >
            {paused ? <Play size={11} /> : <Pause size={11} />}
            <span>{paused ? 'Resume' : 'Pause'}</span>
          </button>
        </div>
      </div>

      {/* Terminal Log Stream Body */}
      <div
        ref={scrollRef}
        onScroll={onScroll}
        style={{
          background: 'var(--bg-base)',
          padding: '16px 20px',
          height: 300,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
          fontSize: '0.8rem',
          lineHeight: '1.6',
          fontFamily: 'JetBrains Mono, Fira Code, monospace',
        }}
      >
        {logs.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', fontStyle: 'italic', padding: '12px 0' }}>
            &gt; Waiting for execution signals…
          </div>
        ) : (
          logs.map(log => {
            const time = new Date(log.created_at).toLocaleTimeString([], {
              hour12: false,
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit'
            });
            const color = levelColor[log.level] || 'var(--text-muted)';
            return (
              <div key={log.id} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <span style={{ color: 'var(--text-dim)', minWidth: 64, flexShrink: 0 }}>{time}</span>
                <span style={{ color, minWidth: 72, flexShrink: 0, fontWeight: 700, fontSize: '0.75rem' }}>
                  [{log.level}]
                </span>
                <span style={{ color: 'var(--text-muted)', minWidth: 90, flexShrink: 0, fontSize: '0.75rem' }}>
                  {log.stage}
                </span>
                <span style={{ color: 'var(--text-secondary)', flex: 1, wordBreak: 'break-word' }}>
                  {log.message}
                </span>
              </div>
            );
          })
        )}
      </div>
    </motion.div>
  );
};

export default LiveConsole;
