#!/bin/bash
# Session Start Hook — SessionStart
# Creates a new memory session with project folder context

MEMORY_API="http://localhost:8100"

# Check if memory service is reachable
if ! curl -sf "$MEMORY_API/health" > /dev/null 2>&1; then
    exit 0
fi

# Project context from working directory
FULL_PATH=$(pwd)
PROJECT=$(basename "$FULL_PATH")
GIT_BRANCH=$(git -C "$FULL_PATH" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
GIT_STATUS=$(git -C "$FULL_PATH" status --porcelain 2>/dev/null | wc -l | tr -d ' ')

# Create a new session on the memory server
SESSION_RESPONSE=$(curl -sf -X POST "$MEMORY_API/sessions/new?project=$PROJECT" 2>/dev/null)
if [ -z "$SESSION_RESPONSE" ]; then
    exit 0
fi

SESSION_ID=$(echo "$SESSION_RESPONSE" | jq -r '.session_id // empty')
if [ -z "$SESSION_ID" ]; then
    exit 0
fi

# Store a session-start context memory with project folder details
CONTEXT_PARTS="Directory: $FULL_PATH"
[ -n "$GIT_BRANCH" ] && CONTEXT_PARTS="$CONTEXT_PARTS, Branch: $GIT_BRANCH, Uncommitted files: $GIT_STATUS"

curl -sf -X POST "$MEMORY_API/memories" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
        --arg type "context" \
        --arg content "Session started for project $PROJECT in $FULL_PATH${GIT_BRANCH:+ on branch $GIT_BRANCH}${GIT_STATUS:+ with $GIT_STATUS uncommitted files}" \
        --arg project "$PROJECT" \
        --arg context "$CONTEXT_PARTS" \
        --arg session_id "$SESSION_ID" \
        --argjson tags "[\"session-start\", \"auto-captured\", \"$PROJECT\"]" \
        '{type: $type, content: $content, project: $project, context: $context, session_id: $session_id, tags: $tags}'
    )" > /dev/null 2>&1

# Export session ID + project path for other hooks
if [ -n "$CLAUDE_ENV_FILE" ]; then
    echo "MEMORY_SESSION_ID=$SESSION_ID" >> "$CLAUDE_ENV_FILE"
    echo "MEMORY_PROJECT_PATH=$FULL_PATH" >> "$CLAUDE_ENV_FILE"
fi

exit 0
