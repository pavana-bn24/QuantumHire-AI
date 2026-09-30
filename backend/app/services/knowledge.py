"""Lightweight keyword retrieval over the local markdown knowledge base.

This is deliberately a *small* RAG implementation - no vector database, no
embeddings service - so the whole pipeline runs offline in tests and demos.

Pipeline:
  1. Load every ``*.md`` file from ``settings.knowledge_dir`` (cached).
  2. Split each document into chunks on markdown headings (``#`` / ``##``).
  3. Score chunks for a query with a token-overlap heuristic: every matching
     token adds weight, heading/title matches count double, and very short
     chunks are slightly penalised so a stray word match cannot win.

Scores are relative (0..~2) and used only for ranking - they are never exposed
as a "candidate score" anywhere in the product.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.models import KnowledgeChunk

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
_TOKEN_RE = re.compile(r"[a-z0-9_]{2,}")

#: Tiny English stopword list - kept short so requirement terms are never dropped.
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
    "has", "have", "had", "not", "but", "its", "into", "than", "then", "them",
    "they", "you", "your", "all", "any", "can", "may", "our", "out", "use",
    "used", "using", "when", "what", "which", "who", "how", "why", "each",
    "must", "should", "will", "would", "been", "being", "does", "did", "also",
    "one", "two", "per", "via", "own", "such", "only", "over", "under",
    "a", "an", "of", "in", "on", "to", "is", "it", "as", "at", "by", "or",
    "be", "if", "so", "do", "no", "up", "we",
}


def tokenize(text: str) -> list[str]:
    """Lower-case word tokens minus stopwords."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


class KnowledgeChunkDraft:
    """Internal chunk record before it becomes a response model."""

    __slots__ = ("source", "heading", "text", "tokens")

    def __init__(self, source: str, heading: str, text: str) -> None:
        self.source = source
        self.heading = heading
        self.text = text
        self.tokens = set(tokenize(f"{heading} {text}"))


def _split_document(source: str, content: str) -> list[KnowledgeChunkDraft]:
    """Split markdown into per-heading sections (preamble gets the doc title)."""
    chunks: list[KnowledgeChunkDraft] = []
    heading = source
    buffer: list[str] = []

    def flush() -> None:
        text = "\n".join(buffer).strip()
        if text:
            chunks.append(KnowledgeChunkDraft(source, heading, text))
        buffer.clear()

    for line in content.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            flush()
            heading = match.group(2).strip()
        else:
            buffer.append(line)
    flush()

    # Guarantee at least one chunk per file, even for heading-less documents.
    if not chunks and content.strip():
        chunks.append(KnowledgeChunkDraft(source, source, content.strip()))
    return chunks


@lru_cache(maxsize=4)
def load_knowledge_chunks(directory: str | None = None) -> tuple[KnowledgeChunkDraft, ...]:
    """Read and chunk every markdown file in the knowledge directory.

    Cached by directory path; tests can point ``KNOWLEDGE_DIR`` elsewhere or
    call ``load_knowledge_chunks.cache_clear()`` after editing files.
    """
    target = directory or settings.knowledge_dir
    root = Path(target) if target else None
    if root is None or not root.is_dir():
        return ()

    drafts: list[KnowledgeChunkDraft] = []
    for path in sorted(root.glob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue  # unreadable file: skip rather than fail the request
        drafts.extend(_split_document(path.name, content))
    return tuple(drafts)


def search_knowledge(query: str, top_k: int | None = None) -> list[KnowledgeChunk]:
    """Return the ``top_k`` chunks most relevant to ``query`` (best first)."""
    tokens = set(tokenize(query or ""))
    if not tokens:
        return []

    limit = top_k or settings.knowledge_top_k
    scored: list[KnowledgeChunk] = []

    for chunk in load_knowledge_chunks():
        overlap = tokens & chunk.tokens
        if not overlap:
            continue
        # Heading matches weigh double; tiny sections are slightly penalised.
        heading_hits = len(tokens & set(tokenize(chunk.heading)))
        size_penalty = 0.9 if len(chunk.tokens) < 12 else 1.0
        score = (len(overlap) + heading_hits) * size_penalty
        scored.append(
            KnowledgeChunk(
                source=chunk.source,
                heading=chunk.heading,
                text=chunk.text,
                score=round(score, 3),
            )
        )

    scored.sort(key=lambda c: (-c.score, c.source, c.heading))
    return scored[:limit]


def knowledge_sources_for(chunks: list[KnowledgeChunk]) -> list[str]:
    """Unique ``source#heading`` citations for an evaluation, in rank order."""
    sources: list[str] = []
    for chunk in chunks:
        citation = f"{chunk.source}#{chunk.heading}"
        if citation not in sources:
            sources.append(citation)
    return sources
