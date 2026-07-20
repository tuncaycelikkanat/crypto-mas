import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Terminal } from 'lucide-react';
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
  ERROR:   '#f87171',
  WARNING: '#fbbf24',
  WARN:    '#fbbf24',
  SUCCESS: '#4ade80',
  INFO:    '#38bdf8',
  DEBUG:   '#94a3b8',
};

const LiveConsole: React.FC<LiveConsoleProps> = ({ symbol }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [paused, setPaused]   = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const isAtBottom = useRef(true);

  const fetchLogs = React.useCallback(async () => {
    if (paused) return;
    try {
      const res = await axios.get('/api/v1/logs/recent?limit=150');
      let fetched: LogEntry[] = res.data;
      if (symbol) fetched = fetched.filter(l => l.message.includes(symbol) || l.stage.includes(symbol));
      setLogs(fetched);
    } catch { /* ignore */ }
  }, [symbol, paused]);

  useEffect(() => { fetchLogs(); const iv = setInterval(fetchLogs, 2000); return () => clearInterval(iv); }, [fetchLogs]);

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
      transition={{ delay: 0.3 }}
      style={{
        borderRadius: 16,
        overflow: 'hidden',
        border: '1px solid var(--border)',
        boxShadow: '0 0 40px rgba(0,0,0,0.5)',
        marginTop: 8,
        fontFamily: '"JetBrains Mono", "Fira Code", "Courier New", monospace',
      }}
    >
      {/* Terminal title bar */}
      <div style={{
        background: 'rgba(9,14,30,0.95)',
        padding: '10px 18px',
        borderBottom: '1px solid rgba(56,189,248,0.12)',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        {/* macOS-style dots */}
        <div style={{ display: 'flex', gap: 6, marginRight: 6 }}>
          {['#f87171','#fbbf24','#4ade80'].map((c, i) => (
            <div key={i} style={{ width: 10, height: 10, borderRadius: '50%', background: c, opacity: 0.9 }} />
          ))}
        </div>
        <Terminal size={14} color="#38bdf8" style={{ opacity: 0.8 }} />
        <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#38bdf8', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          Execution Console
        </span>
        {/* Live pulse */}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
          <motion.div
            animate={!paused ? { opacity: [1, 0.2, 1] } : {}}
            transition={{ duration: 1.5, repeat: Infinity }}
            style={{ width: 6, height: 6, borderRadius: '50%', background: paused ? '#64748b' : '#4ade80', boxShadow: paused ? 'none' : '0 0 6px #4ade80' }}
          />
          <span style={{ fontSize: '0.7rem', color: '#64748b' }}>{paused ? 'PAUSED' : 'LIVE'}</span>
          <button
            onClick={() => setPaused(p => !p)}
            style={{
              marginLeft: 8, padding: '3px 10px', borderRadius: 6,
              background: paused ? 'rgba(56,189,248,0.15)' : 'rgba(100,116,139,0.15)',
              border: `1px solid ${paused ? 'rgba(56,189,248,0.3)' : 'rgba(100,116,139,0.3)'}`,
              color: paused ? '#38bdf8' : '#64748b',
              cursor: 'pointer', fontSize: '0.7rem', fontFamily: 'inherit',
            }}
          >
            {paused ? 'Resume' : 'Pause'}
          </button>
        </div>
      </div>

      {/* Log body */}
      <div
        ref={scrollRef}
        onScroll={onScroll}
        style={{
          background: 'rgba(2,6,23,0.98)',
          padding: '14px 18px',
          height: 320,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 4,
          fontSize: '0.8rem',
          lineHeight: '1.6',
        }}
      >
        {logs.length === 0 ? (
          <div style={{ color: '#334155', fontStyle: 'italic', padding: '12px 0' }}>
            {'>'} Waiting for system logs…
          </div>
        ) : (
          logs.map(log => {
            const time = new Date(log.created_at).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
            const color = levelColor[log.level] || '#94a3b8';
            return (
              <div key={log.id} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <span style={{ color: '#475569', minWidth: 64, flexShrink: 0, letterSpacing: '-0.02em' }}>{time}</span>
                <span style={{ color, minWidth: 72, flexShrink: 0, fontWeight: 700, fontSize: '0.75rem', letterSpacing: '0.03em' }}>
                  [{log.level}]
                </span>
                <span style={{ color: '#64748b', minWidth: 90, flexShrink: 0, fontSize: '0.75rem' }}>
                  {log.stage}
                </span>
                <span style={{ color: '#cbd5e1', flex: 1 }}>{log.message}</span>
              </div>
            );
          })
        )}
      </div>
    </motion.div>
  );
};

export default LiveConsole;
