@echo off
title DropTag
cd /d "%~dp0"

echo.
echo Checking Python...

where py >nul 2>&1
if not errorlevel 1 (
    set "PY=py"
    goto :have_python
)

where python >nul 2>&1
if not errorlevel 1 (
    set "PY=python"
    goto :have_python
)

echo.
echo Python is NOT installed.
echo Open a NEW terminal and try:  py --version
echo.
pause
exit /b 1

:have_python
echo Installing packages...
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install packages.
    pause
    exit /b 1
)

echo.
echo Starting DropTag at http://127.0.0.1:7860
echo Keep this window open. Press Ctrl+C to stop.
echo.

start "" "http://127.0.0.1:7860"
%PY% -m uvicorn webapp:app --host 127.0.0.1 --port 7860

pause
