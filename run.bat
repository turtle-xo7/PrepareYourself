@echo off
REM ============================================================
REM  Prepare Yourself - Start the Django dev server
REM  Double-click this after running setup.bat once.
REM ============================================================

setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Please run setup.bat first.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Starting server at http://127.0.0.1:8000/
echo   Press Ctrl+C to stop.
echo ============================================
echo.

".venv\Scripts\python.exe" manage.py runserver

endlocal
