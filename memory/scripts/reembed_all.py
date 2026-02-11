"""Re-embed all memories with enriched embedding text.

Rebuilds dense (and optionally sparse) vectors for every memory using the
current build_embedding_text() and build_composite_embedding() pipelines.
Payload is left untouched — only vectors are replaced.

Usage:
    python -m scripts.reembed_all [--batch-size 50] [--dry-run] [--no-composite]

Inside Docker:
    docker compose exec claude-mem-core python -m scripts.reembed_all
"""

import argparse
import logging
import os
import sys
import time

# Ensure project root is on path when running as module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient
from qdrant_client.http import models

from src.embedding_client import embed_text, is_sparse_enabled
from src.enhancements import build_embedding_text, build_composite_embedding
from src.models import MemoryType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("reembed")

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "memories"


class _MemoryProxy:
    """Lightweight proxy to satisfy build_embedding_text() and build_composite_embedding()
    without constructing a full Pydantic Memory object (which may reject legacy payloads)."""

    def __init__(self, payload: dict):
        self._p = payload

    def __getattr__(self, name):
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        val = self._p.get(name)
        # type field needs .value attribute
        if name == "type":
            return _TypeProxy(val)
        return val


class _TypeProxy:
    def __init__(self, val):
        self.value = val if isinstance(val, str) else str(val) if val else "context"

    def __str__(self):
        return self.value


def reembed_all(
    batch_size: int = 50,
    dry_run: bool = False,
    use_composite: bool = True,
):
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # Count total points
    info = client.get_collection(COLLECTION_NAME)
    total = info.points_count
    logger.info(f"Collection '{COLLECTION_NAME}' has {total} points")

    if total == 0:
        logger.info("Nothing to re-embed.")
        return

    processed = 0
    updated = 0
    errors = 0
    offset = None
    start_time = time.time()

    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        if not points:
            break

        batch_vectors = []
        for point in points:
            processed += 1
            try:
                proxy = _MemoryProxy(point.payload)
                enriched_text = build_embedding_text(proxy)

                if use_composite:
                    dense = build_composite_embedding(proxy, embed_text)
                else:
                    dense = embed_text(enriched_text)["dense"]

                vectors = {"dense": dense}

                if is_sparse_enabled():
                    sparse_result = embed_text(enriched_text, include_sparse=True)
                    if "sparse" in sparse_result:
                        vectors["sparse"] = models.SparseVector(
                            indices=sparse_result["sparse"]["indices"],
                            values=sparse_result["sparse"]["values"],
                        )

                if not dry_run:
                    batch_vectors.append(
                        models.PointVectors(
                            id=str(point.id),
                            vector=vectors,
                        )
                    )
                updated += 1

            except Exception as exc:
                errors += 1
                logger.warning(f"  [{processed}/{total}] FAILED {point.id}: {exc}")

        # Flush batch
        if batch_vectors and not dry_run:
            client.update_vectors(
                collection_name=COLLECTION_NAME,
                points=batch_vectors,
            )

        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        logger.info(
            f"  [{processed}/{total}] updated={updated} errors={errors} "
            f"({rate:.1f} pts/s){' [DRY RUN]' if dry_run else ''}"
        )

        if offset is None:
            break

    elapsed = time.time() - start_time
    logger.info(
        f"Done. {updated}/{total} re-embedded, {errors} errors, "
        f"{elapsed:.1f}s elapsed.{' [DRY RUN — nothing written]' if dry_run else ''}"
    )


def main():
    parser = argparse.ArgumentParser(description="Re-embed all memories with enriched text")
    parser.add_argument("--batch-size", type=int, default=50, help="Points per batch (default: 50)")
    parser.add_argument("--dry-run", action="store_true", help="Log changes without writing")
    parser.add_argument("--no-composite", action="store_true", help="Use single embedding instead of composite")
    args = parser.parse_args()

    reembed_all(
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        use_composite=not args.no_composite,
    )


if __name__ == "__main__":
    main()
