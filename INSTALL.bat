@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   ANGEL AREUM AI BOT - Easy Installation Script
echo ===================================================
echo.

:: Check Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed. Please install Node.js (v16+) first.
    pause
    exit /b 1
)
echo [OK] Node.js found.

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed. Please install Python (3.11+) first.
    pause
    exit /b 1
)
echo [OK] Python found.

echo.
echo ---------------------------------------------------
echo   1. Backend Setup (Virtual Environment & Deps)
echo ---------------------------------------------------
cd backend
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Installing backend dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install backend dependencies.
    pause
    exit /b 1
)
cd ..

echo.
echo ---------------------------------------------------
echo   2. Frontend Setup (NPM Install)
echo ---------------------------------------------------
cd frontend
echo Installing frontend dependencies (this may take a few minutes)...
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install frontend dependencies.
    pause
    exit /b 1
)
cd ..

echo.
echo ---------------------------------------------------
echo   3. Environment Configuration
echo ---------------------------------------------------
if not exist "backend\.env" (
    if exist ".env.example" (
        echo Creating .env from .env.example...
        copy .env.example backend\.env
        echo [IMPORTANT] Please edit backend\.env and add your Binance API keys.
    ) else (
        echo [WARNING] .env.example not found. You will need to create backend\.env manually.
    )
) else (
    echo [OK] backend\.env already exists.
)

echo.
echo ===================================================
echo   INSTALLATION COMPLETE!
echo ===================================================
echo.
echo Now you can run the bot using 'start_local.bat'
echo.
pause
