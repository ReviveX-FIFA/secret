@echo off
echo Starting Twitch Chat Bot (Clean Mode)...
echo.

REM Kill any existing Python processes that might be Discord bot
taskkill /f /im python.exe 2>nul
taskkill /f /im py.exe 2>nul

REM Wait a moment for processes to terminate
timeout /t 2 /nobreak >nul

REM Start only the chat bot
cd chat
py -3.11 chat_standalone.py
cd ..

pause
