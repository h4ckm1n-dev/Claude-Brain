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
                detail="Session consolidation failed - may have <2 memories or already consolidated"
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
