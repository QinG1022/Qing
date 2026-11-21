@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY=C:\Users\14426\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
set "PYTHONPATH=%~dp0pydeps"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "QING_PORT=5000"

echo Collecting startup info into startup.log ...

echo ==== python version ==== > startup.log
"%PY%" -V >> startup.log 2>&1
echo. >> startup.log
echo ==== import app ==== >> startup.log
"%PY%" -c "import app; print('import ok')" >> startup.log 2>&1
echo. >> startup.log
echo ==== run app.py for 15s ==== >> startup.log
start /b "" "%PY%" app.py >> startup.log 2>&1
timeout /t 15 /nobreak >nul
taskkill /f /im python.exe >nul 2>&1
echo. >> startup.log
echo ==== done ==== >> startup.log

type startup.log
echo.
echo Saved to startup.log
pause