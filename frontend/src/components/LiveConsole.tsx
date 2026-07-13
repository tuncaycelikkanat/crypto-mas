import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Terminal } from 'lucide-react';

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

const LiveConsole: React.FC<LiveConsoleProps> = ({ symbol }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchLogs = React.useCallback(async () => {
    try {
      const res = await axios.get('/api/v1/logs/recent?limit=100');
      let fetchedLogs: LogEntry[] = res.data;
      if (symbol) {
        fetchedLogs = fetchedLogs.filter(log => log.message.includes(symbol) || log.stage.includes(symbol));
      }
      setLogs(fetchedLogs);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    }
  }, [symbol]);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 2000); // Poll every 2 seconds
    return () => clearInterval(interval);
  }, [fetchLogs]);

  useEffect(() => {
    // Auto-scroll to bottom on new logs
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div style={{
      background: '#000000',
      border: '1px solid #333',
      borderRadius: '8px',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      height: '350px',
      fontFamily: '"Courier New", Courier, monospace',
      boxShadow: '0 0 15px rgba(0,0,0,0.8) inset',
      marginTop: '24px'
    }}>
      <div style={{
        background: '#111',
        padding: '12px 16px',
        borderBottom: '1px solid #333',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        color: '#ff9900', // Bloomberg-like amber
        fontWeight: 'bold',
        fontSize: '0.9rem',
        textShadow: '0 0 5px rgba(255,153,0,0.5)'
      }}>
        <Terminal size={18} color="#ff9900" />
        BLOOMBERG TERMINAL - LIVE EXECUTION
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '6px' }}>
          <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ef4444' }}></div>
          <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#f59e0b' }}></div>
          <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#10b981' }}></div>
        </div>
      </div>
      
      <div 
        ref={scrollRef}
        style={{
          padding: '16px',
          overflowY: 'auto',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          color: '#00ff00', // Classic terminal green
          fontSize: '0.85rem',
          lineHeight: '1.5'
        }}
      >
        {logs.length === 0 ? (
          <div style={{ color: '#00aa00', fontStyle: 'italic', textShadow: '0 0 4px rgba(0,255,0,0.4)' }}>Waiting for system logs...</div>
        ) : (
          logs.map((log) => {
            const time = new Date(log.created_at).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' });
            return (
              <div key={log.id} style={{ display: 'flex', gap: '12px' }}>
                <span style={{ color: '#00ffff', minWidth: '70px', textShadow: '0 0 5px rgba(0,255,255,0.5)' }}>[{time}]</span>
                <span style={{ 
                  color: log.level === 'ERROR' ? '#ff0000' : log.level === 'WARN' ? '#ffcc00' : '#00ffff',
                  fontWeight: 'bold',
                  minWidth: '80px',
                  display: 'inline-block',
                  textShadow: log.level === 'ERROR' ? '0 0 5px rgba(255,0,0,0.6)' : log.level === 'WARN' ? '0 0 5px rgba(255,204,0,0.6)' : '0 0 5px rgba(0,255,255,0.6)'
                }}>
                  [{log.stage}]
                </span>
                <span style={{ 
                  color: log.level === 'ERROR' ? '#ff3333' : log.level === 'SUCCESS' ? '#00ff00' : '#ff9900',
                  textShadow: log.level === 'ERROR' ? '0 0 5px rgba(255,51,51,0.5)' : log.level === 'SUCCESS' ? '0 0 5px rgba(0,255,0,0.5)' : '0 0 5px rgba(255,153,0,0.5)'
                }}>
                  {log.message}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default LiveConsole;
