"""Semantic clustering - auto-organize memories by topic.

Real brains organize memories into hierarchical concepts and categories.
This module implements semantic clustering to discover topics automatically.
"""

import logging
from typing import List, Dict, Optional
from collections import Counter
import re

from .collections import get_client, COLLECTION_NAME
from .embeddings import embed_text

logger = logging.getLogger(__name__)


def extract_topics_from_memories(
    min_cluster_size: int = 3,
    max_topics: int = 20
) -> List[Dict]:
    """
    Discover topics by clustering semantically similar memories.

    Uses tags, content analysis, and semantic similarity to find natural groupings.

    Args:
        min_cluster_size: Minimum memories per topic
        max_topics: Maximum topics to return

    Returns:
        List of topics with memory IDs and representative terms
    """
    client = get_client()

    try:
        # Get all memories
        memories, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000
        )

        if len(memories) < min_cluster_size:
            return []

        # Extract tags and keywords
        tag_to_memories = {}
        keyword_to_memories = {}

        for mem in memories:
            mem_id = str(mem.id)
            payload = mem.payload

            # Cluster by tags
            tags = payload.get("tags", [])
            for tag in tags:
                if tag not in tag_to_memories:
                    tag_to_memories[tag] = []
                tag_to_memories[tag].append(mem_id)

            # Extract keywords from content
            content = payload.get("content", "")
            keywords = extract_keywords(content)
            for kw in keywords:
                if kw not in keyword_to_memories:
                    keyword_to_memories[kw] = []
                keyword_to_memories[kw].append(mem_id)

        # Find significant clusters (tags/keywords with enough memories)
        topics = []

        # Tag-based topics
        for tag, mem_ids in tag_to_memories.items():
            if len(mem_ids) >= min_cluster_size:
                topics.append({
                    "topic": tag,
                    "type": "tag",
                    "memory_ids": mem_ids,
                    "size": len(mem_ids),
                    "representative_term": tag
                })

        # Keyword-based topics (only if not already covered by tags)
        existing_terms = {t["representative_term"] for t in topics}
        for kw, mem_ids in keyword_to_memories.items():
            if len(mem_ids) >= min_cluster_size and kw not in existing_terms:
                topics.append({
                    "topic": kw,
                    "type": "keyword",
                    "memory_ids": list(set(mem_ids)),  # Deduplicate
                    "size": len(set(mem_ids)),
                    "representative_term": kw
                })

        # Sort by size and limit
        topics.sort(key=lambda x: x["size"], reverse=True)
        topics = topics[:max_topics]

        logger.info(f"Discovered {len(topics)} semantic topics")

        return topics

    except Exception as e:
        logger.error(f"Topic extraction failed: {e}")
        return []


def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """
    Extract significant keywords from text.

    Simple implementation:
    - Remove common words
    - Extract technical terms, proper nouns
    - Return most significant
    """
    # Common words to filter out
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
        'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them',
        'my', 'your', 'his', 'her', 'its', 'our', 'their'
    }

    # Extract words (alphanumeric + hyphens/underscores)
    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_-]*\b', text.lower())

    # Filter stopwords and short words
    significant = [
        w for w in words
        if len(w) > 3 and w not in stopwords
    ]

    # Count frequencies
    freq = Counter(significant)

    # Return top keywords
    return [word for word, _ in freq.most_common(max_keywords)]


def create_topic_summaries(topics: List[Dict]) -> List[Dict]:
    """
    Create human-readable summaries for discovered topics.

    Args:
        topics: List of topics from extract_topics_from_memories

    Returns:
        Topics with added summaries
    """
    client = get_client()

    try:
        for topic in topics:
            mem_ids = topic["memory_ids"][:10]  # Sample first 10

            # Get sample memories
            points = client.retrieve(
                collection_name=COLLECTION_NAME,
                ids=mem_ids
            )

            # Extract common themes
            all_content = []
            memory_types = []

            for point in points:
                payload = point.payload
                all_content.append(payload.get("content", ""))
                memory_types.append(payload.get("type", "unknown"))

            # Most common memory type
            type_counts = Counter(memory_types)
            dominant_type = type_counts.most_common(1)[0][0] if type_counts else "mixed"

            # Create summary
            summary = f"Topic '{topic['representative_term']}': {topic['size']} {dominant_type} memories"

            topic["summary"] = summary
            topic["dominant_type"] = dominant_type
            topic["sample_content"] = all_content[:3]

        return topics

    except Exception as e:
        logger.error(f"Topic summary creation failed: {e}")
        return topics


def cluster_memories_hierarchically() -> Dict:
    """
    Create hierarchical topic clusters (topics -> subtopics).

    Returns:
        Hierarchical structure of topics
    """
    topics = extract_topics_from_memories(min_cluster_size=3, max_topics=20)
    topics = create_topic_summaries(topics)

    # Group topics by similarity (simple parent-child)
    # For example: "python" parent of "python-ml", "python-api"
    hierarchy = {
        "root": {
            "topics": [],
            "subtopics": {}
        }
    }

    for topic in topics:
        term = topic["representative_term"]

        # Find potential parent
        parent = None
        for other in topics:
            other_term = other["representative_term"]
            if other_term != term and term.startswith(other_term):
                parent = other_term
                break

        if parent:
            # Add as subtopic
            if parent not in hierarchy["root"]["subtopics"]:
                hierarchy["root"]["subtopics"][parent] = []
            hierarchy["root"]["subtopics"][parent].append(topic)
        else:
            # Add as root topic
            hierarchy["root"]["topics"].append(topic)

    return hierarchy


def get_topic_timeline(topic_name: str, limit: int = 50) -> List[Dict]:
    """
    Get chronological timeline of memories in a topic.

    Args:
        topic_name: Topic to get timeline for
        limit: Max memories to return

    Returns:
        Chronologically ordered memories in topic
    """
    client = get_client()

    try:
        from qdrant_client import models as qmodels

        # Search by tag or content
        memories, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=qmodels.Filter(
                should=[
                    qmodels.FieldCondition(
                        key="tags",
                        match=qmodels.MatchAny(any=[topic_name])
                    )
                ]
            ),
            limit=limit
        )

        # Sort by creation time
        timeline = []
        for mem in memories:
            payload = mem.payload
            timeline.append({
                "id": str(mem.id),
                "content": payload.get("content", "")[:200],
                "created_at": payload.get("created_at"),
                "type": payload.get("type"),
                "importance": payload.get("importance_score", 0.5)
            })

        timeline.sort(key=lambda x: x["created_at"])

        return timeline

    except Exception as e:
        logger.error(f"Timeline extraction failed for {topic_name}: {e}")
        return []
