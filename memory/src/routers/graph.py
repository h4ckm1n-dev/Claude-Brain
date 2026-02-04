"""Knowledge graph endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Graph"])


@router.get("/graph/stats")
async def get_graph_statistics():
    """Get knowledge graph statistics."""
    from ..graph import get_graph_stats, is_graph_enabled

    if not is_graph_enabled():
        return {"enabled": False, "message": "Neo4j not available"}

    return get_graph_stats()


@router.get("/graph/related/{memory_id}")
async def get_related(
    memory_id: str,
    max_hops: int = Query(default=2, ge=1, le=3, description="Maximum relationship hops"),
    limit: int = Query(default=20, ge=1, le=100)
):
    """Get memories related to a given memory via graph traversal."""
    from ..graph import get_related_memories, is_graph_enabled

    if not is_graph_enabled():
        raise HTTPException(status_code=503, detail="Knowledge graph not available")

    related = get_related_memories(memory_id, max_hops=max_hops, limit=limit)
    return {"memory_id": memory_id, "related": related, "count": len(related)}


@router.get("/graph/timeline")
async def get_timeline(
    project: Optional[str] = Query(default=None),
    memory_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200)
):
    """Get memories ordered by time with their relationships."""
    from ..graph import get_memory_timeline, is_graph_enabled

    if not is_graph_enabled():
        raise HTTPException(status_code=503, detail="Knowledge graph not available")

    timeline = get_memory_timeline(project=project, memory_type=memory_type, limit=limit)
    return {"timeline": timeline, "count": len(timeline)}


@router.get("/graph/project/{project}")
async def get_project_graph(project: str):
    """Get the knowledge graph for a project."""
    from ..graph import get_project_knowledge_graph, is_graph_enabled

    if not is_graph_enabled():
        raise HTTPException(status_code=503, detail="Knowledge graph not available")

    graph = get_project_knowledge_graph(project)
    return {
        "project": project,
        "nodes": graph["nodes"],
        "edges": graph["edges"],
        "node_count": len(graph["nodes"]),
        "edge_count": len(graph["edges"])
    }


@router.get("/graph/solutions/{error_id}")
async def find_solutions(error_id: str):
    """Find solutions that fixed a specific error."""
    from ..graph import find_error_solutions, is_graph_enabled

    if not is_graph_enabled():
        raise HTTPException(status_code=503, detail="Knowledge graph not available")

    solutions = find_error_solutions(error_id)
    return {"error_id": error_id, "solutions": solutions, "count": len(solutions)}


@router.get("/graph/contradictions")
async def get_contradictions():
    """Detect contradictions in the knowledge graph.

    Finds cycles where A SUPPORTS B but B CONTRADICTS A, or similar
    conflicting relationship patterns.
    """
    from ..graph import detect_contradictions, is_graph_enabled

    if not is_graph_enabled():
        raise HTTPException(status_code=503, detail="Knowledge graph not available")

    try:
        contradictions = detect_contradictions()
        return {"contradictions": contradictions, "count": len(contradictions)}
    except Exception as e:
        logger.error(f"Failed to detect contradictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/recommendations/{memory_id}")
async def get_recommendations(
    memory_id: str,
    limit: int = Query(default=10, ge=1, le=50)
):
    """Get memory recommendations based on graph neighborhood.

    Uses collaborative filtering on the knowledge graph to find
    memories that are similar based on shared relationships.
    """
    from ..graph import get_recommendations as graph_get_recommendations, is_graph_enabled

    if not is_graph_enabled():
        raise HTTPException(status_code=503, detail="Knowledge graph not available")

    try:
        recommendations = graph_get_recommendations(memory_id, limit=limit)
        return {
            "memory_id": memory_id,
            "recommendations": recommendations,
            "count": len(recommendations)
        }
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
