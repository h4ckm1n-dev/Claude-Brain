# Multi-stage build: Frontend + Backend in one image
# Stage 1: Build React dashboard
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install --legacy-peer-deps || npm install --force

# Copy frontend source
COPY frontend/ ./

# Build production bundle
RUN npm run build

# Stage 2: Python backend + serve frontend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download embedding models at build time (cached in image layer)
# Dense model: nomic-embed-text-v1.5 (768 dims, ~500MB)
RUN python -c "from sentence_transformers import SentenceTransformer; print('Downloading nomic-embed-text-v1.5...'); SentenceTransformer('nomic-ai/nomic-embed-text-v1.5', trust_remote_code=True); print('Model downloaded successfully')" || \
    python -c "from sentence_transformers import SentenceTransformer; print('Falling back to all-MiniLM-L6-v2...'); SentenceTransformer('all-MiniLM-L6-v2'); print('Fallback model downloaded')"

# Sparse model: BM42 for hybrid search (~100MB) - optional, continues on failure
RUN python -c "from fastembed import SparseTextEmbedding; print('Downloading BM42 sparse model...'); SparseTextEmbedding(model_name='Qdrant/bm42-all-minilm-l6-v2-attentions'); print('Sparse model downloaded successfully')" || \
    echo "Sparse model download failed (optional) - hybrid search will fall back to dense-only"

# Cross-encoder reranker model (~50MB) - for improved search precision
RUN python -c "from sentence_transformers import CrossEncoder; print('Downloading cross-encoder reranker...'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2'); print('Reranker downloaded successfully')" || \
    echo "Reranker download failed (optional) - search will work without reranking"

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create data directory
RUN mkdir -p /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8100/health || exit 1

EXPOSE 8100

# Info message about dashboard
RUN echo "✅ Dashboard available at http://localhost:8100 after container starts"

CMD ["python", "-m", "src.server"]
