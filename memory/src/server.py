"""FastAPI server for Claude Memory Service."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import json
from qdrant_client import models

from .models import (
    Memory, MemoryCreate, MemoryUpdate, MemoryType,
    SearchQuery, SearchResult, EmbedRequest, EmbedResponse,
    LinkRequest, HealthResponse, StatsResponse, RelationType,
    MigrationResult, utc_now
)
from . import collections
from .embeddings import embed_text, get_embedding_dim, is_sparse_enabled
from . import notifications as notif_module
from . import suggestions as suggestions_module
from . import documents
from .quality import validate_memory_quality, QualityValidationError, get_quality_suggestions
from .enhancements import check_duplicate_before_store, suggest_tags_from_similar, get_template_hints

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


# WebSocket Connection Manager
class ConnectionManager:
    """Manages active WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return

        message_str = json.dumps(message)
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)


manager = ConnectionManager()


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


# Health & Status Endpoints

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and Qdrant connection."""
    from .graph import is_graph_enabled
    from . import documents

    healthy, status = collections.check_health()

    if not healthy:
        raise HTTPException(status_code=503, detail=f"Qdrant unhealthy: {status}")

    stats = collections.get_stats()
    doc_stats = documents.get_document_stats()

    return HealthResponse(
        status="healthy",
        qdrant=status,
        collections=["memories", "documents"],
        memory_count=stats["total_memories"],
        document_chunks=doc_stats.get("total_chunks", 0),
        hybrid_search_enabled=stats.get("hybrid_search_enabled", False),
        graph_enabled=is_graph_enabled(),
        embedding_model="nomic-ai/nomic-embed-text-v1.5",
        embedding_dim=stats.get("embedding_dim", get_embedding_dim())
    )


@app.get("/health/detailed")
async def detailed_health_check():
    """Get detailed health information about all system components."""
    from .graph import is_graph_enabled
    from datetime import datetime
    import time

    start_time = time.time()
    health_info = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": 0,  # Would need to track this globally
        "dependencies": {},
        "features": {},
        "performance": {}
    }

    # Check Qdrant
    try:
        qdrant_healthy, qdrant_status = collections.check_health()
        client = collections.get_client()
        collection_info = client.get_collection(collections.COLLECTION_NAME)

        health_info["dependencies"]["qdrant"] = {
            "status": "healthy" if qdrant_healthy else "unhealthy",
            "message": qdrant_status,
            "details": {
                "host": collections.QDRANT_HOST,
                "port": collections.QDRANT_PORT,
                "collection": collections.COLLECTION_NAME,
                "points_count": collection_info.points_count
            }
        }
    except Exception as e:
        health_info["dependencies"]["qdrant"] = {
            "status": "unhealthy",
            "message": str(e),
            "details": {}
        }
        health_info["status"] = "degraded"

    # Check Neo4j (if enabled)
    if is_graph_enabled():
        try:
            from .graph import get_graph_stats
            graph_stats = get_graph_stats()
            health_info["dependencies"]["neo4j"] = {
                "status": "healthy",
                "message": "connected",
                "details": graph_stats
            }
        except Exception as e:
            health_info["dependencies"]["neo4j"] = {
                "status": "unhealthy",
                "message": str(e),
                "details": {}
            }
            health_info["status"] = "degraded"
    else:
        health_info["dependencies"]["neo4j"] = {
            "status": "disabled",
            "message": "Neo4j not configured",
            "details": {}
        }

    # Feature status
    health_info["features"] = {
        "hybrid_search": is_sparse_enabled(),
        "graph_relationships": is_graph_enabled(),
        "semantic_cache": True,  # Always enabled
        "cross_encoder_reranking": True,  # Check if reranker is loaded
        "learned_fusion": os.getenv("USE_LEARNED_FUSION", "false").lower() == "true",
        "query_understanding": os.getenv("USE_QUERY_UNDERSTANDING", "false").lower() == "true",
        "websocket": len(manager.active_connections) > 0
    }

    # Performance metrics
    response_time = (time.time() - start_time) * 1000  # Convert to ms
    health_info["performance"] = {
        "health_check_ms": round(response_time, 2),
        "active_websocket_connections": len(manager.active_connections)
    }

    # Try to get cache stats
    try:
        from .cache import get_cache_stats
        cache_stats = get_cache_stats()
        health_info["performance"]["cache"] = cache_stats
    except Exception:
        pass

    return health_info


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get memory collection statistics."""
    stats = collections.get_stats()
    return StatsResponse(**stats)


@app.get("/cache/stats")
async def get_cache_stats():
    """Get query cache statistics."""
    from .cache import get_cache_stats
    return get_cache_stats()


@app.post("/cache/clear")
async def clear_cache():
    """Clear the query cache."""
    from .cache import clear_cache
    client = collections.get_client()
    cleared = clear_cache(client)
    return {"status": "cleared", "entries_removed": cleared}


# ============================================================================
# Memory Enhancement Endpoints
# ============================================================================

@app.post("/memories/draft")
async def create_memory_draft(data: MemoryCreate):
    """
    Preview memory quality and get enhancement suggestions before storing.

    This endpoint validates memory quality and provides actionable suggestions
    without actually storing the memory. Useful for:
    - Pre-flight validation in UI
    - Getting tag suggestions
    - Detecting potential duplicates
    - Seeing quality score before committing

    Returns:
        - quality_score: 0-100 score
        - warnings: List of quality issues
        - suggested_tags: Additional tags from similar memories
        - duplicate_warning: Info about similar existing memories
        - template_example: Example of high-quality memory for this type
        - recommendation: "ready" | "needs_improvement" | "blocked"
    """
    try:
        # Check for duplicates
        duplicate_info = check_duplicate_before_store(data)

        # Get tag suggestions
        suggested_tags = suggest_tags_from_similar(
            content=data.content,
            existing_tags=data.tags or [],
            limit=5  # More suggestions in draft mode
        )

        # Calculate quality score
        from .quality import calculate_quality_score
        score, warnings = calculate_quality_score(data)

        # Get template hints
        template_hints = get_template_hints(data.type)

        # Determine recommendation
        from .quality import MIN_QUALITY_SCORE
        if score >= MIN_QUALITY_SCORE:
            recommendation = "ready"
        elif score >= MIN_QUALITY_SCORE - 10:
            recommendation = "needs_improvement"
        else:
            recommendation = "blocked"

        response = {
            "quality_score": score,
            "warnings": warnings,
            "suggested_tags": suggested_tags,
            "recommendation": recommendation,
            "min_required_score": MIN_QUALITY_SCORE,
        }

        # Add duplicate warning if found
        if duplicate_info:
            response["duplicate_warning"] = {
                "message": duplicate_info["message"],
                "existing_id": duplicate_info["existing_id"],
                "existing_content": duplicate_info["existing_content"],
                "similarity": duplicate_info["similarity_score"],
                "suggestion": duplicate_info["suggestion"]
            }

        # Add template example and structure if available
        if template_hints:
            if "example" in template_hints:
                response["template_example"] = template_hints["example"]
            if "suggested_structure" in template_hints:
                response["template_structure"] = template_hints["suggested_structure"]

        # Add quality tips
        response["quality_tips"] = get_quality_suggestions(data.type)

        return response

    except Exception as e:
        logger.error(f"Draft creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Embedding Endpoint

@app.post("/embed", response_model=EmbedResponse)
async def generate_embedding(request: EmbedRequest):
    """Generate embedding for text."""
    result = embed_text(request.text, include_sparse=request.include_sparse)
    return EmbedResponse(
        dense=result["dense"],
        sparse=result.get("sparse"),
        dimensions=get_embedding_dim()
    )


# Memory CRUD Endpoints

@app.post("/memories", response_model=Memory)
async def create_memory(data: MemoryCreate):
    """Store a new memory with quality validation and enhancement suggestions."""
    try:
        # ===== ENHANCEMENT 1: SEMANTIC DEDUPLICATION =====
        duplicate_info = check_duplicate_before_store(data)
        if duplicate_info:
            logger.warning(
                f"Duplicate detected: {duplicate_info['message']} "
                f"(existing: {duplicate_info['existing_id']}, similarity: {duplicate_info['similarity_score']})"
            )
            # Note: We warn but don't block - user may want to store anyway
            # Future: Could add strict mode to reject duplicates

        # ===== ENHANCEMENT 2: TAG SUGGESTIONS =====
        suggested_tags = suggest_tags_from_similar(
            content=data.content,
            existing_tags=data.tags or [],
            limit=3
        )
        if suggested_tags:
            logger.info(f"Tag suggestions for new memory: {suggested_tags}")

        # QUALITY VALIDATION
        try:
            is_valid, score, warnings = validate_memory_quality(data)

            # Add quality metadata to response headers
            if warnings:
                logger.info(f"Memory quality: {score}/100 with {len(warnings)} warnings")

        except QualityValidationError as e:
            # Quality enforcement is strict and memory failed validation
            suggestions = get_quality_suggestions(data.type)
            template_hints = get_template_hints(data.type)

            # Build enhanced error response
            error_detail = {
                "error": "Memory quality too low",
                "score": e.score,
                "issues": e.warnings,
                "suggestions": suggestions
            }

            # Add template example if available
            if template_hints and "example" in template_hints:
                error_detail["example"] = template_hints["example"]
                error_detail["structure"] = template_hints.get("suggested_structure", "")

            # Add tag suggestions if available
            if suggested_tags:
                error_detail["suggested_tags"] = suggested_tags

            # Add duplicate warning if found
            if duplicate_info:
                error_detail["duplicate_warning"] = {
                    "message": duplicate_info["message"],
                    "existing_id": duplicate_info["existing_id"],
                    "similarity": duplicate_info["similarity_score"]
                }

            raise HTTPException(status_code=422, detail=error_detail)

        # LEGACY QUALITY FILTER: Keep existing checks for backward compatibility
        content = data.content.strip()

        # Reject useless session summaries with no data
        if "session-end" in (data.tags or []):
            if "Duration: unknown" in content and ("Files edited: 0" in content or "Files edited:" not in content):
                raise HTTPException(status_code=400, detail="Session summary contains no useful information")

        # Reject generic/empty content patterns
        useless_patterns = [
            "Duration: unknown.",
            "Session ended (session_end) - Duration: unknown.",
        ]
        if any(content == pattern.strip() for pattern in useless_patterns):
            raise HTTPException(status_code=400, detail="Memory content is too generic/empty")

        # Store memory
        memory = collections.store_memory(data)

        # Broadcast update to WebSocket clients
        await manager.broadcast({
            "type": "memory_created",
            "data": memory.model_dump(mode='json')
        })

        return memory

    except HTTPException:
        raise
    except QualityValidationError as e:
        # Already handled above, but catch again in case
        suggestions = get_quality_suggestions(data.type)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Memory quality too low",
                "score": e.score,
                "issues": e.warnings,
                "suggestions": suggestions
            }
        )
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memories/bulk")
async def bulk_store_memories(memories: list[MemoryCreate]):
    """Store multiple memories in a single operation."""
    results = []
    errors = []

    for i, data in enumerate(memories):
        try:
            memory = collections.store_memory(data)
            results.append({"index": i, "id": memory.id, "status": "success"})
        except Exception as e:
            logger.error(f"Failed to store memory {i}: {e}")
            errors.append({"index": i, "error": str(e)})

    return {
        "stored": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }


@app.post("/memories/search", response_model=list[SearchResult])
async def search_memories(query: SearchQuery):
    """Search memories using semantic similarity."""
    try:
        results = collections.search_memories(query)
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories", response_model=list[Memory])
async def list_memories(
    request: Request,
    type: Optional[str] = None,
    project: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List memories with optional filters."""
    try:
        # Check if this is a browser request (SPA navigation)
        # Browser sends Accept: text/html, API calls send Accept: application/json
        accept_header = request.headers.get('accept', '')
        if 'text/html' in accept_header and 'application/json' not in accept_header:
            # Browser navigation - return SPA
            index_path = os.path.join(FRONTEND_BUILD, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path, media_type='text/html')
            raise HTTPException(status_code=404, detail="Dashboard not built")

        from .collections import get_client, COLLECTION_NAME
        from .models import Memory as MemoryModel

        client = get_client()

        # Build filter conditions
        must_conditions = []
        if type:
            must_conditions.append(
                models.FieldCondition(
                    key="type",
                    match=models.MatchValue(value=type)
                )
            )
        if project:
            must_conditions.append(
                models.FieldCondition(
                    key="project",
                    match=models.MatchValue(value=project)
                )
            )

        # Use scroll to get memories
        scroll_filter = None
        if must_conditions:
            scroll_filter = models.Filter(must=must_conditions)

        records, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=scroll_filter,
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )

        # Convert to Memory objects
        memories = []
        for record in records:
            payload = record.payload
            payload["id"] = str(record.id)
            memories.append(MemoryModel(**payload))

        return memories
    except Exception as e:
        logger.error(f"Failed to list memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{memory_id}", response_model=Memory)
async def get_memory(memory_id: str):
    """Get a single memory by ID."""
    memory = collections.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@app.patch("/memories/{memory_id}", response_model=Memory)
async def update_memory(memory_id: str, update: MemoryUpdate):
    """Update an existing memory."""
    memory = collections.update_memory(memory_id, update)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    # Broadcast update to WebSocket clients
    await manager.broadcast({
        "type": "memory_updated",
        "data": memory.model_dump(mode='json')
    })

    return memory


@app.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory by ID."""
    success = collections.delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")

    # Broadcast update to WebSocket clients
    await manager.broadcast({
        "type": "memory_deleted",
        "data": {"id": memory_id}
    })

    return {"status": "deleted", "id": memory_id}


# Special Operations

@app.post("/memories/{memory_id}/resolve", response_model=Memory)
async def resolve_error(memory_id: str, solution: str = Query(..., description="Solution that fixed the error")):
    """Mark an error memory as resolved with a solution."""
    memory = collections.mark_resolved(memory_id, solution)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@app.post("/memories/link")
async def link_memories(request: LinkRequest):
    """Create a relationship between two memories."""
    success = collections.link_memories(
        request.source_id,
        request.target_id,
        request.relation_type
    )
    if not success:
        raise HTTPException(status_code=404, detail="Source memory not found")
    return {"status": "linked", "source": request.source_id, "target": request.target_id}


# Unified Search Endpoint

@app.get("/search/unified")
async def unified_search(
    query: str = Query(..., description="Search query"),
    search_memories: bool = Query(default=True, description="Include memories in search"),
    search_documents: bool = Query(default=True, description="Include documents in search"),
    memory_limit: int = Query(default=10, description="Maximum memories to return"),
    document_limit: int = Query(default=5, description="Maximum documents to return"),
    type_filter: Optional[str] = Query(default=None, description="Filter memories by type"),
    project: Optional[str] = Query(default=None, description="Filter by project")
):
    """
    Unified search across memories and documents.
    Returns both structured memories and filesystem documents.
    """
    results = {
        "query": query,
        "memories": [],
        "documents": [],
        "total_count": 0
    }

    # Search memories if requested
    if search_memories:
        search_query = SearchQuery(
            query=query,
            type=type_filter,
            project=project,
            limit=memory_limit
        )
        memory_results = collections.search_memories(search_query)
        results["memories"] = [r.model_dump(mode='json') for r in memory_results]

    # Search documents if requested
    if search_documents:
        try:
            doc_results = documents.search_documents(
                query=query,
                limit=document_limit,
                folder=project
            )
            results["documents"] = doc_results
        except Exception as e:
            logger.warning(f"Document search failed: {e}")
            results["documents"] = []

    results["total_count"] = len(results["memories"]) + len(results["documents"])
    return results


# Quality Rating Endpoints

class RatingRequest(BaseModel):
    """Request model for rating a memory."""
    rating: int
    feedback: Optional[str] = None


@app.post("/memories/{memory_id}/rate")
async def rate_memory(memory_id: str, request: RatingRequest):
    """
    Record user quality rating (1-5 stars) for a memory.

    Updates running average of user_rating and stores feedback.
    """
    if request.rating < 1 or request.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    try:
        client = collections.get_client()

        # Get current memory
        memory = collections.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        # Calculate new rating (running average)
        old_count = memory.user_rating_count or 0
        old_rating = memory.user_rating or 0.0
        new_rating = ((old_rating * old_count) + request.rating) / (old_count + 1)

        # Prepare update payload
        update_payload = {
            "user_rating": new_rating,
            "user_rating_count": old_count + 1
        }

        # Store feedback if provided
        if request.feedback:
            user_feedback = memory.user_feedback or []
            user_feedback.append({
                "rating": request.rating,
                "feedback": request.feedback,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            update_payload["user_feedback"] = user_feedback

        # Update memory
        client.set_payload(
            collection_name=collections.COLLECTION_NAME,
            payload=update_payload,
            points=[memory_id]
        )

        # Broadcast update
        await manager.broadcast({
            "type": "memory_rated",
            "data": {
                "memory_id": memory_id,
                "rating": request.rating,
                "new_avg_rating": new_rating,
                "rating_count": old_count + 1
            }
        })

        return {
            "success": True,
            "memory_id": memory_id,
            "new_rating": round(new_rating, 2),
            "rating_count": old_count + 1
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rating failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/quality-leaderboard")
async def get_quality_leaderboard(
    limit: int = Query(default=20, ge=1, le=100),
    memory_type: Optional[str] = Query(default=None)
):
    """Get highest-rated memories (4+ stars, minimum 2 ratings)."""
    try:
        client = collections.get_client()

        # Get all memories (filter in Python for simplicity)
        must_conditions = []
        if memory_type:
            must_conditions.append(
                models.FieldCondition(
                    key="type",
                    match=models.MatchValue(value=memory_type)
                )
            )

        scroll_filter = models.Filter(must=must_conditions) if must_conditions else None

        records, _ = client.scroll(
            collection_name=collections.COLLECTION_NAME,
            scroll_filter=scroll_filter,
            limit=1000,  # Get more to filter
            with_payload=True,
            with_vectors=False
        )

        # Filter and build leaderboard in Python
        leaderboard = []
        for record in records:
            payload = record.payload
            user_rating = payload.get("user_rating")
            rating_count = payload.get("user_rating_count", 0)

            # Only include if rated at least twice and rating >= 4.0
            if user_rating is not None and rating_count >= 2 and user_rating >= 4.0:
                leaderboard.append({
                    "id": str(record.id),
                    "type": payload["type"],
                    "content": payload["content"][:200] + "..." if len(payload["content"]) > 200 else payload["content"],
                    "user_rating": user_rating,
                    "rating_count": rating_count,
                    "tags": payload.get("tags", []),
                    "project": payload.get("project"),
                    "created_at": payload["created_at"]
                })

        # Sort by rating descending
        leaderboard.sort(key=lambda x: x["user_rating"], reverse=True)

        # Limit results
        leaderboard = leaderboard[:limit]

        return {
            "leaderboard": leaderboard,
            "count": len(leaderboard),
            "filter": {"type": memory_type, "limit": limit}
        }

    except Exception as e:
        logger.error(f"Leaderboard query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/quality-report")
async def get_quality_report():
    """Get quality rating distribution across all memories."""
    try:
        client = collections.get_client()

        # Get all memories
        all_records, _ = client.scroll(
            collection_name=collections.COLLECTION_NAME,
            limit=10000,  # Get all
            with_payload=True,
            with_vectors=False
        )

        total_memories = len(all_records)
        rated_memories = []

        for record in all_records:
            payload = record.payload
            if payload.get("user_rating") and payload.get("user_rating_count", 0) > 0:
                rated_memories.append({
                    "rating": payload["user_rating"],
                    "count": payload["user_rating_count"]
                })

        # Calculate statistics
        if rated_memories:
            avg_rating = sum(m["rating"] for m in rated_memories) / len(rated_memories)

            # Rating distribution
            five_star = sum(1 for m in rated_memories if m["rating"] >= 4.5)
            four_star = sum(1 for m in rated_memories if 3.5 <= m["rating"] < 4.5)
            three_star = sum(1 for m in rated_memories if 2.5 <= m["rating"] < 3.5)
            two_star = sum(1 for m in rated_memories if 1.5 <= m["rating"] < 2.5)
            one_star = sum(1 for m in rated_memories if m["rating"] < 1.5)
        else:
            avg_rating = 0
            five_star = four_star = three_star = two_star = one_star = 0

        return {
            "total_memories": total_memories,
            "rated_memories": len(rated_memories),
            "unrated_memories": total_memories - len(rated_memories),
            "coverage": round(len(rated_memories) / total_memories * 100, 1) if total_memories > 0 else 0,
            "avg_rating": round(avg_rating, 2) if avg_rating > 0 else 0,
            "rating_distribution": {
                "5_star": five_star,
                "4_star": four_star,
                "3_star": three_star,
                "2_star": two_star,
                "1_star": one_star
            },
            "total_ratings": sum(m["count"] for m in rated_memories)
        }

    except Exception as e:
        logger.error(f"Quality report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Memory Version Management Endpoints

@app.get("/memories/{memory_id}/versions")
async def get_memory_versions(memory_id: str):
    """
    Get all versions of a memory.

    Returns the current version number and complete version history.
    """
    try:
        memory = collections.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        return {
            "memory_id": memory_id,
            "current_version": memory.current_version,
            "total_versions": len(memory.version_history),
            "versions": [
                {
                    "version_number": v.version_number,
                    "content_preview": v.content[:100] + "..." if len(v.content) > 100 else v.content,
                    "change_type": v.change_type,
                    "change_reason": v.change_reason,
                    "changed_by": v.changed_by,
                    "created_at": v.created_at.isoformat(),
                    "tags": v.tags,
                    "importance_score": v.importance_score
                }
                for v in memory.version_history
            ]
        }

    except Exception as e:
        logger.error(f"Get versions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{memory_id}/versions/{version}")
async def get_specific_version(memory_id: str, version: int):
    """
    Get a specific version of a memory by version number.

    Returns the complete version snapshot including all fields.
    """
    try:
        memory = collections.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        if version < 1 or version > len(memory.version_history):
            raise HTTPException(
                status_code=404,
                detail=f"Version {version} not found. Available versions: 1-{len(memory.version_history)}"
            )

        version_snapshot = memory.version_history[version - 1]

        return {
            "memory_id": memory_id,
            "version": version_snapshot.model_dump(),
            "current_version": memory.current_version
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get specific version failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memories/{memory_id}/versions/{version}/restore")
async def restore_version(memory_id: str, version: int):
    """
    Restore a memory to a previous version.

    Creates a new version snapshot of current state before restoring,
    allowing future restoration if needed.
    """
    try:
        from .models import ChangeType

        client = collections.get_client()
        memory = collections.get_memory(memory_id)

        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        if version < 1 or version > len(memory.version_history):
            raise HTTPException(
                status_code=404,
                detail=f"Version {version} not found. Available versions: 1-{len(memory.version_history)}"
            )

        # Get the target version
        target_version = memory.version_history[version - 1]

        # Create snapshot of current state before restoring
        memory.create_version_snapshot(
            change_type=ChangeType.RESTORED,
            change_reason=f"Restored from version {version}",
            changed_by="user"
        )

        # Restore fields from target version
        memory.content = target_version.content
        memory.importance_score = target_version.importance_score
        memory.tags = target_version.tags.copy()

        # Restore type-specific fields
        if target_version.error_message is not None:
            memory.error_message = target_version.error_message
        if target_version.solution is not None:
            memory.solution = target_version.solution
        if target_version.decision is not None:
            memory.decision = target_version.decision
        if target_version.rationale is not None:
            memory.rationale = target_version.rationale

        memory.updated_at = utc_now()

        # Update in Qdrant
        client.set_payload(
            collection_name=collections.COLLECTION_NAME,
            payload=memory.model_dump(mode='json', exclude={'embedding'}),
            points=[memory_id]
        )

        return {
            "success": True,
            "memory_id": memory_id,
            "restored_to_version": version,
            "new_current_version": memory.current_version,
            "message": f"Successfully restored to version {version}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Restore version failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{memory_id}/versions/{v1}/diff/{v2}")
async def diff_versions(memory_id: str, v1: int, v2: int):
    """
    Compare two versions of a memory.

    Returns detailed diff showing what changed between the two versions.
    """
    try:
        memory = collections.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        max_version = len(memory.version_history)

        if v1 < 1 or v1 > max_version or v2 < 1 or v2 > max_version:
            raise HTTPException(
                status_code=404,
                detail=f"Invalid version numbers. Available versions: 1-{max_version}"
            )

        version1 = memory.version_history[v1 - 1]
        version2 = memory.version_history[v2 - 1]

        # Calculate changes
        content_changed = version1.content != version2.content
        importance_changed = version1.importance_score != version2.importance_score
        tags_added = list(set(version2.tags) - set(version1.tags))
        tags_removed = list(set(version1.tags) - set(version2.tags))

        time_between = (version2.created_at - version1.created_at).total_seconds()

        return {
            "memory_id": memory_id,
            "version1": v1,
            "version2": v2,
            "time_between_seconds": time_between,
            "time_between_human": f"{int(time_between // 3600)}h {int((time_between % 3600) // 60)}m",
            "changes": {
                "content_changed": content_changed,
                "content_length_diff": len(version2.content) - len(version1.content) if content_changed else 0,
                "importance_changed": importance_changed,
                "importance_diff": round(version2.importance_score - version1.importance_score, 3) if importance_changed else 0,
                "tags_added": tags_added,
                "tags_removed": tags_removed,
                "tags_changed": len(tags_added) > 0 or len(tags_removed) > 0
            },
            "v1_summary": {
                "content_preview": version1.content[:100] + "..." if len(version1.content) > 100 else version1.content,
                "change_type": version1.change_type,
                "tags": version1.tags
            },
            "v2_summary": {
                "content_preview": version2.content[:100] + "..." if len(version2.content) > 100 else version2.content,
                "change_type": version2.change_type,
                "tags": version2.tags
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Diff versions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Query Intelligence Endpoint

@app.post("/query/enhance")
async def enhance_query(
    query: str = Query(..., description="Search query to enhance"),
    expand_synonyms: bool = Query(default=True, description="Add synonyms for better recall"),
    correct_typos: bool = Query(default=True, description="Suggest typo corrections")
):
    """
    Apply query intelligence enhancements.

    Enhances search queries with:
    - Synonym expansion for better recall
    - Typo correction suggestions
    - Query routing recommendations

    Example:
        POST /query/enhance?query=dcoker%20erro
        Returns: {
            "original_query": "dcoker erro",
            "enhanced_query": "docker error container bug exception",
            "corrections": [{"original": "dcoker", "suggestion": "docker"}],
            "expansions": ["container", "bug", "exception"],
            "routing": {"strategy": "hybrid", ...}
        }
    """
    try:
        from .query_understanding import apply_query_intelligence

        result = apply_query_intelligence(
            query=query,
            expand_synonyms=expand_synonyms,
            correct_typos=correct_typos
        )

        return result

    except Exception as e:
        logger.error(f"Query enhancement failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Context Endpoint

@app.get("/context/{project}")
async def get_project_context(
    project: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours to look back"),
    types: Optional[str] = Query(default=None, description="Comma-separated memory types"),
    include_documents: bool = Query(default=True, description="Include relevant documents"),
    document_limit: int = Query(default=5, ge=0, le=20, description="Max documents to return")
):
    """Get relevant context memories and documents for a project."""
    type_list = None
    if types:
        type_list = [MemoryType(t.strip()) for t in types.split(",")]

    context = collections.get_context(
        project=project if project != "_all" else None,
        hours=hours,
        types=type_list,
        include_documents=include_documents,
        document_limit=document_limit
    )
    return context


@app.get("/context")
async def get_global_context(
    hours: int = Query(default=24, ge=1, le=168),
    types: Optional[str] = Query(default=None),
    include_documents: bool = Query(default=True, description="Include relevant documents"),
    document_limit: int = Query(default=5, ge=0, le=20, description="Max documents to return")
):
    """Get recent context memories and documents across all projects."""
    type_list = None
    if types:
        type_list = [MemoryType(t.strip()) for t in types.split(",")]

    context = collections.get_context(
        hours=hours,
        types=type_list,
        include_documents=include_documents,
        document_limit=document_limit
    )
    return context


# Proactive Surfacing Endpoint

class SuggestRequest(BaseModel):
    """Request model for memory suggestions."""
    project: Optional[str] = None
    keywords: Optional[list[str]] = None
    current_files: Optional[list[str]] = None
    git_branch: Optional[str] = None
    limit: int = 5


@app.post("/memories/suggest")
async def suggest_memories(request: SuggestRequest):
    """
    Proactively suggest relevant memories based on current context.

    This endpoint is designed to be called at conversation start to surface
    potentially useful memories without explicit search queries.

    Returns memories ranked by:
    - Semantic relevance to context
    - Importance with time decay
    - Access frequency
    - Unresolved errors (high priority)
    """
    try:
        suggestions = collections.suggest_memories(
            project=request.project,
            keywords=request.keywords,
            current_files=request.current_files,
            git_branch=request.git_branch,
            limit=request.limit
        )

        # Format for response
        return {
            "suggestions": [
                {
                    "id": s["memory"].id,
                    "type": s["memory"].type.value,
                    "content": s["memory"].content[:200] + "..." if len(s["memory"].content) > 200 else s["memory"].content,
                    "tags": s["memory"].tags,
                    "project": s["memory"].project,
                    "relevance_score": round(s["relevance_score"], 3),
                    "decay_score": round(s["decay_score"], 3),
                    "combined_score": round(s["combined_score"], 3),
                    "reason": s["reason"],
                    "access_count": s["memory"].access_count,
                    "created_at": s["memory"].created_at.isoformat()
                }
                for s in suggestions
            ],
            "count": len(suggestions)
        }
    except Exception as e:
        logger.error(f"Suggest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Migration Endpoint

@app.post("/migrate", response_model=MigrationResult)
async def migrate_collection():
    """Migrate collection to new embedding dimensions.

    This re-embeds all memories with the new embedding model
    and recreates the collection with proper vector dimensions.
    """
    try:
        result = collections.migrate_collection()
        return MigrationResult(**result)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Consolidation Endpoints

@app.post("/consolidate")
async def consolidate_memories(
    older_than_days: int = Query(default=7, ge=1, le=30),
    dry_run: bool = Query(default=False)
):
    """Run memory consolidation pipeline.

    1. Find clusters of similar old memories
    2. Consolidate clusters into single semantic memories
    3. Archive remaining low-value old memories

    Args:
        older_than_days: Process memories older than this (default 7)
        dry_run: If True, analyze only without making changes
    """
    from .consolidation import run_consolidation

    try:
        client = collections.get_client()
        result = run_consolidation(
            client,
            collections.COLLECTION_NAME,
            older_than_days=older_than_days,
            dry_run=dry_run
        )
        return result.model_dump()
    except Exception as e:
        logger.error(f"Consolidation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/consolidate/preview")
async def preview_consolidation(
    older_than_days: int = Query(default=7, ge=1, le=30)
):
    """Preview what would be consolidated without making changes."""
    from .consolidation import find_consolidation_clusters, archive_old_memories

    try:
        client = collections.get_client()

        # Find clusters
        clusters = find_consolidation_clusters(
            client,
            collections.COLLECTION_NAME,
            older_than_days
        )

        # Preview archival
        archive_preview = archive_old_memories(
            client,
            collections.COLLECTION_NAME,
            older_than_days,
            dry_run=True
        )

        return {
            "clusters": [
                {
                    "memory_ids": c.memory_ids,
                    "suggested_type": c.suggested_type.value,
                    "suggested_tags": c.suggested_tags,
                    "size": len(c.memory_ids)
                }
                for c in clusters
            ],
            "archive_candidates": archive_preview.archived,
            "would_keep": archive_preview.kept,
            "total_analyzed": archive_preview.analyzed
        }
    except Exception as e:
        logger.error(f"Consolidation preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memories/{memory_id}/archive")
async def archive_memory(memory_id: str):
    """Manually archive a specific memory."""
    try:
        client = collections.get_client()
        from datetime import datetime, timezone

        client.set_payload(
            collection_name=collections.COLLECTION_NAME,
            payload={
                "archived": True,
                "archived_at": datetime.now(timezone.utc).isoformat()
            },
            points=[memory_id]
        )
        return {"status": "archived", "id": memory_id}
    except Exception as e:
        logger.error(f"Archive failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memories/{memory_id}/pin")
async def pin_memory(memory_id: str):
    """Pin a memory so it never decays in importance."""
    try:
        client = collections.get_client()

        client.set_payload(
            collection_name=collections.COLLECTION_NAME,
            payload={
                "pinned": True,
                "importance_score": 1.0
            },
            points=[memory_id]
        )
        return {"status": "pinned", "id": memory_id}
    except Exception as e:
        logger.error(f"Pin failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memories/{memory_id}/unpin")
async def unpin_memory(memory_id: str):
    """Unpin a memory to allow normal decay."""
    try:
        client = collections.get_client()

        client.set_payload(
            collection_name=collections.COLLECTION_NAME,
            payload={
                "pinned": False
            },
            points=[memory_id]
        )
        return {"status": "unpinned", "id": memory_id}
    except Exception as e:
        logger.error(f"Unpin failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Adaptive Forgetting Endpoints (FadeMem-inspired)

@app.post("/forgetting/update")
async def update_memory_strengths(
    max_updates: Optional[int] = Query(default=None, description="Maximum memories to update (None = all)")
):
    """Manually trigger memory strength update for all active memories.

    This implements FadeMem-inspired adaptive forgetting where:
    - High-importance memories decay slower (differential decay)
    - Frequently accessed memories are reinforced
    - Weak memories are automatically archived when strength < 0.15
    - Optional purging when strength < 0.05 (if MEMORY_PURGE_ENABLED=true)

    Args:
        max_updates: Maximum number of memories to update (default: all)

    Returns:
        Statistics about the update operation including:
        - total_processed: Number of memories processed
        - updated: Number of memories with updated strength
        - archived: Number of memories archived due to low strength
        - purged: Number of memories deleted (if purging enabled)
        - avg_strength: Average memory strength across all processed
    """
    from .forgetting import update_all_memory_strengths

    try:
        client = collections.get_client()
        result = update_all_memory_strengths(
            client,
            collections.COLLECTION_NAME,
            batch_size=100,
            max_updates=max_updates
        )
        return result
    except Exception as e:
        logger.error(f"Memory strength update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/forgetting/stats")
async def get_forgetting_stats():
    """Get statistics about memory strength distribution.

    Returns detailed statistics including:
    - Total active memories
    - Average/median/min/max memory strength
    - Distribution by memory tier (episodic/semantic/procedural)
    - Number of memories below archive/purge thresholds
    - Average decay rate
    - Current configuration (thresholds, purge enabled)
    """
    from .forgetting import get_forgetting_stats

    try:
        client = collections.get_client()
        stats = get_forgetting_stats(client, collections.COLLECTION_NAME)
        return stats
    except Exception as e:
        logger.error(f"Failed to get forgetting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/forgetting/weak")
async def get_weak_memories(
    strength_threshold: float = Query(default=0.3, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=1, le=200)
):
    """Get memories with low strength that are candidates for archival.

    Args:
        strength_threshold: Strength threshold (0.0-1.0, default: 0.3)
        limit: Maximum number of results (default: 50)

    Returns:
        List of weak memories with metadata including:
        - id, content preview, type
        - memory_strength, decay_rate
        - access_count, created_at, last_accessed
    """
    from .forgetting import get_weak_memories

    try:
        client = collections.get_client()
        weak = get_weak_memories(
            client,
            collections.COLLECTION_NAME,
            strength_threshold=strength_threshold,
            limit=limit
        )
        return weak
    except Exception as e:
        logger.error(f"Failed to get weak memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memories/{memory_id}/reinforce")
async def reinforce_memory(
    memory_id: str,
    boost_amount: float = Query(default=0.2, ge=0.0, le=0.5, description="Amount to boost strength (0.0-0.5)")
):
    """Reinforce a memory by boosting its strength (simulates successful recall).

    This is useful when a memory proves particularly valuable - it will
    increase the memory's strength and slow its decay rate.

    Args:
        memory_id: ID of the memory to reinforce
        boost_amount: Amount to boost strength by (default: 0.2, max: 0.5)

    Returns:
        New memory strength after reinforcement
    """
    from .forgetting import reinforce_memory as do_reinforce

    try:
        client = collections.get_client()
        new_strength = do_reinforce(
            client,
            collections.COLLECTION_NAME,
            memory_id,
            boost_amount=boost_amount
        )

        if new_strength is None:
            raise HTTPException(status_code=404, detail="Memory not found")

        return {
            "status": "reinforced",
            "id": memory_id,
            "new_strength": new_strength,
            "boost_amount": boost_amount
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reinforce memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Relationship Inference Endpoints (Phase 1.2)

@app.post("/inference/run")
async def run_relationship_inference(
    inference_type: Optional[str] = Query(default="all", description="Type: all, temporal, semantic, causal, error-solution")
):
    """Manually trigger relationship inference.

    Runs automatic relationship discovery to find and create connections between memories.
    This implements Phase 1.2: Automatic Relationship Inference with multiple strategies:

    - **temporal**: Find memories created close together in time (FOLLOWS)
    - **semantic**: Find semantically similar memories (RELATED, SIMILAR_TO)
    - **causal**: Detect causal patterns in text (CAUSES)
    - **error-solution**: Link errors to their solutions (FIXES)
    - **all**: Run all inference types

    Args:
        inference_type: Type of inference to run (default: all)

    Returns:
        Statistics about relationships created by each inference type
    """
    from .relationship_inference import RelationshipInference
    import asyncio

    try:
        stats = {}

        if inference_type in ["all", "error-solution"]:
            fixes = await RelationshipInference.infer_error_solution_links(lookback_days=30)
            stats["error_solution_links"] = fixes

        if inference_type in ["all", "semantic"]:
            related = await RelationshipInference.infer_related_links(batch_size=20)
            stats["semantic_links"] = related

        if inference_type in ["all", "temporal"]:
            temporal = await RelationshipInference.infer_temporal_links(hours_window=2)
            stats["temporal_links"] = temporal

        if inference_type in ["all", "causal"]:
            causal = await RelationshipInference.infer_causal_links()
            stats["causal_links"] = causal

        stats["total_created"] = sum(stats.values())

        return stats

    except Exception as e:
        logger.error(f"Relationship inference failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/inference/co-access/stats")
async def get_co_access_stats():
    """Get statistics about co-access tracking.

    Co-access tracking monitors which memories are accessed together (e.g., appearing
    in the same search results). After a threshold number of co-accesses (default: 5),
    a RELATED relationship is automatically inferred.

    Returns:
        Statistics including:
        - total_pairs_tracked: Number of memory pairs being tracked
        - pairs_above_threshold: Number of pairs that exceeded the threshold
        - threshold: Current co-access threshold
    """
    from .relationship_inference import RelationshipInference

    try:
        stats = RelationshipInference.get_co_access_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get co-access stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/inference/co-access/reset")
async def reset_co_access_tracker():
    """Reset the co-access tracking data.

    This clears all tracked co-access counts. Useful for testing or maintenance.
    Note: In-memory tracking is lost on service restart.
    """
    from .relationship_inference import RelationshipInference

    try:
        RelationshipInference.reset_co_access_tracker()
        return {"status": "reset", "message": "Co-access tracker cleared"}
    except Exception as e:
        logger.error(f"Failed to reset co-access tracker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Session Management Endpoints (Phase 1.3)

@app.get("/sessions/stats")
async def get_session_stats():
    """Get statistics about conversation sessions.

    Returns:
        Statistics including:
        - total_sessions: Number of conversation sessions
        - total_memories_in_sessions: Total memories with session tracking
        - avg_memories_per_session: Average memories per session
        - sessions_with_summary: Sessions that have been consolidated
        - sessions_without_summary: Sessions pending consolidation
        - config: Session timeout and consolidation settings
    """
    from .session_extraction import SessionManager

    try:
        client = collections.get_client()
        stats = SessionManager.get_session_stats(client, collections.COLLECTION_NAME)
        return stats
    except Exception as e:
        logger.error(f"Failed to get session stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}/memories")
async def get_session_memories(session_id: str):
    """Get all memories in a specific session, ordered by sequence.

    Args:
        session_id: Session identifier

    Returns:
        List of memories in session order with conversation flow
    """
    from .session_extraction import SessionManager

    try:
        client = collections.get_client()
        memories = SessionManager.get_session_memories(
            client,
            collections.COLLECTION_NAME,
            session_id
        )
        return memories
    except Exception as e:
        logger.error(f"Failed to get session memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sessions/{session_id}/consolidate")
async def consolidate_session(session_id: str):
    """Manually trigger consolidation for a specific session.

    This creates a summary memory (type: CONTEXT) that consolidates all
    memories in the session, then links them with PART_OF relationships.

    Also creates FOLLOWS relationships between sequential memories and
    identifies causal chains (ERROR → LEARNING → DECISION).

    Args:
        session_id: Session identifier

    Returns:
        Consolidation result including summary memory ID and link counts
    """
    from .session_extraction import SessionManager

    try:
        client = collections.get_client()

        # First, infer relationships within session
        links_created = SessionManager.infer_session_relationships(
            client,
            collections.COLLECTION_NAME,
            session_id
        )

        # Then consolidate
        summary_id = SessionManager.consolidate_session(
            client,
            collections.COLLECTION_NAME,
            session_id
        )

        if not summary_id:
            raise HTTPException(
                status_code=400,
                detail="Session consolidation failed - may have <2 memories or already consolidated"
            )

        return {
            "status": "consolidated",
            "session_id": session_id,
            "summary_id": summary_id,
            "relationships_created": links_created
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to consolidate session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sessions/consolidate/batch")
async def consolidate_ready_sessions(
    older_than_hours: int = Query(default=24, ge=1, description="Consolidate sessions older than N hours")
):
    """Batch consolidate all sessions ready for consolidation.

    A session is ready if:
    1. It has ≥2 memories
    2. Last memory was created >older_than_hours ago
    3. No summary memory exists yet

    Args:
        older_than_hours: Minimum age in hours (default: 24)

    Returns:
        Statistics about consolidation operation
    """
    from .session_extraction import SessionManager

    try:
        client = collections.get_client()

        # Get sessions ready for consolidation
        ready_sessions = SessionManager.get_sessions_for_consolidation(
            client,
            collections.COLLECTION_NAME,
            older_than_hours=older_than_hours
        )

        consolidated = 0
        failed = 0
        results = []

        # Consolidate each session
        for session_id in ready_sessions:
            try:
                # Infer relationships
                links = SessionManager.infer_session_relationships(
                    client,
                    collections.COLLECTION_NAME,
                    session_id
                )

                # Consolidate
                summary_id = SessionManager.consolidate_session(
                    client,
                    collections.COLLECTION_NAME,
                    session_id
                )

                if summary_id:
                    consolidated += 1
                    results.append({
                        "session_id": session_id,
                        "summary_id": summary_id,
                        "status": "success",
                        "links_created": links
                    })
                else:
                    failed += 1
                    results.append({
                        "session_id": session_id,
                        "status": "failed",
                        "reason": "consolidation returned None"
                    })

            except Exception as e:
                failed += 1
                results.append({
                    "session_id": session_id,
                    "status": "error",
                    "error": str(e)
                })

        return {
            "total_ready": len(ready_sessions),
            "consolidated": consolidated,
            "failed": failed,
            "results": results
        }

    except Exception as e:
        logger.error(f"Batch consolidation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sessions/new")
async def create_new_session(project: Optional[str] = None):
    """Create a new conversation session.

    Args:
        project: Optional project name to associate with session

    Returns:
        New session ID
    """
    from .session_extraction import SessionManager

    try:
        session_id = SessionManager.generate_session_id()
        return {
            "session_id": session_id,
            "project": project,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Knowledge Graph Endpoints

@app.get("/graph/stats")
async def get_graph_statistics():
    """Get knowledge graph statistics."""
    from .graph import get_graph_stats, is_graph_enabled

    if not is_graph_enabled():
        return {"enabled": False, "message": "Neo4j not available"}

    return get_graph_stats()


@app.get("/graph/related/{memory_id}")
async def get_related(
    memory_id: str,
    max_hops: int = Query(default=2, ge=1, le=3, description="Maximum relationship hops"),
    limit: int = Query(default=20, ge=1, le=100)
):
    """Get memories related to a given memory via graph traversal."""
    from .graph import get_related_memories, is_graph_enabled

    if not is_graph_enabled():
        raise HTTPException(status_code=503, detail="Knowledge graph not available")

    related = get_related_memories(memory_id, max_hops=max_hops, limit=limit)
    return {"memory_id": memory_id, "related": related, "count": len(related)}


@app.get("/graph/timeline")
async def get_timeline(
    project: Optional[str] = Query(default=None),
    memory_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200)
):
    """Get memories ordered by time with their relationships."""
    from .graph import get_memory_timeline, is_graph_enabled

    if not is_graph_enabled():
        raise HTTPException(status_code=503, detail="Knowledge graph not available")

    timeline = get_memory_timeline(project=project, memory_type=memory_type, limit=limit)
    return {"timeline": timeline, "count": len(timeline)}


@app.get("/graph/project/{project}")
async def get_project_graph(project: str):
    """Get the knowledge graph for a project."""
    from .graph import get_project_knowledge_graph, is_graph_enabled

    if not is_graph_enabled():
        raise HTTPException(status_code=503, detail="Knowledge graph not available")

    graph = get_project_knowledge_graph(project)
    return {
        "project": project,
        "nodes": graph["nodes"],
        "edges": graph["edges"],
        "node_count": len(graph["nodes"]),
        "edge_count": len(graph["edges"])
    }


@app.get("/graph/solutions/{error_id}")
async def find_solutions(error_id: str):
    """Find solutions that fixed a specific error."""
    from .graph import find_error_solutions, is_graph_enabled

    if not is_graph_enabled():
        raise HTTPException(status_code=503, detail="Knowledge graph not available")

    solutions = find_error_solutions(error_id)
    return {"error_id": error_id, "solutions": solutions, "count": len(solutions)}


# Notification Endpoints

class NotificationCreate(BaseModel):
    """Request model for creating notifications."""
    type: str
    title: str
    message: str
    data: dict = {}


@app.get("/notifications")
async def get_notifications(
    unread_only: bool = Query(default=False),
    type_filter: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=None)
):
    """Get notifications with optional filters."""
    notifications = notif_module.get_notifications(
        unread_only=unread_only,
        type_filter=type_filter,
        limit=limit
    )
    return [n.dict() for n in notifications]


@app.post("/notifications")
async def create_notification(notification: NotificationCreate):
    """Create a new notification."""
    from datetime import datetime
    import uuid

    new_notification = notif_module.Notification(
        id=str(uuid.uuid4()),
        type=notification.type,
        title=notification.title,
        message=notification.message,
        data=notification.data,
        read=False,
        created_at=datetime.now().isoformat()
    )

    stored = notif_module.store_notification(new_notification)
    return stored.dict()


@app.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark a notification as read."""
    success = notif_module.mark_notification_read(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "read", "id": notification_id}


@app.post("/notifications/mark-all-read")
async def mark_all_notifications_read():
    """Mark all notifications as read."""
    count = notif_module.mark_all_read()
    return {"status": "success", "marked_count": count}


@app.delete("/notifications/{notification_id}")
async def delete_notification(notification_id: str):
    """Delete a notification."""
    success = notif_module.delete_notification(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "deleted", "id": notification_id}


@app.delete("/notifications")
async def clear_all_notifications():
    """Clear all notifications."""
    count = notif_module.clear_all_notifications()
    return {"status": "cleared", "count": count}


@app.get("/notifications/stats")
async def get_notification_stats():
    """Get notification statistics."""
    return notif_module.get_notification_stats()


# Settings Endpoints

import json
from pathlib import Path

SETTINGS_FILE = Path.home() / ".claude" / "memory" / "data" / "settings.json"


def ensure_settings_file():
    """Ensure settings file exists with defaults."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        default_settings = {
            "captureWebFetch": True,
            "captureBashSuccess": True,
            "captureBashErrors": True,
            "captureTaskResults": True,
            "suggestionLimit": 5,
            "suggestionMinScore": 0.7,
            "suggestionFrequency": "always",
            "notificationEnabled": True,
            "notificationSound": False,
            "cacheEnabled": True,
            "cacheTtlHours": 24
        }
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(default_settings, f, indent=2)


@app.get("/settings")
async def get_settings(request: Request):
    """Get user settings."""
    # Check if this is a browser request (SPA navigation)
    accept_header = request.headers.get('accept', '')
    if 'text/html' in accept_header and 'application/json' not in accept_header:
        # Browser navigation - return SPA
        index_path = os.path.join(FRONTEND_BUILD, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path, media_type='text/html')
        raise HTTPException(status_code=404, detail="Dashboard not built")

    ensure_settings_file()
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to load settings")


@app.post("/settings")
async def update_settings(settings: dict):
    """Update user settings."""
    ensure_settings_file()
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        logger.info("Settings updated successfully")
        return {"status": "success", "settings": settings}
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to save settings")


# Suggestion Throttling Endpoints

@app.get("/suggestions/should-show")
async def should_show_suggestions(user_id: str = Query(default="default")):
    """Check if suggestions should be shown based on throttling rules."""
    try:
        # Load user settings
        settings = {}
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
        except:
            pass

        should_show = suggestions_module.should_show_suggestions(
            user_id=user_id,
            context={},
            settings=settings
        )

        return {"should_show": should_show}
    except Exception as e:
        logger.error(f"Error checking suggestions: {e}")
        return {"should_show": True}  # Default to showing


@app.post("/suggestions/feedback")
async def record_suggestion_feedback(
    user_id: str = Query(default="default"),
    was_useful: bool = Query(...)
):
    """Record if a suggestion was useful (for quality tracking)."""
    suggestions_module.record_suggestion_quality(user_id, was_useful)
    return {"status": "recorded"}


@app.get("/suggestions/stats")
async def get_suggestion_stats(user_id: Optional[str] = Query(default=None)):
    """Get suggestion throttling statistics."""
    return suggestions_module.get_throttler_stats(user_id)


# ============================================================
# PROCESS MANAGEMENT & JOB EXECUTION
# ============================================================

from .process_manager import ProcessManager
from dataclasses import asdict

process_manager = ProcessManager()

# Process Control (3 endpoints)

@app.get("/processes/watcher/status")
async def get_watcher_status():
    """Check if file watcher is running."""
    return process_manager.get_watcher_status()


@app.post("/processes/watcher/start")
async def start_watcher(interval: int = Query(default=30, ge=10, le=300)):
    """Start file watcher daemon."""
    try:
        result = process_manager.start_watcher(interval=interval)

        # Broadcast to WebSocket clients
        await manager.broadcast({
            "type": "process_status_changed",
            "data": {"process": "watcher", "status": "started"}
        })

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting watcher: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/processes/watcher/stop")
async def stop_watcher():
    """Stop file watcher daemon."""
    try:
        result = process_manager.stop_watcher()

        # Broadcast to WebSocket clients
        await manager.broadcast({
            "type": "process_status_changed",
            "data": {"process": "watcher", "status": "stopped"}
        })

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error stopping watcher: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Script Execution (5 endpoints)

@app.post("/jobs/prune")
async def execute_prune_job(
    days: int = Query(default=30, ge=1, le=365),
    max_delete: int = Query(default=1000, ge=1, le=10000),
    execute: bool = Query(default=False)
):
    """Execute memory pruning job."""
    try:
        args = [f"--days={days}", f"--max={max_delete}"]
        if execute:
            args.append("--execute")

        job_id = process_manager.execute_script("prune_memories", args)

        # Broadcast to WebSocket clients
        await manager.broadcast({
            "type": "job_started",
            "data": {"job_id": job_id, "script": "prune", "args": args}
        })

        return {"job_id": job_id, "status": "started"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting prune job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/tag")
async def execute_tag_job(limit: int = Query(default=1000, ge=1, le=10000)):
    """Execute NLP tagging job."""
    try:
        args = [f"--limit={limit}"]
        job_id = process_manager.execute_script("nlp_tagger", args)

        # Broadcast to WebSocket clients
        await manager.broadcast({
            "type": "job_started",
            "data": {"job_id": job_id, "script": "tag", "args": args}
        })

        return {"job_id": job_id, "status": "started"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting tag job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get job status by ID."""
    job = process_manager.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return asdict(job)


@app.get("/jobs")
async def list_jobs(limit: int = Query(default=20, ge=1, le=100)):
    """List recent jobs."""
    jobs = process_manager.list_jobs(limit=limit)
    return [asdict(job) for job in jobs]


@app.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel running job."""
    success = process_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or not running")
    return {"status": "cancelled", "job_id": job_id}


# Log Access (2 endpoints)

@app.get("/logs/{log_name}")
async def read_log(
    log_name: str,
    lines: int = Query(default=50, ge=1, le=1000)
):
    """Read log file."""
    allowed = ["watcher", "consolidation", "document-watcher"]
    if log_name not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid log name. Allowed: {allowed}")

    try:
        return process_manager.read_log(log_name, lines=lines)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error reading log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/logs/{log_name}/clear")
async def clear_log(log_name: str):
    """Clear log file."""
    allowed = ["watcher", "consolidation", "document-watcher"]
    if log_name not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid log name. Allowed: {allowed}")

    try:
        success = process_manager.clear_log(log_name)
        return {"status": "cleared" if success else "failed", "log_name": log_name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error clearing log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Scheduler (2 endpoints)

from .scheduler import get_scheduler_status, trigger_job

@app.get("/scheduler/status")
async def scheduler_status():
    """Get background scheduler status."""
    try:
        return get_scheduler_status()
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scheduler/jobs/{job_id}/trigger")
async def trigger_scheduled_job(job_id: str):
    """Manually trigger a scheduled job."""
    try:
        success = trigger_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found or scheduler disabled")
        return {"status": "triggered", "job_id": job_id}
    except Exception as e:
        logger.error(f"Error triggering job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Database Management (2 endpoints)

@app.post("/database/reset")
async def reset_database(confirm: bool = Query(default=False)):
    """Reset database by deleting all memories from Qdrant and Neo4j graph."""
    from datetime import datetime
    from .graph import reset_graph

    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to reset database"
        )

    try:
        # Delete all points from the vector collection
        client = collections.get_client()

        # Delete all points using a filter that matches everything
        # This is more efficient than scrolling and deleting individually
        client.delete(
            collection_name=collections.COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter()  # Empty filter matches all points
            )
        )

        # Delete all nodes and relationships from graph database
        graph_result = reset_graph()

        logger.info(f"Database reset successfully - Vector DB cleared, Graph: {graph_result}")

        # Broadcast to WebSocket clients
        await manager.broadcast({
            "type": "database_reset",
            "data": {"timestamp": datetime.now().isoformat()}
        })

        return {
            "status": "success",
            "message": "Database reset successfully (vector DB + graph DB)",
            "vector_db": {"collection": collections.COLLECTION_NAME, "deleted": "all points"},
            "graph_db": graph_result
        }
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/database/stats")
async def get_database_stats():
    """Get database statistics."""
    try:
        client = collections.get_client()
        collection_info = client.get_collection(collection_name=collections.COLLECTION_NAME)
        return {
            "collection_name": collections.COLLECTION_NAME,
            "points_count": collection_info.points_count,
            "status": str(collection_info.status)
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Document Indexing Configuration (3 endpoints)

INDEXING_CONFIG_FILE = os.path.expanduser("~/.claude/memory/data/indexing-config.json")

def ensure_indexing_config():
    """Ensure indexing config file exists with defaults."""
    os.makedirs(os.path.dirname(INDEXING_CONFIG_FILE), exist_ok=True)
    if not os.path.exists(INDEXING_CONFIG_FILE):
        default_config = {
            "folders": [],  # Start empty - user must choose folders
            "exclude_patterns": [".git", "node_modules", "__pycache__"],
            "file_extensions": [".txt", ".md", ".pdf", ".docx", ".py", ".js", ".ts", ".json", ".yaml"],
            "auto_index": False  # Disabled by default - user must enable
        }
        with open(INDEXING_CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=2)


@app.get("/indexing/folders")
async def get_indexing_folders():
    """Get list of folders being indexed."""
    ensure_indexing_config()
    try:
        with open(INDEXING_CONFIG_FILE, 'r') as f:
            config = json.load(f)
        return {
            "folders": config.get("folders", []),  # Empty by default
            "auto_index": config.get("auto_index", False),  # Disabled by default
            "exclude_patterns": config.get("exclude_patterns", []),
            "file_extensions": config.get("file_extensions", [])
        }
    except Exception as e:
        logger.error(f"Failed to load indexing config: {e}")
        raise HTTPException(status_code=500, detail="Failed to load indexing config")


@app.post("/indexing/folders")
async def update_indexing_folders(config: dict):
    """Update list of folders to index."""
    ensure_indexing_config()
    try:
        # Get folder paths from config
        folders = config.get("folders", [])

        # Normalize paths (strip trailing slashes, but keep ~ for host expansion)
        normalized_folders = []
        for folder in folders:
            # Strip trailing slashes but keep the path as-is (don't validate in container)
            # The file watcher script runs on the host and will expand ~ correctly
            normalized = folder.rstrip('/')
            if normalized:  # Skip empty strings
                normalized_folders.append(normalized)

        # Update config
        current_config = {}
        try:
            with open(INDEXING_CONFIG_FILE, 'r') as f:
                current_config = json.load(f)
        except Exception:
            pass

        current_config.update({
            "folders": normalized_folders,
            "auto_index": config.get("auto_index", True),
            "exclude_patterns": config.get("exclude_patterns", current_config.get("exclude_patterns", [])),
            "file_extensions": config.get("file_extensions", current_config.get("file_extensions", []))
        })

        with open(INDEXING_CONFIG_FILE, 'w') as f:
            json.dump(current_config, f, indent=2)

        logger.info(f"Indexing config updated: {len(normalized_folders)} folders")

        return {
            "status": "success",
            "folders": normalized_folders,
            "message": f"Updated {len(normalized_folders)} folders"
        }
    except Exception as e:
        logger.error(f"Failed to update indexing config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/indexing/reindex")
async def trigger_reindex(folders: Optional[list[str]] = Query(default=None)):
    """Trigger manual reindexing of specified folders."""
    try:
        # If no folders specified, use configured folders
        if not folders:
            config_data = await get_indexing_folders()
            folders = config_data.get("folders", [])

        # Ensure folders is a list
        if folders is None:
            folders = []

        # Execute indexing script as a job
        args = []
        for folder in folders:
            args.extend(["--path", folder])

        args.append("--force")  # Force reindex

        job_id = process_manager.execute_script("index_documents", args)

        await manager.broadcast({
            "type": "job_started",
            "data": {"job_id": job_id, "script": "index_documents", "folders": folders}
        })

        return {
            "job_id": job_id,
            "status": "started",
            "folders": folders,
            "message": f"Reindexing {len(folders)} folders"
        }
    except Exception as e:
        logger.error(f"Error triggering reindex: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Document Search & Management (5 endpoints)
# Documents are separate from memories - for filesystem content retrieval

@app.post("/documents/insert")
async def insert_document_endpoint(request_data: dict):
    """
    Insert a document chunk into the documents collection.

    Used by indexing scripts to add filesystem content.
    """
    from . import documents

    try:
        content = request_data.get("content")
        file_path = request_data.get("file_path")
        chunk_index = request_data.get("chunk_index", 0)
        total_chunks = request_data.get("total_chunks", 1)
        metadata = request_data.get("metadata", {})

        if not content or not file_path:
            raise HTTPException(
                status_code=400,
                detail="content and file_path are required"
            )

        point_id = documents.insert_document_chunk(
            content=content,
            file_path=file_path,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            metadata=metadata
        )

        return {
            "status": "inserted",
            "point_id": point_id,
            "file_path": file_path,
            "chunk_index": chunk_index
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to insert document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/search")
async def search_documents_endpoint(
    query: str = Query(..., description="Search query"),
    limit: int = Query(default=10, ge=1, le=100),
    file_type: Optional[str] = Query(default=None, description="Filter by file extension"),
    folder: Optional[str] = Query(default=None, description="Filter by folder path")
):
    """
    Search indexed documents (separate from memories).

    Documents are files from your filesystem indexed for retrieval.
    Memories are structured knowledge (errors, decisions, patterns).
    """
    from . import documents

    try:
        results = documents.search_documents(
            query=query,
            limit=limit,
            file_type=file_type,
            folder=folder
        )

        return {
            "query": query,
            "results": results,
            "count": len(results),
            "filters": {
                "file_type": file_type,
                "folder": folder
            }
        }

    except Exception as e:
        logger.error(f"Document search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/stats")
async def get_document_stats():
    """Get document collection statistics."""
    from . import documents

    try:
        stats = documents.get_document_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get document stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{file_path:path}")
async def delete_document_endpoint(file_path: str):
    """Delete a specific document from the index."""
    from . import documents

    try:
        success = documents.delete_document(file_path)

        if success:
            await manager.broadcast({
                "type": "document_deleted",
                "data": {"file_path": file_path}
            })
            return {"status": "deleted", "file_path": file_path}
        else:
            raise HTTPException(status_code=404, detail="Document not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/reset")
async def reset_documents_endpoint(confirm: bool = Query(default=False)):
    """Delete all indexed documents (separate from memory reset)."""
    from . import documents

    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to reset documents"
        )

    try:
        result = documents.reset_documents()

        await manager.broadcast({
            "type": "documents_reset",
            "data": {"deleted_chunks": result.get("deleted_chunks", 0)}
        })

        return result

    except Exception as e:
        logger.error(f"Failed to reset documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Brain Intelligence API Endpoints
# ============================================================================

@app.post("/brain/infer-relationships")
async def brain_infer_relationships(lookback_days: int = Query(default=30, ge=1, le=90)):
    """
    Manually trigger relationship inference.

    Finds errors that were later solved and creates FIXES relationships.
    Also links semantically similar memories as RELATED.

    Args:
        lookback_days: Days to look back for solutions (1-90)

    Returns:
        Number of relationships created
    """
    try:
        from .relationship_inference import RelationshipInference

        # Infer error→solution links
        fixes_links = await RelationshipInference.infer_error_solution_links(lookback_days)

        # Infer related links
        related_links = await RelationshipInference.infer_related_links(batch_size=20)

        # Infer temporal links
        temporal_links = await RelationshipInference.infer_temporal_links(hours_window=2)

        return {
            "success": True,
            "fixes_links": fixes_links,
            "related_links": related_links,
            "temporal_links": temporal_links,
            "total_links": fixes_links + related_links + temporal_links
        }

    except Exception as e:
        logger.error(f"Failed to infer relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/brain/update-importance")
async def brain_update_importance(limit: int = Query(default=100, ge=1, le=1000)):
    """
    Manually trigger adaptive importance score updates.

    Updates importance scores based on access patterns, type, and co-access.

    Args:
        limit: Max memories to update (1-1000)

    Returns:
        Number of memories updated
    """
    try:
        from .consolidation import update_importance_scores_batch

        updated = update_importance_scores_batch(
            client=collections.get_client(),
            collection_name=collections.COLLECTION_NAME,
            limit=limit
        )

        return {
            "success": True,
            "updated": updated,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Failed to update importance scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/brain/archive-low-utility")
async def brain_archive_low_utility(
    threshold: float = Query(default=0.3, ge=0.0, le=1.0),
    max_archive: int = Query(default=100, ge=1, le=500),
    dry_run: bool = Query(default=False)
):
    """
    Manually trigger utility-based archival.

    Archives memories with low utility scores (based on access, relationships, importance).

    Args:
        threshold: Archive if utility < this (0.0-1.0)
        max_archive: Max memories to archive (1-500)
        dry_run: If true, only simulate (don't actually archive)

    Returns:
        Number of memories archived
    """
    try:
        from .consolidation import archive_low_utility_memories

        archived = archive_low_utility_memories(
            client=collections.get_client(),
            collection_name=collections.COLLECTION_NAME,
            utility_threshold=threshold,
            max_archive=max_archive,
            dry_run=dry_run
        )

        return {
            "success": True,
            "archived": archived,
            "threshold": threshold,
            "dry_run": dry_run
        }

    except Exception as e:
        logger.error(f"Failed to archive low-utility memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/brain/stats")
async def brain_get_stats():
    """
    Get brain intelligence statistics.

    Returns stats about adaptive learning, relationships, and memory utility.

    Returns:
        Statistics about brain features
    """
    try:
        # Get basic stats
        stats = await get_stats()

        # Get graph stats for relationships
        from .graph import get_graph_stats
        graph_stats = get_graph_stats()

        # Calculate utility distribution
        points, _ = collections.get_client().scroll(
            collection_name=collections.COLLECTION_NAME,
            limit=1000,
            with_payload=True,
            with_vectors=False
        )

        from .consolidation import calculate_memory_utility
        from datetime import datetime

        utilities = []
        for point in points:
            payload = point.payload
            utility = calculate_memory_utility(
                access_count=payload.get("access_count", 0),
                importance=payload.get("importance", 0.5),
                created_at=datetime.fromisoformat(payload["created_at"]),
                last_accessed_at=(
                    datetime.fromisoformat(payload["last_accessed_at"])
                    if payload.get("last_accessed_at")
                    else datetime.fromisoformat(payload["created_at"])
                ),
                relationship_count=0,  # Simplified for stats
                memory_type=payload["type"]
            )
            utilities.append(utility)

        # Utility buckets
        high_utility = sum(1 for u in utilities if u >= 0.7)
        medium_utility = sum(1 for u in utilities if 0.3 <= u < 0.7)
        low_utility = sum(1 for u in utilities if u < 0.3)

        return {
            "total_memories": stats.total_memories,
            "relationships": graph_stats.get("relationships", 0),
            "utility_distribution": {
                "high": high_utility,
                "medium": medium_utility,
                "low": low_utility
            },
            "adaptive_features": {
                "importance_scoring": True,
                "relationship_inference": True,
                "utility_archival": True
            }
        }

    except Exception as e:
        logger.error(f"Failed to get brain stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Full Brain Mode Features
# ============================================================================


@app.post("/brain/reconsolidate/{memory_id}")
async def brain_reconsolidate(
    memory_id: str,
    access_context: Optional[str] = Query(default=None),
    co_accessed_ids: Optional[str] = Query(default=None)
):
    """
    Reconsolidate a memory - strengthen it when accessed.

    This simulates how real brains modify memories during recall.

    Args:
        memory_id: Memory to reconsolidate
        access_context: Current context (project, task)
        co_accessed_ids: Comma-separated IDs of co-accessed memories

    Returns:
        Reconsolidation results
    """
    try:
        from .reconsolidation import reconsolidate_memory

        # Parse co-accessed IDs
        co_ids = co_accessed_ids.split(",") if co_accessed_ids else None

        result = reconsolidate_memory(
            memory_id=memory_id,
            access_context=access_context,
            co_accessed_ids=co_ids
        )

        return result

    except Exception as e:
        logger.error(f"Reconsolidation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/brain/spaced-repetition")
async def brain_spaced_repetition(limit: int = Query(default=10, ge=1, le=100)):
    """
    Get memories due for spaced repetition review.

    Returns memories that need reinforcement based on forgetting curve.

    Args:
        limit: Maximum candidates to return

    Returns:
        List of memories due for review
    """
    try:
        from .reconsolidation import get_spaced_repetition_candidates

        candidates = get_spaced_repetition_candidates(limit=limit)

        return {
            "success": True,
            "candidates": candidates,
            "count": len(candidates)
        }

    except Exception as e:
        logger.error(f"Spaced repetition query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/brain/topics")
async def brain_discover_topics(
    min_cluster_size: int = Query(default=3, ge=2, le=20),
    max_topics: int = Query(default=20, ge=5, le=50)
):
    """
    Discover semantic topics by clustering memories.

    Organizes memories into natural groupings like a real brain.

    Args:
        min_cluster_size: Minimum memories per topic
        max_topics: Maximum topics to return

    Returns:
        Discovered topics with memory IDs
    """
    try:
        from .semantic_clustering import extract_topics_from_memories, create_topic_summaries

        topics = extract_topics_from_memories(
            min_cluster_size=min_cluster_size,
            max_topics=max_topics
        )

        topics = create_topic_summaries(topics)

        return {
            "success": True,
            "topics": topics,
            "count": len(topics)
        }

    except Exception as e:
        logger.error(f"Topic discovery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/brain/topics/timeline/{topic_name}")
async def brain_topic_timeline(
    topic_name: str,
    limit: int = Query(default=50, ge=10, le=200)
):
    """
    Get chronological timeline of memories in a topic.

    Args:
        topic_name: Topic to get timeline for
        limit: Max memories to return

    Returns:
        Chronologically ordered memories
    """
    try:
        from .semantic_clustering import get_topic_timeline

        timeline = get_topic_timeline(topic_name, limit=limit)

        return {
            "success": True,
            "topic": topic_name,
            "timeline": timeline,
            "count": len(timeline)
        }

    except Exception as e:
        logger.error(f"Topic timeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/brain/replay")
async def brain_memory_replay(
    count: int = Query(default=10, ge=1, le=100),
    importance_threshold: float = Query(default=0.5, ge=0.0, le=1.0)
):
    """
    Spontaneously replay random important memories to strengthen them.

    Simulates how real brains consolidate memories during rest/sleep.

    Args:
        count: Number of memories to replay
        importance_threshold: Only replay above this importance

    Returns:
        Replay statistics
    """
    try:
        from .memory_replay import replay_random_memories

        result = replay_random_memories(
            count=count,
            importance_threshold=importance_threshold
        )

        return result

    except Exception as e:
        logger.error(f"Memory replay failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/brain/replay/project/{project}")
async def brain_project_replay(
    project: str,
    count: int = Query(default=10, ge=1, le=100)
):
    """
    Replay memories from a specific project.

    Useful for "reviewing" a project's knowledge.

    Args:
        project: Project name
        count: Number of memories to replay

    Returns:
        Replay statistics
    """
    try:
        from .memory_replay import targeted_replay

        result = targeted_replay(project=project, count=count)

        return result

    except Exception as e:
        logger.error(f"Project replay failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/brain/replay/underutilized")
async def brain_underutilized_replay(
    days: int = Query(default=7, ge=1, le=90),
    count: int = Query(default=20, ge=1, le=100)
):
    """
    Replay important memories that haven't been accessed recently.

    Prevents valuable knowledge from fading.

    Args:
        days: Days since last access
        count: Number to replay

    Returns:
        Replay statistics
    """
    try:
        from .memory_replay import replay_underutilized_memories

        result = replay_underutilized_memories(
            days_since_access=days,
            count=count
        )

        return result

    except Exception as e:
        logger.error(f"Underutilized replay failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/brain/dream")
async def brain_dream_mode(duration: int = Query(default=30, ge=10, le=300)):
    """
    "Dream mode" - rapid random replay to discover unexpected connections.

    Simulates REM sleep where brain makes random associations.

    Args:
        duration: How long to run (seconds)

    Returns:
        Dream statistics
    """
    try:
        from .memory_replay import dream_mode_replay

        result = dream_mode_replay(duration_seconds=duration)

        return result

    except Exception as e:
        logger.error(f"Dream mode failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# ============================================================================
# Data Export & Backup API Endpoints
# ============================================================================

from fastapi.responses import Response, StreamingResponse

@app.get("/export/memories")
async def export_memories(
    format: str = Query(default="json", regex="^(json|csv|obsidian)$"),
    type: Optional[str] = Query(default=None),
    project: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    tags: Optional[str] = Query(default=None),
    include_relationships: bool = Query(default=True)
):
    """
    Export memories in specified format.

    Formats:
    - json: JSON with full metadata and relationships
    - csv: CSV for Excel/Google Sheets
    - obsidian: ZIP of markdown files with wiki links

    Query params:
    - format: Export format (json, csv, obsidian)
    - type: Filter by memory type
    - project: Filter by project
    - date_from/date_to: Date range (ISO format)
    - tags: Comma-separated tags
    - include_relationships: Include graph data (JSON only)
    """
    try:
        from .export import MemoryExporter

        # Build filters
        filters = {}
        if type:
            filters["type"] = type
        if project:
            filters["project"] = project
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to
        if tags:
            filters["tags"] = tags.split(",")

        # Generate export based on format
        if format == "json":
            content = MemoryExporter.export_json(filters, include_relationships)
            media_type = "application/json"
            filename = f"memories_{datetime.now().strftime('%Y%m%d')}.json"
            return Response(
                content=content,
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

        elif format == "csv":
            content = MemoryExporter.export_csv(filters)
            media_type = "text/csv"
            filename = f"memories_{datetime.now().strftime('%Y%m%d')}.csv"
            return Response(
                content=content,
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

        elif format == "obsidian":
            zip_buffer = MemoryExporter.export_obsidian(filters)
            filename = f"memories_obsidian_{datetime.now().strftime('%Y%m%d')}.zip"
            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/backup")
async def create_manual_backup(backup_name: Optional[str] = Query(default=None)):
    """Create full system backup (memories + graph data)."""
    try:
        from .export import MemoryExporter

        result = MemoryExporter.create_backup(backup_name)
        return result

    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/backups")
async def list_backups():
    """List all available backups."""
    try:
        from .export import MemoryExporter

        backups = MemoryExporter.list_backups()
        return {"backups": backups, "count": len(backups)}

    except Exception as e:
        logger.error(f"Backup list failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Insight Generation API Endpoints
# ============================================================================

@app.get("/insights/recurring-patterns")
async def get_recurring_patterns(limit: int = Query(default=10, ge=1, le=50)):
    """Get recurring error→solution patterns."""
    try:
        from .insights import InsightGenerator

        patterns = InsightGenerator.discover_recurring_patterns(limit)
        return {"patterns": patterns, "count": len(patterns)}

    except Exception as e:
        logger.error(f"Recurring patterns API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/insights/expertise-profile")
async def get_expertise_profile():
    """Analyze user's technical expertise based on memory distribution."""
    try:
        from .insights import InsightGenerator

        profile = InsightGenerator.analyze_expertise_profile()
        return {
            "expertise": profile,
            "total_technologies": len(profile),
            "expert_in": [tech for tech, data in profile.items() if data["level"] == "expert"],
            "proficient_in": [tech for tech, data in profile.items() if data["level"] == "proficient"]
        }

    except Exception as e:
        logger.error(f"Expertise profile API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/insights/anomalies")
async def get_memory_anomalies():
    """Find unusual/suspicious memories that may need attention."""
    try:
        from .insights import InsightGenerator

        anomalies = InsightGenerator.detect_memory_anomalies()
        return {
            "anomalies": anomalies,
            "count": len(anomalies),
            "by_reason": {
                "extremely_short": sum(1 for a in anomalies if "extremely_short" in a["anomaly_reasons"]),
                "orphaned": sum(1 for a in anomalies if "orphaned" in a["anomaly_reasons"]),
                "old_unaccessed": sum(1 for a in anomalies if "old_unaccessed" in a["anomaly_reasons"]),
                "high_importance_low_access": sum(1 for a in anomalies if "high_importance_low_access" in a["anomaly_reasons"])
            }
        }

    except Exception as e:
        logger.error(f"Anomaly detection API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/insights/error-trends")
async def get_error_trends(days: int = Query(default=30, ge=7, le=90)):
    """Analyze error frequency and resolution trends."""
    try:
        from .insights import InsightGenerator

        trends = InsightGenerator.analyze_error_trends(days)
        return trends

    except Exception as e:
        logger.error(f"Error trends API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/insights/summary")
async def get_intelligence_summary(limit: int = Query(default=5, ge=1, le=10)):
    """Get top intelligence insights about user's memory patterns."""
    try:
        from .insights import InsightGenerator

        insights = InsightGenerator.generate_intelligence_summary(limit)
        return {"insights": insights, "count": len(insights)}

    except Exception as e:
        logger.error(f"Intelligence summary API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Advanced Brain Mode API Endpoints
# ============================================================================

@app.post("/brain/emotional-analysis")
async def run_emotional_analysis_api(limit: int = 100):
    """
    Manually trigger emotional weighting analysis.

    Analyzes memories for emotional significance and boosts importance accordingly.
    """
    try:
        from .emotional_weighting import run_emotional_analysis as analyze

        analyzed = analyze(limit=limit)

        return {
            "success": True,
            "analyzed": analyzed,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Emotional analysis API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/brain/detect-conflicts")
async def detect_conflicts_api(limit: int = 50):
    """
    Manually trigger interference detection and resolution.

    Finds contradictory memories and resolves conflicts via SUPERSEDES relationships.
    """
    try:
        from .interference_detection import run_interference_detection as detect

        result = detect(limit=limit)

        return {
            "success": True,
            "conflicts_detected": result.get("conflicts_detected", 0),
            "conflicts_resolved": result.get("conflicts_resolved", 0),
            "timestamp": result.get("timestamp")
        }

    except Exception as e:
        logger.error(f"Conflict detection API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/brain/meta-learning")
async def run_meta_learning_api():
    """
    Manually trigger meta-learning (performance tracking and parameter tuning).

    Tracks system metrics and automatically tunes parameters for better performance.
    """
    try:
        from .meta_learning import run_meta_learning as learn

        result = learn()

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return {
            "success": True,
            "metrics": result.get("metrics"),
            "tuned_parameters": result.get("tuned_parameters"),
            "timestamp": result.get("timestamp")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Meta-learning API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/brain/performance-metrics")
async def get_performance_metrics(days: int = 7):
    """
    Get historical performance metrics.

    Args:
        days: Number of days to look back (default: 7)

    Returns:
        Historical performance metrics
    """
    try:
        from .meta_learning import MetaLearning

        # Get current metrics
        current = MetaLearning.track_performance_metrics()

        # Get historical metrics
        history = MetaLearning.get_metrics_history(days=days)

        return {
            "success": True,
            "current": current,
            "history": history,
            "days": days
        }

    except Exception as e:
        logger.error(f"Performance metrics API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
