import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

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
        setHistory(data);
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
        alert("Optimizasyon tetiklendi! Durumu aşağıdaki tablodan (RUNNING) takip edebilirsiniz.");
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
      case 'COMPLETED': return <span className="badge-success">Tamamlandı</span>;
      case 'RUNNING': return <span className="badge-warning animate-pulse">Çalışıyor</span>;
      case 'FAILED': return <span className="badge-danger">Hata</span>;
      default: return <span className="badge-muted">{status}</span>;
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="p-6 space-y-8"
    >
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold mb-2">🤖 Auto-Optimizer</h1>
          <p className="text-muted">Paper Trading motorunuzun kendi kendini eğittiği geçmiş kayıtları ve manuel tetikleyici.</p>
        </div>
        <button 
          onClick={handleForceOptimize} 
          disabled={triggering || history.some(h => h.status === 'RUNNING')}
          className="btn-primary flex items-center gap-2 px-6 py-3 font-semibold text-lg"
        >
          {triggering ? "Tetikleniyor..." : "⚡ Force Optimize"}
        </button>
      </div>

      <div className="card">
        <h2 className="section-label mb-4">Optimizasyon Geçmişi</h2>
        {loading ? (
          <div className="text-center p-8 text-muted">Yükleniyor...</div>
        ) : history.length === 0 ? (
          <div className="text-center p-8 text-muted border border-dashed border-border-strong rounded-xl">
            Henüz bir optimizasyon kaydı bulunmuyor. Sol üstteki butonla ilk optimizasyonu başlatabilirsiniz!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="glass-table w-full text-left">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Tarih</th>
                  <th>Tetikleyici</th>
                  <th>Geçmiş Süre</th>
                  <th>Durum</th>
                  <th>Bulunan Ayarlar</th>
                  <th>Hata / Mesaj</th>
                </tr>
              </thead>
              <tbody>
                {history.map(run => (
                  <tr key={run.id}>
                    <td className="mono text-muted">#{run.id}</td>
                    <td>{new Date(run.created_at).toLocaleString()}</td>
                    <td><span className="badge-primary">{run.triggered_by}</span></td>
                    <td>{run.lookback_months} Ay</td>
                    <td>{getStatusBadge(run.status)}</td>
                    <td>
                      {run.best_params_json ? (
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(run.best_params_json).map(([k, v]) => (
                            <span key={k} className="bg-surface px-2 py-1 rounded text-xs border border-border text-text-secondary">
                              {k}: <span className="text-accent font-bold">{v}</span>
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-muted italic">-</span>
                      )}
                    </td>
                    <td className="text-sm text-danger max-w-xs truncate">
                      {run.error_message || '-'}
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
