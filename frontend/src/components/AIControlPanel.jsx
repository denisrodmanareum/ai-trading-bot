import React from 'react';

const AIControlPanel = ({ strategy, updateStrategy, activeSymbol, executionStatus }) => {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', color: 'var(--text-primary)', fontFamily: 'Inter, sans-serif' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <h3 style={{ margin: 0, fontSize: '0.7rem', fontWeight: '900', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#444' }}>Terminal AI Control</h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <div style={{ width: '6px', height: '6px', borderRadius: '1px', background: executionStatus === 'ACTIVE' ? 'var(--accent-success)' : '#222', boxShadow: executionStatus === 'ACTIVE' ? '0 0 8px var(--accent-success)' : 'none' }} />
                    <span style={{ fontSize: '0.6rem', fontWeight: '900', color: executionStatus === 'ACTIVE' ? '#fff' : '#444', textTransform: 'uppercase' }}>{executionStatus}</span>
                </div>
            </div>

            {/* Mode Selection Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', background: '#000', border: '1px solid var(--border-dim)', borderRadius: '2px', padding: '2px' }}>
                {['SCALP', 'SWING'].map(mode => (
                    <button
                        key={mode}
                        onClick={() => updateStrategy({ mode: mode })}
                        style={{
                            padding: '0.5rem',
                            fontSize: '0.7rem',
                            fontWeight: '900',
                            border: 'none',
                            borderRadius: '1px',
                            background: (strategy.mode || strategy.trade_mode) === mode ? '#151515' : 'transparent',
                            color: (strategy.mode || strategy.trade_mode) === mode ? '#fff' : '#444',
                            cursor: 'pointer',
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em'
                        }}
                    >
                        {mode}
                    </button>
                ))}
            </div>

            {/* Confidence Metrics */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <span style={{ fontSize: '0.6rem', fontWeight: '800', color: '#444', textTransform: 'uppercase' }}>Confidence</span>
                    <span style={{ fontSize: '0.75rem', fontWeight: '900', fontFamily: 'var(--font-mono)', color: '#fff' }}>94.2%</span>
                </div>
                <div style={{ height: '2px', background: '#111', overflow: 'hidden', borderRadius: '1px' }}>
                    <div style={{ width: '94.2%', height: '100%', background: '#fff' }} />
                </div>
            </div>

            {/* Status Log */}
            <div style={{
                flex: 1,
                background: '#020202',
                border: '1px solid var(--border-dim)',
                padding: '0.5rem',
                borderRadius: '2px',
                fontSize: '0.65rem',
                fontFamily: 'var(--font-mono)',
                color: '#666',
                maxHeight: '80px',
                overflowY: 'auto'
            }}>
                <div style={{ color: '#aaa', fontWeight: 'bold' }}>[SYSTEM] AI initialized on {activeSymbol}</div>
                <div>[ACTION] Analyzing {strategy.mode || strategy.trade_mode || 'SCALP'} patterns...</div>
                <div>[SIGNAL] Neutral bias detected</div>
            </div>

            {/* Emergency Button */}
            <button
                style={{
                    width: '100%',
                    padding: '0.7rem',
                    background: 'transparent',
                    border: '1px solid #222',
                    color: '#444',
                    fontSize: '0.65rem',
                    fontWeight: '900',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    borderRadius: '2px',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    marginTop: '0.2rem'
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--accent-danger)';
                    e.currentTarget.style.color = 'var(--accent-danger)';
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#222';
                    e.currentTarget.style.color = '#444';
                }}
            >
                Immediate Kill-Switch
            </button>
        </div>
    );
}

export default AIControlPanel;
