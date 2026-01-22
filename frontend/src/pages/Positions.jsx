import React, { useState, useEffect } from 'react';

function Positions() {
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchPositions = async () => {
    try {
      const res = await fetch('/api/positions/');
      const data = await res.json();
      setPositions(data.positions || []);
    } catch (err) {
      console.error('Failed to fetch positions:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading"><div className="spinner"></div></div>;

  return (
    <div className="positions p-4" style={{ background: '#000', minHeight: '100vh', color: '#fff' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: '900', letterSpacing: '-0.04em', textTransform: 'uppercase', marginBottom: '2rem' }}>Operational Status</h1>

      <div className="card" style={{ border: '1px solid #111', background: '#050505' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <h2 style={{ margin: 0, fontSize: '0.75rem', fontWeight: '900', textTransform: 'uppercase', color: '#444', letterSpacing: '0.1em' }}>Live Deployments ({positions.length})</h2>
          <div className="status-indicator connected" style={{ fontSize: '0.6rem' }}>SENTINEL ACTIVE</div>
        </div>

        {positions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '6rem 2rem', border: '1px dashed #111', borderRadius: '1px' }}>
            <p style={{ fontSize: '0.75rem', fontWeight: '900', color: '#222', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Zero Active Signals</p>
            <p style={{ fontSize: '0.65rem', color: '#333', marginTop: '0.5rem', fontWeight: '700' }}>AI ENGINE ANALYSING CLUSTER FLOW...</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th>Size</th>
                  <th>Entry Price</th>
                  <th>PnL (Unr.)</th>
                  <th>Leverage</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: '900', fontSize: '0.85rem' }}>{pos.symbol}</td>
                    <td>
                      <span style={{
                        color: pos.position_amt > 0 ? 'var(--success)' : 'var(--danger)',
                        border: `1px solid ${pos.position_amt > 0 ? 'rgba(0, 176, 124, 0.2)' : 'rgba(255, 91, 91, 0.2)'}`,
                        background: '#000',
                        padding: '0.2rem 0.5rem',
                        borderRadius: '1px',
                        fontSize: '0.65rem',
                        fontWeight: '900',
                        textTransform: 'uppercase'
                      }}>
                        {pos.position_amt > 0 ? 'LONG' : 'SHORT'}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: '700' }}>{Math.abs(pos.position_amt).toFixed(4)}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: '#888' }}>${pos.entry_price?.toFixed(2) || '0.00'}</td>
                    <td style={{
                      color: (pos.unrealized_pnl || 0) >= 0 ? 'var(--success)' : 'var(--danger)',
                      fontWeight: '900',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.9rem'
                    }}>
                      ${pos.unrealized_pnl?.toFixed(2) || '0.00'}
                    </td>
                    <td style={{ fontWeight: '800', color: '#444', fontSize: '0.7rem' }}>{pos.leverage || 5}X</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default Positions;
