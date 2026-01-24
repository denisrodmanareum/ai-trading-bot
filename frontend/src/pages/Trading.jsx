import React, { useState, useEffect, useCallback } from 'react';
import AdvancedChart from '../components/AdvancedChart';
import OrderBook from '../components/OrderBook';
import QuickOrderPanel from '../components/QuickOrderPanel';
import AIControlPanel from '../components/AIControlPanel';
import LastTrades from '../components/LastTrades';

function Trading() {
  const [form, setForm] = useState({
    symbol: localStorage.getItem('selected_trading_symbol') || 'BTCUSDT',
    side: 'BUY',
    quantity: 0.01,
    interval: localStorage.getItem('trading_interval') || '15m',
    leverage: 5,
    type: 'MARKET',
    price: ''
  });

  const [activeSideTab, setActiveSideTab] = useState('Trade'); // Trade, Tools
  const [activeBottomTab, setActiveBottomTab] = useState('Positions');
  const [activeTradeTab, setActiveTradeTab] = useState('Open'); // Open, Close
  const [activeOrderType, setActiveOrderType] = useState('Market'); // Limit, Market, TP/SL
  const [marginMode, setMarginMode] = useState('Isolated'); // Isolated, Cross
  const [leverageValue, setLeverageValue] = useState(5); // Current leverage
  const [activeOrderBookTab, setActiveOrderBookTab] = useState('Order book'); // Order book, Last trades

  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [currentPrice, setCurrentPrice] = useState(null);
  const [positions, setPositions] = useState([]);
  const [openOrders, setOpenOrders] = useState([]);
  const [data, setData] = useState(null);

  const [strategy, setStrategy] = useState({ mode: 'SCALP', leverage_mode: 'AUTO', manual_leverage: 5 });

  const [showSymbolDropdown, setShowSymbolDropdown] = useState(false);
  const [symbolSearch, setSymbolSearch] = useState('');
  const [aiAnalysis, setAiAnalysis] = useState(null); // AI analysis for manual positions



  // Sync with localStorage on mount
  useEffect(() => {
    const storedSymbol = localStorage.getItem('selectedTradingSymbol');
    if (storedSymbol && storedSymbol !== form.symbol) {
      setForm(prevForm => ({ ...prevForm, symbol: storedSymbol }));
    }
  }, []);

  // Data Fetching Logic...
  useEffect(() => {
    fetchStrategyConfig();
    fetchTradingData();
    fetchDashboardOverview();
    const timer = setInterval(() => { fetchTradingData(); fetchDashboardOverview(); }, 5000);
    return () => clearInterval(timer);
  }, [form.symbol]);

  // Fetch AI analysis for positions periodically
  useEffect(() => {
    if (positions.length > 0) {
      fetchAIAnalysis();
      const timer = setInterval(fetchAIAnalysis, 30000); // Every 30s
      return () => clearInterval(timer);
    }
  }, [positions]);

  const fetchStrategyConfig = async () => {
    try {
      const res = await fetch('/api/trading/strategy/config');
      if (res.ok) {
        const d = await res.json();
        if (d.status !== 'not_initialized') setStrategy(d);
      }
    } catch (e) { console.error(e); }
  };

  const updateStrategy = async (updates) => {
    try {
      setStrategy(s => ({ ...s, ...updates }));
      await fetch('/api/trading/strategy/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      setMessage({ type: 'success', text: 'Strategy updated' });
    } catch (e) { console.error(e); }
  };

  const fetchTradingData = useCallback(async () => {
    try {
      const [posRes, ordRes] = await Promise.all([
        fetch('/api/trading/positions'),
        fetch(`/api/trading/orders?symbol=${form.symbol}`)
      ]);
      if (posRes.ok) setPositions(await posRes.json());
      if (ordRes.ok) setOpenOrders(await ordRes.json());
    } catch (e) { console.error(e); }
  }, [form.symbol]);

  const fetchDashboardOverview = async () => {
    try {
      const res = await fetch('/api/dashboard/overview');
      if (res.ok) setData(await res.json());
    } catch (e) { console.error(e); }
  };

  const fetchAIAnalysis = async () => {
    try {
      const res = await fetch('/api/ai/analyze-positions');
      if (res.ok) {
        const analysis = await res.json();
        setAiAnalysis(analysis);
      }
    } catch (e) { console.error('AI Analysis failed:', e); }
  };



  const handleClosePosition = async (symbol) => {
    if (!window.confirm(`Close ${symbol} position?`)) return;
    try {
      const res = await fetch(`/api/trading/close-position/${symbol}`, { method: 'POST' });
      if (res.ok) {
        setMessage({ type: 'success', text: 'Position Closed' });
        fetchTradingData();
      }
    } catch (e) { setMessage({ type: 'error', text: e.message }); }
  };

  const handleOrder = async (side) => {
    setLoading(true);
    try {
      const res = await fetch('/api/trading/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: form.symbol,
          side: side,
          quantity: parseFloat(form.quantity),
          order_type: activeOrderType.toUpperCase(),
          price: activeOrderType === 'Limit' && form.price ? parseFloat(form.price) : null
        })
      });
      if (res.ok) {
        setMessage({ type: 'success', text: `Order Success: ${side}` });
        fetchTradingData();
      } else {
        const err = await res.json();
        throw new Error(err.detail || 'Order failed');
      }
    } catch (e) { setMessage({ type: 'error', text: e.message }); }
    finally { setLoading(false); setTimeout(() => setMessage(null), 3000); }
  };

  const handleCancelOrder = async (orderId) => {
    try {
      const res = await fetch(`/api/trading/orders/${orderId}`, { method: 'DELETE' });
      if (res.ok) {
        setMessage({ type: 'success', text: 'Order Cancelled' });
        fetchTradingData();
      }
    } catch (e) { setMessage({ type: 'error', text: e.message }); }
  };

  const currentSymbolPrice = data?.prices?.[form.symbol] || 0;
  const metrics = data?.market_metrics || {};

  const getFundingCountdown = () => {
    if (!metrics.next_funding_time) return '---';
    const diff = metrics.next_funding_time - Date.now();
    if (diff < 0) return '0h 0m 0s';
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    return `${h}h ${m}m ${s}s`;
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 48px)',
      width: '100%',
      minWidth: '900px',
      background: 'var(--bg-dark)',
      color: 'var(--text-primary)',
      fontFamily: 'Inter, sans-serif',
      overflow: 'hidden'
    }}>

      {/* 1. TOP TICKER RIBBON - MONOCHROME */}
      <div style={{ height: '48px', minHeight: '48px', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', padding: '0 1rem', background: 'var(--bg-dark)', gap: '2rem' }}>
        <div style={{ position: 'relative', display: 'inline-block' }}>
          <div
            onClick={() => setShowSymbolDropdown(!showSymbolDropdown)}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}
          >
            <span style={{ fontSize: '1.1rem', fontWeight: '900', letterSpacing: '-0.02em' }}>{form.symbol}</span>
            <span style={{ fontSize: '0.6rem', padding: '1px 4px', background: '#111', border: '1px solid #222', borderRadius: '1px', color: '#666', fontWeight: 'bold' }}>PERP</span>
            <span style={{ fontSize: '0.7rem', color: '#444' }}>▼</span>
          </div>

          {/* Symbol Dropdown */}
          {showSymbolDropdown && (
            <div style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              marginTop: '0.5rem',
              background: '#0a0a0a',
              border: '1px solid #222',
              borderRadius: '4px',
              boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
              zIndex: 1000,
              minWidth: '200px',
              maxHeight: '400px',
              overflowY: 'auto'
            }}>
              {/* Search */}
              <input
                type="text"
                placeholder="Search symbols..."
                value={symbolSearch}
                onChange={(e) => setSymbolSearch(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  background: '#000',
                  border: 'none',
                  borderBottom: '1px solid #222',
                  color: '#fff',
                  fontSize: '0.75rem',
                  outline: 'none'
                }}
              />

              {/* Symbol List */}
              <div style={{ padding: '0.5rem 0' }}>
                {['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'MATICUSDT', 'DOTUSDT', 'AVAXUSDT', 'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT', 'NEARUSDT', 'APTUSDT', 'ARBUSDT', 'OPUSDT']
                  .filter(s => s.toLowerCase().includes(symbolSearch.toLowerCase()))
                  .map(symbol => (
                    <div
                      key={symbol}
                      onClick={() => {
                        setForm({ ...form, symbol });
                        localStorage.setItem('selectedTradingSymbol', symbol);
                        setShowSymbolDropdown(false);
                        setSymbolSearch('');
                      }}
                      style={{
                        padding: '0.75rem 1rem',
                        cursor: 'pointer',
                        background: form.symbol === symbol ? '#151515' : 'transparent',
                        color: form.symbol === symbol ? '#fff' : '#bbb',
                        fontSize: '0.75rem',
                        fontWeight: '700',
                        transition: 'all 0.2s',
                        borderLeft: form.symbol === symbol ? '2px solid #fff' : '2px solid transparent'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = '#151515'}
                      onMouseLeave={(e) => {
                        if (form.symbol !== symbol) e.currentTarget.style.background = 'transparent';
                      }}
                    >
                      {symbol.replace('USDT', '')} <span style={{ color: '#444', fontSize: '0.65rem' }}>/USDT</span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '1.5rem', height: '100%', alignItems: 'center' }}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '1rem', fontWeight: '800', fontFamily: 'var(--font-mono)', color: currentSymbolPrice > 0 ? 'var(--accent-success)' : 'var(--accent-danger)', lineHeight: '1.1' }}>
              ${currentSymbolPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
            <span style={{ fontSize: '0.6rem', color: '#555', fontWeight: '600' }}>INDEX {metrics.index_price?.toLocaleString() || '---'}</span>
          </div>

          {[
            { label: 'Mark', val: metrics.mark_price?.toLocaleString() || '---' },
            { label: 'Funding (8h)', val: <span style={{ color: 'var(--text-primary)' }}>{(metrics.funding_rate * 100).toFixed(4)}% / {getFundingCountdown()}</span> },
            { label: '24h low', val: metrics.low_24h?.toLocaleString() || '---' },
            { label: '24h high', val: metrics.high_24h?.toLocaleString() || '---' },
            { label: 'Kimchi Prem.', val: <span style={{ color: metrics.kimchi_premium > 0 ? 'var(--accent-success)' : 'var(--accent-danger)' }}>{metrics.kimchi_premium?.toFixed(2)}%</span> },
            { label: '24h volume', val: metrics.volume_24h?.toLocaleString() || '---' }
          ].map(item => (
            <div key={item.label} style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.6rem', color: '#444', textTransform: 'uppercase', fontWeight: '700', letterSpacing: '0.05em' }}>{item.label}</span>
              <span style={{ fontSize: '0.75rem', color: '#bbb', fontWeight: '700', fontFamily: 'var(--font-mono)' }}>{item.val}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 2. MAIN GRID LAYOUT - Responsive with viewport units */}
      <div style={{
        flex: 1,
        display: 'grid',
        gridTemplateColumns: '1fr minmax(250px, 18vw) minmax(280px, 20vw)',
        minHeight: '500px',
        maxHeight: 'calc(100vh - 140px)',
        overflow: 'hidden'
      }}>

        {/* CENTER: CHART SECTION */}
        <div style={{ display: 'flex', flexDirection: 'column', borderRight: '1px solid var(--border-color)', gridRow: '1' }}>
          {/* Chart Header with Timeframe Selector */}
          <div style={{ height: '32px', borderBottom: '1px solid var(--border-dim)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 1rem', background: '#030303' }}>
            {/* Left: Chart Tabs */}
            <div style={{ display: 'flex', gap: '1.5rem' }}>
              {['Chart', 'Overview', 'Feed'].map(t => (
                <span key={t} style={{ fontSize: '0.7rem', fontWeight: '800', textTransform: 'uppercase', color: t === 'Chart' ? '#fff' : '#444', cursor: 'pointer', letterSpacing: '0.05em' }}>{t}</span>
              ))}
            </div>

            {/* Right: Timeframe Selector */}
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              {['1m', '5m', '15m', '1h', '4h', '1d'].map(interval => (
                <button
                  key={interval}
                  onClick={() => setForm({ ...form, interval })}
                  style={{
                    background: form.interval === interval ? '#1a1a1a' : 'transparent',
                    border: 'none',
                    color: form.interval === interval ? '#fff' : '#666',
                    padding: '4px 10px',
                    borderRadius: '2px',
                    fontSize: '0.7rem',
                    fontWeight: '800',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    textTransform: 'uppercase'
                  }}
                  onMouseEnter={(e) => {
                    if (form.interval !== interval) {
                      e.currentTarget.style.background = '#0f0f0f';
                      e.currentTarget.style.color = '#aaa';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (form.interval !== interval) {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = '#666';
                    }
                  }}
                >
                  {interval}
                </button>
              ))}
            </div>
          </div>
          {/* Advanced Chart with Indicators */}
          <div style={{ flex: 1, minHeight: '400px' }}>
            <AdvancedChart symbol={form.symbol} interval={form.interval} />
          </div>
        </div>

        {/* RIGHT 1: ORDER BOOK / LAST TRADES */}
        <div style={{ borderRight: '1px solid var(--border-color)', gridRow: '1 / span 1', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Tab Switcher */}
          <div style={{ height: '32px', borderBottom: '1px solid var(--border-dim)', display: 'flex', alignItems: 'center', padding: '0 0.75rem', gap: '1.5rem', background: '#030303' }}>
            {['Order book', 'Last trades'].map(t => (
              <span
                key={t}
                onClick={() => setActiveOrderBookTab(t)}
                style={{
                  fontSize: '0.7rem',
                  fontWeight: '800',
                  textTransform: 'uppercase',
                  color: activeOrderBookTab === t ? '#fff' : '#444',
                  cursor: 'pointer',
                  letterSpacing: '0.05em',
                  transition: 'color 0.2s'
                }}
              >
                {t}
              </span>
            ))}
          </div>

          {/* Content */}
          {activeOrderBookTab === 'Order book' ? (
            <OrderBook symbol={form.symbol} />
          ) : (
            <LastTrades symbol={form.symbol} />
          )}
        </div>

        {/* RIGHT 2: TRADE SIDEBAR - Responsive */}
        <div style={{
          gridRow: '1 / span 2',
          background: 'var(--bg-panel)',
          display: 'flex',
          flexDirection: 'column',
          borderLeft: '1px solid var(--border-color)',
          overflowY: 'auto',
          minWidth: '280px',
          maxWidth: '400px'
        }}>
          {/* Sidebar Tabs */}
          <div style={{ height: '40px', borderBottom: '1px solid var(--border-dim)', display: 'flex', alignItems: 'center', padding: '0 1rem', gap: '1.5rem', background: '#030303' }}>
            {['Trade', 'Tools'].map(t => (
              <span key={t} onClick={() => setActiveSideTab(t)} style={{ fontSize: '0.75rem', fontWeight: '800', textTransform: 'uppercase', color: activeSideTab === t ? '#fff' : '#444', cursor: 'pointer', letterSpacing: '0.05em' }}>{t}</span>
            ))}
          </div>

          <div style={{ padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Open / Close Tabs */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', background: '#000', border: '1px solid var(--border-dim)', borderRadius: '2px', padding: '2px' }}>
              {['Open', 'Close'].map(t => (
                <button
                  key={t}
                  onClick={() => setActiveTradeTab(t)}
                  style={{
                    border: 'none',
                    padding: '0.4rem',
                    fontSize: '0.75rem',
                    fontWeight: '900',
                    textTransform: 'uppercase',
                    borderRadius: '1px',
                    background: activeTradeTab === t ? '#151515' : 'transparent',
                    color: t === 'Open' && activeTradeTab === t ? 'var(--accent-success)' : activeTradeTab === t ? '#fff' : '#444',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  {t}
                </button>
              ))}
            </div>

            {/* Margin/Leverage */}
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <div
                onClick={() => setMarginMode(marginMode === 'Isolated' ? 'Cross' : 'Isolated')}
                style={{
                  flex: 1,
                  borderBottom: '1px solid var(--border-dim)',
                  padding: '0.3rem 0',
                  fontSize: '0.7rem',
                  fontWeight: 'bold',
                  textAlign: 'center',
                  color: '#fff',
                  textTransform: 'uppercase',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                {marginMode} ▼
              </div>
              <div
                onClick={() => {
                  const leverages = [1, 2, 3, 5, 10, 20, 50, 75, 100];
                  const currentIndex = leverages.indexOf(leverageValue);
                  const nextIndex = (currentIndex + 1) % leverages.length;
                  setLeverageValue(leverages[nextIndex]);
                  setForm({ ...form, leverage: leverages[nextIndex] });
                }}
                style={{
                  flex: 1,
                  borderBottom: '1px solid var(--border-dim)',
                  padding: '0.3rem 0',
                  fontSize: '0.7rem',
                  fontWeight: 'bold',
                  textAlign: 'center',
                  color: leverageValue >= 10 ? 'var(--accent-danger)' : '#fff',
                  textTransform: 'uppercase',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                {leverageValue}x {leverageValue}x ▼
              </div>
            </div>

            {/* Order Type Tabs */}
            <div style={{ display: 'flex', gap: '1rem', marginTop: '0.2rem' }}>
              {['Limit', 'Market', 'TP/SL'].map(t => (
                <span
                  key={t}
                  onClick={() => {
                    setActiveOrderType(t);
                    setForm({ ...form, type: t.toUpperCase() });
                  }}
                  style={{
                    fontSize: '0.7rem',
                    fontWeight: '800',
                    textTransform: 'uppercase',
                    color: activeOrderType === t ? '#fff' : '#444',
                    cursor: 'pointer',
                    borderBottom: activeOrderType === t ? '1.5px solid #fff' : 'none',
                    paddingBottom: '3px',
                    letterSpacing: '0.02em',
                    transition: 'all 0.2s'
                  }}
                >
                  {t}
                </span>
              ))}
            </div>

            {/* Inputs */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.7rem', marginTop: '0.5rem' }}>
              <div style={{ position: 'relative' }}>
                <span style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', fontSize: '0.65rem', fontWeight: '800', color: '#444', textTransform: 'uppercase' }}>Price</span>
                <input
                  readOnly={activeOrderType === 'Market'}
                  value={activeOrderType === 'Market' ? 'Market' : form.price || currentPrice || ''}
                  onChange={(e) => setForm({ ...form, price: e.target.value })}
                  style={{
                    width: '100%',
                    background: activeOrderType === 'Market' ? '#0a0a0a' : '#000',
                    border: '1px solid var(--border-dim)',
                    padding: '0.7rem 4rem 0.7rem 3rem',
                    borderRadius: '2px',
                    fontSize: '0.85rem',
                    color: activeOrderType === 'Market' ? '#666' : '#fff',
                    textAlign: 'right',
                    outline: 'none',
                    fontFamily: 'var(--font-mono)',
                    cursor: activeOrderType === 'Market' ? 'not-allowed' : 'text'
                  }}
                />
                <span style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', fontSize: '0.65rem', fontWeight: '800', color: '#666' }}>USDT</span>
              </div>
              <div style={{ position: 'relative' }}>
                <span style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', fontSize: '0.65rem', fontWeight: '800', color: '#444', textTransform: 'uppercase' }}>Amount</span>
                <input value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} style={{ width: '100%', background: '#000', border: '1px solid var(--border-dim)', padding: '0.7rem 4.5rem 0.7rem 4rem', borderRadius: '2px', fontSize: '0.85rem', color: '#fff', textAlign: 'right', outline: 'none', fontFamily: 'var(--font-mono)' }} />
                <span style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', fontSize: '0.65rem', fontWeight: '800', color: '#666' }}>{form.symbol.replace('USDT', '')}</span>
              </div>
            </div>

            {/* Percent Selector - Monochromatic Dots */}
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0' }}>
              {[0, 25, 50, 75, 100].map(p => {
                const available = data?.account?.balance || 0;
                const targetQty = p === 0 ? 0 : (available * (p / 100) * (strategy.manual_leverage || 5)) / (currentSymbolPrice || 1);
                const isActive = form.quantity > 0 && Math.abs((form.quantity / targetQty) - 1) < 0.1;
                return (
                  <div
                    key={p}
                    onClick={() => setForm({ ...form, quantity: parseFloat(targetQty.toFixed(4)) })}
                    style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px', cursor: 'pointer' }}
                  >
                    <div style={{ width: '6px', height: '6px', border: '1px solid #222', borderRadius: '1px', background: isActive ? '#fff' : 'transparent', transition: 'all 0.2s' }} />
                    <span style={{ fontSize: '0.6rem', fontWeight: '800', color: isActive ? '#fff' : '#333' }}>{p}%</span>
                  </div>
                );
              })}
            </div>

            {/* Buy/Sell Button */}
            <button
              onClick={() => handleOrder(activeTradeTab === 'Open' ? 'BUY' : 'SELL')}
              disabled={loading}
              style={{
                marginTop: '0.4rem',
                background: activeTradeTab === 'Open' ? '#00b07c' : '#ff5b5b',
                color: '#000',
                border: 'none',
                padding: '0.85rem',
                borderRadius: '2px',
                fontWeight: '900',
                fontSize: '0.9rem',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                cursor: 'pointer',
                opacity: loading ? 0.7 : 1,
                transition: 'opacity 0.2s'
              }}
            >
              {loading ? 'Processing...' : (activeTradeTab === 'Open' ? 'Buy / Long' : 'Sell / Short')}
            </button>

            {/* AI Integration Section - Monochrome */}
            <div style={{ marginTop: '0.5rem', borderTop: '1px solid var(--border-dim)', paddingTop: '1rem' }}>
              <AIControlPanel strategy={strategy} updateStrategy={updateStrategy} activeSymbol={form.symbol} executionStatus={strategy.enabled ? 'ACTIVE' : 'PAUSED'} />
            </div>
          </div>
        </div>

        {/* BOTTOM: POSITIONS PANEL - Responsive */}
        <div style={{
          gridColumn: '1 / span 2',
          borderTop: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--bg-dark)',
          minHeight: '200px',
          maxHeight: '35vh',
          overflow: 'hidden'
        }}>
          <div style={{ height: '36px', borderBottom: '1px solid var(--border-dim)', display: 'flex', alignItems: 'center', padding: '0 1rem', gap: '2rem', background: '#030303' }}>
            {['Open orders', 'Order history', 'Open positions', 'Position history', 'Assets'].map(t => (
              <span
                key={t}
                onClick={() => setActiveBottomTab(t)}
                style={{
                  fontSize: '0.7rem',
                  fontWeight: '800',
                  textTransform: 'uppercase',
                  color: activeBottomTab === t ? '#fff' : '#444',
                  cursor: 'pointer',
                  position: 'relative',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  letterSpacing: '0.05em'
                }}
              >
                {t}
                {activeBottomTab === t && <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: '1.5px', background: '#fff' }} />}
              </span>
            ))}
          </div>

          {/* Bottom Panel Content - Conditional Rendering */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {activeBottomTab === 'Open positions' && (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
                <thead>
                  <tr style={{ color: '#444', textAlign: 'left', borderBottom: '1px solid var(--border-dim)', background: '#020202' }}>
                    <th style={{ padding: '0.6rem 1rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Symbol</th>
                    <th style={{ padding: '0.6rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Size</th>
                    <th style={{ padding: '0.6rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Entry Price</th>
                    <th style={{ padding: '0.6rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Mark Price</th>
                    <th style={{ padding: '0.6rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Leverage</th>
                    <th style={{ padding: '0.6rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Unrealized PnL</th>
                    <th style={{ padding: '0.6rem 1rem', textAlign: 'right', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.length > 0 ? positions.map((pos, i) => {
                    const sizeUSDT = Math.abs(pos.position_amt) * (pos.entry_price || 0);
                    return (
                      <tr key={i} style={{ borderBottom: '1px solid #080808', transition: 'background 0.2s' }}>
                        <td style={{ padding: '0.75rem 1rem', fontWeight: '800' }}>{pos.symbol} <span style={{ color: pos.position_amt > 0 ? '#00b07c' : '#ff5b5b', fontSize: '0.65rem', marginLeft: '4px' }}>{pos.position_amt > 0 ? 'LONG' : 'SHORT'}</span></td>
                        <td style={{ padding: '0.75rem', fontFamily: 'var(--font-mono)', fontWeight: '700' }}>
                          <div>{Math.abs(pos.position_amt).toFixed(4)}</div>
                          <div style={{ fontSize: '0.65rem', color: '#666', marginTop: '2px' }}>${sizeUSDT.toLocaleString(undefined, { maximumFractionDigits: 2 })}</div>
                        </td>
                        <td style={{ padding: '0.75rem', fontFamily: 'var(--font-mono)', color: '#bbb' }}>{pos.entry_price?.toLocaleString()}</td>
                        <td style={{ padding: '0.75rem', fontFamily: 'var(--font-mono)', color: '#bbb' }}>{pos.mark_price?.toLocaleString()}</td>
                        <td style={{ padding: '0.75rem', fontFamily: 'var(--font-mono)', color: '#f0b90b', fontWeight: '800' }}>{pos.leverage || 5}x</td>
                        <td style={{ padding: '0.75rem', fontFamily: 'var(--font-mono)', color: pos.unrealized_pnl >= 0 ? '#00b07c' : '#ff5b5b', fontWeight: '900' }}>
                          {pos.unrealized_pnl >= 0 ? '+' : ''}{pos.unrealized_pnl.toFixed(2)} ({((pos.unrealized_pnl / (pos.entry_price * Math.abs(pos.position_amt) / (pos.leverage || strategy.manual_leverage || 5))) * 100).toFixed(2)}%)
                        </td>
                        <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                          <button
                            onClick={() => handleClosePosition(pos.symbol)}
                            style={{ background: 'transparent', border: '1px solid #222', color: '#666', padding: '2px 8px', borderRadius: '1px', cursor: 'pointer', fontSize: '0.65rem', fontWeight: '900', textTransform: 'uppercase' }}>Close</button>
                        </td>
                      </tr>
                    );
                  }) : (
                    <tr><td colSpan="7" style={{ textAlign: 'center', padding: '3rem', color: '#222', fontSize: '0.8rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.1em' }}>No active positions</td></tr>
                  )}
                </tbody>
              </table>
            )}

            {activeBottomTab === 'Open orders' && (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
                <thead>
                  <tr style={{ color: '#444', textAlign: 'left', borderBottom: '1px solid var(--border-dim)', background: '#020202' }}>
                    <th style={{ padding: '0.6rem 1rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Symbol</th>
                    <th style={{ padding: '0.6rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Type</th>
                    <th style={{ padding: '0.6rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Side</th>
                    <th style={{ padding: '0.6rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Price</th>
                    <th style={{ padding: '0.6rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Amount</th>
                    <th style={{ padding: '0.6rem 1rem', textAlign: 'right', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {openOrders.length > 0 ? openOrders.map((order, i) => {
                    const oid = order.orderId || order.order_id;
                    const qty = order.origQty || order.orig_qty || order.quantity;
                    const price = order.price || order.limitPrice; // Fallback just in case
                    return (
                      <tr key={i} style={{ borderBottom: '1px solid #080808' }}>
                        <td style={{ padding: '0.75rem 1rem', fontWeight: '800' }}>{order.symbol}</td>
                        <td style={{ padding: '0.75rem', color: '#888' }}>{order.type}</td>
                        <td style={{ padding: '0.75rem' }}><span style={{ color: order.side === 'BUY' ? '#00b07c' : '#ff5b5b', fontWeight: '800', fontSize: '0.7rem' }}>{order.side}</span></td>
                        <td style={{ padding: '0.75rem', fontFamily: 'var(--font-mono)', color: '#bbb' }}>{price}</td>
                        <td style={{ padding: '0.75rem', fontFamily: 'var(--font-mono)', fontWeight: '700' }}>{qty}</td>
                        <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                          <button
                            onClick={() => handleCancelOrder(oid)}
                            style={{ background: 'transparent', border: '1px solid #222', color: '#666', padding: '2px 8px', borderRadius: '1px', cursor: 'pointer', fontSize: '0.65rem', fontWeight: '900', textTransform: 'uppercase' }}>Cancel</button>
                        </td>
                      </tr>
                    );
                  }) : (
                    <tr><td colSpan="6" style={{ textAlign: 'center', padding: '3rem', color: '#222', fontSize: '0.8rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.1em' }}>No open orders</td></tr>
                  )}
                </tbody>
              </table>
            )}

            {(activeBottomTab === 'Order history' || activeBottomTab === 'Position history') && (
              <div style={{ padding: '3rem', textAlign: 'center', color: '#222', fontSize: '0.8rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                {activeBottomTab} - Feature coming soon
              </div>
            )}

            {activeBottomTab === 'Assets' && (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
                <thead>
                  <tr style={{ color: '#444', textAlign: 'left', borderBottom: '1px solid var(--border-dim)', background: '#020202' }}>
                    <th style={{ padding: '0.6rem 1rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Asset</th>
                    <th style={{ padding: '0.6rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Balance</th>
                    <th style={{ padding: '0.6rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Available</th>
                    <th style={{ padding: '0.6rem 1rem', textAlign: 'right', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em' }}>USD Value</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ borderBottom: '1px solid #080808' }}>
                    <td style={{ padding: '0.75rem 1rem', fontWeight: '800' }}>USDT</td>
                    <td style={{ padding: '0.75rem', fontFamily: 'var(--font-mono)', fontWeight: '700' }}>{data?.account?.balance?.toFixed(2) || '0.00'}</td>
                    <td style={{ padding: '0.75rem', fontFamily: 'var(--font-mono)', color: '#00b07c', fontWeight: '700' }}>{data?.account?.available_balance?.toFixed(2) || '0.00'}</td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontFamily: 'var(--font-mono)', color: '#bbb' }}>${data?.account?.balance?.toFixed(2) || '0.00'}</td>
                  </tr>
                </tbody>
              </table>
            )}
          </div>
        </div>

      </div>

      {/* Notifications */}
      {message && (
        <div style={{
          position: 'fixed', bottom: '2rem', right: '2rem',
          padding: '0.75rem 1.5rem', borderRadius: '2px', zIndex: 1000,
          background: message.type === 'success' ? 'var(--accent-success)' : 'var(--accent-danger)',
          color: '#000', fontWeight: '900', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
        }}>
          {message.text}
        </div>
      )}
    </div>
  );
}

export default Trading;
