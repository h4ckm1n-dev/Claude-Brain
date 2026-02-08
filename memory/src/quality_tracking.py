"""Memory quality evolution tracking and auto-promotion.

Implements Phase 3.2: Memory Quality Evolution Tracking
- Track access_count, user_rating, relationship_count over time
- Calculate quality scores
- Auto-promotion: episodic→semantic→procedural
- Quality trend analysis
- Stability metrics
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
from qdrant_client import QdrantClient
from qdrant_client.http import models

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class QualityScoreCalculator:
    """Calculates and tracks memory quality scores."""

    @staticmethod
    def calculate_quality_score(
        access_count: int,
        user_rating: Optional[float],
        user_rating_count: int,
        relationship_count: int,
        current_version: int,
        memory_age_days: float,
        memory_tier: str = "episodic",
        # Content metadata for richness scoring
        content_length: int = 0,
        tags_count: int = 0,
        memory_type: str = "",
        has_solution: bool = False,
        has_error_message: bool = False,
        has_prevention: bool = False,
        has_rationale: bool = False,
        is_resolved: bool = False,
        has_context: bool = False,
        has_alternatives: bool = False,
        is_auto_captured: bool = False,
        content: str = "",
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate comprehensive quality score.

        Formula (rebalanced to reward completeness at capture time):
        quality_score = (
            content_richness * 0.50 +    # Dominant: quality at capture time
            access_frequency * 0.15 +    # Grows over time
            maturity * 0.10 +            # Grows over time
            stability * 0.05 +           # Near-constant
            relationship_density * 0.10 + # Grows via inference
            user_rating_normalized * 0.10
        )

        A well-formed memory with all required fields should score >= 0.7 on day one.
        """
        # Component 1: Content richness (how complete is the memory)
        # Tags score: 3 tags = 0.6, 4 = 0.8, 5+ = 1.0
        if tags_count >= 5:
            tags_score = 1.0
        elif tags_count >= 3:
            tags_score = 0.4 + (tags_count * 0.12)  # 3=0.76, 4=0.88
        elif tags_count >= 2:
            tags_score = 0.4
        else:
            tags_score = tags_count * 0.15

        # Content length score: 50+ = 0.5, 100+ = 0.7, 200+ = 0.85, 500+ = 1.0
        if content_length >= 500:
            length_score = 1.0
        elif content_length >= 200:
            length_score = 0.85
        elif content_length >= 100:
            length_score = 0.7
        elif content_length >= 50:
            length_score = 0.5
        else:
            length_score = max(0.1, content_length / 100)

        # Type-specific completeness — full marks for complete memories
        type_bonus = 0.0
        if memory_type == "error":
            # Max 1.0: error_msg(0.25) + solution(0.30) + prevention(0.20) + context(0.15) + resolved(0.10)
            if has_error_message:
                type_bonus += 0.25
            if has_solution:
                type_bonus += 0.30
            if has_prevention:
                type_bonus += 0.20
            if has_context:
                type_bonus += 0.15
            if is_resolved:
                type_bonus += 0.10
        elif memory_type == "decision":
            # Max 1.0: rationale(0.35) + alternatives(0.25) + context(0.25) + base(0.15)
            type_bonus += 0.15  # Decisions are inherently valuable
            if has_rationale:
                type_bonus += 0.35
            if has_alternatives:
                type_bonus += 0.25
            if has_context:
                type_bonus += 0.25
        elif memory_type == "pattern":
            # Max 1.0: base(0.35) + length(0.25) + context(0.25) + detail(0.15)
            type_bonus += 0.35
            if content_length >= 100:
                type_bonus += 0.25
            if has_context:
                type_bonus += 0.25
            if content_length >= 200:
                type_bonus += 0.15  # Extra detail bonus
        elif memory_type == "learning":
            # Max 1.0: base(0.50) + context(0.30) + length(0.20)
            type_bonus += 0.50
            if has_context:
                type_bonus += 0.30
            if content_length >= 100:
                type_bonus += 0.20
        elif memory_type == "docs":
            # Max 1.0: base(0.30) + context(0.30) + length(0.20) + source(0.20)
            type_bonus += 0.30
            if has_context:
                type_bonus += 0.30
            if content_length >= 100:
                type_bonus += 0.20
            # has_source not tracked yet, give benefit of doubt
            type_bonus += 0.20
        elif memory_type == "context":
            # Max 1.0: base(0.50) + length(0.30) + tags(0.20)
            type_bonus += 0.50
            if content_length >= 100:
                type_bonus += 0.30
            if tags_count >= 3:
                type_bonus += 0.20

        type_bonus = min(type_bonus, 1.0)

        # Weighted: tags(20%) + length(30%) + type completeness(50%)
        content_richness = (tags_score * 0.20 + length_score * 0.30 + type_bonus * 0.50)

        # Component 2: Access frequency
        # Generous baseline — new memories shouldn't be penalized for not being accessed yet
        if access_count == 0:
            access_frequency = 0.55  # New memories get benefit of doubt
        elif access_count <= 3:
            access_frequency = 0.3 + (access_count * 0.067)  # 0.3-0.5
        elif access_count <= 10:
            access_frequency = 0.5 + ((access_count - 3) / 28)  # 0.5-0.75
        elif access_count <= 30:
            access_frequency = 0.75 + ((access_count - 10) / 133)  # 0.75-0.9
        else:
            access_frequency = min(0.9 + ((access_count - 30) / 200), 1.0)

        # Component 3: Maturity (older surviving memories are higher quality)
        if memory_age_days <= 1:
            maturity = 0.70  # New memories get strong baseline — quality is proven at capture
        elif memory_age_days <= 7:
            maturity = 0.3 + (memory_age_days / 14)  # 0.3-0.8
        elif memory_age_days <= 30:
            maturity = 0.8 + ((memory_age_days - 7) / 115)  # 0.8-1.0
        else:
            maturity = 1.0  # Survived 30+ days

        # Component 4: Stability (fewer edits relative to age = more stable)
        edit_count = current_version - 1
        if edit_count == 0:
            stability = 1.0
        elif edit_count <= 2:
            stability = 0.85
        elif edit_count <= 5:
            stability = 0.7
        else:
            stability = max(0.4, 1.0 - (edit_count * 0.04))

        # Component 5: Relationship density (bonus, not penalty)
        # Having relationships boosts score but lacking them doesn't hurt much
        if relationship_count == 0:
            relationship_density = 0.50  # Relationships come via inference, don't penalize at creation
        elif relationship_count <= 3:
            relationship_density = 0.3 + (relationship_count * 0.167)  # 0.3-0.8
        elif relationship_count <= 10:
            relationship_density = 0.8 + ((relationship_count - 3) / 35)  # 0.8-1.0
        else:
            relationship_density = 1.0

        # Component 6: User rating
        if user_rating and user_rating_count > 0:
            confidence = min(user_rating_count / 3, 1.0)
            user_rating_normalized = (user_rating / 5.0) * confidence
        else:
            user_rating_normalized = 0.5  # Neutral

        # Tier bonus
        tier_bonus = 0.0
        if memory_tier == "procedural":
            tier_bonus = 0.05
        elif memory_tier == "semantic":
            tier_bonus = 0.03

        # Auto-captured boilerplate penalty — crush scores for machine-generated noise
        boilerplate_penalty = 0.0
        if is_auto_captured:
            boilerplate_patterns = [
                'session started for project', 'session closed at',
                'session ended at', 'session resumed for project',
                'uncommitted files', 'on branch main with', 'on branch master with',
            ]
            content_lower = content.lower() if content else ""
            if any(bp in content_lower for bp in boilerplate_patterns):
                boilerplate_penalty = 0.35

        # Weighted overall score — content_richness dominates so well-formed
        # memories score high from day one, with growth room from usage metrics
        overall_score = (
            content_richness * 0.50 +
            access_frequency * 0.15 +
            maturity * 0.10 +
            stability * 0.05 +
            relationship_density * 0.10 +
            user_rating_normalized * 0.10 +
            tier_bonus -
            boilerplate_penalty
        )

        overall_score = max(0.0, min(overall_score, 1.0))

        component_scores = {
            "content_richness": round(content_richness, 3),
            "access_frequency": round(access_frequency, 3),
            "maturity": round(maturity, 3),
            "stability": round(stability, 3),
            "relationship_density": round(relationship_density, 3),
            "user_rating_normalized": round(user_rating_normalized, 3),
            "tier_bonus": round(tier_bonus, 3),
            "boilerplate_penalty": round(boilerplate_penalty, 3),
        }

        return round(overall_score, 3), component_scores

    @staticmethod
    def recalculate_single_memory_quality(
        client: 'QdrantClient',
        collection_name: str,
        memory_id: str,
    ) -> Optional[Tuple[float, Dict[str, float]]]:
        """Recalculate quality score for a single memory and write it back to Qdrant.

        Extracts all necessary params from the Qdrant payload and calls
        calculate_quality_score(), then writes the updated score back.

        Returns (score, components) or None if memory not found.
        """
        try:
            results = client.retrieve(
                collection_name=collection_name,
                ids=[memory_id],
                with_payload=True,
                with_vectors=False,
            )
            if not results:
                logger.warning(f"recalculate_single: memory {memory_id} not found")
                return None

            payload = results[0].payload

            created_at = payload.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

            age_days = (utc_now() - created_at).total_seconds() / 86400 if created_at else 0

            content = payload.get("content", "")
            tags = payload.get("tags", [])
            mem_type = payload.get("type", "")

            quality_score, components = QualityScoreCalculator.calculate_quality_score(
                access_count=payload.get("access_count", 0),
                user_rating=payload.get("user_rating"),
                user_rating_count=payload.get("user_rating_count", 0),
                relationship_count=len(payload.get("relations", [])),
                current_version=payload.get("current_version", 1),
                memory_age_days=age_days,
                memory_tier=payload.get("memory_tier", "episodic"),
                content_length=len(content) if content else 0,
                tags_count=len(tags) if tags else 0,
                memory_type=mem_type,
                has_solution=bool(payload.get("solution")),
                has_error_message=bool(payload.get("error_message")),
                has_prevention=bool(payload.get("prevention")),
                has_rationale=bool(payload.get("rationale")),
                is_resolved=bool(payload.get("resolved")),
                has_context=bool(payload.get("context")),
                has_alternatives=bool(payload.get("alternatives")),
                is_auto_captured="auto-captured" in (tags or []),
                content=content,
            )

            client.set_payload(
                collection_name=collection_name,
                payload={
                    "quality_score": quality_score,
                    "quality_components": components,
                    "quality_last_updated": utc_now().isoformat(),
                },
                points=[memory_id],
            )

            logger.info(f"Recalculated quality for {memory_id}: {quality_score}")
            return quality_score, components

        except Exception as e:
            logger.error(f"Failed to recalculate quality for {memory_id}: {e}")
            return None

    @staticmethod
    def calculate_quality_trend(
        memory_id: str,
        quality_history: List[Dict]
    ) -> Dict[str, Any]:
        """
        Calculate quality trend over time.

        Args:
            memory_id: Memory ID
            quality_history: List of quality snapshots with timestamps

        Returns:
            Trend analysis (improving, stable, declining)
        """
        if len(quality_history) < 2:
            return {
                "trend": "insufficient_data",
                "direction": "unknown",
                "confidence": 0.0
            }

        # Sort by timestamp
        sorted_history = sorted(quality_history, key=lambda x: x.get("timestamp", ""))

        # Calculate linear regression slope
        scores = [h.get("score", 0.5) for h in sorted_history]
        n = len(scores)

        # Simple slope calculation: (last - first) / time_span
        first_score = scores[0]
        last_score = scores[-1]
        score_change = last_score - first_score

        # Determine trend
        if abs(score_change) < 0.05:
            trend = "stable"
            direction = "neutral"
        elif score_change > 0:
            trend = "improving"
            direction = "upward"
        else:
            trend = "declining"
            direction = "downward"

        # Confidence based on history length
        confidence = min(len(quality_history) / 10, 1.0)  # Max confidence at 10+ snapshots

        return {
            "trend": trend,
            "direction": direction,
            "score_change": round(score_change, 3),
            "confidence": round(confidence, 3),
            "current_score": last_score,
            "first_score": first_score,
            "measurement_count": n
        }


class QualityTracker:
    """Tracks memory quality evolution over time."""

    @staticmethod
    def update_quality_scores(
        client: QdrantClient,
        collection_name: str,
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Update quality scores for all active memories.

        Args:
            client: Qdrant client
            collection_name: Collection name
            batch_size: Batch processing size

        Returns:
            Statistics about the update operation
        """
        try:
            stats = {
                "processed": 0,
                "updated": 0,
                "errors": 0
            }

            # Get all active (non-archived) memories
            offset = None
            while True:
                response = client.scroll(
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
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )

                points, next_offset = response
                if not points:
                    break

                # Update quality scores
                for point in points:
                    try:
                        payload = point.payload
                        memory_id = payload.get("id")

                        # Calculate quality score
                        created_at = payload.get("created_at")
                        if isinstance(created_at, str):
                            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

                        age_days = (utc_now() - created_at).total_seconds() / 86400 if created_at else 0

                        content = payload.get("content", "")
                        tags = payload.get("tags", [])
                        mem_type = payload.get("type", "")

                        quality_score, components = QualityScoreCalculator.calculate_quality_score(
                            access_count=payload.get("access_count", 0),
                            user_rating=payload.get("user_rating"),
                            user_rating_count=payload.get("user_rating_count", 0),
                            relationship_count=len(payload.get("relations", [])),
                            current_version=payload.get("current_version", 1),
                            memory_age_days=age_days,
                            memory_tier=payload.get("memory_tier", "episodic"),
                            content_length=len(content) if content else 0,
                            tags_count=len(tags) if tags else 0,
                            memory_type=mem_type,
                            has_solution=bool(payload.get("solution")),
                            has_error_message=bool(payload.get("error_message")),
                            has_prevention=bool(payload.get("prevention")),
                            has_rationale=bool(payload.get("rationale")),
                            is_resolved=bool(payload.get("resolved")),
                            has_context=bool(payload.get("context")),
                            has_alternatives=bool(payload.get("alternatives")),
                            is_auto_captured="auto-captured" in (tags or []),
                            content=content,
                        )

                        # Update payload
                        client.set_payload(
                            collection_name=collection_name,
                            payload={
                                "quality_score": quality_score,
                                "quality_components": components,
                                "quality_last_updated": utc_now().isoformat()
                            },
                            points=[memory_id]
                        )

                        stats["updated"] += 1

                    except Exception as e:
                        logger.warning(f"Failed to update quality for {memory_id}: {e}")
                        stats["errors"] += 1

                    stats["processed"] += 1

                offset = next_offset
                if offset is None:
                    break

            logger.info(
                f"Quality update complete: {stats['processed']} processed, "
                f"{stats['updated']} updated, {stats['errors']} errors"
            )

            return stats

        except Exception as e:
            logger.error(f"Failed to update quality scores: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_quality_distribution(
        client: QdrantClient,
        collection_name: str
    ) -> Dict[str, Any]:
        """
        Get distribution of quality scores.

        Args:
            client: Qdrant client
            collection_name: Collection name

        Returns:
            Quality distribution statistics
        """
        try:
            # Get all memories with quality scores
            response = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="archived",
                            match=models.MatchValue(value=False)
                        )
                    ]
                ),
                limit=10000,
                with_payload=True,
                with_vectors=False
            )

            memories = [point.payload for point in response[0]]

            if not memories:
                return {"total_count": 0}

            # Extract quality scores
            scores = [m.get("quality_score", 0.5) for m in memories]

            # Calculate distribution
            bins = {
                "excellent": 0,  # 0.8-1.0
                "good": 0,       # 0.6-0.8
                "moderate": 0,   # 0.4-0.6
                "low": 0,        # 0.2-0.4
                "poor": 0        # 0.0-0.2
            }

            for score in scores:
                if score >= 0.8:
                    bins["excellent"] += 1
                elif score >= 0.6:
                    bins["good"] += 1
                elif score >= 0.4:
                    bins["moderate"] += 1
                elif score >= 0.2:
                    bins["low"] += 1
                else:
                    bins["poor"] += 1

            # Calculate stats
            avg_score = sum(scores) / len(scores) if scores else 0
            min_score = min(scores) if scores else 0
            max_score = max(scores) if scores else 0

            return {
                "total_count": len(memories),
                "average_score": round(avg_score, 3),
                "min_score": round(min_score, 3),
                "max_score": round(max_score, 3),
                "distribution": bins
            }

        except Exception as e:
            logger.error(f"Failed to get quality distribution: {e}")
            return {"error": str(e)}


class TierPromotionEngine:
    """Handles automatic tier promotion based on quality."""

    @staticmethod
    def evaluate_promotion_candidates(
        client: QdrantClient,
        collection_name: str,
        min_quality_threshold: float = 0.75,
        min_age_days: int = 7
    ) -> List[Dict]:
        """
        Find memories eligible for tier promotion.

        Promotion criteria:
        - Episodic → Semantic: quality > 0.75 for 7+ days
        - Semantic → Procedural: quality > 0.9 for 30+ days

        Args:
            client: Qdrant client
            collection_name: Collection name
            min_quality_threshold: Minimum quality for promotion (default: 0.75)
            min_age_days: Minimum age in days (default: 7)

        Returns:
            List of promotion candidates
        """
        try:
            cutoff = utc_now() - timedelta(days=min_age_days)

            # Get memories with high quality scores
            response = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="archived",
                            match=models.MatchValue(value=False)
                        ),
                        models.FieldCondition(
                            key="created_at",
                            range=models.DatetimeRange(lte=cutoff)
                        )
                    ]
                ),
                limit=1000,
                with_payload=True,
                with_vectors=False
            )

            candidates = []

            for point in response[0]:
                payload = point.payload
                quality_score = payload.get("quality_score", 0.0)
                current_tier = payload.get("memory_tier", "episodic")
                memory_id = payload.get("id")

                # Check promotion eligibility
                if current_tier == "episodic" and quality_score >= min_quality_threshold:
                    candidates.append({
                        "memory_id": memory_id,
                        "current_tier": current_tier,
                        "target_tier": "semantic",
                        "quality_score": quality_score,
                        "promotion_reason": "high_quality_sustained"
                    })

                elif current_tier == "semantic" and quality_score >= 0.9:
                    # Check if it's been semantic for 30+ days
                    created_at = payload.get("created_at")
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

                    age_days = (utc_now() - created_at).total_seconds() / 86400
                    if age_days >= 30:
                        candidates.append({
                            "memory_id": memory_id,
                            "current_tier": current_tier,
                            "target_tier": "procedural",
                            "quality_score": quality_score,
                            "promotion_reason": "exceptional_quality_sustained"
                        })

            return candidates

        except Exception as e:
            logger.error(f"Failed to evaluate promotion candidates: {e}")
            return []

    @staticmethod
    def promote_memory(
        client: QdrantClient,
        collection_name: str,
        memory_id: str,
        target_tier: str,
        reason: str
    ) -> bool:
        """
        Promote a memory to a higher tier.

        Args:
            client: Qdrant client
            collection_name: Collection name
            memory_id: Memory ID
            target_tier: Target tier (semantic or procedural)
            reason: Promotion reason

        Returns:
            True if successful
        """
        try:
            # Update tier
            client.set_payload(
                collection_name=collection_name,
                payload={
                    "memory_tier": target_tier,
                    "promoted_at": utc_now().isoformat(),
                    "promotion_reason": reason
                },
                points=[memory_id]
            )

            logger.info(f"Promoted memory {memory_id} to {target_tier} (reason: {reason})")
            return True

        except Exception as e:
            logger.error(f"Failed to promote memory {memory_id}: {e}")
            return False

    @staticmethod
    def auto_promote_batch(
        client: QdrantClient,
        collection_name: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Automatically promote eligible memories.

        Args:
            client: Qdrant client
            collection_name: Collection name
            dry_run: If True, don't actually promote (just report)

        Returns:
            Statistics about promotions
        """
        try:
            candidates = TierPromotionEngine.evaluate_promotion_candidates(
                client,
                collection_name
            )

            stats = {
                "candidates_found": len(candidates),
                "promoted": 0,
                "failed": 0,
                "promotions": []
            }

            for candidate in candidates:
                if dry_run:
                    stats["promotions"].append(candidate)
                else:
                    success = TierPromotionEngine.promote_memory(
                        client,
                        collection_name,
                        candidate["memory_id"],
                        candidate["target_tier"],
                        candidate["promotion_reason"]
                    )

                    if success:
                        stats["promoted"] += 1
                        stats["promotions"].append(candidate)
                    else:
                        stats["failed"] += 1

            return stats

        except Exception as e:
            logger.error(f"Failed to auto-promote batch: {e}")
            return {"error": str(e)}


def get_memory_quality_trend(
    client: QdrantClient,
    collection_name: str,
    memory_id: str
) -> Dict[str, Any]:
    """
    Get quality trend for a specific memory.

    Args:
        client: Qdrant client
        collection_name: Collection name
        memory_id: Memory ID

    Returns:
        Quality trend analysis
    """
    try:
        # Get memory
        response = client.retrieve(
            collection_name=collection_name,
            ids=[memory_id],
            with_payload=True,
            with_vectors=False
        )

        if not response:
            return {"error": "Memory not found"}

        payload = response[0].payload

        # Get current quality score
        current_score = payload.get("quality_score", 0.5)
        components = payload.get("quality_components", {})

        # Get quality history (if stored)
        quality_history = payload.get("quality_history", [])

        # Calculate trend if history exists
        trend = None
        if quality_history:
            trend = QualityScoreCalculator.calculate_quality_trend(
                memory_id,
                quality_history
            )

        return {
            "memory_id": memory_id,
            "current_score": current_score,
            "components": components,
            "tier": payload.get("memory_tier"),
            "access_count": payload.get("access_count", 0),
            "relationship_count": len(payload.get("relations", [])),
            "trend": trend,
            "last_updated": payload.get("quality_last_updated")
        }

    except Exception as e:
        logger.error(f"Failed to get quality trend: {e}")
        return {"error": str(e)}
