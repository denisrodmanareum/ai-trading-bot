import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import './App.css';

import Dashboard from './pages/Dashboard';
import DashboardV2 from './pages/DashboardV2';
import Trading from './pages/Trading';
import TradingOKX from './pages/TradingOKX';
import TradingPro from './pages/TradingPro';
import TradingPerfect from './pages/TradingPerfect';
import AIHub from './pages/AIHub';
import History from './pages/History';
import Backtest from './pages/Backtest';
import Settings from './pages/Settings';

function AppContent() {
  const location = useLocation();
  const [connected, setConnected] = useState(false);
  const isTradingPage = location.pathname === '/trading';

  useEffect(() => {
    checkServer();
    const interval = setInterval(checkServer, 10000);
    return () => clearInterval(interval);
  }, []);

  const checkServer = async () => {
    try {
      const res = await fetch('/health');
      const data = await res.json();
      setConnected(data.status === 'healthy');
    } catch (err) {
      setConnected(false);
    }
  };

  return (
    <div className="App">
      <nav className="navbar">
        <div className="nav-brand">
          <h1>ANGEL AREUM AI BOT</h1>
          <div className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'currentColor' }}></div>
            {connected ? 'System Live' : 'Offline'}
          </div>
        </div>
        <div className="nav-links">
          <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''}>대시보드</NavLink>
          <NavLink to="/trading" className={({ isActive }) => isActive ? 'active' : ''}>수동 거래</NavLink>
          <NavLink to="/ai-hub" className={({ isActive }) => isActive ? 'active' : ''}>AI 허브</NavLink>
          <NavLink to="/backtest" className={({ isActive }) => isActive ? 'active' : ''}>시뮬레이션</NavLink>
          <NavLink to="/history" className={({ isActive }) => isActive ? 'active' : ''}>성과 분석</NavLink>
          <NavLink to="/settings" className={({ isActive }) => isActive ? 'active' : ''}>설정</NavLink>
        </div>
      </nav>

      <div className={`main-content ${isTradingPage ? 'full-page' : ''}`}>
        <Routes>
          <Route path="/" element={<DashboardV2 />} />
          <Route path="/dashboard-old" element={<Dashboard />} />
          <Route path="/trading" element={<TradingPerfect />} />
          <Route path="/trading-pro" element={<TradingPro />} />
          <Route path="/trading-okx" element={<TradingOKX />} />
          <Route path="/trading-old" element={<Trading />} />
          <Route path="/ai-hub" element={<AIHub />} />
          <Route path="/history" element={<History />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>

      {!isTradingPage && (
        <footer className="footer">
          <div>터미널 코어 v4.0.0 | 보안 엔진</div>
          <div style={{ fontSize: '0.6rem', marginTop: '0.4rem', color: '#444' }}>
            운영자: <span style={{ color: '#fff' }}>riot91</span> · 시스템 상태: 정상 · BTC/USD 실시간 클러스터 활성화
          </div>
        </footer>
      )}
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
