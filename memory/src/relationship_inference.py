"""Automatic relationship discovery between memories.

Implements Phase 1.2: Automatic Relationship Inference
- On-write inference: Automatically infer relationships when storing new memories
- Temporal inference: Track memories created in same session/timeframe
- Semantic inference: Find similar memories and infer relationship types
- Co-access inference: Track memories accessed together
- Type-based patterns: Infer relationships based on memory type combinations
"""

import logging
import re
from typing import List, Tuple, Dict, Optional
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from .graph import create_relationship, is_graph_enabled
from .collections import get_client, COLLECTION_NAME
from .embeddings import embed_text
from .models import MemoryType, RelationType

logger = logging.getLogger(__name__)

# Co-access tracking (in-memory for now, could be persisted)
_co_access_tracker: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
CO_ACCESS_THRESHOLD = 5  # Number of co-accesses before inferring RELATED


class RelationshipInference:
    """Automatically infer and create relationships between memories."""

    # Similarity thresholds
    RELATED_THRESHOLD = 0.75  # Semantic similarity for RELATED
    FIXES_THRESHOLD = 0.85     # High similarity for error→solution

    @staticmethod
    async def infer_error_solution_links(lookback_days: int = 30) -> int:
        """
        Find errors that were later solved and link them.

        Logic:
        - Find unresolved errors
        - Search for later learning/decision memories with similar content
        - If high similarity + temporal proximity, link as FIXES

        Returns:
            Number of FIXES relationships created
        """
        try:
            from qdrant_client import models as qmodels

            client = get_client()

            # Get unresolved errors
            errors, _ = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="type",
                            match=qmodels.MatchValue(value="error")
                        ),
                        qmodels.FieldCondition(
                            key="resolved",
                            match=qmodels.MatchValue(value=False)
                        )
                    ]
                ),
                limit=50
            )

            links_created = 0

            for error in errors:
                error_time = datetime.fromisoformat(error.payload["created_at"])
                error_content = error.payload.get("error_message") or error.payload["content"]

                # Embed error
                error_vector = embed_text(error_content)["dense"]

                # Search for similar memories AFTER this error
                candidates = client.query_points(
                    collection_name=COLLECTION_NAME,
                    query=error_vector,
                    using="dense",
                    query_filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="type",
                                match=qmodels.MatchAny(any=["learning", "decision", "docs"])
                            ),
                        ]
                    ),
                    limit=5,
                    score_threshold=RelationshipInference.FIXES_THRESHOLD
                ).points

                # Check if any candidate is a likely solution (created after error)
                for candidate in candidates:
                    candidate_time = datetime.fromisoformat(candidate.payload["created_at"])

                    # Must be created after error and within lookback window
                    if (candidate_time > error_time and
                        (candidate_time - error_time).days <= lookback_days):

                        # Link solution → error (FIXES)
                        # UPPERCASE required for Neo4j Cypher
                        success = create_relationship(
                            source_id=str(candidate.id),
                            target_id=str(error.id),
                            relation_type="FIXES"
                        )
                        if success:
                            links_created += 1
                            logger.info(f"Linked solution {candidate.id} FIXES error {error.id}")
                        break

            logger.info(f"Created {links_created} FIXES relationships")
            return links_created

        except Exception as e:
            logger.error(f"Error inferring error-solution links: {e}")
            return 0

    @staticmethod
    async def infer_related_links(batch_size: int = 20) -> int:
        """
        Find semantically similar memories and link them as RELATED.

        Logic:
        - Take recent memories without many relationships
        - Find top-K similar memories
        - Link if similarity > threshold

        Returns:
            Number of RELATED relationships created
        """
        try:
            from qdrant_client import models as qmodels

            client = get_client()

            # Get recent memories (last 7 days)
            recent, _ = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="created_at",
                            range=qmodels.DatetimeRange(
                                gte=datetime.now() - timedelta(days=7)
                            )
                        )
                    ]
                ),
                limit=batch_size,
                with_vectors=["dense"]
            )

            links_created = 0

            for memory in recent:
                # Get dense vector
                mem_vector = memory.vector
                if isinstance(mem_vector, dict):
                    mem_vector = mem_vector.get("dense")
                if not mem_vector:
                    continue

                # Search for similar
                similar = client.query_points(
                    collection_name=COLLECTION_NAME,
                    query=mem_vector,
                    using="dense",
                    limit=5,
                    score_threshold=RelationshipInference.RELATED_THRESHOLD
                ).points

                # Link top 3 similar (excluding self)
                for candidate in similar[:3]:
                    if str(candidate.id) != str(memory.id):
                        try:
                            # UPPERCASE required for Neo4j Cypher
                            success = create_relationship(
                                source_id=str(memory.id),
                                target_id=str(candidate.id),
                                relation_type="RELATED"
                            )
                            if success:
                                links_created += 1
                        except Exception as e:
                            # Skip if relationship already exists
                            if "already exists" not in str(e).lower():
                                logger.warning(f"Failed to link {memory.id} to {candidate.id}: {e}")

            logger.info(f"Created {links_created} RELATED relationships")
            return links_created

        except Exception as e:
            logger.error(f"Error inferring related links: {e}")
            return 0

    @staticmethod
    async def infer_temporal_links(hours_window: int = 2) -> int:
        """
        Create FOLLOWS relationships based on temporal proximity.

        Logic:
        - Find memories in same project created within N hours
        - Link as FOLLOWS if sequential

        Returns:
            Number of FOLLOWS relationships created
        """
        try:
            from qdrant_client import models as qmodels

            client = get_client()

            # Get recent memories grouped by project
            memories, _ = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="created_at",
                            range=qmodels.DatetimeRange(
                                gte=datetime.now() - timedelta(days=7)
                            )
                        )
                    ]
                ),
                limit=100
            )

            # Group by project
            by_project = {}
            for mem in memories:
                project = mem.payload.get("project", "unknown")
                if project not in by_project:
                    by_project[project] = []
                by_project[project].append(mem)

            links_created = 0

            # Within each project, link sequential memories
            for project, mems in by_project.items():
                # Sort by creation time
                mems.sort(key=lambda m: m.payload["created_at"])

                # Link sequential pairs within time window
                for i in range(len(mems) - 1):
                    curr_time = datetime.fromisoformat(mems[i].payload["created_at"])
                    next_time = datetime.fromisoformat(mems[i+1].payload["created_at"])

                    if (next_time - curr_time).total_seconds() / 3600 <= hours_window:
                        try:
                            # UPPERCASE required for Neo4j Cypher
                            success = create_relationship(
                                source_id=str(mems[i].id),
                                target_id=str(mems[i+1].id),
                                relation_type="FOLLOWS"
                            )
                            if success:
                                links_created += 1
                        except Exception as e:
                            # Skip if relationship already exists
                            pass

            logger.info(f"Created {links_created} FOLLOWS relationships")
            return links_created

        except Exception as e:
            logger.error(f"Error inferring temporal links: {e}")
            return 0

    @staticmethod
    async def infer_causal_links() -> int:
        """
        Detect CAUSES relationships using keyword patterns.

        Logic:
        - Search for memories mentioning "caused by", "due to", "because of"
        - Extract mentioned concepts
        - Link if both memories exist

        Returns:
            Number of CAUSES relationships created
        """
        try:
            client = get_client()

            # Patterns indicating causality
            causal_patterns = [
                r"caused by (.+?)(?:\.|$)",
                r"due to (.+?)(?:\.|$)",
                r"because of (.+?)(?:\.|$)",
                r"triggered by (.+?)(?:\.|$)"
            ]

            # Get recent memories
            memories, _ = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=None,
                limit=100
            )

            links_created = 0

            for memory in memories:
                content = memory.payload.get("content", "") + " " + memory.payload.get("context", "")

                # Check for causal patterns
                for pattern in causal_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for cause_text in matches:
                        # Search for memories mentioning this cause
                        cause_vector = embed_text(cause_text)["dense"]
                        candidates = client.query_points(
                            collection_name=COLLECTION_NAME,
                            query=cause_vector,
                            using="dense",
                            limit=3,
                            score_threshold=0.8
                        ).points

                        if candidates and str(candidates[0].id) != str(memory.id):
                            try:
                                # Link: cause → effect
                                # UPPERCASE required for Neo4j Cypher
                                success = create_relationship(
                                    source_id=str(candidates[0].id),
                                    target_id=str(memory.id),
                                    relation_type="CAUSES"
                                )
                                if success:
                                    links_created += 1
                            except Exception:
                                pass

            logger.info(f"Created {links_created} CAUSES relationships")
            return links_created

        except Exception as e:
            logger.error(f"Error inferring causal links: {e}")
            return 0

    @staticmethod
    def infer_on_write(memory_id: str, memory_type: str, memory_content: str,
                       memory_tags: List[str], memory_vector: List[float],
                       created_at: datetime, project: Optional[str] = None) -> Dict[str, int]:
        """
        Infer relationships immediately when a new memory is stored.
        This is called from collections.store_memory() after successful storage.

        Args:
            memory_id: ID of the newly stored memory
            memory_type: Type of memory (error, learning, etc.)
            memory_content: Content text
            memory_tags: List of tags
            memory_vector: Dense embedding vector
            created_at: Creation timestamp
            project: Optional project name

        Returns:
            Dict with counts of relationships created by type
        """
        if not is_graph_enabled():
            return {}

        try:
            from qdrant_client import models as qmodels

            client = get_client()
            stats = {"fixes": 0, "supports": 0, "related": 0, "similar_to": 0}

            # 1. Temporal inference: Find memories in same project created recently (last 2 hours)
            time_window = created_at - timedelta(hours=2)
            if project:
                recent_in_project, _ = client.scroll(
                    collection_name=COLLECTION_NAME,
                    scroll_filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="project",
                                match=qmodels.MatchValue(value=project)
                            ),
                            qmodels.FieldCondition(
                                key="created_at",
                                range=qmodels.DatetimeRange(gte=time_window)
                            )
                        ]
                    ),
                    limit=10
                )

                # Link to most recent memory in same project (FOLLOWS)
                if recent_in_project:
                    most_recent = max(recent_in_project,
                                     key=lambda m: m.payload.get("created_at", ""))
                    if str(most_recent.id) != memory_id:
                        if create_relationship(str(most_recent.id), memory_id, "FOLLOWS"):
                            logger.debug(f"Temporal link: {most_recent.id} FOLLOWS {memory_id}")

            # 2. Semantic inference with type-based patterns
            similar = client.query_points(
                collection_name=COLLECTION_NAME,
                query=memory_vector,
                using="dense",
                limit=10,
                score_threshold=0.75
            ).points

            for candidate in similar:
                if str(candidate.id) == memory_id:
                    continue

                candidate_type = candidate.payload.get("type")
                similarity = candidate.score

                # Type-based relationship inference
                rel_type = RelationshipInference._infer_relationship_from_types(
                    memory_type, candidate_type, similarity
                )

                if rel_type:
                    # Check for specific patterns
                    if rel_type == "FIXES":
                        # For FIXES: candidate (learning/decision) should be after error
                        if memory_type in ["learning", "decision"] and candidate_type == "error":
                            candidate_time = datetime.fromisoformat(candidate.payload["created_at"])
                            if candidate_time.tzinfo is None:
                                candidate_time = candidate_time.replace(tzinfo=timezone.utc)
                            if created_at.tzinfo is None:
                                created_at = created_at.replace(tzinfo=timezone.utc)

                            # New memory should be AFTER the error
                            if created_at > candidate_time and (created_at - candidate_time).days <= 30:
                                if create_relationship(memory_id, str(candidate.id), rel_type):
                                    stats["fixes"] += 1
                                    logger.info(f"Inferred FIXES: {memory_id} → {candidate.id}")

                    elif rel_type == "SUPPORTS":
                        if create_relationship(memory_id, str(candidate.id), rel_type):
                            stats["supports"] += 1
                            logger.debug(f"Inferred SUPPORTS: {memory_id} → {candidate.id}")

                    elif rel_type == "SIMILAR_TO":
                        if create_relationship(memory_id, str(candidate.id), rel_type):
                            stats["similar_to"] += 1
                            logger.debug(f"Inferred SIMILAR_TO: {memory_id} → {candidate.id}")

                    elif rel_type == "RELATED" and similarity > 0.8:
                        if create_relationship(memory_id, str(candidate.id), rel_type):
                            stats["related"] += 1
                            logger.debug(f"Inferred RELATED: {memory_id} → {candidate.id}")

            # 3. Tag-based inference: Find memories with overlapping tags
            if memory_tags and len(memory_tags) >= 2:
                tag_matches, _ = client.scroll(
                    collection_name=COLLECTION_NAME,
                    scroll_filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="tags",
                                match=qmodels.MatchAny(any=memory_tags)
                            )
                        ]
                    ),
                    limit=5
                )

                for match in tag_matches:
                    if str(match.id) == memory_id:
                        continue

                    match_tags = set(match.payload.get("tags", []))
                    common_tags = set(memory_tags) & match_tags

                    # If >50% tags overlap, create RELATED
                    if len(common_tags) >= max(2, len(memory_tags) // 2):
                        if create_relationship(memory_id, str(match.id), "RELATED"):
                            stats["related"] += 1
                            logger.debug(f"Tag-based RELATED: {memory_id} → {match.id} (tags: {common_tags})")

            total_links = sum(stats.values())
            if total_links > 0:
                logger.info(f"On-write inference for {memory_id}: created {total_links} relationships")

            return stats

        except Exception as e:
            logger.error(f"Error in on-write inference for {memory_id}: {e}")
            return {}

    @staticmethod
    def _infer_relationship_from_types(type1: str, type2: str, similarity: float) -> Optional[str]:
        """
        Infer relationship type based on memory type combinations and similarity.

        Type-based patterns:
        - ERROR + LEARNING → FIXES (if learning comes after error)
        - ERROR + DECISION → FIXES (if decision comes after error)
        - PATTERN + DECISION → SUPPORTS
        - PATTERN + LEARNING → SUPPORTS
        - ERROR + ERROR → SIMILAR_TO (if high similarity)
        - DECISION + DECISION → SUPERSEDES (if very high similarity, handled separately)
        - * + * → RELATED (if moderate similarity)

        Args:
            type1: Type of first memory
            type2: Type of second memory
            similarity: Semantic similarity score

        Returns:
            Relationship type or None
        """
        # High similarity error-error → SIMILAR_TO (potential duplicates)
        if type1 == "error" and type2 == "error" and similarity > 0.85:
            return "SIMILAR_TO"

        # Learning/Decision after error → FIXES (temporal check done in caller)
        if type1 in ["learning", "decision"] and type2 == "error" and similarity > 0.85:
            return "FIXES"

        # Pattern supports decision/learning
        if type1 == "pattern" and type2 in ["decision", "learning"] and similarity > 0.75:
            return "SUPPORTS"
        if type2 == "pattern" and type1 in ["decision", "learning"] and similarity > 0.75:
            return "SUPPORTS"

        # Decision supports learning
        if type1 == "decision" and type2 == "learning" and similarity > 0.8:
            return "SUPPORTS"

        # Moderate similarity → RELATED
        if similarity > 0.8:
            return "RELATED"

        return None

    @staticmethod
    def track_co_access(memory_ids: List[str]) -> None:
        """
        Track that multiple memories were accessed together (e.g., in same search).
        After threshold co-accesses, infer RELATED relationships.

        Args:
            memory_ids: List of memory IDs accessed together
        """
        global _co_access_tracker

        # Update co-access counts for all pairs
        for i, id1 in enumerate(memory_ids):
            for id2 in memory_ids[i+1:]:
                # Store both directions for easier lookup
                _co_access_tracker[id1][id2] += 1
                _co_access_tracker[id2][id1] += 1

                # Check if threshold reached
                if _co_access_tracker[id1][id2] == CO_ACCESS_THRESHOLD:
                    logger.info(f"Co-access threshold reached for {id1} and {id2}")
                    if is_graph_enabled():
                        if create_relationship(id1, id2, "RELATED"):
                            logger.info(f"Created RELATED relationship from co-access: {id1} ↔ {id2}")

    @staticmethod
    def get_co_access_stats() -> Dict:
        """Get statistics about co-access tracking."""
        global _co_access_tracker

        total_pairs = sum(len(targets) for targets in _co_access_tracker.values()) // 2
        high_cooccurrence = sum(
            1 for targets in _co_access_tracker.values()
            for count in targets.values()
            if count >= CO_ACCESS_THRESHOLD
        ) // 2

        return {
            "total_pairs_tracked": total_pairs,
            "pairs_above_threshold": high_cooccurrence,
            "threshold": CO_ACCESS_THRESHOLD
        }

    @staticmethod
    def reset_co_access_tracker() -> None:
        """Reset the co-access tracker (for testing or maintenance)."""
        global _co_access_tracker
        _co_access_tracker.clear()
        logger.info("Co-access tracker reset")
