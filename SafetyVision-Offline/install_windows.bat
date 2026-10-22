@echo off
setlocal
cd /d "%~dp0"
py -3.12 --version >nul 2>nul
if errorlevel 1 (
  py -3.11 --version >nul 2>nul
  if errorlevel 1 (
    echo Python 3.11 or 3.12 x64 is required.
    pause
    exit /b 1
  )
  py -3.11 -m venv .venv
) else (
  py -3.12 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto fail
python -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo Next run install_model.bat once with internet.
pause
exit /b 0
:fail
echo Installation failed. See the error above.
pause
exit /b 1
