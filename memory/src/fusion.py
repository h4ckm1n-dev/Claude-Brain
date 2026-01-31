"""Learned fusion weights for hybrid search.

Instead of static RRF fusion, this module classifies queries and applies
optimal fusion weights based on query type:
- Conceptual queries → favor dense (semantic) search
- Exact match queries → favor sparse (keyword) search
- Hybrid queries → balanced weights
"""

import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)


class LearnedFusionWeights:
    """Query classification and learned fusion weight selection."""

    # Query type → dense weight mapping (sparse weight = 1 - dense)
    QUERY_TYPES = {
        "conceptual": 0.7,    # Favor semantic search
        "exact_match": 0.3,   # Favor keyword search
        "hybrid": 0.5,        # Balanced
    }

    @staticmethod
    def classify_query(query: str) -> str:
        """
        Classify query type based on patterns.

        Args:
            query: Search query text

        Returns:
            Query type: "conceptual", "exact_match", or "hybrid"
        """
        query_lower = query.lower()
        query_stripped = query.strip()

        # Exact match indicators
        if '"' in query:
            # Quoted strings indicate exact match
            return "exact_match"

        if query.isupper() and len(query) > 3:
            # ALL CAPS often indicates error codes, constants
            return "exact_match"

        if len(query.split()) <= 2 and not any(
            word in query_lower for word in ["how", "why", "what", "when", "where", "explain"]
        ):
            # Short queries without question words likely exact match
            return "exact_match"

        # Check for error patterns (ECONNREFUSED, TypeError, etc.)
        error_patterns = [
            r'^[A-Z][a-z]+Error',  # TypeError, ValueError, etc.
            r'^E[A-Z]+',           # ECONNREFUSED, EACCES, etc.
            r'\b\d{3,4}\b',        # HTTP codes: 404, 500, etc.
        ]
        for pattern in error_patterns:
            if re.search(pattern, query):
                return "exact_match"

        # Conceptual indicators
        question_words = ["how", "why", "what", "when", "where", "explain", "describe", "understand"]
        if any(word in query_lower for word in question_words):
            return "conceptual"

        if len(query.split()) >= 6:
            # Long queries likely conceptual
            return "conceptual"

        # Check for comparative/analytical language
        conceptual_patterns = [
            r'\b(optimize|improve|best|better|difference|compare)\b',
            r'\b(pattern|approach|strategy|design|architecture)\b',
        ]
        for pattern in conceptual_patterns:
            if re.search(pattern, query_lower):
                return "conceptual"

        # Default to hybrid for ambiguous queries
        return "hybrid"

    @classmethod
    def get_fusion_weights(cls, query: str) -> Tuple[float, float]:
        """
        Get optimal fusion weights for a query.

        Args:
            query: Search query text

        Returns:
            Tuple of (dense_weight, sparse_weight)
        """
        query_type = cls.classify_query(query)
        dense_weight = cls.QUERY_TYPES[query_type]
        sparse_weight = 1.0 - dense_weight

        logger.debug(
            f"Query classified as '{query_type}': "
            f"dense={dense_weight:.2f}, sparse={sparse_weight:.2f}"
        )

        return dense_weight, sparse_weight

    @staticmethod
    def weighted_fusion(
        dense_results: List[Tuple[str, float]],
        sparse_results: List[Tuple[str, float]],
        dense_weight: float,
        sparse_weight: float
    ) -> List[Tuple[str, float]]:
        """
        Combine dense and sparse results using weighted fusion.

        Args:
            dense_results: List of (id, score) from dense search
            sparse_results: List of (id, score) from sparse search
            dense_weight: Weight for dense scores
            sparse_weight: Weight for sparse scores

        Returns:
            List of (id, fused_score) sorted by fused score descending
        """
        # Normalize scores to [0, 1] range
        def normalize_scores(results: List[Tuple[str, float]]) -> dict:
            if not results:
                return {}
            scores = [score for _, score in results]
            min_score = min(scores)
            max_score = max(scores)
            score_range = max_score - min_score

            if score_range == 0:
                # All scores are the same
                return {id_: 1.0 for id_, _ in results}

            return {
                id_: (score - min_score) / score_range
                for id_, score in results
            }

        dense_dict = normalize_scores(dense_results)
        sparse_dict = normalize_scores(sparse_results)

        # Combine scores with weights
        all_ids = set(dense_dict.keys()) | set(sparse_dict.keys())
        fused_scores = []

        for id_ in all_ids:
            dense_score = dense_dict.get(id_, 0.0)
            sparse_score = sparse_dict.get(id_, 0.0)
            fused_score = (dense_weight * dense_score) + (sparse_weight * sparse_score)
            fused_scores.append((id_, fused_score))

        # Sort by fused score descending
        fused_scores.sort(key=lambda x: x[1], reverse=True)

        logger.debug(
            f"Fused {len(dense_results)} dense + {len(sparse_results)} sparse "
            f"→ {len(fused_scores)} results"
        )

        return fused_scores


def apply_learned_fusion(
    query: str,
    dense_results: List[Tuple[str, float]],
    sparse_results: List[Tuple[str, float]]
) -> List[Tuple[str, float]]:
    """
    Apply learned fusion weights to combine search results.

    This is the main entry point for using learned fusion.

    Args:
        query: Original search query
        dense_results: Results from dense (semantic) search
        sparse_results: Results from sparse (keyword) search

    Returns:
        Fused results sorted by combined score
    """
    fusion = LearnedFusionWeights()
    dense_weight, sparse_weight = fusion.get_fusion_weights(query)

    return fusion.weighted_fusion(
        dense_results,
        sparse_results,
        dense_weight,
        sparse_weight
    )
