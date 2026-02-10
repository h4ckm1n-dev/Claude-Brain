---
description: "Read-only memory diagnostics with health score and actionable recommendations"
allowed-tools: ["mcp__memory__memory_stats", "mcp__memory__graph_stats", "mcp__memory__error_trends", "mcp__memory__knowledge_gaps", "mcp__memory__get_weak_memories", "mcp__memory__graph_contradictions", "mcp__memory__brain_detect_conflicts", "Bash"]
model: sonnet
---

# Memory Audit — Diagnostics & Health Report

Read-only diagnostics. No mutations. For optimization, use the focused commands listed in recommendations.

---

## Step 1: Gather Diagnostics (all parallel)

**MCP calls (parallel):**
1. `memory_stats()` — total counts, by-type, by-project
2. `graph_stats()` — nodes, relationships, projects
3. `error_trends(time_window_days=90)` — recurring errors, spikes, clusters
4. `knowledge_gaps()` — topics with errors but no patterns
5. `get_weak_memories(strength_threshold=0.3, limit=50)` — fading memories
6. `graph_contradictions(limit=20)` — contradicting pairs
7. `brain_detect_conflicts(limit=50)` — semantic conflicts

**Bash curl calls (parallel):**
8. `curl -s http://localhost:8100/memories/quality-report` — rating distribution, quality scores
9. `curl -s http://localhost:8100/memories/quality-leaderboard?limit=10` — top quality memories
10. `curl -s http://localhost:8100/quality/stats` — average quality score

**Additional data (parallel):**
11. Scroll Qdrant for unresolved errors with solutions:
```bash
curl -s 'http://localhost:6333/collections/memories/points/scroll' \
  -H 'Content-Type: application/json' \
  -d '{"filter":{"must":[{"key":"archived","match":{"value":false}},{"key":"type","match":{"value":"error"}},{"key":"resolved","match":{"value":false}}]},"limit":100,"with_payload":true,"with_vector":false}'
```
12. Scroll Qdrant for boilerplate memories:
```bash
curl -s 'http://localhost:6333/collections/memories/points/scroll' \
  -H 'Content-Type: application/json' \
  -d '{"filter":{"must":[{"key":"archived","match":{"value":false}},{"key":"tags","match":{"any":["auto-captured","session-start","session-end"]}}]},"limit":100,"with_payload":true,"with_vector":false}'
```

---

## Step 2: Compute Health Score (0-100)

Calculate four sub-scores:

1. **Memory diversity** (0-25): All 6 types present = 25. Deduct 5 per missing type.
2. **Graph connectivity** (0-25): `min(edges/nodes / 2.0, 1.0) * 25`. Ratio >= 2.0 = full score.
3. **Knowledge coverage** (0-25): Start at 25, deduct 5 per knowledge gap with error_count >= 2 (min 0).
4. **Memory quality** (0-25): Use `average_score` from quality/stats endpoint. `score = average_score * 25`. Default 15 if unavailable.

**Health Score = sum of all 4 sub-scores.**

---

## Step 3: Build Recommendations

Generate 3-7 actionable recommendations that point to specific commands:

| Condition | Recommendation |
|-----------|---------------|
| Unresolved errors with solutions exist | "Run `/memory-resolve` to auto-resolve {N} errors that already have solutions" |
| Boilerplate memories found | "Run `/memory-cleanup` to archive {N} boilerplate memories" |
| Weak memories > 10 | "Run `/memory-cleanup` to review {N} weak memories" |
| Graph connectivity < 1.5 | "Run `/memory-consolidate` to discover new relationships via inference" |
| Contradictions found | "Run `/memory-graph` to resolve {N} contradictions" |
| Semantic conflicts found | "Run `/memory-graph infer` to run full inference and resolve conflicts" |
| Knowledge gaps exist | "Address knowledge gaps in: {topics}. Store more pattern/learning memories." |
| Any memory type has 0 entries | "Store more {type} memories to improve diversity" |
| Error clusters > 3 | "Investigate recurring error clusters — consider documenting solutions" |
| Quality average < 0.7 | "Run `/memory-consolidate` to strengthen memories via replay and dream mode" |

---

## Step 4: Output Report

```
============================================================
  MEMORY AUDIT REPORT (Diagnostics Only)
============================================================

MEMORY INVENTORY
  Total memories:        {total}
  By type:               error: {n} | decision: {n} | pattern: {n} | learning: {n} | docs: {n} | context: {n}

KNOWLEDGE GRAPH
  Nodes:                 {nodes}
  Relationships:         {edges}
  Connectivity ratio:    {edges/nodes:.2f}

QUALITY
  Average quality:       {avg:.2f}/1.00
  Top memory:            {leaderboard_top_preview}

ISSUES DETECTED
  Weak memories:         {weak_count} (strength < 0.3)
  Contradictions:        {contradiction_count}
  Semantic conflicts:    {conflict_count}
  Unresolved errors:     {unresolved_with_solution} (with solutions) + {unresolved_no_solution} (no solution)
  Boilerplate:           {boilerplate_count}
  Knowledge gaps:        {gap_list or "None"}
  Error clusters:        {cluster_count}

HEALTH SCORE: {score}/100
  Memory diversity:      {n}/25
  Graph connectivity:    {n}/25
  Knowledge coverage:    {n}/25
  Memory quality:        {n}/25

RECOMMENDATIONS
  {numbered list pointing to specific /memory-* commands}

============================================================
Focused commands: /memory-resolve | /memory-cleanup | /memory-consolidate | /memory-graph | /memory-search | /memory-export
============================================================
```
