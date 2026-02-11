"""Restore memories from a JSON export file.

Re-inserts memories using direct Qdrant upsert with new embeddings from the
current embedding model. Preserves original IDs, metadata, and relations.

Usage:
    docker compose exec claude-mem-core python -m scripts.restore_from_export exports/20260210-203305.json
"""

import argparse
import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient
from qdrant_client.http import models

from src.embedding_client import embed_text, embed_texts, is_sparse_enabled, get_embedding_dim
from src.enhancements import build_embedding_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION = "memories"


def restore(export_path: str, batch_size: int = 20, dry_run: bool = False):
    with open(export_path) as f:
        data = json.load(f)

    memories = data.get("memories", data if isinstance(data, list) else [])
    logger.info(f"Loaded {len(memories)} memories from {export_path}")
    logger.info(f"Embedding dim: {get_embedding_dim()}, sparse: {is_sparse_enabled()}")

    if dry_run:
        logger.info("DRY RUN — no changes will be made")
        return

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    restored = 0
    errors = 0
    start = time.time()

    for i in range(0, len(memories), batch_size):
        batch = memories[i:i + batch_size]

        # Build embedding texts
        embed_texts_list = []
        for m in batch:
            parts = [m.get("content", "")]
            if m.get("context"):
                parts.append(m["context"])
            if m.get("error_message"):
                parts.append(m["error_message"])
            if m.get("solution"):
                parts.append(m["solution"])
            if m.get("tags"):
                parts.append(" ".join(m["tags"]))
            embed_texts_list.append(" ".join(parts))

        # Batch embed
        try:
            results = embed_texts(embed_texts_list, include_sparse=is_sparse_enabled())
        except Exception as e:
            logger.error(f"Batch embed failed at {i}: {e}")
            errors += len(batch)
            continue

        # Build points
        points = []
        for j, (m, emb) in enumerate(zip(batch, results)):
            try:
                vectors = {"dense": emb["dense"]}
                if "sparse" in emb and emb["sparse"]:
                    vectors["sparse"] = models.SparseVector(
                        indices=emb["sparse"]["indices"],
                        values=emb["sparse"]["values"]
                    )

                # Build payload (everything except embedding)
                payload = dict(m)
                payload.pop("embedding", None)

                points.append(models.PointStruct(
                    id=m["id"],
                    vector=vectors,
                    payload=payload,
                ))
            except Exception as e:
                logger.warning(f"Failed to prepare {m.get('id', '?')}: {e}")
                errors += 1

        # Upsert batch
        if points:
            try:
                client.upsert(collection_name=COLLECTION, points=points)
                restored += len(points)
                elapsed = time.time() - start
                logger.info(f"Restored {restored}/{len(memories)} ({elapsed:.1f}s)")
            except Exception as e:
                logger.error(f"Upsert failed at batch {i}: {e}")
                errors += len(points)

    elapsed = time.time() - start
    logger.info(f"Done: {restored} restored, {errors} errors in {elapsed:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore memories from export")
    parser.add_argument("export_file", help="Path to JSON export file")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    restore(args.export_file, batch_size=args.batch_size, dry_run=args.dry_run)
