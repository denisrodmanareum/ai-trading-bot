import React, { useState, useEffect } from 'react';

function LastTrades({ symbol }) {
    const [trades, setTrades] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let active = true;
        const fetchTrades = async () => {
            try {
                // Using standard path. Backend 'pip uninstall' will fix the 404.
                const res = await fetch(`/api/trading/trades/recent?symbol=${symbol}&limit=30`);
                if (res.ok) {
                    const data = await res.json();
                    if (active) {
                        setTrades(data);
                        setLoading(false);
                    }
                }
            } catch (e) {
                // Silent fail for now
            }
        };

        fetchTrades();
        const interval = setInterval(fetchTrades, 2000);
        return () => { active = false; clearInterval(interval); };
    }, [symbol]);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-panel)' }}>
            {/* Header */}
            <div style={{
                height: '32px',
                borderBottom: '1px solid var(--border-dim)',
                display: 'grid',
                gridTemplateColumns: '1fr 1fr 1fr',
                alignItems: 'center',
                padding: '0 0.75rem',
                background: '#020202'
            }}>
                <span style={{ fontSize: '0.65rem', fontWeight: '800', color: '#444', textTransform: 'uppercase' }}>Price (USDT)</span>
                <span style={{ fontSize: '0.65rem', fontWeight: '800', color: '#444', textTransform: 'uppercase', textAlign: 'right' }}>Amount</span>
                <span style={{ fontSize: '0.65rem', fontWeight: '800', color: '#444', textTransform: 'uppercase', textAlign: 'right' }}>Time</span>
            </div>

            {/* Trade List */}
            <div style={{ flex: 1, overflowY: 'auto' }}>
                {trades.length === 0 && loading && (
                    <div style={{ padding: '2rem', textAlign: 'center', color: '#666', fontSize: '0.7rem' }}>
                        Loading...
                    </div>
                )}

                {trades.map((trade, i) => (
                    <div
                        key={`${trade.time}-${i}`}
                        style={{
                            display: 'grid',
                            gridTemplateColumns: '1fr 1fr 1fr',
                            padding: '0.4rem 0.75rem',
                            borderBottom: '1px solid #080808',
                            fontSize: '0.75rem',
                            fontFamily: 'var(--font-mono)',
                            animation: i === 0 ? 'fadeIn 0.3s ease-in' : 'none',
                            transition: 'background 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = '#0a0a0a'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                        <span style={{
                            color: trade.is_buyer_maker ? '#ff5b5b' : '#00b07c',
                            fontWeight: '700'
                        }}>
                            {parseFloat(trade.price).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
                        </span>
                        <span style={{ color: '#888', textAlign: 'right', fontWeight: '600' }}>
                            {parseFloat(trade.qty).toFixed(3)}
                        </span>
                        <span style={{ color: '#555', textAlign: 'right', fontSize: '0.7rem' }}>
                            {new Date(trade.time).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </span>
                    </div>
                ))}
            </div>
            <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-5px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
        </div>
    );
}

export default LastTrades;
