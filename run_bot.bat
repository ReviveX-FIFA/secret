@echo off
echo Checking for Python 3.11...
where py >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python launcher not found. Please install Python from python.org
    pause
    exit /b 1
)

echo Testing Python 3.11 availability...
py -3.11 --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python 3.11 not installed. Please run install_python311_auto.bat first
    pause
    exit /b 1
)

echo Python 3.11 found! Starting Twitch bot...
echo.
py -3.11 main.py
pause
