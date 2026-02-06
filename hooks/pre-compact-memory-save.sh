#!/bin/bash
# PreCompact Memory Save
# Captures current session context before compaction so state survives

MEMORY_API="http://localhost:8100"

# Health check - skip if service unavailable
if ! curl -sf "$MEMORY_API/health" >/dev/null 2>&1; then
    exit 0
fi

INPUT=$(cat)

# Gather current context
PROJECT=$(basename "$(pwd)" 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "none")
MODIFIED_FILES=$(git diff --name-only 2>/dev/null | head -10 | tr '\n' ', ' | sed 's/,$//')
STAGED_FILES=$(git diff --cached --name-only 2>/dev/null | head -10 | tr '\n' ', ' | sed 's/,$//')

# Build context summary
CONTEXT_PARTS="Project: $PROJECT, Branch: $GIT_BRANCH"
if [ -n "$MODIFIED_FILES" ]; then
    CONTEXT_PARTS="$CONTEXT_PARTS, Modified: $MODIFIED_FILES"
fi
if [ -n "$STAGED_FILES" ]; then
    CONTEXT_PARTS="$CONTEXT_PARTS, Staged: $STAGED_FILES"
fi

# Store context memory
curl -s -X POST "$MEMORY_API/memories" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
        --arg type "context" \
        --arg content "Pre-compaction context snapshot. $CONTEXT_PARTS" \
        --arg project "$PROJECT" \
        --arg context "Auto-saved before context compaction at $(date '+%Y-%m-%d %H:%M:%S'). Resume work from this state." \
        --argjson tags '["auto-captured", "pre-compaction", "session-state"]' \
        '{type: $type, content: $content, project: $project, context: $context, tags: $tags}'
    )" > /dev/null 2>&1

exit 0
