---
description: "Find and resolve unresolved error memories — auto-resolve errors that already have solutions"
allowed-tools: ["mcp__memory__search_memory", "mcp__memory__mark_resolved", "mcp__memory__link_memories", "mcp__memory__error_trends", "Bash"]
model: sonnet
---

# Error Resolution Workflow

Find unresolved errors, match solutions, and resolve them.

---

## Step 1: Error Landscape

Run in parallel:

1. `error_trends(time_window_days=90)` — recurring patterns, spikes, clusters
2. Scroll Qdrant for unresolved error memories:
```bash
curl -s 'http://localhost:6333/collections/memories/points/scroll' \
  -H 'Content-Type: application/json' \
  -d '{"filter":{"must":[{"key":"archived","match":{"value":false}},{"key":"type","match":{"value":"error"}},{"key":"resolved","match":{"value":false}}]},"limit":100,"with_payload":true,"with_vector":false}'
```

Parse the Qdrant scroll response to get unresolved error memories.

Display error landscape:
- Total error clusters found
- Total unresolved errors
- Recurring patterns (if any)

---

## Step 2: Auto-Resolve Errors with Solutions

From the Qdrant scroll results, identify errors where the `solution` field exists and is 15+ characters.

For each qualifying error:
1. Call `mark_resolved(memory_id="{id}", solution="{solution_from_payload}")`
2. Handle failures gracefully (409 = already resolved, skip)
3. Log each resolution: "{memory_id}: resolved"

Track counts: `auto_resolved`, `skipped` (409/400), `no_solution`

---

## Step 3: Find Solutions for Unsolved Errors

For errors WITHOUT a solution (or solution < 15 chars), up to 5 errors:

1. Extract the `error_message` from the payload
2. Call `search_memory(query="{error_message}", limit=3)` to find related learning/pattern/decision memories
3. If a relevant match is found, display it as a suggested fix

---

## Step 4: Link Resolved Errors

For each error that was auto-resolved in Step 2:

1. Search for related memories: `search_memory(query="{error content}", limit=2)`
2. If a learning or pattern memory is found that relates to the error's solution:
   - Call `link_memories(source_id="{error_id}", target_id="{related_id}", relation="related")`

Cap at 10 new links to avoid noise.

---

## Step 5: Summary

```
ERROR RESOLUTION REPORT
========================
Error clusters:      {N} (from last 90 days)
Unresolved found:    {N}
Auto-resolved:       {N} (had solutions)
Skipped:             {N} (already resolved or short solution)
Still unresolved:    {N} (no solution available)
Links created:       {N}
Suggested fixes:     {N} (see above for details)
```
