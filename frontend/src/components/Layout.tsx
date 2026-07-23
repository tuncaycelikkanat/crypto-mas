import React, { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, FlaskConical, Bot, Terminal, Zap,
  Sun, Moon, TrendingUp, Activity, Wifi, WifiOff
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

const NAV_ITEMS = [
  { to: '/',            label: 'Overview',       icon: LayoutDashboard, end: true },
  { to: '/radar',       label: 'Market Radar',   icon: TrendingUp },
  { to: '/paper',       label: 'Paper Trading',  icon: Bot },
  { to: '/backtesting', label: 'Backtesting',    icon: FlaskConical },
  { to: '/optimization',label: 'Auto-Optimizer', icon: Zap },
  { to: '/logs',        label: 'System Logs',    icon: Terminal },
];

const Layout: React.FC = () => {
  const [theme, setTheme] = useState<'light' | 'dark'>(() =>
    (localStorage.getItem('theme') as 'light' | 'dark') || 'dark'
  );
  const [sysOnline, setSysOnline] = useState<boolean | null>(null);
  const location = useLocation();

  useEffect(() => {
    localStorage.setItem('theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  useEffect(() => {
    const check = async () => {
      try { await axios.get('/api/v1/health'); setSysOnline(true); }
      catch { setSysOnline(false); }
    };
    check();
    const iv = setInterval(check, 15000);
    return () => clearInterval(iv);
  }, []);

  const toggleTheme = () => setTheme(p => p === 'light' ? 'dark' : 'light');

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>

      {/* ── Sidebar ─────────────────────────────────────────── */}
      <aside className="glass-panel" style={{
        width: 228,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        position: 'sticky',
        top: 0,
        height: '100vh',
        zIndex: 50,
      }}>

        {/* Brand */}
        <div style={{ padding: '20px 18px 16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 34, height: 34, borderRadius: 10,
            background: 'linear-gradient(135deg, var(--accent), var(--accent-hover))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 14px var(--primary-glow)',
            flexShrink: 0,
          }}>
            <Activity size={17} color="white" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.95rem', letterSpacing: '-0.01em', color: 'var(--text-primary)' }}>
              Crypto MAS
            </div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 1, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              Multi-Agent System
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '14px 10px', display: 'flex', flexDirection: 'column', gap: 4, position: 'relative' }}>
          <div className="section-label" style={{ padding: '4px 10px 10px' }}>Navigation</div>
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} style={{ textDecoration: 'none', position: 'relative', display: 'block' }}>
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.div
                      layoutId="nav-active"
                      style={{
                        position: 'absolute', inset: 0,
                        background: 'var(--accent-soft)',
                        borderRadius: 10, zIndex: 0,
                        border: '1px solid var(--accent-border)',
                      }}
                      transition={{ type: 'spring', stiffness: 320, damping: 32 }}
                    />
                  )}
                  <div style={{
                    position: 'relative', zIndex: 1,
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '10px 12px', borderRadius: 10,
                    fontSize: '0.875rem',
                    fontWeight: isActive ? 600 : 500,
                    color: isActive ? 'var(--accent)' : 'var(--text-muted)',
                    transition: 'color 0.2s',
                  }}>
                    <Icon size={17} style={{ flexShrink: 0, opacity: isActive ? 1 : 0.65 }} />
                    <span>{label}</span>
                  </div>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div style={{ padding: '12px 14px', borderTop: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            {sysOnline === null
              ? <div style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--text-muted)' }} />
              : sysOnline
                ? <motion.div
                    animate={{ opacity: [1, 0.4, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--success)', boxShadow: '0 0 6px var(--success)' }}
                  />
                : <div style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--danger)' }} />
            }
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              {sysOnline === null ? 'Checking…' : sysOnline ? 'System Online' : 'Offline'}
            </span>
          </div>
          <button
            onClick={toggleTheme}
            className="btn-ghost"
            style={{ width: 30, height: 30, padding: 0, borderRadius: 8, fontSize: '0.85rem' }}
            title="Toggle theme"
          >
            {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
          </button>
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────────────────── */}
      <main style={{ flex: 1, minWidth: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>

        {/* Top bar */}
        <header style={{
          height: 52, padding: '0 32px',
          borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: 'var(--bg-surface)',
          backdropFilter: 'var(--glass-blur)',
          position: 'sticky', top: 0, zIndex: 40, flexShrink: 0,
        }}>
          <div /> {/* left spacer */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {sysOnline ? <Wifi size={13} color="var(--success)" /> : <WifiOff size={13} color="var(--danger)" />}
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                API {sysOnline ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {new Date().toLocaleDateString('tr-TR', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}
            </span>
          </div>
        </header>

        {/* Page */}
        <div style={{ flex: 1, padding: '28px 32px' }}>
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
};

export default Layout;
