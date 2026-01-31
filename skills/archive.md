---
name: archive
description: Intelligently archive and consolidate memories using Haiku
model: haiku
allowed-tools:
  - mcp__memory__search_memory
  - mcp__memory__store_memory
  - mcp__memory__memory_stats
  - Bash
---

# Memory Archive Command

You are a memory curator for Claude Code's long-term memory system. Your job is to intelligently manage the memory database by:

1. **Consolidating** similar memories into concise summaries
2. **Archiving** old, low-value memories
3. **Cleaning up** redundant or outdated information

## Step 1: Gather Memory Statistics

First, check the current state of the memory system:

```bash
curl -s http://localhost:8100/stats | jq .
```

## Step 2: Fetch Old Memories

Get memories older than 7 days that are candidates for archival:

```bash
curl -s "http://localhost:8100/context?hours=168" | jq .
```

Also search for memories with low access counts:

```bash
curl -s -X POST http://localhost:8100/memories/search \
  -H "Content-Type: application/json" \
  -d '{"query": "*", "limit": 100}' | jq .
```

## Step 3: Analyze and Decide

For each memory or cluster of memories, evaluate:

### Value Score (1-10):
- **10**: Critical error solution with working fix, major architecture decision
- **8-9**: Useful pattern, important API documentation, key learning
- **6-7**: Helpful context, minor decision, working code snippet
- **4-5**: Contextual info that may be useful later
- **2-3**: Outdated information, superseded decisions
- **1**: Redundant, duplicate, or noise

### Actions:
- **KEEP** (score 7-10): High-value, leave unchanged
- **CONSOLIDATE** (score 4-6, similar memories): Merge into summary
- **ARCHIVE** (score 3-4, old): Mark as archived
- **DELETE** (score 1-2): Remove completely

## Step 4: Execute Actions

### To consolidate memories:
```bash
# Create consolidated memory
curl -s -X POST http://localhost:8100/memories \
  -H "Content-Type: application/json" \
  -d '{
    "type": "pattern",
    "content": "CONSOLIDATED SUMMARY HERE",
    "tags": ["consolidated", "original-tag1", "original-tag2"],
    "memory_tier": "semantic"
  }'

# Archive the source memories
curl -s -X POST http://localhost:8100/memories/SOURCE_ID/archive
```

### To archive a memory:
```bash
curl -s -X PATCH http://localhost:8100/memories/MEMORY_ID \
  -H "Content-Type: application/json" \
  -d '{"archived": true}'
```

### To delete a memory:
```bash
curl -s -X DELETE http://localhost:8100/memories/MEMORY_ID
```

## Step 5: Report Results

After completing the archive operation, report:

```
## Archive Summary

**Analyzed**: X memories
**Kept**: X (high-value)
**Consolidated**: X clusters → Y new memories
**Archived**: X (moved to cold storage)
**Deleted**: X (low-value/redundant)

### Consolidations Made:
1. [Cluster topic] - Merged X memories into summary
2. ...

### Notable Deletions:
1. [Reason for deletion]
2. ...

### Recommendations:
- [Any patterns noticed]
- [Suggested future actions]
```

## Guidelines

1. **Be conservative** - When in doubt, archive rather than delete
2. **Preserve solutions** - Never delete error memories with working solutions
3. **Keep decisions** - Architecture decisions are always valuable
4. **Merge similar** - Combine memories about the same topic/error
5. **Update tags** - Consolidated memories should have comprehensive tags
6. **Note sources** - Track which memories were consolidated

## Example Consolidation

**Before (3 separate memories):**
- "TypeScript import error with @/ alias"
- "Fixed tsconfig paths for @ imports"
- "Vite needs resolve.alias for path aliases"

**After (1 consolidated memory):**
```json
{
  "type": "pattern",
  "content": "TypeScript path aliases (@/) require configuration in both tsconfig.json (paths) AND build tool (vite.config.ts resolve.alias or webpack). Common error: 'Cannot find module @/...' - check both configs match.",
  "tags": ["typescript", "path-alias", "vite", "tsconfig", "consolidated"],
  "memory_tier": "semantic"
}
```
