"""Temporal query utilities for bi-temporal memory model.

Implements Phase 2.2: Bi-temporal Model (Graphiti-style)
- event_time: When the event actually occurred
- ingestion_time (created_at): When memory was stored
- validity_start/validity_end: Validity window for the memory

Enables:
- Search memories valid at specific time
- Find memories learned in last N days
- Detect obsolete memories
- Temporal graph traversal (valid relationships at specific time)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class TemporalQuery:
    """Utilities for temporal memory queries."""

    @staticmethod
    def build_temporal_filter(
        valid_at: Optional[datetime] = None,
        ingested_after: Optional[datetime] = None,
        ingested_before: Optional[datetime] = None,
        event_after: Optional[datetime] = None,
        event_before: Optional[datetime] = None,
        include_obsolete: bool = False
    ) -> List[models.FieldCondition]:
        """
        Build Qdrant filter conditions for temporal queries.

        Args:
            valid_at: Find memories valid at this specific time
            ingested_after: Find memories learned after this time
            ingested_before: Find memories learned before this time
            event_after: Find memories with event_time after this time
            event_before: Find memories with event_time before this time
            include_obsolete: Whether to include memories with validity_end in the past

        Returns:
            List of Qdrant field conditions
        """
        conditions = []

        # Validity window filter (valid_at time)
        if valid_at:
            # Memory is valid at time T if: validity_start <= T AND (validity_end is NULL OR validity_end > T)
            conditions.append(
                models.FieldCondition(
                    key="validity_start",
                    range=models.DatetimeRange(lte=valid_at)
                )
            )
            # Note: Qdrant doesn't support complex OR conditions in single filter
            # We'll filter validity_end in post-processing

        # Ingestion time filters (when memory was stored)
        if ingested_after:
            conditions.append(
                models.FieldCondition(
                    key="created_at",
                    range=models.DatetimeRange(gte=ingested_after)
                )
            )

        if ingested_before:
            conditions.append(
                models.FieldCondition(
                    key="created_at",
                    range=models.DatetimeRange(lte=ingested_before)
                )
            )

        # Event time filters (when the event occurred)
        if event_after:
            conditions.append(
                models.FieldCondition(
                    key="event_time",
                    range=models.DatetimeRange(gte=event_after)
                )
            )

        if event_before:
            conditions.append(
                models.FieldCondition(
                    key="event_time",
                    range=models.DatetimeRange(lte=event_before)
                )
            )

        # Exclude obsolete memories (unless explicitly included)
        if not include_obsolete:
            # Filter out memories with validity_end in the past
            # This is tricky in Qdrant - we'll do post-processing
            pass

        return conditions

    @staticmethod
    def is_valid_at(memory: Dict[str, Any], target_time: datetime) -> bool:
        """
        Check if a memory is valid at a specific time.

        A memory is valid at time T if:
        - validity_start <= T
        - validity_end is None OR validity_end > T

        Args:
            memory: Memory dict with temporal fields
            target_time: Time to check validity

        Returns:
            True if memory is valid at target_time
        """
        validity_start = memory.get("validity_start")
        validity_end = memory.get("validity_end")

        # Convert strings to datetime if needed
        if isinstance(validity_start, str):
            validity_start = datetime.fromisoformat(validity_start.replace('Z', '+00:00'))
        if isinstance(validity_end, str):
            validity_end = datetime.fromisoformat(validity_end.replace('Z', '+00:00'))

        # Check validity window
        if validity_start and validity_start > target_time:
            return False

        if validity_end and validity_end <= target_time:
            return False

        return True

    @staticmethod
    def filter_valid_at(memories: List[Dict], target_time: datetime) -> List[Dict]:
        """
        Filter a list of memories to only those valid at target_time.

        Args:
            memories: List of memory dicts
            target_time: Time to check validity

        Returns:
            Filtered list of memories
        """
        return [
            mem for mem in memories
            if TemporalQuery.is_valid_at(mem, target_time)
        ]

    @staticmethod
    def is_obsolete(memory: Dict[str, Any]) -> bool:
        """
        Check if a memory is obsolete (validity_end in the past).

        Args:
            memory: Memory dict with temporal fields

        Returns:
            True if memory is obsolete
        """
        validity_end = memory.get("validity_end")

        if not validity_end:
            return False

        # Convert string to datetime if needed
        if isinstance(validity_end, str):
            validity_end = datetime.fromisoformat(validity_end.replace('Z', '+00:00'))

        return validity_end <= utc_now()

    @staticmethod
    def get_obsolete_memories(
        client: QdrantClient,
        collection_name: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Find all obsolete memories (validity_end in the past).

        Args:
            client: Qdrant client
            collection_name: Collection name
            limit: Maximum results

        Returns:
            List of obsolete memories
        """
        try:
            # Search for memories with validity_end set
            # Note: Qdrant doesn't have good support for "field is not null"
            # So we search all and filter in Python
            response = client.scroll(
                collection_name=collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )

            memories = []
            for point in response[0]:  # response is (points, next_offset)
                payload = point.payload
                if TemporalQuery.is_obsolete(payload):
                    memories.append(payload)

            return memories

        except Exception as e:
            logger.error(f"Failed to get obsolete memories: {e}")
            return []

    @staticmethod
    def infer_event_time(memory: Dict[str, Any]) -> Optional[datetime]:
        """
        Infer event_time from memory content if not explicitly provided.

        Heuristics:
        - Errors: Use created_at (error happened when reported)
        - Decisions: Use created_at (decision made at storage time)
        - Patterns: No specific event time (pattern is timeless)
        - Learning: Use created_at (learned at storage time)
        - Context: Use created_at
        - Docs: Use source date if available, else None

        Args:
            memory: Memory dict

        Returns:
            Inferred event_time or None
        """
        memory_type = memory.get("type", "context")
        created_at = memory.get("created_at")

        # Convert created_at string to datetime if needed
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        # Type-based inference
        if memory_type in ["error", "decision", "learning", "context"]:
            # These types typically refer to events at storage time
            return created_at
        elif memory_type == "pattern":
            # Patterns are timeless - no specific event time
            return None
        elif memory_type == "docs":
            # Docs may reference past documentation, use created_at as fallback
            return created_at

        return None

    @staticmethod
    def set_default_temporal_fields(memory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set default temporal fields for a memory if not provided.

        - event_time: Inferred from type and content
        - validity_start: created_at (memory is valid from when it's stored)
        - validity_end: None (memory is valid indefinitely by default)

        Args:
            memory: Memory dict (modified in place)

        Returns:
            Modified memory dict
        """
        created_at = memory.get("created_at") or utc_now()

        # Set event_time if not provided
        if not memory.get("event_time"):
            memory["event_time"] = TemporalQuery.infer_event_time(memory)

        # Set validity_start if not provided (default: created_at)
        if not memory.get("validity_start"):
            memory["validity_start"] = created_at

        # validity_end defaults to None (indefinite validity)

        return memory


class TemporalAnalysis:
    """Temporal analysis utilities for memory patterns."""

    @staticmethod
    def get_time_distribution(memories: List[Dict]) -> Dict[str, Any]:
        """
        Analyze time distribution of memories.

        Returns:
        - count by hour of day
        - count by day of week
        - count by month
        - average age
        - oldest/newest memory

        Args:
            memories: List of memory dicts

        Returns:
            Dict with temporal statistics
        """
        if not memories:
            return {
                "total_count": 0,
                "by_hour": {},
                "by_day_of_week": {},
                "by_month": {},
                "avg_age_days": 0,
                "oldest": None,
                "newest": None
            }

        from collections import defaultdict
        by_hour = defaultdict(int)
        by_day = defaultdict(int)
        by_month = defaultdict(int)

        oldest = None
        newest = None
        ages = []

        for mem in memories:
            created_at = mem.get("created_at")
            if not created_at:
                continue

            # Convert string to datetime if needed
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

            # Track oldest/newest
            if not oldest or created_at < oldest:
                oldest = created_at
            if not newest or created_at > newest:
                newest = created_at

            # Calculate age
            age_days = (utc_now() - created_at).total_seconds() / 86400
            ages.append(age_days)

            # Distribution by time
            by_hour[created_at.hour] += 1
            by_day[created_at.strftime("%A")] += 1
            by_month[created_at.strftime("%Y-%m")] += 1

        avg_age = sum(ages) / len(ages) if ages else 0

        return {
            "total_count": len(memories),
            "by_hour": dict(by_hour),
            "by_day_of_week": dict(by_day),
            "by_month": dict(by_month),
            "avg_age_days": round(avg_age, 2),
            "oldest": oldest.isoformat() if oldest else None,
            "newest": newest.isoformat() if newest else None
        }

    @staticmethod
    def get_validity_stats(memories: List[Dict]) -> Dict[str, Any]:
        """
        Analyze validity windows of memories.

        Returns:
        - count of obsolete memories
        - count of indefinite memories
        - average validity duration
        - memories expiring soon

        Args:
            memories: List of memory dicts

        Returns:
            Dict with validity statistics
        """
        obsolete_count = 0
        indefinite_count = 0
        validity_durations = []
        expiring_soon = []  # Expiring within 7 days

        now = utc_now()
        week_from_now = now + timedelta(days=7)

        for mem in memories:
            validity_end = mem.get("validity_end")

            if not validity_end:
                indefinite_count += 1
                continue

            # Convert string to datetime if needed
            if isinstance(validity_end, str):
                validity_end = datetime.fromisoformat(validity_end.replace('Z', '+00:00'))

            # Check if obsolete
            if validity_end <= now:
                obsolete_count += 1
            elif validity_end <= week_from_now:
                expiring_soon.append({
                    "id": mem.get("id"),
                    "content": mem.get("content", "")[:100],
                    "expires_at": validity_end.isoformat(),
                    "days_remaining": (validity_end - now).total_seconds() / 86400
                })

            # Calculate validity duration
            validity_start = mem.get("validity_start")
            if validity_start:
                if isinstance(validity_start, str):
                    validity_start = datetime.fromisoformat(validity_start.replace('Z', '+00:00'))

                duration_days = (validity_end - validity_start).total_seconds() / 86400
                validity_durations.append(duration_days)

        avg_duration = sum(validity_durations) / len(validity_durations) if validity_durations else 0

        return {
            "total_count": len(memories),
            "obsolete_count": obsolete_count,
            "indefinite_count": indefinite_count,
            "expiring_soon_count": len(expiring_soon),
            "avg_validity_duration_days": round(avg_duration, 2),
            "expiring_soon": expiring_soon[:10]  # Top 10
        }


def mark_memory_obsolete(
    client: QdrantClient,
    collection_name: str,
    memory_id: str,
    validity_end: Optional[datetime] = None
) -> bool:
    """
    Mark a memory as obsolete by setting validity_end.

    Args:
        client: Qdrant client
        collection_name: Collection name
        memory_id: Memory ID to mark obsolete
        validity_end: When memory became obsolete (default: now)

    Returns:
        True if successful
    """
    try:
        end_time = validity_end or utc_now()

        client.set_payload(
            collection_name=collection_name,
            payload={"validity_end": end_time.isoformat()},
            points=[memory_id]
        )

        logger.info(f"Marked memory {memory_id} as obsolete (validity_end: {end_time})")
        return True

    except Exception as e:
        logger.error(f"Failed to mark memory obsolete: {e}")
        return False


def extend_validity(
    client: QdrantClient,
    collection_name: str,
    memory_id: str,
    new_validity_end: datetime
) -> bool:
    """
    Extend or modify the validity window of a memory.

    Args:
        client: Qdrant client
        collection_name: Collection name
        memory_id: Memory ID
        new_validity_end: New expiration time

    Returns:
        True if successful
    """
    try:
        client.set_payload(
            collection_name=collection_name,
            payload={"validity_end": new_validity_end.isoformat()},
            points=[memory_id]
        )

        logger.info(f"Extended validity for memory {memory_id} to {new_validity_end}")
        return True

    except Exception as e:
        logger.error(f"Failed to extend validity: {e}")
        return False
