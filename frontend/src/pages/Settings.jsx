import React, { useState, useEffect } from 'react';

function Settings() {
  const [activeTab, setActiveTab] = useState('risk'); // risk, notifications, api

  // Risk Management States
  const [riskStatus, setRiskStatus] = useState({
    daily_loss_limit: 50.0,
    max_margin_level: 0.8,
    kill_switch: false,
    position_mode: 'FIXED',
    position_ratio: 0.1,
    current_daily_loss: 0.0,
    daily_start_balance: 0.0,
    risk_status: 'NORMAL',
    current_margin_level: 0.0
  });

  const [strategyConfig, setStrategyConfig] = useState({
    mode: 'SCALP',
    selected_interval: '15m',
    available_intervals: ['15m', '30m'],
    leverage_mode: 'AUTO',
    manual_leverage: 5
  });

  // Notification States
  const [notifications, setNotifications] = useState({
    desktop: true,
    email: false,
    telegram: false
  });

  const [telegramSettings, setTelegramSettings] = useState({
    enabled: false,
    bot_token: '',
    chat_id: '',
    bot_token_configured: false
  });

  // API Config States
  const [apiConfig, setApiConfig] = useState({
    active_exchange: 'BINANCE',
    binance_key: '',
    binance_secret: '',
    testnet: false
  });

  const [saving, setSaving] = useState(false);

  // Coin Selection States
  const [selectedCoins, setSelectedCoins] = useState(['BTCUSDT', 'ETHUSDT']);
  const [maxCoins, setMaxCoins] = useState(5);

  const AVAILABLE_COINS = [
    { symbol: 'BTCUSDT', name: 'Bitcoin', emoji: '₿' },
    { symbol: 'ETHUSDT', name: 'Ethereum', emoji: 'Ξ' },
    { symbol: 'BNBUSDT', name: 'BNB', emoji: '⬡' },
    { symbol: 'SOLUSDT', name: 'Solana', emoji: '◎' },
    { symbol: 'XRPUSDT', name: 'Ripple', emoji: 'X' },
    { symbol: 'ADAUSDT', name: 'Cardano', emoji: '₳' },
    { symbol: 'DOGEUSDT', name: 'Dogecoin', emoji: 'Ð' },
    { symbol: 'DOTUSDT', name: 'Polkadot', emoji: '●' },
    { symbol: 'MATICUSDT', name: 'Polygon', emoji: '⬢' },
    { symbol: 'AVAXUSDT', name: 'Avalanche', emoji: '▲' },
  ];

  useEffect(() => {
    fetchRiskStatus();
    fetchStrategyConfig();
    fetchNotificationSettings();
    fetchTelegramSettings();
    fetchApiConfig();
    fetchSelectedCoins();
  }, []);

  const fetchRiskStatus = async () => {
    try {
      const res = await fetch('/api/trading/risk/status');
      if (res.ok) {
        const data = await res.json();
        if (data.status !== 'not_initialized') {
          setRiskStatus(data);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchStrategyConfig = async () => {
    try {
      const res = await fetch('/api/trading/strategy/config');
      if (res.ok) {
        const data = await res.json();
        if (data.status !== 'not_initialized') {
          setStrategyConfig(data);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchNotificationSettings = async () => {
    try {
      const res = await fetch('/api/settings/notifications');
      if (res.ok) {
        const data = await res.json();
        setNotifications(data);
      }
    } catch (e) {
      console.error(e);
    }
  };


  const fetchSelectedCoins = async () => {
    try {
      const res = await fetch('/api/trading/coins/selected');
      if (res.ok) {
        const data = await res.json();
        setSelectedCoins(data.selected_coins || ['BTCUSDT', 'ETHUSDT']);
        setMaxCoins(data.max_coins || 5);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const toggleCoin = (symbol) => {
    if (selectedCoins.includes(symbol)) {
      // Remove coin
      if (selectedCoins.length > 1) {
        setSelectedCoins(selectedCoins.filter(c => c !== symbol));
      } else {
        alert('최소 1개 이상의 코인을 선택해야 합니다');
      }
    } else {
      // Add coin
      if (selectedCoins.length < maxCoins) {
        setSelectedCoins([...selectedCoins, symbol]);
      } else {
        alert(`최대 ${maxCoins}개까지 선택 가능합니다`);
      }
    }
  };

  const applyCoins = async () => {
    try {
      setSaving(true);
      const res = await fetch('/api/trading/coins/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ coins: selectedCoins })
      });

      if (res.ok) {
        alert('✅ 코인 선택이 저장되었습니다');
      } else {
        const error = await res.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (e) {
      console.error(e);
      alert('Failed to save coin selection');
    } finally {
      setSaving(false);
    }
  };

  const fetchTelegramSettings = async () => {
    try {
      const res = await fetch('/api/settings/notifications/telegram');
      if (res.ok) {
        const data = await res.json();
        setTelegramSettings(prev => ({
          ...prev,
          enabled: !!data.enabled,
          chat_id: data.chat_id || '',
          bot_token_configured: !!data.bot_token_configured
        }));
        // keep channels in sync
        setNotifications(prev => ({ ...prev, telegram: !!data.enabled }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchApiConfig = async () => {
    try {
      const res = await fetch('/api/settings/api-config');
      if (res.ok) {
        const data = await res.json();
        setApiConfig({
          active_exchange: data.active_exchange || 'BINANCE',
          binance_key: data.binance_key || '',
          binance_secret: '',
          testnet: !!data.testnet
        });
      }
    } catch (e) {
      console.error(e);
    }
  };

  const saveApiConfig = async () => {
    setSaving(true);
    try {
      const payload = {
        active_exchange: apiConfig.active_exchange,
        binance_key: apiConfig.binance_key,
        binance_secret: apiConfig.binance_secret || undefined,
        testnet: apiConfig.testnet
      };

      const res = await fetch('/api/settings/api-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        alert(data?.detail || 'API 설정 저장에 실패했습니다.');
        return;
      }

      alert('API 설정이 저장되고 클라이언트가 재접속되었습니다.');
      // Refresh to get potentially formatted/masked values back (though secret stays masked)
      fetchApiConfig();

    } catch (e) {
      console.error(e);
      alert('API 설정 저장 중 오류가 발생했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const saveTelegramSettings = async () => {
    setSaving(true);
    try {
      const payload = {
        enabled: telegramSettings.enabled,
        bot_token: telegramSettings.bot_token || undefined,
        chat_id: telegramSettings.chat_id || undefined
      };
      const res = await fetch('/api/settings/notifications/telegram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        alert(data?.detail || '텔레그램 설정 저장에 실패했습니다.');
        return;
      }
      alert('텔레그램 설정이 저장되었습니다.');
      setTelegramSettings(prev => ({
        ...prev,
        enabled: !!data.enabled,
        chat_id: data.chat_id || prev.chat_id,
        bot_token: '',
        bot_token_configured: !!data.bot_token_configured
      }));
      setNotifications(prev => ({ ...prev, telegram: !!data.enabled }));
    } catch (e) {
      console.error(e);
      alert('텔레그램 설정 저장 중 오류가 발생했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const testTelegramMessage = async () => {
    setSaving(true);
    try {
      const payload = {
        message: '✅ 텔레그램 알림 테스트 메시지입니다. (Settings)',
        bot_token: telegramSettings.bot_token || undefined,
        chat_id: telegramSettings.chat_id || undefined
      };
      const res = await fetch('/api/settings/notifications/telegram/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        alert(data?.detail || '텔레그램 테스트 메시지 전송에 실패했습니다.');
        return;
      }
      alert('테스트 메시지를 전송했습니다. 텔레그램을 확인해주세요.');
    } catch (e) {
      console.error(e);
      alert('텔레그램 테스트 중 오류가 발생했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const updateRiskConfig = async (updates) => {
    setSaving(true);
    try {
      const res = await fetch('/api/trading/risk/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      if (res.ok) {
        alert('Risk settings updated!');
        fetchRiskStatus();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const updateStrategyConfig = async (updates) => {
    try {
      const res = await fetch('/api/trading/strategy/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      if (res.ok) {
        alert('Strategy updated!');
        fetchStrategyConfig();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const toggleKillSwitch = async () => {
    await updateRiskConfig({ kill_switch: !riskStatus.kill_switch });
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: '900', color: '#fff', marginBottom: '0.5rem' }}>
          Settings
        </h1>
        <p style={{ color: '#666', fontSize: '0.85rem' }}>
          리스크 관리, 알림 설정, API 구성
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
          { id: 'risk', label: 'Risk Management', icon: '⚠️' },
          { id: 'notifications', label: 'Notifications', icon: '🔔' },
          { id: 'api', label: 'API Config', icon: '🔑' }
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
        {/* Risk Management Tab */}
        {activeTab === 'risk' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Kill Switch */}
            <div style={{
              background: '#0a0a0a',
              border: '1px solid #222',
              borderRadius: '4px',
              padding: '1.5rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontSize: '1rem', fontWeight: '800', color: '#fff', marginBottom: '0.5rem' }}>
                    Emergency Kill Switch
                  </h3>
                  <p style={{ fontSize: '0.8rem', color: '#666' }}>
                    즉시 모든 거래 중단 및 포지션 청산
                  </p>
                </div>
                <button
                  onClick={toggleKillSwitch}
                  style={{
                    padding: '0.75rem 1.5rem',
                    background: riskStatus.kill_switch ? '#ff5b5b' : 'transparent',
                    color: riskStatus.kill_switch ? '#000' : '#fff',
                    border: riskStatus.kill_switch ? 'none' : '1px solid #222',
                    borderRadius: '2px',
                    fontWeight: '900',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    textTransform: 'uppercase'
                  }}
                >
                  {riskStatus.kill_switch ? 'ACTIVE - Click to Deactivate' : 'Activate Kill Switch'}
                </button>
              </div>
            </div>

            {/* Current Risk Status */}
            <div style={{
              background: '#0a0a0a',
              border: '1px solid #222',
              borderRadius: '4px',
              padding: '1.5rem'
            }}>
              <h3 style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '1rem', color: '#fff' }}>
                Current Risk Status
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
                <div style={{ padding: '1rem', background: '#000', borderRadius: '2px' }}>
                  <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.5rem' }}>Daily Loss</div>
                  <div style={{
                    fontSize: '1.2rem',
                    fontWeight: '900',
                    color: riskStatus.current_daily_loss > riskStatus.daily_loss_limit * 0.8 ? '#ff5b5b' : '#fff'
                  }}>
                    ${riskStatus.current_daily_loss.toFixed(2)} / ${riskStatus.daily_loss_limit}
                  </div>
                </div>
                <div style={{ padding: '1rem', background: '#000', borderRadius: '2px' }}>
                  <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.5rem' }}>Margin Level</div>
                  <div style={{
                    fontSize: '1.2rem',
                    fontWeight: '900',
                    color: riskStatus.current_margin_level > riskStatus.max_margin_level * 0.8 ? '#ff5b5b' : '#fff'
                  }}>
                    {(riskStatus.current_margin_level * 100).toFixed(1)}%
                  </div>
                </div>
                <div style={{ padding: '1rem', background: '#000', borderRadius: '2px' }}>
                  <div style={{ fontSize: '0.7rem', color: '#666', marginBottom: '0.5rem' }}>Risk Status</div>
                  <div style={{
                    fontSize: '1.2rem',
                    fontWeight: '900',
                    color: riskStatus.risk_status === 'NORMAL' ? '#00b07c' : riskStatus.risk_status === 'WARNING' ? '#ffaa00' : '#ff5b5b'
                  }}>
                    {riskStatus.risk_status}
                  </div>
                </div>
              </div>
            </div>

            {/* Risk Limits Configuration */}
            <div style={{
              background: '#0a0a0a',
              border: '1px solid #222',
              borderRadius: '4px',
              padding: '1.5rem'
            }}>
              <h3 style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '1rem', color: '#fff' }}>
                Risk Limits
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.5rem', display: 'block' }}>
                    Daily Loss Limit ($)
                  </label>
                  <input
                    type="number"
                    value={riskStatus.daily_loss_limit}
                    onChange={(e) => setRiskStatus({ ...riskStatus, daily_loss_limit: parseFloat(e.target.value) })}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      background: '#000',
                      border: '1px solid #222',
                      borderRadius: '2px',
                      color: '#fff',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.5rem', display: 'block' }}>
                    Max Margin Level (0-1)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={riskStatus.max_margin_level}
                    onChange={(e) => setRiskStatus({ ...riskStatus, max_margin_level: parseFloat(e.target.value) })}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      background: '#000',
                      border: '1px solid #222',
                      borderRadius: '2px',
                      color: '#fff',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>
                <button
                  onClick={() => updateRiskConfig({
                    daily_loss_limit: riskStatus.daily_loss_limit,
                    max_margin_level: riskStatus.max_margin_level
                  })}
                  disabled={saving}
                  style={{
                    padding: '0.75rem',
                    background: '#00b07c',
                    color: '#000',
                    border: 'none',
                    borderRadius: '2px',
                    fontWeight: '900',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    textTransform: 'uppercase',
                    marginTop: '0.5rem'
                  }}
                >
                  {saving ? 'Saving...' : 'Save Risk Settings'}
                </button>
              </div>
            </div>

            {/* Coin Selection Configuration */}
            <div style={{
              background: '#0a0a0a',
              border: '1px solid #222',
              borderRadius: '4px',
              padding: '1.5rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <div>
                  <h3 style={{ fontSize: '1rem', fontWeight: '800', color: '#fff', marginBottom: '0.5rem' }}>
                    Trading Coin Selection
                  </h3>
                  <p style={{ fontSize: '0.8rem', color: '#666' }}>
                    AI가 모니터링하고 거래할 코인을 선택하세요 (최대 {maxCoins}개)
                  </p>
                </div>
                <button
                  onClick={applyCoins}
                  disabled={saving}
                  style={{
                    padding: '0.6rem 1.2rem',
                    background: '#f0b90b',
                    color: '#000',
                    border: 'none',
                    borderRadius: '2px',
                    fontWeight: '900',
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                    textTransform: 'uppercase'
                  }}
                >
                  {saving ? 'Updating...' : 'Apply Selection'}
                </button>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '1rem' }}>
                {AVAILABLE_COINS.map(coin => {
                  const isSelected = selectedCoins.includes(coin.symbol);
                  return (
                    <div
                      key={coin.symbol}
                      onClick={() => toggleCoin(coin.symbol)}
                      style={{
                        padding: '1rem',
                        background: isSelected ? 'rgba(240, 185, 11, 0.1)' : '#000',
                        border: isSelected ? '1px solid #f0b90b' : '1px solid #222',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        transition: 'all 0.2s'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span style={{ fontSize: '1.2rem' }}>{coin.emoji}</span>
                        <div>
                          <div style={{ fontSize: '0.85rem', fontWeight: '800', color: isSelected ? '#f0b90b' : '#fff' }}>
                            {coin.symbol.replace('USDT', '')}
                          </div>
                          <div style={{ fontSize: '0.65rem', color: '#666' }}>{coin.name}</div>
                        </div>
                      </div>
                      <div style={{
                        width: '18px',
                        height: '18px',
                        borderRadius: '2px',
                        border: isSelected ? 'none' : '1px solid #444',
                        background: isSelected ? '#f0b90b' : 'transparent',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#000',
                        fontSize: '12px'
                      }}>
                        {isSelected && '✓'}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Strategy Configuration */}
            <div style={{
              background: '#0a0a0a',
              border: '1px solid #222',
              borderRadius: '4px',
              padding: '1.5rem'
            }}>
              <h3 style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '1rem', color: '#fff' }}>
                Strategy Configuration
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.5rem', display: 'block' }}>
                    Trading Mode
                  </label>
                  <select
                    value={strategyConfig.mode}
                    onChange={(e) => updateStrategyConfig({ mode: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      background: '#000',
                      border: '1px solid #222',
                      borderRadius: '2px',
                      color: '#fff',
                      fontSize: '0.85rem'
                    }}
                  >
                    <option value="SCALP">SCALP (단타)</option>
                    <option value="SWING">SWING (스윙)</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.5rem', display: 'block' }}>
                    Leverage Mode
                  </label>
                  <select
                    value={strategyConfig.leverage_mode}
                    onChange={(e) => updateStrategyConfig({ leverage_mode: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      background: '#000',
                      border: '1px solid #222',
                      borderRadius: '2px',
                      color: '#fff',
                      fontSize: '0.85rem'
                    }}
                  >
                    <option value="AUTO">AUTO (자동)</option>
                    <option value="MANUAL">MANUAL (수동)</option>
                  </select>
                </div>
                {strategyConfig.leverage_mode === 'MANUAL' && (
                  <div>
                    <label style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.5rem', display: 'block' }}>
                      Manual Leverage (1-10x)
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={strategyConfig.manual_leverage}
                      onChange={(e) => setStrategyConfig({ ...strategyConfig, manual_leverage: parseInt(e.target.value) })}
                      onBlur={() => updateStrategyConfig({ manual_leverage: strategyConfig.manual_leverage })}
                      style={{
                        width: '100%',
                        padding: '0.75rem',
                        background: '#000',
                        border: '1px solid #222',
                        borderRadius: '2px',
                        color: '#fff',
                        fontSize: '0.85rem'
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Notifications Tab */}
        {activeTab === 'notifications' && (
          <div style={{
            background: '#0a0a0a',
            border: '1px solid #222',
            borderRadius: '4px',
            padding: '1.5rem'
          }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '1rem', color: '#fff' }}>
              Notification Settings
            </h3>
            <p style={{ fontSize: '0.8rem', color: '#666', marginBottom: '1.5rem' }}>
              텔레그램 알림을 활성화하고 테스트 메시지를 전송할 수 있습니다.
            </p>

            {/* Telegram */}
            <div style={{ padding: '1rem', background: '#000', borderRadius: '2px', border: '1px solid #222' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '0.9rem', fontWeight: '900', color: '#fff' }}>Telegram 알림</div>
                  <div style={{ fontSize: '0.75rem', color: '#666', marginTop: '0.25rem' }}>
                    Bot Token / Chat ID를 저장한 뒤 테스트 메시지를 보내세요.
                    {telegramSettings.bot_token_configured && (
                      <span style={{ color: '#00b07c', marginLeft: '0.5rem', fontWeight: '900' }}>
                        (Token 저장됨)
                      </span>
                    )}
                  </div>
                </div>

                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={telegramSettings.enabled}
                    onChange={(e) => {
                      const enabled = e.target.checked;
                      setTelegramSettings(prev => ({ ...prev, enabled }));
                      setNotifications(prev => ({ ...prev, telegram: enabled }));
                    }}
                  />
                  <span style={{ color: '#fff', fontSize: '0.85rem', fontWeight: '800' }}>
                    {telegramSettings.enabled ? 'ON' : 'OFF'}
                  </span>
                </label>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1rem' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.5rem', display: 'block' }}>
                    Bot Token (API)
                  </label>
                  <input
                    type="password"
                    placeholder={telegramSettings.bot_token_configured ? '이미 저장됨 (변경 시 새로 입력)' : '123456:ABC-DEF...'}
                    value={telegramSettings.bot_token}
                    onChange={(e) => setTelegramSettings(prev => ({ ...prev, bot_token: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      background: '#0a0a0a',
                      border: '1px solid #222',
                      borderRadius: '2px',
                      color: '#fff',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.5rem', display: 'block' }}>
                    Chat ID (챗봇 아이디)
                  </label>
                  <input
                    type="text"
                    placeholder="예: 123456789"
                    value={telegramSettings.chat_id}
                    onChange={(e) => setTelegramSettings(prev => ({ ...prev, chat_id: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      background: '#0a0a0a',
                      border: '1px solid #222',
                      borderRadius: '2px',
                      color: '#fff',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
                <button
                  onClick={saveTelegramSettings}
                  disabled={saving}
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    background: '#00b07c',
                    color: '#000',
                    border: 'none',
                    borderRadius: '2px',
                    fontWeight: '900',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    textTransform: 'uppercase'
                  }}
                >
                  {saving ? 'Saving...' : '저장'}
                </button>

                <button
                  onClick={testTelegramMessage}
                  disabled={saving}
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    background: 'transparent',
                    color: '#fff',
                    border: '1px solid #222',
                    borderRadius: '2px',
                    fontWeight: '900',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    textTransform: 'uppercase'
                  }}
                >
                  테스트 메시지
                </button>
              </div>
            </div>
          </div>
        )}

        {/* API Config Tab */}
        {activeTab === 'api' && (
          <div style={{
            background: '#0a0a0a',
            border: '1px solid #222',
            borderRadius: '4px',
            padding: '1.5rem'
          }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '1rem', color: '#fff' }}>
              Exchange & API Configuration
            </h3>
            <p style={{ fontSize: '0.8rem', color: '#666', marginBottom: '1.5rem' }}>
              사용할 거래소와 API 키를 설정하세요 (변경 시 봇이 재시작됩니다)
            </p>

            <div style={{ display: 'grid', gap: '1.5rem' }}>


              {/* Testnet Toggle */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#000', padding: '1rem', borderRadius: '2px', border: '1px solid #222' }}>
                <div>
                  <div style={{ fontSize: '0.9rem', fontWeight: '900', color: '#fff' }}>Testnet Mode</div>
                  <div style={{ fontSize: '0.75rem', color: '#666', marginTop: '0.25rem' }}>
                    실제 자산이 아닌 테스트넷 환경 사용 (Binance 전용)
                  </div>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={apiConfig.testnet}
                    onChange={(e) => setApiConfig({ ...apiConfig, testnet: e.target.checked })}
                  />
                  <span style={{ color: apiConfig.testnet ? '#f0b90b' : '#666', fontSize: '0.85rem', fontWeight: '800' }}>
                    {apiConfig.testnet ? 'TESTNET ON' : 'MAINNET'}
                  </span>
                </label>
              </div>

              {/* Binance Section */}
              <div style={{ border: '1px solid #1a1a1a', padding: '1.2rem', borderRadius: '4px', background: '#080808' }}>
                <h4 style={{ color: '#f0b90b', fontSize: '0.85rem', marginBottom: '1rem' }}>BINANCE SETTINGS</h4>
                <div style={{ display: 'grid', gap: '1rem' }}>
                  <div>
                    <label style={{ fontSize: '0.65rem', color: '#444', marginBottom: '0.4rem', display: 'block' }}>API KEY</label>
                    <input
                      type="text"
                      value={apiConfig.binance_key}
                      onChange={(e) => setApiConfig({ ...apiConfig, binance_key: e.target.value })}
                      placeholder="Binance API Key"
                      style={{ width: '100%', padding: '0.75rem', background: '#000', border: '1px solid #222', borderRadius: '2px', color: '#fff', fontSize: '0.8rem', fontFamily: 'monospace' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.65rem', color: '#444', marginBottom: '0.4rem', display: 'block' }}>API SECRET</label>
                    <input
                      type="password"
                      value={apiConfig.binance_secret}
                      onChange={(e) => setApiConfig({ ...apiConfig, binance_secret: e.target.value })}
                      placeholder="Insert Secret Key (Hidden)"
                      style={{ width: '100%', padding: '0.75rem', background: '#000', border: '1px solid #222', borderRadius: '2px', color: '#fff', fontSize: '0.8rem', fontFamily: 'monospace' }}
                    />
                  </div>
                </div>
              </div>


              {/* Save Button */}
              <button
                onClick={saveApiConfig}
                disabled={saving}
                style={{
                  padding: '1rem',
                  background: '#f0b90b',
                  color: '#000',
                  border: 'none',
                  borderRadius: '2px',
                  fontWeight: '900',
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  textTransform: 'uppercase',
                  marginTop: '0.5rem',
                  boxShadow: '0 4px 20px rgba(240, 185, 11, 0.2)'
                }}
              >
                {saving ? 'Saving & Reconnecting...' : 'Save API Configuration'}
              </button>

            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Settings;
