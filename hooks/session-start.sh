#!/bin/bash
# Session Start Hook - SessionStart
# Creates a new memory server session and stores a session-start context memory
# Sets MEMORY_SESSION_ID env var for other hooks (e.g., session-summary.sh)

MEMORY_API="http://localhost:8100"

# Get current working directory as project name
PROJECT=$(basename "$(pwd)")

# Check if memory service is reachable
if ! curl -sf "$MEMORY_API/health" > /dev/null 2>&1; then
    exit 0
fi

# Step 1: Create a new session on the memory server
SESSION_RESPONSE=$(curl -sf -X POST "$MEMORY_API/sessions/new?project=$PROJECT" 2>/dev/null)
if [ -z "$SESSION_RESPONSE" ]; then
    exit 0
fi

SESSION_ID=$(echo "$SESSION_RESPONSE" | jq -r '.session_id // empty')
if [ -z "$SESSION_ID" ]; then
    exit 0
fi

# Step 2: Store a "Session started" context memory with the session_id
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
curl -sf -X POST "$MEMORY_API/memories" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
        --arg type "context" \
        --arg content "Session started for project $PROJECT at $TIMESTAMP" \
        --arg project "$PROJECT" \
        --arg session_id "$SESSION_ID" \
        --argjson tags '["auto-captured", "session-start"]' \
        '{type: $type, content: $content, project: $project, session_id: $session_id, tags: $tags}'
    )" > /dev/null 2>&1

# Step 3: Export session ID for other hooks via CLAUDE_ENV_FILE
if [ -n "$CLAUDE_ENV_FILE" ]; then
    echo "MEMORY_SESSION_ID=$SESSION_ID" >> "$CLAUDE_ENV_FILE"
fi

exit 0
