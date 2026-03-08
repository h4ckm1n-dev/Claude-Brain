#!/usr/bin/env python3
"""
Migrate Claude Brain data from Docker (Qdrant + Neo4j) to native SQLite.

Reads all memories, graph data, and sessions from the Docker backend API
and writes them into the SQLite database created by the Swift native app.

Usage:
    python3 scripts/migrate_to_sqlite.py [--source URL] [--db PATH] [--dry-run]

Requirements: Python 3.9+ (stdlib only, no pip dependencies)
"""

import argparse
import json
import os
import random
import sqlite3
import sys
import urllib.request
import urllib.error
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_SOURCE = "http://localhost:8100"
DEFAULT_DB = os.path.expanduser(
    "~/Library/Application Support/ClaudeBrain/claude-brain.db"
)

# Fields returned by API but absent from SQLite schema
SKIP_FIELDS = {"embedding", "state_history", "user_feedback"}

# Fields that store JSON arrays → TEXT
JSON_ARRAY_FIELDS = {
    "tags", "alternatives", "consolidated_from", "version_history",
    "relations", "relationships",
}

# Boolean fields → INTEGER (0/1)
BOOL_FIELDS = {"archived", "pinned", "resolved", "reversible"}

# All columns in the memories table (order matches schema)
MEMORY_COLUMNS = [
    "id", "type", "content", "tags", "project", "source", "context",
    "created_at", "updated_at", "last_accessed",
    "event_time", "validity_start", "validity_end",
    "memory_tier", "state", "state_changed_at",
    "archived", "archived_at", "pinned", "resolved", "resolved_at",
    "access_count", "usefulness_score", "importance_score", "recency_score",
    "quality_score", "memory_strength", "decay_rate", "last_decay_update",
    "session_id", "conversation_context", "session_sequence",
    "user_rating", "user_rating_count",
    "error_message", "stack_trace", "solution", "prevention",
    "decision", "rationale", "alternatives", "reversible", "impact",
    "consolidated_from", "consolidation_summary",
    "current_version", "version_history",
    "relations", "relationships",
]


def api_get(base_url: str, path: str) -> dict | list:
    """GET JSON from the Docker backend API."""
    url = f"{base_url}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {url}", file=sys.stderr)
        raise
    except urllib.error.URLError as e:
        print(f"  Connection error for {url}: {e.reason}", file=sys.stderr)
        raise


def transform_value(key: str, value):
    """Transform an API value to its SQLite representation."""
    if value is None:
        return None
    if key in JSON_ARRAY_FIELDS:
        if isinstance(value, list):
            return json.dumps(value)
        if isinstance(value, str):
            return value  # already JSON string
        return "[]"
    if key in BOOL_FIELDS:
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, int):
            return value
        return 0
    return value


def fetch_all_memories(base_url: str) -> list[dict]:
    """Fetch all memories (active + archived) via paginated API."""
    memories = []
    limit = 100
    offset = 0
    total = None

    print("Phase A: Fetching memories from Docker API...")
    while True:
        data = api_get(base_url, f"/memories?archived=true&limit={limit}&offset={offset}")
        items = data.get("items", [])
        if total is None:
            total = data.get("total", 0)
            print(f"  Total memories to fetch: {total}")
        memories.extend(items)
        print(f"  Fetched {len(memories)}/{total}", end="\r")
        if len(items) < limit or len(memories) >= total:
            break
        offset += limit

    print(f"  Fetched {len(memories)} memories total     ")
    return memories


def insert_memories(conn: sqlite3.Connection, memories: list[dict], dry_run: bool) -> int:
    """Insert memories into SQLite, batched in transactions of 100."""
    placeholders = ", ".join(["?"] * len(MEMORY_COLUMNS))
    sql = f"INSERT OR REPLACE INTO memories ({', '.join(MEMORY_COLUMNS)}) VALUES ({placeholders})"

    inserted = 0
    batch_size = 100

    for i in range(0, len(memories), batch_size):
        batch = memories[i : i + batch_size]
        rows = []
        for mem in batch:
            row = []
            for col in MEMORY_COLUMNS:
                # Handle API field name differences
                api_key = col
                if col == "last_accessed" and "last_accessed" not in mem:
                    api_key = "last_access"  # fallback
                if col == "importance_score" and "importance_score" not in mem:
                    # Export endpoint uses 'importance' instead of 'importance_score'
                    raw = mem.get("importance", mem.get("importance_score"))
                else:
                    raw = mem.get(api_key)
                row.append(transform_value(col, raw))
            rows.append(tuple(row))

        if not dry_run:
            conn.executemany(sql, rows)
            conn.commit()
        inserted += len(rows)
        print(f"  Inserted {inserted}/{len(memories)} memories", end="\r")

    print(f"  Inserted {inserted} memories total     ")
    return inserted


def build_graph(conn: sqlite3.Connection, memories: list[dict], base_url: str,
                projects: list[str], dry_run: bool) -> tuple[int, int]:
    """Build graph_nodes and graph_edges from memories and API graph data."""
    print("\nPhase B: Building knowledge graph...")

    nodes = {}   # id → (id, node_type, name, memory_type, content_preview, created_at)
    edges = set()  # (source_id, target_id, relation_type)
    edge_rows = []  # full edge data for insertion

    # --- Memory nodes ---
    for mem in memories:
        mid = mem["id"]
        nodes[mid] = (
            mid,
            "memory",
            None,
            mem.get("type"),
            (mem.get("content") or "")[:200],
            mem.get("created_at"),
        )

    # --- Project nodes ---
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    project_node_ids = {}
    for proj in projects:
        pid = f"project:{proj}"
        nodes[pid] = (pid, "project", proj, None, None, now_iso)
        project_node_ids[proj] = pid

    # --- Tag nodes ---
    tag_node_ids = {}
    for mem in memories:
        tags = mem.get("tags", [])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                tags = []
        for tag in tags:
            if tag and tag not in tag_node_ids:
                tid = f"tag:{tag}"
                nodes[tid] = (tid, "tag", tag, None, None, now_iso)
                tag_node_ids[tag] = tid

    print(f"  Built {len(nodes)} graph nodes ({sum(1 for n in nodes.values() if n[1]=='memory')} memory, "
          f"{len(project_node_ids)} project, {len(tag_node_ids)} tag)")

    # --- Edges from memory relations field ---
    for mem in memories:
        mid = mem["id"]
        rels = mem.get("relations", [])
        if isinstance(rels, str):
            try:
                rels = json.loads(rels)
            except json.JSONDecodeError:
                rels = []
        for rel in rels:
            if isinstance(rel, dict):
                target = rel.get("target_id") or rel.get("target")
                rtype = rel.get("relation_type") or rel.get("type") or rel.get("relation")
                if target and rtype and target in nodes:
                    key = (mid, target, rtype)
                    if key not in edges:
                        edges.add(key)
                        edge_rows.append(key)

    print(f"  Found {len(edge_rows)} edges from memory relations field")

    # --- Edges from graph API per project ---
    api_edge_count = 0
    for proj in projects:
        try:
            gdata = api_get(base_url, f"/graph/project/{proj}")
            for edge in gdata.get("edges", []):
                src = edge.get("source")
                tgt = edge.get("target")
                rtype = edge.get("type")
                if src and tgt and rtype:
                    key = (src, tgt, rtype)
                    if key not in edges:
                        # Ensure both nodes exist
                        if src not in nodes:
                            nodes[src] = (src, "memory", None, None, None, now_iso)
                        if tgt not in nodes:
                            nodes[tgt] = (tgt, "memory", None, None, None, now_iso)
                        edges.add(key)
                        edge_rows.append(key)
                        api_edge_count += 1
        except Exception as e:
            print(f"  Warning: Could not fetch graph for project '{proj}': {e}")

    print(f"  Found {api_edge_count} additional edges from graph API")

    # --- BELONGS_TO edges (memory → project) ---
    belongs_count = 0
    for mem in memories:
        mid = mem["id"]
        proj = mem.get("project")
        if proj and proj in project_node_ids:
            key = (mid, project_node_ids[proj], "BELONGS_TO")
            if key not in edges:
                edges.add(key)
                edge_rows.append(key)
                belongs_count += 1
    print(f"  Created {belongs_count} BELONGS_TO edges")

    # --- TAGGED_WITH edges (memory → tag) ---
    tagged_count = 0
    for mem in memories:
        mid = mem["id"]
        tags = mem.get("tags", [])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                tags = []
        for tag in tags:
            if tag and tag in tag_node_ids:
                key = (mid, tag_node_ids[tag], "TAGGED_WITH")
                if key not in edges:
                    edges.add(key)
                    edge_rows.append(key)
                    tagged_count += 1
    print(f"  Created {tagged_count} TAGGED_WITH edges")

    # --- Insert nodes ---
    if not dry_run:
        node_sql = "INSERT OR IGNORE INTO graph_nodes (id, node_type, name, memory_type, content_preview, created_at) VALUES (?, ?, ?, ?, ?, ?)"
        node_list = list(nodes.values())
        for i in range(0, len(node_list), 500):
            conn.executemany(node_sql, node_list[i : i + 500])
        conn.commit()

    # --- Insert edges (FK-safe: filter to nodes that were actually inserted) ---
    if not dry_run:
        # Get the set of node IDs actually in the database
        inserted_node_ids = {row[0] for row in conn.execute("SELECT id FROM graph_nodes").fetchall()}
        valid_edges = [
            e for e in edge_rows
            if e[0] in inserted_node_ids and e[1] in inserted_node_ids
        ]
        skipped = len(edge_rows) - len(valid_edges)
        if skipped:
            print(f"  Skipped {skipped} edges with missing node references")

        edge_sql = "INSERT OR IGNORE INTO graph_edges (source_id, target_id, relation_type) VALUES (?, ?, ?)"
        for i in range(0, len(valid_edges), 500):
            conn.executemany(edge_sql, valid_edges[i : i + 500])
        conn.commit()
        actual_edges = len(valid_edges)
    else:
        actual_edges = len(edge_rows)

    print(f"  Total: {len(nodes)} nodes, {actual_edges} edges")
    return len(nodes), actual_edges


def reconstruct_sessions(conn: sqlite3.Connection, memories: list[dict], dry_run: bool) -> int:
    """Reconstruct session records from memory session_id fields."""
    print("\nPhase C: Reconstructing sessions...")

    sessions = defaultdict(list)
    for mem in memories:
        sid = mem.get("session_id")
        if sid:
            sessions[sid].append(mem)

    if not sessions:
        print("  No sessions found in memories")
        return 0

    print(f"  Found {len(sessions)} unique sessions")

    session_rows = []
    for sid, mems in sessions.items():
        # Most common project in this session
        projects = [m.get("project") for m in mems if m.get("project")]
        project = Counter(projects).most_common(1)[0][0] if projects else None

        # Type breakdown
        types = Counter(m.get("type", "unknown") for m in mems)
        type_breakdown = json.dumps(dict(types))

        created_dates = [m["created_at"] for m in mems if m.get("created_at")]
        updated_dates = [m.get("updated_at") or m.get("created_at") for m in mems if m.get("updated_at") or m.get("created_at")]

        session_rows.append((
            sid,
            project,
            "closed",
            len(mems),
            None,  # summary
            type_breakdown,
            min(created_dates) if created_dates else None,
            max(updated_dates) if updated_dates else None,
            max(updated_dates) if updated_dates else None,  # closed_at
        ))

    if not dry_run:
        sql = ("INSERT OR IGNORE INTO sessions "
               "(session_id, project, status, memory_count, summary, type_breakdown, "
               "created_at, last_activity, closed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
        conn.executemany(sql, session_rows)
        conn.commit()

    print(f"  Inserted {len(session_rows)} sessions")
    return len(session_rows)


def verify(conn: sqlite3.Connection, expected_memories: int, expected_sessions: int):
    """Verify migration results."""
    print("\nPhase D: Verification...")

    mem_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    node_count = conn.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0]
    edge_count = conn.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
    session_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]

    print(f"  Memories:  {mem_count} (expected {expected_memories})")
    print(f"  Nodes:     {node_count}")
    print(f"  Edges:     {edge_count}")
    print(f"  Sessions:  {session_count} (expected {expected_sessions})")

    ok = True
    if mem_count != expected_memories:
        print(f"  MISMATCH: memories {mem_count} != {expected_memories}")
        ok = False

    if session_count != expected_sessions:
        print(f"  MISMATCH: sessions {session_count} != {expected_sessions}")
        ok = False

    # Spot-check 5 random memories
    print("\n  Spot-checking 5 random memories...")
    rows = conn.execute(
        "SELECT id, type, content, tags, quality_score, project FROM memories ORDER BY RANDOM() LIMIT 5"
    ).fetchall()
    for row in rows:
        mid, mtype, content, tags, qscore, project = row
        tags_parsed = json.loads(tags) if tags else []
        preview = (content or "")[:60].replace("\n", " ")
        print(f"    [{mtype}] {mid[:12]}... q={qscore:.2f} tags={len(tags_parsed)} proj={project} \"{preview}...\"")

    # FTS5 search test
    print("\n  FTS5 search test...")
    fts_count = conn.execute(
        "SELECT COUNT(*) FROM memories_fts WHERE memories_fts MATCH 'docker'"
    ).fetchone()[0]
    print(f"    'docker' matches: {fts_count}")
    if fts_count == 0:
        print("    WARNING: No FTS5 results for 'docker'")
    else:
        print("    FTS5 search working correctly")

    # Check types distribution
    type_rows = conn.execute(
        "SELECT type, COUNT(*) FROM memories GROUP BY type ORDER BY COUNT(*) DESC"
    ).fetchall()
    print("\n  Type distribution:")
    for ttype, tcount in type_rows:
        print(f"    {ttype}: {tcount}")

    # Check projects
    proj_rows = conn.execute(
        "SELECT project, COUNT(*) FROM memories WHERE project IS NOT NULL GROUP BY project ORDER BY COUNT(*) DESC"
    ).fetchall()
    print("\n  Project distribution:")
    for proj, pcount in proj_rows:
        print(f"    {proj}: {pcount}")

    if ok:
        print("\n  All counts match. Migration verified successfully.")
    else:
        print("\n  WARNING: Some counts did not match. Review above.")

    return ok


def main():
    parser = argparse.ArgumentParser(description="Migrate Claude Brain from Docker to SQLite")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help=f"Docker backend URL (default: {DEFAULT_SOURCE})")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"SQLite database path (default: {DEFAULT_DB})")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and transform data without writing to SQLite")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: SQLite database not found at {db_path}")
        print("Launch the native app once first to create the empty database, then retry.")
        sys.exit(1)

    # Verify Docker backend is reachable
    print(f"Source: {args.source}")
    print(f"Target: {db_path}")
    if args.dry_run:
        print("DRY RUN: No data will be written\n")
    print()

    try:
        stats = api_get(args.source, "/stats")
        print(f"Docker backend stats: {stats['total_memories']} memories, "
              f"{stats['active_memories']} active, {stats['archived_memories']} archived")
    except Exception as e:
        print(f"Error: Cannot reach Docker backend at {args.source}: {e}")
        print("Make sure Docker is running: cd ~/.claude/memory && docker compose up -d")
        sys.exit(1)

    # Get graph stats for reference
    try:
        graph_stats = api_get(args.source, "/graph/stats")
        print(f"Graph stats: {graph_stats['memory_nodes']} memory nodes, "
              f"{graph_stats['project_nodes']} project nodes, "
              f"{graph_stats['tag_nodes']} tag nodes, "
              f"{graph_stats['relationships']} relationships")
    except Exception:
        graph_stats = {}
        print("Warning: Could not fetch graph stats")

    projects = list(stats.get("by_project", {}).keys())
    print(f"Projects: {projects}\n")

    # Phase A: Fetch and insert memories
    memories = fetch_all_memories(args.source)
    if not memories:
        print("No memories fetched. Aborting.")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        mem_count = insert_memories(conn, memories, args.dry_run)

        # Phase B: Build graph
        node_count, edge_count = build_graph(conn, memories, args.source, projects, args.dry_run)

        # Phase C: Reconstruct sessions
        session_count = reconstruct_sessions(conn, memories, args.dry_run)

        # Phase D: Verify
        if not args.dry_run:
            verify(conn, expected_memories=len(memories), expected_sessions=session_count)
        else:
            print(f"\nDry run complete. Would insert: {mem_count} memories, "
                  f"{node_count} nodes, {edge_count} edges, {session_count} sessions")
    finally:
        conn.close()

    print("\nMigration complete.")
    if not args.dry_run:
        print("\nNext steps:")
        print("  1. Stop Docker:  cd ~/.claude/memory && docker compose down")
        print("  2. Change Vapor port from 8101 → 8100 in EmbeddedServer.swift")
        print("  3. Update MCP config to point to the native app")


if __name__ == "__main__":
    main()
