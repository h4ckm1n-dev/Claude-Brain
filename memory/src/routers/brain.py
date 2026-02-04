"""Brain intelligence endpoints.

Provides brain-inspired memory processing: relationship inference,
importance scoring, memory replay, dream mode, emotional analysis,
conflict detection, meta-learning, and performance metrics.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timezone
from .. import collections
from ..models import StatsResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["brain"])


# ============================================================================
# Relationship Inference Endpoints
# ============================================================================


@router.post("/inference/run")
async def run_relationship_inference(
    inference_type: Optional[str] = Query(
        default="all",
        description="Type: all, temporal, semantic, causal, error-solution",
    ),
):
    """Manually trigger relationship inference.

    Runs automatic relationship discovery to find and create connections between memories.
    This implements Phase 1.2: Automatic Relationship Inference with multiple strategies:

    - **temporal**: Find memories created close together in time (FOLLOWS)
    - **semantic**: Find semantically similar memories (RELATED, SIMILAR_TO)
    - **causal**: Detect causal patterns in text (CAUSES)
    - **error-solution**: Link errors to their solutions (FIXES)
    - **all**: Run all inference types

    Args:
        inference_type: Type of inference to run (default: all)

    Returns:
        Statistics about relationships created by each inference type
    """
    from ..relationship_inference import RelationshipInference

    try:
        stats = {}

        if inference_type in ["all", "error-solution"]:
            fixes = await RelationshipInference.infer_error_solution_links(
                lookback_days=30
            )
            stats["error_solution_links"] = fixes

        if inference_type in ["all", "semantic"]:
            related = await RelationshipInference.infer_related_links(batch_size=20)
            stats["semantic_links"] = related

        if inference_type in ["all", "temporal"]:
            temporal = await RelationshipInference.infer_temporal_links(hours_window=2)
            stats["temporal_links"] = temporal

        if inference_type in ["all", "causal"]:
            causal = await RelationshipInference.infer_causal_links()
            stats["causal_links"] = causal

        stats["total_created"] = sum(stats.values())

        return stats

    except Exception as e:
        logger.error(f"Relationship inference failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inference/co-access/stats")
async def get_co_access_stats():
    """Get statistics about co-access tracking.

    Co-access tracking monitors which memories are accessed together (e.g., appearing
    in the same search results). After a threshold number of co-accesses (default: 5),
    a RELATED relationship is automatically inferred.

    Returns:
        Statistics including:
        - total_pairs_tracked: Number of memory pairs being tracked
        - pairs_above_threshold: Number of pairs that exceeded the threshold
        - threshold: Current co-access threshold
    """
    from ..relationship_inference import RelationshipInference

    try:
        stats = RelationshipInference.get_co_access_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get co-access stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inference/co-access/reset")
async def reset_co_access_tracker():
    """Reset the co-access tracking data.

    This clears all tracked co-access counts. Useful for testing or maintenance.
    Note: In-memory tracking is lost on service restart.
    """
    from ..relationship_inference import RelationshipInference

    try:
        RelationshipInference.reset_co_access_tracker()
        return {"status": "reset", "message": "Co-access tracker cleared"}
    except Exception as e:
        logger.error(f"Failed to reset co-access tracker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Brain Intelligence Endpoints
# ============================================================================


@router.post("/brain/infer-relationships")
async def brain_infer_relationships(
    lookback_days: int = Query(default=30, ge=1, le=90),
):
    """
    Manually trigger relationship inference.

    Finds errors that were later solved and creates FIXES relationships.
    Also links semantically similar memories as RELATED.

    Args:
        lookback_days: Days to look back for solutions (1-90)

    Returns:
        Number of relationships created
    """
    try:
        from ..relationship_inference import RelationshipInference

        # Infer error->solution links
        fixes_links = await RelationshipInference.infer_error_solution_links(
            lookback_days
        )

        # Infer related links
        related_links = await RelationshipInference.infer_related_links(batch_size=20)

        # Infer temporal links
        temporal_links = await RelationshipInference.infer_temporal_links(
            hours_window=2
        )

        return {
            "success": True,
            "fixes_links": fixes_links,
            "related_links": related_links,
            "temporal_links": temporal_links,
            "total_links": fixes_links + related_links + temporal_links,
        }

    except Exception as e:
        logger.error(f"Failed to infer relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brain/update-importance")
async def brain_update_importance(
    limit: int = Query(default=100, ge=1, le=1000),
):
    """
    Manually trigger adaptive importance score updates.

    Updates importance scores based on access patterns, type, and co-access.

    Args:
        limit: Max memories to update (1-1000)

    Returns:
        Number of memories updated
    """
    try:
        from ..consolidation import update_importance_scores_batch

        updated = update_importance_scores_batch(
            client=collections.get_client(),
            collection_name=collections.COLLECTION_NAME,
            limit=limit,
        )

        return {"success": True, "updated": updated, "limit": limit}

    except Exception as e:
        logger.error(f"Failed to update importance scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brain/archive-low-utility")
async def brain_archive_low_utility(
    threshold: float = Query(default=0.3, ge=0.0, le=1.0),
    max_archive: int = Query(default=100, ge=1, le=500),
    dry_run: bool = Query(default=False),
):
    """
    Manually trigger utility-based archival.

    Archives memories with low utility scores (based on access, relationships, importance).

    Args:
        threshold: Archive if utility < this (0.0-1.0)
        max_archive: Max memories to archive (1-500)
        dry_run: If true, only simulate (don't actually archive)

    Returns:
        Number of memories archived
    """
    try:
        from ..consolidation import archive_low_utility_memories

        archived = archive_low_utility_memories(
            client=collections.get_client(),
            collection_name=collections.COLLECTION_NAME,
            utility_threshold=threshold,
            max_archive=max_archive,
            dry_run=dry_run,
        )

        return {
            "success": True,
            "archived": archived,
            "threshold": threshold,
            "dry_run": dry_run,
        }

    except Exception as e:
        logger.error(f"Failed to archive low-utility memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brain/stats")
async def brain_get_stats():
    """
    Get brain intelligence statistics.

    Returns stats about adaptive learning, relationships, and memory utility.

    Returns:
        Statistics about brain features
    """
    try:
        # Get basic stats
        stats_data = collections.get_stats()
        stats = StatsResponse(**stats_data)

        # Get graph stats for relationships
        from ..graph import get_graph_stats

        graph_stats = get_graph_stats()

        # Calculate utility distribution
        points, _ = collections.get_client().scroll(
            collection_name=collections.COLLECTION_NAME,
            limit=1000,
            with_payload=True,
            with_vectors=False,
        )

        from ..consolidation import calculate_memory_utility

        utilities = []
        for point in points:
            payload = point.payload
            utility = calculate_memory_utility(
                access_count=payload.get("access_count", 0),
                importance=payload.get("importance", 0.5),
                created_at=datetime.fromisoformat(payload["created_at"]),
                last_accessed_at=(
                    datetime.fromisoformat(payload["last_accessed_at"])
                    if payload.get("last_accessed_at")
                    else datetime.fromisoformat(payload["created_at"])
                ),
                relationship_count=0,  # Simplified for stats
                memory_type=payload["type"],
            )
            utilities.append(utility)

        # Utility buckets
        high_utility = sum(1 for u in utilities if u >= 0.7)
        medium_utility = sum(1 for u in utilities if 0.3 <= u < 0.7)
        low_utility = sum(1 for u in utilities if u < 0.3)

        return {
            "total_memories": stats.total_memories,
            "relationships": graph_stats.get("relationships", 0),
            "utility_distribution": {
                "high": high_utility,
                "medium": medium_utility,
                "low": low_utility,
            },
            "adaptive_features": {
                "importance_scoring": True,
                "relationship_inference": True,
                "utility_archival": True,
            },
        }

    except Exception as e:
        logger.error(f"Failed to get brain stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Full Brain Mode Features
# ============================================================================


@router.post("/brain/reconsolidate/{memory_id}")
async def brain_reconsolidate(
    memory_id: str,
    access_context: Optional[str] = Query(default=None),
    co_accessed_ids: Optional[str] = Query(default=None),
):
    """
    Reconsolidate a memory - strengthen it when accessed.

    This simulates how real brains modify memories during recall.

    Args:
        memory_id: Memory to reconsolidate
        access_context: Current context (project, task)
        co_accessed_ids: Comma-separated IDs of co-accessed memories

    Returns:
        Reconsolidation results
    """
    try:
        from ..reconsolidation import reconsolidate_memory

        # Parse co-accessed IDs
        co_ids = co_accessed_ids.split(",") if co_accessed_ids else None

        result = reconsolidate_memory(
            memory_id=memory_id,
            access_context=access_context,
            co_accessed_ids=co_ids,
        )

        return result

    except Exception as e:
        logger.error(f"Reconsolidation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brain/spaced-repetition")
async def brain_spaced_repetition(
    limit: int = Query(default=10, ge=1, le=100),
):
    """
    Get memories due for spaced repetition review.

    Returns memories that need reinforcement based on forgetting curve.

    Args:
        limit: Maximum candidates to return

    Returns:
        List of memories due for review
    """
    try:
        from ..reconsolidation import get_spaced_repetition_candidates

        candidates = get_spaced_repetition_candidates(limit=limit)

        return {"success": True, "candidates": candidates, "count": len(candidates)}

    except Exception as e:
        logger.error(f"Spaced repetition query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brain/topics")
async def brain_discover_topics(
    min_cluster_size: int = Query(default=3, ge=2, le=20),
    max_topics: int = Query(default=20, ge=5, le=50),
):
    """
    Discover semantic topics by clustering memories.

    Organizes memories into natural groupings like a real brain.

    Args:
        min_cluster_size: Minimum memories per topic
        max_topics: Maximum topics to return

    Returns:
        Discovered topics with memory IDs
    """
    try:
        from ..semantic_clustering import (
            extract_topics_from_memories,
            create_topic_summaries,
        )

        topics = extract_topics_from_memories(
            min_cluster_size=min_cluster_size,
            max_topics=max_topics,
        )

        topics = create_topic_summaries(topics)

        return {"success": True, "topics": topics, "count": len(topics)}

    except Exception as e:
        logger.error(f"Topic discovery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brain/topics/timeline/{topic_name}")
async def brain_topic_timeline(
    topic_name: str,
    limit: int = Query(default=50, ge=10, le=200),
):
    """
    Get chronological timeline of memories in a topic.

    Args:
        topic_name: Topic to get timeline for
        limit: Max memories to return

    Returns:
        Chronologically ordered memories
    """
    try:
        from ..semantic_clustering import get_topic_timeline

        timeline = get_topic_timeline(topic_name, limit=limit)

        return {
            "success": True,
            "topic": topic_name,
            "timeline": timeline,
            "count": len(timeline),
        }

    except Exception as e:
        logger.error(f"Topic timeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brain/replay")
async def brain_memory_replay(
    count: int = Query(default=10, ge=1, le=100),
    importance_threshold: float = Query(default=0.5, ge=0.0, le=1.0),
):
    """
    Spontaneously replay random important memories to strengthen them.

    Simulates how real brains consolidate memories during rest/sleep.

    Args:
        count: Number of memories to replay
        importance_threshold: Only replay above this importance

    Returns:
        Replay statistics
    """
    try:
        from ..memory_replay import replay_random_memories

        result = replay_random_memories(
            count=count,
            importance_threshold=importance_threshold,
        )

        return result

    except Exception as e:
        logger.error(f"Memory replay failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brain/replay/project/{project}")
async def brain_project_replay(
    project: str,
    count: int = Query(default=10, ge=1, le=100),
):
    """
    Replay memories from a specific project.

    Useful for "reviewing" a project's knowledge.

    Args:
        project: Project name
        count: Number of memories to replay

    Returns:
        Replay statistics
    """
    try:
        from ..memory_replay import targeted_replay

        result = targeted_replay(project=project, count=count)

        return result

    except Exception as e:
        logger.error(f"Project replay failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brain/replay/underutilized")
async def brain_underutilized_replay(
    days: int = Query(default=7, ge=1, le=90),
    count: int = Query(default=20, ge=1, le=100),
):
    """
    Replay important memories that haven't been accessed recently.

    Prevents valuable knowledge from fading.

    Args:
        days: Days since last access
        count: Number to replay

    Returns:
        Replay statistics
    """
    try:
        from ..memory_replay import replay_underutilized_memories

        result = replay_underutilized_memories(
            days_since_access=days,
            count=count,
        )

        return result

    except Exception as e:
        logger.error(f"Underutilized replay failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brain/dream")
async def brain_dream_mode(
    duration: int = Query(default=30, ge=10, le=300),
):
    """
    "Dream mode" - rapid random replay to discover unexpected connections.

    Simulates REM sleep where brain makes random associations.

    Args:
        duration: How long to run (seconds)

    Returns:
        Dream statistics
    """
    try:
        from ..memory_replay import dream_mode_replay

        result = dream_mode_replay(duration_seconds=duration)

        return result

    except Exception as e:
        logger.error(f"Dream mode failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Advanced Brain Mode Endpoints
# ============================================================================


@router.post("/brain/emotional-analysis")
async def run_emotional_analysis_api(limit: int = 100):
    """
    Manually trigger emotional weighting analysis.

    Analyzes memories for emotional significance and boosts importance accordingly.
    """
    try:
        from ..emotional_weighting import run_emotional_analysis as analyze

        analyzed = analyze(limit=limit)

        return {
            "success": True,
            "analyzed": analyzed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Emotional analysis API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brain/detect-conflicts")
async def detect_conflicts_api(limit: int = 50):
    """
    Manually trigger interference detection and resolution.

    Finds contradictory memories and resolves conflicts via SUPERSEDES relationships.
    """
    try:
        from ..interference_detection import run_interference_detection as detect

        result = detect(limit=limit)

        return {
            "success": True,
            "conflicts_detected": result.get("conflicts_detected", 0),
            "conflicts_resolved": result.get("conflicts_resolved", 0),
            "timestamp": result.get("timestamp"),
        }

    except Exception as e:
        logger.error(f"Conflict detection API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brain/meta-learning")
async def run_meta_learning_api():
    """
    Manually trigger meta-learning (performance tracking and parameter tuning).

    Tracks system metrics and automatically tunes parameters for better performance.
    """
    try:
        from ..meta_learning import run_meta_learning as learn

        result = learn()

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return {
            "success": True,
            "metrics": result.get("metrics"),
            "tuned_parameters": result.get("tuned_parameters"),
            "timestamp": result.get("timestamp"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Meta-learning API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brain/performance-metrics")
async def get_performance_metrics(days: int = 7):
    """
    Get historical performance metrics.

    Args:
        days: Number of days to look back (default: 7)

    Returns:
        Historical performance metrics
    """
    try:
        from ..meta_learning import MetaLearning

        # Get current metrics
        current = MetaLearning.track_performance_metrics()

        # Get historical metrics
        history = MetaLearning.get_metrics_history(days=days)

        return {
            "success": True,
            "current": current,
            "history": history,
            "days": days,
        }

    except Exception as e:
        logger.error(f"Performance metrics API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
