@echo off
title Sivi AI Server
echo ===================================================
echo Sivi AI - Development Server
echo ===================================================

cd /d "%~dp0"

echo [1/3] Checking frontend build...
if not exist "frontend\dist" (
    echo Building React frontend for the first time...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

echo [2/3] Checking Python virtual environment...
if not exist "backend\venv" (
    echo Creating Python venv...
    python -m venv backend\venv
    echo Installing backend dependencies...
    backend\venv\Scripts\pip install -r backend\requirements.txt
)

echo [3/3] Starting Sivi...
echo Sivi will automatically open in your browser at http://localhost:8000
timeout /t 2 >nul
start http://localhost:8000

echo.
echo Press CTRL+C to stop the server.
echo.
echo Starting Background Monitor...
start /b backend\venv\Scripts\python.exe backend\core\background_monitor.py

backend\venv\Scripts\python.exe backend\bridge_server.py

pause
