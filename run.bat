@echo off
title Add Keywords to Images
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
echo Or install from: https://www.python.org/downloads/
echo.
pause
exit /b 1

:have_python
echo Installing packages (first time only)...
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install packages.
    pause
    exit /b 1
)

echo.
%PY% add_keywords.py
echo.
pause
