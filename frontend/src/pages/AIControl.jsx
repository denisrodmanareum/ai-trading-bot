import React, { useState, useEffect } from 'react';

function AIControl() {
  const [activeTab, setActiveTab] = useState('training');
  const [training, setTraining] = useState(false);
  const [models, setModels] = useState([]);
  const [loadingModel, setLoadingModel] = useState(null); // Track which model is loading
  // -- NEW: Scheduler Config Logic --
  const [autoTrain, setAutoTrain] = useState({
    enabled: false,
    min_win_rate: 50.0,
    check_interval_hours: 24,
    retrain_on_loss: true
  });

  const fetchSchedulerConfig = async () => {
    try {
      const res = await fetch('/api/ai/scheduler/config');
      if (res.ok) {
        const data = await res.json();
        setAutoTrain(data);
      }
    } catch (err) {
      console.error("Failed to fetch scheduler config:", err);
    }
  };

  const updateSchedulerConfig = async (newConfig) => {
    try {
      const res = await fetch('/api/ai/scheduler/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig)
      });
      if (res.ok) {
        const data = await res.json();
        setAutoTrain(data.config);
      }
    } catch (err) {
      console.error("Failed to update scheduler config:", err);
    }
  };

  useEffect(() => {
    fetchModels();
    fetchPerformance();
    fetchSchedulerConfig();
  }, []);

  // Polling for training status
  useEffect(() => {
    let intervalId;

    if (training) {
      intervalId = setInterval(async () => {
        try {
          const res = await fetch('/api/ai/status');
          if (res.ok) {
            const data = await res.json();
            // If training status says false but we are true -> finished
            if (!data.training_status?.is_training) {
              setTraining(false);
              fetchModels(); // Refresh list
              alert("학습이 완료되었습니다! 새로운 모델을 확인하세요.");
            }
          }
        } catch (e) {
          console.error("Polling failed", e);
        }
      }, 5000); // Check every 5s
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [training]);

  const [config, setConfig] = useState({
    symbol: 'BTCUSDT',
    interval: '1m',
    days: 30,
    episodes: 1000,
    leverage: 5,
    stop_loss: 2.0,
    take_profit: 5.0,
    reward_strategy: 'simple'
  });

  const [performance, setPerformance] = useState({
    currentModel: 'None',
    winRate: 65.5,
    totalTrades: 150,
    avgPnL: 8.34,
    sharpeRatio: 1.45,
    lastTraining: '2시간 전'
  });

  const fetchModels = async () => {
    try {
      // 1. Get List
      const resModels = await fetch('/api/ai/models');
      const dataModels = await resModels.json();

      // 2. Get Active Status
      const resStatus = await fetch('/api/ai/status');
      const dataStatus = await resStatus.json();

      // Ensure backend sends 'active_model' or similar, fallback for now
      const activeModelPath = dataStatus.model_info?.model_path || '';

      // Update performance state with active model name if available
      if (activeModelPath) {
        setPerformance(prev => ({
          ...prev,
          currentModel: activeModelPath.split('/').pop() // simplistic filename extraction
        }));
      }

      const formatted = dataModels.models.map(m => {
        const isActive = dataStatus.status === 'loaded' &&
          (activeModelPath.includes(m.filename) || (dataStatus.model_info?.models && dataStatus.model_info.models.some(p => p.includes(m.filename))));

        return {
          name: m.filename || m.name,
          created: new Date(m.modified * 1000).toLocaleString(),
          winRate: 0,
          status: isActive ? 'active' : 'inactive'
        };
      });

      setModels(formatted);
    } catch (err) {
      console.error("Failed to fetch models:", err);
    }
  };

  const [selectedModels, setSelectedModels] = useState([]); // New State

  const toggleModelSelection = (modelName) => {
    if (selectedModels.includes(modelName)) {
      setSelectedModels(selectedModels.filter(m => m !== modelName));
    } else {
      setSelectedModels([...selectedModels, modelName]);
    }
  };

  const startEnsemble = async () => {
    if (selectedModels.length < 2) {
      alert("최소 2개 이상의 모델을 선택해야 합니다.");
      return;
    }

    try {
      const res = await fetch('/api/ai/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // API expects query params or body? backend is query param for single, body for list?
        // The backend definition: load_model(model_path: Optional[str] = None, model_paths: Optional[list[str]] = None)
        // FastAPI handles JSON body for list automatically if pydantic model, but here it's query params?
        // Wait, lists in query params are tricky. Let's send as JSON body if we change backend to accept body.
        // Actually, backend defines arguments to function, so FastAPI treats them as query params by default unless Body() used.
        // Let's check backend... `load_model(model_path..., model_paths...)`. 
        // To send list as query param: `model_paths=a&model_paths=b`.
        // Easier to just use JSON body. I should update backend to use Pydantic model for loading too, or use Body explicitly.

        // Let's assume I fix backend to accept JSON or use correct fetch.
        // For now, let's try constructing query string.
      });

      // Actually, let's fix backend to use a Pydantic model for LoadRequest to be safe and clean.
      // I will do that in next step. For now, assuming I will fix it.

    } catch (e) {
      console.error(e);
    }
  };

  const fetchPerformance = async () => {
    // 실제로는 API 호출
  };

  const handleTrain = async () => {
    setTraining(true);
    try {
      const res = await fetch('/api/ai/train', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
      });

      const data = await res.json();

      if (res.ok) {
        alert("학습이 시작되었습니다! (백그라운드 실행)");
      } else {
        alert("학습 시작 실패: " + data.detail);
        setTraining(false);
      }
    } catch (e) {
      console.error(e);
      alert("학습 요청 중 오류가 발생했습니다.");
      setTraining(false);
    }
  };

  const intervalOptions = [
    { value: '1m', label: '1분' },
    { value: '5m', label: '5분' },
    { value: '15m', label: '15분' },
    { value: '1h', label: '1시간' },
    { value: '4h', label: '4시간' },
    { value: '1d', label: '1일' }
  ];

  return (
    <div className="ai-control container-fluid p-4">
      <header className="mb-5 border-bottom border-dim pb-3">
        <h1 className="display-6 fw-bold text-white uppercase letter-spacing-lg">Neural Orchestration Center</h1>
        <p className="text-secondary small uppercase fw-bold">Advanced model management and strategic intelligence</p>
      </header>

      {/* Performance Summary */}
      <div className="card" style={{ marginBottom: '2.5rem', padding: '1.5rem' }}>
        <h2 style={{ fontSize: '0.8rem', fontWeight: '900', marginBottom: '1.5rem', color: '#444', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Intelligence Profile</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '1rem' }}>
          {[
            { label: 'Win Rate', val: `${performance.winRate}%`, color: 'var(--accent-success)' },
            { label: 'Active Matrix', val: performance.currentModel, color: '#fff', fontSize: '0.7rem' },
            { label: 'Total Ops', val: performance.totalTrades },
            { label: 'Avg PnL', val: `$${performance.avgPnL}`, color: 'var(--accent-success)' },
            { label: 'Sharpe', val: performance.sharpeRatio },
            { label: 'Last Sync', val: performance.lastTraining, fontSize: '0.75rem' }
          ].map(item => (
            <div key={item.label} className="stat-card" style={{ borderLeft: '1px solid #111', paddingLeft: '1rem' }}>
              <div style={{ fontSize: '0.55rem', color: '#333', fontWeight: '900', textTransform: 'uppercase', marginBottom: '4px' }}>{item.label}</div>
              <div style={{ fontSize: item.fontSize || '1.1rem', fontWeight: '800', fontFamily: 'var(--font-mono)', color: item.color || '#888' }}>{item.val}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{
        display: 'flex',
        gap: '2.5rem',
        borderBottom: '1px solid #111',
        marginBottom: '2.5rem',
        padding: '0 1rem'
      }}>
        {['training', 'models', 'ab-testing', 'auto-learning', 'advanced'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '0.75rem 0',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab ? '2px solid #fff' : 'none',
              color: activeTab === tab ? '#fff' : '#333',
              cursor: 'pointer',
              fontSize: '0.65rem',
              fontWeight: '900',
              textTransform: 'uppercase',
              letterSpacing: '0.15em',
              transition: 'all 0.2s'
            }}
          >
            {tab === 'auto-learning' ? 'Self-Healing' :
              tab === 'ab-testing' ? 'A/B Testing' :
                tab === 'advanced' ? 'Systems' :
                  tab === 'training' ? 'Training' : 'Models'}
          </button>
        ))}
      </div>

      {activeTab === 'training' && (
        <div className="card">
          <h2 style={{ fontSize: '0.8rem', fontWeight: '900', marginBottom: '2rem', color: '#444', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Neural Training Parameters</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginTop: '1.5rem' }}>
            <div className="form-group">
              <label>심볼</label>
              <select value={config.symbol} onChange={e => setConfig({ ...config, symbol: e.target.value })}>
                <option value="BTCUSDT">BTC/USDT</option>
                <option value="ETHUSDT">ETH/USDT</option>
                <option value="SOLUSDT">SOL/USDT</option>
              </select>
            </div>

            <div className="form-group">
              <label>시간봉</label>
              <select value={config.interval} onChange={e => setConfig({ ...config, interval: e.target.value })}>
                {intervalOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>학습 기간 (일)</label>
              <input
                type="number"
                value={config.days}
                onChange={e => setConfig({ ...config, days: parseInt(e.target.value) })}
                min="7"
                max="365"
              />
              <small style={{ color: '#10b981', marginTop: '0.5rem', display: 'block' }}>
                ✅ 추천: 30~90일
              </small>
            </div>

            <div className="form-group">
              <label>에피소드</label>
              <input
                type="number"
                value={config.episodes}
                onChange={e => setConfig({ ...config, episodes: parseInt(e.target.value) })}
                min="100"
                max="10000"
                step="100"
              />
            </div>

            <div className="form-group">
              <label>보상 전략 (Reward)</label>
              <select value={config.reward_strategy} onChange={e => setConfig({ ...config, reward_strategy: e.target.value })}>
                <option value="simple">단순 수익 (PnL)</option>
                <option value="sharpe">Sharpe Ratio (위험 조정)</option>
                <option value="sortino">Sortino Ratio (하락 방어)</option>
              </select>
              <small style={{ color: '#a0a0a0', display: 'block', marginTop: '0.5rem' }}>
                {config.reward_strategy === 'sharpe' && '변동성을 줄이고 꾸준한 수익을 추구합니다.'}
                {config.reward_strategy === 'sortino' && '손실 위험을 극도로 회피합니다.'}
                {config.reward_strategy === 'simple' && '오직 수익금 극대화만 목표로 합니다.'}
              </small>
            </div>

            <div className="form-group">
              <label>레버리지</label>
              <select value={config.leverage} onChange={e => setConfig({ ...config, leverage: parseInt(e.target.value) })}>
                {[1, 2, 3, 5, 10, 20].map(l => <option key={l} value={l}>{l}x</option>)}
              </select>
            </div>

            <div className="form-group">
              <label>스탑로스 (%)</label>
              <input
                type="number"
                step="0.5"
                value={config.stop_loss}
                onChange={e => setConfig({ ...config, stop_loss: parseFloat(e.target.value) })}
              />
            </div>

            <div className="form-group">
              <label>익절 (%)</label>
              <input
                type="number"
                step="0.5"
                value={config.take_profit}
                onChange={e => setConfig({ ...config, take_profit: parseFloat(e.target.value) })}
              />
            </div>
          </div>

          <button
            onClick={handleTrain}
            disabled={training}
            className="btn btn-primary primary-glow"
            style={{
              width: '100%',
              marginTop: '2rem',
              padding: '1.2rem',
              fontSize: '1.1rem',
              background: training ? 'var(--glass-surface)' : 'var(--primary-gradient)',
              opacity: training ? 0.7 : 1,
              cursor: training ? 'not-allowed' : 'pointer',
              position: 'relative',
              overflow: 'hidden'
            }}
          >
            {training ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                <div className="spinner" style={{ width: '20px', height: '20px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff' }}></div>
                <span>AI 학습 요청 중...</span>
              </div>
            ) : (
              '🚀 학습 시작'
            )}
            {training && (
              <div style={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                height: '3px',
                background: 'var(--accent-primary)',
                animation: 'loadingBar 2s infinite ease-in-out',
                width: '100%'
              }}></div>
            )}
          </button>
        </div>
      )}

      {/* Models Tab */}
      {activeTab === 'models' && (
        <div>
          <h2>모델 관리 ({models.length})</h2>

          {/* Ensemble Actions */}
          <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#a0a0a0' }}>선택된 모델: {selectedModels.length} / 3</span>
            {selectedModels.length >= 2 && (
              <button
                className="btn btn-primary"
                onClick={async () => {
                  try {
                    const res = await fetch('/api/ai/load', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ model_paths: selectedModels.map(name => "data/models/" + name) })
                    });
                    const data = await res.json();
                    if (res.ok) {
                      alert(`앙상블 모드 시작!\n모델: ${selectedModels.join(', ')}`);
                      fetchPerformance(); // Update status
                      fetchModels(); // Refresh list to update active status
                    } else {
                      alert("Error: " + data.detail);
                    }
                  } catch (e) {
                    alert("Ensemble load failed");
                  }
                }}
              >
                🤝 앙상블 시작 ({selectedModels.length})
              </button>

            )}

            {selectedModels.length >= 1 && (
              <button
                className="btn"
                style={{ background: 'rgba(239, 68, 68, 0.2)', border: '1px solid #ef4444', color: '#ef4444' }}
                onClick={async () => {
                  if (!window.confirm(`선택한 ${selectedModels.length}개 모델을 모두 삭제하시겠습니까?`)) return;

                  try {
                    const res = await fetch('/api/ai/models/batch-delete', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ model_names: selectedModels })
                    });
                    const data = await res.json();

                    if (res.ok) {
                      alert(`총 ${data.deleted}개 모델 삭제 완료`);
                      setSelectedModels([]);
                      fetchModels();
                    } else {
                      alert("삭제 실패: " + (data.detail || "알 수 없는 오류"));
                    }
                  } catch (e) {
                    console.error(e);
                    alert("삭제 요청 중 오류 발생");
                  }
                }}
              >
                🗑 선택 삭제 ({selectedModels.length})
              </button>
            )}

          </div>

          <div style={{ display: 'grid', gap: '1rem', marginTop: '1.5rem' }}>
            {models.map((model, i) => (
              <div key={i} style={{
                background: model.status === 'active' ? 'rgba(16, 185, 129, 0.05)' :
                  selectedModels.includes(model.name) ? 'rgba(99, 102, 241, 0.05)' : 'rgba(255,255,255,0.02)',
                padding: '1.25rem',
                borderRadius: '12px',
                border: model.status === 'active' ? '1px solid var(--success)' :
                  selectedModels.includes(model.name) ? '1px solid var(--accent-primary)' : '1px solid var(--glass-border)',
                cursor: 'pointer',
                transition: 'var(--transition)'
              }}
                onClick={() => toggleModelSelection(model.name)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    {/* Checkbox for selection */}
                    <div style={{
                      width: '20px', height: '20px', borderRadius: '4px',
                      border: selectedModels.includes(model.name) ? 'none' : '2px solid #555',
                      background: selectedModels.includes(model.name) ? '#667eea' : 'none',
                      display: 'flex', alignItems: 'center', justifyContent: 'center'
                    }}>
                      {selectedModels.includes(model.name) && <span style={{ color: 'white', fontSize: '12px' }}>✓</span>}
                    </div>

                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
                        <span style={{ fontWeight: '600', fontSize: '1.1rem' }}>{model.name}</span>
                        {model.status === 'active' && (
                          <span style={{
                            padding: '0.25rem 0.75rem',
                            background: '#10b981',
                            borderRadius: '12px',
                            fontSize: '0.75rem',
                            fontWeight: '600'
                          }}>
                            Active
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.85rem', color: '#a0a0a0' }}>
                        생성: {model.created} | 승률: {model.winRate}%
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {model.status !== 'active' && (
                      <button className="btn"
                        style={{
                          background: 'rgba(102, 126, 234, 0.2)',
                          border: '1px solid #667eea',
                          color: '#667eea',
                          padding: '0.5rem 1rem',
                          opacity: loadingModel ? 0.5 : 1,
                          cursor: loadingModel ? 'not-allowed' : 'pointer'
                        }}
                        disabled={!!loadingModel}
                        onClick={async (e) => {
                          e.stopPropagation();
                          setLoadingModel(model.name);
                          try {
                            const res = await fetch('/api/ai/models/load', {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ model_path: "data/models/" + model.name })
                            });
                            if (res.ok) {
                              alert("모델이 로드되었습니다: " + model.name);
                              fetchModels();
                              fetchPerformance();
                            } else {
                              alert("로드 실패");
                            }
                          } catch (err) {
                            console.error(err);
                            alert("오류 발생");
                          } finally {
                            setLoadingModel(null);
                          }
                        }}
                      >
                        {loadingModel === model.name ? "로드 중..." : "로드"}
                      </button>
                    )}

                    <button className="btn" style={{ background: 'rgba(239, 68, 68, 0.2)', border: '1px solid #ef4444', color: '#ef4444', padding: '0.5rem 1rem' }}
                      onClick={async (e) => {
                        e.stopPropagation();
                        if (!window.confirm(`정말 ${model.name} 모델을 삭제하시겠습니까?`)) return;

                        try {
                          const res = await fetch(`/api/ai/models/${model.name}`, {
                            method: 'DELETE'
                          });
                          if (res.ok) {
                            alert("삭제되었습니다.");
                            fetchModels();
                          } else {
                            alert("삭제 실패");
                          }
                        } catch (err) {
                          console.error(err);
                          alert("오류 발생");
                        }
                      }}
                    >
                      삭제
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* A/B Testing Tab */}
      {activeTab === 'ab-testing' && (
        <div>
          <h2>🕵️ A/B 테스팅 (Shadow Mode)</h2>
          <p style={{ color: '#a0a0a0', marginBottom: '2rem' }}>
            운영 중인 모델(Champion)과 새로운 모델(Challenger)을 실시간으로 비교 검증합니다.
          </p>

          <div style={{ background: 'rgba(59, 130, 246, 0.1)', padding: '1.5rem', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.3)', marginBottom: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ color: '#3b82f6', marginBottom: '0.5rem' }}>👻 Shadow Mode Control</h3>
              </div>
            </div>

            {/* Comparison Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginTop: '1.5rem' }}>
              {/* Champion (Active) */}
              <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '1rem', borderRadius: '8px', border: '1px solid #10b981' }}>
                <h4 style={{ color: '#10b981', marginBottom: '1rem' }}>👑 Champion (Active)</h4>
                <div style={{ marginBottom: '0.5rem' }}>승률: <span style={{ fontWeight: 'bold' }}>{performance.winRate}%</span></div>
                <div style={{ marginBottom: '0.5rem' }}>수익금: <span style={{ fontWeight: 'bold', color: '#10b981' }}>${performance.avgPnL}</span></div>
                <div style={{ fontSize: '0.8rem', color: '#a0a0a0' }}>현재 실전 매매 중</div>
              </div>

              {/* Challenger (Shadow) */}
              <div style={{ background: 'rgba(107, 114, 128, 0.2)', padding: '1rem', borderRadius: '8px', border: '1px dashed #6b7280' }}>
                <h4 style={{ color: '#d1d5db', marginBottom: '1rem' }}>👻 Challenger (Shadow)</h4>
                <div style={{ marginBottom: '0.5rem' }}>승률: <span style={{ fontWeight: 'bold' }}>--%</span></div>
                <div style={{ marginBottom: '0.5rem' }}>가상 수익: <span style={{ fontWeight: 'bold' }}>--</span></div>

                <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
                  <select className="form-control" style={{ width: 'auto', paddingRight: '2.5rem' }}>
                    <option>모델 선택...</option>
                    {models.map(m => <option key={m.name} value={m.name}>{m.name}</option>)}
                  </select>
                  <button className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}
                    onClick={async (e) => {
                      const select = e.target.previousSibling;
                      const modelName = select.value;
                      if (!modelName || modelName.startsWith('모델')) return alert("모델을 선택해주세요.");

                      try {
                        await fetch('/api/ai/shadow/start', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ model_path: "data/models/" + modelName })
                        });
                        alert("Shadow Mode Started!");
                      } catch (e) {
                        alert("Failed to start shadow mode");
                      }
                    }}
                  >Start</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Auto Learning Tab */}
      {activeTab === 'auto-learning' && (
        <div>
          <h2>자동 학습 설정 (Self-Healing)</h2>

          <div style={{ marginTop: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1.5rem', background: 'rgba(102, 126, 234, 0.1)', borderRadius: '8px', marginBottom: '2rem' }}>
              <div>
                <div style={{ fontWeight: '600', marginBottom: '0.5rem' }}>자동 재학습 활성화</div>
                <div style={{ fontSize: '0.85rem', color: '#a0a0a0' }}>성과가 저조할 때 AI가 스스로 두뇌를 다시 학습합니다.</div>
              </div>
              <label style={{ position: 'relative', display: 'inline-block', width: '60px', height: '34px' }}>
                <input
                  type="checkbox"
                  checked={autoTrain.enabled}
                  onChange={e => updateSchedulerConfig({ ...autoTrain, enabled: e.target.checked })}
                  style={{ opacity: 0, width: 0, height: 0 }}
                />
                <span style={{
                  position: 'absolute',
                  cursor: 'pointer',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: autoTrain.enabled ? '#10b981' : '#ccc',
                  transition: '0.4s',
                  borderRadius: '34px'
                }}>
                  <span style={{
                    position: 'absolute',
                    content: '',
                    height: '26px',
                    width: '26px',
                    left: autoTrain.enabled ? '30px' : '4px',
                    bottom: '4px',
                    background: 'white',
                    transition: '0.4s',
                    borderRadius: '50%'
                  }}></span>
                </span>
              </label>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
              <div className="form-group">
                <label>재학습 주기</label>
                <select
                  value={autoTrain.check_interval_hours}
                  onChange={e => updateSchedulerConfig({ ...autoTrain, check_interval_hours: parseInt(e.target.value) })}
                >
                  <option value={12}>12시간마다</option>
                  <option value={24}>24시간마다 (추천)</option>
                  <option value={168}>주 1회 (7일)</option>
                </select>
              </div>

              <div className="form-group">
                <label>트리거 기준: 최소 승률 (%)</label>
                <input
                  type="number"
                  value={autoTrain.min_win_rate}
                  onChange={e => updateSchedulerConfig({ ...autoTrain, min_win_rate: parseFloat(e.target.value) })}
                  min="30"
                  max="100"
                />
                <small style={{ color: '#a0a0a0', display: 'block', marginTop: '0.5rem' }}>
                  승률이 {autoTrain.min_win_rate}% 이하로 떨어지면 재학습 시작
                </small>
              </div>

              <div style={{ gridColumn: '1 / -1' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={autoTrain.retrain_on_loss}
                    onChange={e => updateSchedulerConfig({ ...autoTrain, retrain_on_loss: e.target.checked })}
                  />
                  <span>일일 순수익이 마이너스면 즉시 재학습 트리거</span>
                </label>
              </div>
            </div>

            <div style={{ marginTop: '2rem', padding: '1.5rem', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
              <h3 style={{ color: '#3b82f6', marginBottom: '1rem' }}>💡 작동 방식</h3>
              <ul style={{ color: '#a0a0a0', lineHeight: '1.8', paddingLeft: '1.5rem' }}>
                <li>AI가 매일 밤(또는 주기에 맞춰) 성과를 분석합니다.</li>
                <li>설정한 승률 기준에 못 미치면 즉시 **자동 학습**을 시작합니다.</li>
                <li>학습 기간은 최근 30일~90일 데이터를 사용하여 최신 트렌드를 반영합니다.</li>
                <li>학습이 완료되면 **새로운 모델이 자동으로 교체** 투입됩니다.</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Advanced Tab */}
      {activeTab === 'advanced' && (
        <div>
          <h2>고급 설정 (Hyperparameter Optimization)</h2>
          <div style={{ marginTop: '2rem' }}>
            <div style={{ background: 'rgba(59, 130, 246, 0.1)', padding: '1.5rem', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.3)', marginBottom: '2rem' }}>
              <h3 style={{ color: '#3b82f6', marginBottom: '0.5rem' }}>🧬 Optuna Hyperparameter Optimization</h3>
              <p style={{ color: '#d1d5db', marginBottom: '1.5rem', fontSize: '0.9rem', lineHeight: '1.6' }}>
                AI가 스스로 수백 번의 실험을 수행하여 최적의 두뇌 구조(Learning Rate, Batch Size 등)를 찾아냅니다.
                <br />이 작업은 서버 자원을 많이 소모합니다.
              </p>

              <div style={{ display: 'flex', gap: '1rem', alignItems: 'end' }}>
                <div className="form-group" style={{ marginBottom: 0, flex: 1 }}>
                  <label>실험 횟수 (Trials)</label>
                  <input
                    type="number"
                    defaultValue={10}
                    min="5"
                    max="100"
                    id="n_trials"
                  />
                </div>
                <button
                  className="btn btn-primary"
                  style={{ padding: '0.8rem 1.5rem', height: '48px' }}
                  onClick={async () => {
                    const btn = document.activeElement;
                    btn.disabled = true;
                    btn.innerText = "⏳ 요청 중...";
                    try {
                      const trials = document.getElementById('n_trials').value;
                      const res = await fetch('/api/ai/optimize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          n_trials: parseInt(trials),
                          symbol: config.symbol,
                          interval: config.interval,
                          days: config.days
                        })
                      });

                      if (res.ok) {
                        const data = await res.json();
                        alert(data.message);
                      } else {
                        const data = await res.json();
                        alert("Error: " + data.detail);
                      }
                    } catch (e) {
                      alert("Optimization start failed");
                    } finally {
                      btn.disabled = false;
                      btn.innerText = "🧪 최적화 시작";
                    }
                  }}
                >
                  🧪 최적화 시작
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AIControl;
