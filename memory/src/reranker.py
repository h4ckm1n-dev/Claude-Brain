"""Cross-encoder reranking for improved search precision.

Uses cross-encoder reranking (model configurable via RERANK_MODEL_NAME env var).
Improves search precision by ~40% compared to bi-encoder only.

All model operations are delegated to embedding_client, which routes
to the standalone embedding service (HTTP) or loads models locally.
"""

import logging

from .embedding_client import rerank_texts, is_reranker_enabled

logger = logging.getLogger(__name__)


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

    if not is_reranker_enabled():
        logger.warning("Reranker disabled, returning documents unchanged")
        return documents[:top_k]

    try:
        # Build text list from documents
        texts = []
        for doc in documents:
            content = doc.get(content_key, "")
            if doc.get("context"):
                content += f" {doc['context']}"
            if doc.get("error_message"):
                content += f" {doc['error_message']}"
            texts.append(content)

        # Get reranking scores via embedding client
        scores = rerank_texts(query, texts, top_k=top_k)

        # Attach scores to documents
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = score

        # Sort by rerank score and return top_k
        reranked = sorted(documents, key=lambda x: x.get("rerank_score", 0), reverse=True)

        logger.debug(f"Reranked {len(documents)} documents, returning top {top_k}")
        return reranked[:top_k]

    except Exception as e:
        logger.error(f"Reranking failed: {e}")
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

    if not is_reranker_enabled():
        return search_results[:top_k]

    try:
        # Extract enriched content from search results for reranking
        texts = []
        for result in search_results:
            memory = result.memory
            parts = [memory.content or ""]
            if memory.context:
                parts.append(memory.context)
            if memory.error_message:
                parts.append(memory.error_message)
            if memory.solution:
                parts.append(memory.solution)
            if memory.prevention:
                parts.append(memory.prevention)
            if memory.rationale:
                parts.append(memory.rationale)
            if memory.tags:
                parts.append(" ".join(memory.tags))
            if memory.project:
                parts.append(memory.project)
            texts.append(" ".join(parts))

        # Get reranking scores via embedding client
        scores = rerank_texts(query, texts, top_k=top_k)

        # Create tuples for sorting
        scored_results = list(zip(search_results, scores))
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # Update scores on results and return
        reranked = []
        for result, rerank_score in scored_results[:top_k]:
            result.composite_score = rerank_score
            reranked.append(result)

        logger.debug(f"Reranked {len(search_results)} results, returning top {top_k}")
        return reranked

    except Exception as e:
        logger.error(f"Reranking search results failed: {e}")
        return search_results[:top_k]
