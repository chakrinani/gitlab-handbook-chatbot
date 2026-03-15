@echo off
cd /d "%~dp0\.."
if not exist ".venv\Scripts\activate.bat" (
    echo Creating venv...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
echo Installing dependencies if needed...
pip install -q -r requirements.txt
echo.
echo Starting backend on http://localhost:8000
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
