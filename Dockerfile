# GenAI GitLab Chatbot - Backend (API + RAG)
FROM python:3.11-slim

WORKDIR /app

# Install system deps if needed (e.g. for sentence-transformers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Optional: run ingest on build (comment out for faster builds; run as init job instead)
# RUN python -m backend.ingest && python -m backend.embeddings

EXPOSE 8000
ENV PYTHONUNBUFFERED=1
# Use PORT from Fly.io (default 8000)
CMD ["sh", "-c", "uvicorn backend.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
