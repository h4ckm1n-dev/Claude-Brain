"""Temporal query endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from .. import collections
from qdrant_client import models
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Temporal"])


@router.get("/temporal/valid-at")
async def get_memories_valid_at(
    target_time: str = Query(..., description="ISO 8601 timestamp (e.g., 2024-01-15T12:00:00Z)"),
    limit: int = Query(default=50, ge=1, le=1000),
    project: Optional[str] = None
):
    """Get memories that were valid at a specific point in time.

    A memory is valid at time T if:
    - validity_start <= T
    - validity_end is None OR validity_end > T

    Args:
        target_time: ISO 8601 timestamp
        limit: Maximum results
        project: Optional project filter

    Returns:
        List of memories valid at target_time
    """
    from ..temporal import TemporalQuery
    from datetime import datetime

    try:
        # Parse target time
        target_dt = datetime.fromisoformat(target_time.replace('Z', '+00:00'))

        # Get all memories (with project filter if specified)
        client = collections.get_client()
        query_filter = None
        if project:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="project",
                        match=models.MatchValue(value=project)
                    )
                ]
            )

        response = client.scroll(
            collection_name=collections.COLLECTION_NAME,
            scroll_filter=query_filter,
            limit=limit * 2,  # Get more to filter
            with_payload=True,
            with_vectors=False
        )

        # Filter to only memories valid at target_time
        all_memories = [point.payload for point in response[0]]
        valid_memories = TemporalQuery.filter_valid_at(all_memories, target_dt)

        return {
            "target_time": target_time,
            "count": len(valid_memories),
            "memories": valid_memories[:limit]
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp format: {e}")
    except Exception as e:
        logger.error(f"Failed to get memories valid at time: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/temporal/obsolete")
async def get_obsolete_memories(limit: int = Query(default=100, ge=1, le=1000)):
    """Get memories that are obsolete (validity_end in the past).

    Args:
        limit: Maximum results

    Returns:
        List of obsolete memories
    """
    from ..temporal import TemporalQuery

    try:
        client = collections.get_client()
        obsolete = TemporalQuery.get_obsolete_memories(
            client,
            collections.COLLECTION_NAME,
            limit=limit
        )

        return {
            "count": len(obsolete),
            "memories": obsolete
        }

    except Exception as e:
        logger.error(f"Failed to get obsolete memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/temporal/memories/{memory_id}/mark-obsolete")
async def mark_memory_as_obsolete(
    memory_id: str,
    validity_end: Optional[str] = Query(None, description="ISO 8601 timestamp (default: now)")
):
    """Mark a memory as obsolete by setting validity_end.

    Args:
        memory_id: Memory ID
        validity_end: When memory became obsolete (default: now)

    Returns:
        Success status
    """
    from ..temporal import mark_memory_obsolete
    from datetime import datetime

    try:
        client = collections.get_client()
        end_time = None

        if validity_end:
            try:
                end_time = datetime.fromisoformat(validity_end.replace('Z', '+00:00'))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid timestamp format: {e}")

        success = mark_memory_obsolete(
            client,
            collections.COLLECTION_NAME,
            memory_id,
            validity_end=end_time
        )

        if success:
            return {"success": True, "memory_id": memory_id, "validity_end": validity_end or "now"}
        else:
            raise HTTPException(status_code=404, detail="Memory not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark memory obsolete: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/temporal/stats")
async def get_temporal_statistics(project: Optional[str] = None):
    """Get temporal statistics about memories.

    Args:
        project: Optional project filter

    Returns:
        Temporal analysis including time distribution and validity stats
    """
    from ..temporal import TemporalAnalysis

    try:
        client = collections.get_client()

        # Get memories (with project filter if specified)
        query_filter = None
        if project:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="project",
                        match=models.MatchValue(value=project)
                    )
                ]
            )

        response = client.scroll(
            collection_name=collections.COLLECTION_NAME,
            scroll_filter=query_filter,
            limit=1000,  # Sample up to 1000 memories
            with_payload=True,
            with_vectors=False
        )

        memories = [point.payload for point in response[0]]

        # Analyze temporal distribution
        time_distribution = TemporalAnalysis.get_time_distribution(memories)
        validity_stats = TemporalAnalysis.get_validity_stats(memories)

        return {
            "project": project,
            "time_distribution": time_distribution,
            "validity_stats": validity_stats
        }

    except Exception as e:
        logger.error(f"Failed to get temporal stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/temporal/graph/{memory_id}/related-at")
async def get_temporally_related_memories(
    memory_id: str,
    target_time: str = Query(..., description="ISO 8601 timestamp"),
    max_hops: int = Query(default=2, ge=1, le=3),
    limit: int = Query(default=20, ge=1, le=100)
):
    """Get memories related to a given memory at a specific point in time.

    Only follows relationships that were valid at target_time.

    Args:
        memory_id: Starting memory ID
        target_time: ISO 8601 timestamp
        max_hops: Maximum relationship hops (1-3)
        limit: Maximum results

    Returns:
        List of related memories
    """
    from ..graph import get_related_memories_at_time, is_graph_enabled
    from datetime import datetime

    if not is_graph_enabled():
        raise HTTPException(status_code=503, detail="Neo4j graph not available")

    try:
        target_dt = datetime.fromisoformat(target_time.replace('Z', '+00:00'))

        related = get_related_memories_at_time(
            memory_id,
            target_dt,
            max_hops=max_hops,
            limit=limit
        )

        return {
            "memory_id": memory_id,
            "target_time": target_time,
            "count": len(related),
            "related_memories": related
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp format: {e}")
    except Exception as e:
        logger.error(f"Failed to get temporally-related memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))
