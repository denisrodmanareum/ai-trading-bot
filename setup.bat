@echo off
chcp 65001 >nul
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║          AI 트레이딩 봇 - 자동 설치 스크립트                  ║
echo ║                   v4.0 Setup Wizard                            ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

:: Check Python
echo [1/8] Python 확인 중...
where python >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python이 설치되어 있지 않습니다!
    echo.
    echo Python 3.11 이상을 설치해주세요:
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo ✅ Python 확인 완료
echo.

:: Check Node.js
echo [2/8] Node.js 확인 중...
where node >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Node.js가 설치되어 있지 않습니다!
    echo.
    echo Node.js 16 이상을 설치해주세요:
    echo https://nodejs.org/
    pause
    exit /b 1
)

node --version
npm --version
echo ✅ Node.js 확인 완료
echo.

:: Backend Setup
echo [3/8] 백엔드 가상환경 생성 중...
cd backend

if exist venv (
    echo ⚠️  가상환경이 이미 존재합니다. 건너뜁니다.
) else (
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 가상환경 생성 실패!
        pause
        exit /b 1
    )
    echo ✅ 가상환경 생성 완료
)
echo.

:: Activate venv and install dependencies
echo [4/8] Python 패키지 설치 중... (5-10분 소요)
call venv\Scripts\activate.bat

echo 필수 패키지 설치 중...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ 패키지 설치 실패!
    echo.
    echo 수동으로 실행해보세요:
    echo   cd backend
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)
echo ✅ Python 패키지 설치 완료
echo.

:: Create .env file
echo [5/8] 환경 변수 파일 생성 중...
if exist .env (
    echo ⚠️  .env 파일이 이미 존재합니다.
) else (
    (
        echo # Binance API Configuration
        echo BINANCE_API_KEY=your_api_key_here
        echo BINANCE_API_SECRET=your_api_secret_here
        echo BINANCE_TESTNET=True
        echo.
        echo # Database
        echo DATABASE_URL=sqlite:///./trading_bot.db
        echo.
        echo # AI Settings
        echo DEFAULT_LEVERAGE=5
        echo MAX_LEVERAGE=125
    ) > .env
    
    echo ✅ .env 파일 생성 완료
    echo.
    echo ⚠️  중요: backend\.env 파일을 열어서 API 키를 입력하세요!
    echo.
)

:: Initialize Database
echo [6/8] 데이터베이스 초기화 중...
if exist trading_bot.db (
    echo ⚠️  데이터베이스가 이미 존재합니다. 건너뜁니다.
) else (
    python manual_init_db.py >nul 2>&1
    if errorlevel 1 (
        echo ⚠️  데이터베이스 초기화 실패 (자동 생성됩니다)
    ) else (
        echo ✅ 데이터베이스 초기화 완료
    )
)
echo.

cd ..

:: Frontend Setup
echo [7/8] 프론트엔드 패키지 설치 중... (3-5분 소요)
cd frontend

if exist node_modules (
    echo ⚠️  node_modules가 이미 존재합니다. 건너뜁니다.
    echo    재설치하려면 'npm install'을 실행하세요.
) else (
    echo npm install 실행 중...
    call npm install
    
    if errorlevel 1 (
        echo ❌ npm 패키지 설치 실패!
        pause
        exit /b 1
    )
    echo ✅ 프론트엔드 패키지 설치 완료
)
echo.

cd ..

:: Create initial model directory
echo [8/8] 초기 설정 완료 중...
if not exist backend\data\models mkdir backend\data\models
if not exist backend\data\logs mkdir backend\data\logs
if not exist backend\data\reviews mkdir backend\data\reviews

echo ✅ 디렉토리 구조 생성 완료
echo.

:: Final Instructions
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                    설치 완료! 🎉                               ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 📋 다음 단계:
echo.
echo 1. backend\.env 파일을 열어서 바이낸스 API 키를 입력하세요
echo    BINANCE_API_KEY=실제_API_키
echo    BINANCE_API_SECRET=실제_시크릿_키
echo.
echo 2. 봇을 실행하세요:
echo    start_local.bat
echo.
echo 3. 브라우저에서 http://localhost:3000 접속
echo.
echo 4. AI 허브에서 모델을 학습하세요 (선택사항)
echo.
echo ⚠️  주의사항:
echo    - 테스트넷에서 먼저 테스트하세요 (BINANCE_TESTNET=True)
echo    - 실거래 시 작은 금액부터 시작하세요
echo    - API 키는 절대 공유하지 마세요
echo.
echo 📚 도움말:
echo    - QUICKSTART.md - 빠른 시작 가이드
echo    - README.md - 전체 문서
echo    - GITHUB_UPLOAD.md - 업로드 가이드
echo.
echo ════════════════════════════════════════════════════════════════
echo.

pause
