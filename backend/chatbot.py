"""
RAG-based chatbot: retrieval + LLM generation with guardrails and source citations.
"""

from typing import Any

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage, AIMessage

from backend.config import get_settings
from backend.embeddings import get_vector_store


SYSTEM_PROMPT = """You are an assistant that answers questions strictly using GitLab's handbook and direction documentation.

Rules:
- Use ONLY the provided context from the documentation to answer. Do not use external knowledge.
- If the answer cannot be found in the provided context, say exactly: "I cannot find this information in the GitLab handbook."
- Always cite sources: include the relevant URL(s) from the context at the end of your answer.
- Be concise and clear. If the context mentions a page or section, refer to it.
- Do not make up URLs, facts, or page names. Only use what appears in the context.
- For follow-up questions, use the context provided; if it's insufficient, say you cannot find that information.
- CRITICAL: Output ONLY the final answer. Do not show internal reasoning. Do not output <think> or </think> tags or any chain-of-thought. Only return the final answer. Always include source links at the end."""


def strip_think_blocks(text: str) -> str:
    """Remove <think>...</think> blocks so internal reasoning is never shown to users."""
    if not text or not text.strip():
        return text
    import re
    # Remove <think>...</think> (case-insensitive, multiline)
    cleaned = re.sub(r"\s*<think>.*?</think>\s*", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Also remove any stray </think> or <think> without the other
    cleaned = re.sub(r"\s*</think>\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*<think>\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip() or text.strip()


def get_llm():
    """Return configured LLM (OpenAI, Google Gemini, HuggingFace, or Bytez)."""
    settings = get_settings()
    provider = (settings.llm_provider or "openai").lower()

    if provider == "bytez":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.bytez_model,
            api_key=settings.bytez_api_key or None,
            base_url=(settings.bytez_api_base.rstrip("/") if settings.bytez_api_base else None),
            temperature=0.1,
        )
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key or None,
            temperature=0.1,
        )
    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.google_model,
            google_api_key=settings.google_api_key or None,
            temperature=0.1,
        )
    if provider == "huggingface":
        from langchain_huggingface import ChatHuggingFace
        from langchain_community.llms import HuggingFaceEndpoint
        return ChatHuggingFace(
            llm=HuggingFaceEndpoint(
                repo_id=settings.huggingface_model,
                huggingfacehub_api_token=settings.huggingface_api_key or None,
            ),
            temperature=0.1,
        )
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0.1)


def format_docs(docs: list[Any]) -> str:
    """Format retrieved documents as context string with source URLs."""
    parts = []
    seen_urls = set()
    for i, d in enumerate(docs, 1):
        content = d.page_content if hasattr(d, "page_content") else str(d.get("page_content", d))
        meta = d.metadata if hasattr(d, "metadata") else d.get("metadata", {})
        url = meta.get("source", "")
        title = meta.get("title", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
        parts.append(f"[Source {i}: {url}]\n{content}")
    return "\n\n---\n\n".join(parts) if parts else "No relevant documentation found."


def extract_sources_from_docs(docs: list[Any]) -> list[dict[str, str]]:
    """Extract unique source URLs and titles for citation panel."""
    seen = set()
    out = []
    for d in docs:
        meta = d.metadata if hasattr(d, "metadata") else d.get("metadata", {})
        url = meta.get("source", "")
        if url and url not in seen:
            seen.add(url)
            out.append({"url": url, "title": meta.get("title", "GitLab Handbook")})
    return out


def build_rag_chain(collection_name: str = "gitlab_handbook"):
    """Build RAG chain: retriever + prompt + LLM."""
    settings = get_settings()
    vector_store = get_vector_store(collection_name)
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": settings.top_k_retrieve},
    )
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "Context from GitLab documentation:\n\n{context}\n\nQuestion: {question}"),
    ])

    def retrieve(query: str):
        return retriever.invoke(query)

    def build_context(docs):
        return format_docs(docs)

    def run_chain(inputs: dict):
        question = inputs["question"]
        chat_history = inputs.get("chat_history") or []
        docs = retrieve(question)
        context = build_context(docs)
        return {
            "context": context,
            "question": question,
            "chat_history": chat_history,
            "sources": extract_sources_from_docs(docs),
            "docs": docs,
        }

    chain = (
        RunnablePassthrough.assign(
            context=lambda x: build_context(retriever.invoke(x["question"])),
            docs=lambda x: retriever.invoke(x["question"]),
        )
        | RunnablePassthrough.assign(
            sources=lambda x: extract_sources_from_docs(x["docs"]),
        )
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain, retriever, llm


def query(
    question: str,
    chat_history: list[dict[str, str]] | None = None,
    collection_name: str = "gitlab_handbook",
) -> dict[str, Any]:
    """
    Single query: retrieve context, run LLM, return answer + sources.
    chat_history: list of {"role": "user"|"assistant", "content": "..."}
    """
    from langchain_core.messages import HumanMessage, AIMessage

    chain, retriever, _ = build_rag_chain(collection_name)
    history = chat_history or []
    lc_messages = []
    for m in history:
        if m.get("role") == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        else:
            lc_messages.append(AIMessage(content=m["content"]))

    docs = retriever.invoke(question)
    context = format_docs(docs)
    sources = extract_sources_from_docs(docs)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "Context from GitLab documentation:\n\n{context}\n\nQuestion: {question}"),
    ])
    llm = get_llm()
    full_chain = prompt | llm | StrOutputParser()

    answer = full_chain.invoke({
        "context": context,
        "question": question,
        "chat_history": lc_messages,
    })

    # Strip any <think>...</think> so internal reasoning is never shown
    answer = strip_think_blocks(answer)

    # Confidence: numeric 0-100 and label; more docs + longer context = higher
    has_context = len(context.strip()) > 100 and len(docs) > 0
    if has_context and len(docs) >= 3:
        confidence_label, confidence_score = "high", min(95, 70 + min(len(docs) * 5, 25))
    elif has_context and len(docs) >= 1:
        confidence_label, confidence_score = "medium", min(75, 50 + len(docs) * 8)
    else:
        confidence_label, confidence_score = "low", max(15, 30 - len(docs) * 5)

    # Build retrieved context snippets for transparency panel (title + short snippet per doc)
    retrieved_context = []
    for d in docs:
        meta = d.metadata if hasattr(d, "metadata") else d.get("metadata", {})
        content = (d.page_content if hasattr(d, "page_content") else d.get("page_content", ""))[:400]
        retrieved_context.append({
            "title": meta.get("title", "GitLab Handbook"),
            "url": meta.get("source", ""),
            "snippet": (content + "…") if len(content) >= 400 else content,
        })

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence_label,
        "confidence_score": confidence_score,
        "retrieved_count": len(docs),
        "retrieved_context": retrieved_context,
    }


def get_follow_up_suggestions(question: str, answer: str, sources: list[dict]) -> list[str]:
    """Generate a few suggested follow-up questions (heuristic)."""
    suggestions = []
    if "remote" in question.lower() or "work" in question.lower():
        suggestions.extend([
            "What is GitLab's approach to async communication?",
            "How does GitLab support work-life balance?",
        ])
    if "strategy" in question.lower() or "direction" in question.lower():
        suggestions.extend([
            "What are GitLab's product priorities?",
            "How does GitLab plan its roadmap?",
        ])
    if "culture" in question.lower() or "engineering" in question.lower():
        suggestions.extend([
            "What are GitLab's values?",
            "How does GitLab handle code review?",
        ])
    if "release" in question.lower() or "releases" in question.lower():
        suggestions.extend([
            "How does GitLab manage releases?",
            "What is GitLab's release process?",
        ])
    if "devsecops" in question.lower() or "security" in question.lower():
        suggestions.extend([
            "What is GitLab's DevSecOps strategy?",
            "How does GitLab approach security?",
        ])
    # Generic
    if not suggestions:
        suggestions = [
            "What is GitLab's product strategy?",
            "How does GitLab handle remote work?",
            "What is GitLab's engineering culture?",
            "How does GitLab manage releases?",
            "What is GitLab's DevSecOps strategy?",
        ]
    return suggestions[:4]
