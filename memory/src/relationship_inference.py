"""Automatic relationship discovery between memories."""

import logging
import re
from typing import List, Tuple, Dict, Optional
from datetime import datetime, timedelta

from .graph import create_relationship
from .collections import get_client, COLLECTION_NAME
from .embeddings import embed_text

logger = logging.getLogger(__name__)


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
                error_vector = embed_text(error_content)

                # Search for similar memories AFTER this error
                candidates = client.search(
                    collection_name=COLLECTION_NAME,
                    query_vector=error_vector,
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
                )

                # Check if any candidate is a likely solution (created after error)
                for candidate in candidates:
                    candidate_time = datetime.fromisoformat(candidate.payload["created_at"])

                    # Must be created after error and within lookback window
                    if (candidate_time > error_time and
                        (candidate_time - error_time).days <= lookback_days):

                        # Link solution → error (FIXES)
                        create_relationship(
                            source_id=str(candidate.id),
                            target_id=str(error.id),
                            relation_type="fixes"  # Lowercase per API requirement
                        )
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
                limit=batch_size
            )

            links_created = 0

            for memory in recent:
                # Search for similar
                similar = client.search(
                    collection_name=COLLECTION_NAME,
                    query_vector=memory.vector,
                    limit=5,
                    score_threshold=RelationshipInference.RELATED_THRESHOLD
                )

                # Link top 3 similar (excluding self)
                for candidate in similar[:3]:
                    if str(candidate.id) != str(memory.id):
                        try:
                            create_relationship(
                                source_id=str(memory.id),
                                target_id=str(candidate.id),
                                relation_type="related"  # Lowercase
                            )
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
                            create_relationship(
                                source_id=str(mems[i].id),
                                target_id=str(mems[i+1].id),
                                relation_type="follows"  # Lowercase
                            )
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
                        cause_vector = embed_text(cause_text)
                        candidates = client.search(
                            collection_name=COLLECTION_NAME,
                            query_vector=cause_vector,
                            limit=3,
                            score_threshold=0.8
                        )

                        if candidates and str(candidates[0].id) != str(memory.id):
                            try:
                                # Link: cause → effect
                                create_relationship(
                                    source_id=str(candidates[0].id),
                                    target_id=str(memory.id),
                                    relation_type="causes"  # Lowercase
                                )
                                links_created += 1
                            except Exception:
                                pass

            logger.info(f"Created {links_created} CAUSES relationships")
            return links_created

        except Exception as e:
            logger.error(f"Error inferring causal links: {e}")
            return 0
