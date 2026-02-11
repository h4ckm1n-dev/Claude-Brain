#!/bin/bash
# Session Start Hook — SessionStart
# Registers a new session (no memory stored — real memories come from the conversation)

MEMORY_API="http://localhost:8100"

# Check if memory service is reachable
if ! curl -sf "$MEMORY_API/health" > /dev/null 2>&1; then
    exit 0
fi

# Project context from working directory
FULL_PATH=$(pwd)
PROJECT=$(basename "$FULL_PATH")

# Create a new session on the memory server
SESSION_RESPONSE=$(curl -sf -X POST "$MEMORY_API/sessions/new?project=$PROJECT" 2>/dev/null)
if [ -z "$SESSION_RESPONSE" ]; then
    exit 0
fi

SESSION_ID=$(echo "$SESSION_RESPONSE" | jq -r '.session_id // empty')
if [ -z "$SESSION_ID" ]; then
    exit 0
fi

# Export session ID + project path for other hooks
if [ -n "$CLAUDE_ENV_FILE" ]; then
    echo "MEMORY_SESSION_ID=$SESSION_ID" >> "$CLAUDE_ENV_FILE"
    echo "MEMORY_PROJECT_PATH=$FULL_PATH" >> "$CLAUDE_ENV_FILE"
fi

# Write session ID to a known file for the MCP server to read
# (MCP server is spawned before hooks run, so it can't get env vars)
echo "$SESSION_ID" > /tmp/.claude-memory-session-id

exit 0
