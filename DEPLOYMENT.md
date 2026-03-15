# Deployment Instructions

## Overview

- **Frontend**: React (Vite) → build static assets → deploy to **Vercel** (or Netlify).
- **Backend**: FastAPI → run on **Railway**, **Render**, or **Fly.io** (or any host that runs Python).
- **Vector store**: ChromaDB lives on the backend (persistent disk or volume). Run **ingest + embeddings once** (e.g. during first deploy or via a job).

---

## Option A: Vercel (Frontend) + Railway (Backend)

### Backend (Railway)

1. Create a new project on [Railway](https://railway.app).
2. Connect your GitHub repo; select the project root.
3. Set **Root Directory** to the repo root (or leave default).
4. **Build**:  
   - Build command: `pip install -r requirements.txt`  
   - (Optional) Run ingest once: add a one-off job or run `python -c "..."` from the ingest section in README before first start.
5. **Start**: `uvicorn backend.api:app --host 0.0.0.0 --port $PORT`
6. Add **Variables**:  
   `OPENAI_API_KEY`, `LLM_PROVIDER=openai`, `EMBEDDINGS_PROVIDER=sentence_transformers`, etc. (from `.env.example`).
7. Deploy; copy the public URL (e.g. `https://your-app.railway.app`).

### Frontend (Vercel)

1. Connect the same repo to [Vercel](https://vercel.com).
2. **Root Directory**: `frontend`.
3. **Build**: `npm run build` (Vercel will run `npm install`).
4. **Environment variable**:  
   `VITE_API_URL` = your backend URL (e.g. `https://your-app.railway.app`).
5. Deploy. The chat UI will call the backend at `VITE_API_URL`.

### CORS

The FastAPI app already allows all origins (`allow_origins=["*"]`). For production you can restrict to your Vercel domain.

---

## Option B: Render

### Backend (Web Service)

1. [Render](https://render.com) → New → Web Service → connect repo.
2. **Build**: `pip install -r requirements.txt`
3. **Start**: `uvicorn backend.api:app --host 0.0.0.0 --port $PORT`
4. Add env vars (same as Railway). Use a **persistent disk** for `vector_store/` if Render supports it, or run ingest on each deploy (slower).

### Frontend (Static Site)

1. New → Static Site → connect repo.
2. **Root**: `frontend`, **Build**: `npm run build`, **Publish**: `dist`.
3. Set `VITE_API_URL` to the Render backend URL.

---

## Option C: Fly.io (Backend + optional frontend)

1. Install [flyctl](https://fly.io/docs/hands-on/install-flyctl/).
2. In project root: `fly launch` (create `Dockerfile` if needed).
3. Example **Dockerfile** (backend only):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m app && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

4. Add secrets: `fly secrets set OPENAI_API_KEY=sk-...`
5. For **persistent volume** for ChromaDB: create a volume and mount it to `/app/vector_store` in `fly.toml`.
6. Run ingest once (e.g. `fly ssh console` and run the ingest script, or a one-off job).

Frontend can still be on Vercel with `VITE_API_URL` pointing to `https://your-app.fly.dev`.

---

## Option D: Streamlit Community Cloud (alternative UI)

If you prefer Streamlit instead of React:

1. Add a `streamlit_app.py` in the repo that uses `streamlit-chat` and calls the same FastAPI `/chat` endpoint.
2. Deploy to [Streamlit Community Cloud](https://share.streamlit.io); set secrets for the backend URL and use it in the app.
3. Backend remains deployed as in Option A/B/C.

---

## Option E: Hugging Face Spaces

1. Create a **Space** (Gradio or Streamlit).
2. Build a simple Gradio/Streamlit UI that sends requests to your **already deployed** FastAPI backend (e.g. on Railway/Render).
3. Set the backend URL in the Space’s secrets and in the app code.

---

## Checklist

- [ ] Backend env vars set (e.g. `OPENAI_API_KEY`, `LLM_PROVIDER`).
- [ ] Ingest and vector store built at least once (and persisted if possible).
- [ ] Frontend `VITE_API_URL` points to the public backend URL.
- [ ] CORS on backend allows the frontend origin (or `*` for demo).
- [ ] Health check: `GET /health` returns 200.
