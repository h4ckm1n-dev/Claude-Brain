"""FastAPI router for memory CRUD endpoints.

Handles creation, retrieval, update, deletion of memories plus
quality rating, versioning, consolidation, forgetting, and migration.
"""

import logging
import os
import time
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from qdrant_client import models

from ..models import (
    Memory, MemoryCreate, MemoryUpdate, MemoryType, ChangeType,
    SearchQuery, SearchResult, EmbedRequest, EmbedResponse,
    LinkRequest, MigrationResult, RelationType, utc_now,
)
from .. import collections
from ..embeddings import embed_text, get_embedding_dim
from ..quality import validate_memory_quality, QualityValidationError, get_quality_suggestions
from ..enhancements import (
    check_duplicate_before_store, suggest_tags_from_similar, get_template_hints,
    normalize_tags, auto_enrich_tags, auto_enrich_fields, clean_content,
)
from ..server_deps import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["memories"])

# TTL caches for expensive endpoints (60s)
_quality_report_cache: dict = {"data": None, "expires": 0}
_quality_leaderboard_cache: dict = {"data": None, "expires": 0}

# Frontend build path (for SPA fallback in list endpoint)
FRONTEND_BUILD = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../frontend/dist")
)


# ---------------------------------------------------------------------------
# Request models local to this router
# ---------------------------------------------------------------------------

class RatingRequest(BaseModel):
    """Request model for rating a memory."""
    rating: int
    feedback: Optional[str] = None


# ---------------------------------------------------------------------------
# Draft / Embed
# ---------------------------------------------------------------------------

@router.post("/memories/draft")
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
        from ..quality import calculate_quality_score
        score, warnings = calculate_quality_score(data)

        # Get template hints
        template_hints = get_template_hints(data.type)

        # Determine recommendation
        from ..quality import MIN_QUALITY_SCORE
        if score >= MIN_QUALITY_SCORE:
            recommendation = "ready"
        elif score >= MIN_QUALITY_SCORE - 0.1:
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


@router.post("/embed", response_model=EmbedResponse)
async def generate_embedding(request: EmbedRequest):
    """Generate embedding for text."""
    result = embed_text(request.text, include_sparse=request.include_sparse)
    return EmbedResponse(
        dense=result["dense"],
        sparse=result.get("sparse"),
        dimensions=get_embedding_dim()
    )


# ---------------------------------------------------------------------------
# Shared quality pipeline
# ---------------------------------------------------------------------------

def enhance_and_validate(data: MemoryCreate) -> tuple[MemoryCreate, dict | None]:
    """Run full quality pipeline: clean content, enrich tags, dedup check, validate.

    Returns (enhanced_memory, duplicate_info).
    Raises HTTPException(422) if quality too low.
    Raises HTTPException(400) for useless/empty content patterns.
    """
    # 1. Clean content
    data.content = clean_content(data.content)

    # 2. Auto-enrich missing type-specific fields from content
    data = auto_enrich_fields(data)

    # 3. Normalize + auto-enrich tags
    data = auto_enrich_tags(data)

    # 4. Semantic dedup check
    duplicate_info = check_duplicate_before_store(data)
    if duplicate_info:
        logger.warning(
            f"Duplicate detected: {duplicate_info['message']} "
            f"(existing: {duplicate_info['existing_id']}, similarity: {duplicate_info['similarity_score']})"
        )

    # 5. Quality validation
    try:
        is_valid, score, warnings = validate_memory_quality(data)
        if warnings:
            logger.info(f"Memory quality: {score}/100 with {len(warnings)} warnings")
    except QualityValidationError as e:
        suggestions = get_quality_suggestions(data.type)
        template_hints = get_template_hints(data.type)

        error_detail: dict = {
            "error": "Memory quality too low",
            "score": e.score,
            "issues": e.warnings,
            "suggestions": suggestions,
        }
        if template_hints and "example" in template_hints:
            error_detail["example"] = template_hints["example"]
            error_detail["structure"] = template_hints.get("suggested_structure", "")
        if duplicate_info:
            error_detail["duplicate_warning"] = {
                "message": duplicate_info["message"],
                "existing_id": duplicate_info["existing_id"],
                "similarity": duplicate_info["similarity_score"],
            }

        raise HTTPException(status_code=422, detail=error_detail)

    # 6. Legacy content filters
    content = data.content.strip()

    if "session-end" in (data.tags or []):
        if "Duration: unknown" in content and ("Files edited: 0" in content or "Files edited:" not in content):
            raise HTTPException(status_code=400, detail="Session summary contains no useful information")

    useless_patterns = [
        "Duration: unknown.",
        "Session ended (session_end) - Duration: unknown.",
    ]
    if any(content == pattern.strip() for pattern in useless_patterns):
        raise HTTPException(status_code=400, detail="Memory content is too generic/empty")

    # 7. Auto-captured boilerplate rejection
    boilerplate_starts = [
        "session started for project",
        "session closed at",
        "session ended at",
        "session resumed for project",
    ]
    content_lower = content.lower()
    is_auto_captured = "auto-captured" in (data.tags or [])
    if is_auto_captured and any(content_lower.startswith(bp) for bp in boilerplate_starts):
        raise HTTPException(
            status_code=400,
            detail="Auto-captured session boilerplate rejected — not a genuine memory"
        )

    return data, duplicate_info


# ---------------------------------------------------------------------------
# Memory CRUD
# ---------------------------------------------------------------------------

@router.post("/memories", response_model=Memory)
async def create_memory(data: MemoryCreate):
    """Store a new memory with quality validation and enhancement suggestions."""
    try:
        data, duplicate_info = enhance_and_validate(data)

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
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memories/bulk")
async def bulk_store_memories(memories: list[dict] = Body(...)):
    """Store multiple memories with full quality pipeline (same as single store).

    Accepts raw dicts and validates each item individually so one bad
    memory doesn't reject the entire batch.
    """
    import asyncio
    from pydantic import ValidationError

    results = []
    errors = []

    for i, raw in enumerate(memories):
        try:
            # Per-item Pydantic validation
            data = MemoryCreate(**raw)
        except (ValidationError, Exception) as e:
            logger.warning(f"Bulk store memory {i} validation failed: {e}")
            errors.append({"index": i, "error": str(e)})
            continue

        try:
            data, duplicate_info = enhance_and_validate(data)
            memory = await asyncio.to_thread(collections.store_memory, data)
            entry: dict = {"index": i, "id": memory.id, "status": "success"}
            if duplicate_info:
                entry["duplicate_warning"] = duplicate_info["message"]
            results.append(entry)
        except HTTPException as e:
            logger.warning(f"Bulk store memory {i} rejected: {e.detail}")
            errors.append({"index": i, "error": e.detail})
        except Exception as e:
            logger.error(f"Failed to store memory {i}: {e}")
            errors.append({"index": i, "error": str(e)})

    return {
        "stored": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }


@router.post("/memories/bulk-action")
async def bulk_action(
    operation: str = Query(..., description="Operation: archive, delete, tag, pin, reinforce"),
    memory_ids: list[str] = Body(..., description="List of memory IDs to operate on"),
    tag: Optional[str] = Query(default=None, description="Tag to add (for 'tag' operation)")
):
    """Perform bulk operations on multiple memories."""
    results = []
    errors = []
    client = collections.get_client()

    for memory_id in memory_ids:
        try:
            if operation == "archive":
                collections.archive_memory(memory_id)
                results.append({"id": memory_id, "status": "archived"})
            elif operation == "delete":
                collections.delete_memory(memory_id)
                results.append({"id": memory_id, "status": "deleted"})
            elif operation == "pin":
                collections.safe_set_payload(memory_id, {"pinned": True, "importance_score": 1.0})
                results.append({"id": memory_id, "status": "pinned"})
            elif operation == "reinforce":
                from ..forgetting import reinforce_memory as _reinforce
                _reinforce(client, collections.COLLECTION_NAME, memory_id, boost_amount=0.2)
                results.append({"id": memory_id, "status": "reinforced"})
            elif operation == "tag" and tag:
                memory = collections.get_memory(memory_id)
                if memory:
                    existing_tags = list(memory.tags or [])
                    if tag not in existing_tags:
                        existing_tags.append(tag)
                        from ..models import MemoryUpdate as MU
                        collections.update_memory(memory_id, MU(tags=existing_tags))
                    results.append({"id": memory_id, "status": "tagged"})
                else:
                    errors.append({"id": memory_id, "error": "not found"})
            else:
                errors.append({"id": memory_id, "error": f"unknown operation: {operation}"})
        except Exception as e:
            errors.append({"id": memory_id, "error": str(e)})

    return {
        "operation": operation,
        "succeeded": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }


@router.post("/memories/search", response_model=list[SearchResult])
async def search_memories(
    query: SearchQuery,
    search_mode: str = "hybrid",
    use_cache: bool = True,
    use_reranking: bool = True,
    use_graph_expansion: bool = False
):
    """
    Search memories using semantic similarity with optional enhancements.

    Args:
        query: Search query with filters
        search_mode: "semantic", "keyword", or "hybrid" (default: hybrid)
        use_cache: Enable query cache (default: true)
        use_reranking: Enable cross-encoder reranking (default: true)
        use_graph_expansion: Enable graph-based search expansion (Phase 2.1, default: false)
    """
    try:
        results = collections.search_memories(
            query,
            search_mode=search_mode,
            use_cache=use_cache,
            use_reranking=use_reranking,
            use_graph_expansion=use_graph_expansion
        )
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memories/link")
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


# ---------------------------------------------------------------------------
# Quality leaderboard / report (static paths BEFORE /{memory_id})
# ---------------------------------------------------------------------------

@router.get("/memories/quality-leaderboard")
async def get_quality_leaderboard(
    limit: int = Query(default=20, ge=1, le=100),
    memory_type: Optional[str] = Query(default=None)
):
    """Get highest-rated memories (4+ stars, minimum 2 ratings)."""
    try:
        client = collections.get_client()

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
            limit=1000,
            with_payload=True,
            with_vectors=False
        )

        leaderboard = []
        for record in records:
            payload = record.payload
            user_rating = payload.get("user_rating")
            rating_count = payload.get("user_rating_count", 0)

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

        leaderboard.sort(key=lambda x: x["user_rating"], reverse=True)
        leaderboard = leaderboard[:limit]

        return {
            "leaderboard": leaderboard,
            "count": len(leaderboard),
            "filter": {"type": memory_type, "limit": limit}
        }

    except Exception as e:
        logger.error(f"Leaderboard query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memories/quality-report")
async def get_quality_report():
    """Get quality rating distribution across all memories."""
    # Return cached result if fresh (60s TTL)
    if time.time() < _quality_report_cache["expires"] and _quality_report_cache["data"]:
        return _quality_report_cache["data"]

    try:
        client = collections.get_client()

        all_records, _ = client.scroll(
            collection_name=collections.COLLECTION_NAME,
            limit=10000,
            with_payload=["user_rating", "user_rating_count", "quality_score"],
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

        if rated_memories:
            avg_rating = sum(m["rating"] for m in rated_memories) / len(rated_memories)
            five_star = sum(1 for m in rated_memories if m["rating"] >= 4.5)
            four_star = sum(1 for m in rated_memories if 3.5 <= m["rating"] < 4.5)
            three_star = sum(1 for m in rated_memories if 2.5 <= m["rating"] < 3.5)
            two_star = sum(1 for m in rated_memories if 1.5 <= m["rating"] < 2.5)
            one_star = sum(1 for m in rated_memories if m["rating"] < 1.5)
        else:
            avg_rating = 0
            five_star = four_star = three_star = two_star = one_star = 0

        result = {
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

        _quality_report_cache["data"] = result
        _quality_report_cache["expires"] = time.time() + 60
        return result

    except Exception as e:
        logger.error(f"Quality report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# List / Get / Update / Delete (parameterised paths)
# ---------------------------------------------------------------------------

@router.get("/memories", response_model=list[Memory])
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
        accept_header = request.headers.get('accept', '')
        if 'text/html' in accept_header and 'application/json' not in accept_header:
            index_path = os.path.join(FRONTEND_BUILD, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path, media_type='text/html')
            raise HTTPException(status_code=404, detail="Dashboard not built")

        from ..collections import get_client, COLLECTION_NAME
        from ..models import Memory as MemoryModel

        client = get_client()

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

        memories = []
        for record in records:
            payload = record.payload
            payload["id"] = str(record.id)
            memories.append(MemoryModel(**payload))

        return memories
    except Exception as e:
        logger.error(f"Failed to list memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memories/{memory_id}", response_model=Memory)
async def get_memory(memory_id: str):
    """Get a single memory by ID (tracks access and reinforces strength)."""
    memory = collections.get_memory_with_tracking(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@router.patch("/memories/{memory_id}", response_model=Memory)
async def update_memory(memory_id: str, update: MemoryUpdate):
    """Update an existing memory."""
    memory = collections.update_memory(memory_id, update)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    await manager.broadcast({
        "type": "memory_updated",
        "data": memory.model_dump(mode='json')
    })

    return memory


@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory by ID."""
    success = collections.delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")

    await manager.broadcast({
        "type": "memory_deleted",
        "data": {"id": memory_id}
    })

    return {"status": "deleted", "id": memory_id}


# ---------------------------------------------------------------------------
# Special operations on a single memory
# ---------------------------------------------------------------------------

@router.post("/memories/{memory_id}/resolve", response_model=Memory)
async def resolve_error(
    memory_id: str,
    solution: str = Query(..., description="Solution that fixed the error"),
    related_memory_id: Optional[str] = Query(default=None, description="ID of related memory to auto-link with FIXES relationship"),
):
    """Mark an error memory as resolved with a solution.

    Optionally links to a related memory with a FIXES relationship.
    The underlying mark_resolved() auto-derives prevention if missing
    and recalculates quality score.
    """
    # Check if already resolved — prevent silent overwrite
    existing = collections.get_memory(memory_id)
    if existing and existing.resolved:
        raise HTTPException(
            status_code=409,
            detail="Memory already resolved. Use PATCH to update solution."
        )

    try:
        memory = collections.mark_resolved(memory_id, solution)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    # Auto-create FIXES relationship if related memory specified
    if related_memory_id:
        try:
            from ..models import RelationType
            collections.link_memories(memory_id, related_memory_id, RelationType.FIXES)
        except Exception as e:
            logger.warning(f"Failed to auto-link FIXES relationship: {e}")

    return memory


@router.post("/memories/{memory_id}/recalculate-quality")
async def recalculate_memory_quality(memory_id: str):
    """Recalculate quality score for a single memory on demand.

    Useful after manual edits or when quality score seems stale.
    Returns the fresh score and all component breakdowns.
    """
    from ..quality_tracking import QualityScoreCalculator

    try:
        client = collections.get_client()
        result = QualityScoreCalculator.recalculate_single_memory_quality(
            client, collections.COLLECTION_NAME, memory_id
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Memory not found")

        score, components = result
        return {
            "memory_id": memory_id,
            "quality_score": score,
            "components": components,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quality recalculation failed for {memory_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memories/{memory_id}/rate")
async def rate_memory(memory_id: str, request: RatingRequest):
    """
    Record user quality rating (1-5 stars) for a memory.

    Updates running average of user_rating and stores feedback.
    """
    if request.rating < 1 or request.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    try:
        memory = collections.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        old_count = memory.user_rating_count or 0
        old_rating = memory.user_rating or 0.0
        new_rating = ((old_rating * old_count) + request.rating) / (old_count + 1)

        update_payload = {
            "user_rating": new_rating,
            "user_rating_count": old_count + 1
        }

        if request.feedback:
            user_feedback = memory.user_feedback or []
            user_feedback.append({
                "rating": request.rating,
                "feedback": request.feedback,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            update_payload["user_feedback"] = user_feedback

        collections.safe_set_payload(memory_id, update_payload)

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


@router.post("/memories/{memory_id}/archive")
async def archive_memory(memory_id: str):
    """Manually archive a specific memory."""
    try:
        collections.safe_set_payload(
            memory_id,
            {"archived": True, "archived_at": datetime.now(timezone.utc).isoformat()},
            recalc_quality=False,  # No need to recalc quality for archived memories
        )
        return {"status": "archived", "id": memory_id}
    except Exception as e:
        logger.error(f"Archive failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memories/{memory_id}/pin")
async def pin_memory(memory_id: str):
    """Pin a memory so it never decays in importance."""
    try:
        collections.safe_set_payload(memory_id, {"pinned": True, "importance_score": 1.0})
        return {"status": "pinned", "id": memory_id}
    except Exception as e:
        logger.error(f"Pin failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memories/{memory_id}/unpin")
async def unpin_memory(memory_id: str):
    """Unpin a memory to allow normal decay."""
    try:
        collections.safe_set_payload(memory_id, {"pinned": False})
        return {"status": "unpinned", "id": memory_id}
    except Exception as e:
        logger.error(f"Unpin failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memories/{memory_id}/reinforce")
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
    from ..forgetting import reinforce_memory as do_reinforce

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


# ---------------------------------------------------------------------------
# Memory Version Management
# ---------------------------------------------------------------------------

@router.get("/memories/{memory_id}/versions")
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


@router.get("/memories/{memory_id}/versions/{version}")
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


@router.post("/memories/{memory_id}/versions/{version}/restore")
async def restore_version(memory_id: str, version: int):
    """
    Restore a memory to a previous version.

    Creates a new version snapshot of current state before restoring,
    allowing future restoration if needed.
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

        # Get the target version
        target_version = memory.version_history[version - 1]

        # Create snapshot of current state before restoring
        memory.create_version_snapshot(
            change_type=ChangeType.RESTORED,
            change_reason=f"Restored from version {version}",
            changed_by="user"
        )

        # Restore fields from target version (sanitize in case snapshot predates enrichment pipeline)
        from ..enhancements import clean_content, normalize_tags
        memory.content = clean_content(target_version.content) if target_version.content else target_version.content
        memory.importance_score = target_version.importance_score
        memory.tags = normalize_tags(target_version.tags.copy()) if target_version.tags else target_version.tags.copy()

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

        # Update in Qdrant with quality recalc and enrichment
        collections.safe_set_payload(
            memory_id,
            memory.model_dump(mode='json', exclude={'embedding'}),
            run_enrichment=True,  # Run enrichment on restored content
        )

        # Recalculate quality score after content restoration
        from ..quality_tracking import QualityScoreCalculator
        QualityScoreCalculator.recalculate_single_memory_quality(
            client, collections.COLLECTION_NAME, memory_id
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


@router.get("/memories/{memory_id}/versions/{v1}/diff/{v2}")
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


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

@router.post("/migrate", response_model=MigrationResult)
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


# ---------------------------------------------------------------------------
# Consolidation
# ---------------------------------------------------------------------------

@router.post("/consolidate")
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
    from ..consolidation import run_consolidation

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


@router.get("/consolidate/preview")
async def preview_consolidation(
    older_than_days: int = Query(default=7, ge=1, le=30)
):
    """Preview what would be consolidated without making changes."""
    from ..consolidation import find_consolidation_clusters, archive_old_memories

    try:
        client = collections.get_client()

        clusters = find_consolidation_clusters(
            client,
            collections.COLLECTION_NAME,
            older_than_days
        )

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


# ---------------------------------------------------------------------------
# Adaptive Forgetting (FadeMem-inspired)
# ---------------------------------------------------------------------------

@router.post("/forgetting/update")
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
    from ..forgetting import update_all_memory_strengths

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


@router.get("/forgetting/stats")
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
    from ..forgetting import get_forgetting_stats

    try:
        client = collections.get_client()
        stats = get_forgetting_stats(client, collections.COLLECTION_NAME)
        return stats
    except Exception as e:
        logger.error(f"Failed to get forgetting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forgetting/weak")
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
    from ..forgetting import get_weak_memories

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
