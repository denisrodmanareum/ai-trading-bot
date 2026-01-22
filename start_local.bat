@echo off
echo ===================================================
echo   AI Trading Bot - Local Launcher (Windows)
echo ===================================================
echo.

:: Check if backend directory exists
if not exist "backend" (
    echo ERROR: backend directory not found!
    echo Please run this script from the project root directory.
    pause
    exit /b 1
)

:: Check if frontend directory exists
if not exist "frontend" (
    echo ERROR: frontend directory not found!
    echo Please run this script from the project root directory.
    pause
    exit /b 1
)

:: 1. Backend Start
echo [1/2] Starting Backend Server...
start "AI Bot Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

if errorlevel 1 (
    echo ERROR: Failed to start backend!
    pause
    exit /b 1
)

echo Backend started successfully!
echo Waiting for backend to initialize...
timeout /t 5 >nul

:: 2. Frontend Start
echo.
echo [2/2] Starting Frontend Dashboard...

:: Check Node.js installation
where node >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found! Please install Node.js first.
    pause
    exit /b 1
)

:: Start frontend in separate window
start "AI Bot Frontend" cmd /k "cd /d %~dp0frontend && npm start"

if errorlevel 1 (
    echo ERROR: Failed to start frontend!
    pause
    exit /b 1
)

echo.
echo ===================================================
echo   Both servers are starting!
echo ===================================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to open the dashboard in your browser...
pause >nul

:: Open browser
start http://localhost:3000

echo.
echo To stop the servers, close both terminal windows.
echo.
