@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY=C:\Users\14426\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
set "PYTHONPATH=%~dp0pydeps"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if "%QING_PORT%"=="" set "QING_PORT=5000"

echo ============================================================
echo  Qing starting...
echo    python : %PY%
echo    deps   : %~dp0pydeps
echo    open   : http://127.0.0.1:%QING_PORT%
echo ============================================================
echo.

if not exist "%PY%" goto nopython
if not exist "%~dp0pydeps" goto nodeps

"%PY%" app.py
set "CODE=%ERRORLEVEL%"
echo.
echo ------------------------------------------------------------
echo  exited with code %CODE%
if not "%CODE%"=="0" echo  startup failed, scroll up for the error.
goto end

:nopython
echo [ERROR] python not found: %PY%
goto end

:nodeps
echo [ERROR] pydeps missing. run:
echo   "%PY%" -m pip install --target pydeps -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
goto end

:end
pause