#!/usr/bin/env python3
"""
Import Claude Brain OSX app memories into Docker stack.
Deduplicates by content similarity before importing.
"""

import sqlite3
import json
import hashlib
import sys
import urllib.request
import urllib.error
from pathlib import Path
from difflib import SequenceMatcher

# Config
SQLITE_DB = Path.home() / "Library/Application Support/ClaudeBrain/claude-brain.db"
DOCKER_API = "http://localhost:8100"
SIMILARITY_THRESHOLD = 0.85  # Content similarity above this = duplicate
BATCH_SIZE = 10  # Memories per bulk import call
DRY_RUN = "--dry-run" in sys.argv


def load_osx_memories():
    """Load all active memories from OSX SQLite database."""
    conn = sqlite3.connect(str(SQLITE_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT id, type, content, tags, project, context,
               error_message, solution, prevention,
               decision, rationale, alternatives,
               pinned, archived, resolved,
               quality_score, importance_score, memory_strength,
               created_at, updated_at
        FROM memories
        WHERE archived = 0
        ORDER BY created_at ASC
    """)
    memories = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Parse JSON fields
    for m in memories:
        if isinstance(m.get("tags"), str):
            try:
                m["tags"] = json.loads(m["tags"])
            except (json.JSONDecodeError, TypeError):
                m["tags"] = []
        if isinstance(m.get("alternatives"), str):
            try:
                m["alternatives"] = json.loads(m["alternatives"])
            except (json.JSONDecodeError, TypeError):
                m["alternatives"] = None

    return memories


def api_get(path):
    """GET from Docker stack API."""
    req = urllib.request.Request(
        f"{DOCKER_API}{path}",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def api_post(path, data):
    """POST JSON to Docker stack API."""
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{DOCKER_API}{path}",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def load_docker_memories():
    """Load all memories from Docker stack API (handles pagination)."""
    all_memories = []
    offset = 0
    limit = 100

    while True:
        data = api_get(f"/memories?limit={limit}&offset={offset}")
        if isinstance(data, dict):
            items = data.get("items", [])
            total = data.get("total", 0)
            all_memories.extend(items)
            if len(all_memories) >= total or not items:
                break
            offset += limit
        elif isinstance(data, list):
            all_memories.extend(data)
            break
        else:
            break

    return all_memories


def normalize_content(text):
    """Normalize content for comparison."""
    if not text:
        return ""
    return " ".join(text.lower().split())


def content_hash(text):
    """Quick hash for exact match detection."""
    return hashlib.md5(normalize_content(text).encode()).hexdigest()


def is_similar(text1, text2, threshold=SIMILARITY_THRESHOLD):
    """Check if two texts are similar enough to be considered duplicates."""
    n1 = normalize_content(text1)
    n2 = normalize_content(text2)
    if not n1 or not n2:
        return False
    # Quick exact match
    if n1 == n2:
        return True
    # Length-based pre-filter (if lengths differ by >50%, unlikely similar)
    len_ratio = min(len(n1), len(n2)) / max(len(n1), len(n2))
    if len_ratio < 0.5:
        return False
    # Sequence matching
    return SequenceMatcher(None, n1, n2).ratio() >= threshold


def word_count(text):
    """Count words in text."""
    return len(text.split()) if text else 0


def format_for_import(mem):
    """Format an OSX memory for the Docker stack bulk import API.
    Returns None if the memory can't meet quality requirements."""
    content = mem["content"]
    context = mem.get("context", "")

    # If content is too short, try merging with context
    if word_count(content) < 10 and context:
        content = f"{content}\n{context}"

    # Still too short or just a file path log — skip
    if word_count(content) < 10 or len(content) < 50:
        return None

    payload = {
        "type": mem["type"],
        "content": content,
        "tags": mem.get("tags", []),
        "project": mem.get("project"),
        "context": mem.get("context"),
    }

    # Ensure minimum 3 tags
    if len(payload.get("tags", [])) < 3:
        # Pad with project name and type
        tags = list(payload.get("tags", []))
        if mem.get("project") and mem["project"] not in tags:
            tags.append(mem["project"])
        if mem["type"] not in tags:
            tags.append(mem["type"])
        if "imported" not in tags:
            tags.append("imported")
        payload["tags"] = tags

    # Type-specific fields
    if mem["type"] == "error":
        if mem.get("error_message"):
            payload["error_message"] = mem["error_message"]
        if mem.get("solution"):
            payload["solution"] = mem["solution"]
        if mem.get("prevention"):
            payload["prevention"] = mem["prevention"]
    elif mem["type"] == "decision":
        if mem.get("rationale"):
            payload["rationale"] = mem["rationale"]
        if mem.get("alternatives"):
            payload["alternatives"] = mem["alternatives"]
        if mem.get("decision"):
            payload["decision"] = mem["decision"]
    elif mem["type"] == "docs":
        if not payload.get("context"):
            payload["source"] = "osx-app-import"

    # Remove None values
    return {k: v for k, v in payload.items() if v is not None}


def bulk_import(memories):
    """Import a batch of memories via the Docker stack API."""
    status, data = api_post("/memories/bulk", memories)  # API expects raw list
    if status >= 400:
        print(f"  ERROR {status}: {str(data)[:200]}")
        return 0
    if isinstance(data, dict):
        stored = data.get("stored", 0)
        errors = data.get("errors", [])
        if errors:
            for err in errors[:2]:  # Show first 2 errors
                print(f"    WARN: {str(err.get('error', ''))[:120]}")
        return stored
    return len(memories)


def main():
    print("=" * 60)
    print("Claude Brain: OSX -> Docker Stack Memory Import")
    print("=" * 60)
    if DRY_RUN:
        print("  MODE: DRY RUN (no changes will be made)")
    print()

    # Step 1: Load both sources
    print("[1/4] Loading OSX memories from SQLite...")
    osx_memories = load_osx_memories()
    print(f"  Found {len(osx_memories)} active memories")

    print("[2/4] Loading Docker stack memories...")
    docker_memories = load_docker_memories()
    print(f"  Found {len(docker_memories)} memories")

    # Step 2: Build content index from Docker stack for dedup
    print("[3/4] Deduplicating...")
    docker_hashes = set()
    docker_contents = []
    for m in docker_memories:
        c = m.get("content", "")
        docker_hashes.add(content_hash(c))
        docker_contents.append(normalize_content(c))

    # Categorize OSX memories
    exact_dupes = []
    similar_dupes = []
    unique = []

    for i, mem in enumerate(osx_memories):
        c = mem["content"]
        h = content_hash(c)

        if h in docker_hashes:
            exact_dupes.append(mem)
            continue

        # Check similarity against Docker memories
        is_dupe = False
        norm_c = normalize_content(c)
        for dc in docker_contents:
            if is_similar(norm_c, dc):
                similar_dupes.append(mem)
                is_dupe = True
                break

        if not is_dupe:
            unique.append(mem)

        # Progress
        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(osx_memories)}...")

    print(f"\n  Results:")
    print(f"    Exact duplicates (skip):   {len(exact_dupes)}")
    print(f"    Similar duplicates (skip): {len(similar_dupes)}")
    print(f"    Unique (will import):      {len(unique)}")

    # Breakdown by type
    type_counts = {}
    for m in unique:
        t = m["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    if type_counts:
        print(f"\n  Unique by type:")
        for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"    {t}: {c}")

    # Breakdown by project
    proj_counts = {}
    for m in unique:
        p = m.get("project", "(none)")
        proj_counts[p] = proj_counts.get(p, 0) + 1
    if proj_counts:
        print(f"\n  Unique by project:")
        for p, c in sorted(proj_counts.items(), key=lambda x: -x[1]):
            print(f"    {p}: {c}")

    if not unique:
        print("\n  Nothing to import - all memories already exist in Docker stack!")
        return

    if DRY_RUN:
        print(f"\n  DRY RUN: Would import {len(unique)} memories. Run without --dry-run to import.")
        return

    # Step 3: Import in batches
    print(f"\n[4/4] Importing {len(unique)} unique memories in batches of {BATCH_SIZE}...")
    imported = 0
    failed = 0

    skipped_quality = 0
    for i in range(0, len(unique), BATCH_SIZE):
        batch = unique[i : i + BATCH_SIZE]
        formatted = [format_for_import(m) for m in batch]
        # Filter out None (quality-rejected)
        valid = [m for m in formatted if m is not None]
        skipped_quality += len(batch) - len(valid)

        if not valid:
            print(f"  Batch {i // BATCH_SIZE + 1}: 0/{len(batch)} (all skipped — too short)")
            continue

        count = bulk_import(valid)
        imported += count
        if count < len(valid):
            failed += len(valid) - count

        print(f"  Batch {i // BATCH_SIZE + 1}: {count}/{len(batch)} imported")

    print(f"\n{'=' * 60}")
    print(f"  DONE: {imported} imported, {failed} failed")
    print(f"        {len(exact_dupes) + len(similar_dupes)} skipped (duplicates)")
    print(f"        {skipped_quality} skipped (too short / low quality)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
