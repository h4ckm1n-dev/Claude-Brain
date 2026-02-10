"""Memory consolidation engine for intelligent memory lifecycle management.

Provides:
- Similarity-based clustering of related memories
- Automatic consolidation of episodic -> semantic tier
- Deduplication on store
- Archive/cleanup of low-value memories
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict

from qdrant_client import QdrantClient
from qdrant_client.http import models

from .models import (
    Memory, MemoryCreate, MemoryType, MemoryTier,
    ConsolidationCluster, ArchiveResult
)
from .embeddings import embed_text, get_embedding_dim

logger = logging.getLogger(__name__)

# Consolidation configuration
SIMILARITY_THRESHOLD = 0.85  # Cosine similarity for clustering
DEDUP_THRESHOLD = 0.92  # Higher threshold for deduplication
MIN_CLUSTER_SIZE = 3  # Minimum memories to form a cluster
ARCHIVE_AGE_DAYS = 7  # Archive memories older than this
MIN_ACCESS_COUNT = 2  # Don't archive if accessed more than this


def find_duplicates(
    client: QdrantClient,
    collection_name: str,
    content: str,
    threshold: float = DEDUP_THRESHOLD
) -> list[dict]:
    """
    Find existing memories similar to the given content.

    Args:
        client: Qdrant client
        collection_name: Collection to search
        content: Content to check for duplicates
        threshold: Similarity threshold (default 0.92)

    Returns:
        List of similar memories with scores
    """
    try:
        # Generate embedding for content
        embeddings = embed_text(content, include_sparse=False)

        # Search for similar memories
        results = client.query_points(
            collection_name=collection_name,
            query=embeddings["dense"],
            using="dense",
            limit=5,
            score_threshold=threshold,
            with_payload=True
        ).points

        duplicates = []
        for result in results:
            duplicates.append({
                "id": str(result.id),
                "score": result.score,
                "content": result.payload.get("content", ""),
                "type": result.payload.get("type"),
                "tags": result.payload.get("tags", [])
            })

        return duplicates

    except Exception as e:
        logger.error(f"Duplicate search failed: {e}")
        return []


def merge_with_existing(
    client: QdrantClient,
    collection_name: str,
    existing_id: str,
    new_memory: MemoryCreate
) -> Optional[str]:
    """
    Merge new memory data with existing duplicate.

    Args:
        client: Qdrant client
        collection_name: Collection name
        existing_id: ID of existing memory to merge into
        new_memory: New memory data to merge

    Returns:
        ID of merged memory, or None on failure
    """
    try:
        # Get existing memory
        results = client.retrieve(
            collection_name=collection_name,
            ids=[existing_id],
            with_payload=True
        )

        if not results:
            return None

        existing = results[0].payload

        # Merge tags (union + normalize)
        from .enhancements import normalize_tags
        merged_tags = normalize_tags(list(set(existing.get("tags", []) + new_memory.tags)))

        # Increment access count
        access_count = existing.get("access_count", 0)
        if isinstance(access_count, dict):
            access_count = 0
        access_count += 1

        # Update payload — safe_set_payload auto-recalcs quality (tags affect scoring)
        from .collections import safe_set_payload
        safe_set_payload(
            existing_id,
            {
                "tags": merged_tags,
                "access_count": access_count,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            collection_name=collection_name,
        )

        # Recalculate quality score (tags and access_count changed)
        try:
            from .quality_tracking import QualityScoreCalculator
            QualityScoreCalculator.recalculate_single_memory_quality(
                client, collection_name, existing_id
            )
        except Exception as e:
            logger.warning(f"Quality recalc failed for merged {existing_id}: {e}")

        logger.info(f"Merged new memory into existing {existing_id}")
        return existing_id

    except Exception as e:
        logger.error(f"Merge failed: {e}")
        return None


def find_consolidation_clusters(
    client: QdrantClient,
    collection_name: str,
    older_than_days: int = ARCHIVE_AGE_DAYS,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
    min_cluster_size: int = MIN_CLUSTER_SIZE
) -> list[ConsolidationCluster]:
    """
    Find clusters of similar memories for consolidation.

    Args:
        client: Qdrant client
        collection_name: Collection to analyze
        older_than_days: Only consider memories older than this
        similarity_threshold: Similarity threshold for clustering
        min_cluster_size: Minimum cluster size

    Returns:
        List of ConsolidationCluster objects
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)

        # Get all memories older than cutoff
        all_memories = []
        scroll_offset = None

        while True:
            results, scroll_offset = client.scroll(
                collection_name=collection_name,
                limit=100,
                offset=scroll_offset,
                with_payload=True,
                with_vectors=["dense"],
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="created_at",
                            range=models.DatetimeRange(
                                lt=cutoff_date
                            )
                        )
                    ],
                    must_not=[
                        models.FieldCondition(
                            key="archived",
                            match=models.MatchValue(value=True)
                        )
                    ]
                )
            )
            all_memories.extend(results)
            if scroll_offset is None:
                break

        if len(all_memories) < min_cluster_size:
            logger.info(f"Not enough old memories for clustering ({len(all_memories)})")
            return []

        logger.info(f"Found {len(all_memories)} memories for clustering")

        # Hierarchical clustering for better semantic grouping
        clusters = _hierarchical_cluster(all_memories, similarity_threshold, min_cluster_size)

        # Convert to ConsolidationCluster objects
        result_clusters = []
        for cluster_memories in clusters:
            # Determine suggested type (most common)
            type_counts = defaultdict(int)
            all_tags = set()
            for mem in cluster_memories:
                mem_type = mem.payload.get("type", "context")
                type_counts[mem_type] += 1
                all_tags.update(mem.payload.get("tags", []))

            suggested_type = max(type_counts, key=type_counts.get)

            result_clusters.append(ConsolidationCluster(
                memory_ids=[str(m.id) for m in cluster_memories],
                similarity_score=similarity_threshold,
                suggested_type=MemoryType(suggested_type),
                suggested_tags=list(all_tags)[:10]  # Limit tags
            ))

        return result_clusters

    except Exception as e:
        logger.error(f"Clustering failed: {e}")
        return []


def _hierarchical_cluster(
    memories: list,
    threshold: float,
    min_size: int
) -> list[list]:
    """
    Hierarchical clustering using average linkage.

    Better than greedy clustering because it considers the full dendrogram
    structure to find optimal semantic groupings.

    Args:
        memories: List of Qdrant points with vectors
        threshold: Similarity threshold (converts to distance)
        min_size: Minimum cluster size

    Returns:
        List of clusters (each cluster is a list of memories)
    """
    import numpy as np

    # Try to import sklearn, fall back to greedy if not available
    try:
        from sklearn.cluster import AgglomerativeClustering
    except ImportError:
        logger.warning("scikit-learn not available, falling back to greedy clustering")
        return _greedy_cluster_fallback(memories, threshold, min_size)

    if not memories:
        return []

    # Extract vectors
    vectors = []
    for mem in memories:
        vec = mem.vector
        if isinstance(vec, dict) and "dense" in vec:
            vectors.append(vec["dense"])
        elif isinstance(vec, list):
            vectors.append(vec)
        else:
            vectors.append([0] * get_embedding_dim())

    vectors = np.array(vectors)

    # Normalize for cosine similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    vectors = vectors / norms

    # Compute pairwise distance matrix (1 - cosine similarity)
    similarity = np.dot(vectors, vectors.T)
    distance_matrix = 1 - similarity

    # Hierarchical clustering with average linkage
    # distance_threshold = 1 - threshold converts similarity to distance
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1 - threshold,
        linkage='average',
        metric='precomputed'
    )

    labels = clustering.fit_predict(distance_matrix)

    # Group memories by cluster label
    cluster_map = defaultdict(list)
    for idx, label in enumerate(labels):
        cluster_map[label].append(memories[idx])

    # Filter clusters by minimum size
    clusters = [
        cluster for cluster in cluster_map.values()
        if len(cluster) >= min_size
    ]

    logger.debug(
        f"Hierarchical clustering: {len(memories)} memories → "
        f"{len(clusters)} clusters (min_size={min_size})"
    )

    return clusters


def _greedy_cluster_fallback(
    memories: list,
    threshold: float,
    min_size: int
) -> list[list]:
    """
    Fallback greedy clustering (used when sklearn unavailable).

    Args:
        memories: List of Qdrant points with vectors
        threshold: Similarity threshold
        min_size: Minimum cluster size

    Returns:
        List of clusters (each cluster is a list of memories)
    """
    import numpy as np

    if not memories:
        return []

    # Extract vectors
    vectors = []
    for mem in memories:
        vec = mem.vector
        if isinstance(vec, dict) and "dense" in vec:
            vectors.append(vec["dense"])
        elif isinstance(vec, list):
            vectors.append(vec)
        else:
            vectors.append([0] * get_embedding_dim())

    vectors = np.array(vectors)

    # Normalize for cosine similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    vectors = vectors / norms

    # Compute similarity matrix
    similarity = np.dot(vectors, vectors.T)

    # Greedy clustering
    clustered = set()
    clusters = []

    for i in range(len(memories)):
        if i in clustered:
            continue

        # Find all similar memories
        cluster_indices = [i]
        for j in range(i + 1, len(memories)):
            if j not in clustered and similarity[i, j] >= threshold:
                cluster_indices.append(j)

        if len(cluster_indices) >= min_size:
            clusters.append([memories[idx] for idx in cluster_indices])
            clustered.update(cluster_indices)

    return clusters


def consolidate_cluster(
    client: QdrantClient,
    collection_name: str,
    cluster: ConsolidationCluster,
    archive_originals: bool = True
) -> Optional[str]:
    """
    Consolidate a cluster of memories into a single memory.

    Args:
        client: Qdrant client
        collection_name: Collection name
        cluster: Cluster to consolidate
        archive_originals: Whether to archive original memories

    Returns:
        ID of consolidated memory, or None on failure
    """
    try:
        # Retrieve all memories in cluster
        results = client.retrieve(
            collection_name=collection_name,
            ids=cluster.memory_ids,
            with_payload=True
        )

        if not results:
            return None

        # Find primary memory (highest importance * access_count)
        def get_score(mem):
            importance = mem.payload.get("importance_score", 0.5)
            if isinstance(importance, dict):
                importance = 0.5
            access = mem.payload.get("access_count", 0)
            if isinstance(access, dict):
                access = 0
            return importance * (access + 1)

        primary = max(results, key=get_score)

        # Combine all unique tags
        all_tags = set(cluster.suggested_tags)
        total_access = 0
        for mem in results:
            all_tags.update(mem.payload.get("tags", []))
            access = mem.payload.get("access_count", 0)
            if isinstance(access, int):
                total_access += access

        # Create consolidated memory content
        consolidated_content = primary.payload.get("content", "")
        if cluster.suggested_summary:
            consolidated_content = cluster.suggested_summary

        # Generate new embedding
        embeddings = embed_text(consolidated_content, include_sparse=False)

        # Create consolidated memory
        from uuid6 import uuid7
        consolidated_id = str(uuid7())

        from .enhancements import normalize_tags
        consolidated_payload = {
            "id": consolidated_id,
            "content": consolidated_content,
            "type": cluster.suggested_type.value,
            "tags": normalize_tags(list(all_tags))[:15],
            "memory_tier": MemoryTier.SEMANTIC.value,
            "access_count": total_access,
            "importance_score": 0.8,  # Consolidated memories are valuable
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "consolidated_from": cluster.memory_ids,
            "archived": False
        }

        # Upsert consolidated memory
        client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=consolidated_id,
                    vector={"dense": embeddings["dense"]},
                    payload=consolidated_payload
                )
            ]
        )

        # Calculate quality score for the new consolidated memory
        try:
            from .quality_tracking import QualityScoreCalculator
            QualityScoreCalculator.recalculate_single_memory_quality(
                client, collection_name, consolidated_id
            )
        except Exception as e:
            logger.warning(f"Quality calc failed for consolidated {consolidated_id}: {e}")

        # Archive originals if requested
        if archive_originals:
            from .collections import safe_set_payload
            for mem_id in cluster.memory_ids:
                safe_set_payload(
                    mem_id,
                    {
                        "archived": True,
                        "archived_at": datetime.now(timezone.utc).isoformat()
                    },
                    recalc_quality=False,  # No need to recalc archived memories
                    collection_name=collection_name,
                )

        logger.info(f"Consolidated {len(cluster.memory_ids)} memories into {consolidated_id}")
        return consolidated_id

    except Exception as e:
        logger.error(f"Consolidation failed: {e}")
        return None


def archive_old_memories(
    client: QdrantClient,
    collection_name: str,
    older_than_days: int = ARCHIVE_AGE_DAYS,
    min_access_count: int = MIN_ACCESS_COUNT,
    dry_run: bool = False
) -> ArchiveResult:
    """
    Archive old, low-value memories.

    Args:
        client: Qdrant client
        collection_name: Collection name
        older_than_days: Archive memories older than this
        min_access_count: Don't archive if accessed more than this
        dry_run: If True, don't actually archive

    Returns:
        ArchiveResult with statistics
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)

        # Find candidates for archival
        candidates = []
        scroll_offset = None

        while True:
            results, scroll_offset = client.scroll(
                collection_name=collection_name,
                limit=100,
                offset=scroll_offset,
                with_payload=True,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="created_at",
                            range=models.DatetimeRange(lt=cutoff_date)
                        )
                    ],
                    must_not=[
                        models.FieldCondition(
                            key="archived",
                            match=models.MatchValue(value=True)
                        )
                    ]
                )
            )
            candidates.extend(results)
            if scroll_offset is None:
                break

        # Filter by access count and importance
        to_archive = []
        to_keep = []

        for mem in candidates:
            access_count = mem.payload.get("access_count", 0)
            if isinstance(access_count, dict):
                access_count = 0

            importance = mem.payload.get("importance_score", 0.5)
            if isinstance(importance, dict):
                importance = 0.5

            mem_type = mem.payload.get("type", "context")

            # Don't archive high-value memories
            if mem_type in ("error", "decision") and mem.payload.get("solution"):
                to_keep.append(mem)
                continue

            if access_count > min_access_count:
                to_keep.append(mem)
                continue

            if importance > 0.7:
                to_keep.append(mem)
                continue

            to_archive.append(mem)

        # Archive if not dry run
        if not dry_run and to_archive:
            archive_ids = [str(m.id) for m in to_archive]
            for mem_id in archive_ids:
                client.set_payload(
                    collection_name=collection_name,
                    payload={
                        "archived": True,
                        "archived_at": datetime.now(timezone.utc).isoformat()
                    },
                    points=[mem_id]
                )

        logger.info(f"Archive analysis: {len(to_archive)} to archive, {len(to_keep)} to keep")

        return ArchiveResult(
            analyzed=len(candidates),
            consolidated=0,
            archived=len(to_archive),
            deleted=0,
            kept=len(to_keep),
            dry_run=dry_run
        )

    except Exception as e:
        logger.error(f"Archive failed: {e}")
        return ArchiveResult(
            analyzed=0, consolidated=0, archived=0,
            deleted=0, kept=0, dry_run=dry_run
        )


def run_consolidation(
    client: QdrantClient,
    collection_name: str,
    older_than_days: int = ARCHIVE_AGE_DAYS,
    dry_run: bool = False
) -> ArchiveResult:
    """
    Run full consolidation pipeline.

    1. Find clusters of similar old memories
    2. Consolidate each cluster
    3. Archive remaining old low-value memories

    Args:
        client: Qdrant client
        collection_name: Collection name
        older_than_days: Process memories older than this
        dry_run: If True, don't make changes

    Returns:
        ArchiveResult with statistics
    """
    logger.info(f"Starting consolidation (dry_run={dry_run})")

    # Find clusters
    clusters = find_consolidation_clusters(
        client, collection_name, older_than_days
    )

    consolidated_count = 0
    consolidated_memory_count = 0

    # Consolidate each cluster
    if not dry_run:
        for cluster in clusters:
            result_id = consolidate_cluster(
                client, collection_name, cluster, archive_originals=True
            )
            if result_id:
                consolidated_count += 1
                consolidated_memory_count += len(cluster.memory_ids)

    # Archive remaining old memories
    archive_result = archive_old_memories(
        client, collection_name, older_than_days, dry_run=dry_run
    )

    return ArchiveResult(
        analyzed=archive_result.analyzed + consolidated_memory_count,
        consolidated=consolidated_count,
        archived=archive_result.archived,
        deleted=0,
        kept=archive_result.kept,
        dry_run=dry_run,
        details={
            "clusters_found": len(clusters),
            "memories_consolidated": consolidated_memory_count
        }
    )


# ============================================================================
# Brain-Like Intelligence: Adaptive Learning & Intelligent Forgetting
# ============================================================================


def calculate_adaptive_importance(
    memory_id: str,
    access_count: int,
    created_at: datetime,
    memory_type: str,
    has_solution: bool = False,
    co_accessed_with: Optional[list[str]] = None
) -> float:
    """
    Calculate importance score based on multiple signals (adaptive learning).

    Factors:
    - Access frequency (more accesses = higher)
    - Recency bias (recent accesses weighted higher)
    - Memory type (errors with solutions = high, ephemeral = low)
    - Co-access patterns (accessed with other important memories = higher)

    Args:
        memory_id: Memory ID
        access_count: Number of times accessed
        created_at: Creation timestamp
        memory_type: Type of memory (error, decision, etc.)
        has_solution: For errors, whether solution exists
        co_accessed_with: List of memory IDs accessed together

    Returns:
        Importance score between 0.1 and 1.0
    """
    import math

    # Base importance by type
    type_weights = {
        "error": 0.8 if has_solution else 0.6,
        "decision": 0.9,
        "docs": 0.7,
        "pattern": 0.8,
        "learning": 0.6,
        "context": 0.5,
    }

    base_score = type_weights.get(memory_type, 0.5)

    # Access frequency boost (logarithmic to avoid runaway scores)
    access_boost = min(0.3, math.log(access_count + 1) / 10)

    # Recency bias (memories accessed recently are more important)
    days_since_creation = (datetime.now(timezone.utc) - created_at).days
    recency_penalty = min(0.2, days_since_creation / 100)

    # Co-access boost (if accessed with other memories)
    co_access_boost = 0.0
    if co_accessed_with:
        # If accessed with high-importance memories, boost this memory
        co_access_boost = min(0.2, len(co_accessed_with) * 0.05)

    final_score = base_score + access_boost - recency_penalty + co_access_boost

    return max(0.1, min(1.0, final_score))  # Clamp to [0.1, 1.0]


def update_importance_scores_batch(
    client: QdrantClient,
    collection_name: str,
    limit: int = 100
) -> int:
    """
    Background job to update importance scores for memories.

    Run daily via scheduler to adapt memory importance based on usage.

    Args:
        client: Qdrant client
        collection_name: Collection name
        limit: Max memories to process per batch

    Returns:
        Number of memories updated
    """
    try:
        # Get memories ordered by access count
        points, _ = client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )

        updated = 0
        for point in points:
            payload = point.payload

            # Calculate new importance
            new_importance = calculate_adaptive_importance(
                memory_id=str(point.id),
                access_count=payload.get("access_count", 0),
                created_at=datetime.fromisoformat(payload["created_at"]),
                memory_type=payload["type"],
                has_solution=payload.get("resolved", False),
                co_accessed_with=payload.get("co_accessed_with", [])
            )

            # Update in Qdrant
            client.set_payload(
                collection_name=collection_name,
                points=[point.id],
                payload={"importance_score": new_importance}
            )
            updated += 1

        logger.info(f"Updated importance scores for {updated} memories")
        return updated

    except Exception as e:
        logger.error(f"Failed to update importance scores: {e}")
        return 0


def calculate_memory_utility(
    access_count: int,
    importance: float,
    created_at: datetime,
    last_accessed_at: Optional[datetime],
    relationship_count: int,
    memory_type: str
) -> float:
    """
    Calculate utility score for memory retention (intelligent forgetting).

    High utility = keep
    Low utility = archive/forget

    Factors:
    - Access frequency
    - Recency of access (not creation)
    - Relationship count (memories with many links are valuable)
    - Importance score
    - Memory type

    Args:
        access_count: Number of accesses
        importance: Importance score
        created_at: Creation timestamp
        last_accessed_at: Last access timestamp
        relationship_count: Number of relationships in graph
        memory_type: Type of memory

    Returns:
        Utility score between 0.0 and 1.0
    """
    import math

    # Access frequency (logarithmic)
    access_score = min(0.3, math.log(access_count + 1) / 10)

    # Recency of LAST ACCESS (not creation)
    if last_accessed_at:
        days_since_access = (datetime.now(timezone.utc) - last_accessed_at).days
        recency_score = max(0, 0.3 - days_since_access / 100)
    else:
        recency_score = 0

    # Relationship score (connected memories are valuable)
    relationship_score = min(0.2, relationship_count * 0.05)

    # Importance weight
    importance_score = importance * 0.2

    total = access_score + recency_score + relationship_score + importance_score

    return max(0, min(1.0, total))


def archive_low_utility_memories(
    client: QdrantClient,
    collection_name: str,
    utility_threshold: float = 0.3,
    max_archive: int = 100,
    dry_run: bool = False
) -> int:
    """
    Archive memories with low utility score (utility-based forgetting).

    Replace time-based archival with utility-based to keep valuable memories.

    Args:
        client: Qdrant client
        collection_name: Collection name
        utility_threshold: Archive if utility < this (default 0.3)
        max_archive: Max memories to archive in one run
        dry_run: If True, don't make changes

    Returns:
        Number of memories archived
    """
    try:
        # Import graph module to get relationships
        try:
            from .graph import get_driver
            graph_enabled = True
        except Exception:
            graph_enabled = False
            logger.warning("Graph not available for relationship counts")

        # Get all non-archived memories
        points, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must_not=[
                    models.FieldCondition(
                        key="archived",
                        match=models.MatchValue(value=True)
                    )
                ]
            ),
            limit=1000,
            with_payload=True,
            with_vectors=False
        )

        # Calculate utility for each
        utilities = []
        for point in points:
            payload = point.payload

            # Get relationship count from graph if available
            rel_count = 0
            if graph_enabled:
                try:
                    driver = get_driver()
                    with driver.session() as session:
                        result = session.run(
                            "MATCH (m:Memory {id: $id})-[r]-() RETURN count(r) as count",
                            id=str(point.id)
                        )
                        record = result.single()
                        rel_count = record["count"] if record else 0
                except Exception:
                    pass

            utility = calculate_memory_utility(
                access_count=payload.get("access_count", 0),
                importance=payload.get("importance", 0.5),
                created_at=datetime.fromisoformat(payload["created_at"]),
                last_accessed_at=(
                    datetime.fromisoformat(payload["last_accessed_at"])
                    if payload.get("last_accessed_at")
                    else datetime.fromisoformat(payload["created_at"])
                ),
                relationship_count=rel_count,
                memory_type=payload["type"]
            )

            utilities.append((point.id, utility, payload))

        # Sort by utility (lowest first)
        utilities.sort(key=lambda x: x[1])

        # Archive bottom N with utility < threshold
        archived = 0
        for mem_id, utility, payload in utilities:
            if utility >= utility_threshold or archived >= max_archive:
                break

            # Protected types (never archive)
            if payload["type"] in ["decision", "pattern"]:
                continue

            # Keep resolved errors (they're valuable)
            if payload.get("resolved"):
                continue

            if not dry_run:
                # Archive
                client.set_payload(
                    collection_name=collection_name,
                    points=[mem_id],
                    payload={
                        "archived": True,
                        "archived_at": datetime.now(timezone.utc).isoformat(),
                        "archive_reason": "low_utility",
                        "utility_score": utility
                    }
                )

            archived += 1
            logger.info(f"Archived memory {mem_id} (utility: {utility:.2f})")

        logger.info(f"Archived {archived} low-utility memories")
        return archived

    except Exception as e:
        logger.error(f"Failed to archive low-utility memories: {e}")
        return 0
