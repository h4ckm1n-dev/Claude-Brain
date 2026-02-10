# Embedding Service — ML models only
# Serves dense (nomic), sparse (BM42), and reranker (cross-encoder)
FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (only what the embedding service needs)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download ML models at build time (cached in image layer)
# Dense model: nomic-embed-text-v1.5 (768 dims, ~500MB)
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
print('Downloading nomic-embed-text-v1.5...'); \
SentenceTransformer('nomic-ai/nomic-embed-text-v1.5', trust_remote_code=True); \
print('Dense model downloaded successfully')"

# Sparse model: BM42 for hybrid search (~100MB)
RUN python -c "\
from fastembed import SparseTextEmbedding; \
print('Downloading BM42 sparse model...'); \
SparseTextEmbedding(model_name='Qdrant/bm42-all-minilm-l6-v2-attentions'); \
print('Sparse model downloaded successfully')" || \
    echo "Sparse model download failed (optional)"

# Cross-encoder reranker model (~50MB)
RUN python -c "\
from sentence_transformers import CrossEncoder; \
print('Downloading cross-encoder reranker...'); \
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2'); \
print('Reranker downloaded successfully')" || \
    echo "Reranker download failed (optional)"

# Copy only the service code needed (with package __init__.py files)
COPY src/__init__.py ./src/__init__.py
COPY src/services/ ./src/services/

EXPOSE 8102

CMD ["uvicorn", "src.services.embedding_app:app", "--host", "0.0.0.0", "--port", "8102"]
