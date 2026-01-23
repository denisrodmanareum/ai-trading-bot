import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function DashboardV2() {
  const navigate = useNavigate();

  // State
  const [loading, setLoading] = useState(true);
  const [balance, setBalance] = useState({ balance: 0, available_balance: 0, unrealized_pnl: 0 });
  const [positions, setPositions] = useState([]);
  const [recentTrades, setRecentTrades] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 5000); // 5초마다 갱신 (가벼우므로)
    return () => clearInterval(interval);
  }, []);

  const fetchAllData = async () => {
    try {
      const [balanceRes, positionsRes, tradesRes] = await Promise.all([
        fetch('/api/trading/balance'),
        fetch('/api/positions'),
        fetch('/api/history/trades?limit=5')
      ]);

      if (balanceRes.ok) setBalance(await balanceRes.json());
      if (positionsRes.ok) {
         const posData = await positionsRes.json();
         // positions API returns { positions: [...] } or array directly depending on implementation
         // Based on previous check, it returns { positions: [...] }
         setPositions(posData.positions || []);
      }
      if (tradesRes.ok) {
        const tradeData = await tradesRes.json();
        setRecentTrades(tradeData.trades || []);
      }

      setLoading(false);
      setError(null);
    } catch (e) {
      console.error('Failed to fetch dashboard data:', e);
      setError('데이터를 불러오는 중 오류가 발생했습니다.');
      setLoading(false);
    }
  };

  const handleClosePosition = async (symbol) => {
    if (!window.confirm(`${symbol} 포지션을 종료하시겠습니까?`)) return;
    try {
      const res = await fetch(`/api/trading/close-position/${symbol}`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        alert("포지션이 종료되었습니다.");
        fetchAllData();
      } else {
        alert(`종료 실패: ${data.detail || data.message}`);
      }
    } catch (e) {
      alert(`오류: ${e.message}`);
    }
  };

  // Safe Accessors
  const totalBalance = balance.balance || 0;
  const unrealizedPnl = balance.unrealized_pnl || 0;
  const pnlColor = unrealizedPnl >= 0 ? '#00b07c' : '#ff4b4b';

  // Format Helpers
  const formatMoney = (val) => val ? `$${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '$0.00';
  const formatPct = (val) => val ? `${Number(val).toFixed(2)}%` : '0.00%';

  if (loading && !balance.balance) { // 초기 로딩만 표시
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#000', color: '#666' }}>
        <div className="animate-pulse">Loading...</div>
      </div>
    );
  }

  return (
    <div style={{ background: '#050505', minHeight: '100vh', color: '#e0e0e0', padding: '1.5rem', fontFamily: '"Inter", sans-serif' }}>
      
      {/* 1. Status Header */}
      <header style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '2rem',
        padding: '1rem',
        borderBottom: '1px solid #222'
      }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: '800', margin: 0, color: '#fff', letterSpacing: '-0.02em' }}>
            ANGEL AREUM BOT <span style={{ fontSize: '0.8rem', color: '#00b07c', background: 'rgba(0,176,124,0.1)', padding: '2px 8px', borderRadius: '12px', verticalAlign: 'middle', marginLeft: '8px' }}>● ONLINE</span>
          </h1>
          <p style={{ fontSize: '0.8rem', color: '#666', marginTop: '0.25rem' }}>Automated Trading System v4.0</p>
        </div>
        
        <div style={{ textAlign: 'right' }}>
           <div style={{ fontSize: '0.7rem', color: '#888', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Balance</div>
           <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#fff' }}>{formatMoney(totalBalance)}</div>
           <div style={{ fontSize: '0.8rem', color: pnlColor }}>
             {unrealizedPnl >= 0 ? '+' : ''}{formatMoney(unrealizedPnl)} (Unrealized)
           </div>
        </div>
      </header>

      {/* 2. Main Content */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem' }}>
        
        {/* Active Positions Card */}
        <div style={{ background: '#0a0a0a', border: '1px solid #1a1a1a', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 4px 20px rgba(0,0,0,0.2)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
             <h2 style={{ fontSize: '1.1rem', fontWeight: '700', margin: 0 }}>📊 Active Positions</h2>
             {positions.length > 0 && <span style={{ fontSize: '0.7rem', background: '#222', padding: '2px 8px', borderRadius: '4px' }}>{positions.length} OPEN</span>}
          </div>

          {positions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem 0', color: '#444' }}>
              <div style={{ fontSize: '2rem', marginBottom: '1rem', opacity: 0.3 }}>💤</div>
              <p>현재 열린 포지션이 없습니다.</p>
              <p style={{ fontSize: '0.8rem' }}>AI가 진입 기회를 분석하고 있습니다.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {positions.map((pos, idx) => {
                const isLong = Number(pos.position_amt) > 0;
                const pnl = Number(pos.unRealizedProfit);
                const roe = (pnl / (Number(pos.initialMargin) || 1)) * 100; // Approx ROE
                
                return (
                  <div key={idx} style={{ 
                    padding: '1rem', 
                    background: '#111', 
                    borderRadius: '8px', 
                    borderLeft: `4px solid ${pnl >= 0 ? '#00b07c' : '#ff4b4b'}` 
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                      <span style={{ fontWeight: '700', fontSize: '1rem' }}>{pos.symbol}</span>
                      <span style={{ 
                        color: isLong ? '#00b07c' : '#ff4b4b', 
                        background: isLong ? 'rgba(0,176,124,0.1)' : 'rgba(255,75,75,0.1)',
                        padding: '2px 6px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 'bold'
                      }}>
                        {isLong ? 'LONG' : 'SHORT'} {pos.leverage}x
                      </span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                       <div>
                         <div style={{ fontSize: '0.7rem', color: '#666' }}>Entry Price</div>
                         <div style={{ fontSize: '0.9rem' }}>{Number(pos.entryPrice).toLocaleString()}</div>
                       </div>
                       <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: '0.7rem', color: '#666' }}>PnL (ROE)</div>
                          <div style={{ fontSize: '0.9rem', fontWeight: '700', color: pnl >= 0 ? '#00b07c' : '#ff4b4b' }}>
                            {pnl >= 0 ? '+' : ''}{Number(pnl).toFixed(2)} ({roe.toFixed(2)}%)
                          </div>
                       </div>
                    </div>

                    <button 
                      onClick={() => handleClosePosition(pos.symbol)}
                      style={{ 
                        width: '100%', 
                        padding: '0.5rem', 
                        background: '#1a1a1a', 
                        border: '1px solid #333', 
                        color: '#aaa', 
                        borderRadius: '4px', 
                        cursor: 'pointer',
                        fontSize: '0.8rem',
                        transition: 'all 0.2s'
                      }}
                      onMouseOver={(e) => { e.target.style.background = '#222'; e.target.style.color = '#fff'; }}
                      onMouseOut={(e) => { e.target.style.background = '#1a1a1a'; e.target.style.color = '#aaa'; }}
                    >
                      Close Position
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recent Activity Card */}
        <div style={{ background: '#0a0a0a', border: '1px solid #1a1a1a', borderRadius: '12px', padding: '1.5rem' }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: '700', marginBottom: '1.5rem' }}>📜 Recent Activity</h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
             {recentTrades.length === 0 ? (
               <div style={{ color: '#444', fontStyle: 'italic', fontSize: '0.9rem' }}>최근 거래 내역이 없습니다.</div>
             ) : (
               recentTrades.map((trade, idx) => (
                 <div key={idx} style={{ 
                   display: 'flex', 
                   justifyContent: 'space-between', 
                   alignItems: 'center',
                   padding: '0.75rem', 
                   background: '#111', 
                   borderRadius: '6px',
                   borderBottom: '1px solid #1a1a1a'
                 }}>
                    <div>
                      <div style={{ fontSize: '0.85rem', fontWeight: '600' }}>{trade.symbol} <span style={{ color: '#666', fontWeight: '400' }}>{trade.action}</span></div>
                      <div style={{ fontSize: '0.7rem', color: '#555' }}>
                         {new Date(trade.timestamp).toLocaleString('ko-KR', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                       <div style={{ fontSize: '0.85rem', color: (trade.pnl || 0) >= 0 ? '#00b07c' : '#ff4b4b', fontWeight: '700' }}>
                         {(trade.pnl || 0) !== 0 ? `$${Number(trade.pnl).toFixed(2)}` : 'OPEN'}
                       </div>
                       <div style={{ fontSize: '0.7rem', color: '#555' }}>{trade.strategy || 'System'}</div>
                    </div>
                 </div>
               ))
             )}
          </div>
          
          <button 
            onClick={() => navigate('/history')}
            style={{ 
              marginTop: '1rem', 
              width: '100%', 
              background: 'transparent', 
              color: '#666', 
              border: '1px dashed #333', 
              padding: '0.5rem', 
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.8rem'
            }}
          >
            View Full History →
          </button>
        </div>

      </div>
      
    </div>
  );
}

export default DashboardV2;
