@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if not errorlevel 1 (
  start "AI Router Backend" cmd /k "cd /d ""%~dp0"" && py -3 backend\server.py"
) else (
  start "AI Router Backend" cmd /k "cd /d ""%~dp0"" && python backend\server.py"
)

timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8765"
endlocal
