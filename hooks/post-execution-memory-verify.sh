#!/bin/bash
# Post-Execution Memory Verification Hook
# Verifies that memory was used during the session
# Usage: Called automatically after Claude completes a task

set -euo pipefail

MEMORY_SERVICE="http://localhost:8100"
LOG_FILE="${HOME}/.claude/logs/memory-verification.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Get session context from environment or arguments
SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"
PROJECT="${CLAUDE_PROJECT:-unknown}"

# Check if memory service is running
if ! curl -s -f "${MEMORY_SERVICE}/health" > /dev/null 2>&1; then
    log "⚠️  Memory service not running - cannot verify memory usage"
    exit 0  # Don't block execution, just warn
fi

# Get recent memory activity (last 5 minutes)
FIVE_MIN_AGO=$(date -u -v-5M +%s 2>/dev/null || date -u -d '5 minutes ago' +%s)

# Query memory stats
STATS=$(curl -s "${MEMORY_SERVICE}/stats" || echo '{}')
RECENT_SEARCHES=$(echo "$STATS" | grep -o '"total_memories":[0-9]*' | cut -d: -f2 || echo "0")

# Check audit log for memory tool usage
AUDIT_LOG="${HOME}/.claude/audit.log"
if [ -f "$AUDIT_LOG" ]; then
    SEARCH_COUNT=$(tail -100 "$AUDIT_LOG" | grep -c "search_memory" || echo "0")
    STORE_COUNT=$(tail -100 "$AUDIT_LOG" | grep -c "store_memory" || echo "0")
    GET_CONTEXT_COUNT=$(tail -100 "$AUDIT_LOG" | grep -c "get_context" || echo "0")
else
    SEARCH_COUNT=0
    STORE_COUNT=0
    GET_CONTEXT_COUNT=0
fi

# Verification logic
PASSED=true
WARNINGS=()

if [ "$SEARCH_COUNT" -eq 0 ] && [ "$GET_CONTEXT_COUNT" -eq 0 ]; then
    PASSED=false
    WARNINGS+=("❌ CRITICAL: No memory searches detected (search_memory or get_context)")
fi

if [ "$STORE_COUNT" -eq 0 ]; then
    PASSED=false
    WARNINGS+=("❌ CRITICAL: No memories stored (store_memory)")
fi

# Report results
log "════════════════════════════════════════════════════════════"
log "Memory Usage Verification for Session: $SESSION_ID"
log "Project: $PROJECT"
log "────────────────────────────────────────────────────────────"
log "Memory Operations Detected:"
log "  - search_memory calls: $SEARCH_COUNT"
log "  - get_context calls: $GET_CONTEXT_COUNT"
log "  - store_memory calls: $STORE_COUNT"
log "────────────────────────────────────────────────────────────"

if [ "$PASSED" = true ]; then
    log "✅ PASSED: Memory protocol followed correctly"
    exit 0
else
    log "❌ FAILED: Memory protocol violations detected"
    for warning in "${WARNINGS[@]}"; do
        log "  $warning"
    done
    log "────────────────────────────────────────────────────────────"
    log "📖 REMINDER: Every session MUST:"
    log "  1. START with: search_memory() + get_context()"
    log "  2. END with: store_memory() after solving problems"
    log "════════════════════════════════════════════════════════════"

    # Return non-zero to indicate failure (but don't block - just log)
    exit 1
fi
