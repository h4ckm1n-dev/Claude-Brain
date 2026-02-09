"""Qdrant collection management with hybrid search support.

Supports:
- Dense vectors (nomic-embed-text-v1.5, 768 dims)
- Sparse vectors (BM42/SPLADE for keyword matching)
- RRF (Reciprocal Rank Fusion) for hybrid search
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
from enum import Enum
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from .models import (
    Memory, MemoryCreate, MemoryUpdate, MemoryType,
    SearchQuery, SearchResult, Relation, RelationType
)
from .embeddings import (
    embed_text, embed_query, get_embedding_dim,
    is_sparse_enabled, embed_text_legacy
)
from .reranker import rerank_search_results, is_reranker_enabled
from .cache import (
    init_cache_collection, check_cache, store_cache, get_cache_stats
)
from .fusion import apply_learned_fusion
from .graph import (
    is_graph_enabled, init_graph_schema, create_memory_node,
    create_relationship, get_related_memories, get_graph_stats,
    delete_memory_node
)
from .graph_search import expand_search_with_graph
from .query_understanding import route_query

logger = logging.getLogger(__name__)

# Fields that affect quality score — any set_payload touching these should recalculate
QUALITY_AFFECTING_FIELDS = frozenset({
    "content", "tags", "importance_score", "pinned", "resolved", "solution",
    "prevention", "rationale", "alternatives", "decision", "error_message",
    "context", "state", "relations", "access_count", "memory_strength",
    "user_rating", "user_rating_count", "user_feedback", "archived",
})

# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "memories"

# Search modes
SearchMode = Literal["semantic", "keyword", "hybrid"]


_client: Optional[QdrantClient] = None


def get_client() -> QdrantClient:
    """Get Qdrant client (singleton)."""
    global _client
    if _client is None:
        _client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return _client


def safe_set_payload(
    memory_id: str,
    payload: dict,
    *,
    recalc_quality: bool = True,
    run_enrichment: bool = False,
    collection_name: str | None = None,
) -> None:
    """Centralized wrapper for Qdrant set_payload that auto-triggers quality recalc.

    This is the ONLY function that should be used to modify memory payloads
    outside of full upserts (which go through store_memory/update_memory).

    Args:
        memory_id: ID of the memory to update
        payload: Dict of fields to set/update
        recalc_quality: Auto-recalculate quality if quality-affecting fields changed (default True)
        run_enrichment: Run post-update enrichment pipeline (default False)
        collection_name: Override collection name (defaults to COLLECTION_NAME)
    """
    col = collection_name or COLLECTION_NAME
    client = get_client()

    # Apply the payload update
    client.set_payload(
        collection_name=col,
        payload=payload,
        points=[memory_id],
    )

    # Run enrichment pipeline if requested (derives prevention, rationale, context, alternatives)
    if run_enrichment:
        try:
            _post_update_pipeline(memory_id, payload)
            return  # _post_update_pipeline already recalculates quality
        except Exception as e:
            logger.warning(f"safe_set_payload enrichment failed for {memory_id}: {e}")

    # Auto-recalculate quality if any quality-affecting field was touched
    if recalc_quality and (set(payload.keys()) & QUALITY_AFFECTING_FIELDS):
        try:
            from .quality_tracking import QualityScoreCalculator
            QualityScoreCalculator.recalculate_single_memory_quality(
                client, col, memory_id
            )
        except Exception as e:
            logger.warning(f"safe_set_payload quality recalc failed for {memory_id}: {e}")


def init_collections() -> None:
    """Initialize Qdrant collections with hybrid vector support."""
    client = get_client()

    try:
        collection_info = client.get_collection(COLLECTION_NAME)
        # Check if collection has correct vector size
        if hasattr(collection_info.config.params, 'vectors'):
            vectors_config = collection_info.config.params.vectors
            if isinstance(vectors_config, dict):
                # Named vectors
                if "dense" in vectors_config:
                    current_dim = vectors_config["dense"].size
                    if current_dim != get_embedding_dim():
                        logger.warning(
                            f"Collection has dimension {current_dim}, "
                            f"expected {get_embedding_dim()}. Migration needed."
                        )
            else:
                # Single vector (old format)
                if vectors_config.size != get_embedding_dim():
                    logger.warning(
                        f"Collection has dimension {vectors_config.size}, "
                        f"expected {get_embedding_dim()}. Migration needed."
                    )
        logger.info(f"Collection '{COLLECTION_NAME}' already exists")
    except (UnexpectedResponse, Exception):
        logger.info(f"Creating collection '{COLLECTION_NAME}' with hybrid vectors")
        _create_collection_with_hybrid_vectors(client)

    # Initialize query cache collection
    try:
        init_cache_collection(client, get_embedding_dim())
        logger.info("Query cache collection initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize cache collection: {e}")

    # Initialize Neo4j graph schema
    try:
        if is_graph_enabled():
            init_graph_schema()
            logger.info("Neo4j knowledge graph initialized")
        else:
            logger.info("Neo4j not available, graph features disabled")
    except Exception as e:
        logger.warning(f"Failed to initialize graph schema: {e}")


def _create_collection_with_hybrid_vectors(client: QdrantClient) -> None:
    """Create collection with named vectors for hybrid search and optimizations."""

    # Configure named vectors (dense + sparse) with quantization for memory efficiency
    # Binary quantization: 32x memory reduction with minimal accuracy loss
    vectors_config = {
        "dense": models.VectorParams(
            size=get_embedding_dim(),
            distance=models.Distance.COSINE,
            # HNSW optimization for faster search
            hnsw_config=models.HnswConfigDiff(
                m=16,  # Number of edges per node
                ef_construct=100  # Build quality
            ),
            # Binary quantization: 768 bytes -> 24 bytes per vector
            quantization_config=models.ScalarQuantization(
                scalar=models.ScalarQuantizationConfig(
                    type=models.ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True
                )
            )
        )
    }

    # Add sparse vector config if fastembed is available
    sparse_vectors_config = None
    if is_sparse_enabled():
        sparse_vectors_config = {
            "sparse": models.SparseVectorParams(
                modifier=models.Modifier.IDF  # Use IDF weighting for sparse vectors
            )
        }
        logger.info("Sparse vectors enabled for hybrid search")

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=vectors_config,
        sparse_vectors_config=sparse_vectors_config
    )
    logger.info("Collection created with INT8 scalar quantization (4x memory reduction)")

    # Create payload indexes for filtering
    _create_payload_indexes(client)
    logger.info(f"Collection '{COLLECTION_NAME}' created with hybrid vectors")


def _create_payload_indexes(client: QdrantClient) -> None:
    """Create payload indexes for efficient filtering."""
    indexes = [
        ("type", models.PayloadSchemaType.KEYWORD),
        ("project", models.PayloadSchemaType.KEYWORD),
        ("tags", models.PayloadSchemaType.KEYWORD),
        ("resolved", models.PayloadSchemaType.BOOL),
        ("created_at", models.PayloadSchemaType.DATETIME),
        ("memory_tier", models.PayloadSchemaType.KEYWORD),
        ("archived", models.PayloadSchemaType.BOOL),
    ]

    for field_name, field_type in indexes:
        try:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field_name,
                field_schema=field_type
            )
        except Exception as e:
            logger.debug(f"Index {field_name} may already exist: {e}")


def store_memory(data: MemoryCreate, deduplicate: bool = True) -> Memory:
    """Store a new memory with hybrid embeddings and optional deduplication.

    Args:
        data: Memory data to store
        deduplicate: If True, check for duplicates and merge if found

    Returns:
        Memory object (may be existing memory if duplicate found)
    """
    client = get_client()

    # Check for duplicates if enabled
    if deduplicate:
        from .consolidation import find_duplicates, merge_with_existing

        lifecycle = _load_lifecycle_settings()
        duplicates = find_duplicates(client, COLLECTION_NAME, data.content, threshold=lifecycle["dedupThreshold"])
        if duplicates:
            # Found a duplicate - merge instead of creating new
            existing_id = duplicates[0]["id"]
            logger.info(f"Found duplicate (score: {duplicates[0]['score']:.3f}), merging into {existing_id}")

            merge_result = merge_with_existing(client, COLLECTION_NAME, existing_id, data)
            if merge_result:
                # Return the existing memory
                return get_memory(existing_id)

    # Phase 1.3: Session tracking - get conversation context
    session_id = data.session_id
    conversation_context = data.conversation_context
    session_sequence = data.session_sequence

    # If session_id provided, get previous memories for context
    if session_id and not conversation_context:
        try:
            from .session_extraction import SessionManager
            previous_memories = SessionManager.get_session_memories(client, COLLECTION_NAME, session_id)
            conversation_context = SessionManager.extract_conversation_context(previous_memories)
            # Set sequence number
            if session_sequence is None:
                session_sequence = len(previous_memories)
        except Exception as e:
            logger.debug(f"Failed to extract conversation context: {e}")

    # Create memory object
    from .models import ChangeType

    memory = Memory(
        type=data.type,
        content=data.content,
        tags=data.tags,
        project=data.project,
        source=data.source,
        context=data.context,
        error_message=data.error_message,
        stack_trace=data.stack_trace,
        solution=data.solution,
        prevention=data.prevention,
        decision=data.decision,
        rationale=data.rationale,
        alternatives=data.alternatives,
        reversible=data.reversible,
        impact=data.impact,
        resolved=data.solution is not None if data.type == MemoryType.ERROR else False,
        # Session fields
        session_id=session_id,
        conversation_context=conversation_context,
        session_sequence=session_sequence,
        # Temporal fields (Phase 2.2)
        event_time=data.event_time,
        validity_end=data.validity_end,
        **({"validity_start": data.validity_start} if data.validity_start is not None else {})
    )

    # Create initial version snapshot
    memory.create_version_snapshot(
        change_type=ChangeType.CREATED,
        change_reason="Initial memory creation",
        changed_by="system"
    )

    # Generate combined text for embedding
    embed_text_combined = f"{memory.content}"
    if memory.context:
        embed_text_combined += f" {memory.context}"
    if memory.error_message:
        embed_text_combined += f" {memory.error_message}"

    # Generate hybrid embeddings
    embeddings = embed_text(embed_text_combined, include_sparse=is_sparse_enabled())
    memory.embedding = embeddings["dense"]

    # Prepare payload
    payload = memory.model_dump(exclude={"embedding"})
    payload["created_at"] = memory.created_at.isoformat()
    payload["updated_at"] = memory.updated_at.isoformat()

    # Phase 2.2: Set default temporal fields if not provided
    from .temporal import TemporalQuery
    payload = TemporalQuery.set_default_temporal_fields(payload)

    # Prepare vectors
    vectors = {"dense": embeddings["dense"]}
    if "sparse" in embeddings:
        vectors["sparse"] = models.SparseVector(
            indices=embeddings["sparse"]["indices"],
            values=embeddings["sparse"]["values"]
        )

    # Upsert to Qdrant
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=memory.id,
                vector=vectors,
                payload=payload
            )
        ]
    )

    logger.info(f"Stored memory {memory.id} of type {memory.type}")

    # Calculate and store initial quality score (avoid stale default 0.5)
    try:
        from .quality_tracking import QualityScoreCalculator
        QualityScoreCalculator.recalculate_single_memory_quality(
            client, COLLECTION_NAME, str(memory.id)
        )
    except Exception as e:
        logger.warning(f"Initial quality calculation failed for {memory.id}: {e}")

    # Create corresponding node in knowledge graph
    if is_graph_enabled():
        try:
            create_memory_node(
                memory_id=memory.id,
                memory_type=memory.type.value,
                content_preview=memory.content[:200] if memory.content else "",
                project=memory.project,
                tags=memory.tags,
                created_at=memory.created_at
            )
        except Exception as e:
            logger.warning(f"Failed to create graph node for {memory.id}: {e}")

    # Phase 1.2: On-write relationship inference
    # Automatically infer relationships when storing new memories
    try:
        from .relationship_inference import RelationshipInference

        inference_stats = RelationshipInference.infer_on_write(
            memory_id=memory.id,
            memory_type=memory.type.value,
            memory_content=memory.content,
            memory_tags=memory.tags,
            memory_vector=embeddings["dense"],
            created_at=memory.created_at,
            project=memory.project
        )

        if inference_stats and sum(inference_stats.values()) > 0:
            logger.info(f"On-write inference created {sum(inference_stats.values())} relationships: {inference_stats}")
    except Exception as e:
        logger.warning(f"On-write inference failed for {memory.id}: {e}")

    # Auto-supersede: find semantically similar same-type memories and supersede them
    # Threshold: 0.85-0.91 (below dedup at 0.92, above general "related" at 0.75)
    try:
        _auto_supersede(client, memory, embeddings["dense"])
    except Exception as e:
        logger.warning(f"Auto-supersede failed for {memory.id}: {e}")

    # Re-fetch so the returned object has the fresh quality_score
    # (recalc wrote it to Qdrant but the in-memory object still has 0.5)
    return get_memory(memory.id) or memory


def _load_lifecycle_settings() -> dict:
    """Load auto-supersede settings from the settings file, falling back to env vars."""
    import json
    from pathlib import Path

    defaults = {
        "autoSupersedeEnabled": True,
        "autoSupersedeThreshold": float(os.getenv("AUTO_SUPERSEDE_THRESHOLD", "0.85")),
        "autoSupersedeUpper": float(os.getenv("AUTO_SUPERSEDE_UPPER", "0.91")),
        "dedupThreshold": float(os.getenv("DEDUP_THRESHOLD", "0.92")),
        "purgeEnabled": os.getenv("MEMORY_PURGE_ENABLED", "false").lower() == "true",
        "purgeRetentionDays": 90,
        "rerankSkipThreshold": 0.95,
        "onWriteMaxRelationships": 5,
        "followsMaxGapMinutes": 30,
        "cacheThreshold": 0.85,
    }
    try:
        settings_path = Path.home() / ".claude" / "memory" / "data" / "settings.json"
        with open(settings_path, "r") as f:
            saved = json.load(f)
        result = {}
        for key, default_val in defaults.items():
            result[key] = saved.get(key, default_val)
        return result
    except Exception:
        return defaults


def _auto_supersede(
    client: QdrantClient,
    new_memory: Memory,
    dense_vector: list[float],
) -> int:
    """Auto-supersede older same-type memories that are semantically similar but not identical.

    Reads thresholds from dashboard settings (Settings page), falling back to env vars.
    Finds memories with similarity between the lower and upper supersede thresholds.
    Above the upper threshold, deduplication/merge handles it.
    Below the lower threshold, content is too different.

    Only supersedes memories of the same type (e.g., decision supersedes decision).
    Skips auto-captured hook memories to avoid churn.

    Args:
        client: Qdrant client
        new_memory: The newly stored memory
        dense_vector: Dense embedding vector of the new memory

    Returns:
        Number of memories superseded
    """
    lifecycle = _load_lifecycle_settings()

    if not lifecycle["autoSupersedeEnabled"]:
        return 0

    # Skip auto-captured memories (hook-generated context) to avoid session churn
    if new_memory.tags and "auto-captured" in new_memory.tags:
        return 0

    # Build filter: same type, not archived, not self
    filter_conditions = [
        models.FieldCondition(
            key="type",
            match=models.MatchValue(value=new_memory.type.value)
        ),
        models.FieldCondition(
            key="archived",
            match=models.MatchValue(value=False)
        ),
    ]

    # Scope to same project if present
    if new_memory.project:
        filter_conditions.append(
            models.FieldCondition(
                key="project",
                match=models.MatchValue(value=new_memory.project)
            )
        )

    threshold = lifecycle["autoSupersedeThreshold"]
    upper = lifecycle["autoSupersedeUpper"]

    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=dense_vector,
            using="dense",
            query_filter=models.Filter(must=filter_conditions),
            limit=5,
            score_threshold=threshold,
            with_payload=True,
        ).points
    except Exception as e:
        logger.warning(f"Auto-supersede search failed: {e}")
        return 0

    superseded = 0
    for candidate in results:
        cid = str(candidate.id)
        if cid == new_memory.id:
            continue

        # Only supersede within the threshold band (below upper = dedup range)
        if candidate.score >= upper:
            continue

        # Don't supersede pinned memories
        if candidate.payload.get("pinned", False):
            continue

        # Create supersedes relationship: new_memory supersedes candidate
        try:
            link_memories(new_memory.id, cid, RelationType.SUPERSEDES)

            # Archive the superseded memory (quality recalc not needed for archived)
            safe_set_payload(cid, {"archived": True}, recalc_quality=False)

            superseded += 1
            logger.info(
                f"Auto-superseded: {new_memory.id} supersedes {cid} "
                f"(score={candidate.score:.3f}, type={new_memory.type.value})"
            )
        except Exception as e:
            logger.warning(f"Failed to supersede {cid}: {e}")

    if superseded > 0:
        logger.info(f"Auto-supersede: {superseded} older memories archived for {new_memory.id}")

    return superseded


def search_memories(
    query: SearchQuery,
    search_mode: SearchMode = "hybrid",
    use_cache: bool = True,
    use_reranking: bool = True,
    use_graph_expansion: bool = False
) -> list[SearchResult]:
    """
    Search memories using specified search mode with caching and reranking.

    Args:
        query: Search query parameters
        search_mode: "semantic" (dense only), "keyword" (sparse only), or "hybrid" (both with RRF)
        use_cache: Whether to use semantic query cache
        use_reranking: Whether to apply cross-encoder reranking
        use_graph_expansion: Whether to expand results using knowledge graph relationships (Phase 2.1)

    Returns:
        List of SearchResult objects sorted by relevance
    """
    client = get_client()

    # Apply query understanding if enabled
    use_query_understanding = os.getenv("USE_QUERY_UNDERSTANDING", "true").lower() == "true"
    if use_query_understanding:
        routing = route_query(query.query)
        logger.debug(f"Query understanding routing: {routing}")

        # Map strategy to search_mode
        strategy_map = {
            "sparse_only": "keyword",
            "semantic": "semantic",
            "hybrid": "hybrid",
            "graph_expansion": "hybrid"  # Use hybrid for graph expansion (handled separately)
        }
        search_mode = strategy_map.get(routing["strategy"], search_mode)
        use_reranking = routing.get("rerank", use_reranking)

        # Apply time filters if present
        if routing.get("filters") and routing["filters"].get("must"):
            for f in routing["filters"]["must"]:
                if f.get("key") == "created_at" and "range" in f:
                    r = f["range"]
                    if "gte" in r:
                        query.time_range_start = datetime.fromisoformat(r["gte"])
                    if "lte" in r:
                        query.time_range_end = datetime.fromisoformat(r["lte"])

        # Enable graph expansion when query understanding detects relationship intent
        if routing["strategy"] == "graph_expansion":
            use_graph_expansion = True

    # Generate query embeddings
    use_sparse = search_mode in ("keyword", "hybrid") and is_sparse_enabled()
    query_embeddings = embed_query(query.query, include_sparse=use_sparse)

    # Check cache first (if enabled and no filters that would change results)
    if use_cache and not query.type and not query.tags and not query.project:
        cached_results = check_cache(client, query_embeddings["dense"])
        if cached_results:
            logger.debug(f"Cache hit for query: {query.query[:50]}")
            # Convert cached dicts back to SearchResult objects
            search_results = []
            for cached in cached_results[:query.limit]:
                # Reconstruct minimal memory object from cache
                memory = Memory(
                    id=cached.get("id", ""),
                    content=cached.get("content", ""),
                    type=MemoryType(cached.get("type", "context")),
                    tags=cached.get("tags", [])
                )
                score = cached.get("rerank_score") or cached.get("score", 0.0)
                search_results.append(SearchResult(
                    memory=memory,
                    score=score,
                    memory_strength=cached.get("memory_strength")
                ))
            return search_results

    # Build filter conditions
    query_filter = _build_filter(query)

    # Retrieve more candidates for reranking (50 instead of limit)
    candidate_limit = 50 if use_reranking and is_reranker_enabled() else query.limit

    # Execute search based on mode
    if search_mode == "hybrid" and is_sparse_enabled():
        results = _hybrid_search(
            client, query_embeddings, query_filter, candidate_limit, query.min_score, query.query
        )
    elif search_mode == "keyword" and is_sparse_enabled():
        results = _sparse_search(
            client, query_embeddings, query_filter, candidate_limit, query.min_score
        )
    else:
        # Default to dense semantic search
        results = _dense_search(
            client, query_embeddings, query_filter, candidate_limit, query.min_score
        )

    # Convert to SearchResult objects
    search_results = []
    for result in results:
        memory = _point_to_memory(result)
        search_results.append(SearchResult(
            memory=memory,
            score=result.score,
            memory_strength=memory.memory_strength
        ))

    # Apply cross-encoder reranking if enabled (skip if top result is already high confidence)
    top_score = max(r.score for r in search_results) if search_results else 0
    if use_reranking and is_reranker_enabled() and len(search_results) > 0 and top_score < 0.95:
        logger.debug(f"Reranking {len(search_results)} candidates")
        search_results = rerank_search_results(query.query, search_results, top_k=query.limit)
    else:
        search_results = search_results[:query.limit]

    # Phase 2.1: Apply graph-based search expansion if enabled
    if use_graph_expansion and is_graph_enabled() and len(search_results) > 0:
        logger.debug(f"Expanding {len(search_results)} results using knowledge graph")
        search_results = expand_search_with_graph(
            initial_results=search_results,
            use_expansion=True,
            max_hops=1,  # 1-hop expansion by default
            expansion_factor=0.6,  # Dampen expanded results to 60% of original score
            top_k=query.limit  # Return same number of results
        )

    # Store in cache (only if no filters)
    if use_cache and search_results and not query.type and not query.tags and not query.project:
        cache_data = [
            {
                "id": r.memory.id,
                "content": r.memory.content,
                "type": r.memory.type.value if r.memory.type else "context",
                "score": r.score,
                "rerank_score": r.composite_score,
                "tags": r.memory.tags,
                "memory_strength": r.memory_strength
            }
            for r in search_results
        ]
        store_cache(client, query_embeddings["dense"], query.query, cache_data)

    # Track access and reinforce strength for top results
    for result in search_results[:5]:
        track_access(result.memory.id)

    # Phase 1.2: Track co-access for relationship inference
    # Memories accessed together in search results may be related
    if len(search_results) >= 2:
        try:
            from .relationship_inference import RelationshipInference
            memory_ids = [r.memory.id for r in search_results[:5]]  # Track top 5 results
            RelationshipInference.track_co_access(memory_ids)
        except Exception as e:
            logger.debug(f"Co-access tracking failed: {e}")

    return search_results


def _hybrid_search(
    client: QdrantClient,
    query_embeddings: dict,
    query_filter: Optional[models.Filter],
    limit: int,
    min_score: float,
    query_text: Optional[str] = None
) -> list:
    """Execute hybrid search using RRF or learned fusion.

    Uses learned fusion weights if USE_LEARNED_FUSION=true env var is set,
    otherwise uses Qdrant's built-in RRF fusion.
    """
    use_learned_fusion = os.getenv("USE_LEARNED_FUSION", "false").lower() == "true"

    if use_learned_fusion and query_text and "sparse" in query_embeddings:
        logger.debug("Using learned fusion weights")
        return _hybrid_search_learned(
            client, query_embeddings, query_filter, limit, min_score, query_text
        )

    # Default: use Qdrant's RRF fusion
    # Use Qdrant's query API with prefetch for hybrid search
    prefetch = [
        # Dense vector search
        models.Prefetch(
            query=query_embeddings["dense"],
            using="dense",
            limit=limit * 2,  # Fetch more for fusion
            filter=query_filter
        )
    ]

    # Add sparse prefetch if available
    if "sparse" in query_embeddings:
        prefetch.append(
            models.Prefetch(
                query=models.SparseVector(
                    indices=query_embeddings["sparse"]["indices"],
                    values=query_embeddings["sparse"]["values"]
                ),
                using="sparse",
                limit=limit * 2,
                filter=query_filter
            )
        )

    # Execute hybrid query with RRF fusion
    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            prefetch=prefetch,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            score_threshold=min_score
        ).points
    except Exception as e:
        logger.warning(f"Hybrid search failed, falling back to dense: {e}")
        results = _dense_search(client, query_embeddings, query_filter, limit, min_score)

    return results


def _hybrid_search_learned(
    client: QdrantClient,
    query_embeddings: dict,
    query_filter: Optional[models.Filter],
    limit: int,
    min_score: float,
    query_text: str
) -> list:
    """Execute hybrid search using learned fusion weights."""

    # Fetch dense results
    dense_results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embeddings["dense"],
        using="dense",
        limit=limit * 2,
        filter=query_filter,
        with_payload=True
    ).points

    # Fetch sparse results
    sparse_results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=models.SparseVector(
            indices=query_embeddings["sparse"]["indices"],
            values=query_embeddings["sparse"]["values"]
        ),
        using="sparse",
        limit=limit * 2,
        filter=query_filter,
        with_payload=True
    ).points

    # Convert to (id, score) tuples
    dense_scores = [(str(r.id), r.score) for r in dense_results]
    sparse_scores = [(str(r.id), r.score) for r in sparse_results]

    # Apply learned fusion
    fused_scores = apply_learned_fusion(query_text, dense_scores, sparse_scores)

    # Create a map of all points by ID
    all_points = {str(r.id): r for r in dense_results + sparse_results}

    # Reconstruct points with fused scores
    fused_results = []
    for point_id, fused_score in fused_scores[:limit]:
        if fused_score >= min_score and point_id in all_points:
            point = all_points[point_id]
            # Update score with fused score
            point.score = fused_score
            fused_results.append(point)

    logger.debug(f"Learned fusion: {len(fused_results)} results after fusion")
    return fused_results


def _dense_search(
    client: QdrantClient,
    query_embeddings: dict,
    query_filter: Optional[models.Filter],
    limit: int,
    min_score: float
) -> list:
    """Execute dense-only semantic search."""
    try:
        # Try named vector search first
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embeddings["dense"],
            using="dense",
            query_filter=query_filter,
            limit=limit,
            score_threshold=min_score
        ).points
    except Exception:
        # Fallback for collections without named vectors
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embeddings["dense"],
            query_filter=query_filter,
            limit=limit,
            score_threshold=min_score
        ).points

    return results


def _sparse_search(
    client: QdrantClient,
    query_embeddings: dict,
    query_filter: Optional[models.Filter],
    limit: int,
    min_score: float
) -> list:
    """Execute sparse-only keyword search."""
    if "sparse" not in query_embeddings:
        logger.warning("Sparse embeddings not available, falling back to dense")
        return _dense_search(client, query_embeddings, query_filter, limit, min_score)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=models.SparseVector(
            indices=query_embeddings["sparse"]["indices"],
            values=query_embeddings["sparse"]["values"]
        ),
        using="sparse",
        query_filter=query_filter,
        limit=limit,
        score_threshold=min_score
    ).points

    return results


def _build_filter(query: SearchQuery) -> Optional[models.Filter]:
    """Build Qdrant filter from search query."""
    filter_conditions = []

    if query.type:
        filter_conditions.append(
            models.FieldCondition(
                key="type",
                match=models.MatchValue(value=query.type.value)
            )
        )

    if query.project:
        filter_conditions.append(
            models.FieldCondition(
                key="project",
                match=models.MatchValue(value=query.project)
            )
        )

    if query.tags:
        filter_conditions.append(
            models.FieldCondition(
                key="tags",
                match=models.MatchAny(any=query.tags)
            )
        )

    # Temporal range filters (uses DatetimeRange, NOT Range — Range is for numeric fields only)
    if query.time_range_start:
        filter_conditions.append(
            models.FieldCondition(
                key="created_at",
                range=models.DatetimeRange(gte=query.time_range_start)
            )
        )
    if query.time_range_end:
        filter_conditions.append(
            models.FieldCondition(
                key="created_at",
                range=models.DatetimeRange(lte=query.time_range_end)
            )
        )

    # Build filter with optional archived exclusion
    if not query.include_archived:
        # Use must_not to exclude archived=True
        # This allows memories without the archived field to still match
        return models.Filter(
            must=filter_conditions if filter_conditions else None,
            must_not=[
                models.FieldCondition(
                    key="archived",
                    match=models.MatchValue(value=True)
                )
            ]
        )

    return models.Filter(must=filter_conditions) if filter_conditions else None


def _point_to_memory(point) -> Memory:
    """Convert a Qdrant point to a Memory object."""
    payload = dict(point.payload)

    # Parse datetime strings
    if "created_at" in payload and isinstance(payload["created_at"], str):
        payload["created_at"] = datetime.fromisoformat(payload["created_at"])
    if "updated_at" in payload and isinstance(payload["updated_at"], str):
        payload["updated_at"] = datetime.fromisoformat(payload["updated_at"])

    # Fix legacy MongoDB-style values
    if "access_count" in payload and isinstance(payload["access_count"], dict):
        payload["access_count"] = 0
    if "usefulness_score" in payload and isinstance(payload["usefulness_score"], dict):
        payload["usefulness_score"] = 0.5

    # Remove id from payload (we set it separately)
    payload.pop("id", None)

    return Memory(id=str(point.id), **payload)


def get_memory(memory_id: str) -> Optional[Memory]:
    """Get a single memory by ID."""
    client = get_client()

    results = client.retrieve(
        collection_name=COLLECTION_NAME,
        ids=[memory_id]
    )

    if not results:
        return None

    return _point_to_memory(results[0])


def _post_update_pipeline(memory_id: str, update_data: dict) -> None:
    """Run post-update enrichment and quality recalculation.

    If content/solution/rationale changed, auto-derive missing fields.
    Always recalculates quality score so it stays fresh.
    """
    from .enhancements import _derive_prevention, _derive_rationale, _derive_context, _derive_alternatives
    from .quality_tracking import QualityScoreCalculator

    client = get_client()
    enriched_fields = {}

    # Only auto-derive if substantive fields changed
    trigger_fields = {"content", "solution", "rationale", "error_message", "context", "prevention"}
    if trigger_fields & set(update_data.keys()):
        # Fetch current state
        memory = get_memory(memory_id)
        if memory:
            # Derive prevention from solution if missing
            if not memory.prevention and memory.solution:
                derived = _derive_prevention(memory.content, memory.solution)
                if derived:
                    enriched_fields["prevention"] = derived

            # Derive rationale from content if missing (for decisions)
            if not memory.rationale and memory.type and memory.type.value == "decision":
                derived = _derive_rationale(memory.content)
                if derived:
                    enriched_fields["rationale"] = derived

            # Derive alternatives from content if missing (for decisions)
            if not memory.alternatives and memory.type and memory.type.value == "decision":
                derived = _derive_alternatives(memory.content)
                if derived:
                    enriched_fields["alternatives"] = derived

            # Derive context if missing
            if not memory.context:
                derived = _derive_context(memory.content, memory.project, memory.type)
                if derived:
                    enriched_fields["context"] = derived

    # Write enriched fields if any
    if enriched_fields:
        try:
            client.set_payload(
                collection_name=COLLECTION_NAME,
                payload=enriched_fields,
                points=[memory_id],
            )
            logger.info(f"Post-update enriched {memory_id}: {list(enriched_fields.keys())}")
        except Exception as e:
            logger.warning(f"Post-update enrichment failed for {memory_id}: {e}")

    # Always recalculate quality score
    try:
        result = QualityScoreCalculator.recalculate_single_memory_quality(
            client, COLLECTION_NAME, memory_id
        )
        if result:
            score, _ = result
            logger.info(f"Post-update quality recalculated for {memory_id}: {score}")
    except Exception as e:
        logger.warning(f"Post-update quality recalc failed for {memory_id}: {e}")


def update_memory(memory_id: str, update: MemoryUpdate) -> Optional[Memory]:
    """Update an existing memory."""
    from .models import ChangeType

    client = get_client()

    memory = get_memory(memory_id)
    if not memory:
        return None

    # Create version snapshot before updating
    memory.create_version_snapshot(
        change_type=ChangeType.EDITED,
        change_reason="Memory updated via API",
        changed_by="user"
    )

    # Apply updates
    update_data = update.model_dump(exclude_unset=True)

    # Clean content, tags, and type-specific fields (same as store_memory pipeline)
    from .enhancements import clean_content, normalize_tags
    if "content" in update_data and update_data["content"]:
        update_data["content"] = clean_content(update_data["content"])
    if "tags" in update_data and update_data["tags"]:
        update_data["tags"] = normalize_tags(update_data["tags"])
    for field in ("solution", "prevention", "rationale", "decision", "context", "error_message"):
        if field in update_data and update_data[field] and isinstance(update_data[field], str):
            update_data[field] = clean_content(update_data[field])

    # Validate type-specific required fields if type is being changed
    if "type" in update_data:
        new_type = update_data["type"]
        # Merge existing memory fields with update to check completeness
        merged = {**memory.model_dump(), **update_data}
        if new_type == "error" or (hasattr(new_type, 'value') and new_type.value == "error"):
            missing = []
            if not merged.get("error_message"):
                missing.append("error_message")
            if not merged.get("solution"):
                missing.append("solution")
            if not merged.get("prevention"):
                missing.append("prevention")
            if missing:
                raise ValueError(
                    f"Changing type to 'error' requires: {', '.join(missing)}. "
                    f"Include them in the PATCH or set them first."
                )
        elif new_type == "decision" or (hasattr(new_type, 'value') and new_type.value == "decision"):
            if not merged.get("rationale"):
                raise ValueError(
                    "Changing type to 'decision' requires 'rationale'. "
                    "Include it in the PATCH or set it first."
                )

    for key, value in update_data.items():
        setattr(memory, key, value)

    memory.updated_at = datetime.now(timezone.utc)

    # Re-embed if content or context changed (both feed the embedding)
    if "content" in update_data or "context" in update_data:
        embed_text_combined = f"{memory.content}"
        if memory.context:
            embed_text_combined += f" {memory.context}"
        embeddings = embed_text(embed_text_combined, include_sparse=is_sparse_enabled())
        memory.embedding = embeddings["dense"]

        # Prepare vectors
        vectors = {"dense": embeddings["dense"]}
        if "sparse" in embeddings:
            vectors["sparse"] = models.SparseVector(
                indices=embeddings["sparse"]["indices"],
                values=embeddings["sparse"]["values"]
            )
    else:
        # Use existing embedding
        vectors = {"dense": memory.embedding or embed_text_legacy(memory.content)}

    # Prepare payload
    payload = memory.model_dump(exclude={"embedding"})
    payload["created_at"] = memory.created_at.isoformat()
    payload["updated_at"] = memory.updated_at.isoformat()

    # Update in Qdrant
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=memory_id,
                vector=vectors,
                payload=payload
            )
        ]
    )

    # Post-update pipeline: auto-derive missing fields + recalculate quality
    _post_update_pipeline(memory_id, update_data)

    return memory


def delete_memory(memory_id: str) -> bool:
    """Delete a memory by ID."""
    client = get_client()

    # Clean up Neo4j graph node before deleting from Qdrant
    if is_graph_enabled():
        try:
            delete_memory_node(memory_id)
        except Exception as e:
            logger.warning(f"Failed to delete graph node {memory_id}: {e}")

    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.PointIdsList(points=[memory_id])
    )

    logger.info(f"Deleted memory {memory_id}")
    return True


def archive_memory(memory_id: str) -> Optional[Memory]:
    """Soft-delete a memory by marking it as archived."""
    return update_memory(memory_id, MemoryUpdate(archived=True))


def mark_resolved(memory_id: str, solution: str) -> Optional[Memory]:
    """Mark an error memory as resolved with a solution.

    Auto-derives prevention from solution if the memory doesn't already have one.
    Quality score is recalculated via the post-update pipeline in update_memory().
    """
    # Validate solution is non-empty and meaningful
    if not solution or not solution.strip():
        raise ValueError("Solution cannot be empty")
    if len(solution.strip()) < 15:
        raise ValueError("Solution too brief — explain the actual fix (min 15 chars)")

    # Check if memory already has prevention
    memory = get_memory(memory_id)
    if not memory:
        return None

    update_fields = {
        "solution": solution,
        "resolved": True,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }

    # Auto-derive prevention if missing
    if not memory.prevention:
        from .enhancements import _derive_prevention
        derived = _derive_prevention(memory.content, solution)
        if derived:
            update_fields["prevention"] = derived
            logger.info(f"Auto-derived prevention for {memory_id}: {derived[:60]}...")

    return update_memory(memory_id, MemoryUpdate(**update_fields))


def link_memories(source_id: str, target_id: str, relation_type: RelationType) -> bool:
    """Create a relationship between two memories."""
    memory = get_memory(source_id)
    if not memory:
        return False

    relation = Relation(target_id=target_id, relation_type=relation_type)
    if relation not in memory.relations:
        memory.relations.append(relation)
        # Write relations directly to Qdrant payload (MemoryUpdate doesn't include relations)
        relations_payload = [r.model_dump() for r in memory.relations]
        # Serialize datetime fields to ISO strings
        for r in relations_payload:
            if hasattr(r.get("created_at", ""), "isoformat"):
                r["created_at"] = r["created_at"].isoformat()
        # Use safe_set_payload — auto-recalcs quality for source memory
        safe_set_payload(source_id, {"relations": relations_payload})

    # Also create relationship in knowledge graph
    if is_graph_enabled():
        try:
            # Convert relation type to graph format (uppercase)
            graph_rel_type = relation_type.value.upper()
            create_relationship(source_id, target_id, graph_rel_type)
        except Exception as e:
            logger.warning(f"Failed to create graph relationship: {e}")

    # Recalculate quality for TARGET memory too (it gained an inbound relationship)
    try:
        from .quality_tracking import QualityScoreCalculator
        client = get_client()
        QualityScoreCalculator.recalculate_single_memory_quality(
            client, COLLECTION_NAME, target_id
        )
    except Exception as e:
        logger.warning(f"Quality recalc after link failed for target {target_id}: {e}")

    return True


def get_context(
    project: Optional[str] = None,
    hours: int = 24,
    types: Optional[list[MemoryType]] = None,
    include_documents: bool = True,
    document_limit: int = 5
) -> dict:
    """Get relevant context memories and documents for a project.

    Args:
        project: Optional project name to filter by
        hours: Hours to look back (default: 24)
        types: Optional memory types to filter
        include_documents: Whether to include relevant documents (default: True)
        document_limit: Maximum number of documents to return (default: 5)

    Returns:
        Dict with keys: memories (list[Memory]), documents (list[dict]),
        combined_count (int), has_documents (bool)
    """
    client = get_client()

    time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Build filter conditions (excluding time filter which needs client-side handling)
    filter_conditions = [
        models.FieldCondition(
            key="archived",
            match=models.MatchValue(value=False)
        )
    ]

    if project:
        filter_conditions.append(
            models.FieldCondition(
                key="project",
                match=models.MatchValue(value=project)
            )
        )

    if types:
        filter_conditions.append(
            models.FieldCondition(
                key="type",
                match=models.MatchAny(any=[t.value for t in types])
            )
        )

    results, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=models.Filter(must=filter_conditions),
        limit=200,  # Get more to filter client-side
        with_payload=True
    )

    # Convert to memories and filter by time client-side
    memories = [_point_to_memory(r) for r in results]

    # Filter by time threshold
    filtered = []
    for m in memories:
        created = m.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created >= time_threshold:
            filtered.append(m)

    memories = filtered[:50]  # Limit to 50

    # Search for relevant documents if requested
    documents = []
    if include_documents and project:
        # Build a context query from the recent memory content
        context_query = f"{project} " + " ".join([m.content[:50] for m in memories[:3]])

        try:
            from . import documents as doc_module
            doc_results = doc_module.search_documents(
                query=context_query,
                limit=document_limit,
                folder=project
            )
            documents = doc_results
        except Exception as e:
            logger.warning(f"Failed to fetch documents for context: {e}")
            documents = []

    return {
        "memories": memories,
        "documents": documents,
        "combined_count": len(memories) + len(documents),
        "has_documents": len(documents) > 0
    }


def get_stats() -> dict:
    """Get collection statistics.

    Uses a single scroll instead of 10 individual count/scroll calls.
    """
    client = get_client()

    collection_info = client.get_collection(COLLECTION_NAME)
    total = collection_info.points_count

    # Single scroll with minimal payload instead of 8 count() calls + 1 scroll
    all_points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=5000,
        with_payload=["type", "archived", "resolved", "project"],
        with_vectors=False
    )

    by_type = {}
    by_project = {}
    archived_count = 0
    unresolved_count = 0

    for p in all_points:
        payload = p.payload or {}
        is_archived = payload.get("archived", False)

        if is_archived:
            archived_count += 1
            continue

        # Count by type (only active memories)
        mem_type = payload.get("type")
        if mem_type:
            by_type[mem_type] = by_type.get(mem_type, 0) + 1

        # Count by project (only active memories)
        proj = payload.get("project")
        if proj:
            by_project[proj] = by_project.get(proj, 0) + 1

        # Count unresolved errors (only active memories)
        if mem_type == "error" and not payload.get("resolved", False):
            unresolved_count += 1

    return {
        "total_memories": total,
        "active_memories": total - archived_count,
        "archived_memories": archived_count,
        "by_type": by_type,
        "by_project": by_project,
        "unresolved_errors": unresolved_count,
        "hybrid_search_enabled": is_sparse_enabled(),
        "embedding_dim": get_embedding_dim()
    }


def _increment_access_count(memory_id: str) -> None:
    """Increment the access count for a memory."""
    try:
        memory = get_memory(memory_id)
        if memory:
            new_count = (memory.access_count or 0) + 1
            # Skip quality recalc for simple access increment (high-frequency operation)
            safe_set_payload(memory_id, {"access_count": new_count}, recalc_quality=False)
    except Exception as e:
        logger.debug(f"Failed to increment access count: {e}")


def check_health() -> tuple[bool, str]:
    """Check Qdrant connection health."""
    try:
        client = get_client()
        client.get_collections()
        return True, "connected"
    except Exception as e:
        return False, str(e)


def migrate_collection() -> dict:
    """
    Migrate existing collection to new vector format.
    Creates new collection, re-embeds all memories, then swaps.
    """
    global COLLECTION_NAME  # Declare at start of function

    client = get_client()
    old_collection_name = COLLECTION_NAME
    new_collection_name = f"{COLLECTION_NAME}_v2"

    logger.info("Starting collection migration...")

    # Get all existing memories
    all_memories = []
    scroll_offset = None
    while True:
        results, scroll_offset = client.scroll(
            collection_name=old_collection_name,
            limit=100,
            offset=scroll_offset,
            with_payload=True,
            with_vectors=False
        )
        all_memories.extend(results)
        if scroll_offset is None:
            break

    logger.info(f"Found {len(all_memories)} memories to migrate")

    # Create new collection with hybrid vectors
    try:
        client.delete_collection(new_collection_name)
    except Exception:
        pass

    # Temporarily change global collection name to create new one
    COLLECTION_NAME = new_collection_name
    _create_collection_with_hybrid_vectors(client)

    # Re-embed and store each memory
    migrated = 0
    for point in all_memories:
        payload = dict(point.payload)
        try:
            # Build embed text
            embed_text_combined = payload.get("content", "")
            if payload.get("context"):
                embed_text_combined += f" {payload['context']}"
            if payload.get("error_message"):
                embed_text_combined += f" {payload['error_message']}"

            # Generate new embeddings
            embeddings = embed_text(embed_text_combined, include_sparse=is_sparse_enabled())

            # Prepare vectors
            vectors = {"dense": embeddings["dense"]}
            if "sparse" in embeddings:
                vectors["sparse"] = models.SparseVector(
                    indices=embeddings["sparse"]["indices"],
                    values=embeddings["sparse"]["values"]
                )

            # Store in new collection
            client.upsert(
                collection_name=new_collection_name,
                points=[
                    models.PointStruct(
                        id=str(point.id),
                        vector=vectors,
                        payload=payload
                    )
                ]
            )
            migrated += 1
        except Exception as e:
            logger.error(f"Failed to migrate memory {point.id}: {e}")

    # Restore original collection name
    COLLECTION_NAME = old_collection_name
    try:
        client.delete_collection(f"{old_collection_name}_backup")
    except Exception:
        pass

    # Rename old to backup, new to main
    # Note: Qdrant doesn't have native rename, so we use aliases
    try:
        client.update_collection_aliases(
            change_aliases_operations=[
                models.CreateAliasOperation(
                    create_alias=models.CreateAlias(
                        collection_name=new_collection_name,
                        alias_name=old_collection_name
                    )
                )
            ]
        )
    except Exception as e:
        logger.warning(f"Alias swap failed: {e}. Manual intervention may be needed.")

    logger.info(f"Migration complete: {migrated}/{len(all_memories)} memories migrated")

    return {
        "total": len(all_memories),
        "migrated": migrated,
        "failed": len(all_memories) - migrated,
        "new_embedding_dim": get_embedding_dim(),
        "hybrid_search_enabled": is_sparse_enabled()
    }


# ============================================================================
# Access Tracking & Importance Decay
# ============================================================================

def track_access(memory_id: str) -> bool:
    """
    Update access tracking for a memory.
    Increments access_count, updates last_accessed timestamp,
    and reinforces memory strength to prevent decay.
    """
    client = get_client()

    try:
        results = client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[memory_id],
            with_payload=True
        )

        if not results:
            return False

        current_access_count = results[0].payload.get("access_count", 0)

        # Skip quality recalc for access tracking (high-frequency, batched by scheduler)
        safe_set_payload(
            memory_id,
            {
                "access_count": current_access_count + 1,
                "last_accessed": datetime.now(timezone.utc).isoformat()
            },
            recalc_quality=False,
        )

        # Reinforce memory strength on access to prevent monotonic decay
        try:
            from .forgetting import reinforce_memory
            reinforce_memory(client, COLLECTION_NAME, memory_id, boost_amount=0.1)
        except Exception as e:
            logger.debug(f"Memory reinforcement failed for {memory_id}: {e}")

        logger.debug(f"Tracked access for memory {memory_id}, count: {current_access_count + 1}")
        return True

    except Exception as e:
        logger.warning(f"Failed to track access for {memory_id}: {e}")
        return False


def calculate_decay_score(memory: Memory, decay_rate: float = 0.1) -> float:
    """
    Calculate importance with time decay.

    Formula: effective_importance = base_importance * decay_factor + access_boost
    - decay_factor = exp(-decay_rate * weeks_old)
    - access_boost = min(access_count * 0.05, 0.3)

    Pinned memories always return 1.0 (no decay).
    """
    import math

    # Pinned memories never decay
    if getattr(memory, 'pinned', False):
        return 1.0

    base_importance = memory.calculate_importance()

    now = datetime.now(timezone.utc)
    created_at = memory.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    weeks_old = (now - created_at).total_seconds() / (7 * 24 * 3600)
    decay_factor = math.exp(-decay_rate * weeks_old)

    access_boost = min(memory.access_count * 0.05, 0.3)

    last_accessed = memory.last_accessed
    if last_accessed.tzinfo is None:
        last_accessed = last_accessed.replace(tzinfo=timezone.utc)

    days_since_access = (now - last_accessed).total_seconds() / (24 * 3600)
    recency_boost = 0.2 * math.exp(-0.1 * days_since_access) if days_since_access < 30 else 0

    effective_importance = (base_importance * decay_factor) + access_boost + recency_boost

    return min(max(effective_importance, 0.0), 1.0)


# ============================================================================
# Proactive Memory Surfacing
# ============================================================================

def suggest_memories(
    project: Optional[str] = None,
    keywords: Optional[list[str]] = None,
    current_files: Optional[list[str]] = None,
    git_branch: Optional[str] = None,
    limit: int = 5
) -> list[dict]:
    """
    Proactively suggest relevant memories based on current context.
    Called at conversation start to surface useful memories.
    """
    client = get_client()
    suggestions = []
    seen_ids = set()

    # Build context string for semantic search
    context_parts = []
    if project:
        context_parts.append(f"project: {project}")
    if keywords:
        context_parts.append(f"topics: {' '.join(keywords)}")
    if current_files:
        extensions = set()
        for f in current_files[:5]:
            if '.' in f:
                extensions.add(f.split('.')[-1])
        if extensions:
            context_parts.append(f"technologies: {' '.join(extensions)}")
    if git_branch:
        context_parts.append(f"branch: {git_branch}")

    context_query = " ".join(context_parts) if context_parts else "general development context"

    # 1. Search for semantically relevant memories
    if context_query:
        try:
            query_embeddings = embed_query(context_query)

            filter_conditions = [
                models.FieldCondition(
                    key="archived",
                    match=models.MatchValue(value=False)
                )
            ]

            if project:
                filter_conditions.append(
                    models.FieldCondition(
                        key="project",
                        match=models.MatchAny(any=[project, None, ""])
                    )
                )

            results = client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_embeddings["dense"],
                query_filter=models.Filter(must=filter_conditions),
                limit=limit * 2,
                with_payload=True
            ).points

            for point in results:
                if str(point.id) not in seen_ids:
                    memory = _point_to_memory(point)
                    decay_score = calculate_decay_score(memory)

                    if decay_score > 0.3:
                        suggestions.append({
                            "memory": memory,
                            "relevance_score": point.score,
                            "decay_score": decay_score,
                            "combined_score": (point.score * 0.6) + (decay_score * 0.4),
                            "reason": _generate_suggestion_reason(memory, context_query)
                        })
                        seen_ids.add(str(point.id))
                        track_access(str(point.id))

        except Exception as e:
            logger.warning(f"Semantic suggestion search failed: {e}")

    # 2. Add recently unresolved errors for the project
    if project:
        try:
            unresolved = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=models.Filter(must=[
                    models.FieldCondition(key="type", match=models.MatchValue(value="error")),
                    models.FieldCondition(key="resolved", match=models.MatchValue(value=False)),
                    models.FieldCondition(key="archived", match=models.MatchValue(value=False)),
                    models.FieldCondition(key="project", match=models.MatchValue(value=project))
                ]),
                limit=3,
                with_payload=True
            )[0]

            for point in unresolved:
                if str(point.id) not in seen_ids:
                    memory = _point_to_memory(point)
                    suggestions.append({
                        "memory": memory,
                        "relevance_score": 0.9,
                        "decay_score": calculate_decay_score(memory),
                        "combined_score": 0.95,
                        "reason": "⚠️ Unresolved error in this project"
                    })
                    seen_ids.add(str(point.id))

        except Exception as e:
            logger.warning(f"Unresolved error search failed: {e}")

    # 3. Add high-importance patterns and decisions
    try:
        important = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(must=[
                models.FieldCondition(key="archived", match=models.MatchValue(value=False)),
                models.FieldCondition(
                    key="type",
                    match=models.MatchAny(any=["pattern", "decision"])
                ),
                models.FieldCondition(
                    key="access_count",
                    range=models.Range(gte=3)
                )
            ]),
            limit=5,
            with_payload=True
        )[0]

        for point in important:
            if str(point.id) not in seen_ids:
                memory = _point_to_memory(point)
                decay_score = calculate_decay_score(memory)

                if decay_score > 0.4:
                    suggestions.append({
                        "memory": memory,
                        "relevance_score": 0.7,
                        "decay_score": decay_score,
                        "combined_score": 0.7 + (decay_score * 0.2),
                        "reason": f"📌 Frequently used {memory.type.value}"
                    })
                    seen_ids.add(str(point.id))

    except Exception as e:
        logger.warning(f"Important memory search failed: {e}")

    suggestions.sort(key=lambda x: x["combined_score"], reverse=True)
    return suggestions[:limit]


def _generate_suggestion_reason(memory: Memory, context: str) -> str:
    """Generate a human-readable reason for why this memory was suggested."""
    type_reasons = {
        MemoryType.ERROR: "🔴 Related error you encountered",
        MemoryType.PATTERN: "📋 Useful pattern for this context",
        MemoryType.DECISION: "🎯 Relevant architecture decision",
        MemoryType.DOCS: "📖 Documentation you saved",
        MemoryType.LEARNING: "💡 Learning that might help",
        MemoryType.CONTEXT: "📍 Context about this area",
    }

    base_reason = type_reasons.get(memory.type, "Related memory")

    if memory.tags:
        matching_tags = [t for t in memory.tags if t.lower() in context.lower()]
        if matching_tags:
            base_reason += f" (tags: {', '.join(matching_tags[:3])})"

    return base_reason


def get_memory_with_tracking(memory_id: str) -> Optional[Memory]:
    """Get a memory and track the access."""
    memory = get_memory(memory_id)
    if memory:
        track_access(memory_id)
    return memory
