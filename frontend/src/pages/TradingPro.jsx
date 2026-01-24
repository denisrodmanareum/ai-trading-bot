import React, { useState, useEffect } from 'react';
import AdvancedChart from '../components/AdvancedChart';
import OrderBook from '../components/OrderBook';

/**
 * Perfect Trading Layout
 * 3-Column: Order Panel | Chart | Order Book
 */
function TradingPro() {
  const [symbol, setSymbol] = useState(
    localStorage.getItem('selected_trading_symbol') || 'BTCUSDT'
  );
  const [interval, setInterval] = useState(
    localStorage.getItem('trading_interval') || '15m'
  );
  const [currentPrice, setCurrentPrice] = useState(0);
  const [positions, setPositions] = useState([]);
  const [balance, setBalance] = useState({ available: 0, total: 0 });
  const [prices, setPrices] = useState({}); // 모든 심볼의 가격 저장

  // Order Form State
  const [orderSide, setOrderSide] = useState('BUY'); // BUY or SELL
  const [orderType, setOrderType] = useState('LIMIT'); // LIMIT or MARKET
  const [leverage, setLeverage] = useState(10);
  const [price, setPrice] = useState('');
  const [quantity, setQuantity] = useState('');
  const [totalUSD, setTotalUSD] = useState(0);

  // Symbol search
  const [availableSymbols, setAvailableSymbols] = useState([]);
  const [showSymbolSearch, setShowSymbolSearch] = useState(false);
  const [symbolSearch, setSymbolSearch] = useState('');

  // Fetch data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [posRes, balRes, dashRes] = await Promise.all([
          fetch('/api/trading/positions'),
          fetch('/api/trading/balance'),
          fetch('/api/dashboard/overview')
        ]);

        if (posRes.ok) setPositions(await posRes.json());
        if (balRes.ok) setBalance(await balRes.json());
        if (dashRes.ok) {
          const dashData = await dashRes.json();
          setPrices(dashData.prices || {});
        }
      } catch (e) {
        console.error('Failed to fetch data:', e);
      }
    };

    fetchData();
    const timer = setInterval(fetchData, 3000);
    return () => clearInterval(timer);
  }, [symbol]);

  // Fetch symbols from hybrid mode coin selection
  useEffect(() => {
    const fetchSymbols = async () => {
      try {
        const res = await fetch('/api/coins/selection');
        if (res.ok) {
          const data = await res.json();
          const symbols = data.selected_coins || [];
          // USDT 페어로 변환 (예: BTC -> BTCUSDT)
          const symbolsWithUSDT = symbols.map(coin => coin.includes('USDT') ? coin : `${coin}USDT`);
          setAvailableSymbols(symbolsWithUSDT);
        }
      } catch (e) {
        console.error(e);
        // 실패시 기본 코어 코인들 표시
        setAvailableSymbols(['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']);
      }
    };
    fetchSymbols();
  }, []);

  // Get current price from WebSocket
  useEffect(() => {
    const ws = new WebSocket(
      `wss://fstream.binance.com/ws/${symbol.toLowerCase()}@markPrice@1s`
    );

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const newPrice = parseFloat(data.p);
      setCurrentPrice(newPrice);
      if (orderType === 'MARKET') {
        setPrice(newPrice.toFixed(2));
      }
    };

    return () => ws.close();
  }, [symbol, orderType]);

  // Calculate total
  useEffect(() => {
    if (quantity && price) {
      setTotalUSD(parseFloat(quantity) * parseFloat(price));
    }
  }, [quantity, price]);

  const handlePercentage = (pct) => {
    const availableBalance = balance.available || 1000;
    const positionValue = (availableBalance * leverage * (pct / 100)) / (price || currentPrice);
    setQuantity(positionValue.toFixed(4));
  };

  const handleSubmitOrder = async () => {
    if (!quantity || !price) {
      alert('Please enter quantity and price');
      return;
    }

    try {
      const res = await fetch('/api/trading/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          side: orderSide,
          order_type: orderType,
          quantity: parseFloat(quantity),
          price: orderType === 'LIMIT' ? parseFloat(price) : null,
          leverage
        })
      });

      if (res.ok) {
        alert(`✅ Order submitted: ${orderSide} ${quantity} ${symbol}`);
        setQuantity('');
        setTotalUSD(0);
      } else {
        const error = await res.json();
        alert(`❌ Order failed: ${error.detail}`);
      }
    } catch (e) {
      console.error(e);
      alert('❌ Order failed');
    }
  };

  const handleClosePosition = async (posSymbol) => {
    if (!window.confirm(`Close ${posSymbol}?`)) return;

    try {
      const res = await fetch(`/api/trading/positions/${posSymbol}/close`, {
        method: 'POST'
      });

      if (res.ok) {
        alert('✅ Position closed');
        const posRes = await fetch('/api/trading/positions');
        if (posRes.ok) setPositions(await posRes.json());
      } else {
        alert('❌ Failed to close position');
      }
    } catch (e) {
      console.error(e);
      alert('❌ Error');
    }
  };

  const filteredSymbols = availableSymbols.filter(s =>
    s.toLowerCase().includes(symbolSearch.toLowerCase())
  );

  return (
    <div style={{
      width: '100%',
      height: '100vh',
      background: '#000',
      color: '#fff',
      fontFamily: 'Inter, sans-serif',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden'
    }}>
      {/* Top Header */}
      <div style={{
        height: '50px',
        borderBottom: '1px solid #1a1a1a',
        display: 'flex',
        alignItems: 'center',
        padding: '0 20px',
        gap: '20px',
        background: '#0a0a0a'
      }}>
        {/* Symbol */}
        <div style={{ position: 'relative' }}>
          <div
            onClick={() => setShowSymbolSearch(!showSymbolSearch)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              cursor: 'pointer',
              padding: '6px 12px',
              background: '#111',
              borderRadius: '4px',
              border: '1px solid #222'
            }}
          >
            <span style={{ fontSize: '1rem', fontWeight: '900' }}>{symbol}</span>
            <span style={{ fontSize: '0.6rem', color: '#f0b90b', fontWeight: '700' }}>PERP</span>
            <span style={{ fontSize: '0.7rem', color: '#666' }}>▼</span>
          </div>

          {showSymbolSearch && (
            <div style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              marginTop: '4px',
              background: '#1a1a1a',
              border: '1px solid #333',
              borderRadius: '6px',
              width: '220px',
              maxHeight: '400px',
              overflowY: 'auto',
              zIndex: 1000,
              boxShadow: '0 8px 24px rgba(0,0,0,0.5)'
            }}>
              <input
                type="text"
                placeholder="Search symbol..."
                value={symbolSearch}
                onChange={(e) => setSymbolSearch(e.target.value)}
                style={{
                  width: 'calc(100% - 16px)',
                  padding: '10px 8px',
                  margin: '8px',
                  background: '#0a0a0a',
                  border: '1px solid #333',
                  borderRadius: '4px',
                  color: '#fff',
                  outline: 'none',
                  fontSize: '0.85rem'
                }}
              />
              {filteredSymbols.map(s => (
                <div
                  key={s}
                  onClick={() => {
                    setSymbol(s);
                    localStorage.setItem('selected_trading_symbol', s);
                    setShowSymbolSearch(false);
                    setSymbolSearch('');
                  }}
                  style={{
                    padding: '10px 16px',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    color: symbol === s ? '#00b07c' : '#ccc',
                    background: symbol === s ? '#0a1a0a' : 'transparent',
                    transition: 'background 0.15s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = '#222'}
                  onMouseLeave={(e) => {
                    if (symbol !== s) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  {s}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Current Price */}
        <div style={{
          fontSize: '1.3rem',
          fontWeight: '900',
          color: '#00b07c',
          fontFamily: 'monospace'
        }}>
          ${currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>

        {/* Balance */}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '20px', fontSize: '0.8rem' }}>
          <div>
            <span style={{ color: '#666' }}>Balance: </span>
            <span style={{ color: '#fff', fontWeight: '700' }}>
              ${(balance.total || 0).toLocaleString()}
            </span>
          </div>
          <div>
            <span style={{ color: '#666' }}>Available: </span>
            <span style={{ color: '#00b07c', fontWeight: '700' }}>
              ${(balance.available || 0).toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      {/* Main Trading Area - 3 Columns */}
      <div style={{
        flex: 1,
        display: 'grid',
        gridTemplateColumns: '320px 1fr 320px',
        gridTemplateRows: '1fr auto',
        gap: '1px',
        background: '#0a0a0a',
        overflow: 'hidden'
      }}>
        {/* Left Column: Order Panel */}
        <div style={{
          background: '#000',
          padding: '20px',
          overflowY: 'auto',
          gridRow: '1 / 3'
        }}>
          {/* Order Type Tabs */}
          <div style={{
            display: 'flex',
            gap: '8px',
            marginBottom: '20px'
          }}>
            {['LIMIT', 'MARKET'].map(type => (
              <button
                key={type}
                onClick={() => setOrderType(type)}
                style={{
                  flex: 1,
                  padding: '8px',
                  background: orderType === type ? '#222' : 'transparent',
                  border: `1px solid ${orderType === type ? '#00b07c' : '#333'}`,
                  borderRadius: '4px',
                  color: orderType === type ? '#00b07c' : '#666',
                  fontSize: '0.8rem',
                  fontWeight: '700',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                {type}
              </button>
            ))}
          </div>

          {/* Leverage Slider */}
          <div style={{ marginBottom: '20px' }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginBottom: '8px',
              fontSize: '0.75rem'
            }}>
              <span style={{ color: '#888' }}>Leverage</span>
              <span style={{ color: '#00b07c', fontWeight: '700' }}>{leverage}x</span>
            </div>
            <input
              type="range"
              min="1"
              max="125"
              value={leverage}
              onChange={(e) => setLeverage(parseInt(e.target.value))}
              style={{
                width: '100%',
                accentColor: '#00b07c'
              }}
            />
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '0.65rem',
              color: '#555',
              marginTop: '4px'
            }}>
              <span>1x</span>
              <span>25x</span>
              <span>50x</span>
              <span>125x</span>
            </div>
          </div>

          {/* Price (LIMIT only) */}
          {orderType === 'LIMIT' && (
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '0.75rem', color: '#888', display: 'block', marginBottom: '6px' }}>
                Price (USDT)
              </label>
              <input
                type="number"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                placeholder={currentPrice.toFixed(2)}
                style={{
                  width: '100%',
                  padding: '12px',
                  background: '#111',
                  border: '1px solid #222',
                  borderRadius: '4px',
                  color: '#fff',
                  fontSize: '0.9rem',
                  outline: 'none'
                }}
              />
            </div>
          )}

          {/* Amount */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{ fontSize: '0.75rem', color: '#888', display: 'block', marginBottom: '6px' }}>
              Amount (BTC)
            </label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="0.0000"
              style={{
                width: '100%',
                padding: '12px',
                background: '#111',
                border: '1px solid #222',
                borderRadius: '4px',
                color: '#fff',
                fontSize: '0.9rem',
                outline: 'none'
              }}
            />
          </div>

          {/* Percentage Buttons */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '8px',
            marginBottom: '16px'
          }}>
            {[25, 50, 75, 100].map(pct => (
              <button
                key={pct}
                onClick={() => handlePercentage(pct)}
                style={{
                  padding: '8px',
                  background: '#111',
                  border: '1px solid #222',
                  borderRadius: '4px',
                  color: '#888',
                  fontSize: '0.75rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#00b07c';
                  e.currentTarget.style.color = '#00b07c';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#222';
                  e.currentTarget.style.color = '#888';
                }}
              >
                {pct}%
              </button>
            ))}
          </div>

          {/* Total */}
          <div style={{
            padding: '12px',
            background: '#111',
            borderRadius: '4px',
            marginBottom: '16px',
            fontSize: '0.8rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ color: '#888' }}>Total:</span>
              <span style={{ color: '#fff', fontWeight: '700' }}>
                ${totalUSD.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#888' }}>Margin:</span>
              <span style={{ color: '#fff', fontWeight: '700' }}>
                ${(totalUSD / leverage).toFixed(2)}
              </span>
            </div>
          </div>

          {/* Buy/Sell Buttons */}
          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={() => {
                setOrderSide('BUY');
                handleSubmitOrder();
              }}
              style={{
                flex: 1,
                padding: '16px',
                background: 'linear-gradient(135deg, #00b07c, #00d98e)',
                border: 'none',
                borderRadius: '6px',
                color: '#fff',
                fontSize: '0.9rem',
                fontWeight: '900',
                cursor: 'pointer',
                boxShadow: '0 4px 16px rgba(0, 176, 124, 0.4)',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 6px 20px rgba(0, 176, 124, 0.6)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 4px 16px rgba(0, 176, 124, 0.4)';
              }}
            >
              BUY
            </button>
            <button
              onClick={() => {
                setOrderSide('SELL');
                handleSubmitOrder();
              }}
              style={{
                flex: 1,
                padding: '16px',
                background: 'linear-gradient(135deg, #ff4b4b, #ff6b6b)',
                border: 'none',
                borderRadius: '6px',
                color: '#fff',
                fontSize: '0.9rem',
                fontWeight: '900',
                cursor: 'pointer',
                boxShadow: '0 4px 16px rgba(255, 75, 75, 0.4)',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 6px 20px rgba(255, 75, 75, 0.6)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 4px 16px rgba(255, 75, 75, 0.4)';
              }}
            >
              SELL
            </button>
          </div>
        </div>

        {/* Center Column: Chart */}
        <div style={{
          background: '#000',
          overflow: 'hidden',
          position: 'relative'
        }}>
          <AdvancedChart symbol={symbol} interval={interval || '15m'} />
        </div>

        {/* Right Column: Order Book */}
        <div style={{
          background: '#000',
          overflow: 'hidden',
          gridRow: '1 / 3'
        }}>
          <OrderBook symbol={symbol} />
        </div>

        {/* Bottom: Positions (spans center column only) */}
        <div style={{
          background: '#000',
          overflowY: 'auto',
          borderTop: '1px solid #1a1a1a',
          maxHeight: '200px'
        }}>
          <div style={{
            padding: '12px 20px',
            borderBottom: '1px solid #1a1a1a',
            fontSize: '0.8rem',
            fontWeight: '700',
            color: '#fff'
          }}>
            Open Positions
          </div>
          {positions.length > 0 ? (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
              <thead>
                <tr style={{ color: '#666', borderBottom: '1px solid #1a1a1a' }}>
                  <th style={{ padding: '10px 20px', textAlign: 'left', fontWeight: '600' }}>Symbol</th>
                  <th style={{ padding: '10px', textAlign: 'right', fontWeight: '600' }}>Size</th>
                  <th style={{ padding: '10px', textAlign: 'right', fontWeight: '600' }}>Entry</th>
                  <th style={{ padding: '10px', textAlign: 'right', fontWeight: '600' }}>Mark</th>
                  <th style={{ padding: '10px', textAlign: 'right', fontWeight: '600' }}>Leverage</th>
                  <th style={{ padding: '10px', textAlign: 'right', fontWeight: '600' }}>PnL</th>
                  <th style={{ padding: '10px 20px', textAlign: 'right', fontWeight: '600' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos, idx) => {
                  const isLong = pos.position_amt > 0;
                  const pnlColor = pos.unrealized_pnl >= 0 ? '#00b07c' : '#ff4b4b';
                  const sizeUSDT = Math.abs(pos.position_amt) * (pos.entry_price || 0);
                  return (
                    <tr
                      key={idx}
                      style={{ borderBottom: '1px solid #111' }}
                      onMouseEnter={(e) => e.currentTarget.style.background = '#0a0a0a'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <td style={{ padding: '12px 20px' }}>
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
                        <div>{Math.abs(pos.position_amt).toFixed(4)}</div>
                        <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '2px' }}>${sizeUSDT.toLocaleString(undefined, { maximumFractionDigits: 2 })}</div>
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right', fontFamily: 'monospace', color: '#ccc' }}>
                        {pos.entry_price?.toLocaleString()}
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right', fontFamily: 'monospace', color: '#ccc' }}>
                        {pos.mark_price > 0 ? pos.mark_price.toLocaleString() : '-'}
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right', fontFamily: 'monospace', color: '#f0b90b', fontWeight: '700' }}>
                        {pos.leverage || leverage || 10}x
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
                      <td style={{ padding: '12px 20px', textAlign: 'right' }}>
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
            <div style={{ padding: '40px', textAlign: 'center', color: '#444', fontSize: '0.85rem' }}>
              No open positions
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TradingPro;
