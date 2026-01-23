import React, { useState, useEffect } from 'react';
import AdvancedChart from '../components/AdvancedChart';
import OrderBook from '../components/OrderBook';

/**
 * Premium 3-Column Trading Layout
 * Left: OrderBook & Recent Trades
 * Center: Chart & Positions/Orders
 * Right: AI Intelligence & Trade Entry
 */
function TradingPerfect() {
  const [symbol, setSymbol] = useState(
    localStorage.getItem('selected_trading_symbol') || 'BTCUSDT'
  );
  const [interval, setInterval] = useState(
    localStorage.getItem('trading_interval') || '15m'
  );
  const [currentPrice, setCurrentPrice] = useState(0);
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [balance, setBalance] = useState({ available: 0, total: 0, unrealized_pnl: 0 });
  const [ticker, setTicker] = useState(null);
  const [fundingCountdown, setFundingCountdown] = useState('');

  // AI Control State
  const [aiRunning, setAiRunning] = useState(false);
  const [aiMode, setAiMode] = useState('SCALP');
  const [aiLeverageMode, setAiLeverageMode] = useState('AUTO');

  // Order Form State
  const [orderType, setOrderType] = useState('Limit');
  const [orderSide, setOrderSide] = useState('BUY');
  const [leverage, setLeverage] = useState(10);
  const [price, setPrice] = useState('');
  const [quantity, setQuantity] = useState('');
  const [totalUSD, setTotalUSD] = useState(0);
  const [amountUnit, setAmountUnit] = useState('COIN'); // 'COIN' (BTC) or 'USDT'

  // Bottom tabs
  const [activeBottomTab, setActiveBottomTab] = useState('positions');

  // Symbol selection logic
  const [availableSymbols, setAvailableSymbols] = useState([]);
  const [showSymbolSearch, setShowSymbolSearch] = useState(false);
  const [symbolSearch, setSymbolSearch] = useState('');

  // Fetch initial data & status
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [posRes, ordRes, balRes, aiRes, configRes, symRes] = await Promise.all([
          fetch('/api/trading/positions'),
          fetch(`/api/trading/orders?symbol=${symbol}`),
          fetch('/api/trading/balance'),
          fetch('/api/ai/status'),
          fetch('/api/trading/strategy/config'),
          fetch('/api/trading/symbols')
        ]);

        if (posRes.ok) setPositions(await posRes.json());
        if (ordRes.ok) setOrders(await ordRes.json());
        if (balRes.ok) setBalance(await balRes.json());
        if (aiRes.ok) {
          const data = await aiRes.json();
          setAiRunning(data.running || false);
        }
        if (configRes.ok) {
          const config = await configRes.json();
          if (config.status !== 'not_initialized') {
            setAiMode(config.mode || 'SCALP');
          }
        }
        if (symRes.ok) {
          const data = await symRes.json();
          setAvailableSymbols(data.symbols || []);
        }

        // Fetch Ticker Info
        const tickerRes = await fetch(`/api/trading/ticker/${symbol}`);
        if (tickerRes.ok) setTicker(await tickerRes.json());
      } catch (e) {
        console.error('Failed to fetch data:', e);
      }
    };

    fetchData();
    const intervalId = setInterval(fetchData, 5000);
    return () => clearInterval(intervalId);
  }, [symbol]);

  // Funding Countdown
  useEffect(() => {
    if (!ticker?.next_funding_time) return;

    const updateCountdown = () => {
      const now = Date.now();
      const diff = ticker.next_funding_time - now;
      if (diff <= 0) {
        setFundingCountdown('0h 0m 0s');
        return;
      }
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setFundingCountdown(`${h}h ${m}m ${s}s`);
    };

    const cId = setInterval(updateCountdown, 1000);
    updateCountdown();
    return () => clearInterval(cId);
  }, [ticker]);

  // Price WebSocket
  useEffect(() => {
    const ws = new WebSocket(`wss://fstream.binance.com/ws/${symbol.toLowerCase()}@markPrice@1s`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setCurrentPrice(parseFloat(data.p));
    };
    return () => ws.close();
  }, [symbol]);

  // Total calculation
  useEffect(() => {
    const qValue = parseFloat(quantity) || 0;
    const pValue = parseFloat(price) || currentPrice || 0;

    if (amountUnit === 'USDT') {
      setTotalUSD(qValue); // If user enters 100 USDT, cost is 100
    } else {
      setTotalUSD(qValue * pValue); // If user enters 0.01 BTC, cost is 0.01 * price
    }
  }, [quantity, price, currentPrice, amountUnit]);

  const handlePercentage = (pct) => {
    const availableBalance = balance.available || 1000;
    const calcPrice = parseFloat(price) || currentPrice;
    if (calcPrice > 0) {
      const positionValue = (availableBalance * leverage * (pct / 100)) / calcPrice;
      setQuantity(positionValue.toFixed(4));
    }
  };

  const handleSubmitOrder = async (side) => {
    if (!quantity) return alert('Enter quantity');

    // Convert to quantity (COIN) if in USDT mode
    let finalQty = parseFloat(quantity);
    const finalPrice = orderType === 'Limit' ? parseFloat(price) : currentPrice;

    if (amountUnit === 'USDT') {
      if (!finalPrice) return alert('Price required for USDT conversion');
      finalQty = parseFloat((finalQty / finalPrice).toFixed(4));
    }

    try {
      const res = await fetch('/api/trading/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          side,
          order_type: orderType.toUpperCase(),
          quantity: finalQty,
          price: orderType === 'Limit' ? parseFloat(price) : null,
          leverage
        })
      });
      if (res.ok) {
        alert(`✅ ${side} Success`);
        setQuantity('');
      } else {
        const err = await res.json();
        alert(`❌ Error: ${err.detail || 'Failed'}`);
      }
    } catch (e) { alert('❌ Order Failed'); }
  };

  const toggleAI = async () => {
    const action = aiRunning ? 'stop' : 'start';
    try {
      const res = await fetch(`/api/ai/${action}`, { method: 'POST' });
      if (res.ok) setAiRunning(!aiRunning);
    } catch (e) { console.error(e); }
  };

  const handleClosePosition = async (closingSymbol) => {
    if (!window.confirm(`${closingSymbol} 포지션을 종료하시겠습니까?`)) return;
    try {
      const res = await fetch(`/api/trading/close-position/${closingSymbol}`, { method: 'POST' });
      if (res.ok) {
        alert(`✅ ${closingSymbol} closed`);
        const posRes = await fetch('/api/trading/positions');
        if (posRes.ok) setPositions(await posRes.json());
      } else {
        const err = await res.json();
        alert(`❌ Error: ${err.detail || 'Failed to close'}`);
      }
    } catch (e) { alert('❌ Close Failed'); }
  };

  const handleCloseAll = async () => {
    if (!window.confirm('모든 포지션을 종료하시겠습니까?')) return;
    try {
      const res = await fetch('/api/trading/close-position', { method: 'POST' });
      if (res.ok) {
        alert('✅ All positions closed');
        setPositions([]);
      } else {
        const err = await res.json();
        alert(`❌ Error: ${err.detail || 'Failed to close all'}`);
      }
    } catch (e) { alert('❌ Close All Failed'); }
  };

  const handleCancelOrder = async (orderId, orderSymbol = symbol) => {
    try {
      // Backend expects: /api/trading/order/{symbol}/{order_id}
      const res = await fetch(`/api/trading/order/${orderSymbol}/${orderId}`, { method: 'DELETE' });
      if (res.ok) {
        alert('✅ Order Cancelled');
        const ordRes = await fetch(`/api/trading/orders?symbol=${symbol}`);
        if (ordRes.ok) setOrders(await ordRes.json());
      } else {
        const err = await res.json();
        alert(`❌ Failed: ${err.detail || 'Error'}`);
      }
    } catch (e) { alert('❌ Cancel Failed'); }
  };

  const filteredSymbols = availableSymbols.filter(s => s.toLowerCase().includes(symbolSearch.toLowerCase()));

  // Inline CSS for professional feel
  const scrollbarStyles = `
    .no-scrollbar::-webkit-scrollbar { display: none; }
    .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
    /* Improved Custom Scrollbar */
    .custom-scroll::-webkit-scrollbar { width: 5px; height: 5px; }
    .custom-scroll::-webkit-scrollbar-track { background: #050505; }
    .custom-scroll::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
    .custom-scroll::-webkit-scrollbar-thumb:hover { background: #555; }
    
    /* Disable native number input arrows */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
      -webkit-appearance: none; 
      margin: 0; 
    }
    input[type=number] {
      -moz-appearance: textfield;
    }
  `;

  return (
    <div style={{
      width: '100%',
      height: '100%',
      background: '#000',
      color: '#eee',
      fontFamily: '"Outfit", "Inter", sans-serif',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden'
    }}>
      <style>{scrollbarStyles}</style>

      {/* Header */}
      <header style={{
        height: '48px',
        borderBottom: '1px solid #1a1a1a',
        display: 'flex',
        alignItems: 'center',
        padding: '0 16px',
        gap: '24px',
        background: '#0a0a0a',
        zIndex: 10
      }}>
        <div style={{ position: 'relative' }}>
          <div
            onClick={() => setShowSymbolSearch(!showSymbolSearch)}
            style={{
              display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer',
              padding: '4px 10px', background: '#111', borderRadius: '4px', border: '1px solid #222'
            }}>
            <span style={{ fontWeight: '800', fontSize: '1rem', letterSpacing: '0.5px' }}>{symbol}</span>
            <span style={{ fontSize: '0.6rem', color: '#f0b90b', background: 'rgba(240,185,11,0.1)', padding: '1px 4px', borderRadius: '2px' }}>PERP</span>
            <span style={{ fontSize: '0.6rem', color: '#666' }}>▼</span>
          </div>
          {showSymbolSearch && (
            <div className="custom-scroll" style={{
              position: 'absolute', top: '100%', left: 0, marginTop: '5px', background: '#111',
              border: '1px solid #333', borderRadius: '6px', width: '180px', maxHeight: '300px', overflowY: 'auto', zIndex: 100
            }}>
              <input
                autoFocus placeholder="Search..." value={symbolSearch} onChange={e => setSymbolSearch(e.target.value)}
                style={{ width: '100%', padding: '8px', background: '#0a0a0a', border: 'none', borderBottom: '1px solid #222', color: '#fff', outline: 'none', fontSize: '0.8rem' }}
              />
              {filteredSymbols.map(s => (
                <div key={s} onClick={() => { setSymbol(s); setShowSymbolSearch(false); }}
                  style={{ padding: '8px 12px', cursor: 'pointer', fontSize: '0.8rem', background: symbol === s ? '#1a1a1a' : 'transparent', color: symbol === s ? '#00b07c' : '#888' }}>
                  {s}
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ color: '#00b07c', fontWeight: '800', fontFamily: 'monospace', fontSize: '1.1rem', lineHeight: 1.1 }}>
              ${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 1 })}
            </div>
            <div style={{ fontSize: '0.65rem', color: '#666' }}>
              Index: <span style={{ color: '#999' }}>${ticker?.index_price?.toLocaleString() || (currentPrice * 0.9998).toFixed(1)}</span>
            </div>
          </div>

          <div style={{ width: '1px', height: '20px', background: '#222' }} />

          {/* New Header Stats */}
          <div style={{ display: 'flex', gap: '20px' }}>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ fontSize: '0.55rem', color: '#444' }}>Mark Price</div>
              <div style={{ fontSize: '0.75rem', color: '#eee', fontWeight: '700' }}>${ticker?.mark_price?.toLocaleString() || '---'}</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ fontSize: '0.55rem', color: '#444' }}>Funding Rate / Countdown</div>
              <div style={{ fontSize: '0.75rem', color: '#f0b90b', fontWeight: '700' }}>
                {(ticker?.funding_rate * 100).toFixed(4)}% / <span style={{ color: '#aaa' }}>{fundingCountdown || '---'}</span>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ fontSize: '0.55rem', color: '#444' }}>24h Low / High</div>
              <div style={{ fontSize: '0.75rem', color: '#eee', fontWeight: '700' }}>
                <span style={{ color: '#ff4b4b' }}>${ticker?.low_24h?.toLocaleString() || '---'}</span> / <span style={{ color: '#00b07c' }}>${ticker?.high_24h?.toLocaleString() || '---'}</span>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ fontSize: '0.55rem', color: '#444' }}>24h Vol(BTC) / Turnover(USDT)</div>
              <div style={{ fontSize: '0.75rem', color: '#eee', fontWeight: '700' }}>
                {ticker ? `${(ticker.volume_24h / 1000).toFixed(2)}K / ${(ticker.turnover_24h / 1000000000).toFixed(2)}B` : '---'}
              </div>
            </div>
          </div>
        </div>

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '20px' }}>
          <button
            onClick={toggleAI}
            style={{
              padding: '6px 16px', borderRadius: '4px', border: 'none', cursor: 'pointer',
              background: aiRunning ? 'linear-gradient(135deg, #cc2e2e, #ff4b4b)' : 'linear-gradient(135deg, #00875e, #00b07c)',
              color: '#fff', fontSize: '0.75rem', fontWeight: '900', boxShadow: '0 4px 12px rgba(0,0,0,0.3)', transition: 'all 0.2s'
            }}>
            {aiRunning ? 'STOP AI ENGINE' : 'RUN AI ENGINE'}
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main style={{
        flex: 1,
        display: 'grid',
        gridTemplateColumns: '280px 1fr 320px',
        overflow: 'hidden',
        background: '#050505'
      }}>

        {/* Left Col: OrderBook & History */}
        <section style={{ display: 'flex', flexDirection: 'column', borderRight: '1px solid #111', overflow: 'hidden' }}>
          <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '10px 14px', fontSize: '0.7rem', fontWeight: '800', color: '#444', textTransform: 'uppercase' }}>Order Book</div>
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <OrderBook symbol={symbol} onPriceClick={(p) => setPrice(p.toString())} />
            </div>
          </div>
          <div style={{ height: '300px', borderTop: '1px solid #111', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '10px 14px', fontSize: '0.7rem', fontWeight: '800', color: '#444', textTransform: 'uppercase' }}>Recent Market Trades</div>
            <div className="custom-scroll" style={{ flex: 1, overflowY: 'auto', padding: '0 14px' }}>
              {[...Array(20)].map((_, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', padding: '3px 0', borderBottom: '1px solid #0a0a0a' }}>
                  <span style={{ color: Math.random() > 0.5 ? '#00b07c' : '#ff4b4b', fontWeight: '600' }}>{(currentPrice + Math.random() * 2).toFixed(2)}</span>
                  <span style={{ color: '#444', fontFamily: 'monospace' }}>{(Math.random() * 0.5).toFixed(4)}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Center Col: Chart & Positions */}
        <section style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ flex: 2, background: '#000', position: 'relative', overflow: 'hidden' }}>
            <AdvancedChart symbol={symbol} interval={interval} hideRSI={true} />
            {/* Timeframe float overlay - Positioned below indicator legend to avoid overlap */}
            <div style={{ position: 'absolute', top: '40px', left: '15px', display: 'flex', gap: '4px', zIndex: 5 }}>
              {['1m', '5m', '15m', '1h', '4h', '1d'].map(tf => (
                <button key={tf} onClick={() => setInterval(tf)}
                  style={{ padding: '3px 8px', fontSize: '0.65rem', background: interval === tf ? '#222' : 'rgba(0,0,0,0.5)', border: `1px solid ${interval === tf ? '#00b07c' : '#222'}`, color: interval === tf ? '#00b07c' : '#888', borderRadius: '3px', cursor: 'pointer' }}>
                  {tf}
                </button>
              ))}
            </div>
          </div>

          <div style={{ flex: 1, borderTop: '1px solid #111', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: '#080808' }}>
            <div style={{ display: 'flex', borderBottom: '1px solid #111', justifyContent: 'space-between', alignItems: 'center', paddingRight: '14px' }}>
              <div style={{ display: 'flex' }}>
                {['positions', 'orders'].map(tab => (
                  <button key={tab} onClick={() => setActiveBottomTab(tab)}
                    style={{ padding: '12px 20px', background: 'transparent', border: 'none', borderBottom: activeBottomTab === tab ? '2px solid #00b07c' : 'none', color: activeBottomTab === tab ? '#fff' : '#444', fontWeight: '900', fontSize: '0.75rem', textTransform: 'uppercase', cursor: 'pointer' }}>
                    {tab} ({tab === 'positions' ? positions.length : orders.length})
                  </button>
                ))}
              </div>
              {activeBottomTab === 'positions' && positions.length > 0 && (
                <button
                  onClick={handleCloseAll}
                  style={{
                    padding: '4px 12px',
                    background: 'rgba(255, 75, 75, 0.1)',
                    border: '1px solid #ff4b4b',
                    color: '#ff4b4b',
                    borderRadius: '4px',
                    fontSize: '0.65rem',
                    fontWeight: '800',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = '#ff4b4b'}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(255, 75, 75, 0.1)';
                    e.currentTarget.style.color = '#ff4b4b';
                  }}
                >
                  CLOSE ALL
                </button>
              )}
            </div>
            <div className="custom-scroll" style={{ flex: 1, overflowY: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
                <thead style={{ position: 'sticky', top: 0, background: '#080808', color: '#444', textAlign: 'left', zIndex: 1 }}>
                  <tr>
                    {activeBottomTab === 'positions' ? (
                      <>
                        <th style={{ padding: '10px 14px' }}>Market</th>
                        <th style={{ padding: '10px' }}>Size</th>
                        <th style={{ padding: '10px' }}>Entry</th>
                        <th style={{ padding: '10px' }}>Mark</th>
                        <th style={{ padding: '10px' }}>PnL (ROE%)</th>
                      </>
                    ) : (
                      <>
                        <th style={{ padding: '10px 14px' }}>Market</th>
                        <th style={{ padding: '10px' }}>Type</th>
                        <th style={{ padding: '10px' }}>Side</th>
                        <th style={{ padding: '10px' }}>Price</th>
                        <th style={{ padding: '10px' }}>Amount</th>
                      </>
                    )}
                    <th style={{ padding: '10px 14px', textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {activeBottomTab === 'positions' && positions.map((p, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #111' }}>
                      <td style={{ padding: '10px 14px' }}>
                        <span style={{ fontWeight: '800' }}>{p.symbol}</span>
                        <span style={{ marginLeft: '6px', fontSize: '0.6rem', color: p.position_amt > 0 ? '#00b07c' : '#ff4b4b' }}>{p.position_amt > 0 ? 'LONG' : 'SHORT'}</span>
                      </td>
                      <td style={{ padding: '10px', fontFamily: 'monospace' }}>{Math.abs(p.position_amt).toFixed(4)}</td>
                      <td style={{ padding: '10px', color: '#888' }}>{p.entry_price?.toLocaleString()}</td>
                      <td style={{ padding: '10px', color: '#888' }}>{currentPrice.toLocaleString()}</td>
                      <td style={{ padding: '10px', color: p.unrealized_pnl >= 0 ? '#00b07c' : '#ff4b4b', fontWeight: '700' }}>
                        {p.unrealized_pnl?.toFixed(2)} ({((p.unrealized_pnl / (Math.abs(p.position_amt) * p.entry_price / leverage)) * 100).toFixed(2)}%)
                      </td>
                      <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                        <button
                          onClick={() => handleClosePosition(p.symbol)}
                          style={{
                            background: '#111',
                            border: '1px solid #222',
                            color: '#ff4b4b',
                            padding: '2px 8px',
                            borderRadius: '3px',
                            fontSize: '0.65rem',
                            fontWeight: '700',
                            cursor: 'pointer'
                          }}
                        >
                          Close
                        </button>
                      </td>
                    </tr>
                  ))}
                  {activeBottomTab === 'positions' && positions.length === 0 && (
                    <tr><td colSpan="6" style={{ textAlign: 'center', padding: '40px', color: '#333' }}>No active positions</td></tr>
                  )}

                  {activeBottomTab === 'orders' && orders.map((o, i) => {
                    const oid = o.orderId || o.order_id;
                    const qty = o.origQty || o.orig_qty || o.quantity;
                    const p = o.price || o.limitPrice;
                    return (
                      <tr key={i} style={{ borderBottom: '1px solid #111' }}>
                        <td style={{ padding: '10px 14px' }}>
                          <span style={{ fontWeight: '800' }}>{o.symbol}</span>
                        </td>
                        <td style={{ padding: '10px', color: '#aaa' }}>{o.type}</td>
                        <td style={{ padding: '10px' }}>
                          <span style={{ color: o.side === 'BUY' ? '#00b07c' : '#ff4b4b', fontWeight: '800' }}>{o.side}</span>
                        </td>
                        <td style={{ padding: '10px', fontFamily: 'monospace', color: '#f0b90b' }}>{Number(p).toLocaleString()}</td>
                        <td style={{ padding: '10px', fontFamily: 'monospace' }}>{qty}</td>
                        <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                          <button
                            onClick={() => handleCancelOrder(oid, o.symbol)}
                            style={{
                              background: '#1a1a1a',
                              border: '1px solid #333',
                              color: '#aaa',
                              padding: '4px 10px',
                              borderRadius: '4px',
                              fontSize: '0.65rem',
                              fontWeight: '700',
                              cursor: 'pointer',
                              transition: 'all 0.2s'
                            }}
                            onMouseEnter={(e) => { e.currentTarget.style.background = '#222'; e.currentTarget.style.color = '#fff'; }}
                            onMouseLeave={(e) => { e.currentTarget.style.background = '#1a1a1a'; e.currentTarget.style.color = '#aaa'; }}
                          >
                            Cancel
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                  {activeBottomTab === 'orders' && orders.length === 0 && (
                    <tr><td colSpan="6" style={{ textAlign: 'center', padding: '40px', color: '#333' }}>No open orders</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Right Col: AI & Trade Form */}
        <section style={{ display: 'flex', flexDirection: 'column', borderLeft: '1px solid #111', overflow: 'hidden', background: '#0a0a0a' }}>

          {/* Account Performance & AI Intelligence Card */}
          <div className="custom-scroll" style={{ flex: 1, padding: '16px', overflowY: 'auto' }}>

            {/* Account Panel */}
            <div style={{ marginBottom: '20px', borderBottom: '1px solid #1a1a1a', paddingBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f0b90b', boxShadow: '0 0 10px #f0b90b' }} />
                <span style={{ fontSize: '0.75rem', fontWeight: '900', color: '#fff' }}>ACCOUNT PERFORMANCE</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div style={{ background: '#0d0d0d', padding: '10px', borderRadius: '6px', border: '1px solid #1a1a1a' }}>
                  <div style={{ fontSize: '0.55rem', color: '#444', marginBottom: '4px' }}>WALLET BALANCE (총 잔고)</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: '800', color: '#fff' }}>${(balance.balance || 0).toLocaleString()}</div>
                </div>
                <div style={{ background: '#0d0d0d', padding: '10px', borderRadius: '6px', border: '1px solid #1a1a1a' }}>
                  <div style={{ fontSize: '0.55rem', color: '#444', marginBottom: '4px' }}>AVAILABLE (사용 가능)</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: '800', color: '#00b07c' }}>${(balance.available_balance || 0).toLocaleString()}</div>
                </div>
                <div style={{ background: '#0d0d0d', padding: '10px', borderRadius: '6px', border: '1px solid #1a1a1a' }}>
                  <div style={{ fontSize: '0.55rem', color: '#444', marginBottom: '4px' }}>UNREALIZED PNL</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: '800', color: (balance.unrealized_pnl || 0) >= 0 ? '#00b07c' : '#ff4b4b' }}>
                    {(balance.unrealized_pnl || 0).toFixed(2)}
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#00b07c', boxShadow: '0 0 10px #00b07c' }} />
              <span style={{ fontSize: '0.75rem', fontWeight: '900', color: '#fff' }}>AI INTELLIGENCE</span>
            </div>

            <div style={{ background: 'linear-gradient(to right, rgba(0,176,124,0.1), transparent)', borderLeft: '2px solid #00b07c', padding: '12px', borderRadius: '4px', marginBottom: '16px' }}>
              <div style={{ fontSize: '0.6rem', color: '#00b07c', fontWeight: '900', marginBottom: '4px' }}>CORE SIGNAL</div>
              <div style={{ fontSize: '1.2rem', fontWeight: '900', color: '#fff' }}>BULLISH ✓</div>
              <div style={{ fontSize: '0.65rem', color: '#666', marginTop: '2px' }}>Confidence: 89% | Scalping Focus</div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '16px' }}>
              <div style={{ background: '#111', padding: '10px', borderRadius: '6px', border: '1px solid #1a1a1a' }}>
                <div style={{ fontSize: '0.6rem', color: '#444', marginBottom: '4px' }}>RSI (14)</div>
                <div style={{ fontSize: '1rem', fontWeight: '800', color: '#f0b90b' }}>58.4</div>
              </div>
              <div style={{ background: '#111', padding: '10px', borderRadius: '6px', border: '1px solid #1a1a1a' }}>
                <div style={{ fontSize: '0.6rem', color: '#444', marginBottom: '4px' }}>VOL (24H)</div>
                <div style={{ fontSize: '1rem', fontWeight: '800', color: '#fff' }}>2.4B</div>
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '0.65rem', color: '#444', marginBottom: '8px', fontWeight: '800' }}>MULTI-TIMEFRAME ANALYSIS</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {['1H', '4H', '1D'].map(tf => (
                  <div key={tf} style={{ display: 'flex', justifyContent: 'space-between', background: '#0d0d0d', padding: '6px 10px', borderRadius: '3px', fontSize: '0.7rem' }}>
                    <span style={{ color: '#666' }}>{tf} Trend</span>
                    <span style={{ color: '#00b07c', fontWeight: '800' }}>Bullish</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ padding: '12px', background: 'rgba(0,176,124,0.05)', border: '1px solid rgba(0,176,124,0.2)', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.6rem', color: '#00b07c', marginBottom: '4px' }}>AI RECOMMENDATION</div>
              <div style={{ fontSize: '0.85rem', fontWeight: '900', color: '#fff', letterSpacing: '1px' }}>CONSIDER LONG</div>
            </div>
          </div>

          {/* Trade Entry Panel */}
          <div style={{ padding: '16px', background: '#0d0d0d', borderTop: '1px solid #1a1a1a' }}>
            <div style={{ display: 'flex', gap: '4px', marginBottom: '16px', background: '#050505', padding: '3px', borderRadius: '6px' }}>
              {['Limit', 'Market'].map(t => (
                <button key={t} onClick={() => setOrderType(t)}
                  style={{ flex: 1, padding: '8px', border: 'none', background: orderType === t ? '#1a1a1a' : 'transparent', color: orderType === t ? '#fff' : '#444', borderRadius: '4px', fontSize: '0.7rem', fontWeight: '800', cursor: 'pointer', transition: 'all 0.2s' }}>
                  {t}
                </button>
              ))}
            </div>

            <div style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', marginBottom: '6px' }}>
                <span style={{ color: '#444' }}>LEVERAGE</span>
                <span style={{ color: '#00b07c', fontWeight: '900' }}>{leverage}x</span>
              </div>
              <input type="range" min="1" max="125" value={leverage} onChange={e => setLeverage(parseInt(e.target.value))} style={{ width: '100%', accentColor: '#00b07c' }} />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
              {orderType === 'Limit' && (
                <div style={{ position: 'relative' }}>
                  <input type="number" placeholder="Price" value={price} onChange={e => setPrice(e.target.value)}
                    style={{ width: '100%', padding: '12px', background: '#050505', border: '1px solid #1a1a1a', borderRadius: '6px', color: '#fff', outline: 'none', fontSize: '0.85rem' }} />
                  <span style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', fontSize: '0.6rem', color: '#333' }}>USDT</span>
                </div>
              )}
              <div style={{ position: 'relative' }}>
                <input type="number" placeholder={amountUnit === 'COIN' ? "Amount (BTC)" : "Amount (USDT)"} value={quantity} onChange={e => setQuantity(e.target.value)}
                  style={{ width: '100%', padding: '12px', background: '#050505', border: '1px solid #1a1a1a', borderRadius: '6px', color: '#fff', outline: 'none', fontSize: '0.85rem' }} />
                <span
                  onClick={() => setAmountUnit(amountUnit === 'COIN' ? 'USDT' : 'COIN')}
                  style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', fontSize: '0.6rem', color: '#f0b90b', cursor: 'pointer', fontWeight: 'bold' }}>
                  {amountUnit === 'COIN' ? symbol.replace('USDT', '') : 'USDT'} ⇄
                </span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '4px', marginBottom: '16px' }}>
              {[25, 50, 75, 100].map(p => (
                <button key={p} onClick={() => handlePercentage(p)}
                  style={{ padding: '6px', background: '#111', border: '1px solid #222', borderRadius: '4px', color: '#666', fontSize: '0.65rem', fontWeight: '700', cursor: 'pointer' }}>{p}%</button>
              ))}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderTop: '1px solid #1a1a1a', marginBottom: '16px' }}>
              <span style={{ fontSize: '0.7rem', color: '#444' }}>Approx. Cost:</span>
              <span style={{ fontSize: '0.8rem', fontWeight: '900', color: '#fff' }}>${totalUSD.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button onClick={() => handleSubmitOrder('BUY')}
                style={{ flex: 1, padding: '14px', background: 'linear-gradient(135deg, #00875e, #00b07c)', border: 'none', borderRadius: '6px', color: '#fff', fontWeight: '900', cursor: 'pointer', boxShadow: '0 4px 12px rgba(0,176,124,0.3)' }}>BUY / LONG</button>
              <button onClick={() => handleSubmitOrder('SELL')}
                style={{ flex: 1, padding: '14px', background: 'linear-gradient(135deg, #cc2e2e, #ff4b4b)', border: 'none', borderRadius: '6px', color: '#fff', fontWeight: '900', cursor: 'pointer', boxShadow: '0 4px 12px rgba(255,75,75,0.3)' }}>SELL / SHORT</button>
            </div>
          </div>
        </section>

      </main>

      {/* Footer Info */}
      <footer style={{ height: '30px', background: '#050505', borderTop: '1px solid #111', display: 'flex', alignItems: 'center', padding: '0 16px', fontSize: '0.6rem', color: '#333', gap: '20px' }}>
        <div>STABLE CONNECTION: <span style={{ color: '#00b07c' }}>ONLINE</span></div>
        <div>LATENCY: 24ms</div>
        <div style={{ marginLeft: 'auto' }}>VERSION: 4.2.1-PRO-CORE</div>
      </footer>
    </div>
  );
}

export default TradingPerfect;
