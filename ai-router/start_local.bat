@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if not errorlevel 1 (
  start "AI Router Backend" /D "%~dp0" cmd /k "py -3 backend\server.py"
) else (
  start "AI Router Backend" /D "%~dp0" cmd /k "python backend\server.py"
)

timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8765"
endlocal
