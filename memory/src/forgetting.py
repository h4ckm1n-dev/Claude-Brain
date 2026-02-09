"""Adaptive forgetting mechanism for memory management.

Implements FadeMem-inspired differential decay with automatic archival.

Key features:
- Differential decay: High-importance memories decay slower
- Access-based reinforcement: Frequently accessed memories strengthened
- Automatic archival: Low-strength memories automatically archived
- Configurable thresholds for archival and purging
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models

from .models import Memory, MemoryTier, utc_now

logger = logging.getLogger(__name__)

# Configuration
ARCHIVE_THRESHOLD = float(os.getenv("MEMORY_ARCHIVE_THRESHOLD", "0.15"))
PURGE_THRESHOLD = float(os.getenv("MEMORY_PURGE_THRESHOLD", "0.05"))
PURGE_ENABLED = os.getenv("MEMORY_PURGE_ENABLED", "false").lower() == "true"


def update_memory_strength(
    client: QdrantClient,
    collection_name: str,
    memory_id: str,
    memory: Memory
) -> dict:
    """
    Update memory strength for a single memory.

    Args:
        client: Qdrant client
        collection_name: Collection name
        memory_id: Memory ID
        memory: Memory object

    Returns:
        dict: Update result with old_strength, new_strength, action
    """
    # Calculate new strength
    old_strength = memory.memory_strength
    new_strength = memory.calculate_memory_strength()

    # Update the memory object
    memory.memory_strength = new_strength
    memory.last_decay_update = utc_now()

    # Recalculate decay rate (it may change based on access patterns)
    memory.decay_rate = memory.calculate_decay_rate()

    # Determine action
    action = "updated"
    if new_strength < PURGE_THRESHOLD and PURGE_ENABLED:
        action = "purge"
    elif new_strength < ARCHIVE_THRESHOLD:
        action = "archive"

    # Update in Qdrant
    try:
        from .collections import safe_set_payload
        safe_set_payload(
            memory_id,
            {
                "memory_strength": new_strength,
                "decay_rate": memory.decay_rate,
                "last_decay_update": memory.last_decay_update.isoformat(),
                "archived": action == "archive" or action == "purge"
            },
            collection_name=collection_name,
        )
    except Exception as e:
        logger.error(f"Failed to update memory {memory_id}: {e}")
        return {
            "memory_id": memory_id,
            "old_strength": old_strength,
            "new_strength": new_strength,
            "action": "error",
            "error": str(e)
        }

    return {
        "memory_id": memory_id,
        "old_strength": old_strength,
        "new_strength": new_strength,
        "action": action,
        "decay_rate": memory.decay_rate
    }


def update_all_memory_strengths(
    client: QdrantClient,
    collection_name: str,
    batch_size: int = 100,
    max_updates: Optional[int] = None
) -> dict:
    """
    Update memory strengths for all active memories.

    Args:
        client: Qdrant client
        collection_name: Collection name
        batch_size: Number of memories to process per batch
        max_updates: Maximum number of memories to update (None = all)

    Returns:
        dict: Statistics about the update operation
    """
    logger.info("Starting batch memory strength update...")

    stats = {
        "total_processed": 0,
        "updated": 0,
        "archived": 0,
        "purged": 0,
        "errors": 0,
        "avg_strength": 0.0,
        "min_strength": 1.0,
        "max_strength": 0.0
    }

    # Scroll through all active (non-archived) memories
    scroll_offset = None
    total_strength = 0.0

    while True:
        # Fetch batch
        try:
            results, scroll_offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="archived",
                            match=models.MatchValue(value=False)
                        )
                    ]
                ),
                limit=batch_size,
                offset=scroll_offset,
                with_payload=True
            )
        except Exception as e:
            logger.error(f"Failed to fetch batch: {e}")
            stats["errors"] += 1
            break

        if not results:
            break

        # Process each memory in batch
        for point in results:
            try:
                # Convert to Memory object
                from .collections import _point_to_memory
                memory = _point_to_memory(point)

                # Update strength
                result = update_memory_strength(
                    client, collection_name, str(point.id), memory
                )

                stats["total_processed"] += 1
                total_strength += result["new_strength"]

                # Update stats based on action
                if result["action"] == "updated":
                    stats["updated"] += 1
                elif result["action"] == "archive":
                    stats["archived"] += 1
                elif result["action"] == "purge":
                    stats["purged"] += 1
                    # Actually delete if purging
                    if PURGE_ENABLED:
                        client.delete(
                            collection_name=collection_name,
                            points_selector=models.PointIdsList(points=[str(point.id)])
                        )
                elif result["action"] == "error":
                    stats["errors"] += 1

                # Track min/max strength
                stats["min_strength"] = min(stats["min_strength"], result["new_strength"])
                stats["max_strength"] = max(stats["max_strength"], result["new_strength"])

            except Exception as e:
                logger.error(f"Failed to update memory {point.id}: {e}")
                stats["errors"] += 1

        # Check if we've hit the max updates limit
        if max_updates and stats["total_processed"] >= max_updates:
            break

        # If no more results, we're done
        if scroll_offset is None:
            break

    # Calculate average strength
    if stats["total_processed"] > 0:
        stats["avg_strength"] = total_strength / stats["total_processed"]

    logger.info(
        f"Memory strength update complete: "
        f"processed={stats['total_processed']}, "
        f"updated={stats['updated']}, "
        f"archived={stats['archived']}, "
        f"purged={stats['purged']}, "
        f"avg_strength={stats['avg_strength']:.3f}"
    )

    return stats


def reinforce_memory(
    client: QdrantClient,
    collection_name: str,
    memory_id: str,
    boost_amount: float = 0.2
) -> Optional[float]:
    """
    Reinforce a memory by boosting its strength (called on access).

    Args:
        client: Qdrant client
        collection_name: Collection name
        memory_id: Memory ID to reinforce
        boost_amount: Amount to boost strength by (default: 0.2)

    Returns:
        float: New memory strength, or None if failed
    """
    try:
        # Get current memory
        from .collections import get_memory
        memory = get_memory(memory_id)

        if not memory:
            return None

        # Don't reinforce pinned memories (already at max)
        if memory.pinned:
            return 1.0

        # Calculate current strength
        current_strength = memory.calculate_memory_strength()

        # Boost strength (capped at 1.0)
        new_strength = min(current_strength + boost_amount, 1.0)

        # Update in Qdrant
        client.set_payload(
            collection_name=collection_name,
            payload={
                "memory_strength": new_strength,
                "last_decay_update": utc_now().isoformat()
            },
            points=[memory_id]
        )

        logger.debug(f"Reinforced memory {memory_id}: {current_strength:.3f} -> {new_strength:.3f}")
        return new_strength

    except Exception as e:
        logger.error(f"Failed to reinforce memory {memory_id}: {e}")
        return None


def get_weak_memories(
    client: QdrantClient,
    collection_name: str,
    strength_threshold: float = 0.3,
    limit: int = 50
) -> list[dict]:
    """
    Get memories with low strength that are candidates for archival.

    Args:
        client: Qdrant client
        collection_name: Collection name
        strength_threshold: Strength threshold (default: 0.3)
        limit: Maximum number of results

    Returns:
        list[dict]: List of weak memories with metadata
    """
    try:
        results, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="archived",
                        match=models.MatchValue(value=False)
                    ),
                    models.FieldCondition(
                        key="pinned",
                        match=models.MatchValue(value=False)
                    ),
                    models.FieldCondition(
                        key="memory_strength",
                        range=models.Range(lte=strength_threshold)
                    )
                ]
            ),
            limit=limit,
            with_payload=True
        )

        weak_memories = []
        for point in results:
            from .collections import _point_to_memory
            memory = _point_to_memory(point)

            weak_memories.append({
                "id": str(point.id),
                "content": memory.content[:100],
                "type": memory.type.value,
                "memory_strength": memory.memory_strength,
                "decay_rate": memory.decay_rate,
                "access_count": memory.access_count,
                "created_at": memory.created_at.isoformat(),
                "last_accessed": memory.last_accessed.isoformat()
            })

        return weak_memories

    except Exception as e:
        logger.error(f"Failed to get weak memories: {e}")
        return []


def get_forgetting_stats(
    client: QdrantClient,
    collection_name: str
) -> dict:
    """
    Get statistics about memory strength distribution.

    Args:
        client: Qdrant client
        collection_name: Collection name

    Returns:
        dict: Statistics about memory strengths
    """
    try:
        # Get all active memories
        results, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="archived",
                        match=models.MatchValue(value=False)
                    )
                ]
            ),
            limit=10000,  # Large enough to get all
            with_payload=True
        )

        strengths = []
        decay_rates = []
        by_tier = {"episodic": [], "semantic": [], "procedural": []}

        for point in results:
            strength = point.payload.get("memory_strength", 1.0)
            decay_rate = point.payload.get("decay_rate", 0.005)
            tier = point.payload.get("memory_tier", "episodic")

            strengths.append(strength)
            decay_rates.append(decay_rate)
            by_tier[tier].append(strength)

        import statistics

        stats = {
            "total_memories": len(strengths),
            "avg_strength": statistics.mean(strengths) if strengths else 0.0,
            "median_strength": statistics.median(strengths) if strengths else 0.0,
            "min_strength": min(strengths) if strengths else 0.0,
            "max_strength": max(strengths) if strengths else 0.0,
            "avg_decay_rate": statistics.mean(decay_rates) if decay_rates else 0.0,
            "below_archive_threshold": sum(1 for s in strengths if s < ARCHIVE_THRESHOLD),
            "below_purge_threshold": sum(1 for s in strengths if s < PURGE_THRESHOLD),
            "by_tier": {
                tier: {
                    "count": len(values),
                    "avg_strength": statistics.mean(values) if values else 0.0
                }
                for tier, values in by_tier.items()
            },
            "config": {
                "archive_threshold": ARCHIVE_THRESHOLD,
                "purge_threshold": PURGE_THRESHOLD,
                "purge_enabled": PURGE_ENABLED
            }
        }

        return stats

    except Exception as e:
        logger.error(f"Failed to get forgetting stats: {e}")
        return {
            "error": str(e),
            "total_memories": 0
        }
