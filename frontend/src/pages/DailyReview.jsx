import React, { useState, useEffect } from 'react';

function DailyReview() {
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    const TypingText = ({ text, speed = 30 }) => {
        const [displayedText, setDisplayedText] = useState('');
        useEffect(() => {
            let i = 0;
            const timer = setInterval(() => {
                setDisplayedText(text.slice(0, i));
                i++;
                if (i > text.length) clearInterval(timer);
            }, speed);
            return () => clearInterval(timer);
        }, [text, speed]);
        return <span>{displayedText}</span>;
    };

    useEffect(() => {
        fetchReports();
    }, []);

    const fetchReports = async () => {
        try {
            const res = await fetch('/api/history/reports');
            if (res.ok) {
                const data = await res.json();
                setReports(data);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const triggerManualReport = async () => {
        if (!window.confirm("오늘의 AI 복기를 지금 수동으로 생성하시겠습니까? (테스트용)")) return;

        setRefreshing(true);
        try {
            const res = await fetch('/api/history/report/generate', { method: 'POST' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                alert("일일 보고서가 생성되었습니다!");
                fetchReports();
            } else if (data.status === 'no_trades') {
                alert("오늘의 거래 내역이 없어 보고서를 생성할 수 없습니다.");
            } else {
                alert("보고서 생성 실패: " + (data.detail || "알 수 없는 오류"));
            }
        } catch (e) {
            alert("에러 발생");
        } finally {
            setRefreshing(false);
        }
    };

    if (loading) return <div className="p-4">AI 일기장을 펼치는 중...</div>;

    return (
        <div className="daily-review p-4" style={{ maxWidth: '900px', margin: '0 auto' }}>
            <div className="header d-flex justify-content-between align-items-end mb-5 border-bottom border-dim pb-3">
                <div>
                    <h1 className="display-6 fw-bold text-white uppercase letter-spacing-lg">Tactical Intelligence Briefing</h1>
                    <p className="text-secondary small uppercase fw-bold">Post-operational analysis and structural debriefing</p>
                </div>
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
                        textTransform: 'uppercase',
                        letterSpacing: '0.1em',
                        transition: 'all 0.2s'
                    }}
                >
                    {refreshing ? "PROCESSING..." : "MANUAL TRIGGER"}
                </button>
            </div>

            {reports.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
                    <p style={{ fontSize: '1.2rem', color: 'var(--text-secondary)' }}>아직 작성된 일기가 없습니다.</p>
                    <p style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.3)', marginTop: '0.5rem' }}>거래가 발생한 날 밤 11:55에 자동으로 생성됩니다.</p>
                </div>
            ) : (
                <div className="reports-list flex flex-col gap-6">
                    {reports.map(report => (
                        <div key={report.id} className="card" style={{ padding: 0, overflow: 'hidden' }}>
                            <div className="p-6">
                                <div className="flex justify-between items-start mb-4">
                                    <div className="flex items-center">
                                        <h3 className="text-xl font-bold text-white">
                                            {new Date(report.date).toLocaleDateString()}
                                        </h3>
                                        {report.retrained && (
                                            <span style={{
                                                padding: '0.2rem 0.6rem',
                                                borderRadius: '2px',
                                                background: '#111',
                                                color: '#666',
                                                fontSize: '0.65rem',
                                                marginLeft: '0.8rem',
                                                border: '1px solid #222',
                                                fontWeight: '900',
                                                textTransform: 'uppercase'
                                            }}>
                                                Self-Healing Matrix
                                            </span>
                                        )}
                                    </div>
                                    <span style={{
                                        padding: '0.3rem 0.8rem',
                                        borderRadius: '20px',
                                        background: report.total_pnl >= 0 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                                        color: report.total_pnl >= 0 ? '#10b981' : '#ef4444',
                                        fontWeight: 'bold',
                                        fontSize: '0.9rem'
                                    }}>
                                        {report.total_pnl >= 0 ? '+' : ''}{report.total_pnl?.toFixed(2)} USDT
                                    </span>
                                </div>

                                <div className="stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                                    {[
                                        { label: 'Total Ops', val: `${report.total_trades}` },
                                        { label: 'Win Rate', val: `${report.win_rate?.toFixed(1)}%` },
                                        { label: 'Gross Fees', val: `-$${report.total_commission?.toFixed(2)}`, color: 'var(--accent-danger)' },
                                        { label: 'Net PnL', val: `$${(report.total_pnl - report.total_commission)?.toFixed(2)}`, color: (report.total_pnl - report.total_commission) >= 0 ? 'var(--accent-success)' : 'var(--accent-danger)' }
                                    ].map(item => (
                                        <div key={item.label} style={{ background: '#050505', border: '1px solid #111', padding: '1rem', textAlign: 'center' }}>
                                            <div style={{ fontSize: '0.55rem', color: '#333', fontWeight: '900', textTransform: 'uppercase', marginBottom: '4px' }}>{item.label}</div>
                                            <div style={{ fontSize: '1rem', fontWeight: '800', fontFamily: 'var(--font-mono)', color: item.color || '#888' }}>{item.val}</div>
                                        </div>
                                    ))}
                                </div>

                                <div className="ai-briefing-panel" style={{
                                    marginTop: '1.5rem',
                                    padding: '1.5rem',
                                    background: '#020202',
                                    borderRadius: '2px',
                                    border: '1px solid #111',
                                    position: 'relative',
                                    overflow: 'hidden'
                                }}>
                                    <div style={{
                                        position: 'absolute',
                                        top: 0, left: 0, width: '100%', height: '1px',
                                        background: 'linear-gradient(90deg, transparent, #333, transparent)',
                                        animation: 'scan 3s linear infinite'
                                    }}></div>

                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                                        <div style={{ width: '4px', height: '4px', background: '#444' }}></div>
                                        <h4 style={{ fontSize: '0.7rem', fontWeight: '900', color: '#444', textTransform: 'uppercase', letterSpacing: '0.1em', margin: 0 }}>
                                            Neural Briefing Matrix
                                        </h4>
                                    </div>

                                    <p style={{
                                        color: '#f1f5f9',
                                        fontSize: '1rem',
                                        lineHeight: '1.7',
                                        fontWeight: '500',
                                        letterSpacing: '0.01em',
                                        margin: 0
                                    }}>
                                        <TypingText text={report.ai_remark || ""} />
                                        <span className="cursor-blink">|</span>
                                    </p>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default DailyReview;
