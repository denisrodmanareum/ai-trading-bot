# 🤖 AI Trading Bot

바이낸스 선물 거래를 위한 AI 기반 자동 트레이딩 봇

## ✨ 주요 기능

### 🎯 핵심 기능
- **AI 자동 매매**: PPO 강화학습 기반 자동 거래
- **하이브리드 코인 선택**: BTC/ETH + AI가 선택한 상위 알트코인 (최대 7개)
- **멀티 타임프레임 분석**: 1분~1주 차트 동시 분석
- **시장 체제 감지**: TRENDING/RANGING/HIGH_VOLATILITY 자동 인식
- **동적 레버리지**: 시장 상황에 따라 자동 조절 (1x~125x)
- **실시간 대시보드**: 뉴스, 온체인 데이터, 소셜 트렌드 통합

### 📊 AI 기능
- **일일 리뷰**: 매일 거래 성과 분석 및 개선 제안
- **자동 재학습**: 성과 저하 시 자동으로 모델 재학습
- **Quick Wins**: 김치 프리미엄, 볼륨 스파이크, 고래 움직임 감지
- **손절/익절 AI**: 시장 상황에 맞는 동적 SL/TP 설정

### 🎨 사용자 인터페이스
- **프로 트레이딩 UI**: OKX 스타일의 고급 차트 및 오더북
- **실시간 차트**: 24개 기술적 지표 통합
- **멀티 모드**: Scalping (15m, 30m) / Swing (1h, 4h, 1d)
- **한글 지원**: 모든 UI 및 메시지 완전 한글화

## 🚀 빠른 시작

### 필수 요구사항

- **Python**: 3.11 이상
- **Node.js**: 16 이상
- **바이낸스 계정**: Futures API 키 필요

### 1. 저장소 클론

```bash
git clone https://github.com/denisrodmanareum/ai-trading-bot.git
cd ai-trading-bot
```

### 2. 백엔드 설정

```bash
cd backend

# 가상환경 생성 (권장)
python -m venv venv

# 가상환경 활성화
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
# .env 파일 생성 후 아래 내용 입력:
# BINANCE_API_KEY=your_api_key
# BINANCE_API_SECRET=your_api_secret
# BINANCE_TESTNET=True  # 테스트넷 사용 시

# 백엔드 실행
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 프론트엔드 설정

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm start
```

### 4. 브라우저에서 접속

```
http://localhost:3000
```

## 📦 간편 실행 (Windows)

다른 PC에서 처음 다운로드 받으셨다면, 먼저 설치가 필요합니다:

1. **설치 명령 실행**:
   ```bash
   INSTALL.bat
   ```
   이 스크립트가 자동으로 가상환경을 만들고 모든 라이브러리를 설치합니다.

2. **실행**:
   설치가 완료되면 이후부터는 아래 명령어로 바로 실행할 수 있습니다.
   ```bash
   start_local.bat
   ```
   이 명령어는 백엔드와 프론트엔드를 자동으로 실행하고 브라우저를 열어줍니다.

## 🎮 사용 방법

### 1. AI 모델 학습

1. **AI 허브 → AI 제어** 탭으로 이동
2. 학습 설정:
   - 심볼: BTCUSDT
   - 타임프레임: 1m ~ 1w (11가지)
   - 학습 기간: 7~365일
   - 에피소드: 100~10000
   - 레버리지: 1~125x
3. **학습 시작** 클릭
4. 완료 후 모델 로드

### 2. 하이브리드 코인 선택

**AI 허브 → 코인 선택** 탭에서:
- **코어 코인**: BTC, ETH (항상 거래)
- **자동 선택**: AI가 시장 조건에 따라 상위 5개 알트코인 선택
- **재선별 주기**: 1시간마다 자동
- **수동 재선별**: "지금 재선별" 버튼

### 3. 자동 거래 시작

**수동 거래** 페이지에서:
- **AI 자동 거래 시작** 버튼 클릭
- 모드 선택: Scalping / Swing
- 레버리지 모드: AUTO / MANUAL

### 4. 성과 모니터링

**성과 분석** 페이지에서:
- 거래 내역 확인
- 승률, 수익률 분석
- 거래소 동기화

## 🏗️ 프로젝트 구조

```
ai-trading-bot/
├── backend/                 # FastAPI 백엔드
│   ├── ai/                 # AI 모델 및 알고리즘
│   │   ├── agent.py       # PPO 트레이딩 에이전트
│   │   ├── environment.py # 강화학습 환경
│   │   ├── features.py    # 기술적 지표 (24개)
│   │   ├── market_regime.py      # 시장 체제 감지
│   │   ├── multi_timeframe.py    # 멀티 타임프레임 분석
│   │   ├── daily_review.py       # 일일 성과 리뷰
│   │   └── self_learning.py      # 자동 재학습
│   ├── app/                # FastAPI 앱
│   │   ├── api/           # API 엔드포인트
│   │   ├── services/      # 비즈니스 로직
│   │   └── core/          # 설정
│   ├── data/              # 데이터 수집 및 분석
│   │   ├── crypto_news.py        # 뉴스 수집
│   │   ├── market_data.py        # 시장 데이터
│   │   ├── onchain_data.py       # 온체인 데이터
│   │   └── social_trends.py      # 소셜 트렌드
│   └── trading/           # 거래 로직
│       ├── binance_client.py     # 바이낸스 API
│       └── trading_strategy.py   # 전략
├── frontend/               # React 프론트엔드
│   └── src/
│       ├── components/    # 재사용 가능한 컴포넌트
│       └── pages/         # 페이지 컴포넌트
│           ├── DashboardV2.jsx   # 종합 대시보드
│           ├── TradingPerfect.jsx # 트레이딩 페이지
│           ├── AIHub.jsx         # AI 제어/모니터링
│           ├── History.jsx       # 거래 내역
│           └── Settings.jsx      # 설정
├── start_local.bat        # Windows 실행 스크립트
└── README.md
```

## 🔧 주요 설정

### 백엔드 설정 (.env)

```env
# Binance API
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
BINANCE_TESTNET=True

# Database
DATABASE_URL=sqlite:///./trading_bot.db

# AI Settings
DEFAULT_LEVERAGE=5
MAX_LEVERAGE=125
DEFAULT_TRADING_MODE=SCALP
```

### 코인 선택 설정 (AI Hub)

```python
# backend/app/services/coin_selector.py
config = {
    'core_coins': ['BTC', 'ETH'],      # 코어 코인
    'max_altcoins': 5,                 # 최대 알트코인
    'max_total': 7,                    # 총 최대 코인
    'rebalance_interval_hours': 1,     # 재선별 주기
    'filters': {
        'min_market_cap_usd': 1_000_000_000,    # 최소 시가총액
        'min_volume_24h_usd': 100_000_000,      # 최소 거래량
    }
}
```

## 🛡️ 보안 주의사항

⚠️ **중요**: API 키를 절대 공개하지 마세요!

1. `.env` 파일을 생성하고 API 키 입력
2. `.env` 파일이 `.gitignore`에 포함되어 있는지 확인
3. 테스트넷에서 먼저 테스트
4. 실거래 시 작은 금액부터 시작

## 📈 성능 벤치마크

### AI 학습
- **에피소드**: 1000회
- **학습 시간**: 약 30분 (BTCUSDT, 30일)
- **메모리 사용량**: ~600MB

### 실시간 트레이딩
- **응답 시간**: <100ms
- **동시 처리**: 최대 7개 코인
- **CPU 사용률**: ~10%

## 🐛 트러블슈팅

### 백엔드 시작 오류

```bash
# 모듈 누락 시
pip install -r requirements.txt

# 포트 충돌 시
python -m uvicorn app.main:app --reload --port 8001
```

### 프론트엔드 빌드 오류

```bash
# node_modules 재설치
rm -rf node_modules package-lock.json
npm install

# 캐시 클리어
npm cache clean --force
```

### 데이터베이스 초기화

```bash
cd backend
python manual_init_db.py
```

## 📚 추가 문서

- **QUICKSTART.md**: 빠른 시작 가이드
- **PATCH_NOTES.md**: 버전별 패치 노트
- **QUICK_INSTALL.md**: 간편 설치 가이드

## 🤝 기여

기여는 언제나 환영합니다!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## ⚠️ 면책 조항

이 봇은 교육 및 연구 목적으로 제공됩니다. 실제 거래에 사용 시 발생하는 손실에 대해 개발자는 책임지지 않습니다. 암호화폐 거래는 높은 위험을 수반하므로 신중하게 결정하세요.

## 🙏 감사의 말

- [Stable Baselines3](https://github.com/DLR-RM/stable-baselines3) - PPO 구현
- [python-binance](https://github.com/sammchardy/python-binance) - Binance API
- [lightweight-charts](https://github.com/tradingview/lightweight-charts) - 차트 라이브러리
- [FastAPI](https://fastapi.tiangolo.com/) - 백엔드 프레임워크
- [React](https://reactjs.org/) - 프론트엔드 프레임워크

## 📞 연락처

- **GitHub**: [@denisrodmanareum](https://github.com/denisrodmanareum)
- **Issues**: [GitHub Issues](https://github.com/denisrodmanareum/ai-trading-bot/issues)

---

**⭐ 이 프로젝트가 도움이 되었다면 Star를 눌러주세요!**

Made with ❤️ by riot91
