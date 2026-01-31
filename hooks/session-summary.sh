#!/bin/bash
# Enhanced Session Summary Hook - Stop
# Captures comprehensive session summary when Claude Code stops

MEMORY_API="http://localhost:8100"

# Read hook input from stdin
INPUT=$(cat)

# Extract session info
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
REASON=$(echo "$INPUT" | jq -r '.reason // "user_stop"')
DURATION=$(echo "$INPUT" | jq -r '.duration_seconds // 0')
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // ""')

# Get current working directory as project name
PROJECT=$(basename "$(pwd)")
FULL_PATH=$(pwd)

# Calculate duration in human-readable format
if [ "$DURATION" -gt 0 ]; then
    HOURS=$((DURATION / 3600))
    MINUTES=$(((DURATION % 3600) / 60))
    if [ "$HOURS" -gt 0 ]; then
        DURATION_STR="${HOURS}h ${MINUTES}m"
    else
        DURATION_STR="${MINUTES}m"
    fi
else
    DURATION_STR="unknown"
fi

# Try to extract key actions from transcript if available
ACTIONS_SUMMARY=""
TOTAL_ACTIONS=0
if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ]; then
    # Count tool uses
    EDIT_COUNT=$(grep -c '"tool_name":"Edit"' "$TRANSCRIPT_PATH" 2>/dev/null || echo "0")
    WRITE_COUNT=$(grep -c '"tool_name":"Write"' "$TRANSCRIPT_PATH" 2>/dev/null || echo "0")
    BASH_COUNT=$(grep -c '"tool_name":"Bash"' "$TRANSCRIPT_PATH" 2>/dev/null || echo "0")
    TASK_COUNT=$(grep -c '"tool_name":"Task"' "$TRANSCRIPT_PATH" 2>/dev/null || echo "0")

    TOTAL_ACTIONS=$((EDIT_COUNT + WRITE_COUNT + BASH_COUNT + TASK_COUNT))

    if [ "$TOTAL_ACTIONS" -gt 0 ]; then
        ACTIONS_SUMMARY="Files edited: $EDIT_COUNT, Files created: $WRITE_COUNT, Commands run: $BASH_COUNT, Agents used: $TASK_COUNT"
    fi
fi

# QUALITY FILTER: Only store memory if there's meaningful content
# Skip if: duration unknown AND no actions performed
if [ "$DURATION_STR" = "unknown" ] && [ "$TOTAL_ACTIONS" -eq 0 ]; then
    # No useful information to store
    exit 0
fi

# Skip very short sessions with no actions (< 1 minute)
if [ "$DURATION" -lt 60 ] && [ "$TOTAL_ACTIONS" -eq 0 ]; then
    # Too short and no work done
    exit 0
fi

# Store session end as context memory with more details
curl -s -X POST "$MEMORY_API/memories" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
        --arg type "context" \
        --arg content "Session ended ($REASON) - Duration: $DURATION_STR. $ACTIONS_SUMMARY" \
        --arg project "$PROJECT" \
        --arg context "Session ID: $SESSION_ID, Directory: $FULL_PATH, Reason: $REASON" \
        --argjson tags '["auto-captured", "session-end", "session-summary"]' \
        '{type: $type, content: $content, project: $project, context: $context, tags: $tags}'
    )" > /dev/null 2>&1

# If session was long (>30 min), mark it as potentially important
if [ "$DURATION" -gt 1800 ]; then
    curl -s -X POST "$MEMORY_API/memories" \
        -H "Content-Type: application/json" \
        -d "$(jq -n \
            --arg type "learning" \
            --arg content "Extended work session on $PROJECT (${DURATION_STR}). Consider reviewing for patterns." \
            --arg project "$PROJECT" \
            --argjson tags '["auto-captured", "long-session", "review-candidate"]' \
            '{type: $type, content: $content, project: $project, tags: $tags}'
        )" > /dev/null 2>&1
fi

exit 0
