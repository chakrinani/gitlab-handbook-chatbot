"""
Configuration for the GenAI GitLab Chatbot.
Loads from environment variables with sensible defaults.
.env is loaded from the backend/ directory so the app works when run from project root.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DOCS_DIR = DATA_DIR / "processed_docs"
VECTOR_STORE_DIR = PROJECT_ROOT / "vector_store"
RAW_SCRAPE_DIR = DATA_DIR / "raw_scrape"

# .env next to this file (backend/.env) so uvicorn from project root still finds it
_BACKEND_DIR = Path(__file__).resolve().parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Application settings from environment."""

    # LLM provider: "openai" | "google" | "huggingface" | "bytez"
    llm_provider: str = Field(default="openai", env="LLM_PROVIDER")

    # OpenAI
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")

    # Bytez (OpenAI-compatible API)
    bytez_api_key: str = Field(default="", env="BYTEZ_API_KEY")
    bytez_api_base: str = Field(default="https://api.bytez.com/models/v2/openai/v1", env="BYTEZ_API_BASE")
    bytez_model: str = Field(default="Qwen/Qwen3-4B", env="BYTEZ_MODEL")

    # Google Gemini
    google_api_key: str = Field(default="", env="GOOGLE_API_KEY")
    google_model: str = Field(default="gemini-1.5-flash", env="GOOGLE_MODEL")

    # HuggingFace (optional)
    huggingface_api_key: str = Field(default="", env="HUGGINGFACE_API_KEY")
    huggingface_model: str = Field(default="mistralai/Mixtral-8x7B-Instruct-v0.1", env="HUGGINGFACE_MODEL")

    # Embeddings: "openai" | "sentence_transformers" | "google"
    embeddings_provider: str = Field(default="sentence_transformers", env="EMBEDDINGS_PROVIDER")
    openai_embedding_model: str = Field(default="text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")
    sentence_transformers_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", env="SENTENCE_TRANSFORMERS_MODEL"
    )

    # RAG
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    top_k_retrieve: int = Field(default=5, env="TOP_K_RETRIEVE")
    similarity_threshold: float = Field(default=0.5, env="SIMILARITY_THRESHOLD")

    # Scraper
    scrape_delay_seconds: float = Field(default=1.0, env="SCRAPE_DELAY_SECONDS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")

    # API
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_settings() -> Settings:
    return Settings()
