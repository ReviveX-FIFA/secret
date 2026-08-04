@echo off
echo Testing Final Chat Bot Fix...
echo.

REM Kill any existing Python processes
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im py.exe >nul 2>&1

REM Temporarily disable Discord bot
if exist "discord_bot.py" (
    ren "discord_bot.py" "discord_bot.py.disabled"
    echo Discord bot temporarily disabled for testing
)

echo.
echo Starting isolated chat bot test...
echo The chat bot should now:
echo 1. NOT show any Discord bot startup messages
echo 2. NOT show any log messages like "[+] Log sent to..."
echo 3. Accept channel name input without interference
echo 4. Work completely isolated
echo.
cd chat
py -3.11 chat_standalone.py
cd ..

REM Restore Discord bot
if exist "discord_bot.py.disabled" (
    ren "discord_bot.py.disabled" "discord_bot.py"
    echo Discord bot restored
)

pause
