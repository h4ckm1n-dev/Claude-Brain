"""Shared FastAPI app factory for microservices.

Each service uses create_app() to build a FastAPI instance with consistent
middleware, CORS, and optional Qdrant/documents initialization.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

logger = logging.getLogger(__name__)


def create_app(
    title: str,
    routers: list,
    init_qdrant: bool = True,
    init_docs: bool = False,
    include_websocket: bool = False,
) -> FastAPI:
    """Create a configured FastAPI application.

    Args:
        title: Service title for docs.
        routers: List of APIRouter instances to register.
        init_qdrant: Initialize Qdrant collections on startup.
        init_docs: Initialize documents collection on startup.
        include_websocket: Mount the /ws WebSocket endpoint.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(f"Starting {title}...")

        if init_qdrant:
            from .. import collections
            collections.init_collections()

        if init_docs:
            from .. import documents
            documents.init_documents_collection()

        # Validate embeddings
        try:
            from ..embeddings import validate_embedding_config
            validation = validate_embedding_config()
            if not validation.get("valid", True):
                logger.error(f"EMBEDDING VALIDATION FAILED: {validation['message']}")
            else:
                logger.info(f"Embedding validation: {validation['message']}")
        except Exception as e:
            logger.warning(f"Embedding validation skipped: {e}")

        logger.info(f"{title} ready")
        yield

        # Cleanup
        logger.info(f"Shutting down {title}")
        try:
            from ..graph import close_driver
            close_driver()
        except Exception:
            pass

    app = FastAPI(title=title, lifespan=lifespan)

    # GZip compression for JSON responses
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # CORS — allow dashboard and Vite dev server
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

    for router in routers:
        app.include_router(router)

    # Health endpoint for Docker health checks
    @app.get("/health")
    async def health():
        return {"status": "ok", "service": title}

    return app
