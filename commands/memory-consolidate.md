---
description: "Merge duplicates, discover relationships, and strengthen important memories via consolidation pipeline"
allowed-tools: ["mcp__memory__consolidate_memories", "mcp__memory__run_inference", "mcp__memory__brain_dream", "mcp__memory__brain_replay", "mcp__memory__brain_detect_conflicts", "mcp__memory__consolidate_session"]
model: sonnet
---

# Memory Consolidation Pipeline

Merge duplicate memories, discover new relationships, and strengthen important memories.

Execute all steps sequentially — each builds on the previous.

---

## Step 1: Consolidate Duplicates

Call `consolidate_memories(older_than_days=14, dry_run=false)`.

Log: "Consolidation: merged {N} duplicate groups"

If nothing merged, log: "No duplicates found older than 14 days"

---

## Step 2: Discover Relationships

Call `run_inference(inference_type="all")`.

Log results by inference type:
- Temporal: {N} new relationships
- Semantic: {N} new relationships
- Causal: {N} new relationships
- Error-solution: {N} new relationships
- Total: {N} new relationships discovered

---

## Step 3: Dream Mode

Call `brain_dream(duration=30)`.

Log: "Dream: replayed {N} memories in {duration}s, discovered {N} unexpected connections"

---

## Step 4: Replay Important Memories

Call `brain_replay(count=20, importance_threshold=0.6)`.

Log: "Replay: strengthened {N} important memories"

---

## Step 5: Conflict Detection

Call `brain_detect_conflicts(limit=50)`.

Log: "Conflicts: found {N} semantic conflicts"

If conflicts found, list the top 5:
- "{memory_A_preview}" vs "{memory_B_preview}" — similarity: {score}

Suggest running `/memory-graph` to resolve contradictions via supersedes links.

---

## Summary

```
CONSOLIDATION REPORT
=====================
Duplicates merged:      {N}
Relationships found:    {N} (temporal: {n}, semantic: {n}, causal: {n}, error-solution: {n})
Dream connections:      {N}
Memories replayed:      {N}
Conflicts detected:     {N}

Next steps:
  - Run /memory-graph to resolve any conflicts
  - Run /memory-cleanup to archive weak memories
  - Run /memory-audit for full health report
```
