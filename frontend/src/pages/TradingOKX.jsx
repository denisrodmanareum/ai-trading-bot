import React, { useState, useEffect } from 'react';
import AdvancedChart from '../components/AdvancedChart';
import OrderBook from '../components/OrderBook';
import QuickOrderPanel from '../components/QuickOrderPanel';

/**
 * OKX-Style Trading Page
 * 프로페셔널한 거래 인터페이스
 */
function TradingOKX() {
  const [symbol, setSymbol] = useState(
    localStorage.getItem('selected_trading_symbol') || 'BTCUSDT'
  );
  const [interval, setInterval] = useState(
    localStorage.getItem('trading_interval') || '15m'
  );
  const [currentPrice, setCurrentPrice] = useState(0);
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [activeBottomTab, setActiveBottomTab] = useState('positions'); // positions, orders, history

  // Fetch positions and orders
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [posRes, ordRes] = await Promise.all([
          fetch('/api/trading/positions'),
          fetch(`/api/trading/orders?symbol=${symbol}`)
        ]);

        if (posRes.ok) {
          const posData = await posRes.json();
          setPositions(posData);
        }
        if (ordRes.ok) {
          const ordData = await ordRes.json();
          setOrders(ordData);
        }
      } catch (e) {
        console.error('Failed to fetch trading data:', e);
      }
    };

    fetchData();
    const timer = setInterval(fetchData, 3000);
    return () => clearInterval(timer);
  }, [symbol]);

  // Get current price from WebSocket or API
  useEffect(() => {
    const ws = new WebSocket(
      `wss://fstream.binance.com/ws/${symbol.toLowerCase()}@markPrice@1s`
    );

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setCurrentPrice(parseFloat(data.p));
    };

    return () => ws.close();
  }, [symbol]);

  const handleClosePosition = async (posSymbol) => {
    if (!window.confirm(`Close ${posSymbol} position?`)) return;

    try {
      const res = await fetch(`/api/trading/positions/${posSymbol}/close`, {
        method: 'POST'
      });

      if (res.ok) {
        alert('✅ Position closed');
        // Refresh positions
        const posRes = await fetch('/api/trading/positions');
        if (posRes.ok) setPositions(await posRes.json());
      } else {
        alert('❌ Failed to close position');
      }
    } catch (e) {
      console.error(e);
      alert('❌ Error closing position');
    }
  };

  return (
    <div style={{
      width: '100%',
      height: '100vh',
      background: '#000',
      color: '#fff',
      fontFamily: 'Inter, sans-serif',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Top Header */}
      <div style={{
        height: '60px',
        borderBottom: '1px solid #1a1a1a',
        display: 'flex',
        alignItems: 'center',
        padding: '0 24px',
        gap: '24px'
      }}>
        {/* Symbol Selector */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <span style={{ fontSize: '1.2rem', fontWeight: '900', color: '#fff' }}>
            {symbol}
          </span>
          <span style={{
            fontSize: '0.65rem',
            padding: '2px 6px',
            background: '#111',
            border: '1px solid #222',
            borderRadius: '2px',
            color: '#f0b90b',
            fontWeight: '700'
          }}>
            PERP
          </span>
        </div>

        {/* Current Price */}
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span style={{ fontSize: '1.4rem', fontWeight: '900', color: '#00b07c' }}>
            {currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
          <span style={{ fontSize: '0.75rem', color: '#666' }}>USDT</span>
        </div>

        {/* 24h Stats */}
        <div style={{ display: 'flex', gap: '24px', marginLeft: 'auto' }}>
          <div>
            <div style={{ fontSize: '0.65rem', color: '#666', marginBottom: '2px' }}>24h Change</div>
            <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#00b07c' }}>
              +2.45%
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.65rem', color: '#666', marginBottom: '2px' }}>24h High</div>
            <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#fff' }}>
              106,800
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.65rem', color: '#666', marginBottom: '2px' }}>24h Low</div>
            <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#fff' }}>
              103,200
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.65rem', color: '#666', marginBottom: '2px' }}>24h Volume</div>
            <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#fff' }}>
              2.45B
            </div>
          </div>
        </div>
      </div>

      {/* Main Trading Area */}
      <div style={{
        flex: 1,
        display: 'grid',
        gridTemplateColumns: '1fr 380px',
        gridTemplateRows: '1fr 320px',
        gap: '1px',
        background: '#0a0a0a',
        overflow: 'hidden'
      }}>
        {/* Chart Area (Top Left) */}
        <div style={{
          background: '#000',
          overflow: 'hidden',
          position: 'relative'
        }}>
          <AdvancedChart 
            symbol={symbol}
            interval={interval || '15m'}
          />
        </div>

        {/* Order Book + Quick Order (Top Right) */}
        <div style={{
          background: '#000',
          display: 'flex',
          flexDirection: 'column',
          gap: '1px'
        }}>
          {/* Order Book */}
          <div style={{ flex: 1, minHeight: 0 }}>
            <OrderBook symbol={symbol} />
          </div>
        </div>

        {/* Quick Order Panel (Bottom Left) */}
        <div style={{
          background: '#000',
          overflowY: 'auto',
          padding: '16px'
        }}>
          <QuickOrderPanel 
            symbol={symbol}
            currentPrice={currentPrice}
          />
        </div>

        {/* Positions & Orders (Bottom Right) */}
        <div style={{
          background: '#000',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          {/* Tabs */}
          <div style={{
            display: 'flex',
            gap: '24px',
            padding: '12px 16px',
            borderBottom: '1px solid #1a1a1a',
            background: '#0a0a0a'
          }}>
            {['positions', 'orders', 'history'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveBottomTab(tab)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: activeBottomTab === tab ? '#fff' : '#666',
                  fontSize: '0.8rem',
                  fontWeight: '700',
                  textTransform: 'capitalize',
                  cursor: 'pointer',
                  padding: '4px 0',
                  position: 'relative',
                  transition: 'color 0.2s'
                }}
              >
                {tab}
                {activeBottomTab === tab && (
                  <div style={{
                    position: 'absolute',
                    bottom: '-12px',
                    left: 0,
                    right: 0,
                    height: '2px',
                    background: '#00b07c'
                  }} />
                )}
              </button>
            ))}
          </div>

          {/* Content */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            fontSize: '0.75rem'
          }}>
            {activeBottomTab === 'positions' && (
              <div>
                {positions.length > 0 ? (
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{
                        color: '#666',
                        borderBottom: '1px solid #1a1a1a',
                        background: '#0a0a0a'
                      }}>
                        <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: '600' }}>Symbol</th>
                        <th style={{ padding: '10px', textAlign: 'right', fontWeight: '600' }}>Size</th>
                        <th style={{ padding: '10px', textAlign: 'right', fontWeight: '600' }}>Entry</th>
                        <th style={{ padding: '10px', textAlign: 'right', fontWeight: '600' }}>PnL</th>
                        <th style={{ padding: '10px 16px', textAlign: 'right', fontWeight: '600' }}>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {positions.map((pos, idx) => {
                        const isLong = pos.position_amt > 0;
                        const pnlColor = pos.unrealized_pnl >= 0 ? '#00b07c' : '#ff4b4b';
                        
                        return (
                          <tr
                            key={idx}
                            style={{
                              borderBottom: '1px solid #111',
                              transition: 'background 0.2s'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.background = '#0a0a0a'}
                            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                          >
                            <td style={{ padding: '12px 16px' }}>
                              <div style={{ fontWeight: '700' }}>{pos.symbol}</div>
                              <div style={{
                                fontSize: '0.65rem',
                                color: isLong ? '#00b07c' : '#ff4b4b',
                                fontWeight: '600'
                              }}>
                                {isLong ? 'LONG' : 'SHORT'}
                              </div>
                            </td>
                            <td style={{ padding: '12px', textAlign: 'right', fontFamily: 'monospace' }}>
                              {Math.abs(pos.position_amt).toFixed(4)}
                            </td>
                            <td style={{ padding: '12px', textAlign: 'right', fontFamily: 'monospace', color: '#ccc' }}>
                              {pos.entry_price?.toLocaleString()}
                            </td>
                            <td style={{
                              padding: '12px',
                              textAlign: 'right',
                              fontFamily: 'monospace',
                              color: pnlColor,
                              fontWeight: '700'
                            }}>
                              {pos.unrealized_pnl >= 0 ? '+' : ''}{pos.unrealized_pnl?.toFixed(2)}
                            </td>
                            <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                              <button
                                onClick={() => handleClosePosition(pos.symbol)}
                                style={{
                                  background: 'transparent',
                                  border: '1px solid #333',
                                  color: '#888',
                                  padding: '4px 12px',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  fontSize: '0.7rem',
                                  fontWeight: '600',
                                  transition: 'all 0.2s'
                                }}
                                onMouseEnter={(e) => {
                                  e.currentTarget.style.borderColor = '#ff4b4b';
                                  e.currentTarget.style.color = '#ff4b4b';
                                }}
                                onMouseLeave={(e) => {
                                  e.currentTarget.style.borderColor = '#333';
                                  e.currentTarget.style.color = '#888';
                                }}
                              >
                                Close
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <div style={{
                    padding: '48px',
                    textAlign: 'center',
                    color: '#444',
                    fontSize: '0.85rem'
                  }}>
                    No open positions
                  </div>
                )}
              </div>
            )}

            {activeBottomTab === 'orders' && (
              <div>
                {orders.length > 0 ? (
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{
                        color: '#666',
                        borderBottom: '1px solid #1a1a1a',
                        background: '#0a0a0a'
                      }}>
                        <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: '600' }}>Symbol</th>
                        <th style={{ padding: '10px', textAlign: 'right', fontWeight: '600' }}>Type</th>
                        <th style={{ padding: '10px', textAlign: 'right', fontWeight: '600' }}>Side</th>
                        <th style={{ padding: '10px', textAlign: 'right', fontWeight: '600' }}>Price</th>
                        <th style={{ padding: '10px', textAlign: 'right', fontWeight: '600' }}>Qty</th>
                        <th style={{ padding: '10px 16px', textAlign: 'right', fontWeight: '600' }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {orders.map((order, idx) => (
                        <tr
                          key={idx}
                          style={{ borderBottom: '1px solid #111' }}
                        >
                          <td style={{ padding: '12px 16px', fontWeight: '700' }}>{order.symbol}</td>
                          <td style={{ padding: '12px', textAlign: 'right', color: '#ccc' }}>{order.type}</td>
                          <td style={{
                            padding: '12px',
                            textAlign: 'right',
                            color: order.side === 'BUY' ? '#00b07c' : '#ff4b4b',
                            fontWeight: '600'
                          }}>
                            {order.side}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'right', fontFamily: 'monospace', color: '#ccc' }}>
                            {order.price?.toLocaleString()}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'right', fontFamily: 'monospace' }}>
                            {order.orig_qty}
                          </td>
                          <td style={{ padding: '12px 16px', textAlign: 'right', color: '#f0b90b', fontSize: '0.7rem' }}>
                            {order.status}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div style={{
                    padding: '48px',
                    textAlign: 'center',
                    color: '#444',
                    fontSize: '0.85rem'
                  }}>
                    No open orders
                  </div>
                )}
              </div>
            )}

            {activeBottomTab === 'history' && (
              <div style={{
                padding: '48px',
                textAlign: 'center',
                color: '#444',
                fontSize: '0.85rem'
              }}>
                Trade history coming soon...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default TradingOKX;
