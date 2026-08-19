import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Bot, TrendingUp, FlaskConical, Zap, Terminal, Shield, 
  ArrowRight, Activity, Cpu, Sparkles,
  ChevronRight, BarChart3, Radio
} from 'lucide-react';
import axios from 'axios';
import { getHealth, getAnalyticsSummary } from '../services/api';
import { BorderBeamPanel } from '../components/ui/BorderBeamPanel';
import { FlipDiskMatrix } from '../components/ui/FlipDiskMatrix';

export const Welcome: React.FC = () => {
  const navigate = useNavigate();
  const [sysOnline, setSysOnline] = useState<boolean | null>(null);
  const [summary, setSummary] = useState<any>(null);
  const [regime, setRegime] = useState<string>('BULLISH');

  useEffect(() => {
    getHealth().then(() => setSysOnline(true)).catch(() => setSysOnline(false));
    getAnalyticsSummary().then(res => setSummary(res.data)).catch(() => {});

    // Fetch snapshot
    const apiBase = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : '/api/v1';
    axios.get(`${apiBase}/ws/risk-regime/snapshot`)
      .then(res => {
        if (res.data?.regime_snapshot?.btc_regime) {
          setRegime(res.data.regime_snapshot.btc_regime);
        }
      })
      .catch(() => {});
  }, []);

  const totalTrades = summary?.total_trades ?? 0;
  const winRate = (summary?.win_rate ?? 0).toFixed(1);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '64px', paddingBottom: '48px', maxWidth: '1200px', margin: '0 auto' }}>
      
      {/* ── 1. Hero Section ───────────────────────────────────── */}
      <section style={{
        textAlign: 'center',
        paddingTop: '20px',
        paddingBottom: '10px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '24px',
        position: 'relative',
      }}>
        
        {/* Glowing Badge */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 16px',
            borderRadius: 'var(--radius-full)',
            background: 'var(--accent-soft)',
            border: '1px solid var(--accent-border)',
            boxShadow: '0 0 20px rgba(255, 255, 255, 0.08)',
          }}
        >
          <Sparkles size={14} color="var(--text-primary)" />
          <span style={{
            fontSize: '0.75rem',
            fontWeight: 700,
            letterSpacing: '0.08em',
            color: 'var(--text-primary)',
            textTransform: 'uppercase',
          }}>
            Autonomous Multi-Agent Crypto Platform
          </span>
        </motion.div>

        {/* Hero Title */}
        <motion.h1
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          style={{
            fontSize: 'clamp(2.4rem, 5vw, 3.8rem)',
            fontWeight: 900,
            letterSpacing: '-0.04em',
            lineHeight: 1.1,
            maxWidth: '900px',
            margin: '0 auto',
          }}
        >
          Institutional Multi-Agent Intelligence for <span className="text-shimmer">Crypto Markets</span>
        </motion.h1>

        {/* Hero Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          style={{
            fontSize: '1.05rem',
            color: 'var(--text-muted)',
            maxWidth: '680px',
            lineHeight: 1.6,
            margin: '0 auto',
          }}
        >
          Real-time volatility regime barriers, event-driven multi-agent execution, automatic Optuna tuning, and high-fidelity backtesting engine.
        </motion.p>

        {/* Quick Action CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          style={{
            display: 'flex',
            gap: '14px',
            alignItems: 'center',
            justifyContent: 'center',
            flexWrap: 'wrap',
            marginTop: '8px',
          }}
        >
          <button
            onClick={() => navigate('/paper')}
            className="btn-primary"
            style={{
              padding: '12px 24px',
              fontSize: '0.95rem',
              borderRadius: 'var(--radius-sm)',
              boxShadow: '0 0 25px rgba(255, 255, 255, 0.2)',
            }}
          >
            <Bot size={18} />
            <span>Launch Paper Trading</span>
            <ArrowRight size={16} />
          </button>

          <button
            onClick={() => navigate('/dashboard')}
            className="btn-secondary"
            style={{
              padding: '12px 22px',
              fontSize: '0.95rem',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <Activity size={16} />
            <span>Open Overview</span>
          </button>

          <button
            onClick={() => navigate('/backtesting')}
            className="btn-secondary"
            style={{
              padding: '12px 22px',
              fontSize: '0.95rem',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <FlaskConical size={16} />
            <span>Backtesting Engine</span>
          </button>
        </motion.div>

        {/* ── 3D Electromechanical Flip-Disk Matrix Board ─────── */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.35 }}
          style={{ marginTop: '36px', width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
            <Radio size={14} color="#E5FD52" className="animate-pulse" />
            <span className="section-label" style={{ color: 'var(--text-secondary)' }}>Live Telemetry Board</span>
          </div>
          <FlipDiskMatrix />
        </motion.div>

        {/* Live Telemetry Ribbon */}
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.45 }}
          className="card"
          style={{
            marginTop: '12px',
            padding: '14px 28px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '32px',
            flexWrap: 'wrap',
            background: 'var(--bg-raised)',
            border: '1px solid var(--border-strong)',
            borderRadius: 'var(--radius-full)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 7, height: 7, borderRadius: '50%',
              background: sysOnline ? 'var(--success)' : 'var(--danger)',
              boxShadow: sysOnline ? '0 0 8px var(--success)' : 'none'
            }} />
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              Core Engine: {sysOnline ? 'Online' : 'Connecting…'}
            </span>
          </div>

          <div style={{ width: 1, height: 16, background: 'var(--border)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Shield size={14} color="var(--text-muted)" />
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>BTC Regime:</span>
            <span className="mono" style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {regime}
            </span>
          </div>

          <div style={{ width: 1, height: 16, background: 'var(--border)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <BarChart3 size={14} color="var(--text-muted)" />
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Historical Win Rate:</span>
            <span className="mono" style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--success)' }}>
              {winRate}%
            </span>
          </div>

          <div style={{ width: 1, height: 16, background: 'var(--border)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Cpu size={14} color="var(--text-muted)" />
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Closed Trades:</span>
            <span className="mono" style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {totalTrades}
            </span>
          </div>
        </motion.div>

      </section>

      {/* ── 2. Interactive Feature Showcase (Border Beam Panels) ── */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        <div style={{ textAlign: 'center', marginBottom: '8px' }}>
          <span className="section-label" style={{ letterSpacing: '0.12em' }}>Platform Capabilities</span>
          <h2 style={{ fontSize: '1.8rem', marginTop: 4 }}>Full-Spectrum Multi-Agent Suite</h2>
        </div>

        <div className="grid-cols-3" style={{ gap: '20px' }}>
          
          {/* Card 1: Autonomous Bot Execution */}
          <BorderBeamPanel
            seed={1}
            beams={2}
            colors={['#ffffff', '#a1a1aa']}
            thickness={2}
            idleSpeed={45}
            hoverSpeed={260}
            radius={16}
            onClick={() => navigate('/paper')}
            style={{ padding: '28px 24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '16px' }}
          >
            <div>
              <div style={{
                width: 42, height: 42, borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-raised)', border: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                marginBottom: 16
              }}>
                <Bot size={20} color="var(--text-primary)" />
              </div>
              <h3 style={{ fontSize: '1.15rem', marginBottom: 8 }}>Autonomous Trading Bots</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Deploy multi-slot simulated bots across Binance & MEXC with real-time risk slider adjustment, take-profit triggers, and trailing stops.
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.82rem' }}>
              <span>Open Paper Trading</span>
              <ChevronRight size={14} />
            </div>
          </BorderBeamPanel>

          {/* Card 2: Market Regime Shield */}
          <BorderBeamPanel
            seed={2}
            beams={2}
            colors={['#10b981', '#34d399']}
            thickness={2}
            idleSpeed={45}
            hoverSpeed={260}
            radius={16}
            onClick={() => navigate('/dashboard')}
            style={{ padding: '28px 24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '16px' }}
          >
            <div>
              <div style={{
                width: 42, height: 42, borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-raised)', border: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                marginBottom: 16
              }}>
                <Shield size={20} color="var(--success)" />
              </div>
              <h3 style={{ fontSize: '1.15rem', marginBottom: 8 }}>Real-Time Regime Shield</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Continuous WebSocket evaluation of Bitcoin volatility, correlation matrices, and drawdown caps to protect capital before entries occur.
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.82rem' }}>
              <span>View Live Shield</span>
              <ChevronRight size={14} />
            </div>
          </BorderBeamPanel>

          {/* Card 3: Market Radar Telemetry */}
          <BorderBeamPanel
            seed={3}
            beams={2}
            colors={['#06b6d4', '#38bdf8']}
            thickness={2}
            idleSpeed={45}
            hoverSpeed={260}
            radius={16}
            onClick={() => navigate('/radar')}
            style={{ padding: '28px 24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '16px' }}
          >
            <div>
              <div style={{
                width: 42, height: 42, borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-raised)', border: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                marginBottom: 16
              }}>
                <TrendingUp size={20} color="var(--neon-cyan)" />
              </div>
              <h3 style={{ fontSize: '1.15rem', marginBottom: 8 }}>Market Radar Scanner</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Sub-second candlestick feature extraction, indicator gauges (RSI, ADX, ATR), and micro-pullback signal visualization.
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.82rem' }}>
              <span>Explore Radar</span>
              <ChevronRight size={14} />
            </div>
          </BorderBeamPanel>

          {/* Card 4: High-Fidelity Backtesting */}
          <BorderBeamPanel
            seed={4}
            beams={2}
            colors={['#a855f7', '#c084fc']}
            thickness={2}
            idleSpeed={45}
            hoverSpeed={260}
            radius={16}
            onClick={() => navigate('/backtesting')}
            style={{ padding: '28px 24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '16px' }}
          >
            <div>
              <div style={{
                width: 42, height: 42, borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-raised)', border: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                marginBottom: 16
              }}>
                <FlaskConical size={20} color="var(--neon-purple)" />
              </div>
              <h3 style={{ fontSize: '1.15rem', marginBottom: 8 }}>Backtesting & LLM Shadow</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Run high-speed historical simulations with customizable risk multipliers or multi-agent LLM shadow runs with side-by-side equity comparison.
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.82rem' }}>
              <span>Start Backtesting</span>
              <ChevronRight size={14} />
            </div>
          </BorderBeamPanel>

          {/* Card 5: Optuna Auto-Optimizer */}
          <BorderBeamPanel
            seed={5}
            beams={2}
            colors={['#f59e0b', '#fbbf24']}
            thickness={2}
            idleSpeed={45}
            hoverSpeed={260}
            radius={16}
            onClick={() => navigate('/optimization')}
            style={{ padding: '28px 24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '16px' }}
          >
            <div>
              <div style={{
                width: 42, height: 42, borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-raised)', border: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                marginBottom: 16
              }}>
                <Zap size={20} color="var(--warning)" />
              </div>
              <h3 style={{ fontSize: '1.15rem', marginBottom: 8 }}>AI Auto-Optimizer</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Automated Bayesian parameter tuning discovering optimal stop-loss, take-profit, and volatility thresholds on demand.
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.82rem' }}>
              <span>Open Optimizer</span>
              <ChevronRight size={14} />
            </div>
          </BorderBeamPanel>

          {/* Card 6: Live Telemetry & Logs */}
          <BorderBeamPanel
            seed={6}
            beams={2}
            colors={['#ffffff', '#71717a']}
            thickness={2}
            idleSpeed={45}
            hoverSpeed={260}
            radius={16}
            onClick={() => navigate('/logs')}
            style={{ padding: '28px 24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '16px' }}
          >
            <div>
              <div style={{
                width: 42, height: 42, borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-raised)', border: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                marginBottom: 16
              }}>
                <Terminal size={20} color="var(--text-primary)" />
              </div>
              <h3 style={{ fontSize: '1.15rem', marginBottom: 8 }}>Telemetry & Event Stream</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Inspect real-time agent decisions, raw JSON payloads, risk barriers, and audit trail logs with one-click clipboard export.
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.82rem' }}>
              <span>View System Logs</span>
              <ChevronRight size={14} />
            </div>
          </BorderBeamPanel>

        </div>
      </section>

      {/* ── 3. Bottom Architecture Banner ─────────────────────── */}
      <section className="card" style={{
        padding: '36px 32px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '24px',
        background: 'var(--bg-raised)',
        border: '1px solid var(--border-strong)',
      }}>
        <div style={{ maxWidth: '600px' }}>
          <div className="section-label" style={{ marginBottom: 6 }}>Ready for Execution</div>
          <h2 style={{ fontSize: '1.4rem', marginBottom: 8 }}>Automate Your Strategy Without Code Friction</h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Launch multiple isolated paper accounts, test tactical configurations against historical market crashes, and let autonomous multi-agent algorithms execute your trades.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={() => navigate('/paper')}
            className="btn-primary"
            style={{ padding: '12px 24px', fontSize: '0.9rem' }}
          >
            <Bot size={16} />
            <span>Launch Bot Now</span>
          </button>
        </div>
      </section>

    </div>
  );
};

export default Welcome;
