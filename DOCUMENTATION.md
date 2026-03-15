# GenAI GitLab Chatbot – Project Documentation

## 1. Problem Statement

Employees and candidates need to navigate a large amount of GitLab documentation (Handbook and Direction) to understand processes, strategy, and culture. Manually searching and reading is time-consuming. The goal is to provide an **AI chatbot** that:

- Answers natural language questions using **only** GitLab’s handbook and direction content.
- **Cites sources** (URLs) and avoids hallucination.
- Supports **follow-up questions** and a good **user experience** (chat history, loading states, error handling).

---

## 2. Architecture Explanation

The system is a **RAG (Retrieval Augmented Generation)** pipeline:

1. **Data layer**: GitLab Handbook and Direction pages are scraped, cleaned, chunked, embedded, and stored in a **vector database** (ChromaDB).
2. **Query path**: User question → embedded → **similarity search** in the vector store → top-k chunks retrieved.
3. **Generation**: Retrieved chunks are passed as **context** to an LLM with a **strict system prompt** that instructs the model to answer only from that context and to cite sources; if the answer is not in the context, it must say so.

This keeps answers grounded and reduces hallucination while still allowing natural language interaction.

---

## 3. Data Pipeline

| Stage | Implementation |
|-------|----------------|
| **Scraping** | `ingest.py`: Async HTTP (httpx) + BeautifulSoup. BFS crawl from handbook and direction entry URLs; only same-origin handbook/direction links are followed. |
| **Cleaning** | Main content extracted via selectors (`article`, `main`, `.content`, etc.); scripts/nav/footer removed; whitespace normalized. |
| **Chunking** | LangChain `RecursiveCharacterTextSplitter` (e.g. 1000 chars, 200 overlap) so each chunk fits embedding models and retains some context. |
| **Metadata** | Each chunk stores `source` (URL), `title`, `section`, and chunk index. |
| **Output** | Chunks written to `data/processed_docs/chunks.jsonl` for reproducibility. |

---

## 4. RAG Implementation

- **Embeddings**: Configurable: **Sentence Transformers** (local, default), **OpenAI**, or **Google** embeddings. Stored in ChromaDB.
- **Retrieval**: Similarity search in ChromaDB; `top_k` (e.g. 5) chunks returned per query.
- **Prompt**: System prompt states: answer only from the provided context; if not found, respond with “I cannot find this information in the GitLab handbook”; always cite sources.
- **LLM**: **OpenAI** (e.g. gpt-4o-mini), **Google Gemini**, or **HuggingFace**; temperature kept low (0.1) for stability.
- **Conversation**: Chat history (user/assistant messages) is passed so the model can handle follow-ups within the same context window.

---

## 5. Model Selection

| Component | Options | Rationale |
|-----------|---------|-----------|
| **Embeddings** | Sentence Transformers (e.g. all-MiniLM-L6-v2), OpenAI, Google | Local ST avoids API cost and latency; OpenAI/Google can improve retrieval quality. |
| **LLM** | OpenAI gpt-4o-mini, Gemini 1.5 Flash, HuggingFace | Balance of cost, speed, and instruction-following; all support system prompts and citations. |

---

## 6. Deployment Strategy

- **Backend**: Run FastAPI (e.g. with Gunicorn + Uvicorn) on a PaaS (Railway, Render, Fly.io) or container; set env vars for API keys and optional CORS.
- **Frontend**: Build with `npm run build`; serve static files from Vercel/Netlify; set `VITE_API_URL` to the public backend URL.
- **Vector store**: ChromaDB is file-based; persist `vector_store/` on the backend (e.g. volume or included in image). For scale, consider Supabase Vector or a hosted vector DB and swap the retriever in `embeddings.py` / `chatbot.py`.

---

## 7. Future Improvements

- **Re-ingestion schedule**: Periodic re-scrape and re-embed to keep docs up to date.
- **Caching**: Cache embeddings or responses for repeated queries.
- **Stronger guardrails**: Classifier to detect off-topic or out-of-scope questions and return a standard message.
- **Transparency**: Optional “show retrieved context” panel in the UI.
- **Hosted vector DB**: Move to Supabase Vector or Pinecone for multi-instance and larger corpora.
- **Evaluation**: Benchmark set of Q&A pairs and measure retrieval recall and answer faithfulness.
