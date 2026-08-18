import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';

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
      <div className="card" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span className="text-muted">Shield Engine Başlatılıyor...</span>
      </div>
    );
  }

  const { regime_snapshot, risk_snapshot, trading_mode, system_status } = data;
  const isBull = regime_snapshot.btc_regime.includes('BULL');
  const isBear = regime_snapshot.btc_regime.includes('BEAR');

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="card"
      style={{
        padding: '20px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        borderLeft: isBull
          ? '4px solid var(--success)'
          : isBear
          ? '4px solid var(--danger)'
          : '4px solid var(--accent)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '1.15rem', fontWeight: 600 }} className="text-primary">
            🛡️ Canlı Risk & Rejim Kalkanı
          </span>
          <span className={wsConnected ? 'badge-success' : 'badge-warning'} style={{ fontSize: '0.75rem', padding: '2px 8px' }}>
            {wsConnected ? '● WS Canlı' : '○ Polling Aktif'}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge-primary">{trading_mode} MODU</span>
          <span className="badge-muted">Sistem: {system_status}</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
        {/* BTC Market Regime */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '12px', borderRadius: '8px', background: 'var(--bg-surface)' }}>
          <span className="section-label">BTC Piyasa Rejimi</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span
              className="stat-value"
              style={{
                color: isBull ? 'var(--success)' : isBear ? 'var(--danger)' : 'var(--text-primary)',
                fontSize: '1.25rem',
              }}
            >
              {regime_snapshot.btc_regime}
            </span>
          </div>
          <span className="text-muted" style={{ fontSize: '0.8rem' }}>
            Güven: %{(regime_snapshot.confidence * 100).toFixed(1)}
          </span>
        </div>

        {/* Risk Multiplier */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '12px', borderRadius: '8px', background: 'var(--bg-surface)' }}>
          <span className="section-label">Risk Çarpanı</span>
          <span className="stat-value text-primary" style={{ fontSize: '1.25rem' }}>
            {regime_snapshot.risk_multiplier.toFixed(2)}x
          </span>
          <span className="text-muted" style={{ fontSize: '0.8rem' }}>
            ATR Stop & Boyut Çarpanı
          </span>
        </div>

        {/* Drawdown Gauge */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '12px', borderRadius: '8px', background: 'var(--bg-surface)' }}>
          <span className="section-label">Drawdown Kalkanı</span>
          <span className="stat-value text-primary" style={{ fontSize: '1.25rem' }}>
            %{risk_snapshot.current_drawdown_pct.toFixed(2)} / %{risk_snapshot.max_drawdown_limit_pct.toFixed(0)}
          </span>
          <span className="text-muted" style={{ fontSize: '0.8rem' }}>
            Maksimum Portföy Riski
          </span>
        </div>

        {/* Correlated Assets */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '12px', borderRadius: '8px', background: 'var(--bg-surface)' }}>
          <span className="section-label">Korele Varlık Matrisi</span>
          <span className="stat-value text-primary" style={{ fontSize: '1.25rem' }}>
            {risk_snapshot.correlated_symbols_count} Coin
          </span>
          <span className="text-muted" style={{ fontSize: '0.8rem' }}>
            BTC ile Yüksek Korelasyon
          </span>
        </div>
      </div>
    </motion.div>
  );
};

export default RiskRegimeShield;
