"""
FastAPI backend for the GenAI GitLab Chatbot.
Exposes /chat, /ingest, and health endpoints.
"""

import os
import sys
from pathlib import Path

# Ensure project root is on path when running as script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.chatbot import query, get_follow_up_suggestions

app = FastAPI(
    title="GenAI GitLab Chatbot API",
    description="RAG-based chatbot for GitLab Handbook and Direction documentation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----- Request/Response models -----

class ChatMessage(BaseModel):
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, description="Previous messages for context")


class SourceRef(BaseModel):
    url: str
    title: str


class RetrievedContextItem(BaseModel):
    title: str
    url: str
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceRef] = Field(default_factory=list)
    confidence: str = "medium"
    confidence_score: int | None = Field(default=None, description="Confidence 0-100%")
    follow_up_suggestions: list[str] = Field(default_factory=list)
    retrieved_context: list[RetrievedContextItem] = Field(default_factory=list, description="Docs used for answer (transparency)")


# Off-topic guardrail: reject questions unrelated to GitLab Handbook/Direction
OFF_TOPIC_KEYWORDS = [
    "recipe", "movie", "weather", "sports", "game", "celebrity",
    "president", "usa", "united states", "election", "who is the",
    "capital of", "football", "song", "music", "recipe for",
]
GITLAB_INDICATORS = [
    "gitlab", "handbook", "direction", "remote", "culture", "strategy",
    "engineering", "process", "work", "company", "team", "product", "value",
    "how does", "what is", "policy", "devsecops", "code review", "release",
]


def is_likely_off_topic(message: str) -> bool:
    """Reject clearly off-topic questions; only allow GitLab handbook/direction topics."""
    lower = message.lower().strip()
    if len(lower) < 8:
        return False
    has_off = any(k in lower for k in OFF_TOPIC_KEYWORDS)
    has_gitlab = any(k in lower for k in GITLAB_INDICATORS)
    return has_off and not has_gitlab


@app.get("/")
def root():
    """Root path: point users to the chat UI and API docs."""
    return {
        "service": "GenAI GitLab Chatbot API",
        "docs": "/docs",
        "health": "/health",
        "chat_ui": "Open the frontend at http://localhost:5173 (or 5174) to use the chatbot.",
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "genai-gitlab-chatbot"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Send a message and get an answer grounded in GitLab handbook/direction docs.
    """
    if is_likely_off_topic(request.message):
        return ChatResponse(
            answer="I can only answer questions related to GitLab's Handbook and Direction documentation. Please ask about GitLab's processes, culture, strategy, engineering, or product.",
            sources=[],
            confidence="low",
            confidence_score=0,
            follow_up_suggestions=[
                "What is GitLab's product strategy?",
                "How does GitLab handle remote work?",
                "What is GitLab's engineering culture?",
            ],
            retrieved_context=[],
        )

    try:
        history = [{"role": m.role, "content": m.content} for m in request.history]
        result = query(question=request.message, chat_history=history)
        follow_ups = get_follow_up_suggestions(
            request.message, result["answer"], result["sources"]
        )
        retrieved = [
            RetrievedContextItem(title=c["title"], url=c["url"], snippet=c["snippet"])
            for c in result.get("retrieved_context", [])
        ]
        return ChatResponse(
            answer=result["answer"],
            sources=[SourceRef(url=s["url"], title=s["title"]) for s in result["sources"]],
            confidence=result.get("confidence", "medium"),
            confidence_score=result.get("confidence_score"),
            follow_up_suggestions=follow_ups,
            retrieved_context=retrieved,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@app.post("/ingest")
def run_ingest():
    """
    Trigger data ingestion (scrape + chunk). Long-running; consider running offline.
    """
    try:
        import asyncio
        from backend.ingest import run_ingestion
        from backend.embeddings import build_and_persist_vector_store

        async def do_ingest():
            chunks = await run_ingestion(chunk_size=1000, chunk_overlap=200, delay=1.0, max_pages_per_site=200)
            build_and_persist_vector_store(chunks)

        asyncio.run(do_ingest())
        return {"status": "ok", "message": "Ingestion and vector store build completed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion error: {str(e)}")


def main():
    from backend.config import get_settings
    s = get_settings()
    import uvicorn
    uvicorn.run(app, host=s.api_host, port=s.api_port)


if __name__ == "__main__":
    main()
