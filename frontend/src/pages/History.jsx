import React, { useState, useEffect } from 'react';

function History() {
  const [stats, setStats] = useState({
    total_trades: 0,
    wins: 0,
    losses: 0,
    win_rate: 0,
    total_pnl: 0
  });

  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);

  // Helper to format date to KST
  const formatKST = (dateString) => {
    if (!dateString) return '-';
    // Append 'Z' to treat naive string as UTC if needed
    const utcString = dateString.endsWith('Z') ? dateString : dateString + 'Z';
    return new Date(utcString).toLocaleString('ko-KR', {
      timeZone: 'Asia/Seoul',
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    });
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [resStats, resTrades] = await Promise.all([
        fetch('/api/history/stats'),
        fetch('/api/history/trades?limit=100')
      ]);

      const dataStats = await resStats.json();
      const dataTrades = await resTrades.json();

      setStats(dataStats);
      setTrades(dataTrades.trades || []);
      setLoading(false);
    } catch (e) {
      console.error(e);
      setLoading(false);
    }
  };

  const clearHistory = async () => {
    if (!window.confirm("정말로 모든 거래 내역을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")) return;

    try {
      const res = await fetch('/api/history/clear', { method: 'DELETE' });
      if (res.ok) {
        alert("거래 내역이 성공적으로 삭제되었습니다");
        fetchData(); // Refresh
      } else {
        alert("거래 내역 삭제에 실패했습니다");
      }
    } catch (e) {
      console.error(e);
      alert("거래 내역 삭제 중 오류가 발생했습니다");
    }
  };
  const handleSync = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/trading/sync', { method: 'POST' });
      if (res.ok) {
        // alert("거래소 동기화 성공");
        await fetchData(); // Refresh data
      } else {
        alert("동기화 실패");
      }
    } catch (e) {
      console.error(e);
      alert("동기화 중 오류 발생");
    } finally {
      setLoading(false);
    }
  };


  if (loading) return <div className="p-4">거래 내역 로딩 중...</div>;

  return (
    <div className="history-page p-4">
      <header className="mb-4 d-flex justify-content-between align-items-end">
        <div>
          <h1 className="display-6 fw-bold text-white uppercase letter-spacing-lg">운영 로그</h1>
          <p className="text-secondary small uppercase fw-bold">거래 내역 및 성과 통계</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button
            onClick={handleSync}
            style={{
              background: 'transparent',
              color: '#888',
              border: '1px solid #111',
              padding: '0.5rem 1rem',
              borderRadius: '2px',
              cursor: 'pointer',
              fontWeight: '900',
              fontSize: '0.7rem',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}
          >
            거래소 동기화
          </button>
          <button
            onClick={clearHistory}
            style={{
              background: 'transparent',
              color: 'var(--accent-danger)',
              border: '1px solid #111',
              padding: '0.5rem 1rem',
              borderRadius: '2px',
              cursor: 'pointer',
              fontWeight: '900',
              fontSize: '0.7rem',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}
          >
            기록 삭제
          </button>
        </div>
      </header>

      {/* Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
        {[
          { label: '총 수익 (Gross PnL)', val: `$${stats.total_pnl?.toFixed(2)}`, color: 'var(--accent-success)' },
          { label: '총 수수료', val: `-$${stats.total_commission?.toFixed(2)}`, color: 'var(--accent-danger)' },
          { label: '순수익 (Net PnL)', val: `$${stats.net_pnl?.toFixed(2)}`, color: stats.net_pnl >= 0 ? '#fff' : 'var(--accent-danger)' },
          { label: '승률', val: `${stats.win_rate}%`, sub: `${stats.wins}승 / ${stats.losses}패` },
          { label: '총 거래 수', val: stats.total_trades }
        ].map(item => (
          <div key={item.label} className="card" style={{ padding: '1.25rem', marginBottom: 0 }}>
            <div style={{ fontSize: '0.6rem', color: '#444', fontWeight: '900', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.5rem' }}>{item.label}</div>
            <div style={{ fontSize: '1.25rem', fontWeight: '800', fontFamily: 'var(--font-mono)', color: item.color || '#fff' }}>{item.val}</div>
            {item.sub && <div style={{ fontSize: '0.6rem', color: '#333', fontWeight: '900', marginTop: '2px' }}>{item.sub}</div>}
          </div>
        ))}
      </div>

      {/* Trades Table */}
      <div className="card">
        <h2 className="text-xl font-bold mb-4">최근 거래</h2>
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>시간</th>
                <th>심볼</th>
                <th>액션</th>
                <th>진입가</th>
                <th>청산가</th>
                <th>수량</th>
                <th>수익 (Gross)</th>
                <th>수수료</th>
                <th>순수익</th>
                <th>전략</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr key={trade.id} style={{ borderBottom: '1px solid #374151', color: 'white' }}>
                  <td style={{ padding: '1rem' }}>{formatKST(trade.timestamp)}</td>
                  <td style={{ padding: '1rem' }}>{trade.symbol}</td>
                  <td style={{ padding: '1rem' }}>
                    <span style={{
                      color: trade.action === 'LONG' || trade.side === 'BUY' ? '#10b981' : '#ef4444',
                      fontWeight: 'bold',
                      padding: '0.2rem 0.5rem',
                      borderRadius: '4px',
                      background: trade.action === 'LONG' || trade.side === 'BUY' ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)'
                    }}>
                      {trade.action}
                    </span>
                  </td>
                  <td style={{ padding: '1rem' }}>
                    {/* Entry Price Logic */}
                    {trade.pnl && trade.pnl !== 0 ? (
                      // Closing Trade: Calculate derived Entry
                      trade.side === 'SELL'
                        ? `$${(trade.price - (trade.pnl / trade.quantity)).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`
                        : `$${(trade.price + (trade.pnl / trade.quantity)).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`
                    ) : (
                      // Opening Trade: This is the entry
                      `$${trade.price.toLocaleString()}`
                    )}
                  </td>
                  <td style={{ padding: '1rem' }}>
                    {/* Exit Price Logic */}
                    {trade.pnl && trade.pnl !== 0 ? (
                      // Closing Trade: This is the exit
                      `$${trade.price.toLocaleString()}`
                    ) : (
                      // Opening Trade: No exit yet
                      '-'
                    )}
                  </td>
                  <td style={{ padding: '1rem' }}>{trade.quantity}</td>
                  <td style={{
                    padding: '1rem',
                    color: !trade.pnl ? 'gray' : (trade.pnl > 0 ? '#10b981' : '#ef4444')
                  }}>
                    {trade.pnl ? `$${trade.pnl.toFixed(2)}` : '-'}
                  </td>
                  <td style={{ padding: '1rem', color: '#f87171' }}>
                    {trade.commission > 0 ? `-${trade.commission.toFixed(3)}` : '-'}
                  </td>
                  <td style={{
                    padding: '1rem',
                    fontWeight: 'bold',
                    color: !trade.pnl ? 'gray' : ((trade.pnl - (trade.commission || 0)) > 0 ? '#3b82f6' : '#ef4444')
                  }}>
                    {trade.pnl ? `$${(trade.pnl - (trade.commission || 0)).toFixed(2)}` : '-'}
                  </td>
                  <td style={{ padding: '1rem', fontSize: '0.9rem', color: '#9ca3af' }}>{trade.strategy}</td>
                </tr>
              ))}
              {trades.length === 0 && (
                <tr>
                  <td colSpan="10" style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>
                    아직 기록된 거래가 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div >
  );
}

export default History;
