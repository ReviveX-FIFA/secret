@echo off
echo Starting Twitch Chat Bot (Isolated Mode)...
echo.

REM Kill ALL Python processes aggressively
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im py.exe >nul 2>&1
taskkill /f /im python3.exe >nul 2>&1
taskkill /f /im python3.11.exe >nul 2>&1

REM Wait for processes to terminate completely
timeout /t 3 /nobreak >nul

REM Block Discord bot from starting by renaming it temporarily
if exist "discord_bot.py" (
    ren "discord_bot.py" "discord_bot.py.disabled"
    echo Discord bot temporarily disabled
)

REM Start the standalone chat bot
cd chat
py -3.11 chat_standalone.py
cd ..

REM Restore Discord bot when done
if exist "discord_bot.py.disabled" (
    ren "discord_bot.py.disabled" "discord_bot.py"
    echo Discord bot restored
)

pause
