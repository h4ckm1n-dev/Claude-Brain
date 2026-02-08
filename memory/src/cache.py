"""Semantic query caching for faster repeated searches.

Caches search results by query embedding similarity.
Cache hits provide 5-10x faster responses.
"""

import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_COLLECTION = "query_cache"
CACHE_SIMILARITY_THRESHOLD = 0.85  # Lowered for better hit rate (0.85-0.90 sweet spot)
CACHE_TTL_HOURS = 24
CACHE_MAX_SIZE = 1000  # Max cached queries

# Cache statistics
_cache_stats = {
    "hits": 0,
    "misses": 0,
    "stores": 0,
    "evictions": 0
}


def init_cache_collection(client: QdrantClient, embedding_dim: int) -> None:
    """Initialize the query cache collection."""
    try:
        client.get_collection(CACHE_COLLECTION)
        logger.info(f"Cache collection '{CACHE_COLLECTION}' already exists")
    except (UnexpectedResponse, Exception):
        logger.info(f"Creating cache collection '{CACHE_COLLECTION}'")
        client.create_collection(
            collection_name=CACHE_COLLECTION,
            vectors_config=models.VectorParams(
                size=embedding_dim,
                distance=models.Distance.COSINE
            )
        )


def check_cache(
    client: QdrantClient,
    query_embedding: list[float]
) -> Optional[list[dict]]:
    """
    Check if a similar query exists in cache.

    Args:
        client: Qdrant client
        query_embedding: The query embedding to check

    Returns:
        Cached results if found (similarity > threshold), None otherwise
    """
    try:
        # Search for similar cached queries
        results = client.query_points(
            collection_name=CACHE_COLLECTION,
            query=query_embedding,
            limit=1,
            score_threshold=CACHE_SIMILARITY_THRESHOLD,
            with_payload=True
        ).points

        if results:
            cached = results[0]

            # Check TTL
            cached_at = datetime.fromisoformat(cached.payload.get("cached_at", ""))
            if datetime.now(timezone.utc) - cached_at > timedelta(hours=CACHE_TTL_HOURS):
                logger.debug("Cache hit but expired, treating as miss")
                _cache_stats["misses"] += 1
                # Delete expired entry
                client.delete(
                    collection_name=CACHE_COLLECTION,
                    points_selector=models.PointIdsList(points=[cached.id])
                )
                return None

            _cache_stats["hits"] += 1
            logger.debug(f"Cache hit (score: {cached.score:.4f})")

            # Parse cached results
            return json.loads(cached.payload.get("results", "[]"))

        _cache_stats["misses"] += 1
        return None

    except Exception as e:
        logger.debug(f"Cache check failed: {e}")
        _cache_stats["misses"] += 1
        return None


def store_cache(
    client: QdrantClient,
    query_embedding: list[float],
    query_text: str,
    results: list[dict]
) -> None:
    """
    Store query results in cache.

    Args:
        client: Qdrant client
        query_embedding: The query embedding
        query_text: Original query text (for debugging)
        results: Search results to cache
    """
    try:
        # Check cache size and evict if needed
        _evict_if_needed(client)

        # Generate unique ID from embedding hash
        point_id = abs(hash(tuple(query_embedding[:10]))) % (2**63)

        # Serialize results (only essential fields)
        cached_results = []
        for r in results:
            cached_results.append({
                "id": r.get("id"),
                "content": r.get("content"),
                "type": r.get("type"),
                "score": r.get("score"),
                "rerank_score": r.get("rerank_score"),
                "tags": r.get("tags", []),
                "memory_strength": r.get("memory_strength")
            })

        client.upsert(
            collection_name=CACHE_COLLECTION,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=query_embedding,
                    payload={
                        "query": query_text,
                        "results": json.dumps(cached_results),
                        "cached_at": datetime.now(timezone.utc).isoformat(),
                        "result_count": len(results)
                    }
                )
            ]
        )

        _cache_stats["stores"] += 1
        logger.debug(f"Cached query: '{query_text[:50]}...' ({len(results)} results)")

    except Exception as e:
        logger.debug(f"Cache store failed: {e}")


def _evict_if_needed(client: QdrantClient) -> None:
    """Evict old entries if cache is full."""
    try:
        collection_info = client.get_collection(CACHE_COLLECTION)
        current_size = collection_info.points_count

        if current_size >= CACHE_MAX_SIZE:
            # Delete oldest 10% of entries
            evict_count = CACHE_MAX_SIZE // 10

            # Get oldest entries by cached_at
            oldest = client.scroll(
                collection_name=CACHE_COLLECTION,
                limit=evict_count,
                with_payload=["cached_at"],
                order_by=models.OrderBy(
                    key="cached_at",
                    direction=models.Direction.ASC
                )
            )[0]

            if oldest:
                ids_to_delete = [point.id for point in oldest]
                client.delete(
                    collection_name=CACHE_COLLECTION,
                    points_selector=models.PointIdsList(points=ids_to_delete)
                )
                _cache_stats["evictions"] += len(ids_to_delete)
                logger.info(f"Evicted {len(ids_to_delete)} old cache entries")

    except Exception as e:
        logger.debug(f"Cache eviction check failed: {e}")


def clear_cache(client: QdrantClient) -> int:
    """Clear all cache entries. Returns number deleted."""
    try:
        collection_info = client.get_collection(CACHE_COLLECTION)
        count = collection_info.points_count

        # Delete and recreate collection
        client.delete_collection(CACHE_COLLECTION)
        init_cache_collection(client, 768)  # Assume 768 dims

        logger.info(f"Cleared {count} cache entries")
        return count

    except Exception as e:
        logger.error(f"Cache clear failed: {e}")
        return 0


def get_cache_stats() -> dict:
    """Get cache statistics."""
    total = _cache_stats["hits"] + _cache_stats["misses"]
    hit_rate = _cache_stats["hits"] / total if total > 0 else 0

    return {
        **_cache_stats,
        "total_queries": total,
        "hit_rate": round(hit_rate * 100, 2),
        "ttl_hours": CACHE_TTL_HOURS,
        "max_size": CACHE_MAX_SIZE,
        "similarity_threshold": CACHE_SIMILARITY_THRESHOLD
    }


def reset_cache_stats() -> None:
    """Reset cache statistics."""
    global _cache_stats
    _cache_stats = {
        "hits": 0,
        "misses": 0,
        "stores": 0,
        "evictions": 0
    }
