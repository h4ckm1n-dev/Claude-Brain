# Brain Intelligence Features

## Overview

Your Claude Code memory system now has brain-like intelligence features that make it more autonomous and adaptive. These features run automatically in the background and can also be triggered manually via API.

---

## ✅ Implemented Features

### 1. Automatic Relationship Discovery (Phase 4)

**File**: `src/relationship_inference.py`

Automatically creates relationships between memories without manual intervention.

**Types of relationships created**:
- **FIXES**: Links solutions to the errors they fix
  - Finds unresolved errors
  - Searches for later learning/decision memories with similar content
  - Links if similarity > 85% and created after the error

- **RELATED**: Links semantically similar memories
  - Finds recent memories (last 7 days)
  - Searches for similar memories (similarity > 75%)
  - Links top 3 similar memories to each

- **TEMPORAL**: Links sequential memories in same project
  - Finds memories created within 2 hours in same project
  - Links as FOLLOWS relationship

- **CAUSES**: Detects causal relationships from content
  - Searches for "caused by", "due to", "because of" patterns
  - Extracts mentioned concepts and links them

**Scheduled**: Runs daily at 24-hour intervals

**Manual Trigger**:
```bash
curl -X POST "http://localhost:8100/brain/infer-relationships?lookback_days=30"
```

---

### 2. Adaptive Importance Scoring (Phase 3)

**File**: `src/consolidation.py` (new functions added)

Automatically adjusts memory importance scores based on usage patterns.

**Factors considered**:
- **Access frequency**: More accesses = higher importance (logarithmic)
- **Memory type**: Errors with solutions = 0.8, decisions = 0.9, docs = 0.7, etc.
- **Recency bias**: Newer memories start higher, decay over time
- **Co-access patterns**: Memories accessed together boost each other

**Formula**:
```
importance = base_type_weight + log(access_count+1)/10 - days_since_creation/100 + co_access_boost
```

**Scheduled**: Runs daily at 24-hour intervals (updates 100 memories per batch)

**Manual Trigger**:
```bash
curl -X POST "http://localhost:8100/brain/update-importance?limit=100"
```

---

### 3. Utility-Based Forgetting (Phase 5)

**File**: `src/consolidation.py` (new functions added)

Replaces time-based archival with intelligent utility-based archival.

**Utility factors**:
- **Access frequency**: log(access_count + 1) / 10 (max 0.3)
- **Recency of last access**: max(0, 0.3 - days_since_access/100)
- **Relationship count**: min(0.2, relationship_count * 0.05)
- **Importance score**: importance * 0.2

**Formula**:
```
utility = access_score + recency_score + relationship_score + importance_score
```

**Archive if**: `utility < 0.3` (default threshold)

**Protected memories**:
- Decisions (type = "decision")
- Patterns (type = "pattern")
- Resolved errors (valuable for learning)

**Scheduled**: Runs daily at 24-hour intervals (archives up to 100 low-utility memories)

**Manual Trigger**:
```bash
# Dry run (see what would be archived)
curl -X POST "http://localhost:8100/brain/archive-low-utility?threshold=0.3&dry_run=true"

# Actually archive
curl -X POST "http://localhost:8100/brain/archive-low-utility?threshold=0.3&dry_run=false"
```

---

## 🔌 API Endpoints

All brain intelligence features are exposed via REST API:

### GET /brain/stats

Get brain intelligence statistics.

**Response**:
```json
{
  "total_memories": 100,
  "relationships": 45,
  "utility_distribution": {
    "high": 30,
    "medium": 50,
    "low": 20
  },
  "adaptive_features": {
    "importance_scoring": true,
    "relationship_inference": true,
    "utility_archival": true
  }
}
```

### POST /brain/update-importance

Update importance scores based on usage patterns.

**Parameters**:
- `limit` (query): Max memories to update (1-1000, default: 100)

**Response**:
```json
{
  "success": true,
  "updated": 100,
  "limit": 100
}
```

### POST /brain/infer-relationships

Create relationships between memories.

**Parameters**:
- `lookback_days` (query): Days to look back for solutions (1-90, default: 30)

**Response**:
```json
{
  "success": true,
  "fixes_links": 5,
  "related_links": 12,
  "temporal_links": 8,
  "total_links": 25
}
```

### POST /brain/archive-low-utility

Archive memories with low utility scores.

**Parameters**:
- `threshold` (query): Archive if utility < this (0.0-1.0, default: 0.3)
- `max_archive` (query): Max memories to archive (1-500, default: 100)
- `dry_run` (query): Only simulate, don't actually archive (default: false)

**Response**:
```json
{
  "success": true,
  "archived": 15,
  "threshold": 0.3,
  "dry_run": false
}
```

---

## ⚙️ Scheduler Configuration

The brain intelligence features run automatically via the scheduler.

**Enable Scheduler**:
```bash
export SCHEDULER_ENABLED=true
```

**Scheduled Jobs**:
- `relationship_inference_job`: Runs every 24 hours
- `adaptive_importance_job`: Runs every 24 hours
- `utility_archival_job`: Runs every 24 hours
- `consolidation_job`: Existing job, runs every 24 hours

**Check Scheduler Status**:
```bash
curl http://localhost:8100/scheduler/status
```

**Manually Trigger Job**:
```bash
curl -X POST http://localhost:8100/scheduler/jobs/relationship_inference_job/trigger
```

---

## 🧪 Testing

Run the comprehensive test script:

```bash
chmod +x /tmp/test-brain-intelligence.sh
/tmp/test-brain-intelligence.sh
```

This tests all brain intelligence endpoints and shows their current status.

---

## 📊 Expected Impact

**Before** (Manual System):
- Manual memory creation via `store_memory` tool
- No proactive suggestions
- Time-based archival (7 days old = archive)
- Manual relationship linking
- Static importance scores

**After** (Brain-Like Intelligence):
- 🧠 **Adaptive**: Importance scores evolve based on usage
- 🧠 **Connected**: Auto-links related memories (FIXES, RELATED, TEMPORAL, CAUSES)
- 🧠 **Intelligent**: Forgets based on utility, not time
- 🧠 **Automated**: Runs daily without intervention

**User Experience**:
- **Better recall**: Well-connected memories easier to find
- **Cleaner memory**: Low-value memories archived automatically
- **Smarter search**: Relationships improve discovery via graph traversal
- **Less maintenance**: Automated intelligence reduces manual work

---

## 🔮 Future Enhancements (Not Yet Implemented)

The following phases from the plan are not yet implemented:

### Phase 1: MCP Tool Hooks (Autonomous Capture)
- Auto-capture from Bash errors, WebFetch, Read failures
- Requires MCP server integration (not part of this repo)

### Phase 2: Proactive Suggestions
- Pre-prompt hooks to suggest memories before user asks
- Requires MCP server integration (not part of this repo)

### Phase 6: Pattern Recognition (Optional)
- Detect recurring command sequences
- Create procedural memories for workflows

---

## 📝 Configuration Options

**Environment Variables**:
- `SCHEDULER_ENABLED`: Enable/disable automated jobs (default: false)
- `CONSOLIDATION_INTERVAL_HOURS`: How often to run jobs (default: 24)
- `CONSOLIDATION_OLDER_THAN_DAYS`: Age threshold for consolidation (default: 7)

**Runtime Parameters** (API):
- Utility threshold: How aggressively to archive (lower = more aggressive)
- Lookback days: How far back to search for solutions
- Batch limits: How many memories to process per job

---

## 🐛 Troubleshooting

**Scheduler not running**:
1. Check `SCHEDULER_ENABLED=true` in environment
2. Check logs for scheduler errors
3. Verify `apscheduler` is installed

**No relationships created**:
1. Check if memories have sufficient similarity
2. Verify graph database is connected (`curl /health` shows `graph_enabled: true`)
3. Lower similarity thresholds in `relationship_inference.py` if needed

**Importance scores not changing**:
1. Verify memories are being accessed (check `access_count` field)
2. Run manual update: `POST /brain/update-importance`
3. Check logs for errors

**Too many memories archived**:
1. Increase utility threshold (default 0.3 → 0.5)
2. Check if important memories have proper type (decision, pattern)
3. Ensure resolved errors are marked correctly

---

## 🎯 Best Practices

1. **Enable scheduler for production**: Set `SCHEDULER_ENABLED=true`
2. **Monitor brain stats**: Check `/brain/stats` regularly
3. **Adjust thresholds**: Tune based on your usage patterns
4. **Test with dry-run first**: Use `dry_run=true` before real archival
5. **Review relationships**: Check `/graph/stats` to see connections
6. **Access memories to boost importance**: Frequently used memories get higher scores

---

## 📚 Related Documentation

- `/docs/workflow-test-report.md` - System workflow testing results
- `/docs/dashboard-improvements.md` - Dashboard visualization features
- `/.claude/plans/pure-wiggling-gosling.md` - Full brain intelligence implementation plan
- `/src/graph.py` - Neo4j knowledge graph implementation
- `/src/consolidation.py` - Memory lifecycle management

---

**Status**: ✅ Server-side brain intelligence features fully implemented and ready for use

**Next Steps**:
1. Restart memory service to load new code
2. Run test script: `/tmp/test-brain-intelligence.sh`
3. Enable scheduler: `SCHEDULER_ENABLED=true`
4. Monitor brain stats and adjust thresholds as needed
