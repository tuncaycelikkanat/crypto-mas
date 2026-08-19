import React, { useState, useEffect } from 'react';
import { getCoinSymbols, getCoinData } from '../services/api';
import type { CoinDataResponse } from '../types/api';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import LiveConsole from '../components/LiveConsole';
import RiskRegimeShield from '../components/RiskRegimeShield';
import { Coins, TrendingUp } from 'lucide-react';

const MarketRadar: React.FC = () => {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [coinData, setCoinData] = useState<CoinDataResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchSymbols = async () => {
      try {
        const res = await getCoinSymbols();
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
        const res = await getCoinData(selectedSymbol);
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
    <div style={{ display: 'flex', gap: '24px', minHeight: 'calc(100vh - 160px)' }}>
      
      {/* ── Left Sidebar (Active Coins) ────────────────────────── */}
      <div className="card" style={{
        width: '240px',
        flexShrink: 0,
        padding: '18px 14px',
        display: 'flex',
        flexDirection: 'column',
        maxHeight: 'calc(100vh - 120px)',
        position: 'sticky',
        top: '80px',
        overflowY: 'auto'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 6px 14px', borderBottom: '1px solid var(--border)', marginBottom: 12 }}>
          <Coins size={16} color="var(--text-primary)" />
          <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Active Pairs</h3>
        </div>

        {symbols.length === 0 ? (
          <div className="text-muted" style={{ fontSize: '0.85rem', padding: '12px 6px' }}>Loading symbols…</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {symbols.map(sym => {
              const isSelected = selectedSymbol === sym;
              return (
                <button
                  key={sym}
                  onClick={() => setSelectedSymbol(sym)}
                  className={isSelected ? "btn-primary" : "btn-ghost"}
                  style={{
                    justifyContent: 'flex-start',
                    width: '100%',
                    padding: '8px 12px',
                    fontSize: '0.82rem',
                    fontFamily: 'JetBrains Mono, monospace',
                    fontWeight: isSelected ? 700 : 500,
                  }}
                >
                  {sym}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Right Main Analysis Viewport ──────────────────────── */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        overflowY: 'auto',
        paddingRight: '4px'
      }}>
        <RiskRegimeShield />
        
        {loading && !coinData && (
          <div className="text-muted" style={{ padding: '24px 0' }}>Loading {selectedSymbol} telemetry…</div>
        )}
        
        <AnimatePresence mode="wait">
          {coinData && (
            <motion.div
              key={coinData.symbol}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}
            >
              {/* Price Chart Card */}
              <div className="card" style={{ padding: '22px 24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ width: 28, height: 28, borderRadius: 8, background: 'var(--accent-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <TrendingUp size={15} color="var(--text-primary)" />
                    </div>
                    <div>
                      <h3 style={{ margin: 0 }}>{coinData.symbol} Price Action</h3>
                      <div className="text-muted mono" style={{ fontSize: '0.75rem', marginTop: 2 }}>
                        {coinData.timeframe} Interval · {coinData.exchange}
                      </div>
                    </div>
                  </div>
                </div>

                <div style={{ width: '100%', height: '320px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={coinData.candles} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorCloseMono" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--success)" stopOpacity={0.25}/>
                          <stop offset="95%" stopColor="var(--success)" stopOpacity={0.0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                      <XAxis 
                        dataKey="time" 
                        stroke="var(--text-dim)" 
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
                        stroke="var(--text-dim)" 
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
                        contentStyle={{
                          backgroundColor: 'var(--bg-raised)',
                          borderColor: 'var(--border-hover)',
                          borderRadius: '8px',
                          color: 'var(--text-primary)',
                        }}
                        itemStyle={{ color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}
                        labelStyle={{ color: 'var(--text-muted)', marginBottom: '4px', fontSize: '0.75rem' }}
                        labelFormatter={(label) => {
                          try {
                            return new Date(label).toLocaleString();
                          } catch {
                            return label;
                          }
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="close"
                        stroke="var(--success)"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorCloseMono)"
                        dot={false}
                        activeDot={{ r: 4, fill: 'var(--success)', stroke: 'var(--bg-base)', strokeWidth: 2 }}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Technical Features Grid Cards */}
              {coinData.features && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '14px' }}>
                  {Object.entries(coinData.features).map(([key, value]: [string, any]) => (
                    <div key={key} className="card" style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <div className="section-label">
                        {key.replace(/_/g, ' ')}
                      </div>
                      <div className="stat-value" style={{ fontSize: '1.25rem', color: 'var(--text-primary)' }}>
                        {typeof value === 'number'
                          ? (Math.abs(value) < 0.001 && value !== 0 ? value.toExponential(2) : value.toFixed(4))
                          : value}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              {/* Targeted Console */}
              <LiveConsole symbol={selectedSymbol} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

    </div>
  );
};

export default MarketRadar;
