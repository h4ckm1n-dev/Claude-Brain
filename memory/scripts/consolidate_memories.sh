#!/bin/bash
# Memory Consolidation Script
# Runs daily to merge duplicates and archive low-value memories
# Cron: 0 3 * * * ~/.claude/memory/scripts/consolidate_memories.sh

MEMORY_API="http://localhost:8100"
LOG_FILE=~/.claude/memory/logs/consolidation.log
OLDER_THAN_DAYS=7

# Ensure log directory exists
mkdir -p ~/.claude/memory/logs

# Log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if memory service is running
if ! curl -sf "$MEMORY_API/health" >/dev/null 2>&1; then
    log "❌ Memory service not available, skipping consolidation"
    exit 0
fi

log "🧹 Starting memory consolidation (older than $OLDER_THAN_DAYS days)"

# Run consolidation
RESULT=$(curl -s "$MEMORY_API/memories/consolidate" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{\"older_than_days\": $OLDER_THAN_DAYS, \"dry_run\": false}" 2>/dev/null)

# Parse results
MERGED=$(echo "$RESULT" | jq -r '.merged_count // 0' 2>/dev/null)
ARCHIVED=$(echo "$RESULT" | jq -r '.archived_count // 0' 2>/dev/null)

if [ -n "$MERGED" ] && [ "$MERGED" != "0" ]; then
    log "✓ Merged: $MERGED duplicate memories"
fi

if [ -n "$ARCHIVED" ] && [ "$ARCHIVED" != "0" ]; then
    log "✓ Archived: $ARCHIVED low-value memories"
fi

# Get stats after consolidation
STATS=$(curl -s "$MEMORY_API/memories/stats" 2>/dev/null)
TOTAL=$(echo "$STATS" | jq -r '.total_memories // 0' 2>/dev/null)

log "📊 Total memories: $TOTAL"
log "✓ Consolidation complete"

exit 0
