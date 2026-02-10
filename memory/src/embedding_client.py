"""Embedding client — HTTP-first with local-model fallback.

If EMBEDDING_SERVICE_URL is set, all calls go over HTTP to the standalone
embedding service.  Otherwise, models are loaded in-process (same behaviour
as the original monolith).
"""

import hashlib
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
EMBEDDING_SERVICE_URL: str | None = os.environ.get("EMBEDDING_SERVICE_URL")

DENSE_MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"
SPARSE_MODEL_NAME = "Qdrant/bm42-all-minilm-l6-v2-attentions"
RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
EMBEDDING_DIM = 768

# ---------------------------------------------------------------------------
# Module-level HTTP client (connection-pooled, lazy-initialised)
# ---------------------------------------------------------------------------
_http_client: httpx.Client | None = None


def _get_http_client() -> httpx.Client:
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(
            base_url=EMBEDDING_SERVICE_URL,
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
    return _http_client


# ---------------------------------------------------------------------------
# Local-model fallback singletons (only used when EMBEDDING_SERVICE_URL unset)
# ---------------------------------------------------------------------------
_dense_model = None
_sparse_model = None   # None = not loaded, "disabled" = failed
_reranker = None        # None = not loaded, "disabled" = failed

# Simple LRU-style embedding cache (local mode only)
_embedding_cache: dict[str, list[float]] = {}
_CACHE_MAX_SIZE = 512


def _cache_key(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _get_cached(text: str) -> Optional[list[float]]:
    return _embedding_cache.get(_cache_key(text))


def _set_cached(text: str, embedding: list[float]) -> None:
    if len(_embedding_cache) >= _CACHE_MAX_SIZE:
        oldest = next(iter(_embedding_cache))
        del _embedding_cache[oldest]
    _embedding_cache[_cache_key(text)] = embedding


def _local_dense_model():
    global _dense_model
    if _dense_model is None:
        logger.info("Loading dense model locally: %s", DENSE_MODEL_NAME)
        from sentence_transformers import SentenceTransformer
        _dense_model = SentenceTransformer(
            DENSE_MODEL_NAME, trust_remote_code=True
        )
        logger.info("Dense model loaded (%d dims)", EMBEDDING_DIM)
    return _dense_model


def _local_sparse_model():
    global _sparse_model
    if _sparse_model is None:
        try:
            logger.info("Loading sparse model locally: %s", SPARSE_MODEL_NAME)
            from fastembed import SparseTextEmbedding
            _sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL_NAME)
            logger.info("Sparse model loaded (BM42)")
        except Exception as exc:
            logger.warning("Sparse model unavailable: %s", exc)
            _sparse_model = "disabled"
    return _sparse_model


def _local_reranker():
    global _reranker
    if _reranker is None:
        try:
            logger.info("Loading reranker locally: %s", RERANK_MODEL_NAME)
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder(RERANK_MODEL_NAME)
            logger.info("Reranker loaded")
        except Exception as exc:
            logger.warning("Reranker unavailable: %s", exc)
            _reranker = "disabled"
    return _reranker


# ===================================================================
# Public API — same signatures the rest of the codebase expects
# ===================================================================

def embed_text(text: str, include_sparse: bool = False) -> dict:
    """Embed a single document text."""
    if EMBEDDING_SERVICE_URL:
        resp = _get_http_client().post(
            "/embed", json={"text": text, "include_sparse": include_sparse}
        )
        resp.raise_for_status()
        return resp.json()

    # --- local fallback ---
    result: dict = {}
    prefixed = f"search_document: {text}"
    cached = _get_cached(prefixed)
    if cached:
        result["dense"] = cached
    else:
        model = _local_dense_model()
        embedding = model.encode(prefixed, convert_to_numpy=True)
        result["dense"] = embedding.tolist()
        _set_cached(prefixed, result["dense"])

    if include_sparse:
        sparse_model = _local_sparse_model()
        if sparse_model != "disabled":
            try:
                sparse_embs = list(sparse_model.embed([text]))
                if sparse_embs:
                    se = sparse_embs[0]
                    result["sparse"] = {
                        "indices": se.indices.tolist(),
                        "values": se.values.tolist(),
                    }
            except Exception as exc:
                logger.warning("Sparse embedding failed: %s", exc)
    return result


def embed_query(query: str, include_sparse: bool = False) -> dict:
    """Embed a search query (different prefix than document embedding)."""
    if EMBEDDING_SERVICE_URL:
        resp = _get_http_client().post(
            "/embed_query", json={"query": query, "include_sparse": include_sparse}
        )
        resp.raise_for_status()
        return resp.json()

    # --- local fallback ---
    result: dict = {}
    model = _local_dense_model()
    prefixed = f"search_query: {query}"
    embedding = model.encode(prefixed, convert_to_numpy=True)
    result["dense"] = embedding.tolist()

    if include_sparse:
        sparse_model = _local_sparse_model()
        if sparse_model != "disabled":
            try:
                sparse_embs = list(sparse_model.embed([query]))
                if sparse_embs:
                    se = sparse_embs[0]
                    result["sparse"] = {
                        "indices": se.indices.tolist(),
                        "values": se.values.tolist(),
                    }
            except Exception as exc:
                logger.warning("Sparse query embedding failed: %s", exc)
    return result


def embed_texts(texts: list[str], include_sparse: bool = False) -> list[dict]:
    """Embed multiple document texts in a batch."""
    if EMBEDDING_SERVICE_URL:
        resp = _get_http_client().post(
            "/embed_batch", json={"texts": texts, "include_sparse": include_sparse}
        )
        resp.raise_for_status()
        return resp.json()

    # --- local fallback ---
    model = _local_dense_model()
    prefixed = [f"search_document: {t}" for t in texts]
    dense_all = model.encode(prefixed, convert_to_numpy=True, batch_size=32)

    sparse_all = None
    if include_sparse:
        sparse_model = _local_sparse_model()
        if sparse_model != "disabled":
            try:
                sparse_all = list(sparse_model.embed(texts))
            except Exception as exc:
                logger.warning("Batch sparse embedding failed: %s", exc)

    results = []
    for i, dense_emb in enumerate(dense_all):
        entry: dict = {"dense": dense_emb.tolist()}
        if sparse_all and i < len(sparse_all):
            se = sparse_all[i]
            entry["sparse"] = {
                "indices": se.indices.tolist(),
                "values": se.values.tolist(),
            }
        results.append(entry)
    return results


def rerank_texts(query: str, texts: list[str], top_k: int = 10) -> list[float]:
    """Score query-text pairs. Returns a list of float scores (same order as input)."""
    if not texts:
        return []

    if EMBEDDING_SERVICE_URL:
        resp = _get_http_client().post(
            "/rerank", json={"query": query, "texts": texts, "top_k": top_k}
        )
        resp.raise_for_status()
        return resp.json()["scores"]

    # --- local fallback ---
    reranker = _local_reranker()
    if reranker == "disabled":
        return [0.0] * len(texts)
    pairs = [[query, t] for t in texts]
    scores = reranker.predict(pairs)
    return [float(s) for s in scores]


def get_embedding_dim() -> int:
    return EMBEDDING_DIM


def is_sparse_enabled() -> bool:
    if EMBEDDING_SERVICE_URL:
        try:
            resp = _get_http_client().get("/config")
            resp.raise_for_status()
            return resp.json().get("sparse_enabled", False)
        except Exception:
            return False
    sparse_model = _local_sparse_model()
    return sparse_model != "disabled"


def is_reranker_enabled() -> bool:
    if EMBEDDING_SERVICE_URL:
        try:
            resp = _get_http_client().get("/config")
            resp.raise_for_status()
            return resp.json().get("reranker_enabled", False)
        except Exception:
            return False
    reranker = _local_reranker()
    return reranker != "disabled"
