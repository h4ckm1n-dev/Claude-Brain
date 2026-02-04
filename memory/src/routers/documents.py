"""Document and indexing endpoints.

Handles document insertion, search, stats, deletion, reset,
and folder indexing configuration.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from .. import documents as doc_module
from ..server_deps import manager
import json
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])

# ---------------------------------------------------------------------------
# Indexing configuration helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Document Indexing Configuration (3 endpoints)
# ---------------------------------------------------------------------------

@router.get("/indexing/folders")
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


@router.post("/indexing/folders")
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


@router.post("/indexing/reindex")
async def trigger_reindex(folders: Optional[list[str]] = Query(default=None)):
    """Trigger manual reindexing of specified folders."""
    from ..process_manager import ProcessManager
    process_manager = ProcessManager()

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


# ---------------------------------------------------------------------------
# Document Search & Management (5 endpoints)
# Documents are separate from memories - for filesystem content retrieval
# ---------------------------------------------------------------------------

@router.post("/documents/insert")
async def insert_document_endpoint(request_data: dict):
    """
    Insert a document chunk into the documents collection.

    Used by indexing scripts to add filesystem content.
    """
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

        point_id = doc_module.insert_document_chunk(
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


@router.post("/documents/search")
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
    try:
        results = doc_module.search_documents(
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


@router.get("/documents/stats")
async def get_document_stats():
    """Get document collection statistics."""
    try:
        stats = doc_module.get_document_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get document stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{file_path:path}")
async def delete_document_endpoint(file_path: str):
    """Delete a specific document from the index."""
    try:
        success = doc_module.delete_document(file_path)

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


@router.post("/documents/reset")
async def reset_documents_endpoint(confirm: bool = Query(default=False)):
    """Delete all indexed documents (separate from memory reset)."""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to reset documents"
        )

    try:
        result = doc_module.reset_documents()

        await manager.broadcast({
            "type": "documents_reset",
            "data": {"deleted_chunks": result.get("deleted_chunks", 0)}
        })

        return result

    except Exception as e:
        logger.error(f"Failed to reset documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
