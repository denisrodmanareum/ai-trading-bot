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

  // API Config States
  const [apiConfig, setApiConfig] = useState({
    binance_api_key: '',
    binance_secret_key: '',
    testnet: false
  });

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchRiskStatus();
    fetchStrategyConfig();
    fetchNotificationSettings();
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
              알림 기능은 곧 출시됩니다
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', opacity: 0.5 }}>
              {Object.entries(notifications).map(([key, value]) => (
                <div key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', background: '#000', borderRadius: '2px' }}>
                  <span style={{ fontSize: '0.85rem', color: '#fff', textTransform: 'capitalize' }}>{key}</span>
                  <div style={{
                    width: '40px',
                    height: '20px',
                    background: value ? '#00b07c' : '#333',
                    borderRadius: '10px',
                    position: 'relative',
                    cursor: 'not-allowed'
                  }}>
                    <div style={{
                      width: '16px',
                      height: '16px',
                      background: '#fff',
                      borderRadius: '50%',
                      position: 'absolute',
                      top: '2px',
                      left: value ? '22px' : '2px',
                      transition: 'left 0.2s'
                    }} />
                  </div>
                </div>
              ))}
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
              API Configuration
            </h3>
            <p style={{ fontSize: '0.8rem', color: '#666', marginBottom: '1.5rem' }}>
              Binance API 키는 환경 변수(.env)에서 설정됩니다
            </p>
            <div style={{ padding: '2rem', background: '#000', borderRadius: '2px', textAlign: 'center' }}>
              <p style={{ color: '#666', fontSize: '0.85rem' }}>
                API 설정은 <code style={{ color: '#00b07c' }}>backend/.env</code> 파일에서 관리됩니다.
              </p>
              <p style={{ color: '#444', fontSize: '0.75rem', marginTop: '0.5rem' }}>
                BINANCE_API_KEY, BINANCE_SECRET_KEY
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Settings;
