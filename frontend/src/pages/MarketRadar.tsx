import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { motion } from 'framer-motion';
import LiveConsole from '../components/LiveConsole';

const MarketRadar: React.FC = () => {
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
    
    const fetchCoinData = async (isInitial = false) => {
      if (isInitial) setLoading(true);
      try {
        const res = await axios.get(`/api/v1/analytics/coin/${selectedSymbol}`);
        setCoinData(res.data);
      } catch (err) {
        console.error("Error fetching coin data:", err);
      } finally {
        if (isInitial) setLoading(false);
      }
    };

    fetchCoinData(true);
    const interval = setInterval(() => fetchCoinData(false), 5000);
    return () => clearInterval(interval);
  }, [selectedSymbol]);

  return (
    <div style={{ display: 'flex', gap: '24px', height: 'calc(100vh - 120px)' }}>
      {/* ── Left Sidebar ──────────────────────────────────────── */}
      <div className="card" style={{ width: '250px', flexShrink: 0, padding: '16px', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
        <h3 style={{ marginBottom: '16px', fontSize: '1.1rem', color: 'var(--text-primary)' }}>Active Coins</h3>
        {symbols.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Loading symbols...</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {symbols.map(sym => {
              const isSelected = selectedSymbol === sym;
              return (
                <button
                  key={sym}
                  onClick={() => setSelectedSymbol(sym)}
                  style={{
                    padding: '10px 16px',
                    borderRadius: '8px',
                    border: '1px solid',
                    borderColor: isSelected ? 'var(--primary)' : 'var(--border)',
                    background: isSelected ? 'var(--accent-soft)' : 'transparent',
                    color: isSelected ? 'var(--primary)' : 'var(--text-secondary)',
                    boxShadow: isSelected ? '0 0 12px rgba(var(--primary-rgb, 0, 255, 255), 0.3)' : 'none',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.2s',
                    fontSize: '0.95rem',
                    fontWeight: isSelected ? 600 : 400,
                  }}
                >
                  {sym}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Right Main Area ───────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '24px', overflowY: 'auto', paddingRight: '8px' }}>
        {loading && !coinData && <div style={{ color: 'var(--text-muted)' }}>Loading {selectedSymbol}...</div>}
        
        {coinData && (
          <>
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="card" 
              style={{ padding: '24px' }}
            >
              <h3 style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>{coinData.symbol} Price Action</span>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                  {coinData.timeframe} | {coinData.exchange}
                </span>
              </h3>
              <div style={{ width: '100%', height: '320px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={coinData.candles} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--success)" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="var(--success)" stopOpacity={0}/>
                      </linearGradient>
                      <filter id="glow">
                        <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                        <feMerge>
                          <feMergeNode in="coloredBlur"/>
                          <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                      </filter>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis 
                      dataKey="time" 
                      stroke="var(--text-muted)" 
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
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
                    <YAxis 
                      stroke="var(--text-muted)" 
                      domain={['dataMin', 'dataMax']} 
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={v => {
                        if (v === 0) return '$0';
                        if (Math.abs(v) < 0.001) return `$${Number(v).toExponential(2)}`;
                        if (Math.abs(v) < 1) return `$${Number(v).toFixed(4)}`;
                        return `$${Number(v).toFixed(2)}`;
                      }}
                      width={70}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)', borderRadius: '8px' }}
                      itemStyle={{ color: 'var(--text-primary)' }}
                      labelStyle={{ color: 'var(--text-muted)', marginBottom: '4px' }}
                      labelFormatter={(label) => {
                        try {
                          return new Date(label).toLocaleString();
                        } catch {
                          return label;
                        }
                      }}
                    />
                    <Area type="monotone" dataKey="close" stroke="var(--success)" strokeWidth={2} fillOpacity={1} fill="url(#colorClose)" filter="url(#glow)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </motion.div>

            {coinData.features && (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.1 }}
                style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '16px' }}
              >
                {Object.entries(coinData.features).map(([key, value]: [string, any]) => (
                  <div key={key} className="card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 500 }}>
                      {key.replace(/_/g, ' ')}
                    </div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {typeof value === 'number' ? (Math.abs(value) < 0.001 && value !== 0 ? value.toExponential(2) : value.toFixed(4)) : value}
                    </div>
                  </div>
                ))}
              </motion.div>
            )}
            
            <LiveConsole symbol={selectedSymbol} />
          </>
        )}
      </div>
    </div>
  );
};

export default MarketRadar;
