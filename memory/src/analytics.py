"""Advanced pattern detection and analytics for memory system.

Implements Phase 3.1: Advanced Pattern Detection
- Error trend analysis (clustering, spikes, recurring errors)
- Knowledge gap detection (errors without patterns, low documentation)
- Error severity scoring
- Pattern mining and insights
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any, Tuple
from collections import defaultdict, Counter
from qdrant_client import QdrantClient
from qdrant_client.http import models

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class ErrorTrendAnalyzer:
    """Analyzes error trends and patterns over time."""

    @staticmethod
    def cluster_errors_by_tags(
        client: QdrantClient,
        collection_name: str,
        time_window_days: int = 30,
        min_cluster_size: int = 2
    ) -> List[Dict]:
        """
        Cluster errors by shared tags over a time window.

        Args:
            client: Qdrant client
            collection_name: Collection name
            time_window_days: Time window in days (default: 30)
            min_cluster_size: Minimum errors to form a cluster (default: 2)

        Returns:
            List of error clusters with statistics
        """
        try:
            # Get errors from time window
            cutoff = utc_now() - timedelta(days=time_window_days)

            response = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="type",
                            match=models.MatchValue(value="error")
                        ),
                        models.FieldCondition(
                            key="created_at",
                            range=models.Range(gte=cutoff.isoformat())
                        )
                    ]
                ),
                limit=1000,
                with_payload=True,
                with_vectors=False
            )

            errors = [point.payload for point in response[0]]

            # Cluster by tag combinations
            tag_clusters = defaultdict(list)
            for error in errors:
                tags = tuple(sorted(error.get("tags", [])))
                tag_clusters[tags].append(error)

            # Format clusters
            clusters = []
            for tags, cluster_errors in tag_clusters.items():
                if len(cluster_errors) >= min_cluster_size:
                    # Calculate cluster stats
                    resolved_count = sum(1 for e in cluster_errors if e.get("resolved", False))
                    avg_resolution_time = ErrorTrendAnalyzer._calculate_avg_resolution_time(cluster_errors)

                    clusters.append({
                        "tags": list(tags),
                        "error_count": len(cluster_errors),
                        "resolved_count": resolved_count,
                        "unresolved_count": len(cluster_errors) - resolved_count,
                        "resolution_rate": resolved_count / len(cluster_errors) if cluster_errors else 0,
                        "avg_resolution_time_hours": avg_resolution_time,
                        "first_seen": min(e.get("created_at") for e in cluster_errors),
                        "last_seen": max(e.get("created_at") for e in cluster_errors),
                        "error_ids": [e.get("id") for e in cluster_errors]
                    })

            # Sort by error count (most common first)
            clusters.sort(key=lambda x: x["error_count"], reverse=True)

            return clusters

        except Exception as e:
            logger.error(f"Failed to cluster errors: {e}")
            return []

    @staticmethod
    def _calculate_avg_resolution_time(errors: List[Dict]) -> Optional[float]:
        """Calculate average resolution time in hours for resolved errors."""
        resolution_times = []

        for error in errors:
            if error.get("resolved"):
                created_at = error.get("created_at")
                # Try to find resolution time from version history or updated_at
                updated_at = error.get("updated_at")

                if created_at and updated_at:
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if isinstance(updated_at, str):
                        updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))

                    resolution_time_hours = (updated_at - created_at).total_seconds() / 3600
                    resolution_times.append(resolution_time_hours)

        return sum(resolution_times) / len(resolution_times) if resolution_times else None

    @staticmethod
    def detect_error_spikes(
        client: QdrantClient,
        collection_name: str,
        spike_threshold: float = 5.0,
        time_window_days: int = 7,
        baseline_days: int = 30
    ) -> List[Dict]:
        """
        Detect spike patterns in error occurrence.

        A spike is detected when error count increases by spike_threshold times
        compared to baseline.

        Args:
            client: Qdrant client
            collection_name: Collection name
            spike_threshold: Multiplier for spike detection (default: 5x)
            time_window_days: Recent window to check for spikes (default: 7 days)
            baseline_days: Baseline period for comparison (default: 30 days)

        Returns:
            List of detected spikes with details
        """
        try:
            now = utc_now()
            recent_cutoff = now - timedelta(days=time_window_days)
            baseline_cutoff = now - timedelta(days=baseline_days)

            # Get recent errors
            recent_response = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="type",
                            match=models.MatchValue(value="error")
                        ),
                        models.FieldCondition(
                            key="created_at",
                            range=models.Range(gte=recent_cutoff.isoformat())
                        )
                    ]
                ),
                limit=1000,
                with_payload=True,
                with_vectors=False
            )

            # Get baseline errors
            baseline_response = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="type",
                            match=models.MatchValue(value="error")
                        ),
                        models.FieldCondition(
                            key="created_at",
                            range=models.Range(
                                gte=baseline_cutoff.isoformat(),
                                lte=recent_cutoff.isoformat()
                            )
                        )
                    ]
                ),
                limit=1000,
                with_payload=True,
                with_vectors=False
            )

            recent_errors = [point.payload for point in recent_response[0]]
            baseline_errors = [point.payload for point in baseline_response[0]]

            # Count by tag combinations
            recent_counts = Counter()
            baseline_counts = Counter()

            for error in recent_errors:
                tags = tuple(sorted(error.get("tags", [])))
                recent_counts[tags] += 1

            for error in baseline_errors:
                tags = tuple(sorted(error.get("tags", [])))
                baseline_counts[tags] += 1

            # Detect spikes
            spikes = []
            for tags, recent_count in recent_counts.items():
                baseline_count = baseline_counts.get(tags, 0)

                # Calculate daily rates
                recent_rate = recent_count / time_window_days
                baseline_rate = baseline_count / (baseline_days - time_window_days) if baseline_count > 0 else 0

                # Detect spike
                if baseline_rate == 0 and recent_count >= 3:
                    # New error type (no baseline)
                    spike_ratio = float('inf')
                    is_spike = True
                elif baseline_rate > 0:
                    spike_ratio = recent_rate / baseline_rate
                    is_spike = spike_ratio >= spike_threshold
                else:
                    continue

                if is_spike:
                    spikes.append({
                        "tags": list(tags),
                        "recent_count": recent_count,
                        "baseline_count": baseline_count,
                        "recent_rate_per_day": round(recent_rate, 2),
                        "baseline_rate_per_day": round(baseline_rate, 2),
                        "spike_ratio": round(spike_ratio, 2) if spike_ratio != float('inf') else "new",
                        "severity": "critical" if spike_ratio > 10 else "high" if spike_ratio > 5 else "moderate"
                    })

            # Sort by severity
            spikes.sort(key=lambda x: (
                0 if x["spike_ratio"] == "new" else -x["spike_ratio"]
            ))

            return spikes

        except Exception as e:
            logger.error(f"Failed to detect error spikes: {e}")
            return []

    @staticmethod
    def find_recurring_errors(
        client: QdrantClient,
        collection_name: str,
        time_window_days: int = 30,
        min_occurrences: int = 3,
        similarity_threshold: float = 0.85
    ) -> List[Dict]:
        """
        Identify recurring errors (same error multiple times).

        Args:
            client: Qdrant client
            collection_name: Collection name
            time_window_days: Time window to check (default: 30 days)
            min_occurrences: Minimum occurrences to be recurring (default: 3)
            similarity_threshold: Similarity threshold for matching (default: 0.85)

        Returns:
            List of recurring error patterns
        """
        try:
            cutoff = utc_now() - timedelta(days=time_window_days)

            response = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="type",
                            match=models.MatchValue(value="error")
                        ),
                        models.FieldCondition(
                            key="created_at",
                            range=models.Range(gte=cutoff.isoformat())
                        )
                    ]
                ),
                limit=1000,
                with_payload=True,
                with_vectors=False
            )

            errors = [point.payload for point in response[0]]

            # Group by error_message (exact match)
            error_groups = defaultdict(list)
            for error in errors:
                error_msg = error.get("error_message", "")
                if error_msg:
                    error_groups[error_msg].append(error)

            # Find recurring patterns
            recurring = []
            for error_msg, group_errors in error_groups.items():
                if len(group_errors) >= min_occurrences:
                    resolved_count = sum(1 for e in group_errors if e.get("resolved", False))

                    recurring.append({
                        "error_message": error_msg,
                        "occurrence_count": len(group_errors),
                        "resolved_count": resolved_count,
                        "resolution_rate": resolved_count / len(group_errors),
                        "first_occurrence": min(e.get("created_at") for e in group_errors),
                        "last_occurrence": max(e.get("created_at") for e in group_errors),
                        "affected_projects": list(set(e.get("project") for e in group_errors if e.get("project"))),
                        "error_ids": [e.get("id") for e in group_errors],
                        "severity": "critical" if resolved_count / len(group_errors) < 0.5 else "moderate"
                    })

            # Sort by occurrence count
            recurring.sort(key=lambda x: x["occurrence_count"], reverse=True)

            return recurring

        except Exception as e:
            logger.error(f"Failed to find recurring errors: {e}")
            return []

    @staticmethod
    def calculate_error_severity(
        error_count: int,
        resolution_time_hours: Optional[float],
        resolved: bool
    ) -> Tuple[float, str]:
        """
        Calculate error severity score.

        Formula: frequency * (1 / resolution_time) if resolved, else frequency * 2

        Args:
            error_count: Number of occurrences
            resolution_time_hours: Time to resolve in hours
            resolved: Whether error is resolved

        Returns:
            Tuple of (severity_score, severity_level)
        """
        if not resolved:
            # Unresolved errors get double weight
            score = error_count * 2.0
        elif resolution_time_hours and resolution_time_hours > 0:
            # Higher frequency + faster resolution = lower severity
            score = error_count / resolution_time_hours
        else:
            score = error_count

        # Categorize severity
        if score >= 10:
            level = "critical"
        elif score >= 5:
            level = "high"
        elif score >= 2:
            level = "moderate"
        else:
            level = "low"

        return round(score, 2), level


class KnowledgeGapDetector:
    """Detects gaps in knowledge and documentation."""

    @staticmethod
    def find_errors_without_patterns(
        client: QdrantClient,
        collection_name: str,
        time_window_days: int = 30
    ) -> List[Dict]:
        """
        Find topics with errors but no corresponding patterns or learnings.

        This indicates knowledge gaps where solutions exist but aren't documented.

        Args:
            client: Qdrant client
            collection_name: Collection name
            time_window_days: Time window to check (default: 30 days)

        Returns:
            List of topics with knowledge gaps
        """
        try:
            cutoff = utc_now() - timedelta(days=time_window_days)

            # Get all errors
            errors_response = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="type",
                            match=models.MatchValue(value="error")
                        ),
                        models.FieldCondition(
                            key="created_at",
                            range=models.Range(gte=cutoff.isoformat())
                        )
                    ]
                ),
                limit=1000,
                with_payload=True,
                with_vectors=False
            )

            # Get all patterns
            patterns_response = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="type",
                            match=models.MatchValue(value="pattern")
                        )
                    ]
                ),
                limit=1000,
                with_payload=True,
                with_vectors=False
            )

            errors = [point.payload for point in errors_response[0]]
            patterns = [point.payload for point in patterns_response[0]]

            # Extract error tags
            error_tag_sets = defaultdict(list)
            for error in errors:
                for tag in error.get("tags", []):
                    error_tag_sets[tag].append(error)

            # Extract pattern tags
            pattern_tags = set()
            for pattern in patterns:
                pattern_tags.update(pattern.get("tags", []))

            # Find gaps
            gaps = []
            for tag, tag_errors in error_tag_sets.items():
                if tag not in pattern_tags:
                    # No pattern exists for this error tag
                    resolved_count = sum(1 for e in tag_errors if e.get("resolved", False))

                    gaps.append({
                        "topic_tag": tag,
                        "error_count": len(tag_errors),
                        "resolved_count": resolved_count,
                        "pattern_count": 0,
                        "gap_type": "no_pattern",
                        "recommendation": f"Create best practice pattern for '{tag}' errors",
                        "affected_projects": list(set(e.get("project") for e in tag_errors if e.get("project")))
                    })

            # Sort by error count (most common gaps first)
            gaps.sort(key=lambda x: x["error_count"], reverse=True)

            return gaps

        except Exception as e:
            logger.error(f"Failed to find knowledge gaps: {e}")
            return []

    @staticmethod
    def find_low_documentation_projects(
        client: QdrantClient,
        collection_name: str,
        min_docs_threshold: int = 3
    ) -> List[Dict]:
        """
        Find projects with low documentation coverage.

        Args:
            client: Qdrant client
            collection_name: Collection name
            min_docs_threshold: Minimum expected docs per project (default: 3)

        Returns:
            List of projects with low documentation
        """
        try:
            # Get all memories
            response = client.scroll(
                collection_name=collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False
            )

            memories = [point.payload for point in response[0]]

            # Count by project and type
            project_stats = defaultdict(lambda: {
                "docs": 0,
                "errors": 0,
                "patterns": 0,
                "decisions": 0,
                "learnings": 0,
                "total": 0
            })

            for memory in memories:
                project = memory.get("project")
                if not project:
                    continue

                mem_type = memory.get("type", "context")
                project_stats[project][mem_type] += 1
                project_stats[project]["total"] += 1

            # Find low-documentation projects
            low_doc_projects = []
            for project, stats in project_stats.items():
                if stats["docs"] < min_docs_threshold:
                    # Calculate coverage score
                    coverage_score = stats["docs"] / stats["total"] if stats["total"] > 0 else 0

                    low_doc_projects.append({
                        "project": project,
                        "docs_count": stats["docs"],
                        "total_memories": stats["total"],
                        "error_count": stats["errors"],
                        "pattern_count": stats["patterns"],
                        "coverage_score": round(coverage_score, 2),
                        "recommendation": "Add documentation for common tasks and patterns",
                        "priority": "high" if stats["errors"] > 5 and stats["docs"] == 0 else "moderate"
                    })

            # Sort by priority and error count
            low_doc_projects.sort(key=lambda x: (
                x["priority"] == "high",
                x["error_count"]
            ), reverse=True)

            return low_doc_projects

        except Exception as e:
            logger.error(f"Failed to find low-documentation projects: {e}")
            return []

    @staticmethod
    def identify_expertise_clusters(
        client: QdrantClient,
        collection_name: str
    ) -> List[Dict]:
        """
        Identify expertise clusters based on error/pattern distribution.

        Expertise clusters are domains where patterns exist, indicating accumulated knowledge.
        Lack of patterns in error-prone areas indicates expertise gaps.

        Args:
            client: Qdrant client
            collection_name: Collection name

        Returns:
            List of expertise clusters and gaps
        """
        try:
            # Get errors and patterns
            response = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="type",
                            match=models.MatchAny(any=["error", "pattern"])
                        )
                    ]
                ),
                limit=5000,
                with_payload=True,
                with_vectors=False
            )

            memories = [point.payload for point in response[0]]

            # Count by tag
            tag_stats = defaultdict(lambda: {"errors": 0, "patterns": 0})

            for memory in memories:
                mem_type = memory.get("type")
                for tag in memory.get("tags", []):
                    if mem_type == "error":
                        tag_stats[tag]["errors"] += 1
                    elif mem_type == "pattern":
                        tag_stats[tag]["patterns"] += 1

            # Classify clusters
            clusters = []
            for tag, stats in tag_stats.items():
                total = stats["errors"] + stats["patterns"]
                pattern_ratio = stats["patterns"] / total if total > 0 else 0

                # Determine cluster type
                if pattern_ratio >= 0.6:
                    cluster_type = "strong_expertise"
                    recommendation = "Maintain and share this expertise"
                elif pattern_ratio >= 0.3:
                    cluster_type = "moderate_expertise"
                    recommendation = "Document more patterns to solidify knowledge"
                else:
                    cluster_type = "expertise_gap"
                    recommendation = "Create patterns from solved errors to build expertise"

                clusters.append({
                    "domain_tag": tag,
                    "error_count": stats["errors"],
                    "pattern_count": stats["patterns"],
                    "pattern_ratio": round(pattern_ratio, 2),
                    "cluster_type": cluster_type,
                    "recommendation": recommendation
                })

            # Sort by error count (focus on active domains)
            clusters.sort(key=lambda x: x["error_count"], reverse=True)

            return clusters

        except Exception as e:
            logger.error(f"Failed to identify expertise clusters: {e}")
            return []


def get_comprehensive_analytics(
    client: QdrantClient,
    collection_name: str
) -> Dict[str, Any]:
    """
    Get comprehensive analytics across all dimensions.

    Args:
        client: Qdrant client
        collection_name: Collection name

    Returns:
        Dictionary with all analytics results
    """
    try:
        analytics = {
            "error_trends": {
                "clusters": ErrorTrendAnalyzer.cluster_errors_by_tags(client, collection_name),
                "spikes": ErrorTrendAnalyzer.detect_error_spikes(client, collection_name),
                "recurring": ErrorTrendAnalyzer.find_recurring_errors(client, collection_name)
            },
            "knowledge_gaps": {
                "errors_without_patterns": KnowledgeGapDetector.find_errors_without_patterns(client, collection_name),
                "low_documentation_projects": KnowledgeGapDetector.find_low_documentation_projects(client, collection_name),
                "expertise_clusters": KnowledgeGapDetector.identify_expertise_clusters(client, collection_name)
            },
            "generated_at": utc_now().isoformat()
        }

        return analytics

    except Exception as e:
        logger.error(f"Failed to generate comprehensive analytics: {e}")
        return {"error": str(e)}
