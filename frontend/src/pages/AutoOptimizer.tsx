import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Zap, Info, RefreshCw } from 'lucide-react';

interface OptimizationRun {
  id: number;
  status: string;
  triggered_by: string;
  strategy_name: string;
  lookback_months: number;
  best_params_json: Record<string, number> | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export const AutoOptimizer: React.FC = () => {
  const [history, setHistory] = useState<OptimizationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/v1/optimization/history');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          setHistory(data);
        } else {
          console.error("Invalid data format received:", data);
        }
      } else {
        console.error(`API Error: ${res.status} ${res.statusText}`);
      }
    } catch (e) {
      console.error("Failed to fetch optimization history", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    const interval = setInterval(fetchHistory, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleForceOptimize = async () => {
    if (!window.confirm("Bu işlem arka planda yoğun bir Optuna optimizasyon süreci başlatacaktır (Yaklaşık 3-5 dakika sürebilir). Onaylıyor musunuz?")) {
      return;
    }
    
    setTriggering(true);
    try {
      const res = await fetch('/api/v1/optimization/force', { method: 'POST' });
      if (res.ok) {
        alert("Optimizasyon tetiklendi! Durumu tablodan takip edebilirsiniz.");
        await fetchHistory();
      } else {
        alert("Tetikleme başarısız oldu.");
      }
    } catch (e) {
      console.error(e);
      alert("Bir hata oluştu.");
    } finally {
      setTriggering(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED': return <span className="badge badge-success">Tamamlandı</span>;
      case 'RUNNING': return <span className="badge badge-warning animate-pulse">Çalışıyor</span>;
      case 'FAILED': return <span className="badge badge-danger">Hata</span>;
      default: return <span className="badge badge-muted">{status}</span>;
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}
    >
      {/* Header & Trigger */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ marginBottom: 4 }}>Auto-Optimizer</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Machine-learning driven hyperparameter tuning and self-adapting risk calibration
          </p>
        </div>
        <button 
          onClick={handleForceOptimize} 
          disabled={triggering || history.some(h => h.status === 'RUNNING')}
          className="btn-primary"
          style={{ fontSize: '0.9rem', padding: '10px 18px' }}
        >
          {triggering ? <RefreshCw size={15} className="animate-spin" /> : <Zap size={15} />}
          {triggering ? "Tetikleniyor…" : "Force Optimize"}
        </button>
      </div>

      {/* Guide Card */}
      <div className="card" style={{ padding: '20px 24px', background: 'var(--bg-raised)', border: '1px solid var(--border)' }}>
        <h2 style={{ fontSize: '1rem', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-primary)' }}>
          <Info size={16} /> Otomatik Hiperparametre Eğitimi
        </h2>
        <ul style={{ listStyleType: 'disc', paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 6, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          <li>Sistem, değişen piyasa koşullarına göre en karlı Take Profit ve Stop Loss oranlarını bulmak için periyodik Optuna modelleri çalıştırır.</li>
          <li>Beklemek istemediğinizde <strong>"Force Optimize"</strong> butonuna basarak anlık arka plan eğitim turunu tetikleyebilirsiniz.</li>
          <li>Eğitim tamamlandığında bulunan yeni optimal katsayılar bir sonraki işlem döngüsünde <strong>otomatik olarak</strong> devreye girer.</li>
        </ul>
      </div>

      {/* Optimization History Table */}
      <div className="card" style={{ padding: '22px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>Optimizasyon Geçmişi</h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Toplam: {history.length}
          </span>
        </div>

        {loading && history.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>Yükleniyor…</div>
        ) : history.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            Henüz bir optimizasyon kaydı bulunmuyor. Üstteki butonla ilk optimizasyonu başlatabilirsiniz!
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="glass-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Tarih</th>
                  <th>Tetikleyici</th>
                  <th>Geçmiş Süre</th>
                  <th>Durum</th>
                  <th>Bulunan En İyi Parametreler</th>
                  <th>Hata / Mesaj</th>
                </tr>
              </thead>
              <tbody>
                {history.map(run => (
                  <tr key={run.id}>
                    <td className="mono" style={{ color: 'var(--text-muted)' }}>#{run.id}</td>
                    <td className="mono" style={{ fontSize: '0.8rem' }}>{new Date(run.created_at).toLocaleString('tr-TR')}</td>
                    <td><span className="badge badge-primary">{run.triggered_by}</span></td>
                    <td className="mono">{run.lookback_months} Ay</td>
                    <td>{getStatusBadge(run.status)}</td>
                    <td>
                      {(() => {
                        let paramsObj = run.best_params_json;
                        if (typeof paramsObj === 'string') {
                          try {
                            paramsObj = JSON.parse(paramsObj);
                          } catch (e) {
                            paramsObj = null;
                          }
                        }
                        
                        if (paramsObj && typeof paramsObj === 'object') {
                          return (
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                              {Object.entries(paramsObj).map(([k, v]) => (
                                <span key={k} className="badge badge-muted" style={{ padding: '3px 8px', fontSize: '0.7rem' }}>
                                  {k}: <strong style={{ color: 'var(--text-primary)', marginLeft: 4 }}>{String(v)}</strong>
                                </span>
                              ))}
                            </div>
                          );
                        }
                        return <span className="text-muted italic">—</span>;
                      })()}
                    </td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--danger)', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {run.error_message || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </motion.div>
  );
};
