"""Quality tracking and lifecycle state machine endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from .. import collections
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Quality & Lifecycle"])


@router.get("/quality/stats")
async def get_quality_stats():
    """Get quality score distribution and statistics.

    Returns:
        - Distribution across quality bins
        - Average quality by tier
        - Tier distribution
    """
    from ..quality_tracking import QualityTracker

    try:
        client = collections.get_client()

        distribution = QualityTracker.get_quality_distribution(
            client,
            collections.COLLECTION_NAME
        )

        return distribution

    except Exception as e:
        logger.error(f"Failed to get quality stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality/{memory_id}/trend")
async def get_quality_trend(
    memory_id: str,
    days_back: int = Query(default=30, ge=1, le=90)
):
    """Get quality score trend for a specific memory.

    Args:
        memory_id: Memory ID
        days_back: Number of days to look back

    Returns:
        Quality score history with timestamps
    """
    from ..quality_tracking import QualityTracker

    try:
        # Get current memory to verify it exists
        memory = collections.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        client = collections.get_client()

        trend = QualityTracker.get_quality_trend(
            client,
            collections.COLLECTION_NAME,
            memory_id,
            days_back=days_back
        )

        return trend

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quality trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quality/update")
async def trigger_quality_update():
    """Manually trigger quality score update for all memories.

    Returns:
        Update statistics
    """
    from ..quality_tracking import QualityTracker

    try:
        client = collections.get_client()

        result = QualityTracker.update_quality_scores(
            client,
            collections.COLLECTION_NAME,
            batch_size=100
        )

        return result

    except Exception as e:
        logger.error(f"Failed to trigger quality update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality/promotion-candidates")
async def get_promotion_candidates(
    min_quality_threshold: float = Query(default=0.75, ge=0.0, le=1.0),
    min_age_days: int = Query(default=7, ge=1, le=365)
):
    """Get list of memories eligible for tier promotion.

    Args:
        min_quality_threshold: Minimum quality score for promotion
        min_age_days: Minimum age in days

    Returns:
        List of promotion candidates with scores
    """
    from ..quality_tracking import TierPromotionEngine

    try:
        client = collections.get_client()

        candidates = TierPromotionEngine.evaluate_promotion_candidates(
            client,
            collections.COLLECTION_NAME,
            min_quality_threshold=min_quality_threshold,
            min_age_days=min_age_days
        )

        return {
            "total_candidates": len(candidates),
            "candidates": candidates
        }

    except Exception as e:
        logger.error(f"Failed to get promotion candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quality/promote-batch")
async def promote_memories_batch(
    dry_run: bool = Query(default=False, description="Preview promotions without applying")
):
    """Trigger automatic tier promotion for eligible memories.

    Args:
        dry_run: If true, preview promotions without applying

    Returns:
        Promotion results with counts
    """
    from ..quality_tracking import TierPromotionEngine

    try:
        client = collections.get_client()

        result = TierPromotionEngine.auto_promote_batch(
            client,
            collections.COLLECTION_NAME,
            dry_run=dry_run
        )

        return result

    except Exception as e:
        logger.error(f"Failed to promote memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quality/{memory_id}/rate")
async def rate_memory_quality(
    memory_id: str,
    rating: float = Query(..., ge=0.0, le=5.0, description="Rating from 0-5")
):
    """Add a user rating to a memory's quality score.

    Args:
        memory_id: Memory ID
        rating: Rating from 0-5

    Returns:
        Updated memory with new quality score
    """
    from ..quality_tracking import QualityScoreCalculator
    from qdrant_client.http import models

    try:
        # Get current memory
        memory = collections.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        client = collections.get_client()

        # Update rating
        new_rating_count = memory.user_rating_count + 1
        new_avg_rating = (
            (memory.user_rating * memory.user_rating_count + rating) / new_rating_count
        )

        # Recalculate quality score
        memory_age_days = (datetime.now(timezone.utc) - memory.created_at).days

        new_quality = QualityScoreCalculator.calculate_quality_score(
            access_count=memory.access_count,
            user_rating=new_avg_rating,
            user_rating_count=new_rating_count,
            relationship_count=len(memory.relationships),
            current_version=memory.current_version,
            memory_age_days=memory_age_days,
            memory_tier=memory.tier,
            content_length=len(memory.content) if memory.content else 0,
            tags_count=len(memory.tags) if memory.tags else 0,
            memory_type=memory.type if isinstance(memory.type, str) else memory.type.value if memory.type else "",
            has_solution=bool(getattr(memory, 'solution', None)),
            has_error_message=bool(getattr(memory, 'error_message', None)),
            has_prevention=bool(getattr(memory, 'prevention', None)),
            has_rationale=bool(getattr(memory, 'rationale', None)),
            is_resolved=bool(getattr(memory, 'resolved', False)),
        )

        # Update Qdrant point directly
        client.set_payload(
            collection_name=collections.COLLECTION_NAME,
            payload={
                "user_rating": new_avg_rating,
                "user_rating_count": new_rating_count,
                "quality_score": new_quality
            },
            points=[memory_id]
        )

        # Get updated memory
        updated_memory = collections.get_memory(memory_id)

        return {
            "memory_id": memory_id,
            "new_rating": new_avg_rating,
            "rating_count": new_rating_count,
            "new_quality_score": new_quality,
            "updated_memory": updated_memory.model_dump() if updated_memory else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rate memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Lifecycle State Machine Endpoints


@router.get("/lifecycle/stats")
async def get_lifecycle_stats():
    """Get memory state distribution statistics.

    Returns:
        Distribution of memories across lifecycle states
    """
    from ..lifecycle import get_state_distribution

    try:
        client = collections.get_client()

        distribution = get_state_distribution(
            client,
            collections.COLLECTION_NAME
        )

        return distribution

    except Exception as e:
        logger.error(f"Failed to get lifecycle stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lifecycle/update")
async def trigger_lifecycle_update():
    """Manually trigger memory state machine updates.

    Evaluates all memories and applies state transitions
    according to lifecycle rules.

    Returns:
        Update statistics
    """
    from ..lifecycle import update_memory_states

    try:
        client = collections.get_client()

        result = update_memory_states(
            client,
            collections.COLLECTION_NAME,
            batch_size=100
        )

        return result

    except Exception as e:
        logger.error(f"Failed to trigger lifecycle update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memories/{memory_id}/state")
async def manual_state_transition(
    memory_id: str,
    new_state: str = Query(..., description="New state (episodic, staging, semantic, procedural, archived, purged)"),
    reason: str = Query(default="Manual transition", description="Reason for transition")
):
    """Manually transition a memory to a new state.

    Args:
        memory_id: Memory ID
        new_state: Desired new state
        reason: Reason for manual transition

    Returns:
        Result of transition
    """
    from ..lifecycle import manual_state_transition as do_manual_transition, MemoryState

    try:
        # Validate state
        try:
            state_enum = MemoryState(new_state.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid state '{new_state}'. Valid states: {[s.value for s in MemoryState]}"
            )

        client = collections.get_client()

        result = do_manual_transition(
            client,
            collections.COLLECTION_NAME,
            memory_id,
            state_enum,
            reason
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "State transition failed")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to transition memory state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memories/{memory_id}/state-history")
async def get_memory_state_history(memory_id: str):
    """Get state transition history for a memory.

    Args:
        memory_id: Memory ID

    Returns:
        State history with transitions
    """
    try:
        # Get memory
        memory = collections.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        # Extract state history
        state_history = memory.state_history if hasattr(memory, 'state_history') else []

        return {
            "memory_id": memory_id,
            "current_state": memory.state if hasattr(memory, 'state') else "episodic",
            "state_changed_at": memory.state_changed_at if hasattr(memory, 'state_changed_at') else memory.created_at,
            "state_history": state_history
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get state history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lifecycle/transitions")
async def get_recent_transitions(
    limit: int = Query(default=50, ge=1, le=500, description="Maximum transitions to return")
):
    """Get recent state transitions across all memories.

    Args:
        limit: Maximum number of transitions

    Returns:
        Recent transitions with memory details
    """
    from qdrant_client.http import models

    try:
        client = collections.get_client()

        # Get memories with state history
        response = client.scroll(
            collection_name=collections.COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    # Only memories with state history
                    models.HasIdCondition(has_id=[])  # Placeholder, we'll get all
                ]
            ),
            limit=limit * 2,  # Get more to filter
            with_payload=True,
            with_vectors=False
        )

        points, _ = response

        # Extract all transitions
        all_transitions = []
        for point in points:
            payload = point.payload
            state_history = payload.get("state_history", [])

            for transition in state_history:
                all_transitions.append({
                    "memory_id": payload.get("id"),
                    "memory_content": payload.get("content", "")[:100],
                    "from_state": transition.get("from_state"),
                    "to_state": transition.get("to_state"),
                    "timestamp": transition.get("timestamp"),
                    "reason": transition.get("reason")
                })

        # Sort by timestamp (most recent first)
        all_transitions.sort(
            key=lambda x: x["timestamp"],
            reverse=True
        )

        return {
            "total": len(all_transitions),
            "transitions": all_transitions[:limit]
        }

    except Exception as e:
        logger.error(f"Failed to get recent transitions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
