@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================
::  AI Trading Bot - 통합 자동 설치 스크립트
::  모든 PC에서 원클릭 설치 가능!
:: ============================================================

title AI Trading Bot - Easy Install

:: 현재 스크립트 위치를 프로젝트 루트로 설정 (폴더명 무관)
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                                                                  ║
echo ║        🚀 AI Trading Bot - 원클릭 자동 설치 🚀                  ║
echo ║                                                                  ║
echo ║     어떤 PC에서든, 어떤 폴더명이든 자동으로 설치됩니다!        ║
echo ║                                                                  ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo 📁 설치 경로: %PROJECT_ROOT%
echo.
timeout /t 2 >nul

:: ============================================================
::  Step 1: 시스템 요구사항 자동 검사 및 설치 안내
:: ============================================================
echo ═══════════════════════════════════════════════════════════════════
echo [1/10] 시스템 요구사항 검사 중...
echo ═══════════════════════════════════════════════════════════════════
echo.

set "MISSING_DEPS="
set "PYTHON_OK=0"
set "NODE_OK=0"

:: Python 검사
echo [1-1] Python 확인 중...
where python >nul 2>&1
if errorlevel 1 (
    echo     ❌ Python이 설치되어 있지 않습니다!
    set "MISSING_DEPS=!MISSING_DEPS! Python"
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
    echo     ✅ Python !PYTHON_VER! 설치됨
    set "PYTHON_OK=1"
)

:: Node.js 검사
echo [1-2] Node.js 확인 중...
where node >nul 2>&1
if errorlevel 1 (
    echo     ❌ Node.js가 설치되어 있지 않습니다!
    set "MISSING_DEPS=!MISSING_DEPS! Node.js"
) else (
    for /f "tokens=1" %%i in ('node --version 2^>^&1') do set NODE_VER=%%i
    echo     ✅ Node.js !NODE_VER! 설치됨
    set "NODE_OK=1"
)

:: Git 검사 (선택사항)
echo [1-3] Git 확인 중...
where git >nul 2>&1
if errorlevel 1 (
    echo     ⚠️  Git이 설치되어 있지 않습니다 (선택사항)
) else (
    for /f "tokens=3" %%i in ('git --version 2^>^&1') do set GIT_VER=%%i
    echo     ✅ Git !GIT_VER! 설치됨
)

echo.

:: 필수 프로그램 미설치 시 자동 설치 안내
if not "%MISSING_DEPS%"=="" (
    echo ══════════════════════════════════════════════════════════════════
    echo ❌ 설치 중단: 필수 프로그램이 설치되어 있지 않습니다!
    echo ══════════════════════════════════════════════════════════════════
    echo.
    echo 다음 프로그램을 설치해주세요:!MISSING_DEPS!
    echo.
    
    if "!PYTHON_OK!"=="0" (
        echo 📦 Python 3.11 이상:
        echo    https://www.python.org/downloads/
        echo    ※ 설치 시 "Add Python to PATH" 체크 필수!
        echo.
    )
    
    if "!NODE_OK!"=="0" (
        echo 📦 Node.js 16 이상:
        echo    https://nodejs.org/
        echo    ※ LTS 버전 권장
        echo.
    )
    
    echo 설치 후 이 스크립트를 다시 실행하세요.
    echo.
    pause
    exit /b 1
)

echo ✅ 시스템 요구사항 충족!
timeout /t 1 >nul
echo.

:: ============================================================
::  Step 2: 프로젝트 구조 검사
:: ============================================================
echo ═══════════════════════════════════════════════════════════════════
echo [2/10] 프로젝트 구조 검사 중...
echo ═══════════════════════════════════════════════════════════════════
echo.

if not exist "backend" (
    echo ❌ backend 폴더가 없습니다!
    echo 프로젝트가 올바르게 다운로드되지 않았습니다.
    pause
    exit /b 1
)

if not exist "frontend" (
    echo ❌ frontend 폴더가 없습니다!
    echo 프로젝트가 올바르게 다운로드되지 않았습니다.
    pause
    exit /b 1
)

echo ✅ 프로젝트 구조 정상
echo.

:: ============================================================
::  Step 3: 기존 설치 정리 (선택)
:: ============================================================
echo ═══════════════════════════════════════════════════════════════════
echo [3/10] 기존 설치 확인 중...
echo ═══════════════════════════════════════════════════════════════════
echo.

if exist "backend\venv" (
    echo ⚠️  기존 Python 가상환경이 발견되었습니다.
    echo.
    set /p "REINSTALL=재설치하시겠습니까? (Y/N): "
    if /i "!REINSTALL!"=="Y" (
        echo 기존 가상환경 삭제 중...
        rmdir /s /q "backend\venv" 2>nul
        echo ✅ 삭제 완료
    ) else (
        echo ℹ️  기존 가상환경 유지
    )
) else (
    echo ℹ️  새로운 설치
)

if exist "frontend\node_modules" (
    echo.
    echo ⚠️  기존 Node.js 패키지가 발견되었습니다.
    set /p "REINSTALL_NODE=재설치하시겠습니까? (Y/N): "
    if /i "!REINSTALL_NODE!"=="Y" (
        echo 기존 node_modules 삭제 중...
        rmdir /s /q "frontend\node_modules" 2>nul
        echo ✅ 삭제 완료
    ) else (
        echo ℹ️  기존 패키지 유지
    )
)

echo.

:: ============================================================
::  Step 4: 백엔드 가상환경 생성
:: ============================================================
echo ═══════════════════════════════════════════════════════════════════
echo [4/10] 백엔드 가상환경 생성 중...
echo ═══════════════════════════════════════════════════════════════════
echo.

cd backend

if not exist "venv" (
    echo Python 가상환경 생성 중... (1-2분 소요)
    python -m venv venv
    
    if errorlevel 1 (
        echo ❌ 가상환경 생성 실패!
        echo.
        echo 해결 방법:
        echo 1. Python이 제대로 설치되었는지 확인
        echo 2. 관리자 권한으로 실행
        echo 3. 바이러스 백신이 차단하는지 확인
        pause
        exit /b 1
    )
    
    echo ✅ 가상환경 생성 완료
) else (
    echo ℹ️  가상환경이 이미 존재합니다
)

echo.

:: ============================================================
::  Step 5: Python 패키지 설치 (자동 재시도)
:: ============================================================
echo ═══════════════════════════════════════════════════════════════════
echo [5/10] Python 패키지 설치 중... (5-10분 소요)
echo ═══════════════════════════════════════════════════════════════════
echo.

call venv\Scripts\activate.bat

echo [5-1] pip 업그레이드 중...
python -m pip install --upgrade pip --quiet

echo [5-2] 필수 패키지 설치 중...
echo      (진행 상황: 터미널 아래쪽 확인)
echo.

set "RETRY_COUNT=0"
set "MAX_RETRIES=3"

:INSTALL_BACKEND_DEPS
pip install -r requirements.txt

if errorlevel 1 (
    set /a RETRY_COUNT+=1
    echo.
    echo ⚠️  설치 실패! (시도 !RETRY_COUNT!/%MAX_RETRIES%)
    
    if !RETRY_COUNT! lss %MAX_RETRIES% (
        echo 5초 후 재시도합니다...
        timeout /t 5 >nul
        goto INSTALL_BACKEND_DEPS
    ) else (
        echo.
        echo ❌ Python 패키지 설치 실패!
        echo.
        echo 수동 설치 방법:
        echo   1. cd backend
        echo   2. venv\Scripts\activate
        echo   3. pip install -r requirements.txt
        echo.
        echo 오류 내용을 복사해서 ChatGPT에 물어보세요!
        pause
        exit /b 1
    )
)

echo.
echo ✅ Python 패키지 설치 완료
echo.

cd ..

:: ============================================================
::  Step 6: 환경 변수 파일 생성
:: ============================================================
echo ═══════════════════════════════════════════════════════════════════
echo [6/10] 환경 변수 파일 생성 중...
echo ═══════════════════════════════════════════════════════════════════
echo.

if exist "backend\.env" (
    echo ℹ️  .env 파일이 이미 존재합니다
    echo     (기존 설정 유지)
) else (
    echo .env 파일 생성 중...
    (
        echo # ══════════════════════════════════════════════════════════
        echo # Binance API Configuration
        echo # ══════════════════════════════════════════════════════════
        echo BINANCE_API_KEY=your_api_key_here
        echo BINANCE_API_SECRET=your_api_secret_here
        echo BINANCE_TESTNET=True
        echo.
        echo # ══════════════════════════════════════════════════════════
        echo # Exchange Selection
        echo # ══════════════════════════════════════════════════════════
        echo ACTIVE_EXCHANGE=BINANCE
        echo.
        echo # ══════════════════════════════════════════════════════════
        echo # Database
        echo # ══════════════════════════════════════════════════════════
        echo DATABASE_URL=sqlite:///./trading_bot.db
        echo.
        echo # ══════════════════════════════════════════════════════════
        echo # AI Settings
        echo # ══════════════════════════════════════════════════════════
        echo DEFAULT_LEVERAGE=5
        echo MAX_LEVERAGE=125
        echo.
        echo # ══════════════════════════════════════════════════════════
        echo # Trading Mode
        echo # ══════════════════════════════════════════════════════════
        echo TRADING_MODE=SCALP
        echo.
        echo # ══════════════════════════════════════════════════════════
        echo # Risk Management
        echo # ══════════════════════════════════════════════════════════
        echo DAILY_LOSS_LIMIT=25
        echo MAX_MARGIN_LEVEL=0.8
        echo.
    ) > backend\.env
    
    echo ✅ .env 파일 생성 완료
)

echo.

:: ============================================================
::  Step 7: 데이터베이스 초기화
:: ============================================================
echo ═══════════════════════════════════════════════════════════════════
echo [7/10] 데이터베이스 초기화 중...
echo ═══════════════════════════════════════════════════════════════════
echo.

cd backend

if exist "trading_bot.db" (
    echo ℹ️  데이터베이스가 이미 존재합니다
) else (
    echo 데이터베이스 초기화 중...
    call venv\Scripts\activate.bat
    python manual_init_db.py >nul 2>&1
    
    if errorlevel 1 (
        echo ⚠️  초기화 실패 (봇 실행 시 자동 생성됩니다)
    ) else (
        echo ✅ 데이터베이스 초기화 완료
    )
)

echo.

cd ..

:: ============================================================
::  Step 8: 프론트엔드 패키지 설치 (자동 재시도)
:: ============================================================
echo ═══════════════════════════════════════════════════════════════════
echo [8/10] 프론트엔드 패키지 설치 중... (3-5분 소요)
echo ═══════════════════════════════════════════════════════════════════
echo.

cd frontend

if exist "node_modules" (
    echo ℹ️  node_modules가 이미 존재합니다
    echo     (재설치하려면 3단계에서 Y를 선택하세요)
) else (
    echo npm install 실행 중...
    echo (진행 상황: 터미널 아래쪽 확인)
    echo.
    
    set "NPM_RETRY=0"
    
    :INSTALL_NPM_DEPS
    call npm install
    
    if errorlevel 1 (
        set /a NPM_RETRY+=1
        echo.
        echo ⚠️  npm 설치 실패! (시도 !NPM_RETRY!/3)
        
        if !NPM_RETRY! lss 3 (
            echo npm 캐시 정리 후 재시도...
            call npm cache clean --force >nul 2>&1
            timeout /t 3 >nul
            goto INSTALL_NPM_DEPS
        ) else (
            echo.
            echo ❌ 프론트엔드 패키지 설치 실패!
            echo.
            echo 수동 설치 방법:
            echo   1. cd frontend
            echo   2. npm cache clean --force
            echo   3. npm install
            echo.
            pause
            exit /b 1
        )
    )
    
    echo.
    echo ✅ 프론트엔드 패키지 설치 완료
)

echo.

cd ..

:: ============================================================
::  Step 9: 디렉토리 구조 생성
:: ============================================================
echo ═══════════════════════════════════════════════════════════════════
echo [9/10] 디렉토리 구조 생성 중...
echo ═══════════════════════════════════════════════════════════════════
echo.

if not exist "backend\data\models" mkdir "backend\data\models"
if not exist "backend\data\logs" mkdir "backend\data\logs"
if not exist "backend\data\reviews" mkdir "backend\data\reviews"
if not exist "backend\data\tensorboard" mkdir "backend\data\tensorboard"

echo ✅ 디렉토리 구조 생성 완료
echo.

:: ============================================================
::  Step 10: 바로가기 스크립트 생성
:: ============================================================
echo ═══════════════════════════════════════════════════════════════════
echo [10/10] 바로가기 스크립트 생성 중...
echo ═══════════════════════════════════════════════════════════════════
echo.

:: 빠른 시작 스크립트 생성
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo title AI Trading Bot
    echo.
    echo :: 현재 스크립트 위치에서 프로젝트 루트 찾기
    echo set "PROJECT_ROOT=%%~dp0"
    echo cd /d "%%PROJECT_ROOT%%"
    echo.
    echo echo 🚀 AI Trading Bot 시작 중...
    echo echo.
    echo.
    echo :: 백엔드 시작
    echo start "Backend" cmd /k "cd backend && venv\Scripts\activate && python app/main.py"
    echo.
    echo :: 2초 대기
    echo timeout /t 2 ^>nul
    echo.
    echo :: 프론트엔드 시작
    echo start "Frontend" cmd /k "cd frontend && npm start"
    echo.
    echo echo ✅ 백엔드와 프론트엔드가 시작되었습니다!
    echo echo.
    echo echo 📱 브라우저가 자동으로 열립니다...
    echo echo    수동 접속: http://localhost:3000
    echo echo.
    echo echo 종료하려면 두 터미널 창을 모두 닫으세요.
    echo echo.
    echo pause
) > "START_BOT.bat"

echo ✅ START_BOT.bat 생성 완료
echo.

:: ============================================================
::  설치 완료!
:: ============================================================
echo.
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                                                                  ║
echo ║                  ✅ 설치 완료! 🎉                               ║
echo ║                                                                  ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo ═══════════════════════════════════════════════════════════════════
echo  📋 다음 단계
echo ═══════════════════════════════════════════════════════════════════
echo.
echo  1️⃣  API 키 설정 (필수!)
echo      📝 backend\.env 파일을 열어서:
echo         BINANCE_API_KEY=실제_API_키
echo         BINANCE_API_SECRET=실제_시크릿_키
echo.
echo  2️⃣  봇 실행
echo      🚀 START_BOT.bat 더블클릭 또는
echo         start_local.bat 실행
echo.
echo  3️⃣  브라우저 접속
echo      🌐 http://localhost:3000
echo.
echo  4️⃣  AI 학습 (선택사항)
echo      📚 AI 허브 탭에서 모델 학습
echo.
echo ═══════════════════════════════════════════════════════════════════
echo  ⚠️  중요 안내
echo ═══════════════════════════════════════════════════════════════════
echo.
echo  ✓ 테스트넷에서 먼저 테스트하세요 (BINANCE_TESTNET=True)
echo  ✓ 실거래는 작은 금액부터 시작하세요
echo  ✓ API 키는 절대 공유하지 마세요
echo  ✓ 정기적으로 백업하세요
echo.
echo ═══════════════════════════════════════════════════════════════════
echo  📚 도움말
echo ═══════════════════════════════════════════════════════════════════
echo.
echo  📖 QUICKSTART.md - 빠른 시작 가이드
echo  📖 README.md - 전체 문서
echo  📖 BALANCE_BASED_STRATEGY.md - 잔고 기반 전략
echo  📖 AI_PERFORMANCE_ANALYSIS.md - AI 성능 분석
echo.
echo  🐛 문제 발생 시:
echo     doctor.bat 실행 - 자동 진단
echo.
echo ═══════════════════════════════════════════════════════════════════
echo.
echo 설치 경로: %PROJECT_ROOT%
echo.
echo 이 창을 닫으셔도 됩니다.
echo.
pause
