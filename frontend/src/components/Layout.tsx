import React, { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, FlaskConical, Bot, Terminal, Zap,
  Sun, Moon, TrendingUp, Cpu, Home
} from 'lucide-react';
import { motion } from 'framer-motion';
import api from '../services/api';

const NAV_ITEMS = [
  { to: '/',            label: 'Home',           icon: Home, end: true },
  { to: '/dashboard',   label: 'Overview',       icon: LayoutDashboard },
  { to: '/radar',       label: 'Market Radar',   icon: TrendingUp },
  { to: '/paper',       label: 'Paper Trading',  icon: Bot },
  { to: '/backtesting', label: 'Backtesting',    icon: FlaskConical },
  { to: '/optimization',label: 'Auto-Optimizer', icon: Zap },
  { to: '/logs',        label: 'System Logs',    icon: Terminal },
];

const Layout: React.FC = () => {
  const navigate = useNavigate();
  const [theme, setTheme] = useState<'light' | 'dark'>(() =>
    (localStorage.getItem('theme') as 'light' | 'dark') || 'dark'
  );
  const [sysOnline, setSysOnline] = useState<boolean | null>(null);

  useEffect(() => {
    localStorage.setItem('theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  useEffect(() => {
    const check = async () => {
      try { 
        await api.get('/health'); 
        setSysOnline(true); 
      } catch { 
        setSysOnline(false); 
      }
    };
    check();
    const iv = setInterval(check, 15000);
    return () => clearInterval(iv);
  }, []);

  const toggleTheme = () => setTheme(p => p === 'light' ? 'dark' : 'light');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', position: 'relative' }}>

      {/* Ambient Bottom Glow Light */}
      <div className="ambient-bottom-glow" />

      {/* ── Permanent Floating Minimalist Top Navbar ─────────── */}
      <div style={{
        position: 'fixed',
        top: 16,
        left: 0,
        right: 0,
        width: '100%',
        zIndex: 100,
        display: 'flex',
        justifyContent: 'center',
        pointerEvents: 'none',
      }}>
        <header
          style={{
            width: '92%',
            maxWidth: '1200px',
            height: 56,
            borderRadius: '9999px',
            padding: '0 20px',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.45)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 16,
            pointerEvents: 'auto',
          }}
        >

          {/* Left: Brand Logo */}
          <div
            onClick={() => navigate('/')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              cursor: 'pointer',
              userSelect: 'none',
              flexShrink: 0,
            }}
          >
            <div style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              background: 'var(--text-primary)',
              color: 'var(--bg-base)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px rgba(255, 255, 255, 0.2)',
              flexShrink: 0,
            }}>
              <Cpu size={17} />
            </div>
            <div>
              <div style={{
                fontWeight: 800,
                fontSize: '0.92rem',
                letterSpacing: '-0.02em',
                color: 'var(--text-primary)',
                lineHeight: 1.1,
                whiteSpace: 'nowrap',
              }}>
                Crypto MAS
              </div>
              <div style={{
                fontSize: '0.6rem',
                color: 'var(--text-muted)',
                marginTop: 1,
                letterSpacing: '0.08em',
                fontWeight: 600,
                textTransform: 'uppercase',
                whiteSpace: 'nowrap',
              }}>
                LaunchPad Engine
              </div>
            </div>
          </div>

          {/* Center: Sliding Pill Nav Items */}
          <nav style={{
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            background: 'var(--bg-raised)',
            padding: '3px',
            borderRadius: 'var(--radius-full)',
            border: '1px solid var(--border)',
            flexShrink: 0,
          }}>
            {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                style={{ textDecoration: 'none', position: 'relative', display: 'block' }}
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <motion.div
                        layoutId="top-nav-active-pill"
                        style={{
                          position: 'absolute',
                          inset: 0,
                          background: 'var(--text-primary)',
                          borderRadius: 'var(--radius-full)',
                          zIndex: 0,
                        }}
                        transition={{ type: 'spring', stiffness: 450, damping: 35 }}
                      />
                    )}
                    <div style={{
                      position: 'relative',
                      zIndex: 1,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      padding: '5px 12px',
                      borderRadius: 'var(--radius-full)',
                      fontSize: '0.78rem',
                      fontWeight: isActive ? 700 : 500,
                      color: isActive ? 'var(--bg-base)' : 'var(--text-muted)',
                      transition: 'color 0.15s ease',
                      whiteSpace: 'nowrap',
                    }}>
                      <Icon size={13} style={{ flexShrink: 0 }} />
                      <span>{label}</span>
                    </div>
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          {/* Right: Status, Theme & Action CTA */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            flexShrink: 0,
            whiteSpace: 'nowrap',
          }}>
            
            {/* Live Online/Offline Status Indicator */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 10px',
              background: 'var(--bg-raised)',
              borderRadius: 'var(--radius-full)',
              border: '1px solid var(--border)',
              flexShrink: 0,
            }}>
              {sysOnline === null ? (
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--text-muted)' }} />
              ) : sysOnline ? (
                <motion.div
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: 'var(--success)',
                    boxShadow: '0 0 6px var(--success)',
                  }}
                />
              ) : (
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--danger)' }} />
              )}
              <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                {sysOnline === null ? 'Checking…' : sysOnline ? 'Online' : 'Offline'}
              </span>
            </div>

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="btn-ghost"
              style={{ width: 30, height: 30, padding: 0, borderRadius: 'var(--radius-sm)', flexShrink: 0 }}
              title="Toggle theme"
            >
              {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
            </button>

            {/* Launch Bot CTA */}
            <button
              onClick={() => navigate('/paper')}
              className="btn-primary"
              style={{
                padding: '6px 14px',
                fontSize: '0.78rem',
                borderRadius: 'var(--radius-full)',
                flexShrink: 0,
              }}
            >
              <Bot size={13} />
              <span>Launch Bot</span>
            </button>
          </div>

        </header>
      </div>

      {/* ── Main Viewport Content ─────────────────────────────── */}
      <main style={{
        flex: 1,
        padding: '92px 32px 48px',
        position: 'relative',
        zIndex: 1,
      }}>
        <Outlet />
      </main>

    </div>
  );
};

export default Layout;
