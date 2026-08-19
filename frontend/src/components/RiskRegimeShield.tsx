import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Shield } from 'lucide-react';

interface RegimeSnapshot {
  btc_regime: string;
  confidence: number;
  risk_multiplier: number;
}

interface RiskSnapshot {
  max_drawdown_limit_pct: number;
  current_drawdown_pct: number;
  gross_exposure_pct: number;
  correlated_symbols_count: number;
  max_positions_allowed: number;
}

interface RiskRegimeData {
  timestamp: string;
  system_status: string;
  trading_mode: string;
  regime_snapshot: RegimeSnapshot;
  risk_snapshot: RiskSnapshot;
}

const RiskRegimeShield: React.FC = () => {
  const [data, setData] = useState<RiskRegimeData | null>(null);
  const [wsConnected, setWsConnected] = useState<boolean>(false);

  const fetchSnapshot = async () => {
    try {
      const apiBase = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : '/api/v1';
      const res = await axios.get(`${apiBase}/ws/risk-regime/snapshot`);
      if (res.data) {
        setData(res.data);
      }
    } catch (err) {
      console.error('Error fetching risk-regime snapshot:', err);
    }
  };

  useEffect(() => {
    fetchSnapshot();

    const isSecure = window.location.protocol === 'https:' || (import.meta.env.VITE_API_URL && import.meta.env.VITE_API_URL.startsWith('https'));
    const protocol = isSecure ? 'wss:' : 'ws:';
    let host = window.location.host;
    if (import.meta.env.VITE_API_URL) {
      try {
        host = new URL(import.meta.env.VITE_API_URL).host;
      } catch (e) {
        // fallback
      }
    }
    const wsUrl = `${protocol}//${host}/api/v1/ws/risk-regime`;
    let ws: WebSocket | null = null;
    let fallbackInterval: ReturnType<typeof setInterval> | null = null;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed && parsed.regime_snapshot) {
            setData(parsed);
          }
        } catch (e) {
          console.error('Error parsing WS risk payload:', e);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        fallbackInterval = setInterval(fetchSnapshot, 5000);
      };

      ws.onerror = () => {
        setWsConnected(false);
      };
    } catch (err) {
      setWsConnected(false);
      fallbackInterval = setInterval(fetchSnapshot, 5000);
    }

    return () => {
      if (ws) ws.close();
      if (fallbackInterval) clearInterval(fallbackInterval);
    };
  }, []);

  if (!data) {
    return (
      <div className="card" style={{ padding: '20px 24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <Shield size={18} className="animate-spin text-muted" />
        <span className="text-muted" style={{ fontSize: '0.85rem' }}>Risk & Rejim Kalkanı Başlatılıyor…</span>
      </div>
    );
  }

  const { regime_snapshot, risk_snapshot, trading_mode, system_status } = data;
  const isBull = regime_snapshot.btc_regime?.includes('BULL');
  const isBear = regime_snapshot.btc_regime?.includes('BEAR');

  const borderColor = isBull
    ? 'rgba(16, 185, 129, 0.4)'
    : isBear
    ? 'rgba(244, 63, 94, 0.4)'
    : 'var(--border-strong)';

  const glowShadow = isBull
    ? '0 0 24px rgba(16, 185, 129, 0.08)'
    : isBear
    ? '0 0 24px rgba(244, 63, 94, 0.08)'
    : 'var(--shadow)';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="card"
      style={{
        padding: '20px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '18px',
        borderColor: borderColor,
        boxShadow: glowShadow,
        position: 'relative',
      }}
    >
      {/* Top Header Row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 8,
            background: 'var(--accent-soft)', border: '1px solid var(--accent-border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <Shield size={15} color="var(--text-primary)" />
          </div>
          <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
            Risk & Rejim Kalkanı
          </span>
          <span className={`badge ${wsConnected ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '0.68rem', padding: '2px 7px' }}>
            {wsConnected ? '● WS Canlı' : '○ Polling Aktif'}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge badge-primary" style={{ fontWeight: 700 }}>
            {trading_mode} MODU
          </span>
          <span className="badge badge-muted">
            Sistem: {system_status}
          </span>
        </div>
      </div>

      {/* 4 Bento Stat Columns */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
        
        {/* BTC Market Regime */}
        <div style={{
          padding: '14px 16px',
          borderRadius: 'var(--radius-sm)',
          background: 'var(--bg-raised)',
          border: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <span className="section-label">BTC Piyasa Rejimi</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', margin: '2px 0' }}>
            <span
              className="stat-value"
              style={{
                color: isBull ? 'var(--success)' : isBear ? 'var(--danger)' : 'var(--text-primary)',
                fontSize: '1.25rem',
              }}
            >
              {regime_snapshot.btc_regime || 'NEUTRAL'}
            </span>
          </div>
          <span className="text-muted mono" style={{ fontSize: '0.75rem' }}>
            Güven: %{(regime_snapshot.confidence * 100).toFixed(1)}
          </span>
        </div>

        {/* Risk Multiplier */}
        <div style={{
          padding: '14px 16px',
          borderRadius: 'var(--radius-sm)',
          background: 'var(--bg-raised)',
          border: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <span className="section-label">Risk Çarpanı</span>
          <div className="stat-value" style={{ fontSize: '1.25rem', color: 'var(--text-primary)', margin: '2px 0' }}>
            {regime_snapshot.risk_multiplier?.toFixed(2)}x
          </div>
          <span className="text-muted mono" style={{ fontSize: '0.75rem' }}>
            ATR Stop & Boyut Çarpanı
          </span>
        </div>

        {/* Drawdown Gauge */}
        <div style={{
          padding: '14px 16px',
          borderRadius: 'var(--radius-sm)',
          background: 'var(--bg-raised)',
          border: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <span className="section-label">Drawdown Kalkanı</span>
          <div className="stat-value" style={{ fontSize: '1.25rem', color: 'var(--text-primary)', margin: '2px 0' }}>
            %{risk_snapshot.current_drawdown_pct?.toFixed(2)} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>/ %{risk_snapshot.max_drawdown_limit_pct?.toFixed(0)}</span>
          </div>
          <span className="text-muted mono" style={{ fontSize: '0.75rem' }}>
            Maksimum Portföy Riski
          </span>
        </div>

        {/* Correlated Assets */}
        <div style={{
          padding: '14px 16px',
          borderRadius: 'var(--radius-sm)',
          background: 'var(--bg-raised)',
          border: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <span className="section-label">Korele Varlık Matrisi</span>
          <div className="stat-value" style={{ fontSize: '1.25rem', color: 'var(--text-primary)', margin: '2px 0' }}>
            {risk_snapshot.correlated_symbols_count} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Coin</span>
          </div>
          <span className="text-muted mono" style={{ fontSize: '0.75rem' }}>
            BTC ile Yüksek Korelasyon
          </span>
        </div>

      </div>
    </motion.div>
  );
};

export default RiskRegimeShield;
