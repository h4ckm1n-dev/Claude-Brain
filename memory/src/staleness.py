"""Memory staleness detection engine.

Detects when memories become outdated through multiple signals:
- Semantic conflict: new memory contradicts existing knowledge
- Supersession cascade: memory superseded by newer version
- Access divergence: active project but memory untouched
- Drift detection: memory embedding drifted from project centroid
- Tag activity gap: tag has new memories but old ones stale
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models

from .models import Memory, utc_now

logger = logging.getLogger(__name__)

# Staleness signal weights
CONFLICT_STALENESS = 0.3
SUPERSEDE_STALENESS = 0.8
ACCESS_DIVERGENCE_STALENESS = 0.2
DRIFT_STALENESS = 0.3
TAG_GAP_STALENESS = 0.15

# Thresholds
SIMILARITY_CONFLICT_THRESHOLD = 0.85  # Cosine sim for semantic conflict
ACCESS_DIVERGENCE_DAYS = 30           # Days without access in active project
DRIFT_DISTANCE_THRESHOLD = 0.3       # Cosine distance for drift detection
FRESHNESS_RECOVERY = 0.4             # Staleness reduction on access


def check_staleness_on_write(
    client: QdrantClient,
    collection_name: str,
    new_memory: Memory,
    new_embedding: list[float],
) -> list[dict]:
    """Check if the new memory makes existing memories stale.

    Called during store_memory() to detect on-write staleness signals.

    Returns:
        List of {memory_id, old_score, new_score, reason} for updated memories.
    """
    updates = []

    try:
        # Find semantically similar existing memories
        similar = client.query_points(
            collection_name=collection_name,
            query=new_embedding,
            using="dense",
            limit=10,
            score_threshold=SIMILARITY_CONFLICT_THRESHOLD,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="archived", match=models.MatchValue(value=False)
                    )
                ],
                must_not=[
                    models.FieldCondition(
                        key="id", match=models.MatchValue(value=new_memory.id)
                    )
                ],
            ),
            with_payload=["staleness_score", "staleness_reasons", "type",
                          "content", "solution", "project", "tags"],
        )

        for point in similar.points:
            old_score = point.payload.get("staleness_score", 0.0)
            old_reasons = point.payload.get("staleness_reasons", [])
            bump = 0.0
            reasons = list(old_reasons)

            existing_type = point.payload.get("type", "")
            existing_content = point.payload.get("content", "")

            # Signal 1: Semantic conflict — same type, high similarity, different content
            if (existing_type == new_memory.type.value
                    and point.score >= SIMILARITY_CONFLICT_THRESHOLD
                    and _content_diverged(existing_content, new_memory.content)):
                bump += CONFLICT_STALENESS
                reason = f"semantic_conflict: new memory {new_memory.id[:8]} covers same topic"
                if reason not in reasons:
                    reasons.append(reason)

            # Signal 2: Solution conflict — existing has solution, new has different one
            existing_solution = point.payload.get("solution")
            if (existing_solution and new_memory.solution
                    and existing_solution != new_memory.solution
                    and point.score >= SIMILARITY_CONFLICT_THRESHOLD):
                bump += CONFLICT_STALENESS
                reason = f"solution_conflict: newer solution in {new_memory.id[:8]}"
                if reason not in reasons:
                    reasons.append(reason)

            if bump > 0:
                new_score = min(old_score + bump, 1.0)
                _update_staleness(
                    client, collection_name,
                    str(point.id), new_score, reasons
                )
                updates.append({
                    "memory_id": str(point.id),
                    "old_score": old_score,
                    "new_score": new_score,
                    "reason": reasons[-1],
                })

    except Exception as e:
        logger.warning(f"Staleness on-write check failed: {e}")

    return updates


def on_supersede(
    client: QdrantClient,
    collection_name: str,
    loser_id: str,
) -> None:
    """Called when a memory is superseded — set high staleness."""
    try:
        _update_staleness(
            client, collection_name, loser_id,
            SUPERSEDE_STALENESS,
            [f"superseded: replaced by newer memory"],
        )
    except Exception as e:
        logger.warning(f"Staleness supersede update failed for {loser_id}: {e}")


def reduce_staleness_on_access(
    client: QdrantClient,
    collection_name: str,
    memory_id: str,
) -> None:
    """Reduce staleness when a memory is accessed (search hit, reinforce).

    Prevents false positives from staying permanently flagged.
    """
    try:
        points = client.retrieve(
            collection_name=collection_name,
            ids=[memory_id],
            with_payload=["staleness_score", "staleness_reasons"],
            with_vectors=False,
        )
        if not points:
            return

        old_score = points[0].payload.get("staleness_score", 0.0)
        if old_score <= 0.0:
            return

        new_score = max(0.0, old_score - FRESHNESS_RECOVERY)
        reasons = points[0].payload.get("staleness_reasons", [])
        if new_score == 0.0:
            reasons = []

        _update_staleness(client, collection_name, memory_id, new_score, reasons)
        logger.debug(f"Staleness reduced for {memory_id}: {old_score:.2f} -> {new_score:.2f}")

    except Exception as e:
        logger.debug(f"Failed to reduce staleness for {memory_id}: {e}")


def run_staleness_sweep(
    client: QdrantClient,
    collection_name: str,
    max_memories: int = 500,
) -> dict:
    """Periodic sweep for staleness signals that can't be detected on-write.

    Checks:
    1. Access divergence: active project, memory untouched 30+ days
    2. Drift detection: embedding distance from recent project centroid
    3. Tag activity gap: tag has new memories but old ones stale

    Returns:
        Stats dict with counts.
    """
    stats = {"access_divergence": 0, "drift": 0, "tag_gap": 0, "total_updated": 0}

    try:
        # --- 1. Access Divergence ---
        stats["access_divergence"] = _sweep_access_divergence(
            client, collection_name, max_memories
        )

        # --- 2. Drift Detection ---
        stats["drift"] = _sweep_drift_detection(
            client, collection_name, max_per_project=100
        )

        # --- 3. Tag Activity Gap ---
        stats["tag_gap"] = _sweep_tag_activity_gap(
            client, collection_name
        )

        stats["total_updated"] = (
            stats["access_divergence"] + stats["drift"] + stats["tag_gap"]
        )

    except Exception as e:
        logger.error(f"Staleness sweep failed: {e}")

    return stats


def get_stale_memories(
    client: QdrantClient,
    collection_name: str,
    threshold: float = 0.5,
    project: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """Get memories with high staleness scores.

    Args:
        threshold: Minimum staleness_score to include
        project: Filter by project
        limit: Max results

    Returns:
        List of stale memory summaries.
    """
    filters = [
        models.FieldCondition(
            key="archived", match=models.MatchValue(value=False)
        ),
        models.FieldCondition(
            key="staleness_score",
            range=models.Range(gte=threshold),
        ),
    ]
    if project:
        filters.append(
            models.FieldCondition(
                key="project", match=models.MatchValue(value=project)
            )
        )

    try:
        results, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(must=filters),
            limit=limit,
            with_payload=True,
            order_by=models.OrderBy(
                key="staleness_score",
                direction=models.Direction.DESC,
            ),
        )

        return [
            {
                "id": str(point.id),
                "content": (point.payload.get("content", ""))[:120],
                "type": point.payload.get("type", ""),
                "project": point.payload.get("project", ""),
                "staleness_score": point.payload.get("staleness_score", 0.0),
                "staleness_reasons": point.payload.get("staleness_reasons", []),
                "last_accessed": point.payload.get("last_accessed", ""),
                "created_at": point.payload.get("created_at", ""),
            }
            for point in results
        ]

    except Exception as e:
        logger.error(f"Failed to get stale memories: {e}")
        return []


# ── Internal helpers ──────────────────────────────────────────────────────


def _content_diverged(old_content: str, new_content: str) -> bool:
    """Check if two pieces of content are different enough to signal conflict."""
    if not old_content or not new_content:
        return False
    # Simple word overlap check — if <50% words overlap, content diverged
    old_words = set(old_content.lower().split())
    new_words = set(new_content.lower().split())
    if not old_words or not new_words:
        return False
    overlap = len(old_words & new_words) / min(len(old_words), len(new_words))
    return overlap < 0.5


def _update_staleness(
    client: QdrantClient,
    collection_name: str,
    memory_id: str,
    score: float,
    reasons: list[str],
) -> None:
    """Update staleness fields in Qdrant."""
    from .collections import safe_set_payload
    safe_set_payload(
        memory_id,
        {"staleness_score": score, "staleness_reasons": reasons},
        collection_name=collection_name,
    )


def _sweep_access_divergence(
    client: QdrantClient,
    collection_name: str,
    max_memories: int = 500,
) -> int:
    """Flag memories in active projects that haven't been accessed recently."""
    cutoff = (utc_now() - timedelta(days=ACCESS_DIVERGENCE_DAYS)).isoformat()
    updated = 0

    try:
        # Get memories not accessed in 30+ days, not archived, not pinned
        results, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="archived", match=models.MatchValue(value=False)
                    ),
                    models.FieldCondition(
                        key="pinned", match=models.MatchValue(value=False)
                    ),
                    models.FieldCondition(
                        key="last_accessed",
                        range=models.DatetimeRange(lt=cutoff),
                    ),
                ]
            ),
            limit=max_memories,
            with_payload=["project", "staleness_score", "staleness_reasons",
                          "tags", "last_accessed"],
        )

        # Group by project, check if project is active
        by_project: dict[str, list] = {}
        for point in results:
            proj = point.payload.get("project", "")
            if proj:
                by_project.setdefault(proj, []).append(point)

        for project, points in by_project.items():
            if not _is_project_active(client, collection_name, project):
                continue

            for point in points:
                old_score = point.payload.get("staleness_score", 0.0)
                reasons = point.payload.get("staleness_reasons", [])
                reason = f"access_divergence: untouched {ACCESS_DIVERGENCE_DAYS}+ days in active project"
                if reason not in reasons:
                    reasons.append(reason)
                new_score = min(old_score + ACCESS_DIVERGENCE_STALENESS, 1.0)
                _update_staleness(
                    client, collection_name, str(point.id), new_score, reasons
                )
                updated += 1

    except Exception as e:
        logger.warning(f"Access divergence sweep failed: {e}")

    return updated


def _sweep_drift_detection(
    client: QdrantClient,
    collection_name: str,
    max_per_project: int = 100,
) -> int:
    """Detect memories whose embeddings have drifted from project centroid."""
    updated = 0

    try:
        # Get distinct projects
        projects = _get_active_projects(client, collection_name)

        for project in projects:
            # Get recent memories (last 30 days) to build centroid
            recent_cutoff = (utc_now() - timedelta(days=30)).isoformat()
            recent_points, _ = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="project", match=models.MatchValue(value=project)
                        ),
                        models.FieldCondition(
                            key="archived", match=models.MatchValue(value=False)
                        ),
                        models.FieldCondition(
                            key="created_at",
                            range=models.DatetimeRange(gte=recent_cutoff),
                        ),
                    ]
                ),
                limit=50,
                with_vectors=["dense"],
                with_payload=False,
            )

            if len(recent_points) < 3:
                continue

            # Compute centroid of recent memories
            centroid = _compute_centroid(
                [p.vector["dense"] for p in recent_points if p.vector and "dense" in p.vector]
            )
            if centroid is None:
                continue

            # Find old memories far from centroid
            old_cutoff = (utc_now() - timedelta(days=60)).isoformat()
            old_points, _ = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="project", match=models.MatchValue(value=project)
                        ),
                        models.FieldCondition(
                            key="archived", match=models.MatchValue(value=False)
                        ),
                        models.FieldCondition(
                            key="pinned", match=models.MatchValue(value=False)
                        ),
                        models.FieldCondition(
                            key="created_at",
                            range=models.DatetimeRange(lt=old_cutoff),
                        ),
                    ]
                ),
                limit=max_per_project,
                with_vectors=["dense"],
                with_payload=["staleness_score", "staleness_reasons"],
            )

            for point in old_points:
                if not point.vector or "dense" not in point.vector:
                    continue

                distance = _cosine_distance(point.vector["dense"], centroid)
                if distance > DRIFT_DISTANCE_THRESHOLD:
                    old_score = point.payload.get("staleness_score", 0.0)
                    reasons = point.payload.get("staleness_reasons", [])
                    reason = f"drift: embedding distance {distance:.2f} from project centroid"
                    if not any(r.startswith("drift:") for r in reasons):
                        reasons.append(reason)
                    new_score = min(old_score + DRIFT_STALENESS, 1.0)
                    _update_staleness(
                        client, collection_name, str(point.id), new_score, reasons
                    )
                    updated += 1

    except Exception as e:
        logger.warning(f"Drift detection sweep failed: {e}")

    return updated


def _sweep_tag_activity_gap(
    client: QdrantClient,
    collection_name: str,
) -> int:
    """Flag old memories when their tags have lots of new activity."""
    updated = 0

    try:
        recent_cutoff = (utc_now() - timedelta(days=30)).isoformat()
        old_cutoff = (utc_now() - timedelta(days=60)).isoformat()

        # Get recent memories to find active tags
        recent_points, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="archived", match=models.MatchValue(value=False)
                    ),
                    models.FieldCondition(
                        key="created_at",
                        range=models.DatetimeRange(gte=recent_cutoff),
                    ),
                ]
            ),
            limit=200,
            with_payload=["tags"],
        )

        # Count tag frequency in recent memories
        tag_counts: dict[str, int] = {}
        for point in recent_points:
            for tag in point.payload.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Tags with 5+ recent memories are "active"
        active_tags = {tag for tag, count in tag_counts.items() if count >= 5}
        if not active_tags:
            return 0

        # Find old memories with active tags that haven't been accessed
        for tag in active_tags:
            old_points, _ = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="archived", match=models.MatchValue(value=False)
                        ),
                        models.FieldCondition(
                            key="pinned", match=models.MatchValue(value=False)
                        ),
                        models.FieldCondition(
                            key="tags", match=models.MatchAny(any=[tag])
                        ),
                        models.FieldCondition(
                            key="created_at",
                            range=models.DatetimeRange(lt=old_cutoff),
                        ),
                        models.FieldCondition(
                            key="last_accessed",
                            range=models.DatetimeRange(lt=recent_cutoff),
                        ),
                    ]
                ),
                limit=20,
                with_payload=["staleness_score", "staleness_reasons"],
            )

            for point in old_points:
                old_score = point.payload.get("staleness_score", 0.0)
                reasons = point.payload.get("staleness_reasons", [])
                reason = f"tag_gap: tag '{tag}' has {tag_counts[tag]} new memories"
                if not any(r.startswith(f"tag_gap: tag '{tag}'") for r in reasons):
                    reasons.append(reason)
                new_score = min(old_score + TAG_GAP_STALENESS, 1.0)
                _update_staleness(
                    client, collection_name, str(point.id), new_score, reasons
                )
                updated += 1

    except Exception as e:
        logger.warning(f"Tag activity gap sweep failed: {e}")

    return updated


def _is_project_active(
    client: QdrantClient, collection_name: str, project: str
) -> bool:
    """Check if a project has new memories in the last 7 days."""
    cutoff = (utc_now() - timedelta(days=7)).isoformat()
    try:
        count = client.count(
            collection_name=collection_name,
            count_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="project", match=models.MatchValue(value=project)
                    ),
                    models.FieldCondition(
                        key="created_at", range=models.DatetimeRange(gte=cutoff)
                    ),
                ]
            ),
        )
        return count.count > 0
    except Exception:
        return False


def _get_active_projects(
    client: QdrantClient, collection_name: str
) -> list[str]:
    """Get projects with recent activity."""
    cutoff = (utc_now() - timedelta(days=7)).isoformat()
    try:
        results, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="created_at", range=models.DatetimeRange(gte=cutoff)
                    ),
                ]
            ),
            limit=200,
            with_payload=["project"],
        )
        return list({
            p.payload.get("project")
            for p in results
            if p.payload.get("project")
        })
    except Exception:
        return []


def _compute_centroid(vectors: list[list[float]]) -> Optional[list[float]]:
    """Compute mean vector from list of vectors."""
    if not vectors:
        return None
    dim = len(vectors[0])
    centroid = [0.0] * dim
    for vec in vectors:
        for i in range(dim):
            centroid[i] += vec[i]
    n = len(vectors)
    return [c / n for c in centroid]


def _cosine_distance(a: list[float], b: list[float]) -> float:
    """Compute cosine distance (1 - cosine_similarity)."""
    import math
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 1.0
    return 1.0 - (dot / (norm_a * norm_b))
