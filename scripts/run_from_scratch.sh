#!/usr/bin/env bash
# Run GenAI GitLab Chatbot from scratch (macOS/Linux)
# Run from project root: ./scripts/run_from_scratch.sh
set -e
cd "$(dirname "$0")/.."

echo "=== GenAI GitLab Chatbot - Run from scratch ==="
echo

# 1. Python venv
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "Using Python: $VIRTUAL_ENV"

# 2. Install backend deps
echo
echo "Installing backend dependencies..."
pip install -q -r requirements.txt

# 3. Backend .env
if [ ! -f "backend/.env" ]; then
    echo
    echo "Backend .env not found. Copying backend/.env.example to backend/.env"
    cp backend/.env.example backend/.env
    echo
    echo "** IMPORTANT: Edit backend/.env and set your API key:"
    echo "   - OPENAI_API_KEY=sk-...  if using LLM_PROVIDER=openai"
    echo "   - GOOGLE_API_KEY=...     if using LLM_PROVIDER=google"
    echo
    read -p "Have you set your API key in backend/.env? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then exit 1; fi
else
    echo "Backend .env found."
fi

# 4. Ingest + vector store
if [ ! -f "data/processed_docs/chunks.jsonl" ]; then
    echo
    echo "Running data ingestion (scrape handbook + direction)..."
    python -m backend.ingest
    echo "Building vector store..."
    python -m backend.embeddings
    echo "Ingest complete."
else
    echo
    echo "Found data/processed_docs/chunks.jsonl. Skipping ingest."
    echo "To re-ingest, remove that file and run again, or: python -m backend.ingest"
fi

echo
echo "=== Backend ready. Start servers:"
echo "  Terminal 1: uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000"
echo "  Terminal 2: cd frontend && npm install && npm run dev"
echo
echo "Then open http://localhost:5173"
echo
