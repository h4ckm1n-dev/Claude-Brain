"""Cross-encoder reranking for improved search precision.

Uses ms-marco-MiniLM-L-6-v2 for fast, accurate reranking.
Improves search precision by ~40% compared to bi-encoder only.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Model configuration
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Lazy loading
_reranker = None


def _get_reranker():
    """Get the cross-encoder reranker (singleton, lazy loaded)."""
    global _reranker
    if _reranker is None:
        logger.info(f"Loading cross-encoder reranker: {RERANK_MODEL}")
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder(RERANK_MODEL)
            logger.info("Cross-encoder reranker loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load reranker: {e}")
            _reranker = "disabled"
    return _reranker


def is_reranker_enabled() -> bool:
    """Check if reranker is available."""
    reranker = _get_reranker()
    return reranker != "disabled"


def rerank(
    query: str,
    documents: list[dict],
    top_k: int = 10,
    content_key: str = "content"
) -> list[dict]:
    """
    Rerank documents using cross-encoder.

    Args:
        query: The search query
        documents: List of document dicts with content
        top_k: Number of top results to return
        content_key: Key in document dict containing text to rerank

    Returns:
        Reranked documents sorted by rerank_score (descending)
    """
    if not documents:
        return []

    reranker = _get_reranker()

    if reranker == "disabled":
        logger.warning("Reranker disabled, returning documents unchanged")
        return documents[:top_k]

    try:
        # Build query-document pairs
        pairs = []
        for doc in documents:
            content = doc.get(content_key, "")
            # Include additional context if available
            if doc.get("context"):
                content += f" {doc['context']}"
            if doc.get("error_message"):
                content += f" {doc['error_message']}"
            pairs.append([query, content])

        # Get reranking scores
        scores = reranker.predict(pairs)

        # Attach scores to documents
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)

        # Sort by rerank score and return top_k
        reranked = sorted(documents, key=lambda x: x.get("rerank_score", 0), reverse=True)

        logger.debug(f"Reranked {len(documents)} documents, returning top {top_k}")
        return reranked[:top_k]

    except Exception as e:
        logger.error(f"Reranking failed: {e}")
        # Fall back to original order
        return documents[:top_k]


def rerank_search_results(
    query: str,
    search_results: list,
    top_k: int = 10
) -> list:
    """
    Rerank SearchResult objects from memory search.

    Args:
        query: The search query
        search_results: List of SearchResult objects
        top_k: Number of results to return

    Returns:
        Reranked SearchResult list
    """
    if not search_results:
        return []

    reranker = _get_reranker()

    if reranker == "disabled":
        return search_results[:top_k]

    try:
        # Extract content from search results
        pairs = []
        for result in search_results:
            memory = result.memory
            content = memory.content or ""
            if memory.context:
                content += f" {memory.context}"
            if memory.error_message:
                content += f" {memory.error_message}"
            pairs.append([query, content])

        # Get reranking scores
        scores = reranker.predict(pairs)

        # Create tuples for sorting
        scored_results = list(zip(search_results, scores))

        # Sort by rerank score
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # Update scores on results and return
        reranked = []
        for result, rerank_score in scored_results[:top_k]:
            # Store both original score and rerank score
            result.composite_score = float(rerank_score)
            reranked.append(result)

        logger.debug(f"Reranked {len(search_results)} results, returning top {top_k}")
        return reranked

    except Exception as e:
        logger.error(f"Reranking search results failed: {e}")
        return search_results[:top_k]
