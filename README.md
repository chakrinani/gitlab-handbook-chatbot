# GenAI GitLab Handbook Chatbot

A production-ready **Retrieval Augmented Generation (RAG)** chatbot that answers questions using [GitLab's Handbook](https://about.gitlab.com/handbook/) and [Direction](https://about.gitlab.com/direction/) documentation. Built for employees and aspiring employees who want to quickly understand GitLab's processes, strategy, and culture.

---

## Project Overview

- **Objective**: Let users query GitLab's public handbook and direction pages in natural language and get accurate, cited answers.
- **Architecture**: User → Chat UI → Backend API → Vector DB (ChromaDB) → LLM → Response with source links.
- **Stack**: Python (FastAPI), LangChain, ChromaDB, React (Vite), OpenAI / Google Gemini / HuggingFace.

---

## Architecture Diagram

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   User      │────▶│  React Frontend   │────▶│  FastAPI        │
│   Browser   │◀────│  (Chat UI)        │◀────│  /chat, /health │
└─────────────┘     └──────────────────┘     └────────┬────────┘
                                                      │
                     ┌────────────────────────────────┼────────────────────────────────┐
                     │                                │                                │
                     ▼                                ▼                                ▼
              ┌──────────────┐              ┌─────────────────┐              ┌─────────────────┐
              │  ChromaDB    │              │  Embeddings      │              │  LLM            │
              │  Vector Store│              │  (OpenAI /       │              │  (OpenAI /      │
              │              │              │   Sentence       │              │   Gemini / HF)  │
              └──────┬───────┘              │   Transformers)  │              └─────────────────┘
                     │                      └─────────────────┘
                     │
              ┌──────▼───────┐
              │  Data        │
              │  Ingestion   │
              │  (scrape →   │
              │   chunk →    │
              │   embed)     │
              └──────────────┘
```

---

## Repository Structure

```
genai-gitlab-chatbot/
├── backend/
│   ├── config.py          # Settings (env vars)
│   ├── ingest.py          # Scraper + chunking pipeline
│   ├── embeddings.py      # Embeddings + ChromaDB
│   ├── chatbot.py         # RAG chain + LLM
│   ├── api.py             # FastAPI app
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── ChatUI.jsx     # Chat window, input, sources
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── data/
│   └── processed_docs/    # chunks.jsonl after ingest
├── vector_store/          # ChromaDB persistence
├── requirements.txt
├── README.md
├── DOCUMENTATION.md       # Full project write-up
└── DEPLOYMENT.md          # Deploy instructions
```

---

## Run from scratch (quick start)

From the **project root**:

**Windows (PowerShell or CMD):**
```bat
scripts\run_from_scratch.bat
```
Then set your API key in `backend\.env` when prompted, and start the servers (see below).

**macOS/Linux:**
```bash
chmod +x scripts/run_from_scratch.sh
./scripts/run_from_scratch.sh
```
Then edit `backend/.env` with your API key if needed, and start the servers.

**Manual start (after run_from_scratch):**
- Terminal 1: `uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000`
- Terminal 2: `cd frontend && npm install && npm run dev`
- Open **http://localhost:5173**

---

## Setup Instructions

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for frontend)
- **API key**: OpenAI or Google Gemini (recommended); or use local Sentence Transformers for embeddings only.

### 1. Clone and backend setup

```bash
cd genai-gitlab-chatbot
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
cp backend/.env.example backend/.env
# Edit backend/.env and set OPENAI_API_KEY or GOOGLE_API_KEY
```

### 2. Environment variables

Create `backend/.env` (see `backend/.env.example`). Minimum for OpenAI:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
EMBEDDINGS_PROVIDER=sentence_transformers
```

For Gemini:

```env
LLM_PROVIDER=google
GOOGLE_API_KEY=...
EMBEDDINGS_PROVIDER=sentence_transformers
```

### 3. Ingest data and build vector store

Run once from **project root** (with `.venv` activated):

```bash
# Option A: Run ingest then build vector store (from project root)
python -m backend.ingest
python -m backend.embeddings
```

Or run the full pipeline in one go:

```bash
python -c "
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))
from backend.ingest import run_ingestion
from backend.embeddings import build_and_persist_vector_store
async def main():
    chunks = await run_ingestion(chunk_size=1000, chunk_overlap=200, delay=1.0, max_pages_per_site=200)
    build_and_persist_vector_store(chunks)
asyncio.run(main())
"
```

### 4. Start backend

```bash
# From project root
uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` to `http://localhost:8000`.

---

## How to Run Locally

| Step | Command | Purpose |
|------|---------|--------|
| 1 | `pip install -r requirements.txt` | Install Python deps |
| 2 | Set `.env` in `backend/` | API keys and options |
| 3 | Run ingest + embeddings (see above) | Populate vector store |
| 4 | `uvicorn backend.api:app --reload --port 8000` | Start API |
| 5 | `cd frontend && npm install && npm run dev` | Start UI |

---

## Example Queries

- *"What is GitLab's product strategy?"*
- *"How does GitLab handle remote work?"*
- *"What is GitLab's engineering culture?"*
- *"What are GitLab's values?"*
- *"How does GitLab do code review?"*
- *"What is the direction for DevSecOps?"*

The bot answers only from retrieved handbook/direction context and cites source URLs. If the answer is not in the docs, it says: *"I cannot find this information in the GitLab handbook."*

---

## Deployment

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for:

- **Vercel** (frontend) + **Railway / Render / Fly.io** (backend)
- **Streamlit Community Cloud** (alternative UI)
- **Hugging Face Spaces** (optional)

The deployed frontend must set `VITE_API_URL` to your public backend URL (e.g. `https://your-api.fly.dev`).

---

## Testing Guide

See **[EXAMPLE_QUERIES.md](EXAMPLE_QUERIES.md)** for sample questions and step-by-step tests.

Quick checks:
1. **Health**: `curl http://localhost:8000/health` → `{"status":"ok",...}`  
2. **Chat**:  
   `curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"What is GitLab's product strategy?\",\"history\":[]}"`  
   Expect `answer`, `sources`, `confidence`, `follow_up_suggestions`.  
3. **UI**: Type the same question in the chat; check that source links open the correct handbook/direction pages.

---

## License

MIT. This project is not affiliated with GitLab Inc.; it uses public documentation only.
