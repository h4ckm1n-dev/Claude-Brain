"""Graph-based search expansion for improved retrieval.

Implements Phase 2.1: Graph-based Search Expansion
- Expand vector search results using knowledge graph relationships
- Weight results by relationship type and strength
- Merge and re-rank expanded results
- Provide richer context through connected knowledge
"""

import logging
from typing import List, Dict, Set, Optional
from collections import defaultdict

from .models import SearchResult, Memory
from .graph import is_graph_enabled, get_related_memories

logger = logging.getLogger(__name__)

# Relationship weights for search expansion
# Higher weights indicate stronger relevance
RELATIONSHIP_WEIGHTS = {
    "FIXES": 1.0,       # Strongest - solution directly fixes problem
    "SUPPORTS": 0.9,    # Very strong - pattern/decision supports solution
    "FOLLOWS": 0.8,     # Strong - sequential relationship
    "RELATED": 0.7,     # Moderate - general semantic similarity
    "SIMILAR_TO": 0.6,  # Moderate-weak - similar content
    "PART_OF": 0.5,     # Weak - part of larger context
    "CAUSES": 0.4,      # Weak - causal but not solution
    "CONTRADICTS": -0.5  # Negative - contradictory information
}

# Default weight for unknown relationship types
DEFAULT_RELATIONSHIP_WEIGHT = 0.5


class GraphSearchExpander:
    """Expands vector search results using knowledge graph relationships."""

    @staticmethod
    def expand_search_results(
        initial_results: List[SearchResult],
        max_hops: int = 1,
        expansion_factor: float = 0.6,
        top_k: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Expand search results using graph relationships.

        Algorithm:
        1. Take initial vector search results (top N)
        2. For each result, get 1-hop neighbors from graph
        3. Score neighbors: neighbor_score = relationship_weight * original_score * expansion_factor
        4. Merge expanded results, deduplicate
        5. Re-rank by combined score
        6. Return top K results

        Args:
            initial_results: Initial vector search results
            max_hops: Maximum relationship hops (1-3, default: 1)
            expansion_factor: Dampening factor for expanded results (default: 0.6)
            top_k: Number of results to return (default: len(initial_results))

        Returns:
            Expanded and re-ranked search results
        """
        if not is_graph_enabled():
            logger.debug("Graph not enabled, returning original results")
            return initial_results

        if not initial_results:
            return []

        if top_k is None:
            top_k = len(initial_results)

        # Track scores for all memories (initial + expanded)
        # Key: memory_id, Value: (memory, max_score, source)
        all_scores: Dict[str, tuple] = {}

        # Add initial results
        for result in initial_results:
            all_scores[result.memory.id] = (
                result.memory,
                result.score,
                "initial"
            )

        # Expand each initial result
        for result in initial_results:
            try:
                # Get related memories from graph
                related = get_related_memories(
                    result.memory.id,
                    max_hops=max_hops,
                    limit=10  # Limit neighbors per node
                )

                if not related:
                    continue

                # Score and add each related memory
                for rel in related:
                    rel_memory_id = rel.get("id")
                    # Extract relationship type from path (use first/closest relationship)
                    rel_path = rel.get("relationship_path", [])
                    rel_type = rel_path[0] if rel_path else "RELATED"
                    rel_depth = rel.get("distance", 1)

                    # Skip if already in results with higher score
                    if rel_memory_id in all_scores:
                        continue

                    # Calculate neighbor score
                    rel_weight = RELATIONSHIP_WEIGHTS.get(
                        rel_type,
                        DEFAULT_RELATIONSHIP_WEIGHT
                    )

                    # Apply depth penalty (each hop reduces score)
                    depth_penalty = 0.8 ** rel_depth

                    # Final score: base_score * rel_weight * expansion_factor * depth_penalty
                    neighbor_score = (
                        result.score *
                        rel_weight *
                        expansion_factor *
                        depth_penalty
                    )

                    # Skip if score is too low or negative (contradicts)
                    if neighbor_score < 0.1:
                        continue

                    # Add to results (will need to fetch full memory later)
                    all_scores[rel_memory_id] = (
                        None,  # Memory object (to be fetched)
                        neighbor_score,
                        f"expanded_{rel_type}"
                    )

                    logger.debug(
                        f"Expanded: {rel_memory_id} via {rel_type} "
                        f"(score: {neighbor_score:.3f})"
                    )

            except Exception as e:
                logger.warning(f"Failed to expand result {result.memory.id}: {e}")
                continue

        # Fetch full memory objects for expanded results
        expanded_count = 0
        for memory_id, (memory, score, source) in list(all_scores.items()):
            if memory is None:  # Expanded result, need to fetch
                try:
                    from .collections import get_memory
                    fetched_memory = get_memory(memory_id)
                    if fetched_memory:
                        all_scores[memory_id] = (fetched_memory, score, source)
                        expanded_count += 1
                    else:
                        # Memory not found, remove from results
                        del all_scores[memory_id]
                except Exception as e:
                    logger.warning(f"Failed to fetch memory {memory_id}: {e}")
                    del all_scores[memory_id]

        # Sort by score and create SearchResult objects
        sorted_results = sorted(
            all_scores.values(),
            key=lambda x: x[1],  # Sort by score
            reverse=True
        )

        # Convert to SearchResult objects
        final_results = []
        for memory, score, source in sorted_results[:top_k]:
            final_results.append(
                SearchResult(
                    memory=memory,
                    score=score,
                    composite_score=score  # Use expanded score as composite
                )
            )

        logger.info(
            f"Graph expansion: {len(initial_results)} initial → "
            f"{len(all_scores)} total → {len(final_results)} returned "
            f"({expanded_count} expanded)"
        )

        return final_results

    @staticmethod
    def expand_with_context(
        initial_results: List[SearchResult],
        context_depth: int = 1
    ) -> Dict[str, List[Dict]]:
        """
        Expand search results with contextual information from graph.

        For each result, include connected memories as context
        without affecting the main search ranking.

        Args:
            initial_results: Initial vector search results
            context_depth: How many hops to include for context (default: 1)

        Returns:
            Dict mapping memory_id to list of context memories
        """
        if not is_graph_enabled():
            return {}

        context_map = {}

        for result in initial_results:
            try:
                # Get related memories for context
                related = get_related_memories(
                    result.memory.id,
                    max_hops=context_depth,
                    limit=5  # Limit context items
                )

                if related:
                    context_map[result.memory.id] = related

            except Exception as e:
                logger.warning(f"Failed to get context for {result.memory.id}: {e}")

        return context_map

    @staticmethod
    def get_expansion_stats(
        initial_results: List[SearchResult],
        expanded_results: List[SearchResult]
    ) -> Dict:
        """
        Get statistics about the expansion operation.

        Args:
            initial_results: Initial search results
            expanded_results: Expanded search results

        Returns:
            Dictionary with expansion statistics
        """
        initial_ids = {r.memory.id for r in initial_results}
        expanded_ids = {r.memory.id for r in expanded_results}

        new_results = expanded_ids - initial_ids
        kept_results = initial_ids & expanded_ids
        dropped_results = initial_ids - expanded_ids

        return {
            "initial_count": len(initial_results),
            "expanded_count": len(expanded_results),
            "new_results": len(new_results),
            "kept_results": len(kept_results),
            "dropped_results": len(dropped_results),
            "expansion_rate": len(new_results) / len(initial_results) if initial_results else 0
        }


def expand_search_with_graph(
    initial_results: List[SearchResult],
    use_expansion: bool = True,
    max_hops: int = 1,
    expansion_factor: float = 0.6,
    top_k: Optional[int] = None
) -> List[SearchResult]:
    """
    Convenience function to expand search results with graph relationships.

    Args:
        initial_results: Initial vector search results
        use_expansion: Whether to enable graph expansion
        max_hops: Maximum relationship hops (1-3)
        expansion_factor: Dampening factor for expanded results
        top_k: Number of results to return

    Returns:
        Expanded search results (or original if expansion disabled)
    """
    if not use_expansion or not is_graph_enabled():
        return initial_results

    try:
        expanded = GraphSearchExpander.expand_search_results(
            initial_results=initial_results,
            max_hops=max_hops,
            expansion_factor=expansion_factor,
            top_k=top_k
        )

        # Log stats
        stats = GraphSearchExpander.get_expansion_stats(initial_results, expanded)
        logger.info(
            f"Graph expansion stats: "
            f"initial={stats['initial_count']}, "
            f"expanded={stats['expanded_count']}, "
            f"new={stats['new_results']}, "
            f"rate={stats['expansion_rate']:.2f}"
        )

        return expanded

    except Exception as e:
        logger.error(f"Graph expansion failed: {e}")
        return initial_results
