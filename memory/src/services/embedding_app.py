"""Standalone Embedding Service.

Loads ML models once at startup and serves embeddings + reranking over HTTP.
Models: nomic-embed-text-v1.5 (dense), BM42 (sparse), ms-marco-MiniLM (reranker).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model singletons (loaded once at startup)
# ---------------------------------------------------------------------------
DENSE_MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"
SPARSE_MODEL_NAME = "Qdrant/bm42-all-minilm-l6-v2-attentions"
RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
EMBEDDING_DIM = 768

_dense_model = None
_sparse_model = None  # None = not loaded, "disabled" = failed
_reranker = None       # None = not loaded, "disabled" = failed


def _load_models():
    global _dense_model, _sparse_model, _reranker

    # Dense model (required)
    logger.info("Loading dense model: %s", DENSE_MODEL_NAME)
    from sentence_transformers import SentenceTransformer
    _dense_model = SentenceTransformer(DENSE_MODEL_NAME, trust_remote_code=True)
    logger.info("Dense model loaded (%d dims)", EMBEDDING_DIM)

    # Sparse model (optional)
    try:
        logger.info("Loading sparse model: %s", SPARSE_MODEL_NAME)
        from fastembed import SparseTextEmbedding
        _sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL_NAME)
        logger.info("Sparse model loaded (BM42)")
    except Exception as exc:
        logger.warning("Sparse model unavailable: %s", exc)
        _sparse_model = "disabled"

    # Reranker (optional)
    try:
        logger.info("Loading reranker: %s", RERANK_MODEL_NAME)
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(RERANK_MODEL_NAME)
        logger.info("Reranker loaded")
    except Exception as exc:
        logger.warning("Reranker unavailable: %s", exc)
        _reranker = "disabled"


# ---------------------------------------------------------------------------
# FastAPI lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_models()
    yield


app = FastAPI(title="Embedding Service", version="1.0.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class EmbedRequest(BaseModel):
    text: str
    include_sparse: bool = False


class EmbedQueryRequest(BaseModel):
    query: str
    include_sparse: bool = False


class EmbedBatchRequest(BaseModel):
    texts: list[str]
    include_sparse: bool = False
    batch_size: int = Field(default=32, ge=1, le=256)


class RerankRequest(BaseModel):
    query: str
    texts: list[str]
    top_k: int = Field(default=10, ge=1)


class SparseResult(BaseModel):
    indices: list[int]
    values: list[float]


class EmbedResponse(BaseModel):
    dense: list[float]
    sparse: SparseResult | None = None


class RerankResponse(BaseModel):
    scores: list[float]


class ConfigResponse(BaseModel):
    embedding_dim: int
    dense_model: str
    sparse_enabled: bool
    reranker_enabled: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _sparse_embed(texts: list[str]) -> list[dict | None]:
    """Return sparse embeddings for a list of texts, or None per-text on failure."""
    if _sparse_model is None or _sparse_model == "disabled":
        return [None] * len(texts)
    try:
        results = list(_sparse_model.embed(texts))
        return [
            {"indices": r.indices.tolist(), "values": r.values.tolist()}
            for r in results
        ]
    except Exception as exc:
        logger.warning("Sparse embedding failed: %s", exc)
        return [None] * len(texts)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/embed", response_model=EmbedResponse)
def embed_document(req: EmbedRequest):
    """Embed a single document (uses 'search_document: ' prefix)."""
    if _dense_model is None:
        raise HTTPException(503, "Dense model not loaded")
    prefixed = f"search_document: {req.text}"
    dense = _dense_model.encode(prefixed, convert_to_numpy=True).tolist()
    sparse = None
    if req.include_sparse:
        sparse_results = _sparse_embed([req.text])
        sparse = sparse_results[0]
    return EmbedResponse(
        dense=dense,
        sparse=SparseResult(**sparse) if sparse else None,
    )


@app.post("/embed_query", response_model=EmbedResponse)
def embed_query(req: EmbedQueryRequest):
    """Embed a search query (uses 'search_query: ' prefix)."""
    if _dense_model is None:
        raise HTTPException(503, "Dense model not loaded")
    prefixed = f"search_query: {req.query}"
    dense = _dense_model.encode(prefixed, convert_to_numpy=True).tolist()
    sparse = None
    if req.include_sparse:
        sparse_results = _sparse_embed([req.query])
        sparse = sparse_results[0]
    return EmbedResponse(
        dense=dense,
        sparse=SparseResult(**sparse) if sparse else None,
    )


@app.post("/embed_batch", response_model=list[EmbedResponse])
def embed_batch(req: EmbedBatchRequest):
    """Embed multiple documents in a batch."""
    if _dense_model is None:
        raise HTTPException(503, "Dense model not loaded")
    if not req.texts:
        return []
    prefixed = [f"search_document: {t}" for t in req.texts]
    dense_all = _dense_model.encode(
        prefixed, convert_to_numpy=True, batch_size=req.batch_size
    )
    sparse_all = (
        _sparse_embed(req.texts) if req.include_sparse else [None] * len(req.texts)
    )
    results = []
    for dense_vec, sparse in zip(dense_all, sparse_all):
        results.append(EmbedResponse(
            dense=dense_vec.tolist(),
            sparse=SparseResult(**sparse) if sparse else None,
        ))
    return results


@app.post("/rerank", response_model=RerankResponse)
def rerank(req: RerankRequest):
    """Score query-text pairs with the cross-encoder reranker."""
    if _reranker is None or _reranker == "disabled":
        raise HTTPException(503, "Reranker not loaded")
    if not req.texts:
        return RerankResponse(scores=[])
    pairs = [[req.query, t] for t in req.texts]
    scores = _reranker.predict(pairs)
    return RerankResponse(scores=[float(s) for s in scores])


@app.get("/health")
def health():
    return {
        "status": "ok",
        "dense_model": _dense_model is not None,
        "sparse_model": _sparse_model is not None and _sparse_model != "disabled",
        "reranker": _reranker is not None and _reranker != "disabled",
    }


@app.get("/config", response_model=ConfigResponse)
def config():
    return ConfigResponse(
        embedding_dim=EMBEDDING_DIM,
        dense_model=DENSE_MODEL_NAME,
        sparse_enabled=_sparse_model is not None and _sparse_model != "disabled",
        reranker_enabled=_reranker is not None and _reranker != "disabled",
    )
