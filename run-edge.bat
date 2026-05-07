@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [Dosys Edge] Creating virtual environment...
  py -3 -m venv .venv
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo [Dosys Edge] Failed to activate .venv
  exit /b 1
)

echo [Dosys Edge] Installing/updating dependencies...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
  echo [Dosys Edge] Dependency installation failed
  exit /b 1
)

echo [Dosys Edge] Starting API on EDGE_HTTP_PORT/PORT...
python -m app.main
