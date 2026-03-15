@echo off
REM Run GenAI GitLab Chatbot from scratch (Windows)
REM Run this from project root: scripts\run_from_scratch.bat
cd /d "%~dp0\.."

echo === GenAI GitLab Chatbot - Run from scratch ===
echo.

REM 1. Python venv
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate
echo Using Python: %VIRTUAL_ENV%

REM 2. Install backend deps
echo.
echo Installing backend dependencies...
pip install -q -r requirements.txt

REM 3. Backend .env
if not exist "backend\.env" (
    echo.
    echo Backend .env not found. Copying backend\.env.example to backend\.env
    copy backend\.env.example backend\.env
    echo.
    echo ** IMPORTANT: Edit backend\.env and set your API key:
    echo    - OPENAI_API_KEY=sk-...  if using LLM_PROVIDER=openai
    echo    - GOOGLE_API_KEY=...     if using LLM_PROVIDER=google
    echo.
    set /p CONTINUE="Have you set your API key in backend\.env? (y/n): "
    if /i not "%CONTINUE%"=="y" exit /b 1
) else (
    echo Backend .env found.
)

REM 4. Ingest + vector store (optional: skip if vector_store already populated)
if not exist "data\processed_docs\chunks.jsonl" (
    echo.
    echo Running data ingestion (scrape handbook + direction)...
    python -m backend.ingest
    echo Building vector store...
    python -m backend.embeddings
    echo Ingest complete.
) else (
    echo.
    echo Found data\processed_docs\chunks.jsonl. Skipping ingest.
    echo To re-ingest, delete data\processed_docs\chunks.jsonl and run again, or: python -m backend.ingest
)

if not exist "vector_store\chroma.sqlite3" (
    echo Building vector store from existing chunks...
    python -m backend.embeddings
)

echo.
echo === Backend ready. Start servers:
echo   Terminal 1: uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
echo   Terminal 2: cd frontend ^&^& npm install ^&^& npm run dev
echo.
echo Then open http://localhost:5173
echo.
pause
