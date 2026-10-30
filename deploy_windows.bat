@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo             ECO-SHIELD Production Deployment Launcher
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/3] Building frontend production bundle...
cd frontend
call npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed. Please run 'npm install' first.
    pause
    exit /b %errorlevel%
)
cd ..

echo.
echo [2/3] Checking backend Python virtual environment...
cd backend
if not exist ".venv\Scripts\activate.bat" (
    echo Creating virtual environment in backend\.venv...
    py -m venv .venv
)

call .\.venv\Scripts\activate.bat
echo Installing/verifying backend dependencies...
pip install -q -r requirements.txt reportlab pillow

echo.
echo [3/3] Launching unified production server on http://localhost:8000 ...
echo Both API (/api) and UI (/) will be served on a single port!
echo Press Ctrl+C to stop the server anytime.
echo.

start "" "http://localhost:8000"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

pause
