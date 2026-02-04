"""Search, context, and suggestion endpoints."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from .. import collections
from .. import documents
from ..models import SearchQuery, SearchResult, MemoryType
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Search"])


class SuggestRequest(BaseModel):
    """Request model for memory suggestions."""
    project: Optional[str] = None
    keywords: Optional[list[str]] = None
    current_files: Optional[list[str]] = None
    git_branch: Optional[str] = None
    limit: int = 5


@router.post("/memories/search", response_model=list[SearchResult])
async def search_memories(
    query: SearchQuery,
    search_mode: str = "hybrid",
    use_cache: bool = True,
    use_reranking: bool = True,
    use_graph_expansion: bool = False
):
    """
    Search memories using semantic similarity with optional enhancements.

    Args:
        query: Search query with filters
        search_mode: "semantic", "keyword", or "hybrid" (default: hybrid)
        use_cache: Enable query cache (default: true)
        use_reranking: Enable cross-encoder reranking (default: true)
        use_graph_expansion: Enable graph-based search expansion (Phase 2.1, default: false)
    """
    try:
        results = collections.search_memories(
            query,
            search_mode=search_mode,
            use_cache=use_cache,
            use_reranking=use_reranking,
            use_graph_expansion=use_graph_expansion
        )
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/unified")
async def unified_search(
    query: str = Query(..., description="Search query"),
    search_memories: bool = Query(default=True, description="Include memories in search"),
    search_documents: bool = Query(default=True, description="Include documents in search"),
    memory_limit: int = Query(default=10, description="Maximum memories to return"),
    document_limit: int = Query(default=5, description="Maximum documents to return"),
    type_filter: Optional[str] = Query(default=None, description="Filter memories by type"),
    project: Optional[str] = Query(default=None, description="Filter by project")
):
    """
    Unified search across memories and documents.
    Returns both structured memories and filesystem documents.
    """
    results = {
        "query": query,
        "memories": [],
        "documents": [],
        "total_count": 0
    }

    # Search memories if requested
    if search_memories:
        search_query = SearchQuery(
            query=query,
            type=type_filter,
            project=project,
            limit=memory_limit
        )
        memory_results = collections.search_memories(search_query)
        results["memories"] = [r.model_dump(mode='json') for r in memory_results]

    # Search documents if requested
    if search_documents:
        try:
            doc_results = documents.search_documents(
                query=query,
                limit=document_limit,
                folder=project
            )
            results["documents"] = doc_results
        except Exception as e:
            logger.warning(f"Document search failed: {e}")
            results["documents"] = []

    results["total_count"] = len(results["memories"]) + len(results["documents"])
    return results


@router.post("/query/enhance")
async def enhance_query(
    query: str = Query(..., description="Search query to enhance"),
    expand_synonyms: bool = Query(default=True, description="Add synonyms for better recall"),
    correct_typos: bool = Query(default=True, description="Suggest typo corrections")
):
    """
    Apply query intelligence enhancements.

    Enhances search queries with:
    - Synonym expansion for better recall
    - Typo correction suggestions
    - Query routing recommendations

    Example:
        POST /query/enhance?query=dcoker%20erro
        Returns: {
            "original_query": "dcoker erro",
            "enhanced_query": "docker error container bug exception",
            "corrections": [{"original": "dcoker", "suggestion": "docker"}],
            "expansions": ["container", "bug", "exception"],
            "routing": {"strategy": "hybrid", ...}
        }
    """
    try:
        from ..query_understanding import apply_query_intelligence

        result = apply_query_intelligence(
            query=query,
            expand_synonyms=expand_synonyms,
            correct_typos=correct_typos
        )

        return result

    except Exception as e:
        logger.error(f"Query enhancement failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context/{project}")
async def get_project_context(
    project: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours to look back"),
    types: Optional[str] = Query(default=None, description="Comma-separated memory types"),
    include_documents: bool = Query(default=True, description="Include relevant documents"),
    document_limit: int = Query(default=5, ge=0, le=20, description="Max documents to return")
):
    """Get relevant context memories and documents for a project."""
    type_list = None
    if types:
        type_list = [MemoryType(t.strip()) for t in types.split(",")]

    context = collections.get_context(
        project=project if project != "_all" else None,
        hours=hours,
        types=type_list,
        include_documents=include_documents,
        document_limit=document_limit
    )
    return context


@router.get("/context")
async def get_global_context(
    hours: int = Query(default=24, ge=1, le=168),
    types: Optional[str] = Query(default=None),
    include_documents: bool = Query(default=True, description="Include relevant documents"),
    document_limit: int = Query(default=5, ge=0, le=20, description="Max documents to return")
):
    """Get recent context memories and documents across all projects."""
    type_list = None
    if types:
        type_list = [MemoryType(t.strip()) for t in types.split(",")]

    context = collections.get_context(
        hours=hours,
        types=type_list,
        include_documents=include_documents,
        document_limit=document_limit
    )
    return context


@router.post("/memories/suggest")
async def suggest_memories(request: SuggestRequest):
    """
    Proactively suggest relevant memories based on current context.

    This endpoint is designed to be called at conversation start to surface
    potentially useful memories without explicit search queries.

    Returns memories ranked by:
    - Semantic relevance to context
    - Importance with time decay
    - Access frequency
    - Unresolved errors (high priority)
    """
    try:
        suggestions = collections.suggest_memories(
            project=request.project,
            keywords=request.keywords,
            current_files=request.current_files,
            git_branch=request.git_branch,
            limit=request.limit
        )

        # Format for response
        return {
            "suggestions": [
                {
                    "id": s["memory"].id,
                    "type": s["memory"].type.value,
                    "content": s["memory"].content[:200] + "..." if len(s["memory"].content) > 200 else s["memory"].content,
                    "tags": s["memory"].tags,
                    "project": s["memory"].project,
                    "relevance_score": round(s["relevance_score"], 3),
                    "decay_score": round(s["decay_score"], 3),
                    "combined_score": round(s["combined_score"], 3),
                    "reason": s["reason"],
                    "access_count": s["memory"].access_count,
                    "created_at": s["memory"].created_at.isoformat()
                }
                for s in suggestions
            ],
            "count": len(suggestions)
        }
    except Exception as e:
        logger.error(f"Suggest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
