"""FastAPI server for Claude Memory Service.

Thin orchestrator that wires up routers, middleware, WebSocket, and CORS.
Frontend serving is handled by Nginx (docker/frontend.Dockerfile).
Background scheduler is handled by the worker (src/worker.py).
"""

import logging
import os
from contextlib import asynccontextmanager
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from . import collections
from . import documents
from .server_deps import manager

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize collections on startup."""
    logger.info("Starting Claude Memory Service...")
    collections.init_collections()

    # Initialize documents collection (separate from memories)
    documents.init_documents_collection()

    # Validate embedding dimensions match Qdrant collection
    try:
        from .embeddings import validate_embedding_config
        validation = validate_embedding_config()
        if not validation.get("valid", True):
            logger.error(f"EMBEDDING VALIDATION FAILED: {validation['message']}")
        else:
            logger.info(f"Embedding validation: {validation['message']}")
    except Exception as e:
        logger.warning(f"Embedding validation skipped: {e}")

    # Start background scheduler if enabled (disabled by default in microservice mode)
    scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"
    if scheduler_enabled:
        try:
            from .scheduler import start_scheduler
            if start_scheduler():
                logger.info("Background scheduler started (in-process mode)")
            else:
                logger.info("Background scheduler disabled")
        except Exception as e:
            logger.warning(f"Failed to start scheduler: {e}")

    logger.info("Memory Service ready")
    yield
    # Cleanup on shutdown
    logger.info("Shutting down Memory Service")
    try:
        from .graph import close_driver
        close_driver()
    except Exception:
        pass
    if scheduler_enabled:
        try:
            from .scheduler import stop_scheduler
            stop_scheduler()
        except Exception:
            pass


app = FastAPI(
    title="Claude Memory Service",
    description="Vector database memory storage for Claude Code",
    version="1.0.0",
    lifespan=lifespan
)

# GZip compression for JSON responses (60-80% reduction)
from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS for local development and Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8100",
        "http://127.0.0.1:8100",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all API routers
from .routers import register_routers
register_routers(app)


# WebSocket Endpoint

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time memory updates.

    Clients receive JSON messages with structure:
    {
        "type": "memory_created" | "memory_updated" | "memory_deleted",
        "data": { memory object or id }
    }
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
            # Echo back for heartbeat/ping
            await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Run server
if __name__ == "__main__":
    uvicorn.run(
        "src.server:app",
        host="0.0.0.0",
        port=8100,
        reload=False,
        log_level="info"
    )
