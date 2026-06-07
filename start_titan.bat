@echo off
title TITAN AI — Advanced Voice Assistant
color 0b

echo.
echo  ████████╗██╗████████╗ █████╗ ███╗   ██╗
echo  ╚══██╔══╝██║╚══██╔══╝██╔══██╗████╗  ██║
echo     ██║   ██║   ██║   ███████║██╔██╗ ██║
echo     ██║   ██║   ██║   ██╔══██║██║╚██╗██║
echo     ██║   ██║   ██║   ██║  ██║██║ ╚████║
echo     ╚═╝   ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝
echo.
echo  Advanced Voice Assistant System
echo  ================================================
echo.

echo [1/4] Freeing Port 8000 (Backend Bridge Server)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /f /pid %%a 2>nul
)

echo [2/4] Freeing Port 5173 (Frontend Dashboard)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /f /pid %%a 2>nul
)

echo [3/4] Killing old Node.js processes...
taskkill /f /im node.exe 2>nul

echo [4/4] Killing lingering Python processes...
wmic process where "name='python.exe' and commandline like '%%Wake_Word%%'" call terminate >nul 2>&1
wmic process where "name='python.exe' and commandline like '%%background_monitor%%'" call terminate >nul 2>&1
wmic process where "name='python.exe' and commandline like '%%bridge_server%%'" call terminate >nul 2>&1

echo.
echo Waiting 2 seconds for ports to clear...
ping -n 3 127.0.0.1 >nul

echo.
echo ================================================
echo  Launching TITAN AI Services
echo ================================================
echo.

echo Starting Backend Bridge Server (Port 8000)...
start "TITAN Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\python bridge_server.py"

echo Waiting for backend to initialize...
ping -n 5 127.0.0.1 >nul

echo Starting Wake Word Listener...
start "TITAN WakeWord" cmd /k "cd /d %~dp0backend && venv\Scripts\python core\Wake_Word_detection.py"

echo Starting Proactive Background Monitor...
start "TITAN Background" cmd /k "cd /d %~dp0backend && venv\Scripts\python core\background_monitor.py"

echo Starting Frontend Dashboard (Port 5173)...
start "TITAN Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ================================================
echo   All systems GO!
echo   Dashboard: http://localhost:5173
echo   API:       http://localhost:8000
echo   Docs:      http://localhost:8000/docs
echo ================================================
echo.
echo  Voice Commands Ready:
echo  - Say wake word to activate
echo  - "Hey Jarvis" or custom wake word
echo  - Or use the dashboard at localhost:5173
echo.
ping -n 5 127.0.0.1 >nul
