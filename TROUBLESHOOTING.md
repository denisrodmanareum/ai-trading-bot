# 🔧 문제 해결 가이드

다른 PC에서 실행 시 자주 발생하는 오류와 해결 방법

## 🚨 일반적인 오류

### 1. "Python을 찾을 수 없습니다"

**증상:**
```
'python'은(는) 내부 또는 외부 명령, 실행할 수 있는 프로그램, 또는 배치 파일이 아닙니다.
```

**해결:**
1. Python 설치: https://www.python.org/downloads/
2. 설치 시 "Add Python to PATH" 체크
3. 터미널 재시작

**확인:**
```bash
python --version  # Python 3.11.x 이상 나와야 함
```

---

### 2. "Node.js를 찾을 수 없습니다"

**증상:**
```
'node'은(는) 내부 또는 외부 명령이 아닙니다.
```

**해결:**
1. Node.js 설치: https://nodejs.org/
2. LTS 버전 선택 (현재 20.x)
3. 터미널 재시작

**확인:**
```bash
node --version  # v16.x 이상
npm --version   # 8.x 이상
```

---

### 3. "Module not found" 에러

**증상:**
```python
ModuleNotFoundError: No module named 'fastapi'
```

**해결:**
```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt
```

**npm 패키지 누락:**
```bash
cd frontend
npm install
```

---

### 4. "BINANCE_API_KEY not found" 에러

**증상:**
```
ERROR: BINANCE_API_KEY environment variable not set
```

**해결:**
1. `backend\.env` 파일 확인
2. API 키 입력:
```env
BINANCE_API_KEY=실제_API_키
BINANCE_API_SECRET=실제_시크릿_키
```

**API 키 발급:**
- 바이낸스: https://www.binance.com/en/my/settings/api-management
- 권한: "Futures Trading" 활성화
- IP 제한 설정 권장

---

### 5. "Port 8000 already in use"

**증상:**
```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)
```

**해결:**
```bash
# 포트 사용 프로세스 확인
netstat -ano | findstr :8000

# 프로세스 종료 (PID는 위 명령어에서 확인)
taskkill /PID [프로세스ID] /F
```

또는 다른 포트 사용:
```bash
cd backend
uvicorn app.main:app --reload --port 8001
```

---

### 6. "Port 3000 already in use" (React)

**해결:**
```bash
# 1. 다른 React 앱 종료
# 2. 또는 다른 포트 사용
set PORT=3001
npm start
```

---

### 7. Database 오류

**증상:**
```
sqlite3.OperationalError: no such table: trades
```

**해결:**
```bash
cd backend
venv\Scripts\activate
python manual_init_db.py
```

또는 데이터베이스 재생성:
```bash
del trading_bot.db
python manual_init_db.py
```

---

### 8. 가상환경 활성화 안 됨

**증상:**
```
pip를 찾을 수 없습니다.
```

**해결:**
```bash
cd backend
venv\Scripts\activate.bat  # Windows
# venv/bin/activate  # Mac/Linux
```

**확인:** 터미널에 `(venv)` 표시되어야 함

---

### 9. "Cannot find module 'react'" (Frontend)

**해결:**
```bash
cd frontend
rmdir /s /q node_modules  # 기존 삭제
rmdir /s /q package-lock.json
npm cache clean --force
npm install
```

---

### 10. "Leverage change failed" (Binance)

**증상:**
```
DEBUG: Leverage change skipped for BTCUSDT: APIError(code=-1000)
```

**설명:**
- ⚠️ 이것은 에러가 아닙니다!
- 포지션이 열려있을 때 레버리지를 변경할 수 없음
- 봇이 현재 레버리지로 계속 거래함
- 정상 작동

---

## 🔍 디버깅 팁

### 백엔드 로그 확인
```bash
cd backend
python -m uvicorn app.main:app --reload --log-level debug
```

### 프론트엔드 디버그
1. 브라우저 F12 (개발자 도구)
2. Console 탭 확인
3. Network 탭에서 API 요청 확인

### 의존성 문제 해결
```bash
# Python 패키지 완전 재설치
cd backend
pip uninstall -r requirements.txt -y
pip install -r requirements.txt

# Node 패키지 완전 재설치
cd frontend
rmdir /s /q node_modules
npm install
```

---

## 🆘 여전히 안 되면?

### 1. 완전 초기화

```bash
# 1. 가상환경 삭제
rmdir /s /q backend\venv

# 2. node_modules 삭제
rmdir /s /q frontend\node_modules

# 3. 데이터베이스 삭제
del backend\trading_bot.db

# 4. 자동 설치 재실행
setup.bat
```

### 2. 로그 확인

**백엔드 로그:**
- `backend/data/logs/` 폴더 확인

**에러 메시지 복사:**
- 전체 에러 스택 트레이스 복사
- GitHub Issues에 올리기

### 3. 시스템 요구사항 재확인

- ✅ Windows 10 이상
- ✅ Python 3.11 이상
- ✅ Node.js 16 이상
- ✅ 최소 4GB RAM
- ✅ 2GB 이상 디스크 공간

---

## 📞 도움 받기

1. **GitHub Issues:**
   https://github.com/denisrodmanareum/ai-trading-bot/issues

2. **체크리스트 준비:**
   - [ ] 운영체제 버전
   - [ ] Python 버전 (`python --version`)
   - [ ] Node.js 버전 (`node --version`)
   - [ ] 전체 에러 메시지
   - [ ] 어떤 단계에서 오류 발생
   - [ ] 시도한 해결 방법

3. **자주 확인할 파일:**
   - `backend/.env` - API 키 설정
   - `backend/requirements.txt` - Python 패키지
   - `frontend/package.json` - Node 패키지
   - `QUICKSTART.md` - 설치 가이드

---

## ✅ 정상 작동 확인

### 백엔드
```bash
# http://localhost:8000/health 접속
# Response: {"status":"healthy"}
```

### 프론트엔드
```bash
# http://localhost:3000 접속
# 대시보드가 보여야 함
```

### API 연결
```bash
# 대시보드에서 "OFFLINE" 표시 없어야 함
# 차트가 정상적으로 로드되어야 함
```

---

**모든 것이 정상이면 이제 거래를 시작하세요!** 🚀

⚠️ **주의:** 테스트넷에서 충분히 테스트 후 실거래를 시작하세요!
