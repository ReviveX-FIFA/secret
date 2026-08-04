@echo off
echo Starting Pure Twitch Chat Bot...
echo.

REM Kill ALL Python processes multiple times
for /l %%i in (1,1,3) do (
    taskkill /f /im python.exe >nul 2>&1
    taskkill /f /im py.exe >nul 2>&1
    taskkill /f /im python3.exe >nul 2>&1
    taskkill /f /im python3.11.exe >nul 2>&1
    timeout /t 1 /nobreak >nul
)

REM Block Discord bot completely
if exist "discord_bot.py" (
    move "discord_bot.py" "discord_bot.py.blocked" >nul 2>&1
)

REM Also block main.py if it might start Discord bot
if exist "main.py" (
    move "main.py" "main.py.blocked" >nul 2>&1
)

echo Starting isolated chat bot...
cd chat
py -3.11 chat_standalone.py %*
cd ..

REM Restore files
if exist "discord_bot.py.blocked" (
    move "discord_bot.py.blocked" "discord_bot.py" >nul 2>&1
)
if exist "main.py.blocked" (
    move "main.py.blocked" "main.py" >nul 2>&1
)

pause
