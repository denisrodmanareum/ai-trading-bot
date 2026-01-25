# 🚀 초간단 설치 가이드 (어떤 PC에서든 5분 안에!)

## ✨ **특징**

- ✅ **원클릭 설치**: 모든 것이 자동으로 설치됩니다
- ✅ **폴더명 무관**: 어떤 이름의 폴더에 있어도 작동
- ✅ **자동 오류 수정**: 일반적인 문제 자동 해결
- ✅ **다른 PC 완벽 지원**: USB에 복사해서 어디서든 실행

---

## 📦 **1. 프로젝트 다운로드**

### **방법 A: Git 사용 (권장)**
```bash
git clone https://github.com/denisrodmanareum/ai-trading-bot.git
cd ai-trading-bot
```

### **방법 B: ZIP 다운로드**
1. GitHub에서 "Code" → "Download ZIP" 클릭
2. 압축 해제 (폴더명 상관없음!)
3. 폴더 열기

---

## ⚡ **2. 자동 설치 (단 1번!)**

### **Windows**

1. **`EASY_INSTALL.bat`** 더블클릭

   ```
   🎯 이것만 클릭하면 끝!
   ```

2. 설치 진행 (5-10분)
   - Python/Node.js 확인
   - 가상환경 생성
   - 패키지 자동 설치
   - 환경 파일 생성
   - 데이터베이스 초기화

3. 완료!

### **설치 중 오류 발생 시**

```bash
doctor.bat
```
- 자동으로 문제를 찾아서 수정합니다!

---

## 🔑 **3. API 키 설정**

1. **`backend\.env`** 파일 열기
2. API 키 입력:
   ```env
   BINANCE_API_KEY=실제_API_키
   BINANCE_API_SECRET=실제_시크릿_키
   BINANCE_TESTNET=True  # 테스트넷 사용
   ```

### **API 키 발급 방법**

**바이낸스 테스트넷:**
1. https://testnet.binancefuture.com 접속
2. 깃허브 계정으로 로그인
3. API Key 생성
4. 복사해서 `.env`에 붙여넣기

---

## 🚀 **4. 봇 실행**

### **빠른 시작**
```bash
START_BOT.bat
```
- 백엔드 + 프론트엔드 동시 실행
- 브라우저 자동 열림

### **또는 기존 방법**
```bash
start_local.bat
```

---

## 🌐 **5. 접속**

브라우저에서 자동으로 열림 또는:
```
http://localhost:3000
```

---

## 🔧 **문제 해결**

### **설치 오류**
```bash
doctor.bat
```
- 모든 문제 자동 진단 및 수정
- 진단 보고서 자동 생성

### **일반적인 문제**

#### **1. Python이 없습니다**
→ https://www.python.org/downloads/
- Python 3.11 이상 설치
- "Add Python to PATH" 체크!

#### **2. Node.js가 없습니다**
→ https://nodejs.org/
- LTS 버전 설치

#### **3. 패키지 설치 실패**
```bash
# 백엔드
cd backend
venv\Scripts\activate
pip install -r requirements.txt

# 프론트엔드
cd frontend
npm cache clean --force
npm install
```

#### **4. 데이터베이스 오류**
```bash
cd backend
venv\Scripts\activate
python manual_init_db.py
```

---

## 📂 **다른 PC로 이동**

### **방법 1: USB 복사**
1. 전체 폴더 복사
2. 새 PC에서 `EASY_INSTALL.bat` 실행
3. 끝!

### **방법 2: Git Clone**
```bash
git clone https://github.com/denisrodmanareum/ai-trading-bot.git
cd ai-trading-bot
EASY_INSTALL.bat
```

### **주의사항**
- ✅ `.env` 파일은 자동으로 제외됨 (보안)
- ✅ `venv`, `node_modules`는 자동 재생성
- ✅ 폴더명 변경해도 OK
- ✅ 한글 경로는 피하세요

---

## 📋 **파일 구조**

```
ai-trading-bot/              ← 어떤 이름이든 OK!
├── EASY_INSTALL.bat         ← 🎯 이것만 실행!
├── START_BOT.bat            ← 봇 실행
├── doctor.bat               ← 문제 해결
├── backend/
│   ├── venv/                ← 자동 생성
│   ├── .env                 ← API 키 설정
│   └── trading_bot.db       ← 자동 생성
└── frontend/
    └── node_modules/        ← 자동 생성
```

---

## 🎯 **빠른 체크리스트**

### **새 PC 설정 (5분)**
- [ ] 1. 프로젝트 다운로드
- [ ] 2. `EASY_INSTALL.bat` 실행
- [ ] 3. `backend\.env`에 API 키 입력
- [ ] 4. `START_BOT.bat` 실행
- [ ] 5. 완료! 🎉

### **문제 발생 시 (1분)**
- [ ] 1. `doctor.bat` 실행
- [ ] 2. 자동 수정 확인
- [ ] 3. 여전히 문제? → 진단 보고서 확인

---

## 💡 **자주 묻는 질문**

### **Q: 폴더명을 바꿔도 되나요?**
A: 네! 어떤 이름이든 상관없습니다.

### **Q: 다른 PC로 옮기면 다시 설치해야 하나요?**
A: 네, `EASY_INSTALL.bat`만 다시 실행하면 됩니다. (5분)

### **Q: USB에 넣고 다니면서 쓸 수 있나요?**
A: 네! 각 PC에서 한 번씩 `EASY_INSTALL.bat` 실행만 하면 됩니다.

### **Q: Python/Node.js도 자동 설치되나요?**
A: 아니요, 이 두 가지만 수동 설치 필요합니다.
   - Python: https://www.python.org/downloads/
   - Node.js: https://nodejs.org/

### **Q: 설치가 너무 오래 걸려요**
A: 정상입니다!
   - Python 패키지: 5-10분
   - Node.js 패키지: 3-5분
   - 총 10-15분 소요

### **Q: 오류 메시지가 나와요**
A: `doctor.bat` 실행 → 자동 수정!

---

## 🚨 **중요 안내**

### **보안**
- ⚠️ `.env` 파일은 절대 공유하지 마세요
- ⚠️ GitHub에 업로드하지 마세요 (자동 제외됨)
- ⚠️ API 키는 읽기 전용 권한만 주세요

### **테스트**
- ✅ 먼저 테스트넷에서 테스트하세요
- ✅ 실거래는 작은 금액부터 시작
- ✅ 정기적으로 백업하세요

---

## 📚 **더 많은 도움말**

- 📖 **QUICKSTART.md** - 빠른 시작 가이드
- 📖 **README.md** - 전체 문서
- 📖 **BALANCE_BASED_STRATEGY.md** - 잔고 기반 전략
- 📖 **AI_PERFORMANCE_ANALYSIS.md** - AI 성능 분석
- 📖 **TROUBLESHOOTING.md** - 문제 해결 가이드

---

## 🎉 **성공적인 설치!**

이제 다른 PC에서도 5분 안에 설치할 수 있습니다!

```
1. 프로젝트 다운로드
2. EASY_INSTALL.bat 클릭
3. API 키 입력
4. START_BOT.bat 클릭
5. 트레이딩 시작! 🚀
```

**문제가 있나요?**
→ `doctor.bat` 실행!
→ 자동으로 해결됩니다! ✨
