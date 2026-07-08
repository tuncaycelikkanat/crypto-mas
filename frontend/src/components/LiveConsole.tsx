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

const LiveConsole: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchLogs = async () => {
    try {
      const res = await axios.get('/api/v1/logs/recent?limit=50');
      setLogs(res.data);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 2000); // Poll every 2 seconds
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Auto-scroll to bottom on new logs
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const getLogColor = (level: string) => {
    switch (level) {
      case 'ERROR': return '#ef4444'; // Red
      case 'WARN': return '#f59e0b'; // Yellow
      case 'SUCCESS': return '#10b981'; // Green
      default: return '#a78bfa'; // Purple for INFO/System
    }
  };

  return (
    <div style={{
      background: '#09090b',
      border: '1px solid rgba(139, 92, 246, 0.2)',
      borderRadius: '12px',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      height: '350px',
      fontFamily: 'monospace',
      boxShadow: '0 10px 30px -10px rgba(0,0,0,0.5)',
      marginTop: '24px'
    }}>
      <div style={{
        background: 'rgba(139, 92, 246, 0.1)',
        padding: '12px 16px',
        borderBottom: '1px solid rgba(139, 92, 246, 0.2)',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        color: '#e2e8f0',
        fontWeight: 600,
        fontSize: '0.9rem'
      }}>
        <Terminal size={18} color="#a78bfa" />
        Live Execution Terminal
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
          color: '#cbd5e1',
          fontSize: '0.85rem',
          lineHeight: '1.5'
        }}
      >
        {logs.length === 0 ? (
          <div style={{ color: '#64748b', fontStyle: 'italic' }}>Waiting for system logs...</div>
        ) : (
          logs.map((log) => {
            const time = new Date(log.created_at).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' });
            return (
              <div key={log.id} style={{ display: 'flex', gap: '12px' }}>
                <span style={{ color: '#64748b', minWidth: '70px' }}>[{time}]</span>
                <span style={{ 
                  color: getLogColor(log.level),
                  fontWeight: 600,
                  minWidth: '80px',
                  display: 'inline-block'
                }}>
                  [{log.stage}]
                </span>
                <span style={{ color: log.level === 'ERROR' ? '#ef4444' : log.level === 'SUCCESS' ? '#10b981' : '#e2e8f0' }}>
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
