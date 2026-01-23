import React, { useState, useEffect } from 'react';

function Backtest() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState([]);

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const res = await fetch('/api/ai/models');
      const data = await res.json();
      if (data.models && data.models.length > 0) {
        const names = data.models.map(m => m.filename);
        setModels(names);
        // Set first model as default if current config.model is placeholder
        if (config.model.startsWith('model_v') || !names.includes(config.model)) {
          setConfig(prev => ({ ...prev, model: names[0] }));
        }
      }
    } catch (err) {
      console.error("Failed to fetch models:", err);
    }
  };

  const [config, setConfig] = useState({
    model: '',
    symbol: 'BTCUSDT',
    interval: '1h',
    days: 7,
    initialBalance: 10000
  });

  const [tradeAnalysis, setTradeAnalysis] = useState({
    totalTrades: 125,
    wins: 82,
    losses: 43,
    winRate: 65.6,
    avgWinPnL: 15.50,
    avgLossPnL: -8.20,
    largestWin: 125.00,
    largestLoss: -45.00,
    avgHoldTime: '2.5시간',
    // 체결 분석
    fills: {
      market: 120,
      limit: 5,
      avgSlippage: 0.02,  // %
      totalFees: 125.50
    },
    // 시간대별 분석
    byHour: [
      { hour: '00-04', trades: 8, winRate: 62.5 },
      { hour: '04-08', trades: 15, winRate: 73.3 },
      { hour: '08-12', trades: 32, winRate: 68.8 },
      { hour: '12-16', trades: 28, winRate: 64.3 },
      { hour: '16-20', trades: 25, winRate: 60.0 },
      { hour: '20-24', trades: 17, winRate: 70.6 }
    ]
  });

  const handleBacktest = async () => {
    setLoading(true);
    setResults(null);
    try {
      const res = await fetch('/api/ai/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_path: "data/models/" + config.model,
          interval: config.interval,
          start_date: null,
          days: config.days,
          symbol: config.symbol,
          initial_balance: config.initialBalance
        })
      });
      console.log("Backtest status:", res.status);

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);

      const m = data.results;
      // Map API result to UI state
      setResults({
        totalReturn: m.total_return,
        sharpeRatio: m.sharpe_ratio,
        maxDrawdown: m.max_drawdown,
        finalBalance: m.final_balance,
        totalTrades: m.total_trades,
        winRate: m.win_rate
      });

      setTradeAnalysis({
        totalTrades: m.total_trades,
        wins: m.wins,
        losses: m.losses,
        winRate: m.win_rate,
        avgWinPnL: m.avg_win_pnl,
        avgLossPnL: m.avg_loss_pnl,
        largestWin: m.largest_win,
        largestLoss: m.largest_loss,
        avgHoldTime: m.avg_hold_time,
        fills: {
          market: m.total_trades, // Default for now
          limit: 0,
          avgSlippage: 0.0,
          totalFees: m.total_fees || 0
        },
        byHour: m.by_hour || []
      });

    } catch (e) {
      alert("Backtest failed: " + e.message);
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="backtest-page container-fluid p-4">
      <header className="mb-5 border-bottom border-dim pb-3">
        <h1 className="display-6 fw-bold text-white uppercase letter-spacing-lg">Strategic Simulation Lab</h1>
        <p className="text-secondary small uppercase fw-bold">High-fidelity backtesting and neural verification</p>
      </header>

      {/* Backtest Config */}
      <div className="card" style={{ marginBottom: '2.5rem', padding: '1.5rem' }}>
        <h2 style={{ fontSize: '0.8rem', fontWeight: '900', marginBottom: '1.5rem', color: '#444', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Simulation Parameters</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem', marginTop: '1.5rem' }}>
          <div className="form-group">
            <label>Intelligence Model</label>
            <select value={config.model} onChange={e => setConfig({ ...config, model: e.target.value })}>
              {models.length > 0 ? (
                models.map(m => <option key={m} value={m}>{m}</option>)
              ) : (
                <option value="">모델 로딩 중...</option>
              )}
            </select>
          </div>
          <div className="form-group">
            <label>Tactical Asset</label>
            <select value={config.symbol} onChange={e => setConfig({ ...config, symbol: e.target.value })}>
              <option value="BTCUSDT">BTC/USDT</option>
              <option value="ETHUSDT">ETH/USDT</option>
            </select>
          </div>
          <div className="form-group">
            <label>Tactical Interval</label>
            <select value={config.interval} onChange={e => setConfig({ ...config, interval: e.target.value })}>
              <option value="1m">1 minute (Scalp)</option>
              <option value="5m">5 minutes</option>
              <option value="15m">15 minutes</option>
              <option value="1h">1 hour (Swing)</option>
              <option value="4h">4 hours</option>
              <option value="1d">1 day</option>
            </select>
          </div>
          <div className="form-group">
            <label>Inception Balance (USDT)</label>
            <input type="number" value={config.initialBalance} onChange={e => setConfig({ ...config, initialBalance: parseFloat(e.target.value) })} />
          </div>
        </div>
        <button
          onClick={handleBacktest}
          disabled={loading}
          className="btn btn-primary"
          style={{ width: '100%', marginTop: '1.5rem', padding: '1rem', fontSize: '0.8rem', fontWeight: '900', textTransform: 'uppercase', letterSpacing: '0.1em', borderRadius: '2px' }}
        >
          {loading ? 'COMPUTING PATHWAYS...' : 'EXECUTE SIMULATION'}
        </button>
      </div>

      {/* Results Summary */}
      {results && (
        <div className="card" style={{ marginBottom: '2.5rem', padding: '1.5rem' }}>
          <h2 style={{ fontSize: '0.8rem', fontWeight: '900', marginBottom: '1.5rem', color: '#444', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Tactical Evaluation Registry</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '1rem', marginTop: '1rem' }}>
            {[
              { label: 'ROI', val: `${results.totalReturn}%`, color: results.totalReturn >= 0 ? 'var(--accent-success)' : 'var(--accent-danger)' },
              { label: 'Sharpe', val: results.sharpeRatio },
              { label: 'Max DD', val: `${results.maxDrawdown}%`, color: 'var(--accent-danger)' },
              { label: 'Equity', val: `$${results.finalBalance.toLocaleString()}` },
              { label: 'Ops', val: results.totalTrades },
              { label: 'Win Rate', val: `${results.winRate}%`, color: 'var(--accent-success)' }
            ].map(item => (
              <div key={item.label} className="card" style={{ background: '#050505', border: '1px solid #111', padding: '1rem', textAlign: 'center', marginBottom: 0 }}>
                <div style={{ fontSize: '0.55rem', color: '#333', fontWeight: '900', textTransform: 'uppercase', marginBottom: '4px' }}>{item.label}</div>
                <div style={{ fontSize: '1.1rem', fontWeight: '800', fontFamily: 'var(--font-mono)', color: item.color || '#888' }}>{item.val}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trade Analysis */}
      {results && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
          {/* Left: 거래 통계 */}
          <div className="card">
            <h2>거래 분석</h2>
            <div style={{ marginTop: '1.5rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '2rem' }}>
                <div className="stat-card" style={{ background: 'rgba(16, 185, 129, 0.1)' }}>
                  <div className="stat-label">승</div>
                  <div className="stat-value positive">{tradeAnalysis.wins}회</div>
                  <small style={{ color: '#10b981' }}>평균 +${tradeAnalysis.avgWinPnL}</small>
                </div>
                <div className="stat-card" style={{ background: 'rgba(239, 68, 68, 0.1)' }}>
                  <div className="stat-label">패</div>
                  <div className="stat-value negative">{tradeAnalysis.losses}회</div>
                  <small style={{ color: '#ef4444' }}>평균 ${tradeAnalysis.avgLossPnL}</small>
                </div>
              </div>

              <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.05)', borderRadius: '8px', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ color: '#a0a0a0' }}>최대 수익</span>
                  <span style={{ color: '#10b981', fontWeight: '600' }}>${tradeAnalysis.largestWin}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ color: '#a0a0a0' }}>최대 손실</span>
                  <span style={{ color: '#ef4444', fontWeight: '600' }}>${tradeAnalysis.largestLoss}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#a0a0a0' }}>평균 보유 시간</span>
                  <span style={{ fontWeight: '600' }}>{tradeAnalysis.avgHoldTime}</span>
                </div>
              </div>

              <h3 style={{ marginTop: '2rem', marginBottom: '1rem' }}>체결 분석</h3>
              <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ color: '#a0a0a0' }}>시장가 체결</span>
                  <span>{tradeAnalysis.fills.market}회</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ color: '#a0a0a0' }}>지정가 체결</span>
                  <span>{tradeAnalysis.fills.limit}회</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ color: '#a0a0a0' }}>평균 슬리피지</span>
                  <span style={{ color: '#ef4444' }}>{tradeAnalysis.fills.avgSlippage}%</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#a0a0a0' }}>총 수수료</span>
                  <span style={{ color: '#ef4444' }}>${tradeAnalysis.fills.totalFees}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right: 시간대별 분석 */}
          <div className="card">
            <h2>시간대별 성과</h2>
            <div style={{ marginTop: '1.5rem' }}>
              {tradeAnalysis.byHour.map((hour, i) => (
                <div key={i} style={{ marginBottom: '1.5rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <span>{hour.hour}</span>
                    <span style={{ color: hour.winRate >= 65 ? '#10b981' : '#a0a0a0' }}>
                      {hour.trades}회 | 승률 {hour.winRate}%
                    </span>
                  </div>
                  <div style={{ height: '8px', background: 'rgba(0,0,0,0.3)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{
                      width: `${hour.winRate}%`,
                      height: '100%',
                      background: hour.winRate >= 65 ? '#10b981' : hour.winRate >= 50 ? '#667eea' : '#ef4444',
                      transition: 'width 0.3s'
                    }}></div>
                  </div>
                </div>
              ))}

              <div style={{ marginTop: '2rem', padding: '1rem', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
                <h3 style={{ color: '#3b82f6', marginBottom: '0.5rem' }}>💡 인사이트</h3>
                <ul style={{ color: '#a0a0a0', lineHeight: '1.8', paddingLeft: '1.5rem', margin: 0 }}>
                  <li>오전 4~8시 승률 최고 (73.3%)</li>
                  <li>오후 4~8시 승률 저조 (60.0%)</li>
                  <li>야간 거래 빈도 낮음</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 비용 분석 */}
      {results && (
        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>비용 분석 (수수료 + 슬리피지)</h2>
          <div style={{ marginTop: '1.5rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
              <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                <div style={{ color: '#a0a0a0', fontSize: '0.9rem', marginBottom: '0.5rem' }}>거래 수수료</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#ef4444' }}>${tradeAnalysis.fills.totalFees.toFixed(2)}</div>
                <div style={{ color: '#a0a0a0', fontSize: '0.85rem', marginTop: '0.5rem' }}></div>
              </div>
              <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                <div style={{ color: '#a0a0a0', fontSize: '0.9rem', marginBottom: '0.5rem' }}>슬리피지 비용 (추정)</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#ef4444' }}>${(tradeAnalysis.totalTrades * config.initialBalance * 0.0004).toFixed(2)}</div>
                <div style={{ color: '#a0a0a0', fontSize: '0.85rem', marginTop: '0.5rem' }}>총 거래액의 0.04%</div>
              </div>
              <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                <div style={{ color: '#a0a0a0', fontSize: '0.9rem', marginBottom: '0.5rem' }}>총 비용</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#ef4444' }}>${(tradeAnalysis.fills.totalFees + (tradeAnalysis.totalTrades * config.initialBalance * 0.0004)).toFixed(2)}</div>
                <div style={{ color: '#a0a0a0', fontSize: '0.85rem', marginTop: '0.5rem' }}></div>
              </div>
              <div style={{ padding: '1rem', background: results.totalReturn >= 0 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: results.totalReturn >= 0 ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)' }}>
                <div style={{ color: '#a0a0a0', fontSize: '0.9rem', marginBottom: '0.5rem' }}>순이익 (비용 차감 전)</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '600', color: results.totalReturn >= 0 ? '#10b981' : '#ef4444' }}>${(results.finalBalance - config.initialBalance).toLocaleString(undefined, { maximumFractionDigits: 2 })}</div>
                <div style={{ color: results.totalReturn >= 0 ? '#10b981' : '#ef4444', fontSize: '0.85rem', marginTop: '0.5rem' }}>{results.totalReturn}%</div>
              </div>
            </div>

            <div style={{ marginTop: '2rem', padding: '1.5rem', background: 'rgba(255, 193, 7, 0.1)', borderRadius: '8px', border: '1px solid rgba(255, 193, 7, 0.3)' }}>
              <h3 style={{ color: '#ffc107', marginBottom: '1rem' }}>⚠️ 비용 최적화 제안</h3>
              <ul style={{ color: '#a0a0a0', lineHeight: '1.8', paddingLeft: '1.5rem', margin: 0 }}>
                <li>시장가 주문 대신 지정가 주문 사용 → 슬리피지 50% 감소 예상</li>
                <li>거래 빈도 최적화 (125회 → 80회) → 수수료 36% 감소 예상</li>
                <li>예상 비용 절감: ${((tradeAnalysis.fills.totalFees + (tradeAnalysis.totalTrades * config.initialBalance * 0.0004)) * 0.36 * 12).toFixed(0)}/년 검토 권장</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Backtest;
