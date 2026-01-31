"""
Document indexing and search - separate from memories.

Documents are files indexed from the filesystem for retrieval.
Memories are structured knowledge (errors, decisions, patterns, learnings).
"""

import logging
import os
from typing import Optional, List, Dict
from qdrant_client import QdrantClient, models
from . import collections
from .embeddings import embed_query, get_embedding_dim, is_sparse_enabled

logger = logging.getLogger(__name__)

DOCUMENTS_COLLECTION = "documents"


def get_client() -> QdrantClient:
    """Get Qdrant client (shared with memories)."""
    return collections.get_client()


def init_documents_collection():
    """Initialize documents collection if it doesn't exist."""
    client = get_client()

    try:
        # Check if collection exists
        client.get_collection(DOCUMENTS_COLLECTION)
        logger.info(f"Documents collection '{DOCUMENTS_COLLECTION}' already exists")
        return
    except Exception:
        pass

    # Create documents collection
    logger.info(f"Creating documents collection: {DOCUMENTS_COLLECTION}")

    try:
        client.create_collection(
            collection_name=DOCUMENTS_COLLECTION,
            vectors_config=models.VectorParams(
                size=get_embedding_dim(),
                distance=models.Distance.COSINE
            ),
            sparse_vectors_config={
                "text": models.SparseVectorParams(
                    modifier=models.Modifier.IDF
                )
            } if is_sparse_enabled() else None
        )

        # Create payload indexes for efficient filtering
        client.create_payload_index(
            collection_name=DOCUMENTS_COLLECTION,
            field_name="file_path",
            field_schema=models.PayloadSchemaType.KEYWORD
        )

        client.create_payload_index(
            collection_name=DOCUMENTS_COLLECTION,
            field_name="file_type",
            field_schema=models.PayloadSchemaType.KEYWORD
        )

        client.create_payload_index(
            collection_name=DOCUMENTS_COLLECTION,
            field_name="folder",
            field_schema=models.PayloadSchemaType.KEYWORD
        )

        logger.info(f"Documents collection created successfully")

    except Exception as e:
        logger.error(f"Failed to create documents collection: {e}")
        raise


def search_documents(
    query: str,
    limit: int = 10,
    file_type: Optional[str] = None,
    folder: Optional[str] = None
) -> List[Dict]:
    """
    Search documents using hybrid search.

    Args:
        query: Search query
        limit: Maximum results
        file_type: Filter by file extension (e.g., ".md", ".py")
        folder: Filter by folder path

    Returns:
        List of document results with metadata
    """
    client = get_client()

    try:
        # Build filter
        must_conditions = []
        if file_type:
            must_conditions.append(
                models.FieldCondition(
                    key="file_type",
                    match=models.MatchValue(value=file_type)
                )
            )
        if folder:
            must_conditions.append(
                models.FieldCondition(
                    key="folder",
                    match=models.MatchValue(value=folder)
                )
            )

        filter_obj = models.Filter(must=must_conditions) if must_conditions else None

        # Get embeddings
        embeddings = embed_query(query, include_sparse=is_sparse_enabled())
        dense_vector = embeddings["dense"]
        sparse_vector = embeddings.get("sparse") if is_sparse_enabled() else None

        # Hybrid search
        if sparse_vector:
            results = client.query_points(
                collection_name=DOCUMENTS_COLLECTION,
                prefetch=[
                    models.Prefetch(
                        query=dense_vector,
                        using="",
                        limit=limit * 3
                    ),
                    models.Prefetch(
                        query=models.SparseVector(
                            indices=sparse_vector["indices"],
                            values=sparse_vector["values"]
                        ),
                        using="text",
                        limit=limit * 3
                    )
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=limit,
                query_filter=filter_obj
            )
        else:
            # Dense-only search
            results = client.query_points(
                collection_name=DOCUMENTS_COLLECTION,
                query=dense_vector,
                limit=limit,
                query_filter=filter_obj
            )

        # Format results
        documents = []
        for point in results.points:
            doc = {
                "id": point.id,
                "score": point.score,
                "file_path": point.payload.get("file_path"),
                "file_type": point.payload.get("file_type"),
                "folder": point.payload.get("folder"),
                "content": point.payload.get("content"),
                "chunk_index": point.payload.get("chunk_index", 0),
                "total_chunks": point.payload.get("total_chunks", 1),
                "modified_at": point.payload.get("modified_at")
            }
            documents.append(doc)

        return documents

    except Exception as e:
        logger.error(f"Document search failed: {e}")
        return []


def get_document_stats() -> Dict:
    """Get document collection statistics."""
    client = get_client()

    try:
        collection_info = client.get_collection(DOCUMENTS_COLLECTION)
        return {
            "collection": DOCUMENTS_COLLECTION,
            "total_chunks": collection_info.points_count,
            "status": str(collection_info.status)
        }
    except Exception as e:
        logger.error(f"Failed to get document stats: {e}")
        return {
            "collection": DOCUMENTS_COLLECTION,
            "total_chunks": 0,
            "status": "error",
            "error": str(e)
        }


def delete_document(file_path: str) -> bool:
    """
    Delete all chunks for a specific document.

    Args:
        file_path: Path to the document

    Returns:
        True if deleted successfully
    """
    client = get_client()

    try:
        client.delete(
            collection_name=DOCUMENTS_COLLECTION,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="file_path",
                            match=models.MatchValue(value=file_path)
                        )
                    ]
                )
            )
        )
        logger.info(f"Deleted document: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete document {file_path}: {e}")
        return False


def insert_document_chunk(
    content: str,
    file_path: str,
    chunk_index: int = 0,
    total_chunks: int = 1,
    metadata: Optional[Dict] = None
) -> str:
    """
    Insert a document chunk into the collection.

    Args:
        content: Chunk content
        file_path: Full path to the file
        chunk_index: Index of this chunk (0-based)
        total_chunks: Total number of chunks for this file
        metadata: Additional metadata (file_type, folder, modified_at, etc.)

    Returns:
        Inserted point ID
    """
    from .embeddings import embed_text
    import uuid

    client = get_client()
    metadata = metadata or {}

    try:
        # Generate embeddings
        embeddings = embed_text(content, include_sparse=collections.is_sparse_enabled())

        # Prepare payload
        payload = {
            "file_path": file_path,
            "content": content,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "file_type": metadata.get("file_type", os.path.splitext(file_path)[1]),
            "folder": metadata.get("folder", os.path.dirname(file_path)),
            "modified_at": metadata.get("modified_at"),
            **metadata  # Include any additional metadata
        }

        # Generate unique ID
        point_id = str(uuid.uuid4())

        # Prepare vectors
        vectors = {"": embeddings["dense"]}
        if embeddings.get("sparse"):
            sparse = embeddings["sparse"]
            vectors["text"] = models.SparseVector(
                indices=sparse["indices"],
                values=sparse["values"]
            )

        # Insert point
        client.upsert(
            collection_name=DOCUMENTS_COLLECTION,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=vectors,
                    payload=payload
                )
            ]
        )

        logger.debug(f"Inserted document chunk: {file_path} [{chunk_index}/{total_chunks}]")
        return point_id

    except Exception as e:
        logger.error(f"Failed to insert document chunk: {e}")
        raise


def reset_documents() -> Dict:
    """
    Delete all documents from the collection.

    Returns:
        dict with deletion stats
    """
    client = get_client()

    try:
        # Get count before deletion
        stats = get_document_stats()
        count_before = stats.get("total_chunks", 0)

        # Delete all points
        client.delete(
            collection_name=DOCUMENTS_COLLECTION,
            points_selector=models.FilterSelector(
                filter=models.Filter()  # Empty filter matches all
            )
        )

        logger.info(f"Reset documents collection: deleted {count_before} chunks")

        return {
            "deleted_chunks": count_before,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Failed to reset documents: {e}")
        return {
            "deleted_chunks": 0,
            "status": "error",
            "error": str(e)
        }
