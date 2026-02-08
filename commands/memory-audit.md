---
description: "Deep audit and optimize the memory database — diagnostics, cleanup, consolidation, and full report"
allowed-tools: ["mcp__memory__*", "Bash"]
model: sonnet
---

# Memory Audit & Optimization Pipeline

Execute all three phases in order. Do NOT skip any phase.

---

## PHASE 1: AUDIT (Diagnostics)

Run all of these in parallel — they are all read-only:

**MCP tool calls (parallel batch 1):**
1. `memory_stats()` — capture total counts, by-type breakdown, by-project breakdown
2. `graph_stats()` — capture node count, relationship count, projects
3. `error_trends(time_window_days=90)` — capture recurring error patterns, spikes, clusters
4. `knowledge_gaps()` — capture topics with errors but no patterns, sparse projects
5. `get_weak_memories(strength_threshold=0.3, limit=50)` — capture fading memories
6. `graph_contradictions(limit=20)` — capture contradicting memory pairs
7. `brain_detect_conflicts(limit=50)` — capture semantic conflicts

**Bash curl calls (parallel batch 2):**
8. `curl -s http://localhost:8100/memories/quality-report` — rating distribution, quality scores
9. `curl -s http://localhost:8100/memories/quality-leaderboard?limit=10` — top quality memories
10. `curl -s http://localhost:8100/quality/lifecycle/transitions` — state transition history

**Bash curl calls (parallel batch 3 — for auto-resolve/link):**
11. Scroll ALL non-archived memories from Qdrant to get full payloads:
```bash
curl -s 'http://localhost:6333/collections/memories/points/scroll' \
  -H 'Content-Type: application/json' \
  -d '{"filter":{"must":[{"key":"archived","match":{"value":false}}]},"limit":500,"with_payload":true,"with_vector":false}'
```
Parse the response into a local list of all memories with their full payloads.

Save a `before_stats` snapshot with these values:
- `total` — total memory count
- `by_type` — count per memory type (error, decision, pattern, learning, docs, context)
- `graph_nodes` — node count
- `graph_edges` — relationship count
- `weak_count` — number of weak memories returned
- `contradiction_count` — number of contradictions found
- `error_clusters` — number of error clusters
- `knowledge_gaps` — list of gap descriptions

Also build these derived lists from the Qdrant scroll for Phase 2:
- `unresolved_errors` — error memories where `resolved` is false/missing BUT `solution` exists (non-empty)
- `unlinked_pairs` — pairs of memories that share the same `session_id` but have no relationships between them (check `relations` array in payload)
- `boilerplate_memories` — memories tagged with `auto-captured` AND content starts with boilerplate phrases: "session started for project", "session closed at", "session ended at", "session resumed for project"
- `orphan_memories` — memories with 0 entries in their `relations` array (completely isolated)
- `tag_clusters` — group memories by overlapping tags (3+ shared tags = cluster). Within each cluster, find pairs with no relationship.

---

## PHASE 2: OPTIMIZE (Mutations — strictly sequential)

Execute these steps in order. After each step, log what was done (count of items affected).

### Step 0: Refresh quality scores & auto-rate
Run these two curl calls sequentially:
1. `curl -s -X POST http://localhost:8100/quality/update` — recompute quality_score for all memories
2. `curl -s -X POST http://localhost:8100/quality/auto-rate` — derive user_rating from quality_score for unrated memories
Log: "Quality: updated N scores, auto-rated N memories (avg {avg}/5)"

### Step 1: Consolidate old memories
Call `consolidate_memories(older_than_days=14, dry_run=false)`.
Log: "Consolidated: merged N duplicate groups"

### Step 2: Run relationship inference
Call `run_inference(inference_type="all")`.
Log: "Inference: discovered N new relationships"

### Step 3: Dream mode
Call `brain_dream(duration=30)`.
Log: "Dream: replayed N memories, found N connections"

### Step 4: Replay important memories
Call `brain_replay(count=20, importance_threshold=0.6)`.
Log: "Replay: strengthened N important memories"

### Step 5: Resolve contradictions
Using the contradictions found in Phase 1 (`graph_contradictions` results):
- For each contradicting pair, determine which memory is newer (by timestamp/ID)
- Call `link_memories(source_id=<newer>, target_id=<older>, relation="supersedes")` for each pair
- If no contradictions were found, log "No contradictions to resolve"
Log: "Contradictions: resolved N via supersedes links"

### Step 6: Auto-resolve errors with solutions
From `unresolved_errors` built in Phase 1:
- For each error memory that has a `solution` field but `resolved` is false/missing:
  - Call: `curl -s -X POST "http://localhost:8100/memories/{memory_id}/resolve?solution={url_encoded_solution}"`
  - The solution text comes from the memory's own `solution` field
- If none found, log "No unresolved errors with solutions"
Log: "Auto-resolved: marked N errors as resolved (had solutions but weren't flagged)"

### Step 7: Auto-link session siblings
From `unlinked_pairs` built in Phase 1 (memories in same session with no relationships):
- Sort each session's memories by `session_sequence` or `created_at`
- For consecutive pairs (memory[i] → memory[i+1]), call:
  `link_memories(source_id=<later>, target_id=<earlier>, relation="follows")`
- Skip if they already have a relationship of any kind
- If none found, log "No unlinked session siblings"
Log: "Session links: created N 'follows' links between session siblings"

### Step 8: Auto-link by tag affinity
From `tag_clusters` built in Phase 1 (pairs of memories sharing 3+ tags but no relationship):
- For each unlinked pair sharing 3+ tags:
  - If one is `error` and the other is `learning`/`pattern`/`decision` → use relation `"fixes"`
  - If one is `decision` and the other is `pattern` → use relation `"supports"`
  - Otherwise → use relation `"related"`
- Cap at 20 new links per audit run to avoid noise
- If none found, log "No tag-affinity pairs to link"
Log: "Tag links: created N relationships between tag-similar memories"

### Step 9: Archive boilerplate memories
From `boilerplate_memories` built in Phase 1:
- For each memory tagged `auto-captured` with boilerplate content:
  - Call `archive_memory(memory_id=<id>)`
- If none found, log "No boilerplate to archive"
Log: "Boilerplate: archived N auto-captured session noise memories"

### Step 10: Reinforce weak but valuable memories
From the weak memories found in Phase 1 (`get_weak_memories` results):
- Filter to memories where access count appears high (accessed frequently despite low strength) OR that are pinned
- For each qualifying memory, call `reinforce_memory(memory_id=<id>, boost_amount=0.3)`
- If none qualify, log "No weak-but-valuable memories to reinforce"
Log: "Reinforced: boosted N weak-but-valuable memories"

### Step 11: Fix orphaned memories
Run `curl -s http://localhost:8100/insights/anomalies` and count entries with "orphaned" in anomaly_reasons.
If orphans > 0, run `curl -s -X POST http://localhost:8100/admin/sync-graph-to-qdrant` to backfill Neo4j relationships into Qdrant relations payload.
Log: "Orphans: synced N memories from Neo4j ({n} relationships)"

### Step 12: Archive truly dead memories
From the weak memories found in Phase 1:
- Filter to memories where: strength < 0.1 AND the memory appears to have zero or very low access AND appears to be older than 30 days
- For each qualifying memory, call `archive_memory(memory_id=<id>)`
- Be conservative — when in doubt, do NOT archive
- If none qualify, log "No dead memories to archive"
Log: "Archived: cleaned up N dead memories"

---

## PHASE 3: REPORT (Before/After Comparison)

Re-run these three calls in parallel:
- `memory_stats()`
- `graph_stats()`
- `get_weak_memories(strength_threshold=0.3, limit=50)` — just count them

Save as `after_stats`. Compute deltas (after - before) for each metric.

### Compute Health Score (0-100)

Calculate these 4 sub-scores, then average them:

1. **Memory diversity** (0-25): How evenly distributed are memory types? If all 6 types have at least some entries, score 25. Deduct 5 points for each type with 0 entries.
2. **Graph connectivity** (0-25): Calculate edges/nodes ratio. If ratio >= 2.0, score 25. Scale linearly from 0 at ratio=0 to 25 at ratio=2.0.
3. **Knowledge coverage** (0-25): Start at 25, deduct 5 points per knowledge gap with error_count >= 2 (min 0). Ignore single-occurrence gaps — they are noise from resolved one-off errors.
4. **Memory quality** (0-25): Fetch `curl -s http://localhost:8100/quality/stats` and use its `average_score` field (0-1). Map to 0-25: `score = average_score * 25`. This uses the computed quality_score, not user ratings. If unavailable, use 15 as default.

**Health Score = sum of all 4 sub-scores.**

### Generate Recommendations

Based on findings, suggest 3-5 actionable items. Examples:
- If any memory type has 0 entries: "Store more {type} memories to improve diversity"
- If graph connectivity < 1.0: "Run inference more often to improve graph connectivity"
- If weak_count > 20: "Review weak memories — consider pinning valuable ones"
- If knowledge gaps exist: "Address knowledge gaps in: {project/topic list}"
- If error clusters found: "Investigate recurring error cluster: {description}"
- If contradictions remain: "Review unresolved contradictions for accuracy"
- If auto-resolved > 0: "Review auto-resolved errors for correctness"

### Output the Report

Display the full report in this exact format (fill in all values):

```
============================================================
  MEMORY AUDIT REPORT
============================================================

PHASE 1: DIAGNOSTICS
  Total memories:        {before.total}
  By type:               error: {n} | decision: {n} | pattern: {n} | learning: {n} | docs: {n} | context: {n}
  Graph nodes:           {before.graph_nodes}
  Graph relationships:   {before.graph_edges}
  Weak memories:         {before.weak_count} (strength < 0.3)
  Contradictions found:  {before.contradiction_count}
  Error clusters:        {before.error_clusters}
  Knowledge gaps:        {list or "None"}

PHASE 2: OPTIMIZATIONS APPLIED
  Quality refresh:       Updated {n} scores, auto-rated {n} (avg {n}/5)
  Consolidation:         Merged {n} duplicate groups
  Inference:             Discovered {n} new relationships
  Dream mode:            Replayed {n} memories, found {n} connections
  Replay:                Strengthened {n} important memories
  Contradictions:        Resolved {n} via supersedes links
  Auto-resolved errors:  Marked {n} errors resolved (had solutions)
  Session links:         Created {n} 'follows' links between siblings
  Tag-affinity links:    Created {n} relationships by tag similarity
  Boilerplate archived:  Cleaned {n} auto-captured noise memories
  Reinforced:            Boosted {n} weak-but-valuable memories
  Orphans fixed:         Synced {n} memories from Neo4j ({n} relationships)
  Dead archived:         Cleaned up {n} dead memories

PHASE 3: AFTER STATE
  Total memories:        {after.total} ({+/-delta})
  Graph relationships:   {after.graph_edges} ({+/-delta})
  Weak memories:         {after.weak_count} ({+/-delta})

HEALTH SCORE: {score}/100
  - Memory diversity:    {n}/25
  - Graph connectivity:  {n}/25
  - Knowledge coverage:  {n}/25
  - Memory quality:      {n}/25

RECOMMENDATIONS:
  {numbered list of 3-5 actionable items}
============================================================
```
