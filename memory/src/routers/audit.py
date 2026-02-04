"""Audit trail, versioning, and restore endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from .. import collections
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Audit"])


@router.get("/audit/{memory_id}")
async def get_memory_audit_trail(
    memory_id: str,
    limit: int = Query(default=100, ge=1, le=500, description="Maximum entries to return")
):
    """Get audit trail for a specific memory.

    Args:
        memory_id: Memory ID
        limit: Maximum entries

    Returns:
        Audit trail entries
    """
    from ..audit import AuditLogger

    try:
        client = collections.get_client()

        entries = AuditLogger.get_audit_trail(
            client,
            memory_id=memory_id,
            limit=limit
        )

        return {
            "memory_id": memory_id,
            "total_entries": len(entries),
            "entries": [entry.to_dict() for entry in entries]
        }

    except Exception as e:
        logger.error(f"Failed to get audit trail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit")
async def get_audit_trail(
    action: Optional[str] = Query(default=None, description="Filter by action type"),
    actor: Optional[str] = Query(default=None, description="Filter by actor"),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum entries to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset")
):
    """Get recent audit trail entries across all memories.

    Args:
        action: Filter by action type
        actor: Filter by actor
        limit: Maximum entries
        offset: Pagination offset

    Returns:
        Audit trail entries
    """
    from ..audit import AuditLogger, AuditAction

    try:
        client = collections.get_client()

        # Parse action if provided
        action_enum = None
        if action:
            try:
                action_enum = AuditAction(action.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid action '{action}'. Valid actions: {[a.value for a in AuditAction]}"
                )

        entries = AuditLogger.get_audit_trail(
            client,
            action=action_enum,
            actor=actor,
            limit=limit,
            offset=offset
        )

        return {
            "total_entries": len(entries),
            "offset": offset,
            "limit": limit,
            "entries": [entry.to_dict() for entry in entries]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit trail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/stats")
async def get_audit_statistics(
    memory_id: Optional[str] = Query(default=None, description="Filter by memory ID")
):
    """Get audit trail statistics.

    Args:
        memory_id: Optional memory ID filter

    Returns:
        Audit statistics
    """
    from ..audit import AuditLogger

    try:
        client = collections.get_client()

        stats = AuditLogger.get_audit_statistics(
            client,
            memory_id=memory_id
        )

        return stats

    except Exception as e:
        logger.error(f"Failed to get audit statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memories/{memory_id}/versions")
async def get_restorable_versions(memory_id: str):
    """Get list of restorable versions for a memory.

    Args:
        memory_id: Memory ID

    Returns:
        List of restorable versions with metadata
    """
    from ..audit import RestoreManager

    try:
        # Verify memory exists
        memory = collections.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        client = collections.get_client()

        versions = RestoreManager.get_restorable_versions(
            client,
            memory_id
        )

        return {
            "memory_id": memory_id,
            "total_versions": len(versions),
            "versions": versions
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get restorable versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memories/{memory_id}/restore")
async def restore_memory_version(
    memory_id: str,
    target_timestamp: str = Query(..., description="Timestamp to restore to (ISO format)"),
    actor: str = Query(default="system", description="Who is performing the restore")
):
    """Restore a memory to a previous version.

    Args:
        memory_id: Memory ID
        target_timestamp: Timestamp to restore to
        actor: Who is performing the restore

    Returns:
        Restore result
    """
    from ..audit import RestoreManager

    try:
        # Verify memory exists
        memory = collections.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        client = collections.get_client()

        result = RestoreManager.restore_to_version(
            client,
            collections.COLLECTION_NAME,
            memory_id,
            target_timestamp,
            actor
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Restore failed")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memories/{memory_id}/undo")
async def undo_last_change(
    memory_id: str,
    actor: str = Query(default="system", description="Who is performing the undo")
):
    """Undo the last change to a memory.

    Args:
        memory_id: Memory ID
        actor: Who is performing the undo

    Returns:
        Undo result
    """
    from ..audit import RestoreManager

    try:
        # Verify memory exists
        memory = collections.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        client = collections.get_client()

        result = RestoreManager.undo_last_change(
            client,
            collections.COLLECTION_NAME,
            memory_id,
            actor
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Undo failed")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to undo last change: {e}")
        raise HTTPException(status_code=500, detail=str(e))
