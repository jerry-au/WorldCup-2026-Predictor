@echo off
chcp 65001 >nul
title Restart Frontend - WorldCup 2026

echo ========================================
echo   Stopping frontend on port 9001...
echo ========================================
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":9001 "') do (
    echo   Killing PID %%a
    taskkill /F /PID %%a >nul 2>&1
)
ping 127.0.0.1 -n 4 >nul

echo.
echo ========================================
echo   Starting frontend on port 9001...
echo   (Flutter runs in its own window)
echo ========================================
cd /d "%~dp0flutter_app"
start "Flutter - WorldCup 2026" cmd /c "C:\Users\jerry\flutter\bin\flutter.bat run -d web-server --web-hostname 0.0.0.0 --web-port 9001"

echo.
echo Waiting for frontend to start...
setlocal enabledelayedexpansion
set /a retries=0
:wait_frontend
ping 127.0.0.1 -n 6 >nul
set /a retries+=1
netstat -ano | findstr ":9001 " >nul 2>&1
if errorlevel 1 (
    echo   retry !retries!: port not up yet
    if !retries! lss 30 goto wait_frontend
    echo [FAIL] Frontend did not start within 2.5 minutes.
    echo        Check the "Flutter - WorldCup 2026" window for errors.
    pause
    exit /b 1
)
echo [OK] Port 9001 is listening.

ping 127.0.0.1 -n 3 >nul
curl -s -o nul -w "%%{http_code}" http://localhost:9001/ > "%TEMP%\frontend_check.txt" 2>&1
set /p http_code=<"%TEMP%\frontend_check.txt"
del "%TEMP%\frontend_check.txt" 2>nul
if "%http_code%"=="200" (
    echo [OK] Page responds with HTTP 200.
    echo.
    echo Frontend is ready: http://localhost:9001
) else (
    echo [WARN] Port is listening but page returned HTTP %http_code%.
    echo        Check the "Flutter - WorldCup 2026" window for errors.
)
echo.
echo Note: Flutter is running in a separate window. Close it to stop the server.
pause
