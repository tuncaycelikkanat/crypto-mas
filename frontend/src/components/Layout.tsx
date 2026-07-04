import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, History, PlaySquare, LineChart } from 'lucide-react';

const Layout: React.FC = () => {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', width: '100%' }}>
      {/* Sidebar */}
      <aside className="glass-panel" style={{ width: '260px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ background: 'var(--primary)', width: '32px', height: '32px', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <LineChart size={20} color="white" />
          </div>
          <h2 style={{ fontSize: '1.25rem', margin: 0 }} className="text-gradient">Crypto MAS</h2>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <NavLink to="/" end style={({isActive}) => ({
            display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px', 
            borderRadius: '12px', color: isActive ? 'white' : 'var(--text-muted)',
            background: isActive ? 'rgba(139, 92, 246, 0.15)' : 'transparent',
            textDecoration: 'none', transition: 'all 0.2s',
            border: isActive ? '1px solid rgba(139, 92, 246, 0.3)' : '1px solid transparent'
          })}>
            <LayoutDashboard size={20} />
            <span style={{ fontWeight: 500 }}>Overview</span>
          </NavLink>

          <NavLink to="/backtesting" style={({isActive}) => ({
            display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px', 
            borderRadius: '12px', color: isActive ? 'white' : 'var(--text-muted)',
            background: isActive ? 'rgba(139, 92, 246, 0.15)' : 'transparent',
            textDecoration: 'none', transition: 'all 0.2s',
            border: isActive ? '1px solid rgba(139, 92, 246, 0.3)' : '1px solid transparent'
          })}>
            <PlaySquare size={20} />
            <span style={{ fontWeight: 500 }}>Backtesting</span>
          </NavLink>

          <NavLink to="/decisions" style={({isActive}) => ({
            display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px', 
            borderRadius: '12px', color: isActive ? 'white' : 'var(--text-muted)',
            background: isActive ? 'rgba(139, 92, 246, 0.15)' : 'transparent',
            textDecoration: 'none', transition: 'all 0.2s',
            border: isActive ? '1px solid rgba(139, 92, 246, 0.3)' : '1px solid transparent'
          })}>
            <History size={20} />
            <span style={{ fontWeight: 500 }}>Decisions</span>
          </NavLink>
        </nav>
      </aside>

      {/* Main Content */}
      <main style={{ flex: 1, padding: '32px 48px', overflowY: 'auto' }}>
        <header style={{ display: 'flex', justifyContent: 'flex-end', paddingBottom: '32px' }}>
          <div className="glass-card" style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '8px', borderRadius: '999px' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)', boxShadow: '0 0 10px var(--success)' }}></div>
            <span style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-muted)' }}>System Online</span>
          </div>
        </header>

        <div className="animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default Layout;
