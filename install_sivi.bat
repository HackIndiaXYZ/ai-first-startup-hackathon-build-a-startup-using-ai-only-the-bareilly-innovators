@echo off
title SIVI AI Setup
color 0A

echo ================================================
echo  SIVI AI Installer (Windows)
echo ================================================
echo.

echo [1/4] Checking prerequisites...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH! Please install Python.
    pause
    exit /b
)

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo Node.js/npm is not installed or not in PATH! Please install Node.js.
    pause
    exit /b
)

echo [2/4] Setting up Python virtual environment...
cd /d %~dp0backend
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo [3/4] Installing Frontend dependencies...
cd /d %~dp0frontend
call npm install

echo [4/4] Creating Desktop Shortcut...
cd /d %~dp0
set SCRIPT="%TEMP%\CreateShortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > %SCRIPT%
echo sLinkFile = oWS.ExpandEnvironmentStrings("%USERPROFILE%\Desktop\SIVI AI.lnk") >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "%~dp0start_sivi.bat" >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%
cscript /nologo %SCRIPT%
del %SCRIPT%

echo.
echo ================================================
echo  Setup Complete! 
echo  You can now launch SIVI AI from your desktop.
echo ================================================
pause
