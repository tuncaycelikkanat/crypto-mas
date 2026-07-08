import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export const CoinDetails: React.FC = () => {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [coinData, setCoinData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchSymbols = async () => {
      try {
        const res = await axios.get('/api/v1/analytics/coins');
        if (res.data && res.data.symbols) {
          setSymbols(res.data.symbols);
          if (res.data.symbols.length > 0) {
            setSelectedSymbol(res.data.symbols[0]);
          }
        }
      } catch (err) {
        console.error("Error fetching symbols:", err);
      }
    };
    fetchSymbols();
  }, []);

  useEffect(() => {
    if (!selectedSymbol) return;
    
    const fetchCoinData = async () => {
      setLoading(true);
      try {
        const res = await axios.get(`/api/v1/analytics/coin/${selectedSymbol}`);
        setCoinData(res.data);
      } catch (err) {
        console.error("Error fetching coin data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchCoinData();
    const interval = setInterval(fetchCoinData, 5000);
    return () => clearInterval(interval);
  }, [selectedSymbol]);

  if (symbols.length === 0) return null;

  return (
    <div style={{ marginTop: '32px' }}>
      <h2 style={{ fontSize: '1.5rem', marginBottom: '16px' }}>Live Markets</h2>
      
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', overflowX: 'auto', paddingBottom: '8px' }}>
        {symbols.map(sym => (
          <button
            key={sym}
            onClick={() => setSelectedSymbol(sym)}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: '1px solid',
              borderColor: selectedSymbol === sym ? 'var(--primary)' : 'rgba(255,255,255,0.1)',
              background: selectedSymbol === sym ? 'rgba(139, 92, 246, 0.2)' : 'transparent',
              color: selectedSymbol === sym ? 'var(--primary)' : 'var(--text-muted)',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s'
            }}
          >
            {sym}
          </button>
        ))}
      </div>

      {loading && !coinData && <div style={{ color: 'var(--text-muted)' }}>Loading {selectedSymbol}...</div>}
      
      {coinData && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="glass-card" style={{ padding: '24px' }}>
            <h3 style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between' }}>
              <span>{coinData.symbol} Price Action</span>
              <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                {coinData.timeframe} | {coinData.exchange}
              </span>
            </h3>
            <div style={{ width: '100%', height: '300px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={coinData.candles} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                  <XAxis 
                    dataKey="time" 
                    stroke="var(--text-muted)" 
                    tickFormatter={(tick) => {
                      try {
                        const d = new Date(tick);
                        if (isNaN(d.getTime())) return tick;
                        return `${d.getHours()}:${d.getMinutes().toString().padStart(2, '0')}`;
                      } catch {
                        return tick;
                      }
                    }} 
                  />
                  <YAxis stroke="var(--text-muted)" domain={['auto', 'auto']} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'var(--bg-card)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    itemStyle={{ color: '#fff' }}
                    labelFormatter={(label) => new Date(label).toLocaleString()}
                  />
                  <Area type="monotone" dataKey="close" stroke="#10b981" fillOpacity={1} fill="url(#colorClose)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {coinData.features && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '16px' }}>
              {Object.entries(coinData.features).map(([key, value]: [string, any]) => (
                <div key={key} className="glass-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{key.replace(/_/g, ' ')}</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>
                    {typeof value === 'number' ? value.toFixed(4) : value}
                  </div>
                </div>
              ))}
            </div>
          )}

          {coinData.logs && coinData.logs.length > 0 && (
            <div className="glass-card" style={{ padding: '24px' }}>
              <h3 style={{ marginBottom: '16px' }}>Decision Logs</h3>
              <div style={{ maxHeight: '300px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {coinData.logs.map((log: any, idx: number) => (
                  <div key={idx} style={{ 
                    padding: '12px', 
                    background: 'rgba(255,255,255,0.02)', 
                    borderRadius: '8px',
                    borderLeft: `4px solid ${log.level === 'error' ? 'var(--danger)' : log.level === 'warn' ? 'var(--warning)' : 'var(--primary)'}`
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--primary)' }}>{log.stage || 'GENERAL'}</span>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{new Date(log.created_at).toLocaleTimeString()}</span>
                    </div>
                    <div style={{ fontSize: '0.95rem' }}>{log.message}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
