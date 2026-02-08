#!/bin/bash
# Session Close Hook — Stop
# Calls /sessions/{id}/close to store end memory, infer relationships, and consolidate

MEMORY_API="http://localhost:8100"

# Check if memory service is reachable
if ! curl -sf "$MEMORY_API/health" > /dev/null 2>&1; then
    exit 0
fi

# MEMORY_SESSION_ID is set by session-start.sh via CLAUDE_ENV_FILE
if [ -z "$MEMORY_SESSION_ID" ]; then
    exit 0
fi

# Close the session — this handles:
#   1. Stores a session-end context memory
#   2. Infers relationships between session memories
#   3. Consolidates into a summary (if >=2 memories)
#   4. Double-close guard (safe to call multiple times)
curl -sf -X POST "$MEMORY_API/sessions/$MEMORY_SESSION_ID/close" > /dev/null 2>&1

exit 0
