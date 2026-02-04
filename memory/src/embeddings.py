"""Advanced embedding service with hybrid (dense + sparse) support.

Uses nomic-embed-text-v1.5 for dense embeddings (768 dims)
and SPLADE via fastembed for sparse embeddings.
"""

import hashlib
import logging
from functools import lru_cache
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

# Model configuration
DENSE_MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"
SPARSE_MODEL_NAME = "Qdrant/bm42-all-minilm-l6-v2-attentions"
EMBEDDING_DIM = 768  # nomic-embed-text-v1.5 output dimension

# Lazy imports to avoid loading at module level
_dense_model = None
_sparse_model = None

# LRU cache for dense embeddings to avoid re-embedding identical content
_embedding_cache: dict[str, list[float]] = {}
_CACHE_MAX_SIZE = 512


def _cache_key(text: str) -> str:
    """Generate cache key for embedding text."""
    return hashlib.md5(text.encode()).hexdigest()


def _get_cached_embedding(text: str) -> Optional[list[float]]:
    """Get cached embedding if available."""
    key = _cache_key(text)
    return _embedding_cache.get(key)


def _set_cached_embedding(text: str, embedding: list[float]) -> None:
    """Cache an embedding, evicting oldest if full."""
    if len(_embedding_cache) >= _CACHE_MAX_SIZE:
        # Remove oldest entry (first key in dict)
        oldest_key = next(iter(_embedding_cache))
        del _embedding_cache[oldest_key]
    _embedding_cache[_cache_key(text)] = embedding


def _get_dense_model():
    """Get the dense embedding model (singleton, lazy loaded).

    Raises RuntimeError instead of silently falling back to a different
    dimension model, which would crash Qdrant inserts.
    """
    global _dense_model
    if _dense_model is None:
        logger.info(f"Loading dense embedding model: {DENSE_MODEL_NAME}")
        try:
            from sentence_transformers import SentenceTransformer
            _dense_model = SentenceTransformer(
                DENSE_MODEL_NAME,
                trust_remote_code=True  # Required for nomic models
            )
            logger.info(f"Dense model loaded. Dimension: {EMBEDDING_DIM}")
        except Exception as e:
            logger.error(f"Failed to load dense model '{DENSE_MODEL_NAME}': {e}")
            raise RuntimeError(
                f"Primary embedding model '{DENSE_MODEL_NAME}' failed to load. "
                f"Cannot fall back to a different-dimension model (would corrupt "
                f"Qdrant collection configured for {EMBEDDING_DIM}-dim vectors). "
                f"Fix the model installation or restart the service."
            ) from e
    return _dense_model


def _get_sparse_model():
    """Get the sparse embedding model (singleton, lazy loaded)."""
    global _sparse_model
    if _sparse_model is None:
        logger.info(f"Loading sparse embedding model: {SPARSE_MODEL_NAME}")
        try:
            from fastembed import SparseTextEmbedding
            _sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL_NAME)
            logger.info("Sparse model loaded (BM42/SPLADE)")
        except ImportError:
            logger.warning("fastembed not installed, sparse embeddings disabled")
            _sparse_model = "disabled"
        except Exception as e:
            logger.error(f"Failed to load sparse model: {e}")
            _sparse_model = "disabled"
    return _sparse_model


def embed_text(text: str, include_sparse: bool = False) -> dict:
    """
    Generate embeddings for a single text string.

    Args:
        text: The text to embed
        include_sparse: Whether to include sparse embeddings for hybrid search

    Returns:
        dict with 'dense' (list[float]) and optionally 'sparse' (dict with indices/values)
    """
    result = {}

    # Check cache for dense embedding
    prefixed_text = f"search_document: {text}"
    cached = _get_cached_embedding(prefixed_text)
    if cached:
        result["dense"] = cached
    else:
        # Generate dense embedding
        model = _get_dense_model()
        embedding = model.encode(prefixed_text, convert_to_numpy=True)
        result["dense"] = embedding.tolist()
        _set_cached_embedding(prefixed_text, result["dense"])

    # Generate sparse embedding if requested
    if include_sparse:
        sparse_model = _get_sparse_model()
        if sparse_model != "disabled":
            try:
                sparse_embeddings = list(sparse_model.embed([text]))
                if sparse_embeddings:
                    sparse_emb = sparse_embeddings[0]
                    result["sparse"] = {
                        "indices": sparse_emb.indices.tolist(),
                        "values": sparse_emb.values.tolist()
                    }
            except Exception as e:
                logger.warning(f"Sparse embedding failed: {e}")

    return result


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
    result = {}

    # Generate dense embedding with query prefix
    model = _get_dense_model()
    prefixed_query = f"search_query: {query}"
    embedding = model.encode(prefixed_query, convert_to_numpy=True)
    result["dense"] = embedding.tolist()

    # Generate sparse embedding if requested
    if include_sparse:
        sparse_model = _get_sparse_model()
        if sparse_model != "disabled":
            try:
                sparse_embeddings = list(sparse_model.embed([query]))
                if sparse_embeddings:
                    sparse_emb = sparse_embeddings[0]
                    result["sparse"] = {
                        "indices": sparse_emb.indices.tolist(),
                        "values": sparse_emb.values.tolist()
                    }
            except Exception as e:
                logger.warning(f"Sparse query embedding failed: {e}")

    return result


def embed_texts(texts: list[str], include_sparse: bool = False) -> list[dict]:
    """
    Generate embeddings for multiple texts (batched).

    Args:
        texts: List of texts to embed
        include_sparse: Whether to include sparse embeddings

    Returns:
        List of dicts with 'dense' and optionally 'sparse' embeddings
    """
    results = []

    # Batch dense embeddings
    model = _get_dense_model()
    prefixed_texts = [f"search_document: {t}" for t in texts]
    dense_embeddings = model.encode(prefixed_texts, convert_to_numpy=True, batch_size=32)

    # Batch sparse embeddings if requested
    sparse_embeddings = None
    if include_sparse:
        sparse_model = _get_sparse_model()
        if sparse_model != "disabled":
            try:
                sparse_embeddings = list(sparse_model.embed(texts))
            except Exception as e:
                logger.warning(f"Batch sparse embedding failed: {e}")

    # Combine results
    for i, dense_emb in enumerate(dense_embeddings):
        result = {"dense": dense_emb.tolist()}
        if sparse_embeddings and i < len(sparse_embeddings):
            sparse_emb = sparse_embeddings[i]
            result["sparse"] = {
                "indices": sparse_emb.indices.tolist(),
                "values": sparse_emb.values.tolist()
            }
        results.append(result)

    return results


def get_embedding_dim() -> int:
    """Return the dense embedding dimension."""
    return EMBEDDING_DIM


def is_sparse_enabled() -> bool:
    """Check if sparse embeddings are available."""
    sparse_model = _get_sparse_model()
    return sparse_model != "disabled"


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
