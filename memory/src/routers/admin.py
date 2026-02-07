"""Admin, health, notifications, settings, processes, scheduler, database, and export endpoints."""

import os
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel

from .. import collections
from .. import notifications as notif_module
from .. import suggestions as suggestions_module
from ..models import HealthResponse, StatsResponse
from ..embeddings import get_embedding_dim, is_sparse_enabled
from ..process_manager import ProcessManager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Admin"])

# Frontend build path
FRONTEND_BUILD = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))

# Settings file path
SETTINGS_FILE = Path.home() / ".claude" / "memory" / "data" / "settings.json"

# Indexing config path
INDEXING_CONFIG_FILE = os.path.expanduser("~/.claude/memory/data/indexing-config.json")

# Process manager singleton
process_manager = ProcessManager()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _broadcast(message: dict):
    """Broadcast a WebSocket message if the connection manager is available."""
    try:
        from ..server_deps import manager
        await manager.broadcast(message)
    except Exception:
        pass


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
            "cacheTtlHours": 24,
            "autoSupersedeEnabled": True,
            "autoSupersedeThreshold": 0.85,
            "autoSupersedeUpper": 0.91,
            "dedupThreshold": 0.92
        }
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(default_settings, f, indent=2)


def ensure_indexing_config():
    """Ensure indexing config file exists with defaults."""
    os.makedirs(os.path.dirname(INDEXING_CONFIG_FILE), exist_ok=True)
    if not os.path.exists(INDEXING_CONFIG_FILE):
        default_config = {
            "folders": [],
            "exclude_patterns": [".git", "node_modules", "__pycache__"],
            "file_extensions": [".txt", ".md", ".pdf", ".docx", ".py", ".js", ".ts", ".json", ".yaml"],
            "auto_index": False
        }
        with open(INDEXING_CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=2)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class NotificationCreate(BaseModel):
    """Request model for creating notifications."""
    type: str
    title: str
    message: str
    data: dict = {}


# ===========================================================================
# Health & Status Endpoints
# ===========================================================================


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and Qdrant connection."""
    from ..graph import is_graph_enabled
    from .. import documents

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


@router.get("/health/detailed")
async def detailed_health_check():
    """Get detailed health information about all system components."""
    from ..graph import is_graph_enabled
    import time

    start_time = time.time()
    health_info = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": 0,
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
            from ..graph import get_graph_stats
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
    ws_count = 0
    try:
        from ..server_deps import manager
        ws_count = len(manager.active_connections)
    except Exception:
        pass

    health_info["features"] = {
        "hybrid_search": is_sparse_enabled(),
        "graph_relationships": is_graph_enabled(),
        "semantic_cache": True,
        "cross_encoder_reranking": True,
        "learned_fusion": os.getenv("USE_LEARNED_FUSION", "false").lower() == "true",
        "query_understanding": os.getenv("USE_QUERY_UNDERSTANDING", "false").lower() == "true",
        "websocket": ws_count > 0
    }

    # Performance metrics
    response_time = (time.time() - start_time) * 1000
    health_info["performance"] = {
        "health_check_ms": round(response_time, 2),
        "active_websocket_connections": ws_count
    }

    # Try to get cache stats
    try:
        from ..cache import get_cache_stats
        cache_stats = get_cache_stats()
        health_info["performance"]["cache"] = cache_stats
    except Exception:
        pass

    return health_info


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get memory collection statistics."""
    stats = collections.get_stats()
    return StatsResponse(**stats)


@router.get("/cache/stats")
async def get_cache_stats():
    """Get query cache statistics."""
    from ..cache import get_cache_stats
    return get_cache_stats()


@router.post("/cache/clear")
async def clear_cache():
    """Clear the query cache."""
    from ..cache import clear_cache
    client = collections.get_client()
    cleared = clear_cache(client)
    return {"status": "cleared", "entries_removed": cleared}


# ===========================================================================
# Notification Endpoints
# ===========================================================================


@router.get("/notifications")
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


@router.post("/notifications")
async def create_notification(notification: NotificationCreate):
    """Create a new notification."""
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


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark a notification as read."""
    success = notif_module.mark_notification_read(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "read", "id": notification_id}


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read():
    """Mark all notifications as read."""
    count = notif_module.mark_all_read()
    return {"status": "success", "marked_count": count}


@router.delete("/notifications/{notification_id}")
async def delete_notification(notification_id: str):
    """Delete a notification."""
    success = notif_module.delete_notification(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "deleted", "id": notification_id}


@router.delete("/notifications")
async def clear_all_notifications():
    """Clear all notifications."""
    count = notif_module.clear_all_notifications()
    return {"status": "cleared", "count": count}


@router.get("/notifications/stats")
async def get_notification_stats():
    """Get notification statistics."""
    return notif_module.get_notification_stats()


# ===========================================================================
# Settings Endpoints
# ===========================================================================


@router.get("/settings")
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


@router.post("/settings")
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


# ===========================================================================
# Suggestion Throttling Endpoints
# ===========================================================================


@router.get("/suggestions/should-show")
async def should_show_suggestions(user_id: str = Query(default="default")):
    """Check if suggestions should be shown based on throttling rules."""
    try:
        # Load user settings
        settings = {}
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
        except Exception:
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


@router.post("/suggestions/feedback")
async def record_suggestion_feedback(
    user_id: str = Query(default="default"),
    was_useful: bool = Query(...)
):
    """Record if a suggestion was useful (for quality tracking)."""
    suggestions_module.record_suggestion_quality(user_id, was_useful)
    return {"status": "recorded"}


@router.get("/suggestions/stats")
async def get_suggestion_stats(user_id: Optional[str] = Query(default=None)):
    """Get suggestion throttling statistics."""
    return suggestions_module.get_throttler_stats(user_id)


# ===========================================================================
# Process Control Endpoints
# ===========================================================================


@router.get("/processes/watcher/status")
async def get_watcher_status():
    """Check if file watcher is running."""
    return process_manager.get_watcher_status()


@router.post("/processes/watcher/start")
async def start_watcher(interval: int = Query(default=30, ge=10, le=300)):
    """Start file watcher daemon."""
    try:
        result = process_manager.start_watcher(interval=interval)

        # Broadcast to WebSocket clients
        await _broadcast({
            "type": "process_status_changed",
            "data": {"process": "watcher", "status": "started"}
        })

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting watcher: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/processes/watcher/stop")
async def stop_watcher():
    """Stop file watcher daemon."""
    try:
        result = process_manager.stop_watcher()

        # Broadcast to WebSocket clients
        await _broadcast({
            "type": "process_status_changed",
            "data": {"process": "watcher", "status": "stopped"}
        })

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error stopping watcher: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# Job Execution Endpoints
# ===========================================================================


@router.post("/jobs/prune")
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
        await _broadcast({
            "type": "job_started",
            "data": {"job_id": job_id, "script": "prune", "args": args}
        })

        return {"job_id": job_id, "status": "started"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting prune job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/tag")
async def execute_tag_job(limit: int = Query(default=1000, ge=1, le=10000)):
    """Execute NLP tagging job."""
    try:
        args = [f"--limit={limit}"]
        job_id = process_manager.execute_script("nlp_tagger", args)

        # Broadcast to WebSocket clients
        await _broadcast({
            "type": "job_started",
            "data": {"job_id": job_id, "script": "tag", "args": args}
        })

        return {"job_id": job_id, "status": "started"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting tag job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get job status by ID."""
    job = process_manager.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return asdict(job)


@router.get("/jobs")
async def list_jobs(limit: int = Query(default=20, ge=1, le=100)):
    """List recent jobs."""
    jobs = process_manager.list_jobs(limit=limit)
    return [asdict(job) for job in jobs]


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel running job."""
    success = process_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or not running")
    return {"status": "cancelled", "job_id": job_id}


# ===========================================================================
# Log Access Endpoints
# ===========================================================================


@router.get("/logs/{log_name}")
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


@router.post("/logs/{log_name}/clear")
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


# ===========================================================================
# Scheduler Endpoints
# ===========================================================================


@router.get("/scheduler/status")
async def scheduler_status():
    """Get background scheduler status."""
    try:
        from ..scheduler import get_scheduler_status
        return get_scheduler_status()
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/jobs/{job_id}/trigger")
async def trigger_scheduled_job(job_id: str):
    """Manually trigger a scheduled job."""
    try:
        from ..scheduler import trigger_job
        success = trigger_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found or scheduler disabled")
        return {"status": "triggered", "job_id": job_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/trigger-all")
async def trigger_all_scheduled_jobs():
    """Trigger all scheduled jobs at once."""
    try:
        from ..scheduler import get_scheduler
        from datetime import datetime, timezone

        scheduler = get_scheduler()
        if not scheduler or scheduler == "disabled":
            raise HTTPException(status_code=503, detail="Scheduler not available")

        triggered = []
        failed = []
        now = datetime.now(timezone.utc)
        for job in scheduler.get_jobs():
            try:
                job.modify(next_run_time=now)
                triggered.append(job.id)
            except Exception as e:
                failed.append({"job_id": job.id, "error": str(e)})

        return {
            "status": "triggered",
            "triggered": triggered,
            "failed": failed,
            "total": len(triggered),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering all jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# Database Management Endpoints
# ===========================================================================


@router.post("/database/reset")
async def reset_database(confirm: bool = Query(default=False)):
    """Reset database by deleting all memories from Qdrant and Neo4j graph."""
    from ..graph import reset_graph
    from qdrant_client import models

    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to reset database"
        )

    try:
        # Delete all points from the vector collection
        client = collections.get_client()

        # Delete all points using a filter that matches everything
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
        await _broadcast({
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


@router.get("/database/stats")
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


# ===========================================================================
# Data Export & Backup Endpoints
# ===========================================================================


@router.get("/export/memories")
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
        from ..export import MemoryExporter

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


@router.post("/backup")
async def create_manual_backup(backup_name: Optional[str] = Query(default=None)):
    """Create full system backup (memories + graph data)."""
    try:
        from ..export import MemoryExporter

        result = MemoryExporter.create_backup(backup_name)
        return result

    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backups")
async def list_backups():
    """List all available backups."""
    try:
        from ..export import MemoryExporter

        backups = MemoryExporter.list_backups()
        return {"backups": backups, "count": len(backups)}

    except Exception as e:
        logger.error(f"Backup list failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
