import React, { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, FlaskConical, Bot, Terminal,
  Sun, Moon, TrendingUp, Circle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

const NAV_ITEMS = [
  { to: '/',            label: 'Overview',        icon: LayoutDashboard, end: true },
  { to: '/radar',       label: 'Market Radar',    icon: TrendingUp      },
  { to: '/paper',       label: 'Paper Trading',   icon: Bot             },
  { to: '/backtesting', label: 'Backtesting',     icon: FlaskConical    },
  { to: '/logs',        label: 'System Logs',     icon: Terminal        },
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
      try {
        await axios.get('/api/v1/health');
        setSysOnline(true);
      } catch {
        setSysOnline(false);
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => clearInterval(interval);
  }, []);

  const toggleTheme = () => setTheme(p => p === 'light' ? 'dark' : 'light');

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>

      {/* ── Sidebar ─────────────────────────────────────────── */}
      <aside style={{
        width: 220,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg-sidebar)',
        borderRight: '1px solid var(--border)',
        position: 'sticky',
        top: 0,
        height: '100vh',
        zIndex: 50,
      }}>

        {/* Brand */}
        <div style={{
          padding: '20px 20px 16px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}>
          <div style={{
            width: 30, height: 30, borderRadius: 7,
            background: 'var(--accent)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}>
            <TrendingUp size={16} color="white" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.95rem', letterSpacing: '-0.01em', color: 'var(--text-primary)' }}>
              Crypto MAS
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 1 }}>
              Multi-Agent System
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: 2 }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', padding: '4px 10px 8px' }}>
            Navigation
          </div>
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '8px 10px',
                borderRadius: 6,
                textDecoration: 'none',
                fontSize: '0.875rem',
                fontWeight: isActive ? 600 : 400,
                color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                background: isActive ? 'var(--accent-soft)' : 'transparent',
                transition: 'all 0.15s',
              })}
            >
              {({ isActive }) => (
                <>
                  <Icon size={16} style={{ flexShrink: 0, opacity: isActive ? 1 : 0.7 }} />
                  <span>{label}</span>
                  {isActive && (
                    <div style={{
                      marginLeft: 'auto', width: 5, height: 5, borderRadius: '50%',
                      background: 'var(--accent)',
                    }} />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div style={{
          padding: '12px 10px',
          borderTop: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          {/* System status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <Circle
              size={7}
              style={{
                fill: sysOnline === null ? 'var(--text-muted)' : sysOnline ? 'var(--success)' : 'var(--danger)',
                color: sysOnline === null ? 'var(--text-muted)' : sysOnline ? 'var(--success)' : 'var(--danger)',
              }}
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {sysOnline === null ? 'Checking…' : sysOnline ? 'System Online' : 'Offline'}
            </span>
          </div>

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: 28, height: 28, borderRadius: 6,
              background: 'var(--bg-raised)',
              border: '1px solid var(--border)',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
            title="Toggle theme"
          >
            {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
          </button>
        </div>
      </aside>

      {/* ── Main Content ─────────────────────────────────────── */}
      <main style={{ flex: 1, minWidth: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>

        {/* Top bar */}
        <header style={{
          height: 52,
          padding: '0 32px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          gap: 12,
          background: 'var(--bg-surface)',
          position: 'sticky',
          top: 0,
          zIndex: 40,
          flexShrink: 0,
        }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            {new Date().toLocaleDateString('tr-TR', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}
          </span>
        </header>

        {/* Page */}
        <div style={{ flex: 1, padding: '28px 32px' }}>
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
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
