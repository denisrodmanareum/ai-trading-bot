import React, { useState, useEffect } from 'react';

function AIHub() {
  const [activeTab, setActiveTab] = useState('control'); // control, review, learning, coins

  // AI Control States
  const [training, setTraining] = useState(false);
  const [models, setModels] = useState([]);
  const [loadingModel, setLoadingModel] = useState(null);
  const [selectedModels, setSelectedModels] = useState(new Set());
  const [selectAll, setSelectAll] = useState(false);

  // Coin Selection States
  const [coinSelection, setCoinSelection] = useState({
    selected_coins: [],
    scores: {},
    config: {},
    last_rebalance: null,
    total_coins: 0
  });
  const [coinCandidates, setCoinCandidates] = useState([]);
  const [coinStats, setCoinStats] = useState(null);
  const [rebalancing, setRebalancing] = useState(false);
  const [autoTrain, setAutoTrain] = useState({
    enabled: false,
    min_win_rate: 50.0,
    check_interval_hours: 24,
    retrain_on_loss: true
  });
  const [config, setConfig] = useState({
    symbol: 'BTCUSDT',
    interval: '1m',
    days: 30,
    episodes: 1000,
    leverage: 5,
    stop_loss: 2.0,
    take_profit: 5.0,
    reward_strategy: 'improved'
  });
  const [performance, setPerformance] = useState({
    currentModel: 'None',
    winRate: 0,
    totalTrades: 0,
    avgPnL: 0,
    sharpeRatio: 0,
    lastTraining: '-'
  });

  // Daily Review States
  const [reports, setReports] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  // Learning Progress States
  const [learningProgress, setLearningProgress] = useState(null);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [weeklySummary, setWeeklySummary] = useState(null);

  // Available Symbols State
  const [availableSymbols, setAvailableSymbols] = useState([]);

  // Fetch data on mount
  useEffect(() => {
    fetchModels();
    fetchPerformance();
    fetchSchedulerConfig();
    fetchReports();
    fetchLearningProgress();
    fetchWeeklySummary();
    fetchAvailableSymbols();
  }, []);

  // AI Control Functions
  const fetchModels = async () => {
    try {
      const res = await fetch('/api/ai/models');
      if (res.ok) {
        const data = await res.json();
        setModels(data.models || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchPerformance = async () => {
    try {
      const res = await fetch('/api/ai/status');
      if (res.ok) {
        const data = await res.json();
        setPerformance({
          currentModel: data.current_model || 'None',
          winRate: data.stats?.win_rate || 0,
          totalTrades: data.stats?.total_trades || 0,
          avgPnL: data.stats?.avg_pnl || 0,
          sharpeRatio: data.stats?.sharpe_ratio || 0,
          lastTraining: data.last_training || '-'
        });
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchSchedulerConfig = async () => {
    try {
      const res = await fetch('/api/ai/scheduler/config');
      if (res.ok) {
        const data = await res.json();
        setAutoTrain(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAvailableSymbols = async () => {
    try {
      // 하이브리드 모드에서 선택된 코인들만 가져오기
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

  const startTraining = async () => {
    if (!window.confirm('AI 학습을 시작하시겠습니까?')) return;

    setTraining(true);
    try {
      const res = await fetch('/api/ai/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });

      if (res.ok) {
        alert('학습이 시작되었습니다!');
      }
    } catch (e) {
      console.error(e);
      setTraining(false);
    }
  };

  const toggleModelSelection = (filename) => {
    const newSelection = new Set(selectedModels);
    if (newSelection.has(filename)) {
      newSelection.delete(filename);
    } else {
      newSelection.add(filename);
    }
    setSelectedModels(newSelection);
    setSelectAll(newSelection.size === models.length);
  };

  const toggleSelectAll = () => {
    if (selectAll) {
      setSelectedModels(new Set());
      setSelectAll(false);
    } else {
      setSelectedModels(new Set(models.map(m => m.filename)));
      setSelectAll(true);
    }
  };

  const deleteSelectedModels = async () => {
    if (selectedModels.size === 0) {
      alert('삭제할 모델을 선택해주세요.');
      return;
    }

    if (!window.confirm(`${selectedModels.size}개의 모델을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.`)) return;

    let successCount = 0;
    let failCount = 0;

    for (const filename of selectedModels) {
      try {
        const res = await fetch(`/api/ai/models/${filename}`, {
          method: 'DELETE'
        });
        if (res.ok) {
          successCount++;
        } else {
          failCount++;
        }
      } catch (e) {
        console.error(e);
        failCount++;
      }
    }

    // Show notification
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 1.5rem;
      background: ${successCount > 0 ? 'linear-gradient(135deg, #00b07c, #00d98e)' : 'linear-gradient(135deg, #ff4b4b, #ff6b6b)'};
      color: ${successCount > 0 ? '#000' : '#fff'};
      border-radius: 8px;
      font-weight: 900;
      font-size: 0.9rem;
      box-shadow: 0 8px 24px rgba(0, 176, 124, 0.4);
      z-index: 10000;
      animation: slideIn 0.3s ease-out;
    `;
    notification.innerHTML = `
      <div style="display: flex; align-items: center; gap: 12px;">
        <div style="font-size: 2rem;">${successCount > 0 ? '🗑️' : '❌'}</div>
        <div>
          <div style="font-size: 1.1rem; margin-bottom: 4px;">
            ${successCount > 0 ? `${successCount}개 모델 삭제 완료!` : '삭제 실패'}
          </div>
          ${failCount > 0 ? `<div style="font-size: 0.8rem; opacity: 0.8;">${failCount}개 실패</div>` : ''}
        </div>
      </div>
    `;
    document.body.appendChild(notification);

    setTimeout(() => {
      notification.style.animation = 'slideOut 0.3s ease-out';
      setTimeout(() => notification.remove(), 300);
    }, 3000);

    // Clear selection and refresh
    setSelectedModels(new Set());
    setSelectAll(false);
    fetchModels();
  };

  const deleteModel = async (modelFilename) => {
    if (!window.confirm(`${modelFilename} 모델을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.`)) return;

    try {
      const res = await fetch(`/api/ai/models/${modelFilename}`, {
        method: 'DELETE'
      });

      if (res.ok) {
        // Success notification
        const notification = document.createElement('div');
        notification.style.cssText = `
          position: fixed;
          top: 20px;
          right: 20px;
          padding: 1.5rem;
          background: linear-gradient(135deg, #00b07c, #00d98e);
          color: #000;
          border-radius: 8px;
          font-weight: 900;
          font-size: 0.9rem;
          box-shadow: 0 8px 24px rgba(0, 176, 124, 0.4);
          z-index: 10000;
          animation: slideIn 0.3s ease-out;
        `;
        notification.innerHTML = `
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="font-size: 2rem;">🗑️</div>
            <div>
              <div style="font-size: 1.1rem; margin-bottom: 4px;">모델 삭제 완료!</div>
              <div style="font-size: 0.8rem; opacity: 0.8;">${modelFilename}</div>
            </div>
          </div>
        `;
        document.body.appendChild(notification);

        setTimeout(() => {
          notification.style.animation = 'slideOut 0.3s ease-out';
          setTimeout(() => notification.remove(), 300);
        }, 3000);

        // Refresh model list
        fetchModels();
      } else {
        // Error notification
        const notification = document.createElement('div');
        notification.style.cssText = `
          position: fixed;
          top: 20px;
          right: 20px;
          padding: 1.5rem;
          background: linear-gradient(135deg, #ff4b4b, #ff6b6b);
          color: #fff;
          border-radius: 8px;
          font-weight: 900;
          font-size: 0.9rem;
          box-shadow: 0 8px 24px rgba(255, 75, 75, 0.4);
          z-index: 10000;
          animation: slideIn 0.3s ease-out;
        `;
        notification.innerHTML = `
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="font-size: 2rem;">❌</div>
            <div>
              <div style="font-size: 1.1rem; margin-bottom: 4px;">삭제 실패</div>
              <div style="font-size: 0.8rem; opacity: 0.8;">모델을 삭제할 수 없습니다</div>
            </div>
          </div>
        `;
        document.body.appendChild(notification);

        setTimeout(() => {
          notification.style.animation = 'slideOut 0.3s ease-out';
          setTimeout(() => notification.remove(), 300);
        }, 3000);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadModel = async (modelFilename) => {
    if (!window.confirm(`${modelFilename} 모델을 로드하시겠습니까?`)) return;

    setLoadingModel(modelFilename);
    try {
      const res = await fetch('/api/ai/load-model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name: modelFilename })
      });

      if (res.ok) {
        const data = await res.json();

        // Success notification with details
        const notification = document.createElement('div');
        notification.style.cssText = `
          position: fixed;
          top: 20px;
          right: 20px;
          padding: 1.5rem;
          background: linear-gradient(135deg, #00b07c, #00d98e);
          color: #000;
          border-radius: 8px;
          font-weight: 900;
          font-size: 0.9rem;
          box-shadow: 0 8px 24px rgba(0, 176, 124, 0.4);
          z-index: 10000;
          animation: slideIn 0.3s ease-out;
        `;
        notification.innerHTML = `
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="font-size: 2rem;">✅</div>
            <div>
              <div style="font-size: 1.1rem; margin-bottom: 4px;">모델 로드 성공!</div>
              <div style="font-size: 0.8rem; opacity: 0.8;">${modelFilename}</div>
            </div>
          </div>
        `;
        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
          notification.style.animation = 'slideOut 0.3s ease-out';
          setTimeout(() => notification.remove(), 300);
        }, 3000);

        // Refresh performance data
        fetchPerformance();
      } else {
        // Error notification
        const notification = document.createElement('div');
        notification.style.cssText = `
          position: fixed;
          top: 20px;
          right: 20px;
          padding: 1.5rem;
          background: linear-gradient(135deg, #ff4b4b, #ff6b6b);
          color: #fff;
          border-radius: 8px;
          font-weight: 900;
          font-size: 0.9rem;
          box-shadow: 0 8px 24px rgba(255, 75, 75, 0.4);
          z-index: 10000;
          animation: slideIn 0.3s ease-out;
        `;
        notification.innerHTML = `
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="font-size: 2rem;">❌</div>
            <div>
              <div style="font-size: 1.1rem; margin-bottom: 4px;">로드 실패</div>
              <div style="font-size: 0.8rem; opacity: 0.8;">모델을 로드할 수 없습니다</div>
            </div>
          </div>
        `;
        document.body.appendChild(notification);

        setTimeout(() => {
          notification.style.animation = 'slideOut 0.3s ease-out';
          setTimeout(() => notification.remove(), 300);
        }, 3000);
      }
    } catch (e) {
      console.error(e);

      // Network error notification
      const notification = document.createElement('div');
      notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1.5rem;
        background: linear-gradient(135deg, #ff4b4b, #ff6b6b);
        color: #fff;
        border-radius: 8px;
        font-weight: 900;
        font-size: 0.9rem;
        box-shadow: 0 8px 24px rgba(255, 75, 75, 0.4);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
      `;
      notification.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px;">
          <div style="font-size: 2rem;">⚠️</div>
          <div>
            <div style="font-size: 1.1rem; margin-bottom: 4px;">네트워크 오류</div>
            <div style="font-size: 0.8rem; opacity: 0.8;">서버에 연결할 수 없습니다</div>
          </div>
        </div>
      `;
      document.body.appendChild(notification);

      setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
      }, 3000);
    } finally {
      setLoadingModel(null);
    }
  };

  // Daily Review Functions
  const fetchReports = async () => {
    try {
      const res = await fetch('/api/ai/daily-review');
      if (res.ok) {
        const data = await res.json();
        console.log('Daily Review Data:', data); // Debug log

        // Handle different response structures
        if (Array.isArray(data)) {
          setReports(data);
        } else if (data && typeof data === 'object') {
          // If it's a single report object, wrap it in an array
          setReports([data]);
        } else {
          console.warn('Unexpected data structure:', data);
          setReports([]);
        }
      } else {
        console.warn('Failed to fetch reports:', res.status);
        setReports([]);
      }
    } catch (e) {
      console.error('Error fetching reports:', e);
      setReports([]);
    }
  };

  const triggerManualReport = async () => {
    if (!window.confirm('일일 복기를 지금 실행하시겠습니까?')) return;

    setRefreshing(true);
    try {
      const res = await fetch('/api/ai/trigger-daily-review', { method: 'POST' });
      if (res.ok) {
        alert('복기가 완료되었습니다!');
        fetchReports();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setRefreshing(false);
    }
  };

  // Learning Progress Functions
  const fetchLearningProgress = async () => {
    try {
      const res = await fetch('/api/ai/improvement-suggestions');
      if (res.ok) {
        const data = await res.json();
        // If the API returns { suggestions: { category: [...] } }, use suggestions
        setLearningProgress(data.suggestions || data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchWeeklySummary = async () => {
    try {
      const res = await fetch('/api/ai/weekly-summary');
      if (res.ok) {
        const data = await res.json();
        setWeeklySummary(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Helper function for notifications
  const showNotification = (type, message) => {
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 1rem 1.5rem;
      background: ${type === 'success' ? '#00b07c' : '#ff5b5b'};
      color: white;
      border-radius: 4px;
      font-size: 0.9rem;
      font-weight: 700;
      z-index: 10000;
      animation: slideIn 0.3s ease-out;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    notification.innerHTML = `
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span>${type === 'success' ? '✅' : '❌'}</span>
        <span>${message}</span>
      </div>
    `;
    document.body.appendChild(notification);

    setTimeout(() => {
      notification.style.animation = 'slideOut 0.3s ease-out';
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  };

  // Coin Selection Functions
  const fetchCoinSelection = async () => {
    try {
      const res = await fetch('/api/coins/selection');
      if (res.ok) {
        const data = await res.json();
        setCoinSelection(data);
      }
    } catch (e) {
      console.error('Failed to fetch coin selection:', e);
    }
  };

  const fetchCoinCandidates = async () => {
    try {
      const res = await fetch('/api/coins/candidates');
      if (res.ok) {
        const data = await res.json();
        setCoinCandidates(data.candidates || []);
      }
    } catch (e) {
      console.error('Failed to fetch candidates:', e);
    }
  };

  const fetchCoinStats = async () => {
    try {
      const res = await fetch('/api/coins/stats');
      if (res.ok) {
        const data = await res.json();
        setCoinStats(data.stats);
      }
    } catch (e) {
      console.error('Failed to fetch stats:', e);
    }
  };

  const handleRebalance = async () => {
    setRebalancing(true);
    try {
      const res = await fetch('/api/coins/rebalance', { method: 'POST' });
      if (res.ok) {
        await fetchCoinSelection();
        await fetchCoinStats();
        await fetchAvailableSymbols(); // 학습 가능한 코인 목록 업데이트
        showNotification('success', 'Coin selection rebalanced successfully!');
      }
    } catch (e) {
      console.error('Failed to rebalance:', e);
      showNotification('error', 'Failed to rebalance coins');
    } finally {
      setRebalancing(false);
    }
  };

  const updateCoinConfig = async (newConfig) => {
    try {
      const res = await fetch('/api/coins/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig)
      });
      if (res.ok) {
        await fetchCoinSelection();
        await fetchCoinStats();
        await fetchAvailableSymbols(); // 학습 가능한 코인 목록 업데이트
        showNotification('success', 'Configuration updated successfully!');
      }
    } catch (e) {
      console.error('Failed to update config:', e);
      showNotification('error', 'Failed to update configuration');
    }
  };

  // Load coin selection data when tab is active
  useEffect(() => {
    if (activeTab === 'coins') {
      fetchCoinSelection();
      fetchCoinCandidates();
      fetchCoinStats();
    }
    if (activeTab === 'control') {
      fetchAvailableSymbols(); // control 탭에서 최신 심볼 목록 가져오기
    }
  }, [activeTab]);

  return (
    <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Add animation styles */}
      <style>{`
        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        @keyframes slideOut {
          from {
            transform: translateX(0);
            opacity: 1;
          }
          to {
            transform: translateX(100%);
            opacity: 0;
          }
        }
      `}</style>

      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: '900', color: '#fff', marginBottom: '0.5rem' }}>
          AI Hub
        </h1>
        <p style={{ color: '#666', fontSize: '0.85rem' }}>
          AI 제어, 학습 현황, 복기 보고서를 한 곳에서 관리
        </p>
      </div>

      {/* Tab Navigation */}
      <div style={{
        display: 'flex',
        gap: '2rem',
        borderBottom: '1px solid #222',
        marginBottom: '2rem'
      }}>
        {[
          { id: 'control', label: 'AI 제어', icon: '🤖' },
          { id: 'coins', label: '코인 선택', icon: '🪙' },
          { id: 'review', label: '일일 리뷰', icon: '📊' },
          { id: 'learning', label: '학습 진행', icon: '📈' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              background: 'transparent',
              border: 'none',
              padding: '1rem 0',
              fontSize: '0.85rem',
              fontWeight: '800',
              color: activeTab === tab.id ? '#fff' : '#666',
              cursor: 'pointer',
              borderBottom: activeTab === tab.id ? '2px solid #fff' : '2px solid transparent',
              transition: 'all 0.2s',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}
          >
            <span style={{ marginRight: '0.5rem' }}>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div>
        {/* AI Control Tab */}
        {activeTab === 'control' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Performance Overview */}
            <div style={{
              background: '#0a0a0a',
              border: '1px solid #222',
              borderRadius: '4px',
              padding: '1.5rem'
            }}>
              <h3 style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '1rem', color: '#fff' }}>
                Current Performance
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                {[
                  { label: 'Win Rate', value: `${(performance.winRate || 0).toFixed(1)}%`, color: performance.winRate > 60 ? '#00b07c' : '#ff5b5b' },
                  { label: 'Total Trades', value: performance.totalTrades || 0, color: '#fff' },
                  { label: 'Avg PnL', value: `$${(performance.avgPnL || 0).toFixed(2)}`, color: performance.avgPnL > 0 ? '#00b07c' : '#ff5b5b' },
                  { label: 'Sharpe Ratio', value: (performance.sharpeRatio || 0).toFixed(2), color: '#fff' }
                ].map(metric => (
                  <div key={metric.label} style={{ padding: '1rem', background: '#000', borderRadius: '2px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.5rem', textTransform: 'uppercase', fontWeight: '700' }}>
                      {metric.label}
                    </div>
                    <div style={{ fontSize: '1.5rem', fontWeight: '900', color: metric.color, fontFamily: 'monospace' }}>
                      {metric.value}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Training Configuration */}
            <div style={{
              background: '#0a0a0a',
              border: '1px solid #222',
              borderRadius: '4px',
              padding: '1.5rem'
            }}>
              <h3 style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '1.5rem', color: '#fff' }}>
                🎯 Training Configuration
              </h3>

              {/* Grid Layout for Settings */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1.5rem', marginBottom: '1.5rem' }}>
                {/* Symbol */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#888', marginBottom: '0.5rem' }}>
                    SYMBOL (학습할 코인)
                  </label>
                  <select
                    value={config.symbol}
                    onChange={(e) => setConfig({ ...config, symbol: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      background: '#111',
                      border: '1px solid #222',
                      borderRadius: '3px',
                      color: '#fff',
                      fontSize: '0.85rem',
                      outline: 'none',
                      cursor: 'pointer'
                    }}
                  >
                    {availableSymbols.length > 0 ? (
                      availableSymbols.map((symbol) => (
                        <option key={symbol} value={symbol}>
                          {symbol}
                        </option>
                      ))
                    ) : (
                      <>
                        <option value="BTCUSDT">BTCUSDT</option>
                        <option value="ETHUSDT">ETHUSDT</option>
                        <option value="SOLUSDT">SOLUSDT</option>
                        <option value="BNBUSDT">BNBUSDT</option>
                      </>
                    )}
                  </select>
                  <span style={{ fontSize: '0.65rem', color: '#666', marginTop: '0.25rem', display: 'block' }}>
                    💡 코인 선택 탭에서 모드 변경 가능 (BTC Only / Hybrid)
                  </span>
                </div>

                {/* Timeframe */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#888', marginBottom: '0.5rem' }}>
                    TIMEFRAME (분봉/시간봉)
                  </label>
                  <select
                    value={config.interval}
                    onChange={(e) => setConfig({ ...config, interval: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      background: '#111',
                      border: '1px solid #222',
                      borderRadius: '3px',
                      color: '#fff',
                      fontSize: '0.85rem',
                      outline: 'none',
                      cursor: 'pointer'
                    }}
                  >
                    <option value="1m">1분봉</option>
                    <option value="3m">3분봉</option>
                    <option value="5m">5분봉</option>
                    <option value="15m">15분봉</option>
                    <option value="30m">30분봉</option>
                    <option value="1h">1시간봉</option>
                    <option value="2h">2시간봉</option>
                    <option value="4h">4시간봉</option>
                    <option value="6h">6시간봉</option>
                    <option value="12h">12시간봉</option>
                    <option value="1d">1일봉</option>
                  </select>
                </div>

                {/* Training Period */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#888', marginBottom: '0.5rem' }}>
                    학습 기간 (일)
                  </label>
                  <input
                    type="number"
                    value={config.days}
                    onChange={(e) => setConfig({ ...config, days: parseInt(e.target.value) })}
                    min="7"
                    max="365"
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      background: '#111',
                      border: '1px solid #222',
                      borderRadius: '3px',
                      color: '#fff',
                      fontSize: '0.85rem',
                      outline: 'none'
                    }}
                  />
                  <span style={{ fontSize: '0.65rem', color: '#444', marginTop: '0.25rem', display: 'block' }}>
                    권장: 30-90일 (더 많은 데이터 = 더 나은 학습)
                  </span>
                </div>

                {/* Episodes */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#888', marginBottom: '0.5rem' }}>
                    EPISODES (반복 횟수)
                  </label>
                  <input
                    type="number"
                    value={config.episodes}
                    onChange={(e) => setConfig({ ...config, episodes: parseInt(e.target.value) })}
                    min="100"
                    max="10000"
                    step="100"
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      background: '#111',
                      border: '1px solid #222',
                      borderRadius: '3px',
                      color: '#fff',
                      fontSize: '0.85rem',
                      outline: 'none'
                    }}
                  />
                  <span style={{ fontSize: '0.65rem', color: '#444', marginTop: '0.25rem', display: 'block' }}>
                    권장: 1000-3000 (더 많은 반복 = 더 나은 학습)
                  </span>
                </div>

                {/* Leverage */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#888', marginBottom: '0.5rem' }}>
                    LEVERAGE (레버리지)
                  </label>
                  <input
                    type="number"
                    value={config.leverage}
                    onChange={(e) => setConfig({ ...config, leverage: parseInt(e.target.value) })}
                    min="1"
                    max="125"
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      background: '#111',
                      border: '1px solid #222',
                      borderRadius: '3px',
                      color: '#fff',
                      fontSize: '0.85rem',
                      outline: 'none'
                    }}
                  />
                </div>

                {/* Reward Strategy */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#888', marginBottom: '0.5rem' }}>
                    REWARD STRATEGY
                  </label>
                  <select
                    value={config.reward_strategy}
                    onChange={(e) => setConfig({ ...config, reward_strategy: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      background: '#111',
                      border: '1px solid #222',
                      borderRadius: '3px',
                      color: '#fff',
                      fontSize: '0.85rem',
                      outline: 'none',
                      cursor: 'pointer'
                    }}
                  >
                    <option value="improved">Improved (추천)</option>
                    <option value="pnl">PnL Only</option>
                    <option value="sharpe">Sharpe Ratio</option>
                  </select>
                </div>
              </div>

              {/* Summary Box */}
              <div style={{
                padding: '1rem',
                background: 'linear-gradient(135deg, rgba(0, 176, 124, 0.05), transparent)',
                border: '1px solid rgba(0, 176, 124, 0.2)',
                borderRadius: '4px',
                marginBottom: '1.5rem'
              }}>
                <div style={{ fontSize: '0.7rem', color: '#00b07c', fontWeight: '800', marginBottom: '0.5rem' }}>
                  📊 학습 요약
                </div>
                <div style={{ fontSize: '0.8rem', color: '#ccc', lineHeight: '1.8' }}>
                  <strong style={{ color: '#fff' }}>{config.symbol}</strong>의{' '}
                  <strong style={{ color: '#00b07c' }}>{config.interval}</strong> 데이터를{' '}
                  <strong style={{ color: '#00b07c' }}>{config.days}일</strong> 동안 수집하여{' '}
                  <strong style={{ color: '#00b07c' }}>{config.episodes}회</strong> 반복 학습합니다.
                  <br />
                  레버리지 <strong style={{ color: '#00b07c' }}>{config.leverage}x</strong>,{' '}
                  보상 전략: <strong style={{ color: '#00b07c' }}>{config.reward_strategy}</strong>
                  <br />
                  <span style={{ color: '#f0b90b', fontSize: '0.75rem' }}>
                    💾 저장: ppo_{config.symbol}_{config.interval}_YYYYMMDD_HHMM.zip
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button
                  onClick={startTraining}
                  disabled={training}
                  style={{
                    flex: 1,
                    padding: '1rem',
                    background: training ? '#222' : 'linear-gradient(135deg, #00b07c, #00d98e)',
                    color: training ? '#666' : '#000',
                    border: 'none',
                    borderRadius: '4px',
                    fontWeight: '900',
                    fontSize: '0.9rem',
                    cursor: training ? 'not-allowed' : 'pointer',
                    textTransform: 'uppercase',
                    boxShadow: training ? 'none' : '0 4px 12px rgba(0, 176, 124, 0.3)',
                    transition: 'all 0.2s'
                  }}
                >
                  {training ? '🔄 Training in Progress...' : '🚀 START AI TRAINING'}
                </button>
                <button
                  onClick={fetchModels}
                  style={{
                    padding: '1rem 1.5rem',
                    background: 'transparent',
                    color: '#fff',
                    border: '1px solid #222',
                    borderRadius: '4px',
                    fontWeight: '900',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    textTransform: 'uppercase',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = '#111'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  🔄 Refresh
                </button>
              </div>
            </div>

            {/* Saved Models */}
            <div style={{
              background: '#0a0a0a',
              border: '1px solid #222',
              borderRadius: '4px',
              padding: '1.5rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: '800', color: '#fff', margin: 0 }}>
                  💾 Saved Models
                </h3>
                {selectedModels.size > 0 && (
                  <button
                    onClick={deleteSelectedModels}
                    style={{
                      padding: '0.5rem 1rem',
                      background: 'linear-gradient(135deg, #ff4b4b, #ff6b6b)',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      fontWeight: '900',
                      cursor: 'pointer',
                      textTransform: 'uppercase',
                      boxShadow: '0 2px 8px rgba(255, 75, 75, 0.4)'
                    }}
                  >
                    🗑️ Delete Selected ({selectedModels.size})
                  </button>
                )}
              </div>

              {/* Model List */}
              <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                {models.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
                    No models available
                  </div>
                ) : (
                  <>
                    {/* Select All Header */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '0.5rem 0.75rem',
                      background: '#151515',
                      borderBottom: '1px solid #222',
                      marginBottom: '0.5rem'
                    }}>
                      <input
                        type="checkbox"
                        checked={selectAll}
                        onChange={toggleSelectAll}
                        style={{
                          width: '16px',
                          height: '16px',
                          cursor: 'pointer',
                          accentColor: '#00b07c'
                        }}
                      />
                      <span style={{ marginLeft: '0.75rem', fontSize: '0.7rem', color: '#888', fontWeight: '700' }}>
                        SELECT ALL
                      </span>
                    </div>

                    {/* Model Items */}
                    {models.map(model => {
                      const isActive = model.filename === performance.currentModel;
                      const isSelected = selectedModels.has(model.filename);

                      return (
                        <div
                          key={model.filename}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '0.75rem',
                            background: isActive ? '#151515' : isSelected ? 'rgba(0, 176, 124, 0.05)' : 'transparent',
                            borderBottom: '1px solid #0a0a0a',
                            fontSize: '0.8rem',
                            transition: 'all 0.2s'
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', flex: 1, gap: '0.75rem' }}>
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleModelSelection(model.filename)}
                              disabled={isActive}
                              style={{
                                width: '16px',
                                height: '16px',
                                cursor: isActive ? 'not-allowed' : 'pointer',
                                accentColor: '#00b07c'
                              }}
                            />
                            <div style={{ flex: 1 }}>
                              <div style={{ color: '#fff', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                {model.filename}
                                {isActive && (
                                  <span style={{
                                    fontSize: '0.6rem',
                                    background: '#00b07c',
                                    color: '#000',
                                    padding: '2px 6px',
                                    borderRadius: '3px',
                                    fontWeight: '900'
                                  }}>
                                    ACTIVE
                                  </span>
                                )}
                              </div>
                              <div style={{ color: '#666', fontSize: '0.7rem' }}>
                                {new Date(model.modified * 1000).toLocaleString('ko-KR')}
                              </div>
                            </div>
                          </div>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                              onClick={() => loadModel(model.filename)}
                              disabled={loadingModel === model.filename || isActive}
                              style={{
                                padding: '0.25rem 0.75rem',
                                background: isActive ? '#00b07c' : 'transparent',
                                color: isActive ? '#000' : '#fff',
                                border: isActive ? 'none' : '1px solid #222',
                                borderRadius: '2px',
                                fontSize: '0.7rem',
                                fontWeight: '900',
                                cursor: isActive ? 'default' : 'pointer',
                                textTransform: 'uppercase'
                              }}
                            >
                              {isActive ? 'Active' : loadingModel === model.filename ? 'Loading...' : 'Load'}
                            </button>
                            <button
                              onClick={() => deleteModel(model.filename)}
                              disabled={isActive}
                              style={{
                                padding: '0.25rem 0.75rem',
                                background: 'transparent',
                                color: isActive ? '#444' : '#ff4b4b',
                                border: `1px solid ${isActive ? '#222' : '#ff4b4b'}`,
                                borderRadius: '2px',
                                fontSize: '0.7rem',
                                fontWeight: '900',
                                cursor: isActive ? 'not-allowed' : 'pointer',
                                textTransform: 'uppercase',
                                transition: 'all 0.2s'
                              }}
                              onMouseEnter={(e) => {
                                if (!isActive) {
                                  e.currentTarget.style.background = 'rgba(255, 75, 75, 0.1)';
                                }
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'transparent';
                              }}
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Daily Review Tab */}
        {activeTab === 'review' && (
          <div>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '2rem'
            }}>
              <h3 style={{ fontSize: '1.2rem', fontWeight: '800', color: '#fff' }}>
                AI Daily Review
              </h3>
              <button
                onClick={triggerManualReport}
                disabled={refreshing}
                style={{
                  padding: '0.6rem 1.5rem',
                  background: 'transparent',
                  color: refreshing ? '#444' : '#fff',
                  border: '1px solid #222',
                  borderRadius: '2px',
                  cursor: 'pointer',
                  fontSize: '0.7rem',
                  fontWeight: '900',
                  textTransform: 'uppercase'
                }}
              >
                {refreshing ? 'Processing...' : 'Generate Report'}
              </button>
            </div>

            {reports.length === 0 ? (
              <div style={{
                background: '#0a0a0a',
                border: '1px solid #222',
                borderRadius: '4px',
                padding: '4rem 2rem',
                textAlign: 'center'
              }}>
                <p style={{ color: '#666', fontSize: '1rem' }}>No review reports yet</p>
                <p style={{ color: '#333', fontSize: '0.8rem', marginTop: '0.5rem' }}>
                  Reports are automatically generated daily at midnight
                </p>
              </div>
            ) : (
              reports.map((report, idx) => (
                <div
                  key={idx}
                  style={{
                    background: '#0a0a0a',
                    border: '1px solid #222',
                    borderRadius: '4px',
                    padding: '2rem',
                    marginBottom: '1rem'
                  }}
                >
                  <h4 style={{ color: '#fff', fontWeight: '800', marginBottom: '1rem' }}>
                    {report.date}
                  </h4>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.25rem' }}>Total Trades</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: '800', color: '#fff' }}>{report.total_trades}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.25rem' }}>Win Rate</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: '800', color: '#00b07c' }}>{((report.win_rate || 0) * 100).toFixed(1)}%</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.25rem' }}>Total PnL</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: '800', color: (report.total_pnl || 0) > 0 ? '#00b07c' : '#ff5b5b' }}>
                        ${(report.total_pnl || 0).toFixed(2)}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.25rem' }}>Avg Win/Loss</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: '800', color: '#fff' }}>
                        {(report.avg_win || 0).toFixed(2)} / {(report.avg_loss || 0).toFixed(2)}
                      </div>
                    </div>
                  </div>

                  {report.patterns && report.patterns.length > 0 && (
                    <div style={{ marginBottom: '1.5rem' }}>
                      <div style={{ fontSize: '0.8rem', fontWeight: '800', color: '#00b07c', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                        ✅ Patterns Identified
                      </div>
                      {report.patterns.map((p, i) => (
                        <div key={i} style={{ fontSize: '0.8rem', color: '#bbb', marginBottom: '0.25rem' }}>• {p}</div>
                      ))}
                    </div>
                  )}

                  {report.mistakes && report.mistakes.length > 0 && (
                    <div style={{ marginBottom: '1.5rem' }}>
                      <div style={{ fontSize: '0.8rem', fontWeight: '800', color: '#ff5b5b', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                        ❌ Mistakes
                      </div>
                      {report.mistakes.map((m, i) => (
                        <div key={i} style={{ fontSize: '0.8rem', color: '#bbb', marginBottom: '0.25rem' }}>• {m}</div>
                      ))}
                    </div>
                  )}

                  {report.recommendations && report.recommendations.length > 0 && (
                    <div>
                      <div style={{ fontSize: '0.8rem', fontWeight: '800', color: '#fff', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                        💡 Recommendations
                      </div>
                      {report.recommendations.map((r, i) => (
                        <div key={i} style={{ fontSize: '0.8rem', color: '#bbb', marginBottom: '0.25rem' }}>• {r}</div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* Learning Progress Tab */}
        {activeTab === 'learning' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Weekly Summary */}
            {weeklySummary && (
              <div style={{
                background: '#0a0a0a',
                border: '1px solid #222',
                borderRadius: '4px',
                padding: '1.5rem'
              }}>
                <h3 style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '1rem', color: '#fff' }}>
                  Weekly Summary
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
                  <div style={{ padding: '1rem', background: '#000', borderRadius: '2px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.5rem' }}>Total Trades</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: '900', color: '#fff' }}>{weeklySummary.total_trades || 0}</div>
                  </div>
                  <div style={{ padding: '1rem', background: '#000', borderRadius: '2px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.5rem' }}>Total PnL</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: '900', color: weeklySummary.total_pnl > 0 ? '#00b07c' : '#ff5b5b' }}>
                      ${(weeklySummary.total_pnl || 0).toFixed(2)}
                    </div>
                  </div>
                  <div style={{ padding: '1rem', background: '#000', borderRadius: '2px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.5rem' }}>Avg Win Rate</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: '900', color: '#00b07c' }}>
                      {((weeklySummary.avg_win_rate || 0) * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Improvement Suggestions */}
            {learningProgress && (
              <div style={{
                background: '#0a0a0a',
                border: '1px solid #222',
                borderRadius: '4px',
                padding: '1.5rem'
              }}>
                <h3 style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '1rem', color: '#fff' }}>
                  AI Improvement Suggestions
                </h3>

                {Object.entries(learningProgress).map(([category, suggestions]) => (
                  suggestions && suggestions.length > 0 && (
                    <div key={category} style={{ marginBottom: '1.5rem' }}>
                      <div style={{
                        fontSize: '0.8rem',
                        fontWeight: '800',
                        color: '#00b07c',
                        marginBottom: '0.5rem',
                        textTransform: 'uppercase'
                      }}>
                        {category.replace('_', ' ')}
                      </div>
                      {Array.isArray(suggestions) && suggestions.map((suggestion, idx) => (
                        <div key={idx} style={{ fontSize: '0.8rem', color: '#bbb', marginBottom: '0.25rem' }}>
                          • {suggestion}
                        </div>
                      ))}
                    </div>
                  )
                ))}
              </div>
            )}
          </div>
        )}

        {/* Coin Selection Tab */}
        {activeTab === 'coins' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Current Selection Stats */}
            {coinStats && (
              <div style={{
                background: '#0a0a0a',
                border: '1px solid #222',
                borderRadius: '4px',
                padding: '1.5rem'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: '800', color: '#fff' }}>
                    {coinSelection.config?.mode === 'BTC_ONLY' ? '₿ Bitcoin Only 모드' : '🪙 현재 선택된 코인 (하이브리드 모드)'}
                  </h3>
                  <button
                    onClick={handleRebalance}
                    disabled={rebalancing}
                    style={{
                      padding: '0.5rem 1rem',
                      background: rebalancing ? '#333' : '#00b07c',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '2px',
                      cursor: rebalancing ? 'not-allowed' : 'pointer',
                      fontSize: '0.8rem',
                      fontWeight: '800'
                    }}
                  >
                    {rebalancing ? '⏳ 재선별 중...' : '🔄 지금 재선별'}
                  </button>
                </div>

                {/* Stats Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                  <div style={{ padding: '1rem', background: '#000', borderRadius: '2px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.5rem' }}>총 코인 수</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: '900', color: '#00b07c' }}>{coinStats.total_coins}</div>
                  </div>
                  <div style={{ padding: '1rem', background: '#000', borderRadius: '2px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.5rem' }}>코어 코인</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: '900', color: '#fff' }}>{coinStats.core_coins}</div>
                  </div>
                  <div style={{ padding: '1rem', background: '#000', borderRadius: '2px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.5rem' }}>자동 선택</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: '900', color: '#ffd93d' }}>{coinStats.auto_coins}</div>
                  </div>
                  <div style={{ padding: '1rem', background: '#000', borderRadius: '2px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.5rem' }}>평균 점수</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: '900', color: '#00b07c' }}>{coinStats.avg_score}</div>
                  </div>
                </div>

                {/* Selected Coins List */}
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: '800', color: '#666', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                    활성 트레이딩 코인
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {coinStats.coins_list?.map(coin => {
                      const score = coinSelection.scores[coin] || 0;
                      const isCore = coinSelection.config?.core_coins?.some(c => coin.startsWith(c));
                      return (
                        <div
                          key={coin}
                          style={{
                            padding: '0.5rem 1rem',
                            background: isCore ? '#1a1a2e' : '#000',
                            border: isCore ? '1px solid #00b07c' : '1px solid #333',
                            borderRadius: '2px',
                            fontSize: '0.8rem',
                            fontWeight: '800',
                            color: '#fff',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                          }}
                        >
                          {isCore && <span style={{ color: '#00b07c' }}>⭐</span>}
                          <span>{coin.replace('USDT', '')}</span>
                          <span style={{ fontSize: '0.7rem', color: '#666' }}>({score.toFixed(1)})</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Last Rebalance Info */}
                {coinSelection.last_rebalance && (
                  <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '1rem' }}>
                    마지막 재선별: {new Date(coinSelection.last_rebalance).toLocaleString('ko-KR')}
                  </div>
                )}
              </div>
            )}

            {/* 🆕 Trading Mode Selection */}
            <div style={{
              background: '#0a0a0a',
              border: '1px solid #222',
              borderRadius: '4px',
              padding: '1.5rem',
              marginBottom: '1rem'
            }}>
              <h3 style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '1rem', color: '#fff' }}>
                🎯 트레이딩 모드 선택
              </h3>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                {/* BTC Only Mode */}
                <button
                  onClick={() => updateCoinConfig({ mode: 'BTC_ONLY' })}
                  style={{
                    padding: '1.5rem',
                    background: coinSelection.config?.mode === 'BTC_ONLY'
                      ? 'linear-gradient(135deg, #f0b90b, #f8d12f)'
                      : '#111',
                    border: coinSelection.config?.mode === 'BTC_ONLY'
                      ? '2px solid #f0b90b'
                      : '1px solid #333',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    transition: 'all 0.3s',
                    textAlign: 'left'
                  }}
                  onMouseEnter={(e) => {
                    if (coinSelection.config?.mode !== 'BTC_ONLY') {
                      e.currentTarget.style.borderColor = '#f0b90b';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (coinSelection.config?.mode !== 'BTC_ONLY') {
                      e.currentTarget.style.borderColor = '#333';
                    }
                  }}
                >
                  <div style={{
                    fontSize: '2rem',
                    marginBottom: '0.5rem',
                    color: coinSelection.config?.mode === 'BTC_ONLY' ? '#000' : '#f0b90b'
                  }}>
                    ₿
                  </div>
                  <div style={{
                    fontSize: '1rem',
                    fontWeight: '900',
                    marginBottom: '0.5rem',
                    color: coinSelection.config?.mode === 'BTC_ONLY' ? '#000' : '#fff'
                  }}>
                    BTC ONLY
                  </div>
                  <div style={{
                    fontSize: '0.75rem',
                    color: coinSelection.config?.mode === 'BTC_ONLY' ? 'rgba(0,0,0,0.7)' : '#888',
                    lineHeight: '1.6'
                  }}>
                    비트코인에만 올인<br />
                    단일 코인 집중 전략<br />
                    높은 유동성 & 안정성
                  </div>
                  {coinSelection.config?.mode === 'BTC_ONLY' && (
                    <div style={{
                      marginTop: '0.75rem',
                      padding: '0.5rem',
                      background: 'rgba(0,0,0,0.2)',
                      borderRadius: '3px',
                      fontSize: '0.7rem',
                      fontWeight: '800',
                      color: '#000'
                    }}>
                      ✅ 현재 활성화
                    </div>
                  )}
                </button>

                {/* Hybrid Mode */}
                <button
                  onClick={() => updateCoinConfig({ mode: 'HYBRID' })}
                  style={{
                    padding: '1.5rem',
                    background: coinSelection.config?.mode === 'HYBRID' || !coinSelection.config?.mode
                      ? 'linear-gradient(135deg, #00b07c, #00d98e)'
                      : '#111',
                    border: coinSelection.config?.mode === 'HYBRID' || !coinSelection.config?.mode
                      ? '2px solid #00b07c'
                      : '1px solid #333',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    transition: 'all 0.3s',
                    textAlign: 'left'
                  }}
                  onMouseEnter={(e) => {
                    if (coinSelection.config?.mode !== 'HYBRID' && coinSelection.config?.mode) {
                      e.currentTarget.style.borderColor = '#00b07c';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (coinSelection.config?.mode !== 'HYBRID' && coinSelection.config?.mode) {
                      e.currentTarget.style.borderColor = '#333';
                    }
                  }}
                >
                  <div style={{
                    fontSize: '2rem',
                    marginBottom: '0.5rem',
                    color: coinSelection.config?.mode === 'HYBRID' || !coinSelection.config?.mode ? '#000' : '#00b07c'
                  }}>
                    🪙
                  </div>
                  <div style={{
                    fontSize: '1rem',
                    fontWeight: '900',
                    marginBottom: '0.5rem',
                    color: coinSelection.config?.mode === 'HYBRID' || !coinSelection.config?.mode ? '#000' : '#fff'
                  }}>
                    HYBRID
                  </div>
                  <div style={{
                    fontSize: '0.75rem',
                    color: coinSelection.config?.mode === 'HYBRID' || !coinSelection.config?.mode ? 'rgba(0,0,0,0.7)' : '#888',
                    lineHeight: '1.6'
                  }}>
                    코어 코인 + 알트코인<br />
                    AI 자동 선택 전략<br />
                    분산 투자 & 기회 포착
                  </div>
                  {(coinSelection.config?.mode === 'HYBRID' || !coinSelection.config?.mode) && (
                    <div style={{
                      marginTop: '0.75rem',
                      padding: '0.5rem',
                      background: 'rgba(0,0,0,0.2)',
                      borderRadius: '3px',
                      fontSize: '0.7rem',
                      fontWeight: '800',
                      color: '#000'
                    }}>
                      ✅ 현재 활성화
                    </div>
                  )}
                </button>
              </div>

              {/* Mode Description */}
              <div style={{
                marginTop: '1rem',
                padding: '1rem',
                background: coinSelection.config?.mode === 'BTC_ONLY'
                  ? 'rgba(240, 185, 11, 0.1)'
                  : 'rgba(0, 176, 124, 0.1)',
                border: `1px solid ${coinSelection.config?.mode === 'BTC_ONLY' ? 'rgba(240, 185, 11, 0.3)' : 'rgba(0, 176, 124, 0.3)'}`,
                borderRadius: '4px'
              }}>
                <div style={{
                  fontSize: '0.75rem',
                  fontWeight: '800',
                  color: coinSelection.config?.mode === 'BTC_ONLY' ? '#f0b90b' : '#00b07c',
                  marginBottom: '0.5rem'
                }}>
                  {coinSelection.config?.mode === 'BTC_ONLY' ? '₿ BTC Only 모드 활성화' : '🪙 하이브리드 모드 활성화'}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#bbb', lineHeight: '1.6' }}>
                  {coinSelection.config?.mode === 'BTC_ONLY'
                    ? 'BTCUSDT만 거래하며, 모든 자본을 비트코인에 집중합니다. 가장 높은 유동성과 안정성을 제공하며, 시장 대표 지표를 따릅니다.'
                    : '코어 코인(BTC, ETH, SOL, BNB)과 AI가 선택한 상위 알트코인을 함께 거래합니다. 안정성과 기회 포착을 동시에 추구합니다.'
                  }
                </div>
              </div>
            </div>

            {/* Configuration Panel (HYBRID Mode only) */}
            {(coinSelection.config?.mode === 'HYBRID' || !coinSelection.config?.mode) && (
              <div style={{
                background: '#0a0a0a',
                border: '1px solid #222',
                borderRadius: '4px',
                padding: '1.5rem'
              }}>
                <h3 style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '1rem', color: '#fff' }}>
                  ⚙️ 선택 설정 (하이브리드 모드)
                </h3>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                  {/* Core Coins */}
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '800', color: '#666', marginBottom: '0.5rem' }}>
                      코어 코인 (항상 포함)
                    </label>
                    <div style={{ fontSize: '0.8rem', color: '#fff' }}>
                      {coinSelection.config?.core_coins?.join(', ') || 'BTC, ETH, SOL, BNB'}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '0.25rem' }}>
                      코어 코인은 최대 10배, 나머지는 최대 5배 레버리지
                    </div>
                  </div>

                  {/* Max Altcoins */}
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '800', color: '#666', marginBottom: '0.5rem' }}>
                      최대 자동 알트코인
                    </label>
                    <div style={{ fontSize: '0.8rem', color: '#fff' }}>
                      {coinSelection.config?.max_altcoins || 3} coins
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '0.25rem' }}>
                      AI가 자동으로 상위 성과 코인 선택
                    </div>
                  </div>

                  {/* Rebalance Interval */}
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '800', color: '#666', marginBottom: '0.5rem' }}>
                      재선별 주기
                    </label>
                    <div style={{ fontSize: '0.8rem', color: '#fff' }}>
                      Every {coinSelection.config?.rebalance_interval_hours || 1} hour(s)
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '0.25rem' }}>
                      자동 선택 업데이트
                    </div>
                  </div>

                  {/* Max Total */}
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '800', color: '#666', marginBottom: '0.5rem' }}>
                      최대 총 코인 수
                    </label>
                    <div style={{ fontSize: '0.8rem', color: '#fff' }}>
                      {coinSelection.config?.max_total || 7} coins
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '0.25rem' }}>
                      최대 동시 거래 수
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Top Candidates (HYBRID Mode only) */}
            {coinCandidates.length > 0 && (
              <div style={{
                background: '#0a0a0a',
                border: '1px solid #222',
                borderRadius: '4px',
                padding: '1.5rem'
              }}>
                <h3 style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '1rem', color: '#fff' }}>
                  🏆 상위 코인 후보 (AI 점수 기준)
                </h3>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
                  {coinCandidates.slice(0, 9).map((candidate, idx) => (
                    <div
                      key={candidate.symbol}
                      style={{
                        padding: '1rem',
                        background: '#000',
                        border: '1px solid #222',
                        borderRadius: '2px'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                        <div style={{ fontSize: '0.9rem', fontWeight: '900', color: '#fff' }}>
                          #{idx + 1} {candidate.base_symbol}
                        </div>
                        <div style={{
                          fontSize: '0.8rem',
                          fontWeight: '800',
                          color: candidate.score > 80 ? '#00b07c' : candidate.score > 60 ? '#ffd93d' : '#666'
                        }}>
                          {candidate.score.toFixed(1)}
                        </div>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.7rem' }}>
                        <div>
                          <div style={{ color: '#666' }}>24h Change</div>
                          <div style={{
                            color: candidate.metrics.price_change_24h > 0 ? '#00b07c' : '#ff5b5b',
                            fontWeight: '800'
                          }}>
                            {candidate.metrics.price_change_24h.toFixed(2)}%
                          </div>
                        </div>
                        <div>
                          <div style={{ color: '#666' }}>Volume</div>
                          <div style={{ color: '#fff', fontWeight: '800' }}>
                            ${(candidate.metrics.volume_24h / 1_000_000).toFixed(0)}M
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '1rem' }}>
                  * 점수는 거래량, 변동성, 모멘텀, 유동성을 기반으로 계산됩니다
                </div>
              </div>
            )}

            {/* Selection Criteria Info (HYBRID Mode only) */}
            {(coinSelection.config?.mode === 'HYBRID' || !coinSelection.config?.mode) && (
              <div style={{
                background: '#0a0a0a',
                border: '1px solid #222',
                borderRadius: '4px',
                padding: '1.5rem'
              }}>
                <h3 style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '1rem', color: '#fff' }}>
                  🎯 자동 선택 기준
                </h3>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', fontSize: '0.8rem' }}>
                  <div>
                    <div style={{ fontWeight: '800', color: '#00b07c', marginBottom: '0.5rem' }}>✅ 최소 요구사항</div>
                    <ul style={{ margin: 0, paddingLeft: '1.5rem', color: '#bbb', lineHeight: '1.8' }}>
                      <li>시가총액: $1B 이상</li>
                      <li>24시간 거래량: $100M 이상</li>
                      <li>바이낸스 선물 거래 가능</li>
                      <li>가격 변동: -50% ~ +100%</li>
                    </ul>
                  </div>
                  <div>
                    <div style={{ fontWeight: '800', color: '#ffd93d', marginBottom: '0.5rem' }}>📊 점수 계산 요소</div>
                    <ul style={{ margin: 0, paddingLeft: '1.5rem', color: '#bbb', lineHeight: '1.8' }}>
                      <li>거래량 (30%): 높을수록 좋음</li>
                      <li>변동성 (30%): 적당한 변동성 선호</li>
                      <li>모멘텀 (20%): 긍정적 모멘텀 선호</li>
                      <li>유동성 (20%): 상위 100개 코인</li>
                    </ul>
                  </div>
                </div>

                <div style={{
                  marginTop: '1rem',
                  padding: '1rem',
                  background: 'rgba(0, 176, 124, 0.1)',
                  border: '1px solid rgba(0, 176, 124, 0.3)',
                  borderRadius: '2px',
                  fontSize: '0.75rem',
                  color: '#bbb',
                  lineHeight: '1.6'
                }}>
                  <div style={{ fontWeight: '800', color: '#00b07c', marginBottom: '0.5rem' }}>
                    💡 하이브리드 모드 작동 방식:
                  </div>
                  코어 코인(BTC, ETH, SOL, BNB)은 안정성을 제공하며 항상 거래됩니다(최대 10배 레버리지).
                  AI는 시장 상황에 따라 매시간 최상위 알트코인을 자동으로 선택하여(최대 5배 레버리지),
                  높은 거래량과 적당한 변동성을 가진 기회를 최적화합니다. 이러한 균형 잡힌 접근 방식은 리스크를 관리하면서 수익을 극대화합니다.
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default AIHub;
