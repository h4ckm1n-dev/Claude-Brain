"""Memory reconsolidation - memories evolve when accessed.

Real brains don't just retrieve memories - they modify them during recall.
This module implements reconsolidation to make memories "alive".
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .collections import get_client, COLLECTION_NAME
from .graph import create_relationship, get_related_memories

logger = logging.getLogger(__name__)


def reconsolidate_memory(
    memory_id: str,
    access_context: Optional[str] = None,
    co_accessed_ids: Optional[list[str]] = None
) -> dict:
    """
    Reconsolidate a memory when accessed - strengthen it and its relationships.

    This simulates how real brains modify memories during recall:
    1. Update access metadata
    2. Strengthen related memories (co-activation)
    3. Create new relationships based on context
    4. Boost importance if frequently recalled

    Args:
        memory_id: ID of memory being accessed
        access_context: Current context (e.g., current project, task)
        co_accessed_ids: Other memories accessed in same session

    Returns:
        dict with reconsolidation results
    """
    client = get_client()

    try:
        # Get current memory
        points = client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[memory_id]
        )

        if not points:
            return {"success": False, "error": "Memory not found"}

        point = points[0]
        payload = point.payload

        # Update access metadata
        access_count = payload.get("access_count", 0) + 1
        last_accessed = datetime.now(timezone.utc).isoformat()

        # Calculate access interval (for spaced repetition)
        previous_access = payload.get("last_accessed_at")
        if previous_access:
            prev_dt = datetime.fromisoformat(previous_access.replace('Z', '+00:00'))
            interval_hours = (datetime.now(timezone.utc) - prev_dt).total_seconds() / 3600
        else:
            interval_hours = None

        # Track access intervals for spaced repetition
        intervals = payload.get("access_intervals", [])
        if interval_hours is not None:
            intervals.append(interval_hours)
            # Keep last 10 intervals
            intervals = intervals[-10:]

        # Boost importance based on access pattern
        current_importance = payload.get("importance", 0.5)

        # Frequent recent access = more important
        if access_count > 5 and interval_hours and interval_hours < 24:
            importance_boost = min(0.1, 0.02 * access_count)
            new_importance = min(1.0, current_importance + importance_boost)
        else:
            new_importance = current_importance

        # Update payload
        updated_payload = {
            "access_count": access_count,
            "last_accessed_at": last_accessed,
            "access_intervals": intervals,
            "importance": new_importance,
        }

        # Track co-accessed memories for future importance boosting
        if co_accessed_ids:
            co_accessed = payload.get("co_accessed_with", [])
            # Add new co-accessed memories
            for cid in co_accessed_ids:
                if cid != memory_id and cid not in co_accessed:
                    co_accessed.append(cid)
            # Keep last 20
            updated_payload["co_accessed_with"] = co_accessed[-20:]

        # Update in Qdrant
        client.set_payload(
            collection_name=COLLECTION_NAME,
            points=[memory_id],
            payload=updated_payload
        )

        # Strengthen relationships to co-accessed memories
        new_links = 0
        if co_accessed_ids:
            for cid in co_accessed_ids[:5]:  # Top 5 co-accessed
                if cid != memory_id:
                    # Create CO_ACTIVATED relationship
                    if create_relationship(
                        source_id=memory_id,
                        target_id=cid,
                        relation_type="co_activated",
                        properties={"access_context": access_context}
                    ):
                        new_links += 1

        logger.info(
            f"Reconsolidated memory {memory_id}: "
            f"access_count={access_count}, importance={new_importance:.2f}, "
            f"new_links={new_links}"
        )

        return {
            "success": True,
            "memory_id": memory_id,
            "access_count": access_count,
            "importance": new_importance,
            "importance_change": new_importance - current_importance,
            "new_relationships": new_links,
            "interval_hours": interval_hours
        }

    except Exception as e:
        logger.error(f"Reconsolidation failed for {memory_id}: {e}")
        return {"success": False, "error": str(e)}


def get_spaced_repetition_candidates(limit: int = 10) -> list[dict]:
    """
    Get memories that should be reviewed based on spaced repetition.

    Implements forgetting curve - memories need reinforcement at specific intervals:
    - 1 hour, 1 day, 1 week, 1 month

    Returns:
        List of memories due for review
    """
    client = get_client()

    try:
        from qdrant_client import models as qmodels
        from datetime import timedelta

        now = datetime.now(timezone.utc)

        # Get all memories with access history
        memories, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000,
            scroll_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="access_count",
                        range=qmodels.Range(gte=1)
                    )
                ]
            )
        )

        candidates = []

        for mem in memories:
            payload = mem.payload
            last_access = payload.get("last_accessed_at")
            if not last_access:
                continue

            last_dt = datetime.fromisoformat(last_access.replace('Z', '+00:00'))
            hours_since = (now - last_dt).total_seconds() / 3600

            # Spaced repetition intervals (hours)
            intervals = [1, 24, 168, 720]  # 1h, 1d, 1w, 1mo

            # Check if due for review
            access_count = payload.get("access_count", 0)
            interval_index = min(access_count - 1, len(intervals) - 1)
            target_interval = intervals[interval_index]

            # Due if past target interval
            if hours_since >= target_interval:
                candidates.append({
                    "id": str(mem.id),
                    "content": payload.get("content", "")[:100],
                    "hours_since_access": hours_since,
                    "target_interval": target_interval,
                    "access_count": access_count,
                    "importance": payload.get("importance", 0.5)
                })

        # Sort by importance * how overdue
        candidates.sort(
            key=lambda x: x["importance"] * (x["hours_since_access"] / x["target_interval"]),
            reverse=True
        )

        return candidates[:limit]

    except Exception as e:
        logger.error(f"Failed to get spaced repetition candidates: {e}")
        return []
