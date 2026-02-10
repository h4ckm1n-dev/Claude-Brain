"""Advanced embedding service with hybrid (dense + sparse) support.

Uses nomic-embed-text-v1.5 for dense embeddings (768 dims)
and SPLADE via fastembed for sparse embeddings.

All model operations are delegated to embedding_client, which routes
to the standalone embedding service (HTTP) or loads models locally.
"""

import logging
from typing import Optional

from .embedding_client import (
    embed_text as _client_embed_text,
    embed_query as _client_embed_query,
    embed_texts as _client_embed_texts,
    get_embedding_dim as _client_get_dim,
    is_sparse_enabled as _client_is_sparse,
    EMBEDDING_DIM,
)

logger = logging.getLogger(__name__)


def embed_text(text: str, include_sparse: bool = False) -> dict:
    """
    Generate embeddings for a single text string.

    Args:
        text: The text to embed
        include_sparse: Whether to include sparse embeddings for hybrid search

    Returns:
        dict with 'dense' (list[float]) and optionally 'sparse' (dict with indices/values)
    """
    return _client_embed_text(text, include_sparse=include_sparse)


def embed_query(query: str, include_sparse: bool = False) -> dict:
    """
    Generate embeddings for a search query.
    Uses different prefix than document embedding for better retrieval.

    Args:
        query: The search query
        include_sparse: Whether to include sparse embeddings

    Returns:
        dict with 'dense' and optionally 'sparse' embeddings
    """
    return _client_embed_query(query, include_sparse=include_sparse)


def embed_texts(texts: list[str], include_sparse: bool = False) -> list[dict]:
    """
    Generate embeddings for multiple texts (batched).

    Args:
        texts: List of texts to embed
        include_sparse: Whether to include sparse embeddings

    Returns:
        List of dicts with 'dense' and optionally 'sparse' embeddings
    """
    return _client_embed_texts(texts, include_sparse=include_sparse)


def get_embedding_dim() -> int:
    """Return the dense embedding dimension."""
    return _client_get_dim()


def is_sparse_enabled() -> bool:
    """Check if sparse embeddings are available."""
    return _client_is_sparse()


def validate_embedding_config() -> dict:
    """Validate that embedding dimension matches Qdrant collection config.

    Call at startup to catch dimension mismatches early.
    Returns dict with validation status.
    """
    try:
        from .collections import get_client, COLLECTION_NAME
        client = get_client()
        collection_info = client.get_collection(COLLECTION_NAME)

        # Check dense vector config
        vectors_config = collection_info.config.params.vectors
        if hasattr(vectors_config, 'size'):
            qdrant_dim = vectors_config.size
        elif isinstance(vectors_config, dict) and 'dense' in vectors_config:
            qdrant_dim = vectors_config['dense'].size
        else:
            return {"valid": True, "message": "Could not determine Qdrant dimension, skipping check"}

        if qdrant_dim != EMBEDDING_DIM:
            logger.error(
                f"DIMENSION MISMATCH: Embedding model outputs {EMBEDDING_DIM}-dim "
                f"but Qdrant collection expects {qdrant_dim}-dim vectors"
            )
            return {
                "valid": False,
                "embedding_dim": EMBEDDING_DIM,
                "qdrant_dim": qdrant_dim,
                "message": f"Dimension mismatch: model={EMBEDDING_DIM}, qdrant={qdrant_dim}"
            }

        return {
            "valid": True,
            "embedding_dim": EMBEDDING_DIM,
            "qdrant_dim": qdrant_dim,
            "message": f"Dimensions match: {EMBEDDING_DIM}"
        }

    except Exception as e:
        logger.warning(f"Embedding validation skipped: {e}")
        return {"valid": True, "message": f"Validation skipped: {e}"}


# Legacy compatibility functions
def embed_text_legacy(text: str) -> list[float]:
    """Legacy function returning only dense embedding as list."""
    return embed_text(text, include_sparse=False)["dense"]


def embed_texts_legacy(texts: list[str]) -> list[list[float]]:
    """Legacy function returning only dense embeddings as list of lists."""
    results = embed_texts(texts, include_sparse=False)
    return [r["dense"] for r in results]
