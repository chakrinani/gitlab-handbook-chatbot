# GenAI GitLab Handbook Chatbot - Backend (API + RAG)
# Hugging Face Spaces: port 7860 | Fly.io: set PORT in fly.toml
FROM python:3.10-slim

WORKDIR /app

# Install system deps (e.g. for sentence-transformers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 7860
ENV PYTHONUNBUFFERED=1
# Hugging Face Spaces: port 7860. Fly.io: set PORT in fly.toml to override.
ENV PORT=7860
CMD ["sh", "-c", "uvicorn backend.api:app --host 0.0.0.0 --port ${PORT}"]
