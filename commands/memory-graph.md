---
description: "Explore and maintain the knowledge graph — stats, contradictions, relationships, and inference"
allowed-tools: ["mcp__memory__graph_stats", "mcp__memory__find_related", "mcp__memory__memory_timeline", "mcp__memory__graph_recommendations", "mcp__memory__run_inference", "mcp__memory__graph_contradictions", "mcp__memory__brain_detect_conflicts", "mcp__memory__link_memories"]
model: sonnet
---

# Knowledge Graph Explorer

Explore, analyze, and maintain the memory knowledge graph.

**Input:** `$ARGUMENTS` — optional memory ID to explore, or `infer` to run inference, or empty for overview.

---

## Mode 1: Overview (no arguments or empty)

Run in parallel:

1. `graph_stats()` — nodes, edges, projects, connectivity
2. `graph_contradictions(limit=20)` — conflicting memory pairs
3. `memory_timeline(limit=30)` — recent memories with relationships

### Display Graph Overview

```
KNOWLEDGE GRAPH OVERVIEW
=========================
Nodes:              {N}
Relationships:      {N}
Connectivity:       {edges/nodes ratio:.2f}
Projects:           {list}
Contradictions:     {N}

RECENT ACTIVITY (last 30 memories):
  {timestamp} [{type}] {content_preview} — {N} relationships
  ...

CONTRADICTIONS (if any):
  {memory_A_preview} <-> {memory_B_preview}
  ...
```

---

## Mode 2: Explore Memory (memory ID provided)

If `$ARGUMENTS` looks like a UUID (contains dashes, 30+ chars):

Run in parallel:

1. `find_related(memory_id="$ARGUMENTS", max_hops=2, limit=10)`
2. `graph_recommendations(memory_id="$ARGUMENTS", limit=10)`

Display:
- Related memories (with relationship types and hop distance)
- Recommended memories (collaborative filtering)
- Suggest linking any recommended memories that seem strongly related

---

## Mode 3: Run Inference (`$ARGUMENTS` = "infer")

1. Call `run_inference(inference_type="all")`
2. Display results: new relationships discovered by type (temporal, semantic, causal, error-solution)

---

## Mode 4: Resolve Contradictions

If contradictions were found in Mode 1 overview:

For each contradicting pair:
1. Determine which memory is newer (by ID/timestamp)
2. Call `link_memories(source_id="{newer_id}", target_id="{older_id}", relation="supersedes")`
3. Log: "Resolved: {newer_preview} supersedes {older_preview}"

If no contradictions, skip this step.

---

## Final Summary

```
Graph health:       {edges/nodes:.1f} connectivity ratio
Contradictions:     {N} found, {N} resolved
New relationships:  {N} (if inference ran)
```
