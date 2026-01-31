"""Meta-learning - learn how to learn better.

Real brains adapt their learning strategies based on what works (metacognition).
This module tracks memory system performance and automatically tunes parameters
for better accuracy and efficiency.
"""

import logging
import json
from typing import Dict, List
from datetime import datetime, timedelta
from pathlib import Path

from .collections import get_client, COLLECTION_NAME

logger = logging.getLogger(__name__)

# Metrics file path
METRICS_FILE = Path(__file__).parent.parent / "metrics" / "performance_metrics.json"


class MetaLearning:
    """Learn how to learn better - optimize memory system parameters."""

    # Default thresholds (can be tuned)
    DEFAULT_THRESHOLDS = {
        "similarity_threshold": 0.75,
        "importance_threshold": 0.5,
        "emotional_threshold": 0.1,
        "utility_threshold": 0.3,
        "consolidation_threshold": 0.7
    }

    @staticmethod
    def track_performance_metrics() -> Dict:
        """
        Track key performance metrics for the memory system.

        Metrics tracked:
        - Search accuracy (how often top results are accessed)
        - Recall rate (% of searches returning results)
        - Average importance scores
        - Memory distribution by type
        - Relationship density

        Returns:
            Current performance metrics
        """
        client = get_client()

        try:
            # Get all memories
            memories, _ = client.scroll(
                collection_name=COLLECTION_NAME,
                limit=1000
            )

            if len(memories) == 0:
                return {"error": "No memories to analyze"}

            # Calculate metrics
            total_memories = len(memories)

            # Importance distribution
            importance_scores = [
                m.payload.get("importance", 0.5) for m in memories
            ]
            avg_importance = sum(importance_scores) / len(importance_scores)

            # Type distribution
            type_counts = {}
            for memory in memories:
                mem_type = memory.payload.get("type", "unknown")
                type_counts[mem_type] = type_counts.get(mem_type, 0) + 1

            # Access patterns
            accessed_memories = [
                m for m in memories
                if m.payload.get("access_count", 0) > 0
            ]
            access_rate = len(accessed_memories) / total_memories if total_memories > 0 else 0

            # Emotional weighting adoption
            emotional_memories = [
                m for m in memories
                if m.payload.get("emotional_weight") is not None
            ]
            emotional_coverage = len(emotional_memories) / total_memories if total_memories > 0 else 0

            metrics = {
                "total_memories": total_memories,
                "avg_importance": round(avg_importance, 3),
                "access_rate": round(access_rate, 3),
                "emotional_coverage": round(emotional_coverage, 3),
                "type_distribution": type_counts,
                "timestamp": datetime.now().isoformat()
            }

            # Save metrics to file
            MetaLearning._save_metrics(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Performance metric tracking failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def tune_parameters(metrics: Dict) -> Dict:
        """
        Automatically tune system parameters based on performance.

        Tuning strategy:
        - If avg_importance is too low → decrease importance_threshold
        - If access_rate is too low → decrease similarity_threshold
        - If emotional_coverage is low → decrease emotional_threshold

        Args:
            metrics: Performance metrics from track_performance_metrics

        Returns:
            Tuned parameters
        """
        current_thresholds = MetaLearning.DEFAULT_THRESHOLDS.copy()

        try:
            avg_importance = metrics.get("avg_importance", 0.5)
            access_rate = metrics.get("access_rate", 0.5)
            emotional_coverage = metrics.get("emotional_coverage", 0.0)

            # Tune importance threshold
            if avg_importance < 0.4:
                # Memories are too low importance - be less strict
                current_thresholds["importance_threshold"] = max(0.3, avg_importance - 0.1)
            elif avg_importance > 0.8:
                # Memories are too high importance - be more strict
                current_thresholds["importance_threshold"] = min(0.7, avg_importance)

            # Tune similarity threshold
            if access_rate < 0.3:
                # Not enough memories being accessed - lower similarity bar
                current_thresholds["similarity_threshold"] = max(0.65, current_thresholds["similarity_threshold"] - 0.05)
            elif access_rate > 0.8:
                # Too many memories being accessed - raise similarity bar
                current_thresholds["similarity_threshold"] = min(0.85, current_thresholds["similarity_threshold"] + 0.05)

            # Tune emotional threshold
            if emotional_coverage < 0.5:
                # Not enough emotional analysis - lower threshold
                current_thresholds["emotional_threshold"] = max(0.05, current_thresholds["emotional_threshold"] - 0.02)

            logger.info(f"Parameters tuned: {current_thresholds}")
            return current_thresholds

        except Exception as e:
            logger.error(f"Parameter tuning failed: {e}")
            return current_thresholds

    @staticmethod
    def _save_metrics(metrics: Dict):
        """Save metrics to file for historical tracking."""
        try:
            METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)

            # Load existing metrics
            if METRICS_FILE.exists():
                with open(METRICS_FILE, 'r') as f:
                    history = json.load(f)
            else:
                history = {"metrics_history": []}

            # Append new metrics
            history["metrics_history"].append(metrics)

            # Keep only last 30 days
            cutoff = datetime.now() - timedelta(days=30)
            history["metrics_history"] = [
                m for m in history["metrics_history"]
                if datetime.fromisoformat(m["timestamp"]) > cutoff
            ]

            # Save
            with open(METRICS_FILE, 'w') as f:
                json.dump(history, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    @staticmethod
    def get_metrics_history(days: int = 7) -> List[Dict]:
        """
        Get historical performance metrics.

        Args:
            days: Number of days to look back

        Returns:
            List of metrics from past N days
        """
        try:
            if not METRICS_FILE.exists():
                return []

            with open(METRICS_FILE, 'r') as f:
                history = json.load(f)

            cutoff = datetime.now() - timedelta(days=days)
            recent = [
                m for m in history.get("metrics_history", [])
                if datetime.fromisoformat(m["timestamp"]) > cutoff
            ]

            return recent

        except Exception as e:
            logger.error(f"Failed to load metrics history: {e}")
            return []


def run_meta_learning() -> Dict:
    """
    Run meta-learning: track metrics and tune parameters.

    Run weekly via scheduler.

    Returns:
        Meta-learning results
    """
    try:
        # Track current performance
        metrics = MetaLearning.track_performance_metrics()

        if "error" in metrics:
            return metrics

        # Tune parameters based on performance
        tuned_params = MetaLearning.tune_parameters(metrics)

        result = {
            "metrics": metrics,
            "tuned_parameters": tuned_params,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(
            f"Meta-learning complete: "
            f"avg_importance={metrics.get('avg_importance'):.3f}, "
            f"access_rate={metrics.get('access_rate'):.3f}"
        )

        return result

    except Exception as e:
        logger.error(f"Meta-learning job failed: {e}")
        return {"error": str(e)}
