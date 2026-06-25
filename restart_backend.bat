@echo off
chcp 65001 >nul
title Restart Backend - WorldCup 2026

set LOG=%~dp0backend\uvicorn_9000.log

echo ========================================
echo   Stopping backend on port 9000...
echo ========================================
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":9000 "') do (
    echo   Killing PID %%a
    taskkill /F /PID %%a >nul 2>&1
)
ping 127.0.0.1 -n 4 >nul

echo.
echo ========================================
echo   Starting backend on port 9000...
echo ========================================
cd /d "%~dp0backend"
start "" /B cmd /c "%~dp0.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 9000 > %LOG% 2>&1"

echo.
echo Waiting for backend to start...
setlocal enabledelayedexpansion
set /a retries=0
:wait_backend
ping 127.0.0.1 -n 4 >nul
set /a retries+=1
netstat -ano | findstr ":9000 " >nul 2>&1
if errorlevel 1 (
    echo   retry !retries!: port not up yet
    if !retries! lss 15 goto wait_backend
    echo [FAIL] Backend did not start within 60 seconds.
    echo        Check %LOG% for details.
    type "%LOG%" 2>nul
    pause
    exit /b 1
)
echo [OK] Port 9000 is listening.

ping 127.0.0.1 -n 3 >nul
curl -s -o nul -w "%%{http_code}" http://localhost:9000/openapi.json > "%TEMP%\backend_check.txt" 2>&1
set /p http_code=<"%TEMP%\backend_check.txt"
del "%TEMP%\backend_check.txt" 2>nul
if "%http_code%"=="200" (
    echo [OK] API responds with HTTP 200.
    echo.
    echo Backend is ready: http://localhost:9000/docs
) else (
    echo [WARN] Port is listening but API returned HTTP %http_code%.
    echo        Check %LOG% for details.
)
echo.
pause
