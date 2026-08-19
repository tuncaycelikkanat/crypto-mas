import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export const CoinDetails: React.FC = () => {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [coinData, setCoinData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchSymbols = async () => {
      try {
        const res = await api.get('/analytics/coins');
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
        const res = await api.get(`/analytics/coin/${selectedSymbol}`);
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
    <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <h2 style={{ fontSize: '1.25rem', marginBottom: '8px' }}>Live Markets</h2>
      
      <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '8px' }}>
        {symbols.map(sym => {
          const isSelected = selectedSymbol === sym;
          return (
            <button
              key={sym}
              onClick={() => setSelectedSymbol(sym)}
              className={isSelected ? 'btn-primary' : 'btn-secondary'}
              style={{
                padding: '6px 14px',
                fontSize: '0.8rem',
                fontFamily: 'JetBrains Mono, monospace',
              }}
            >
              {sym}
            </button>
          );
        })}
      </div>

      {loading && !coinData && <div className="text-muted">Loading {selectedSymbol}…</div>}
      
      {coinData && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="card" style={{ padding: '22px 24px' }}>
            <h3 style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>{coinData.symbol} Price Action</span>
              <span className="mono text-muted" style={{ fontSize: '0.75rem' }}>
                {coinData.timeframe} | {coinData.exchange}
              </span>
            </h3>
            <div style={{ width: '100%', height: '280px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={coinData.candles} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="coinGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--success)" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="var(--success)" stopOpacity={0.0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis 
                    dataKey="time" 
                    stroke="var(--text-dim)" 
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
                  <YAxis stroke="var(--text-dim)" domain={['auto', 'auto']} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'var(--bg-raised)', borderColor: 'var(--border-hover)', borderRadius: '8px' }}
                    itemStyle={{ color: 'var(--text-primary)' }}
                    labelFormatter={(label) => new Date(label).toLocaleString()}
                  />
                  <Area type="monotone" dataKey="close" stroke="var(--success)" strokeWidth={2} fillOpacity={1} fill="url(#coinGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {coinData.features && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '14px' }}>
              {Object.entries(coinData.features).map(([key, value]: [string, any]) => (
                <div key={key} className="card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div className="section-label">{key.replace(/_/g, ' ')}</div>
                  <div className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--text-primary)' }}>
                    {typeof value === 'number' ? value.toFixed(4) : value}
                  </div>
                </div>
              ))}
            </div>
          )}

        </div>
      )}
    </div>
  );
};
