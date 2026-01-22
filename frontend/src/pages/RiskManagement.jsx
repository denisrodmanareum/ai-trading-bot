import React, { useState, useEffect } from 'react';

function RiskManagement() {
    const [status, setStatus] = useState({
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

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // Strategy Config State
    const [strategyConfig, setStrategyConfig] = useState({
        mode: 'SCALP',
        selected_interval: '15m',
        available_intervals: ['15m', '30m'],
        leverage_mode: 'AUTO',
        manual_leverage: 5
    });

    // Edit State
    const [editConfig, setEditConfig] = useState({
        daily_loss_limit: 0,
        max_margin_level: 0,
        position_mode: 'FIXED',
        position_ratio: 0.1
    });

    useEffect(() => {
        fetchStatus();
        fetchStrategyConfig();
        const interval = setInterval(() => {
            fetchStatus();
            fetchStrategyConfig();
        }, 5000);
        return () => clearInterval(interval);
    }, []);

    const fetchStrategyConfig = async () => {
        try {
            const res = await fetch('/api/trading/strategy/config');
            const data = await res.json();
            if (data.status !== "not_initialized") {
                setStrategyConfig(data);
            }
        } catch (e) {
            console.error("Failed to fetch strategy config:", e);
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
                const data = await res.json();
                setStrategyConfig(data.config);
            } else {
                const err = await res.json();
                alert("Error: " + err.detail);
            }
        } catch (e) {
            console.error("Failed to update strategy config:", e);
        }
    };

    const fetchStatus = async () => {
        try {
            const res = await fetch('/api/trading/risk/status');
            const data = await res.json();
            if (data.status !== "not_initialized") {
                setStatus(data);
                if (loading) {
                    setEditConfig({
                        daily_loss_limit: data.daily_loss_limit,
                        max_margin_level: data.max_margin_level,
                        position_mode: data.position_mode,
                        position_ratio: data.position_ratio
                    });
                    setLoading(false);
                }
            }
        } catch (e) {
            console.error(e);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            const res = await fetch('/api/trading/risk/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    daily_loss_limit: parseFloat(editConfig.daily_loss_limit),
                    max_margin_level: parseFloat(editConfig.max_margin_level),
                    kill_switch: status.kill_switch,
                    position_mode: editConfig.position_mode,
                    position_ratio: parseFloat(editConfig.position_ratio)
                })
            });
            if (res.ok) {
                alert("Risk settings updated!");
                fetchStatus();
            } else {
                alert("Failed to update settings");
            }
        } catch (e) {
            alert("Error saving settings");
        } finally {
            setSaving(false);
        }
    };

    const toggleKillSwitch = async () => {
        if (!window.confirm(status.kill_switch ? "Disable Kill Switch? Trading will resume." : "ENABLE KILL SWITCH? All trading will stop immediately.")) return;

        try {
            await fetch('/api/trading/risk/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    kill_switch: !status.kill_switch
                })
            });
            fetchStatus();
        } catch (e) {
            alert("Error toggling switch");
        }
    };

    if (loading) return <div className="p-4">Loading Risk Manager...</div>;

    const getStatusColor = () => {
        if (status.kill_switch || status.risk_status === 'STOPPED') return '#ef4444'; // Red
        if (status.risk_status === 'WARNING') return '#f59e0b'; // Orange
        return '#10b981'; // Green
    };

    return (
        <div className="risk-management p-4">
            <header className="mb-4">
                <h1 className="display-6 fw-bold text-white uppercase letter-spacing-lg">Risk Control Center</h1>
                <p className="text-secondary small uppercase fw-bold">Operational security and margin safeguards</p>
            </header>

            {/* Status Banner */}
            <div style={{
                background: status.kill_switch || status.risk_status === 'STOPPED'
                    ? 'rgba(255, 91, 91, 0.05)'
                    : 'rgba(255, 255, 255, 0.02)',
                padding: '1.5rem 2rem',
                borderRadius: '2px',
                marginBottom: '2rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                border: '1px solid var(--border-main)'
            }}>
                <div>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: '800', marginBottom: '0.5rem', color: getStatusColor() }}>
                        SYSTEM STATUS: {status.kill_switch ? "KILL SWITCH ACTIVE" : status.risk_status}
                    </h2>
                    <p style={{ color: 'var(--text-secondary)', fontWeight: '500' }}>
                        {status.kill_switch
                            ? "🛑 All trading operations are halted manually."
                            : status.risk_status === 'STOPPED'
                                ? "🛑 Trading halted due to risk limits."
                                : "✅ Systems operating normally."}
                    </p>
                </div>

                <button
                    onClick={toggleKillSwitch}
                    className="btn"
                    style={{
                        background: status.kill_switch ? 'var(--accent-success)' : 'var(--accent-danger)',
                        color: '#000',
                        padding: '0.75rem 2rem',
                        fontSize: '0.85rem',
                        fontWeight: '900',
                        border: 'none',
                        borderRadius: '2px'
                    }}
                >
                    {status.kill_switch ? "RESUME OPERATIONS" : "EMERGENCY STOP"}
                </button>
            </div>

            {/* Strategy Mode Card */}
            <div className="card" style={{ marginBottom: '2rem', padding: '1.5rem' }}>
                <h3 style={{ fontSize: '0.8rem', fontWeight: '900', marginBottom: '1.5rem', color: '#444', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                    Trading Strategy Mode
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1.5rem', alignItems: 'end' }}>
                    <div className="form-group" style={{ marginBottom: 0 }}>
                        <label style={{ fontSize: '0.65rem', fontWeight: '800', color: '#666', marginBottom: '0.5rem', display: 'block' }}>전략 모드</label>
                        <select
                            value={strategyConfig.mode}
                            onChange={e => updateStrategyConfig({ mode: e.target.value })}
                            style={{ background: '#000', border: '1px solid var(--border-dim)', borderRadius: '2px', padding: '0.75rem', fontSize: '0.9rem', color: '#fff', width: '100%' }}
                        >
                            <option value="SCALP">⚡ SCALP (단기 매매)</option>
                            <option value="SWING">📈 SWING (중장기 매매)</option>
                        </select>
                    </div>

                    <div className="form-group" style={{ marginBottom: 0 }}>
                        <label style={{ fontSize: '0.65rem', fontWeight: '800', color: '#666', marginBottom: '0.5rem', display: 'block' }}>시간봉 (Timeframe)</label>
                        <select
                            value={strategyConfig.selected_interval}
                            onChange={e => updateStrategyConfig({ selected_interval: e.target.value })}
                            style={{ background: '#000', border: '1px solid var(--border-dim)', borderRadius: '2px', padding: '0.75rem', fontSize: '0.9rem', color: '#fff', width: '100%' }}
                        >
                            {strategyConfig.available_intervals?.map(interval => (
                                <option key={interval} value={interval}>
                                    {interval === '15m' ? '15분봉' :
                                        interval === '30m' ? '30분봉' :
                                            interval === '1h' ? '1시간봉' :
                                                interval === '4h' ? '4시간봉' :
                                                    interval === '1d' ? '일봉' : interval}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div style={{
                        padding: '0.75rem 1rem',
                        background: strategyConfig.mode === 'SCALP' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(59, 130, 246, 0.1)',
                        border: strategyConfig.mode === 'SCALP' ? '1px solid rgba(245, 158, 11, 0.3)' : '1px solid rgba(59, 130, 246, 0.3)',
                        borderRadius: '4px'
                    }}>
                        <div style={{ fontSize: '0.6rem', color: '#666', fontWeight: '800', textTransform: 'uppercase', marginBottom: '4px' }}>현재 설정</div>
                        <div style={{ fontSize: '1rem', fontWeight: '700', color: strategyConfig.mode === 'SCALP' ? '#f59e0b' : '#3b82f6' }}>
                            {strategyConfig.mode} · {strategyConfig.selected_interval}
                        </div>
                    </div>
                </div>

                <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                    <p style={{ fontSize: '0.75rem', color: '#666', lineHeight: '1.6', margin: 0 }}>
                        {strategyConfig.mode === 'SCALP'
                            ? '⚡ SCALP 모드: 15분~30분봉 기준 단기 매매. 빠른 진입/청산으로 소폭의 수익을 자주 실현합니다.'
                            : '📈 SWING 모드: 1시간~일봉 기준 중장기 매매. 큰 트렌드를 따라 포지션을 오래 유지합니다.'}
                    </p>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>

                {/* Daily Loss Limit Card */}
                <div className="card">
                    <h3 style={{ fontSize: '0.8rem', fontWeight: '900', marginBottom: '1.5rem', color: '#444', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                        Daily Loss Safeguard
                    </h3>

                    <div style={{ marginBottom: '2rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.6rem' }}>
                            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Current Loss</span>
                            <span style={{ color: status.current_daily_loss > 0 ? 'var(--danger)' : 'var(--success)', fontWeight: 'bold' }}>
                                -${status.current_daily_loss.toFixed(2)}
                            </span>
                        </div>
                        <div style={{ height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', overflow: 'hidden' }}>
                            <div style={{
                                width: `${Math.min((status.current_daily_loss / status.daily_loss_limit) * 100, 100)}%`,
                                height: '100%',
                                background: 'var(--danger)',
                                boxShadow: '0 0 10px var(--danger)',
                                transition: 'width 0.5s ease-out'
                            }}></div>
                        </div>
                    </div>

                    <div className="form-group">
                        <label>Max Daily Loss ($)</label>
                        <input
                            type="number"
                            value={editConfig.daily_loss_limit}
                            onChange={e => setEditConfig({ ...editConfig, daily_loss_limit: e.target.value })}
                        />
                    </div>
                </div>

                <div className="card">
                    <h3 style={{ fontSize: '0.8rem', fontWeight: '900', marginBottom: '1.5rem', color: '#444', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                        Margin Health
                    </h3>

                    <div>
                        <div style={{ fontSize: '0.6rem', color: '#333', fontWeight: '900', textTransform: 'uppercase', marginBottom: '4px' }}>Maintenance Ratio</div>
                        <div style={{ fontSize: '1.5rem', fontWeight: '800', marginBottom: '1.5rem', fontFamily: 'var(--font-mono)' }}>
                            {status.current_margin_level ? (status.current_margin_level * 100).toFixed(2) + "%" : "0.00%"}
                        </div>

                        <div className="form-group">
                            <label style={{ fontSize: '0.65rem', fontWeight: '800', color: '#444' }}>Max Margin Ratio</label>
                            <input
                                type="number"
                                step="0.01"
                                value={editConfig.max_margin_level}
                                onChange={e => setEditConfig({ ...editConfig, max_margin_level: e.target.value })}
                                style={{ background: '#000', border: '1px solid var(--border-dim)', borderRadius: '2px', padding: '0.5rem', fontSize: '0.8rem', color: '#fff' }}
                            />
                        </div>
                    </div>
                </div>

                {/* Money Management Card */}
                <div className="card" style={{ gridColumn: 'span 2' }}>
                    <h3 style={{ fontSize: '0.8rem', fontWeight: '900', marginBottom: '1.5rem', color: '#444', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                        Neural Allocation (Position Sizing)
                    </h3>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                        <div className="form-group">
                            <label style={{ fontSize: '0.65rem', fontWeight: '800', color: '#444' }}>Strategy Mode</label>
                            <select
                                value={editConfig.position_mode}
                                onChange={e => setEditConfig({ ...editConfig, position_mode: e.target.value })}
                                style={{ background: '#000', border: '1px solid var(--border-dim)', borderRadius: '2px', padding: '0.5rem', fontSize: '0.8rem', color: '#fff' }}
                            >
                                <option value="FIXED">FIXED (SAFE MINIMUM)</option>
                                <option value="RATIO">DYNAMIC (% OF EQUITY)</option>
                            </select>
                        </div>

                        {editConfig.position_mode === 'RATIO' && (
                            <div className="form-group">
                                <label style={{ fontSize: '0.65rem', fontWeight: '800', color: '#444' }}>Allocation Ratio (0.01 - 1.0)</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    min="0.01"
                                    max="1.0"
                                    value={editConfig.position_ratio}
                                    onChange={e => setEditConfig({ ...editConfig, position_ratio: e.target.value })}
                                    style={{ background: '#000', border: '1px solid var(--border-dim)', borderRadius: '2px', padding: '0.5rem', fontSize: '0.8rem', color: '#fff' }}
                                />
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <div style={{ marginTop: '2.5rem', display: 'flex', justifyContent: 'flex-end' }}>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="btn btn-primary"
                    style={{ padding: '0.75rem 3rem', fontSize: '0.8rem', fontWeight: '900', borderRadius: '2px' }}
                >
                    {saving ? "SYNCHRONIZING..." : "SAVE CONFIGURATION"}
                </button>
            </div>

        </div>
    );
}

export default RiskManagement;
