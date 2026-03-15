@echo off
cd /d "%~dp0\.."
.venv\Scripts\activate 2>nul || python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt -q
echo Running ingestion...
python -m backend.ingest
echo Building vector store...
python -m backend.embeddings
echo Done.
