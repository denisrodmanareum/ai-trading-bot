import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function DashboardV2() {
  const navigate = useNavigate();

  // State
  const [loading, setLoading] = useState(true);
  const [market, setMarket] = useState({});
  const [news, setNews] = useState([]);
  const [whale, setWhale] = useState([]);
  const [funding, setFunding] = useState([]);
  const [social, setSocial] = useState([]);
  const [aiSignals, setAiSignals] = useState([]);
  const [balance, setBalance] = useState({ balance: 0, available_balance: 0, unrealized_pnl: 0 });

  // Tabs
  const [activeNewsTab, setActiveNewsTab] = useState('all');
  const [activeSocialTab, setActiveSocialTab] = useState('twitter');

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const fetchAllData = async () => {
    try {
      const [newsRes, marketRes, whaleRes, fundingRes, socialRes, aiRes, balanceRes] = await Promise.all([
        fetch('/api/dashboard/v2/news?limit=15'),
        fetch('/api/dashboard/v2/market'),
        fetch('/api/dashboard/v2/onchain/whale?hours_ago=24'),
        fetch('/api/dashboard/v2/onchain/funding'),
        fetch('/api/dashboard/v2/social/trends'),
        fetch('/api/dashboard/v2/ai/signals'),
        fetch('/api/trading/balance')
      ]);

      if (newsRes.ok) setNews((await newsRes.json()).news || []);
      if (marketRes.ok) setMarket((await marketRes.json()).market || {});
      if (whaleRes.ok) setWhale((await whaleRes.json()).whale_activities || []);
      if (fundingRes.ok) setFunding((await fundingRes.json()).funding_rates || []);
      if (socialRes.ok) setSocial((await socialRes.json()).trends || []);
      if (aiRes.ok) setAiSignals((await aiRes.json()).signals || []);
      if (balanceRes.ok) setBalance(await balanceRes.json());

      setLoading(false);
    } catch (e) {
      console.error('Failed to fetch dashboard data:', e);
      setLoading(false);
    }
  };

  const getTimeAgo = (timestamp) => {
    const now = new Date();
    const past = new Date(timestamp);
    const diffMs = now - past;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return '방금 전';
    if (diffMins < 60) return `${diffMins}분 전`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}시간 전`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}일 전`;
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#000', color: '#fff' }}>
        <div>Loading Dashboard...</div>
      </div>
    );
  }

  const filteredNews = activeNewsTab === 'all' ? news : news.filter(n => n.tags && n.tags.includes(activeNewsTab));

  return (
    <div style={{ background: '#000', minHeight: '100vh', color: '#fff', fontFamily: '"Inter", sans-serif', padding: '1rem' }}>
      {/* Header - Market Overview */}
      <header style={{
        background: 'linear-gradient(135deg, #0a0a0a, #151515)',
        border: '1px solid #222',
        borderRadius: '8px',
        padding: '1rem',
        marginBottom: '1rem',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '1rem'
      }}>
        {[
          { label: 'Wallet Balance (잔고)', value: `$${(balance.balance || 0).toLocaleString()}`, color: '#fff' },
          { label: 'Available (사용 가능)', value: `$${(balance.available_balance || 0).toLocaleString()}`, color: '#00b07c' },
          { label: 'Unrealized PnL', value: `${(balance.unrealized_pnl || 0).toFixed(2)}`, color: (balance.unrealized_pnl || 0) >= 0 ? '#00b07c' : '#ff4b4b' },
          { label: 'Total Market Cap', value: `$${((market.total_market_cap || 0) / 1e12).toFixed(2)}T`, color: '#888' },
          { label: 'Fear & Greed', value: `${market.fear_greed_index || 50} - ${market.fear_greed_label || 'Neutral'}`, emoji: market.fear_greed_emoji || '😐', color: market.fear_greed_index > 60 ? '#00b07c' : market.fear_greed_index < 40 ? '#ff4b4b' : '#333' }
        ].map((item, i) => (
          <div key={i} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.25rem', fontWeight: '700', textTransform: 'uppercase' }}>{item.label}</div>
            <div style={{ fontSize: '1.1rem', fontWeight: '900', color: item.color }}>
              {item.emoji && <span style={{ marginRight: '0.5rem' }}>{item.emoji}</span>}
              {item.value}
            </div>
          </div>
        ))}
      </header>

      {/* Main Content Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '400px 1fr 320px',
        gap: '1rem',
        marginBottom: '1rem'
      }}>
        {/* Left: Real-time News */}
        <div style={{ background: '#0a0a0a', border: '1px solid #222', borderRadius: '8px', padding: '1rem', maxHeight: '800px', overflowY: 'auto' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: '900', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            📰 Real-time News
            <div style={{ marginLeft: 'auto', width: '8px', height: '8px', background: '#00b07c', borderRadius: '50%', boxShadow: '0 0 8px #00b07c', animation: 'pulse 2s infinite' }}></div>
          </h3>

          {/* News Tabs */}
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap', fontSize: '0.7rem' }}>
            {['all', 'Bitcoin', 'Ethereum', 'Regulation', 'DeFi'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveNewsTab(tab)}
                style={{
                  padding: '0.25rem 0.75rem',
                  background: activeNewsTab === tab ? '#00b07c' : 'transparent',
                  color: activeNewsTab === tab ? '#000' : '#888',
                  border: `1px solid ${activeNewsTab === tab ? '#00b07c' : '#333'}`,
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: '700',
                  textTransform: 'uppercase'
                }}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* News Feed */}
          {filteredNews.map((article, i) => (
            <div key={i} style={{
              marginBottom: '1rem',
              padding: '0.75rem',
              background: '#151515',
              borderRadius: '6px',
              borderLeft: `3px solid ${article.importance === 'hot' ? '#ff4b4b' : article.importance === 'important' ? '#f0b90b' : '#333'}`,
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#1a1a1a'}
              onMouseLeave={(e) => e.currentTarget.style.background = '#151515'}
              onClick={() => window.open(article.url, '_blank')}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.65rem', color: '#666', fontWeight: '700' }}>{article.source}</span>
                {article.importance === 'hot' && <span style={{ fontSize: '0.65rem', background: '#ff4b4b', color: '#fff', padding: '2px 6px', borderRadius: '3px', fontWeight: '900' }}>🔥 HOT</span>}
              </div>

              <h4 style={{ fontSize: '0.85rem', fontWeight: '700', marginBottom: '0.5rem', lineHeight: '1.4' }}>{article.title}</h4>

              {article.description && (
                <p style={{ fontSize: '0.7rem', color: '#888', marginBottom: '0.5rem', lineHeight: '1.4' }}>
                  {article.description.substring(0, 100)}...
                </p>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.65rem' }}>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <span style={{ color: article.sentiment?.label === 'bullish' ? '#00b07c' : article.sentiment?.label === 'bearish' ? '#ff4b4b' : '#888' }}>
                    {article.sentiment?.emoji} {article.sentiment?.label} ({article.sentiment?.score}%)
                  </span>
                </div>
                <span style={{ color: '#666' }}>{getTimeAgo(article.published_at)}</span>
              </div>

              {article.tags && article.tags.length > 0 && (
                <div style={{ display: 'flex', gap: '0.25rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
                  {article.tags.slice(0, 3).map((tag, idx) => (
                    <span key={idx} style={{ fontSize: '0.6rem', background: '#222', color: '#888', padding: '2px 6px', borderRadius: '3px' }}>{tag}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Center: AI Insights & OnChain Data */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* AI Trading Signals */}
          <div style={{ background: '#0a0a0a', border: '1px solid #222', borderRadius: '8px', padding: '1rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '900', marginBottom: '1rem' }}>🧠 AI Trading Signals</h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '0.75rem' }}>
              {aiSignals.slice(0, 4).map((signal, i) => (
                <div key={i} style={{
                  padding: '1rem',
                  background: `linear-gradient(135deg, ${signal.action.includes('BUY') ? 'rgba(0, 176, 124, 0.1)' : 'rgba(255, 255, 255, 0.05)'}, rgba(0, 0, 0, 0.2))`,
                  border: `1px solid ${signal.action.includes('BUY') ? '#00b07c' : '#333'}`,
                  borderRadius: '6px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '0.9rem', fontWeight: '900' }}>{signal.symbol.replace('USDT', '')}</span>
                    <span style={{ fontSize: '1.2rem' }}>{signal.emoji}</span>
                  </div>

                  <div style={{ fontSize: '0.85rem', fontWeight: '900', color: signal.action.includes('BUY') ? '#00b07c' : '#fff', marginBottom: '0.5rem' }}>
                    {signal.action}
                  </div>

                  <div style={{ fontSize: '0.7rem', color: '#888', marginBottom: '0.5rem' }}>
                    Signal: {signal.signal_strength}/100 | Risk: {signal.risk_level}
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.65rem' }}>
                    <div>
                      <div style={{ color: '#666' }}>Entry</div>
                      <div style={{ color: '#fff', fontWeight: '700' }}>${signal.entry_price.toFixed(2)}</div>
                    </div>
                    <div>
                      <div style={{ color: '#666' }}>Target</div>
                      <div style={{ color: '#00b07c', fontWeight: '700' }}>${signal.target_price.toFixed(2)}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Whale Activities */}
          <div style={{ background: '#0a0a0a', border: '1px solid #222', borderRadius: '8px', padding: '1rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '900', marginBottom: '1rem' }}>🐋 Whale Activities</h3>

            {whale.slice(0, 5).map((tx, i) => (
              <div key={i} style={{
                padding: '0.75rem',
                background: '#151515',
                borderRadius: '4px',
                marginBottom: '0.5rem',
                borderLeft: `3px solid ${tx.transaction_type === 'withdrawal' ? '#00b07c' : tx.transaction_type === 'deposit' ? '#ff4b4b' : '#888'}`
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: '900', color: '#fff' }}>
                    {tx.amount.toLocaleString()} {tx.symbol}
                  </span>
                  <span style={{ fontSize: '0.7rem', color: '#666' }}>{getTimeAgo(tx.timestamp)}</span>
                </div>
                <div style={{ fontSize: '0.7rem', color: '#888' }}>
                  ${(tx.amount_usd / 1000000).toFixed(1)}M | {tx.from} → {tx.to}
                </div>
              </div>
            ))}
          </div>

          {/* Funding Rates */}
          <div style={{ background: '#0a0a0a', border: '1px solid #222', borderRadius: '8px', padding: '1rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '900', marginBottom: '1rem' }}>📊 Funding Rates</h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '0.5rem' }}>
              {funding.map((fund, i) => (
                <div key={i} style={{
                  padding: '0.75rem',
                  background: '#151515',
                  borderRadius: '4px',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: '900', marginBottom: '0.25rem' }}>
                    {fund.symbol.replace('USDT', '')}
                  </div>
                  <div style={{ fontSize: '0.9rem', fontWeight: '900', color: fund.funding_rate > 0 ? '#00b07c' : '#ff4b4b', marginBottom: '0.25rem' }}>
                    {fund.funding_rate > 0 ? '+' : ''}{fund.funding_rate.toFixed(4)}%
                  </div>
                  <div style={{ fontSize: '0.6rem', color: '#666' }}>
                    {fund.emoji} {fund.signal}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Social Trends & Portfolio */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Social Trends */}
          <div style={{ background: '#0a0a0a', border: '1px solid #222', borderRadius: '8px', padding: '1rem', maxHeight: '500px', overflowY: 'auto' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '900', marginBottom: '1rem' }}>💬 Social Trends</h3>

            {social.map((trend, i) => (
              <div key={i} style={{
                padding: '0.75rem',
                background: '#151515',
                borderRadius: '4px',
                marginBottom: '0.5rem'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: '900' }}>#{trend.topic}</span>
                  <span style={{ fontSize: '0.65rem', color: '#666', background: '#222', padding: '2px 6px', borderRadius: '3px' }}>{trend.platform}</span>
                </div>
                <div style={{ fontSize: '0.7rem', color: '#888', marginBottom: '0.25rem' }}>
                  {trend.mentions.toLocaleString()} mentions
                  <span style={{ color: trend.change_24h > 0 ? '#00b07c' : '#ff4b4b', marginLeft: '0.5rem' }}>
                    {trend.change_24h > 0 ? '▲' : '▼'} {Math.abs(trend.change_24h)}%
                  </span>
                </div>
                <div style={{ fontSize: '0.7rem' }}>
                  {trend.sentiment_emoji} <span style={{ color: trend.sentiment === 'Bullish' ? '#00b07c' : '#888' }}>{trend.sentiment}</span>
                  <span style={{ color: '#666', marginLeft: '0.5rem' }}>({trend.sentiment_score}%)</span>
                </div>
              </div>
            ))}
          </div>

          {/* Quick Actions */}
          <div style={{ background: '#0a0a0a', border: '1px solid #222', borderRadius: '8px', padding: '1rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '900', marginBottom: '1rem' }}>⚡ Quick Actions</h3>

            {[
              { label: 'Start Trading', icon: '🚀', color: '#00b07c', path: '/trading' },
              { label: 'AI Hub', icon: '🧠', color: '#5dade2', path: '/ai-hub' },
              { label: 'History', icon: '📊', color: '#f0b90b', path: '/history' }
            ].map((action, i) => (
              <button
                key={i}
                onClick={() => navigate(action.path)}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  marginBottom: '0.5rem',
                  background: `linear-gradient(135deg, ${action.color}22, ${action.color}11)`,
                  border: `1px solid ${action.color}`,
                  borderRadius: '4px',
                  color: '#fff',
                  fontSize: '0.8rem',
                  fontWeight: '900',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
              >
                <span style={{ fontSize: '1.2rem' }}>{action.icon}</span>
                {action.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}

export default DashboardV2;
