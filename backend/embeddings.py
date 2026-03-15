"""
Embedding generation and vector store (ChromaDB) for RAG.
Supports OpenAI, Sentence Transformers (local), and Google embeddings.
"""

import sys
from pathlib import Path
from typing import Any

# Allow running as script from backend dir: python embeddings.py
if __name__ == "__main__":
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from backend.config import PROJECT_ROOT, get_settings

VECTOR_STORE_DIR = PROJECT_ROOT / "vector_store"
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)


def get_embedding_function():
    """Return a LangChain-compatible embedding function based on config."""
    settings = get_settings()
    provider = (settings.embeddings_provider or "sentence_transformers").lower()

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key or None,
        )
    if provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=settings.google_api_key or None,
        )
    # Default: sentence_transformers (local, no API key)
    from langchain_community.embeddings import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name=settings.sentence_transformers_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_vector_store(collection_name: str = "gitlab_handbook"):
    """
    Get or create ChromaDB vector store with the configured embeddings.
    Persists to vector_store/ directory.
    """
    from langchain_community.vectorstores import Chroma

    embed = get_embedding_function()
    persist_path = str(VECTOR_STORE_DIR)
    return Chroma(
        persist_directory=persist_path,
        embedding_function=embed,
        collection_name=collection_name,
    )


def add_chunks_to_vector_store(
    chunks: list[dict[str, Any]],
    collection_name: str = "gitlab_handbook",
) -> None:
    """
    Add chunk dicts (with 'text' and 'metadata') to ChromaDB.
    """
    from langchain_core.documents import Document
    from langchain_community.vectorstores import Chroma

    if not chunks:
        return

    documents = [
        Document(page_content=c["text"], metadata=c.get("metadata", {}))
        for c in chunks
    ]
    embed = get_embedding_function()
    persist_path = str(VECTOR_STORE_DIR)

    Chroma.from_documents(
        documents=documents,
        embedding=embed,
        persist_directory=persist_path,
        collection_name=collection_name,
    )


def build_and_persist_vector_store(chunks: list[dict[str, Any]]) -> None:
    """One-shot: build vector store from chunks and persist."""
    add_chunks_to_vector_store(chunks, collection_name="gitlab_handbook")


if __name__ == "__main__":
    from backend.ingest import load_processed_chunks

    chunks = load_processed_chunks()
    if not chunks:
        print("No processed chunks found. Run ingest.py first.")
    else:
        print(f"Building vector store from {len(chunks)} chunks...")
        build_and_persist_vector_store(chunks)
        print("Done.")
