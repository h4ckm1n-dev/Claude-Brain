"""Memory replay - spontaneous reactivation to strengthen memories.

Real brains spontaneously reactivate memories during rest/sleep to consolidate them.
This module implements memory replay to strengthen important memories automatically.
"""

import logging
import random
from typing import List, Dict
from datetime import datetime, timezone, timedelta

from .collections import get_client, COLLECTION_NAME
from .reconsolidation import reconsolidate_memory
from .relationship_inference import RelationshipInference

logger = logging.getLogger(__name__)


def replay_random_memories(
    count: int = 10,
    importance_threshold: float = 0.5
) -> Dict:
    """
    Spontaneously "recall" random important memories to strengthen them.

    Similar to how brains replay memories during sleep to consolidate learning.

    Args:
        count: Number of memories to replay
        importance_threshold: Only replay memories above this importance

    Returns:
        Replay statistics
    """
    client = get_client()

    try:
        from qdrant_client import models as qmodels

        # Get memories above importance threshold
        memories, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="importance",
                        range=qmodels.Range(gte=importance_threshold)
                    )
                ]
            ),
            limit=100
        )

        if len(memories) == 0:
            logger.info("No memories above importance threshold for replay")
            return {
                "replayed": 0,
                "relationships_discovered": 0
            }

        # Randomly select memories for replay
        replay_count = min(count, len(memories))
        selected = random.sample(memories, replay_count)

        replayed = 0
        relationships_discovered = 0

        for mem in selected:
            mem_id = str(mem.id)

            # "Recall" the memory (reconsolidate it, internal = no access_count bump)
            result = reconsolidate_memory(mem_id, internal=True)

            if result.get("success"):
                replayed += 1

                # During replay, discover new relationships
                # (simulate co-activation of related memories)
                payload = mem.payload
                tags = payload.get("tags", [])

                # Find other memories with similar tags
                similar_filter = qmodels.Filter(
                    should=[
                        qmodels.FieldCondition(
                            key="tags",
                            match=qmodels.MatchAny(any=tags[:3])  # Top 3 tags
                        )
                    ]
                ) if tags else None

                if similar_filter:
                    similar, _ = client.scroll(
                        collection_name=COLLECTION_NAME,
                        scroll_filter=similar_filter,
                        limit=5
                    )

                    # Reconsolidate with co-activated memories
                    co_ids = [str(s.id) for s in similar if str(s.id) != mem_id]
                    if co_ids:
                        reconsolidate_memory(
                            mem_id,
                            access_context="memory_replay",
                            co_accessed_ids=co_ids,
                            internal=True,
                        )
                        relationships_discovered += len(co_ids)

        logger.info(
            f"Replayed {replayed} memories, discovered {relationships_discovered} co-activations"
        )

        return {
            "replayed": replayed,
            "relationships_discovered": relationships_discovered,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Memory replay failed: {e}")
        return {
            "replayed": 0,
            "relationships_discovered": 0,
            "error": str(e)
        }


def targeted_replay(
    project: str,
    count: int = 10
) -> Dict:
    """
    Replay memories from a specific project.

    Useful for "reviewing" a project's knowledge.

    Args:
        project: Project name to replay
        count: Number of memories to replay

    Returns:
        Replay statistics
    """
    client = get_client()

    try:
        from qdrant_client import models as qmodels

        # Get project memories
        memories, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="project",
                        match=qmodels.MatchValue(value=project)
                    )
                ]
            ),
            limit=count
        )

        if len(memories) == 0:
            return {
                "replayed": 0,
                "project": project,
                "error": "No memories found for project"
            }

        # Replay all project memories
        replayed = 0
        mem_ids = [str(m.id) for m in memories]

        for i, mem in enumerate(memories):
            mem_id = str(mem.id)

            # Reconsolidate with other project memories as co-activated
            co_ids = [mid for mid in mem_ids if mid != mem_id]

            result = reconsolidate_memory(
                mem_id,
                access_context=f"project_review:{project}",
                co_accessed_ids=co_ids[:5],  # Top 5
                internal=True,
            )

            if result.get("success"):
                replayed += 1

        logger.info(f"Replayed {replayed} memories for project {project}")

        return {
            "replayed": replayed,
            "project": project,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Targeted replay failed for {project}: {e}")
        return {
            "replayed": 0,
            "project": project,
            "error": str(e)
        }


def replay_underutilized_memories(
    days_since_access: int = 7,
    count: int = 20
) -> Dict:
    """
    Replay memories that haven't been accessed recently.

    Prevents valuable but underutilized knowledge from fading.

    Args:
        days_since_access: Replay memories not accessed in this many days
        count: Number to replay

    Returns:
        Replay statistics
    """
    client = get_client()

    try:
        from qdrant_client import models as qmodels

        # Calculate cutoff time
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_since_access)

        # Get memories not accessed recently but important
        memories, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="importance",
                        range=qmodels.Range(gte=0.6)  # Important memories
                    )
                ]
            ),
            limit=200
        )

        # Filter by last access time
        underutilized = []
        for mem in memories:
            last_access = mem.payload.get("last_accessed_at")
            if not last_access:
                # Never accessed - definitely underutilized
                underutilized.append(mem)
            else:
                last_dt = datetime.fromisoformat(last_access.replace('Z', '+00:00'))
                if last_dt < cutoff:
                    underutilized.append(mem)

        if len(underutilized) == 0:
            return {
                "replayed": 0,
                "message": "No underutilized memories found"
            }

        # Select random sample
        replay_count = min(count, len(underutilized))
        selected = random.sample(underutilized, replay_count)

        replayed = 0
        for mem in selected:
            result = reconsolidate_memory(str(mem.id), internal=True)
            if result.get("success"):
                replayed += 1

        logger.info(
            f"Replayed {replayed} underutilized memories "
            f"(not accessed in {days_since_access} days)"
        )

        return {
            "replayed": replayed,
            "underutilized_found": len(underutilized),
            "days_threshold": days_since_access,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Underutilized replay failed: {e}")
        return {
            "replayed": 0,
            "error": str(e)
        }


def dream_mode_replay(duration_seconds: int = 30) -> Dict:
    """
    "Dream mode" - rapid random replay to discover unexpected connections.

    Simulates REM sleep where brain makes random associations.

    Args:
        duration_seconds: How long to run dream mode

    Returns:
        Dream statistics
    """
    import time

    start_time = time.time()
    replayed = 0
    new_relationships = 0

    try:
        while time.time() - start_time < duration_seconds:
            # Replay 5 random memories
            result = replay_random_memories(count=5, importance_threshold=0.3)

            replayed += result.get("replayed", 0)
            new_relationships += result.get("relationships_discovered", 0)

            # Short pause between batches
            time.sleep(1)

        logger.info(
            f"Dream mode completed: {replayed} memories replayed, "
            f"{new_relationships} new connections discovered"
        )

        return {
            "replayed": replayed,
            "new_relationships": new_relationships,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Dream mode failed: {e}")
        return {
            "replayed": replayed,
            "new_relationships": new_relationships,
            "error": str(e)
        }
