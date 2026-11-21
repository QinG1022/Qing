@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY=C:\Users\14426\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
set "PYTHONPATH=%~dp0pydeps"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if not exist "%PY%" (
    echo [ERROR] python not found: %PY%
    pause
    exit /b 1
)

"%PY%" check.py
echo.
echo ---- done ----
pause >nul