@echo off
REM ============================================================
REM  Prepare Yourself - One-time setup
REM  Run this ONCE after downloading the project.
REM  Creates a local Python environment and installs everything.
REM ============================================================

setlocal
cd /d "%~dp0"

echo.
echo ============================================
echo   Prepare Yourself - Setup
echo ============================================
echo.

REM 1. Find a working Python (prefer the py launcher to avoid the
REM    Microsoft Store "python.exe" stub that ships with Windows).
set "PYCMD="
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYCMD=py -3"
) else (
    where python >nul 2>&1
    if not errorlevel 1 (
        python --version >nul 2>&1
        if not errorlevel 1 set "PYCMD=python"
    )
)

if not defined PYCMD (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    echo and tick "Add Python to PATH" during installation.
    echo.
    echo If you see a Microsoft Store window when typing 'python',
    echo open Settings ^> Apps ^> Advanced app settings ^> App execution
    echo aliases and turn OFF python.exe and python3.exe.
    pause
    exit /b 1
)

REM 2. Create a virtual environment in .venv if it does not already exist
if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating virtual environment in .venv ...
    %PYCMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Virtual environment already exists. Skipping.
)

REM 3. Upgrade pip
echo [2/4] Upgrading pip ...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet

REM 4. Install requirements
echo [3/4] Installing required packages from requirements.txt ...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install packages.
    pause
    exit /b 1
)

REM 5. Apply database migrations
echo [4/4] Applying database migrations ...
".venv\Scripts\python.exe" manage.py migrate

echo.
echo ============================================
echo   Setup complete!
echo   Now double-click run.bat to start the server.
echo ============================================
echo.
pause
endlocal
