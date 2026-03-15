"""
Data ingestion pipeline for GitLab Handbook and Direction pages.
Scrapes, cleans, chunks, and optionally stores in vector DB.
"""

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DOCS_DIR = DATA_DIR / "processed_docs"
RAW_SCRAPE_DIR = DATA_DIR / "raw_scrape"

# Source URLs
HANDBOOK_BASE = "https://about.gitlab.com/handbook/"
DIRECTION_BASE = "https://about.gitlab.com/direction/"

# Entry points and seed URLs (key pages to ensure we have real handbook/direction content)
HANDBOOK_ENTRY = "https://about.gitlab.com/handbook/"
DIRECTION_ENTRY = "https://about.gitlab.com/direction/"

# Seed URLs: fetch these explicitly so RAG has content even if crawl misses them
HANDBOOK_SEED_URLS = [
    "https://about.gitlab.com/handbook/",
    "https://about.gitlab.com/handbook/engineering/",
    "https://about.gitlab.com/handbook/product/",
    "https://about.gitlab.com/handbook/company/culture/",
    "https://about.gitlab.com/handbook/values/",
    "https://about.gitlab.com/handbook/leadership/",
]
DIRECTION_SEED_URLS = [
    "https://about.gitlab.com/direction/",
    "https://about.gitlab.com/direction/product/",
    "https://about.gitlab.com/direction/engineering/",
]

# Selectors for main content (GitLab handbook/direction pages)
CONTENT_SELECTORS = [
    "article",
    "main",
    "[role='main']",
    ".content",
    ".handbook-content",
    "#main-content",
    ".md-content",
]


def ensure_dirs() -> None:
    """Create data directories if they don't exist."""
    PROCESSED_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_SCRAPE_DIR.mkdir(parents=True, exist_ok=True)


def extract_links_from_page(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Extract same-origin links from a page (handbook or direction)."""
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        if "about.gitlab.com" in parsed.netloc and ("/handbook/" in full_url or "/direction/" in full_url):
            # Normalize: remove fragment, trailing slash for consistency
            normalized = full_url.split("#")[0].rstrip("/") or full_url
            links.add(normalized)
    return list(links)


def extract_text_from_soup(soup: BeautifulSoup) -> str:
    """Extract clean text from main content area."""
    for selector in CONTENT_SELECTORS:
        el = soup.select_one(selector)
        if el:
            # Remove script, style, nav
            for tag in el.find_all(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()
            text = el.get_text(separator="\n", strip=True)
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text.strip()
    # Fallback: body
    body = soup.find("body")
    if body:
        for tag in body.find_all(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        return body.get_text(separator="\n", strip=True)
    return ""


def get_title(soup: BeautifulSoup) -> str:
    """Get page title."""
    t = soup.find("title")
    if t:
        return t.get_text(strip=True)
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return "Untitled"


def get_section_from_url(url: str) -> str:
    """Derive section from URL path (e.g. handbook/engineering, direction/product)."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    parts = path.split("/")
    if len(parts) >= 2:
        return "/".join(parts[:2])  # e.g. handbook/engineering
    return path or "general"


async def fetch_page(client: httpx.AsyncClient, url: str, delay: float = 1.0) -> tuple[str, BeautifulSoup | None]:
    """Fetch a single page and return (url, soup or None)."""
    try:
        await asyncio.sleep(delay)
        r = await client.get(url, follow_redirects=True, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        return (url, soup)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return (url, None)


async def crawl_from_entry(
    client: httpx.AsyncClient,
    start_url: str,
    base_prefix: str,
    delay: float = 1.0,
    max_pages: int = 500,
) -> dict[str, BeautifulSoup]:
    """BFS crawl from entry URL, limited to same base (handbook or direction)."""
    seen = {start_url}
    queue = [start_url]
    pages: dict[str, BeautifulSoup] = {}

    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        if url in pages:
            continue
        url_norm = url.split("#")[0].rstrip("/") or url
        _, soup = await fetch_page(client, url_norm, delay)
        if soup is None:
            continue
        pages[url_norm] = soup
        for link in extract_links_from_page(soup, url_norm):
            if link not in seen and link.startswith(base_prefix):
                seen.add(link)
                queue.append(link)

    return pages


def doc_to_chunks(
    text: str,
    metadata: dict[str, Any],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[dict[str, Any]]:
    """Split document into overlapping chunks with metadata."""
    if not text or len(text.strip()) < 50:
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    return [
        {
            "text": c,
            "metadata": {
                **metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
            },
        }
        for i, c in enumerate(chunks)
    ]


async def run_ingestion(
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    delay: float = 1.0,
    max_pages_per_site: int = 300,
) -> list[dict[str, Any]]:
    """
    Full ingestion: scrape handbook + direction, clean, chunk.
    Returns list of chunk dicts with 'text' and 'metadata'.
    """
    ensure_dirs()
    all_chunks: list[dict[str, Any]] = []

    async with httpx.AsyncClient(
        headers={
            "User-Agent": "GitLabHandbookBot/1.0 (Documentation indexer; contact via GitLab)",
            "Accept": "text/html,application/xhtml+xml",
        },
        follow_redirects=True,
    ) as client:
        # Fetch seed URLs first so we always have key pages
        handbook_pages: dict[str, Any] = {}
        for url in HANDBOOK_SEED_URLS:
            url_norm = url.split("#")[0].rstrip("/") or url
            _, soup = await fetch_page(client, url_norm, delay)
            if soup:
                handbook_pages[url_norm] = soup
        print("Fetched handbook seed pages:", len(handbook_pages))

        direction_pages: dict[str, Any] = {}
        for url in DIRECTION_SEED_URLS:
            url_norm = url.split("#")[0].rstrip("/") or url
            _, soup = await fetch_page(client, url_norm, delay)
            if soup:
                direction_pages[url_norm] = soup
        print("Fetched direction seed pages:", len(direction_pages))

        # Crawl more handbook pages from entry
        print("Crawling GitLab Handbook...")
        crawled_h = await crawl_from_entry(
            client, HANDBOOK_ENTRY, "https://about.gitlab.com/handbook/", delay, max_pages_per_site
        )
        handbook_pages = {**handbook_pages, **crawled_h}
        print(f"Handbook total: {len(handbook_pages)} pages")

        # Crawl more direction pages
        print("Crawling GitLab Direction...")
        crawled_d = await crawl_from_entry(
            client, DIRECTION_ENTRY, "https://about.gitlab.com/direction/", delay, max_pages_per_site
        )
        direction_pages = {**direction_pages, **crawled_d}
        print(f"Direction total: {len(direction_pages)} pages")

    for url, soup in list(handbook_pages.items()) + list(direction_pages.items()):
        title = get_title(soup)
        section = get_section_from_url(url)
        text = extract_text_from_soup(soup)
        if not text or len(text) < 100:
            continue
        metadata = {
            "source": url,
            "title": title,
            "section": section,
        }
        chunks = doc_to_chunks(text, metadata, chunk_size, chunk_overlap)
        all_chunks.extend(chunks)

    # Persist processed docs (JSONL) for reproducibility
    out_file = PROCESSED_DOCS_DIR / "chunks.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for item in all_chunks:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Wrote {len(all_chunks)} chunks to {out_file}")

    return all_chunks


def load_processed_chunks() -> list[dict[str, Any]]:
    """Load chunks from processed_docs/chunks.jsonl if present."""
    out_file = PROCESSED_DOCS_DIR / "chunks.jsonl"
    if not out_file.exists():
        return []
    chunks = []
    with open(out_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


if __name__ == "__main__":
    import sys
    from pathlib import Path
    # Allow running as script from backend dir
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    asyncio.run(run_ingestion(chunk_size=1000, chunk_overlap=200, delay=1.0, max_pages_per_site=200))
