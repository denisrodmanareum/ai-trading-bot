@echo off
chcp 65001 >nul
setlocal

echo ===================================================
echo   AI Trading Bot - Doctor (Windows)
echo ===================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found.
  echo Please install Python 3.11+ and re-run.
  pause
  exit /b 1
)

python "%~dp0doctor.py"

echo.
echo ===================================================
echo   Done
echo ===================================================
pause

