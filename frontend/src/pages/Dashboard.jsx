import React, { useState, useEffect, useRef } from 'react';
import { createChart, ColorType } from 'lightweight-charts';
import { useNavigate } from 'react-router-dom';

function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeNav, setActiveNav] = useState('Markets');
  const [hotCryptoType, setHotCryptoType] = useState('Spot');
  const [newListingsType, setNewListingsType] = useState('Spot');
  const [activeMainTab, setActiveMainTab] = useState('Crypto');
  const [activeCategory, setActiveCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [favorites, setFavorites] = useState(new Set());
  const [quickWins, setQuickWins] = useState(null); // Quick Wins alerts
  
  // Chart refs
  const macroChartRef = useRef(null);
  const etfChartRef = useRef(null);
  const rowChartRefs = useRef(new Map());
  const cancelledRef = useRef(false);
  const retryTimersRef = useRef([]);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const res = await fetch('/api/dashboard/overview');
        if (res.ok) {
          const result = await res.json();
          setData(result);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
    const timer = setInterval(fetchAll, 5000);
    return () => clearInterval(timer);
  }, []);

  // Fetch Quick Wins alerts
  useEffect(() => {
    const fetchQuickWins = async () => {
      try {
        const res = await fetch('/api/quick-wins/all?symbols=BTC,ETH,SOL');
        if (res.ok) {
          const result = await res.json();
          setQuickWins(result);
        }
      } catch (e) {
        console.error('Quick Wins fetch failed:', e);
      }
    };
    fetchQuickWins();
    const timer = setInterval(fetchQuickWins, 60000); // 1분마다 체크
    return () => clearInterval(timer);
  }, []);

  // Initialize charts
  useEffect(() => {
    if (loading) return;

    const initCharts = () => {
      if (cancelledRef.current) return;
      // Macro data chart
      if (macroChartRef.current && !macroChartRef.current.chart) {
        const container = macroChartRef.current;
        if (container.clientWidth === 0) {
          retryTimersRef.current.push(setTimeout(initCharts, 100));
          return;
        }
        
        const chart = createChart(container, {
          width: container.clientWidth,
          height: 60,
          layout: {
            background: { type: ColorType.Solid, color: 'transparent' },
            textColor: '#888',
          },
          grid: {
            vertLines: { visible: false },
            horzLines: { visible: false },
          },
          timeScale: { visible: false },
          rightPriceScale: { visible: false },
        });

        const lineSeries = chart.addLineSeries({
          color: '#00b07c',
          lineWidth: 1,
        });

        // Generate mock data for market cap trend (green upward trend)
        const baseValue = 3.1;
        const mockData = Array.from({ length: 30 }, (_, i) => ({
          time: Date.now() / 1000 - (30 - i) * 3600,
          value: baseValue + (i / 30) * 0.1 + Math.random() * 0.05,
        }));
        lineSeries.setData(mockData);
        macroChartRef.current.chart = chart;
      }

      // ETF flows chart
      if (etfChartRef.current && !etfChartRef.current.chart) {
        const container = etfChartRef.current;
        if (container.clientWidth === 0) {
          retryTimersRef.current.push(setTimeout(initCharts, 100));
          return;
        }
        
        const chart = createChart(container, {
          width: container.clientWidth,
          height: 80,
          layout: {
            background: { type: ColorType.Solid, color: 'transparent' },
            textColor: '#888',
          },
          grid: {
            vertLines: { visible: false },
            horzLines: { visible: false },
          },
          timeScale: { visible: false },
          rightPriceScale: { visible: false },
        });

        const barSeries = chart.addHistogramSeries({
          color: '#00b07c',
          priceFormat: { type: 'volume' },
        });

        // Generate mock ETF flow data (mostly negative/red)
        const mockData = Array.from({ length: 7 }, (_, i) => ({
          time: Date.now() / 1000 - (7 - i) * 86400,
          value: Math.random() > 0.3 ? -(Math.random() * 200 + 50) : Math.random() * 100,
          color: Math.random() > 0.3 ? '#ff5b5b' : '#00b07c',
        }));
        barSeries.setData(mockData);
        etfChartRef.current.chart = chart;
      }
    };

    // Small delay to ensure DOM is ready
    cancelledRef.current = false;
    const timer = setTimeout(initCharts, 100);
    retryTimersRef.current.push(timer);

    return () => {
      cancelledRef.current = true;
      retryTimersRef.current.forEach((t) => clearTimeout(t));
      retryTimersRef.current = [];
      if (macroChartRef.current?.chart) {
        macroChartRef.current.chart.remove();
        macroChartRef.current.chart = null;
      }
      if (etfChartRef.current?.chart) {
        etfChartRef.current.chart.remove();
        etfChartRef.current.chart = null;
      }
    };
  }, [loading]);

  // Initialize row charts
  useEffect(() => {
    if (loading) return;

    const initRowCharts = () => {
      if (cancelledRef.current) return;
      rowChartRefs.current.forEach((container, key) => {
        if (!container || container.chart) return;
        if (container.clientWidth === 0) {
          retryTimersRef.current.push(setTimeout(initRowCharts, 100));
          return;
        }

        const chart = createChart(container, {
          width: container.clientWidth || 60,
          height: 20,
          layout: {
            background: { type: ColorType.Solid, color: 'transparent' },
            textColor: '#888',
          },
          grid: {
            vertLines: { visible: false },
            horzLines: { visible: false },
          },
          timeScale: { visible: false },
          rightPriceScale: { visible: false },
        });

        const lineSeries = chart.addLineSeries({
          color: '#00b07c',
          lineWidth: 1,
        });

        // Generate mock 24h price data (green upward trend)
        const basePrice = 100;
        const mockData = Array.from({ length: 24 }, (_, i) => ({
          time: Date.now() / 1000 - (24 - i) * 3600,
          value: basePrice + (i / 24) * 5 + Math.sin(i / 4) * 2 + Math.random() * 1,
        }));
        lineSeries.setData(mockData);
        container.chart = chart;
      });
    };

    cancelledRef.current = false;
    const timer = setTimeout(initRowCharts, 200);
    retryTimersRef.current.push(timer);
    return () => {
      cancelledRef.current = true;
      retryTimersRef.current.forEach((t) => clearTimeout(t));
      retryTimersRef.current = [];
      rowChartRefs.current.forEach((container) => {
        if (container?.chart) {
          container.chart.remove();
          container.chart = null;
        }
      });
    };
  }, [loading, data]);

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const getSortIcon = (columnKey) => {
    if (sortConfig.key !== columnKey) return '↕';
    return sortConfig.direction === 'asc' ? '↑' : '↓';
  };

  if (loading) return <div className="loading"><div className="spinner"></div></div>;

  const metrics = data?.market_metrics || {};
  const prices = data?.prices || {};

  // Mock data matching the image - filtered by type
  const hotCryptosSpot = [
    { symbol: 'BTC/USDT', price: prices.BTCUSDT || 90012.0, change: 0.83, logo: '🟠' },
    { symbol: 'ETH/USDT', price: prices.ETHUSDT || 3009.05, change: 1.38, logo: '💜' },
    { symbol: 'SOL/USDT', price: prices.SOLUSDT || 129.87, change: 2.03, logo: '🔵' },
  ];

  const hotCryptosFutures = [
    { symbol: 'BTC/USDT', price: prices.BTCUSDT || 90012.0, change: 0.85, logo: '🟠' },
    { symbol: 'ETH/USDT', price: prices.ETHUSDT || 3009.05, change: 1.40, logo: '💜' },
    { symbol: 'BNB/USDT', price: 892.10, change: 2.20, logo: '🟡' },
  ];

  const hotCryptos = hotCryptoType === 'Spot' ? hotCryptosSpot : hotCryptosFutures;

  const newListingsSpot = [
    { symbol: 'LIT/USDT', price: 1.816, change: 9.07, logo: 'L' },
    { symbol: 'FOGO/USDT', price: 0.03110, change: 0.65, logo: '🔥' },
    { symbol: 'BREV/USDT', price: 0.2383, change: -3.29, logo: '🎯' },
  ];

  const newListingsFutures = [
    { symbol: 'LIT/USDT', price: 1.820, change: 9.15, logo: 'L' },
    { symbol: 'FOGO/USDT', price: 0.03120, change: 0.70, logo: '🔥' },
    { symbol: 'BREV/USDT', price: 0.2385, change: -3.20, logo: '🎯' },
  ];

  const newListings = newListingsType === 'Spot' ? newListingsSpot : newListingsFutures;

  const baseCryptoList = [
    { name: 'Bitcoin', symbol: 'BTC', price: prices.BTCUSDT || 89933.80, change24h: 0.86, range24h: { low: 87187.90, high: 90481.60 }, marketCap: 1790000000000, logo: '🟠', type: 'Crypto', category: 'Top' },
    { name: 'Ethereum', symbol: 'ETH', price: prices.ETHUSDT || 3006.02, change24h: 1.39, range24h: { low: 2864.24, high: 3066.53 }, marketCap: 361830000000, logo: '💜', type: 'Crypto', category: 'Top' },
    { name: 'Tether', symbol: 'USDT', price: 0.99906, change24h: 0.02, range24h: { low: 0.99836, high: 0.99927 }, marketCap: 186730000000, logo: '💵', type: 'Crypto', category: 'Payment' },
    { name: 'BNB', symbol: 'BNB', price: 892.10, change24h: 2.19, range24h: { low: 863.50, high: 893.40 }, marketCap: 121240000000, logo: '🟡', type: 'Crypto', category: 'Top' },
    { name: 'XRP', symbol: 'XRP', price: 1.9573, change24h: 3.01, range24h: { low: 1.8701, high: 1.9880 }, marketCap: 118510000000, logo: '💙', type: 'Crypto', category: 'Payment' },
    { name: 'USD Coin', symbol: 'USDC', price: 0.99978, change24h: 0.00, range24h: { low: 0.99946, high: 1.0001 }, marketCap: 74420000000, logo: '🔵', type: 'Crypto', category: 'Payment' },
    { name: 'Solana', symbol: 'SOL', price: prices.SOLUSDT || 129.75, change24h: 2.04, range24h: { low: 125.17, high: 131.99 }, marketCap: 73480000000, logo: '🔵', type: 'Crypto', category: 'Solana' },
    { name: 'Tron', symbol: 'TRX', price: 0.29984, change24h: 1.31, range24h: { low: 0.29467, high: 0.30130 }, marketCap: 28330000000, logo: '🔴', type: 'Crypto', category: 'Layer 1' },
    { name: 'Lido Staked Ether', symbol: 'STETH', price: 3001.57, change24h: 1.43, range24h: { low: 2866.42, high: 3063.00 }, marketCap: 27660000000, logo: '💎', type: 'Crypto', category: 'DeFi' },
    { name: 'Dogecoin', symbol: 'DOGE', price: 0.12659, change24h: 1.97, range24h: { low: 0.12019, high: 0.12869 }, marketCap: 21200000000, logo: '🐕', type: 'Crypto', category: 'Meme' },
    { name: 'Cardano', symbol: 'ADA', price: 0.36460, change24h: 2.07, range24h: { low: 0.35634, high: 0.37340 }, marketCap: 13370000000, logo: '🔷', type: 'Crypto', category: 'Layer 1' },
  ];

  // Add favorite property based on state
  const cryptoList = baseCryptoList.map(crypto => ({
    ...crypto,
    favorite: favorites.has(crypto.symbol)
  }));

  // Filter and sort crypto list based on active tabs and filters
  let filteredCryptoList = [...cryptoList];

  // Filter by main tab (Favorites, Crypto, Spot, Futures, Options)
  if (activeMainTab === 'Favorites') {
    filteredCryptoList = filteredCryptoList.filter(c => c.favorite);
  } else if (activeMainTab === 'Spot') {
    // Spot trading pairs (all crypto)
    filteredCryptoList = filteredCryptoList;
  } else if (activeMainTab === 'Futures') {
    // Futures trading pairs (major coins)
    filteredCryptoList = filteredCryptoList.filter(c => ['BTC', 'ETH', 'SOL', 'BNB', 'XRP'].includes(c.symbol));
  } else if (activeMainTab === 'Options') {
    // Options (limited selection)
    filteredCryptoList = filteredCryptoList.filter(c => ['BTC', 'ETH'].includes(c.symbol));
  }

  // Filter by category
  if (activeCategory !== 'All') {
    if (activeCategory === 'Top') {
      filteredCryptoList = filteredCryptoList.filter(c => c.marketCap > 100000000000); // Top 10 by market cap
    } else if (activeCategory === 'New') {
      filteredCryptoList = filteredCryptoList.filter(c => ['SOL', 'DOGE', 'ADA'].includes(c.symbol)); // Mock new coins
    } else {
      filteredCryptoList = filteredCryptoList.filter(c => c.category === activeCategory);
    }
  }

  // Filter by search query
  if (searchQuery) {
    filteredCryptoList = filteredCryptoList.filter(c => 
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.symbol.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }

  // Sort crypto list
  const sortedCryptoList = [...filteredCryptoList].sort((a, b) => {
    if (!sortConfig.key) return 0;
    const aVal = a[sortConfig.key];
    const bVal = b[sortConfig.key];
    if (sortConfig.key === 'range24h') {
      const aRange = a.range24h.high - a.range24h.low;
      const bRange = b.range24h.high - b.range24h.low;
      return sortConfig.direction === 'asc' ? aRange - bRange : bRange - aRange;
    }
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
    }
    return 0;
  });

  const formatMarketCap = (value) => {
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    return `$${value.toFixed(2)}`;
  };

  const formatPrice = (price) => {
    if (price >= 1000) return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (price >= 1) return price.toFixed(2);
    return price.toFixed(5);
  };

  const handleNavigateToTrading = (symbol) => {
    // Store selected symbol in localStorage
    localStorage.setItem('selected_trading_symbol', `${symbol}USDT`);
    // Navigate to trading page
    navigate('/trading');
  };

  return (
    <div style={{ background: '#000', color: '#fff', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>
      {/* Top Navigation */}
      <div style={{ 
        display: 'flex', 
        gap: '2rem', 
        padding: '1rem 2rem', 
        borderBottom: '1px solid #111',
        background: '#000'
      }}>
        {['Markets', 'Rankings', 'Trading data'].map((nav) => (
          <button
            key={nav}
            onClick={() => setActiveNav(nav)}
            style={{
              background: 'transparent',
              border: 'none',
              color: activeNav === nav ? '#fff' : '#444',
              fontSize: '0.875rem',
              fontWeight: 600,
              cursor: 'pointer',
              padding: '0.5rem 0',
              borderBottom: activeNav === nav ? '2px solid #fff' : '2px solid transparent',
              transition: 'all 0.2s',
            }}
          >
            {nav}
          </button>
        ))}
      </div>

      <div style={{ padding: '2rem', maxWidth: '1600px', margin: '0 auto' }}>
        {/* Quick Wins Alerts Banner */}
        {quickWins && quickWins.total_alerts > 0 && (
          <div style={{
            background: 'linear-gradient(90deg, rgba(255,91,91,0.1) 0%, rgba(0,176,124,0.1) 100%)',
            border: '1px solid rgba(255,91,91,0.3)',
            borderRadius: '4px',
            padding: '1rem',
            marginBottom: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '1.2rem' }}>⚡</span>
              <span style={{ fontSize: '0.9rem', fontWeight: '800', color: '#fff', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Quick Wins Alerts ({quickWins.total_alerts})
              </span>
            </div>

            {/* Kimchi Premium Alert */}
            {quickWins.kimchi_premium?.alert && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.75rem',
                background: 'rgba(0,0,0,0.3)',
                borderRadius: '2px',
                border: '1px solid rgba(255,255,255,0.1)'
              }}>
                <span style={{ fontSize: '1.5rem' }}>
                  {quickWins.kimchi_premium.premium_pct > 0 ? '🔥' : '❄️'}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#fff', marginBottom: '0.25rem' }}>
                    김치 프리미엄 {quickWins.kimchi_premium.premium_pct > 0 ? '상승' : '하락'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#bbb' }}>
                    {quickWins.kimchi_premium.alert_message}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '1.2rem', fontWeight: '900', color: quickWins.kimchi_premium.premium_pct > 0 ? '#00b07c' : '#ff5b5b' }}>
                    {quickWins.kimchi_premium.premium_pct > 0 ? '+' : ''}{quickWins.kimchi_premium.premium_pct.toFixed(2)}%
                  </div>
                  <div style={{ fontSize: '0.65rem', color: '#666', marginTop: '0.25rem' }}>
                    Binance: ${quickWins.kimchi_premium.binance_price.toLocaleString()} | Upbit: ${quickWins.kimchi_premium.upbit_price_usd.toLocaleString()}
                  </div>
                </div>
              </div>
            )}

            {/* Volume Spikes */}
            {quickWins.volume_spikes?.map((spike, idx) => (
              <div key={idx} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.75rem',
                background: 'rgba(0,0,0,0.3)',
                borderRadius: '2px',
                border: '1px solid rgba(255,255,255,0.1)'
              }}>
                <span style={{ fontSize: '1.5rem' }}>⚡</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#fff', marginBottom: '0.25rem' }}>
                    거래량 급증 - {spike.symbol}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#bbb' }}>
                    {spike.alert_message}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '1.2rem', fontWeight: '900', color: '#ffaa00' }}>
                    {spike.spike_ratio.toFixed(1)}x
                  </div>
                  <div style={{ fontSize: '0.65rem', color: '#666', marginTop: '0.25rem' }}>
                    현재: {spike.current_volume.toLocaleString()} | 평균: {spike.avg_volume.toLocaleString()}
                  </div>
                </div>
              </div>
            ))}

            {/* Whale Movements */}
            {quickWins.whale_movements?.map((whale, idx) => (
              <div key={idx} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.75rem',
                background: 'rgba(0,0,0,0.3)',
                borderRadius: '2px',
                border: '1px solid rgba(255,255,255,0.1)'
              }}>
                <span style={{ fontSize: '1.5rem' }}>🐋</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#fff', marginBottom: '0.25rem' }}>
                    고래 움직임 - {whale.symbol}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#bbb' }}>
                    {whale.alert_message}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '1.2rem', fontWeight: '900', color: '#ff5b5b' }}>
                    {whale.to_exchanges}건
                  </div>
                  <div style={{ fontSize: '0.65rem', color: '#666', marginTop: '0.25rem' }}>
                    거래소 입금: {whale.total_amount.toFixed(1)} {whale.symbol}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Render different views based on activeNav */}
        {activeNav === 'Markets' && (
          <>
            {/* Header Section - 4 Cards */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(4, 1fr)', 
          gap: '1rem', 
          marginBottom: '2rem' 
        }}>
          {/* Hot crypto */}
          <div style={{ 
            background: '#050505', 
            border: '1px solid #111', 
            borderRadius: '4px',
            padding: '1rem'
          }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              marginBottom: '1rem'
            }}>
              <h3 style={{ margin: 0, fontSize: '0.875rem', fontWeight: 600, color: '#fff' }}>
                Hot crypto <span style={{ color: '#444' }}>›</span>
              </h3>
              <div style={{ display: 'flex', gap: '0.25rem' }}>
                <button
                  onClick={() => setHotCryptoType('Spot')}
                  style={{
                    padding: '0.25rem 0.5rem',
                    fontSize: '0.7rem',
                    background: hotCryptoType === 'Spot' ? '#fff' : 'transparent',
                    color: hotCryptoType === 'Spot' ? '#000' : '#444',
                    border: '1px solid #222',
                    borderRadius: '2px',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  Spot
                </button>
                <button
                  onClick={() => setHotCryptoType('Futures')}
                  style={{
                    padding: '0.25rem 0.5rem',
                    fontSize: '0.7rem',
                    background: hotCryptoType === 'Futures' ? '#fff' : 'transparent',
                    color: hotCryptoType === 'Futures' ? '#000' : '#444',
                    border: '1px solid #222',
                    borderRadius: '2px',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  Futures
                </button>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {hotCryptos.map((crypto, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontSize: '1.2rem' }}>{crypto.logo}</span>
                    <div>
                      <div style={{ fontSize: '0.75rem', fontWeight: 600 }}>{crypto.symbol}</div>
                      <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                        {formatPrice(crypto.price)}
                      </div>
                    </div>
                  </div>
                  <div style={{ 
                    color: crypto.change >= 0 ? '#00b07c' : '#ff5b5b',
                    fontSize: '0.75rem',
                    fontWeight: 600
                  }}>
                    {crypto.change >= 0 ? '+' : ''}{crypto.change.toFixed(2)}%
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* New listings */}
          <div style={{ 
            background: '#050505', 
            border: '1px solid #111', 
            borderRadius: '4px',
            padding: '1rem'
          }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              marginBottom: '1rem'
            }}>
              <h3 style={{ margin: 0, fontSize: '0.875rem', fontWeight: 600, color: '#fff' }}>
                New listings <span style={{ color: '#444' }}>›</span>
              </h3>
              <div style={{ display: 'flex', gap: '0.25rem' }}>
                <button
                  onClick={() => setNewListingsType('Spot')}
                  style={{
                    padding: '0.25rem 0.5rem',
                    fontSize: '0.7rem',
                    background: newListingsType === 'Spot' ? '#fff' : 'transparent',
                    color: newListingsType === 'Spot' ? '#000' : '#444',
                    border: '1px solid #222',
                    borderRadius: '2px',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  Spot
                </button>
                <button
                  onClick={() => setNewListingsType('Futures')}
                  style={{
                    padding: '0.25rem 0.5rem',
                    fontSize: '0.7rem',
                    background: newListingsType === 'Futures' ? '#fff' : 'transparent',
                    color: newListingsType === 'Futures' ? '#000' : '#444',
                    border: '1px solid #222',
                    borderRadius: '2px',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  Futures
                </button>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {newListings.map((crypto, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontSize: '1.2rem' }}>{crypto.logo}</span>
                    <div>
                      <div style={{ fontSize: '0.75rem', fontWeight: 600 }}>{crypto.symbol}</div>
                      <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                        {formatPrice(crypto.price)}
                      </div>
                    </div>
                  </div>
                  <div style={{ 
                    color: crypto.change >= 0 ? '#00b07c' : '#ff5b5b',
                    fontSize: '0.75rem',
                    fontWeight: 600
                  }}>
                    {crypto.change >= 0 ? '+' : ''}{crypto.change.toFixed(2)}%
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Macro data */}
          <div style={{ 
            background: '#050505', 
            border: '1px solid #111', 
            borderRadius: '4px',
            padding: '1rem'
          }}>
            <h3 style={{ 
              margin: '0 0 1rem 0', 
              fontSize: '0.875rem', 
              fontWeight: 600, 
              color: '#fff' 
            }}>
              Macro data <span style={{ color: '#444' }}>›</span>
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '0.75rem' }}>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#444', marginBottom: '0.25rem' }}>Market cap</div>
                <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                  $3.17T <span style={{ color: '#00b07c', fontSize: '0.75rem' }}>+2.47%</span>
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#444', marginBottom: '0.25rem' }}>Volume</div>
                <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                  $148.85B
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#444', marginBottom: '0.25rem' }}>BTC dominance</div>
                <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                  {metrics.btc_dominance?.toFixed(1) || '56.5'}%
                </div>
              </div>
            </div>
            <div ref={macroChartRef} style={{ width: '100%', height: '60px', minWidth: '150px' }} />
          </div>

          {/* BTC ETF flows */}
          <div style={{ 
            background: '#050505', 
            border: '1px solid #111', 
            borderRadius: '4px',
            padding: '1rem'
          }}>
            <h3 style={{ 
              margin: '0 0 1rem 0', 
              fontSize: '0.875rem', 
              fontWeight: 600, 
              color: '#fff' 
            }}>
              BTC ETF flows <span style={{ color: '#444' }}>›</span>
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '0.75rem' }}>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#444', marginBottom: '0.25rem' }}>Daily net</div>
                <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ff5b5b' }}>
                  -$11.30M
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#444', marginBottom: '0.25rem' }}>Last 30D</div>
                <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ff5b5b' }}>
                  -$381.70M
                </div>
              </div>
            </div>
            <div ref={etfChartRef} style={{ width: '100%', height: '80px', minWidth: '150px' }} />
          </div>
        </div>

        {/* Main Data Table Section */}
        <div style={{ background: '#050505', border: '1px solid #111', borderRadius: '4px', padding: '1rem' }}>
          {/* Main Tabs */}
          <div style={{ 
            display: 'flex', 
            gap: '1.5rem', 
            marginBottom: '1rem',
            borderBottom: '1px solid #111',
            paddingBottom: '0.5rem'
          }}>
            {['Favorites', 'Crypto', 'Spot', 'Futures', 'Options'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveMainTab(tab)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: activeMainTab === tab ? '#fff' : '#444',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  padding: '0.5rem 0',
                  borderBottom: activeMainTab === tab ? '2px solid #fff' : '2px solid transparent',
                  transition: 'all 0.2s',
                }}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Category Tabs and Search */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            marginBottom: '1rem'
          }}>
            <div style={{ display: 'flex', gap: '0.75rem', overflowX: 'auto', flex: 1 }}>
              {['All', 'Top', 'New', 'AI', 'Solana', 'RWA', 'Meme', 'Payment', 'DeFi', 'Layer 1', 'Gaming', 'DePIN'].map((cat) => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  style={{
                    padding: '0.5rem 1rem',
                    fontSize: '0.75rem',
                    background: activeCategory === cat ? '#fff' : 'transparent',
                    color: activeCategory === cat ? '#000' : '#444',
                    border: '1px solid #222',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontWeight: 600,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {cat}
                </button>
              ))}
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <div style={{ position: 'relative' }}>
                <input
                  type="text"
                  placeholder="Search..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    padding: '0.5rem 2.5rem 0.5rem 0.75rem',
                    background: '#000',
                    border: '1px solid #222',
                    borderRadius: '4px',
                    color: '#fff',
                    fontSize: '0.75rem',
                    width: '200px',
                  }}
                />
                <span style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: '#444' }}>🔍</span>
              </div>
              <button style={{
                padding: '0.5rem 1rem',
                fontSize: '0.75rem',
                background: 'transparent',
                border: '1px solid #222',
                borderRadius: '4px',
                cursor: 'pointer',
                color: '#444',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}>
                🗂️ Filters
              </button>
            </div>
          </div>

          {/* Crypto Table */}
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #111' }}>
                  <th 
                    style={{ padding: '0.75rem', textAlign: 'left', fontSize: '0.7rem', color: '#444', fontWeight: 600, textTransform: 'uppercase', cursor: 'pointer' }}
                    onClick={() => handleSort('name')}
                  >
                    Name {getSortIcon('name')}
                  </th>
                  <th 
                    style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.7rem', color: '#444', fontWeight: 600, textTransform: 'uppercase', cursor: 'pointer' }}
                    onClick={() => handleSort('price')}
                  >
                    Price {getSortIcon('price')}
                  </th>
                  <th 
                    style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.7rem', color: '#444', fontWeight: 600, textTransform: 'uppercase', cursor: 'pointer' }}
                    onClick={() => handleSort('change24h')}
                  >
                    24h change {getSortIcon('change24h')}
                  </th>
                  <th style={{ padding: '0.75rem', textAlign: 'center', fontSize: '0.7rem', color: '#444', fontWeight: 600, textTransform: 'uppercase' }}>Last 24h</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.7rem', color: '#444', fontWeight: 600, textTransform: 'uppercase' }}>24h range</th>
                  <th 
                    style={{ padding: '0.75rem', textAlign: 'right', fontSize: '0.7rem', color: '#444', fontWeight: 600, textTransform: 'uppercase', cursor: 'pointer' }}
                    onClick={() => handleSort('marketCap')}
                  >
                    Market cap {getSortIcon('marketCap')}
                  </th>
                  <th style={{ padding: '0.75rem', textAlign: 'center', fontSize: '0.7rem', color: '#444', fontWeight: 600, textTransform: 'uppercase' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {sortedCryptoList.map((crypto, idx) => {
                  const chartKey = `${crypto.symbol}-${idx}`;
                  return (
                    <tr 
                      key={idx} 
                      style={{ 
                        borderBottom: '1px solid #080808',
                        transition: 'background 0.2s',
                        cursor: 'pointer'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = '#080808'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      onClick={() => handleNavigateToTrading(crypto.symbol)}
                    >
                      <td style={{ padding: '1rem 0.75rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span 
                            style={{ fontSize: '0.875rem', color: crypto.favorite ? '#ffd700' : '#444', cursor: 'pointer' }}
                            onClick={(e) => {
                              e.stopPropagation();
                              const newFavorites = new Set(favorites);
                              if (crypto.favorite) {
                                newFavorites.delete(crypto.symbol);
                              } else {
                                newFavorites.add(crypto.symbol);
                              }
                              setFavorites(newFavorites);
                            }}
                          >
                            {crypto.favorite ? '★' : '☆'}
                          </span>
                          <span style={{ fontSize: '1.2rem' }}>{crypto.logo}</span>
                          <div>
                            <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{crypto.symbol}</div>
                            <div style={{ fontSize: '0.75rem', color: '#444' }}>{crypto.name}</div>
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: '1rem 0.75rem', textAlign: 'right', fontSize: '0.875rem', fontWeight: 600 }}>
                        ${formatPrice(crypto.price)}
                      </td>
                      <td style={{ padding: '1rem 0.75rem', textAlign: 'right' }}>
                        <span style={{ 
                          color: crypto.change24h >= 0 ? '#00b07c' : '#ff5b5b',
                          fontSize: '0.875rem',
                          fontWeight: 600
                        }}>
                          {crypto.change24h >= 0 ? '+' : ''}{crypto.change24h.toFixed(2)}%
                        </span>
                      </td>
                      <td style={{ padding: '1rem 0.75rem', textAlign: 'center' }}>
                        <div 
                          ref={(el) => {
                            if (el && !rowChartRefs.current.has(chartKey)) {
                              rowChartRefs.current.set(chartKey, el);
                            }
                          }}
                          style={{ 
                            width: '60px', 
                            height: '20px',
                            margin: '0 auto'
                          }} 
                        />
                      </td>
                      <td style={{ padding: '1rem 0.75rem', textAlign: 'right', fontSize: '0.75rem', color: '#444' }}>
                        ${formatPrice(crypto.range24h.low)} - ${formatPrice(crypto.range24h.high)}
                      </td>
                      <td style={{ padding: '1rem 0.75rem', textAlign: 'right', fontSize: '0.875rem', fontWeight: 600 }}>
                        {formatMarketCap(crypto.marketCap)}
                      </td>
                      <td style={{ padding: '1rem 0.75rem', textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                        <button 
                          onClick={(e) => {
                            e.stopPropagation();
                            handleNavigateToTrading(crypto.symbol);
                          }}
                          style={{
                            padding: '0.25rem 0.75rem',
                            fontSize: '0.7rem',
                            background: 'transparent',
                            border: '1px solid #222',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            color: '#fff',
                            fontWeight: 600,
                          }}
                        >
                          Trade
                        </button>
                          <button style={{
                            padding: '0.25rem 0.75rem',
                            fontSize: '0.7rem',
                            background: 'transparent',
                            border: '1px solid #222',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            color: '#444',
                            fontWeight: 600,
                          }}>
                            Convert
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
          </>
        )}

        {activeNav === 'Rankings' && (
          <div style={{ background: '#050505', border: '1px solid #111', borderRadius: '4px', padding: '2rem' }}>
            <h2 style={{ marginBottom: '2rem', fontSize: '1.5rem', fontWeight: 700 }}>Cryptocurrency Rankings</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
              {sortedCryptoList
                .sort((a, b) => b.marketCap - a.marketCap)
                .map((crypto, idx) => (
                  <div 
                    key={idx}
                    style={{
                      background: '#020202',
                      border: '1px solid #111',
                      borderRadius: '4px',
                      padding: '1rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                      <span style={{ fontSize: '1.5rem' }}>#{idx + 1}</span>
                      <span style={{ fontSize: '1.5rem' }}>{crypto.logo}</span>
                      <div>
                        <div style={{ fontSize: '1rem', fontWeight: 600 }}>{crypto.symbol}</div>
                        <div style={{ fontSize: '0.75rem', color: '#444' }}>{crypto.name}</div>
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{formatMarketCap(crypto.marketCap)}</div>
                      <div style={{ 
                        fontSize: '0.75rem', 
                        color: crypto.change24h >= 0 ? '#00b07c' : '#ff5b5b' 
                      }}>
                        {crypto.change24h >= 0 ? '+' : ''}{crypto.change24h.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {activeNav === 'Trading data' && (
          <div style={{ background: '#050505', border: '1px solid #111', borderRadius: '4px', padding: '2rem' }}>
            <h2 style={{ marginBottom: '2rem', fontSize: '1.5rem', fontWeight: 700 }}>Trading Data</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
              <div style={{ background: '#020202', border: '1px solid #111', borderRadius: '4px', padding: '1.5rem' }}>
                <div style={{ fontSize: '0.7rem', color: '#444', marginBottom: '0.5rem', textTransform: 'uppercase' }}>24h Volume</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>$148.85B</div>
                <div style={{ fontSize: '0.75rem', color: '#00b07c', marginTop: '0.5rem' }}>+34.34%</div>
              </div>
              <div style={{ background: '#020202', border: '1px solid #111', borderRadius: '4px', padding: '1.5rem' }}>
                <div style={{ fontSize: '0.7rem', color: '#444', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Active Markets</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>2,847</div>
                <div style={{ fontSize: '0.75rem', color: '#00b07c', marginTop: '0.5rem' }}>+12 new</div>
              </div>
              <div style={{ background: '#020202', border: '1px solid #111', borderRadius: '4px', padding: '1.5rem' }}>
                <div style={{ fontSize: '0.7rem', color: '#444', marginBottom: '0.5rem', textTransform: 'uppercase' }}>BTC Dominance</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{metrics.btc_dominance?.toFixed(1) || '56.5'}%</div>
                <div style={{ fontSize: '0.75rem', color: '#ff5b5b', marginTop: '0.5rem' }}>-0.2%</div>
              </div>
            </div>
            <div style={{ background: '#020202', border: '1px solid #111', borderRadius: '4px', padding: '1.5rem' }}>
              <h3 style={{ marginBottom: '1rem', fontSize: '1rem', fontWeight: 600 }}>Top Gainers (24h)</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {sortedCryptoList
                  .sort((a, b) => b.change24h - a.change24h)
                  .slice(0, 5)
                  .map((crypto, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: '#000', borderRadius: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span>{crypto.logo}</span>
                        <span style={{ fontWeight: 600 }}>{crypto.symbol}</span>
                      </div>
                      <div style={{ color: '#00b07c', fontWeight: 600 }}>
                        +{crypto.change24h.toFixed(2)}%
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
