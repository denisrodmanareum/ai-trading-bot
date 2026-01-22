# 🚀 빠른 시작 가이드

다른 PC에서 프로젝트를 다운로드하고 즉시 실행하는 방법

## 📋 체크리스트

### 필수 설치
- [ ] Python 3.11 이상
- [ ] Node.js 16 이상
- [ ] Git

## 🎯 5분 설치 (Windows)

### 1단계: 저장소 클론

```bash
git clone https://github.com/denisrodmanareum/ai-trading-bot.git
cd ai-trading-bot
```

### 2단계: 의존성 설치

```bash
# 백엔드 의존성
cd backend
python -m pip install -r requirements.txt

# 프론트엔드 의존성 (새 터미널)
cd frontend
npm install
```

### 3단계: 환경 설정

```bash
# backend/.env 파일 생성
echo BINANCE_API_KEY=your_api_key > backend/.env
echo BINANCE_API_SECRET=your_secret >> backend/.env
echo BINANCE_TESTNET=True >> backend/.env
```

### 4단계: 실행

```bash
# 프로젝트 루트에서
start_local.bat
```

## 🐧 5분 설치 (Linux/Mac)

### 1단계: 저장소 클론

```bash
git clone https://github.com/denisrodmanareum/ai-trading-bot.git
cd ai-trading-bot
```

### 2단계: 의존성 설치

```bash
# 백엔드
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 프론트엔드 (새 터미널)
cd frontend
npm install
```

### 3단계: 환경 설정

```bash
# backend/.env 파일 생성
cat > backend/.env << EOF
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_secret
BINANCE_TESTNET=True
EOF
```

### 4단계: 실행

```bash
# 터미널 1 - 백엔드
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 터미널 2 - 프론트엔드
cd frontend
npm start
```

## 🎮 첫 거래까지

### 1. AI 모델 학습 (5분)

1. 브라우저에서 `http://localhost:3000` 접속
2. **AI 허브 → AI 제어** 탭
3. 기본 설정으로 **학습 시작**
4. 완료되면 모델 **로드**

### 2. 코인 선택 (1분)

1. **AI 허브 → 코인 선택** 탭
2. **지금 재선별** 클릭
3. 선택된 7개 코인 확인

### 3. 거래 시작 (1분)

1. **수동 거래** 탭
2. **AI 자동 거래 시작** 클릭
3. Scalping 모드 선택

### 4. 모니터링

- **대시보드**: 실시간 뉴스 및 시장 데이터
- **성과 분석**: 거래 내역 및 수익률

## 🔧 문제 해결

### Python 모듈 에러

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Node 에러

```bash
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### 포트 충돌

```bash
# 백엔드 포트 변경
python -m uvicorn app.main:app --port 8001

# 프론트엔드 포트 변경 (자동)
# 3000번 포트가 사용 중이면 자동으로 3001 제안
```

## 📞 도움말

문제가 해결되지 않으면:
- [GitHub Issues](https://github.com/denisrodmanareum/ai-trading-bot/issues)
- README.md의 트러블슈팅 섹션 참고

---

**설치 완료!** 이제 트레이딩을 시작하세요! 🎉
