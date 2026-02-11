"""Rebuild Neo4j graph from Qdrant memories.

Creates Memory nodes, Project/Tag links, and inter-memory relationships
for all memories currently in Qdrant.

Usage:
    docker compose exec claude-mem-core python -m scripts.rebuild_graph
"""

import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from qdrant_client import QdrantClient

from src.graph import (
    is_graph_enabled, reset_graph, create_memory_node,
    create_relationship, init_graph_schema
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION = "memories"


def rebuild():
    if not is_graph_enabled():
        logger.error("Neo4j graph is not enabled. Cannot rebuild.")
        return

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # Reset graph and reinitialize schema
    logger.info("Resetting Neo4j graph...")
    reset_graph()
    init_graph_schema()

    # Scroll all memories
    all_points = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        all_points.extend(points)
        if offset is None:
            break

    logger.info(f"Found {len(all_points)} memories to rebuild graph for")

    # Phase 1: Create all memory nodes
    nodes_created = 0
    start = time.time()

    for point in all_points:
        p = point.payload or {}
        memory_id = str(point.id)
        memory_type = p.get("type", "context")
        content = p.get("content", "")
        project = p.get("project")
        tags = p.get("tags", [])

        created_at = None
        if p.get("created_at"):
            try:
                created_at = datetime.fromisoformat(p["created_at"])
            except (ValueError, TypeError):
                created_at = datetime.now(timezone.utc)

        ok = create_memory_node(
            memory_id=memory_id,
            memory_type=memory_type,
            content_preview=content[:200],
            project=project,
            tags=tags,
            created_at=created_at,
        )
        if ok:
            nodes_created += 1

        if nodes_created % 20 == 0 and nodes_created > 0:
            logger.info(f"  Nodes: {nodes_created}/{len(all_points)}")

    logger.info(f"Created {nodes_created} graph nodes in {time.time() - start:.1f}s")

    # Phase 2: Create inter-memory relationships from Qdrant relations payload
    rels_created = 0
    rels_start = time.time()

    for point in all_points:
        p = point.payload or {}
        source_id = str(point.id)
        relations = p.get("relations", [])

        for rel in relations:
            target_id = rel.get("target_id")
            rel_type = rel.get("relation_type", "related")
            if not target_id:
                continue

            graph_rel_type = rel_type.upper()
            ok = create_relationship(source_id, target_id, graph_rel_type)
            if ok:
                rels_created += 1

    elapsed = time.time() - start
    logger.info(f"Created {rels_created} relationships in {time.time() - rels_start:.1f}s")
    logger.info(f"Graph rebuild complete: {nodes_created} nodes, {rels_created} relationships ({elapsed:.1f}s total)")


if __name__ == "__main__":
    rebuild()
