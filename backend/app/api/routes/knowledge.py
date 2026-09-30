"""Knowledge-base search (retrieval half of RAG)."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_database
from app.models import KnowledgeSearchResponse
from app.services.knowledge import knowledge_sources_for, search_knowledge

router = APIRouter(
    prefix="/knowledge", tags=["knowledge"], dependencies=[Depends(require_database)]
)


@router.get("/search", response_model=KnowledgeSearchResponse, summary="Search the knowledge base")
def knowledge_search(
    q: str = Query(..., min_length=2, description="Keyword query"),
    top_k: int = Query(default=4, ge=1, le=20, description="Max chunks to return"),
) -> dict:
    """Keyword retrieval over the internal markdown knowledge base (RAG)."""
    chunks = search_knowledge(q, top_k=top_k)
    return {"query": q, "chunks": chunks, "sources": knowledge_sources_for(chunks)}
