"""Emotional weighting - detect sentiment and boost importance.

Real brains prioritize emotionally significant memories (amygdala modulation).
This module detects emotional content and boosts memory importance accordingly.
"""

import logging

from .collections import get_client, COLLECTION_NAME

logger = logging.getLogger(__name__)


class EmotionalWeighting:
    """Detect emotional significance in memories."""

    # Emotional keywords (positive/negative sentiment)
    POSITIVE_KEYWORDS = [
        "success", "fixed", "solved", "excellent", "great", "breakthrough",
        "achieved", "resolved", "perfect", "brilliant", "amazing", "wonderful",
        "accomplished", "improved", "optimized", "efficient", "faster"
    ]

    NEGATIVE_KEYWORDS = [
        "critical", "urgent", "broken", "failed", "severe", "disaster",
        "catastrophic", "blocking", "deadlock", "corruption", "emergency",
        "crash", "fatal", "panic", "danger", "threat", "vulnerable"
    ]

    # Intensity multipliers
    INTENSITY_WORDS = {
        "very": 1.3,
        "extremely": 1.5,
        "absolutely": 1.5,
        "really": 1.2,
        "completely": 1.4,
        "totally": 1.3,
        "highly": 1.4
    }

    @staticmethod
    def calculate_emotional_weight(content: str, memory_type: str) -> float:
        """
        Calculate emotional weight (0.0 to 1.0) based on content sentiment.

        Args:
            content: Memory content to analyze
            memory_type: Type of memory (error, decision, etc.)

        Returns:
            Emotional weight to boost importance
        """
        content_lower = content.lower()

        # Count positive/negative keywords
        positive_count = sum(
            1 for word in EmotionalWeighting.POSITIVE_KEYWORDS
            if word in content_lower
        )
        negative_count = sum(
            1 for word in EmotionalWeighting.NEGATIVE_KEYWORDS
            if word in content_lower
        )

        # Check for intensity modifiers
        intensity_boost = 1.0
        for word, multiplier in EmotionalWeighting.INTENSITY_WORDS.items():
            if word in content_lower:
                intensity_boost = max(intensity_boost, multiplier)

        # Calculate base emotional score
        emotional_score = (positive_count + negative_count) * 0.15
        emotional_score *= intensity_boost

        # Type-specific adjustments
        if memory_type == "error" and negative_count > 0:
            emotional_score *= 1.3  # Errors with negative sentiment are critical
        elif memory_type == "decision" and positive_count > 0:
            emotional_score *= 1.2  # Positive decisions are important

        return min(1.0, emotional_score)

    @staticmethod
    def apply_emotional_boost(
        client,
        collection_name: str,
        memory_id: str,
        emotional_weight: float,
        current_importance: float
    ) -> float:
        """
        Boost memory importance based on emotional weight.

        Args:
            client: Qdrant client
            collection_name: Collection name
            memory_id: Memory ID to boost
            emotional_weight: Calculated emotional weight
            current_importance: Current importance score

        Returns:
            New importance score
        """
        # Emotional boost (max +0.2 importance)
        importance_boost = emotional_weight * 0.2
        new_importance = min(1.0, current_importance + importance_boost)

        # Update in Qdrant
        client.set_payload(
            collection_name=collection_name,
            points=[memory_id],
            payload={
                "importance_score": new_importance,
                "emotional_weight": emotional_weight
            }
        )

        return new_importance


def run_emotional_analysis(limit: int = 100) -> int:
    """
    Analyze recent memories for emotional content and boost importance.

    Run daily via scheduler.

    Args:
        limit: Maximum memories to analyze

    Returns:
        Number of memories analyzed
    """
    client = get_client()

    try:
        # Get recent memories without emotional_weight
        memories, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=limit
        )

        analyzed = 0
        for memory in memories:
            payload = memory.payload

            # Skip if already analyzed
            if payload.get("emotional_weight") is not None:
                continue

            # Calculate emotional weight
            content = payload.get("content", "")
            memory_type = payload.get("type", "learning")
            emotional_weight = EmotionalWeighting.calculate_emotional_weight(
                content, memory_type
            )

            # Apply boost if significant
            if emotional_weight > 0.1:  # Threshold for significance
                current_importance = payload.get("importance_score", 0.5)
                new_importance = EmotionalWeighting.apply_emotional_boost(
                    client,
                    COLLECTION_NAME,
                    str(memory.id),
                    emotional_weight,
                    current_importance
                )
                analyzed += 1
                logger.info(
                    f"Applied emotional boost to memory {memory.id}: "
                    f"weight={emotional_weight:.2f}, "
                    f"importance {current_importance:.2f} → {new_importance:.2f}"
                )

        logger.info(f"Emotional analysis complete: {analyzed} memories boosted")
        return analyzed

    except Exception as e:
        logger.error(f"Emotional analysis failed: {e}")
        return 0
