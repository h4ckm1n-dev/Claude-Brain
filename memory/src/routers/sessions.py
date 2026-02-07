"""Session management endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from .. import collections
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Sessions"])


@router.get("/sessions/stats")
async def get_session_stats():
    """Get statistics about conversation sessions.

    Returns:
        Statistics including:
        - total_sessions: Number of conversation sessions
        - total_memories_in_sessions: Total memories with session tracking
        - avg_memories_per_session: Average memories per session
        - sessions_with_summary: Sessions that have been consolidated
        - sessions_without_summary: Sessions pending consolidation
        - config: Session timeout and consolidation settings
    """
    from ..session_extraction import SessionManager

    try:
        client = collections.get_client()
        stats = SessionManager.get_session_stats(client, collections.COLLECTION_NAME)
        return stats
    except Exception as e:
        logger.error(f"Failed to get session stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/memories")
async def get_session_memories(session_id: str):
    """Get all memories in a specific session, ordered by sequence.

    Args:
        session_id: Session identifier

    Returns:
        List of memories in session order with conversation flow
    """
    from ..session_extraction import SessionManager

    try:
        client = collections.get_client()
        memories = SessionManager.get_session_memories(
            client,
            collections.COLLECTION_NAME,
            session_id
        )
        return memories
    except Exception as e:
        logger.error(f"Failed to get session memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/consolidate")
async def consolidate_session(session_id: str):
    """Manually trigger consolidation for a specific session.

    This creates a summary memory (type: CONTEXT) that consolidates all
    memories in the session, then links them with PART_OF relationships.

    Also creates FOLLOWS relationships between sequential memories and
    identifies causal chains (ERROR -> LEARNING -> DECISION).

    Args:
        session_id: Session identifier

    Returns:
        Consolidation result including summary memory ID and link counts
    """
    from ..session_extraction import SessionManager

    try:
        client = collections.get_client()

        # Check if already consolidated — return existing summary (idempotent)
        existing_memories = SessionManager.get_session_memories(
            client, collections.COLLECTION_NAME, session_id
        )
        for mem in existing_memories:
            if mem.type.value == "context" and "session-summary" in (mem.tags or []):
                return {
                    "status": "consolidated",
                    "session_id": session_id,
                    "summary_id": mem.id,
                    "relationships_created": 0,
                    "already_consolidated": True,
                }

        # First, infer relationships within session
        links_created = SessionManager.infer_session_relationships(
            client,
            collections.COLLECTION_NAME,
            session_id
        )

        # Then consolidate
        summary_id = SessionManager.consolidate_session(
            client,
            collections.COLLECTION_NAME,
            session_id
        )

        if not summary_id:
            raise HTTPException(
                status_code=400,
                detail="Session consolidation failed - may have <2 memories"
            )

        return {
            "status": "consolidated",
            "session_id": session_id,
            "summary_id": summary_id,
            "relationships_created": links_created
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to consolidate session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/consolidate/batch")
async def consolidate_ready_sessions(
    older_than_hours: int = Query(default=24, ge=1, description="Consolidate sessions older than N hours")
):
    """Batch consolidate all sessions ready for consolidation.

    A session is ready if:
    1. It has >=2 memories
    2. Last memory was created >older_than_hours ago
    3. No summary memory exists yet

    Args:
        older_than_hours: Minimum age in hours (default: 24)

    Returns:
        Statistics about consolidation operation
    """
    from ..session_extraction import SessionManager

    try:
        client = collections.get_client()

        # Get sessions ready for consolidation
        ready_sessions = SessionManager.get_sessions_for_consolidation(
            client,
            collections.COLLECTION_NAME,
            older_than_hours=older_than_hours
        )

        consolidated = 0
        failed = 0
        results = []

        # Consolidate each session
        for session_id in ready_sessions:
            try:
                # Infer relationships
                links = SessionManager.infer_session_relationships(
                    client,
                    collections.COLLECTION_NAME,
                    session_id
                )

                # Consolidate
                summary_id = SessionManager.consolidate_session(
                    client,
                    collections.COLLECTION_NAME,
                    session_id
                )

                if summary_id:
                    consolidated += 1
                    results.append({
                        "session_id": session_id,
                        "summary_id": summary_id,
                        "status": "success",
                        "links_created": links
                    })
                else:
                    failed += 1
                    results.append({
                        "session_id": session_id,
                        "status": "failed",
                        "reason": "consolidation returned None"
                    })

            except Exception as e:
                failed += 1
                results.append({
                    "session_id": session_id,
                    "status": "error",
                    "error": str(e)
                })

        return {
            "total_ready": len(ready_sessions),
            "consolidated": consolidated,
            "failed": failed,
            "results": results
        }

    except Exception as e:
        logger.error(f"Batch consolidation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete all memories belonging to a session.

    Args:
        session_id: Session identifier

    Returns:
        Count of deleted memories
    """
    from qdrant_client import models as qmodels

    try:
        client = collections.get_client()

        # Count memories in this session first
        results, _ = client.scroll(
            collection_name=collections.COLLECTION_NAME,
            scroll_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="session_id",
                        match=qmodels.MatchValue(value=session_id)
                    )
                ]
            ),
            limit=10000,
            with_payload=False
        )

        if not results:
            raise HTTPException(status_code=404, detail="Session not found")

        point_ids = [r.id for r in results]

        # Clean up Neo4j graph nodes before deleting from Qdrant
        from ..graph import is_graph_enabled, delete_memory_node
        if is_graph_enabled():
            for pid in point_ids:
                try:
                    delete_memory_node(str(pid))
                except Exception as e:
                    logger.warning(f"Failed to delete graph node {pid}: {e}")

        # Delete all points with this session_id
        client.delete(
            collection_name=collections.COLLECTION_NAME,
            points_selector=qmodels.PointIdsList(points=point_ids)
        )

        return {
            "status": "deleted",
            "session_id": session_id,
            "memories_deleted": len(point_ids),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/close")
async def close_session(session_id: str):
    """Close a session: store an end memory, infer relationships, and consolidate.

    Steps:
    1. Store a session-end context memory
    2. Infer relationships within the session
    3. Consolidate into a summary (if >=2 memories)

    Args:
        session_id: Session identifier

    Returns:
        Close result with summary_id and memory count
    """
    from ..session_extraction import SessionManager
    from ..models import MemoryCreate, MemoryType

    try:
        client = collections.get_client()

        # Get existing session memories to determine project
        memories = SessionManager.get_session_memories(
            client, collections.COLLECTION_NAME, session_id
        )

        # Double-close guard — if session-end memory already exists, return existing state
        for mem in memories:
            if "session-end" in (mem.tags or []):
                # Find existing summary if any
                existing_summary_id = None
                for m in memories:
                    if m.type.value == "context" and "session-summary" in (m.tags or []):
                        existing_summary_id = m.id
                        break
                return {
                    "status": "closed",
                    "session_id": session_id,
                    "memory_count": len(memories),
                    "summary_id": existing_summary_id,
                    "relationships_created": 0,
                    "consolidated": existing_summary_id is not None,
                    "already_closed": True,
                }

        project = None
        for mem in memories:
            if mem.project:
                project = mem.project
                break

        # Store session-end memory
        end_memory = MemoryCreate(
            type=MemoryType.CONTEXT,
            content=f"Session closed at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}. "
                    f"Session had {len(memories)} memories"
                    f"{' for project ' + project if project else ''}.",
            tags=["auto-captured", "session-end"],
            project=project,
            session_id=session_id,
        )
        collections.store_memory(end_memory, deduplicate=False)

        # Infer relationships within session
        links_created = 0
        try:
            links_created = SessionManager.infer_session_relationships(
                client, collections.COLLECTION_NAME, session_id
            )
        except Exception as e:
            logger.warning(f"Relationship inference failed for {session_id}: {e}")

        # Consolidate if enough memories (now including the end memory)
        summary_id = None
        total_memories = len(memories) + 1  # +1 for the end memory we just stored
        if total_memories >= 2:
            try:
                summary_id = SessionManager.consolidate_session(
                    client, collections.COLLECTION_NAME, session_id
                )
            except Exception as e:
                logger.warning(f"Consolidation failed for {session_id}: {e}")

        return {
            "status": "closed",
            "session_id": session_id,
            "memory_count": total_memories,
            "summary_id": summary_id,
            "relationships_created": links_created,
            "consolidated": summary_id is not None,
        }

    except Exception as e:
        logger.error(f"Failed to close session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/new")
async def create_new_session(project: Optional[str] = None):
    """Create a new conversation session.

    Args:
        project: Optional project name to associate with session

    Returns:
        New session ID
    """
    from ..session_extraction import SessionManager

    try:
        session_id = SessionManager.generate_session_id()
        return {
            "session_id": session_id,
            "project": project,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
