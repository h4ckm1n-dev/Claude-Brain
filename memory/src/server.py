"""FastAPI server for Claude Memory Service.

Thin orchestrator that wires up routers, middleware, WebSocket, and SPA serving.
All endpoint logic lives in src/routers/*.py modules.
"""

import logging
import os
from contextlib import asynccontextmanager
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# Frontend build path
FRONTEND_BUILD = os.path.normpath(os.path.join(os.path.dirname(__file__), "../frontend/dist"))


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

    # Start background scheduler for brain intelligence
    try:
        from .scheduler import start_scheduler
        if start_scheduler():
            logger.info("Background scheduler started for brain intelligence jobs")
        else:
            logger.info("Background scheduler disabled (set SCHEDULER_ENABLED=true to enable)")
    except Exception as e:
        logger.warning(f"Failed to start scheduler: {e}")

    logger.info("Memory Service ready (memories + documents)")
    yield
    # Cleanup on shutdown
    logger.info("Shutting down Memory Service")
    try:
        from .graph import close_driver
        close_driver()
    except Exception:
        pass
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

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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


# Serve React Dashboard (Static Files)
if os.path.exists(FRONTEND_BUILD):
    logger.info(f"Serving React dashboard from {FRONTEND_BUILD}")

    # Mount static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=f"{FRONTEND_BUILD}/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """
        Serve React SPA for all non-API routes.
        API routes are handled by FastAPI, everything else returns index.html
        for client-side routing.
        """
        # Check Accept header to distinguish browser navigation from API calls
        accept_header = request.headers.get('accept', '')
        is_browser_request = 'text/html' in accept_header

        # If browser navigation, always return SPA (let React Router handle it)
        if is_browser_request:
            index_path = os.path.join(FRONTEND_BUILD, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path, media_type='text/html')
            raise HTTPException(status_code=404, detail="Dashboard not built. Run: cd frontend && npm run build")

        # For API requests, check if it's a known API route
        api_prefixes = [
            'memories', 'documents', 'health', 'stats', 'graph', 'context',
            'consolidate', 'migrate', 'embed', 'notifications', 'settings',
            'processes', 'jobs', 'logs', 'scheduler', 'database', 'indexing',
            'docs', 'openapi.json', 'brain/'  # Changed to 'brain/' to avoid blocking brain.svg
        ]
        if any(full_path.startswith(prefix) for prefix in api_prefixes):
            raise HTTPException(status_code=404, detail="API route not found")

        # Check if it's a specific file request (e.g., /brain.svg, /manifest.json)
        file_path = os.path.join(FRONTEND_BUILD, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)

        # Unknown route
        raise HTTPException(status_code=404, detail="Not found")
else:
    logger.warning(f"Frontend build not found at {FRONTEND_BUILD}. Dashboard not available.")
    logger.warning("To build the dashboard, run: cd frontend && npm run build")


# Run server
if __name__ == "__main__":
    uvicorn.run(
        "src.server:app",
        host="0.0.0.0",
        port=8100,
        reload=False,
        log_level="info"
    )
