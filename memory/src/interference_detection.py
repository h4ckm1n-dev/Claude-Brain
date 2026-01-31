"""Interference detection - find and resolve conflicting memories.

Real brains actively detect and resolve conflicting information through
interference resolution. This module finds contradictory memories and
creates SUPERSEDES relationships to maintain knowledge coherence.
"""

import logging
import asyncio
from typing import List, Dict
from datetime import datetime

from .collections import get_client, COLLECTION_NAME
from .graph import create_relationship

logger = logging.getLogger(__name__)


class InterferenceDetection:
    """Detect conflicting memories and resolve contradictions."""

    # Contradiction patterns (positive, negative)
    CONTRADICTION_INDICATORS = [
        ("should use", "should not use"),
        ("best practice", "avoid"),
        ("recommended", "deprecated"),
        ("fixed", "still broken"),
        ("works", "doesn't work"),
        ("use", "never use"),
        ("always", "never"),
        ("correct", "incorrect"),
        ("required", "forbidden"),
        ("enabled", "disabled")
    ]

    # Similarity threshold for finding candidates
    SIMILARITY_THRESHOLD = 0.80

    @staticmethod
    async def detect_conflicts(limit: int = 50) -> List[Dict]:
        """
        Find pairs of memories that contradict each other.

        Args:
            limit: Maximum memories to analyze

        Returns:
            List of conflict pairs with resolution suggestions
        """
        client = get_client()

        try:
            # Get all memories
            memories, _ = client.scroll(
                collection_name=COLLECTION_NAME,
                limit=limit
            )

            conflicts = []

            for memory in memories:
                mem_id = str(memory.id)
                payload = memory.payload
                content = payload.get("content", "").lower()

                # Find similar memories (semantic search)
                similar = client.search(
                    collection_name=COLLECTION_NAME,
                    query_vector=memory.vector,
                    limit=10,
                    score_threshold=InterferenceDetection.SIMILARITY_THRESHOLD
                )

                # Check each similar memory for contradictions
                for candidate in similar:
                    if str(candidate.id) == mem_id:
                        continue  # Skip self

                    candidate_content = candidate.payload.get("content", "").lower()

                    # Check for contradiction indicators
                    for pos_pattern, neg_pattern in InterferenceDetection.CONTRADICTION_INDICATORS:
                        if pos_pattern in content and neg_pattern in candidate_content:
                            conflicts.append({
                                "memory_a": mem_id,
                                "memory_b": str(candidate.id),
                                "content_a": payload.get("content", "")[:200],
                                "content_b": candidate.payload.get("content", "")[:200],
                                "created_a": payload.get("created_at"),
                                "created_b": candidate.payload.get("created_at"),
                                "importance_a": payload.get("importance", 0.5),
                                "importance_b": candidate.payload.get("importance", 0.5),
                                "contradiction_type": f"{pos_pattern} vs {neg_pattern}"
                            })
                            break

            logger.info(f"Detected {len(conflicts)} potential conflicts")
            return conflicts

        except Exception as e:
            logger.error(f"Conflict detection failed: {e}")
            return []

    @staticmethod
    async def resolve_conflict(conflict: Dict) -> Dict:
        """
        Resolve a conflict by choosing the more authoritative memory.

        Strategy:
        1. Prefer newer memory (knowledge evolves)
        2. Prefer higher importance
        3. Prefer resolved errors over unresolved
        4. Create SUPERSEDES relationship

        Args:
            conflict: Conflict dict from detect_conflicts

        Returns:
            Resolution result with winner/loser/reason
        """
        client = get_client()

        try:
            mem_a_id = conflict["memory_a"]
            mem_b_id = conflict["memory_b"]

            # Compare timestamps
            created_a = datetime.fromisoformat(conflict["created_a"].replace('Z', '+00:00'))
            created_b = datetime.fromisoformat(conflict["created_b"].replace('Z', '+00:00'))
            newer_is_a = created_a > created_b

            # Compare importance
            importance_a = conflict["importance_a"]
            importance_b = conflict["importance_b"]

            # Resolution logic
            if abs(importance_a - importance_b) > 0.2:
                # Significant importance difference - trust higher importance
                winner = mem_a_id if importance_a > importance_b else mem_b_id
                loser = mem_b_id if importance_a > importance_b else mem_a_id
                reason = "higher_importance"
            else:
                # Similar importance - trust newer
                winner = mem_a_id if newer_is_a else mem_b_id
                loser = mem_b_id if newer_is_a else mem_a_id
                reason = "newer"

            # Create SUPERSEDES relationship (winner → loser)
            create_relationship(
                source_id=winner,
                target_id=loser,
                relation_type="SUPERSEDES"
            )

            # Mark the loser as superseded
            client.set_payload(
                collection_name=COLLECTION_NAME,
                points=[loser],
                payload={
                    "superseded": True,
                    "superseded_by": winner,
                    "superseded_at": datetime.now().isoformat()
                }
            )

            logger.info(
                f"Resolved conflict: {winner} SUPERSEDES {loser} (reason: {reason})"
            )

            return {
                "winner": winner,
                "loser": loser,
                "reason": reason
            }

        except Exception as e:
            logger.error(f"Conflict resolution failed: {e}")
            return {
                "winner": None,
                "loser": None,
                "reason": "error",
                "error": str(e)
            }


def run_interference_detection(limit: int = 50) -> Dict:
    """
    Detect and resolve memory conflicts.

    Run weekly via scheduler.

    Args:
        limit: Maximum memories to analyze

    Returns:
        Detection and resolution statistics
    """
    async def detect_and_resolve():
        # Detect conflicts
        conflicts = await InterferenceDetection.detect_conflicts(limit=limit)

        # Resolve each conflict
        resolutions = []
        for conflict in conflicts:
            resolution = await InterferenceDetection.resolve_conflict(conflict)
            if resolution.get("winner"):  # Only count successful resolutions
                resolutions.append(resolution)

        return {
            "conflicts_detected": len(conflicts),
            "conflicts_resolved": len(resolutions),
            "timestamp": datetime.now().isoformat()
        }

    try:
        result = asyncio.run(detect_and_resolve())
        logger.info(
            f"Interference detection complete: "
            f"{result['conflicts_detected']} detected, "
            f"{result['conflicts_resolved']} resolved"
        )
        return result

    except Exception as e:
        logger.error(f"Interference detection job failed: {e}")
        return {
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
            "error": str(e)
        }
