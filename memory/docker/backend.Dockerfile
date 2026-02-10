# Shared base image for API and Worker services
# ML models are in the embedding service — this image is lean
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

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create data directory
RUN mkdir -p /app/data

# When EMBEDDING_SERVICE_URL is set, all embedding/reranking calls go over
# HTTP to the standalone embedding service.  When unset, models are loaded
# in-process (backward-compatible monolith mode).
ENV EMBEDDING_SERVICE_URL=""

EXPOSE 8100

CMD ["python", "-m", "src.server"]
