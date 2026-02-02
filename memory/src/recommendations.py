"""Recommendation engine for memory system.

Implements Phase 3.1: Recommendation Engine
- Suggest related patterns/docs when storing errors
- Recommend preventive patterns when searching
- Collaborative filtering ("users who accessed A also accessed B")
- Context-aware suggestions
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from collections import defaultdict, Counter
from qdrant_client import QdrantClient
from qdrant_client.http import models

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class RecommendationEngine:
    """Generates recommendations based on memory patterns and usage."""

    @staticmethod
    def suggest_patterns_for_error(
        client: QdrantClient,
        collection_name: str,
        error_tags: List[str],
        error_content: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Suggest relevant patterns/docs for an error based on tags and similarity.

        Args:
            client: Qdrant client
            collection_name: Collection name
            error_tags: Tags from the error
            error_content: Error content for semantic search
            limit: Maximum suggestions

        Returns:
            List of suggested patterns/docs
        """
        try:
            suggestions = []

            # Strategy 1: Find patterns with matching tags
            if error_tags:
                response = client.scroll(
                    collection_name=collection_name,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="type",
                                match=models.MatchAny(any=["pattern", "docs"])
                            ),
                            models.FieldCondition(
                                key="tags",
                                match=models.MatchAny(any=error_tags)
                            )
                        ]
                    ),
                    limit=limit,
                    with_payload=True,
                    with_vectors=False
                )

                for point in response[0]:
                    payload = point.payload
                    # Calculate tag overlap score
                    pattern_tags = set(payload.get("tags", []))
                    overlap_count = len(set(error_tags) & pattern_tags)
                    overlap_score = overlap_count / len(error_tags) if error_tags else 0

                    suggestions.append({
                        "id": payload.get("id"),
                        "type": payload.get("type"),
                        "content": payload.get("content", "")[:200],
                        "tags": payload.get("tags", []),
                        "relevance_score": overlap_score,
                        "reason": f"Matches {overlap_count}/{len(error_tags)} tags",
                        "recommendation_type": "tag_match"
                    })

            # Sort by relevance and limit
            suggestions.sort(key=lambda x: x["relevance_score"], reverse=True)
            return suggestions[:limit]

        except Exception as e:
            logger.error(f"Failed to suggest patterns for error: {e}")
            return []

    @staticmethod
    def recommend_preventive_patterns(
        client: QdrantClient,
        collection_name: str,
        search_query: str,
        query_tags: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Recommend preventive patterns based on a search query.

        When user searches for an error, recommend patterns that could prevent
        similar issues in the future.

        Args:
            client: Qdrant client
            collection_name: Collection name
            search_query: User's search query
            query_tags: Optional tags from search context
            limit: Maximum recommendations

        Returns:
            List of preventive patterns
        """
        try:
            # Find patterns related to the search topic
            must_conditions = [
                models.FieldCondition(
                    key="type",
                    match=models.MatchValue(value="pattern")
                )
            ]

            if query_tags:
                must_conditions.append(
                    models.FieldCondition(
                        key="tags",
                        match=models.MatchAny(any=query_tags)
                    )
                )

            response = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(must=must_conditions),
                limit=limit * 2,  # Get more to filter
                with_payload=True,
                with_vectors=False
            )

            patterns = []
            for point in response[0]:
                payload = point.payload

                # Score based on access count (popular patterns)
                access_count = payload.get("access_count", 0)
                importance = payload.get("importance_score", 0.5)

                patterns.append({
                    "id": payload.get("id"),
                    "content": payload.get("content", "")[:200],
                    "tags": payload.get("tags", []),
                    "access_count": access_count,
                    "importance": importance,
                    "relevance_score": (access_count * 0.3 + importance * 0.7),
                    "recommendation_type": "preventive_pattern"
                })

            # Sort by relevance
            patterns.sort(key=lambda x: x["relevance_score"], reverse=True)
            return patterns[:limit]

        except Exception as e:
            logger.error(f"Failed to recommend preventive patterns: {e}")
            return []

    @staticmethod
    def collaborative_recommendations(
        client: QdrantClient,
        collection_name: str,
        memory_id: str,
        co_access_data: Optional[Dict] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Generate collaborative filtering recommendations.

        "Users who accessed memory A also accessed memories B, C, D"

        Args:
            client: Qdrant client
            collection_name: Collection name
            memory_id: Source memory ID
            co_access_data: Optional pre-computed co-access statistics
            limit: Maximum recommendations

        Returns:
            List of recommended memories
        """
        try:
            if not co_access_data:
                # No co-access data available
                return []

            # Get memories frequently accessed with this one
            memory_pair_counts = co_access_data.get("pairs", {})
            related_memory_ids = []

            for pair_key, count in memory_pair_counts.items():
                # pair_key format: "mem1_id:mem2_id"
                ids = pair_key.split(":")
                if memory_id in ids:
                    # Find the other memory in the pair
                    other_id = ids[0] if ids[1] == memory_id else ids[1]
                    related_memory_ids.append((other_id, count))

            # Sort by co-access count
            related_memory_ids.sort(key=lambda x: x[1], reverse=True)

            # Fetch top related memories
            recommendations = []
            for other_id, count in related_memory_ids[:limit]:
                try:
                    # Fetch memory details
                    response = client.retrieve(
                        collection_name=collection_name,
                        ids=[other_id],
                        with_payload=True,
                        with_vectors=False
                    )

                    if response:
                        payload = response[0].payload
                        recommendations.append({
                            "id": payload.get("id"),
                            "type": payload.get("type"),
                            "content": payload.get("content", "")[:200],
                            "tags": payload.get("tags", []),
                            "co_access_count": count,
                            "recommendation_type": "collaborative_filtering"
                        })

                except Exception as e:
                    logger.debug(f"Failed to fetch memory {other_id}: {e}")
                    continue

            return recommendations

        except Exception as e:
            logger.error(f"Failed to generate collaborative recommendations: {e}")
            return []

    @staticmethod
    def context_aware_suggestions(
        client: QdrantClient,
        collection_name: str,
        current_memory: Dict,
        project_context: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Generate context-aware suggestions based on current memory and project.

        Args:
            client: Qdrant client
            collection_name: Collection name
            current_memory: Current memory being viewed
            project_context: Optional project name for filtering
            limit: Maximum suggestions

        Returns:
            List of contextually relevant memories
        """
        try:
            current_type = current_memory.get("type")
            current_tags = set(current_memory.get("tags", []))

            # Build context-aware filter
            must_conditions = []

            # Suggest complementary memory types
            type_suggestions = {
                "error": ["pattern", "learning", "docs"],  # For errors, suggest solutions
                "pattern": ["learning", "decision"],  # For patterns, suggest use cases
                "decision": ["pattern", "docs"],  # For decisions, suggest supporting info
                "learning": ["pattern", "docs"],  # For learnings, suggest best practices
                "docs": ["pattern", "learning"]  # For docs, suggest practical examples
            }

            suggested_types = type_suggestions.get(current_type, ["pattern", "learning"])
            must_conditions.append(
                models.FieldCondition(
                    key="type",
                    match=models.MatchAny(any=suggested_types)
                )
            )

            # Filter by project if provided
            if project_context:
                must_conditions.append(
                    models.FieldCondition(
                        key="project",
                        match=models.MatchValue(value=project_context)
                    )
                )

            # Search for related memories
            response = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(must=must_conditions),
                limit=limit * 3,  # Get more to filter by tags
                with_payload=True,
                with_vectors=False
            )

            suggestions = []
            for point in response[0]:
                payload = point.payload

                # Skip self
                if payload.get("id") == current_memory.get("id"):
                    continue

                # Calculate tag overlap
                memory_tags = set(payload.get("tags", []))
                overlap_count = len(current_tags & memory_tags)
                overlap_score = overlap_count / len(current_tags) if current_tags else 0

                # Only suggest if there's some tag overlap or high importance
                importance = payload.get("importance_score", 0.5)
                if overlap_count > 0 or importance > 0.7:
                    suggestions.append({
                        "id": payload.get("id"),
                        "type": payload.get("type"),
                        "content": payload.get("content", "")[:200],
                        "tags": payload.get("tags", []),
                        "tag_overlap": overlap_count,
                        "relevance_score": (overlap_score * 0.6 + importance * 0.4),
                        "recommendation_type": "context_aware"
                    })

            # Sort by relevance
            suggestions.sort(key=lambda x: x["relevance_score"], reverse=True)
            return suggestions[:limit]

        except Exception as e:
            logger.error(f"Failed to generate context-aware suggestions: {e}")
            return []

    @staticmethod
    def suggest_documentation_topics(
        client: QdrantClient,
        collection_name: str,
        project: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Suggest topics that need documentation based on errors/learnings.

        Args:
            client: Qdrant client
            collection_name: Collection name
            project: Optional project filter
            limit: Maximum suggestions

        Returns:
            List of suggested documentation topics
        """
        try:
            # Get errors and learnings
            must_conditions = [
                models.FieldCondition(
                    key="type",
                    match=models.MatchAny(any=["error", "learning"])
                )
            ]

            if project:
                must_conditions.append(
                    models.FieldCondition(
                        key="project",
                        match=models.MatchValue(value=project)
                    )
                )

            response = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(must=must_conditions),
                limit=1000,
                with_payload=True,
                with_vectors=False
            )

            # Count tag frequencies
            tag_counts = Counter()
            tag_memories = defaultdict(list)

            for point in response[0]:
                payload = point.payload
                for tag in payload.get("tags", []):
                    tag_counts[tag] += 1
                    tag_memories[tag].append(payload.get("id"))

            # Get existing docs
            docs_response = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="type",
                            match=models.MatchValue(value="docs")
                        )
                    ]
                ),
                limit=1000,
                with_payload=True,
                with_vectors=False
            )

            documented_tags = set()
            for point in docs_response[0]:
                documented_tags.update(point.payload.get("tags", []))

            # Find undocumented topics
            suggestions = []
            for tag, count in tag_counts.most_common(limit * 2):
                if tag not in documented_tags and count >= 2:
                    suggestions.append({
                        "topic_tag": tag,
                        "error_learning_count": count,
                        "is_documented": False,
                        "priority": "high" if count >= 5 else "moderate",
                        "recommendation": f"Create documentation for '{tag}' (mentioned in {count} errors/learnings)",
                        "related_memory_ids": tag_memories[tag][:5]
                    })

            return suggestions[:limit]

        except Exception as e:
            logger.error(f"Failed to suggest documentation topics: {e}")
            return []


class CoAccessTracker:
    """Tracks co-access patterns for collaborative filtering."""

    def __init__(self):
        self.pair_counts: Dict[str, int] = defaultdict(int)
        self.last_access: Dict[str, datetime] = {}

    def track_access_batch(self, memory_ids: List[str]):
        """
        Track a batch of memories accessed together (e.g., search results).

        Args:
            memory_ids: List of memory IDs accessed together
        """
        if len(memory_ids) < 2:
            return

        # Record all pairs
        for i in range(len(memory_ids)):
            for j in range(i + 1, len(memory_ids)):
                pair_key = self._make_pair_key(memory_ids[i], memory_ids[j])
                self.pair_counts[pair_key] += 1

        # Update last access times
        now = utc_now()
        for memory_id in memory_ids:
            self.last_access[memory_id] = now

    def _make_pair_key(self, id1: str, id2: str) -> str:
        """Create consistent pair key regardless of order."""
        return ":".join(sorted([id1, id2]))

    def get_recommendations(self, memory_id: str, limit: int = 5) -> List[Dict]:
        """
        Get recommendations based on co-access patterns.

        Args:
            memory_id: Source memory ID
            limit: Maximum recommendations

        Returns:
            List of recommended memory IDs with scores
        """
        recommendations = []

        for pair_key, count in self.pair_counts.items():
            ids = pair_key.split(":")
            if memory_id in ids:
                other_id = ids[0] if ids[1] == memory_id else ids[1]
                recommendations.append({
                    "memory_id": other_id,
                    "co_access_count": count,
                    "last_accessed": self.last_access.get(other_id)
                })

        # Sort by co-access count
        recommendations.sort(key=lambda x: x["co_access_count"], reverse=True)
        return recommendations[:limit]

    def get_stats(self) -> Dict:
        """Get co-access tracking statistics."""
        return {
            "total_pairs": len(self.pair_counts),
            "total_unique_memories": len(self.last_access),
            "most_common_pairs": [
                {"pair": k, "count": v}
                for k, v in sorted(
                    self.pair_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            ]
        }

    def reset(self):
        """Reset co-access tracking data."""
        self.pair_counts.clear()
        self.last_access.clear()


# Global co-access tracker instance
_co_access_tracker = CoAccessTracker()


def get_co_access_tracker() -> CoAccessTracker:
    """Get the global co-access tracker instance."""
    return _co_access_tracker


def generate_comprehensive_recommendations(
    client: QdrantClient,
    collection_name: str,
    memory: Dict,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Generate comprehensive recommendations for a memory.

    Args:
        client: Qdrant client
        collection_name: Collection name
        memory: Memory to generate recommendations for
        limit: Maximum recommendations per category

    Returns:
        Dictionary with recommendations by category
    """
    try:
        recommendations = {}

        # Context-aware suggestions
        recommendations["context_aware"] = RecommendationEngine.context_aware_suggestions(
            client,
            collection_name,
            memory,
            project_context=memory.get("project"),
            limit=limit
        )

        # If error, suggest patterns
        if memory.get("type") == "error":
            recommendations["suggested_patterns"] = RecommendationEngine.suggest_patterns_for_error(
                client,
                collection_name,
                memory.get("tags", []),
                memory.get("content", ""),
                limit=limit
            )

        # Collaborative filtering
        co_access_data = {
            "pairs": _co_access_tracker.pair_counts
        }
        recommendations["collaborative"] = RecommendationEngine.collaborative_recommendations(
            client,
            collection_name,
            memory.get("id"),
            co_access_data=co_access_data,
            limit=limit
        )

        recommendations["generated_at"] = utc_now().isoformat()

        return recommendations

    except Exception as e:
        logger.error(f"Failed to generate comprehensive recommendations: {e}")
        return {"error": str(e)}
