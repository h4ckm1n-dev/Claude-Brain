#!/bin/bash
# File Edit Tracker
# Triggers: PostToolUse (Write, Edit)
# Purpose: Track file edits and link them to user prompts via FOLLOWS relationship

MEMORY_API="http://localhost:8100"

# Health check - exit silently if service unavailable
if ! curl -sf "$MEMORY_API/health" >/dev/null 2>&1; then
    exit 0
fi

OPERATION="$1"  # "Write" or "Edit"
TOOL_INPUT="$2"
TOOL_OUTPUT="$3"

# Extract file path from tool input
FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.file_path' 2>/dev/null)

if [ -z "$FILE_PATH" ] || [ "$FILE_PATH" = "null" ]; then
    exit 0
fi

# Skip certain files (logs, state files, etc.)
FILENAME=$(basename "$FILE_PATH")
case "$FILENAME" in
    *.log|watch-state.json|audit.log|*.tmp|*.cache)
        exit 0
        ;;
esac

# Get current context
SESSION_ID="session-$(date +%Y%m%d%H)"
PROJECT_DIR=$(basename "$(pwd)" 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

# Extract content (first 500 chars for context)
if [ "$OPERATION" = "Write" ]; then
    CONTENT=$(echo "$TOOL_INPUT" | jq -r '.content' 2>/dev/null | head -c 500)
else
    # For Edit, get new_string
    CONTENT=$(echo "$TOOL_INPUT" | jq -r '.new_string' 2>/dev/null | head -c 500)
fi

if [ -z "$CONTENT" ] || [ "$CONTENT" = "null" ]; then
    exit 0
fi

# Prepare tags
TAGS="[\"file-edit\", \"$OPERATION\", \"$SESSION_ID\", \"$PROJECT_DIR\"]"

# Add file extension tag
EXT="${FILE_PATH##*.}"
if [ -n "$EXT" ] && [ "$EXT" != "$FILE_PATH" ]; then
    TAGS="[\"file-edit\", \"$OPERATION\", \"$SESSION_ID\", \"$PROJECT_DIR\", \"$EXT\"]"
fi

# Create file edit memory
FILE_MEMORY_RESPONSE=$(curl -s "$MEMORY_API/memories" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{\"type\": \"pattern\", \"content\": \"File $OPERATION: $FILE_PATH\", \"context\": \"$CONTENT\", \"tags\": $TAGS, \"project\": \"$PROJECT_DIR\", \"source\": \"$FILE_PATH\"}" 2>/dev/null)

FILE_MEMORY_ID=$(echo "$FILE_MEMORY_RESPONSE" | jq -r '.id' 2>/dev/null)

if [ "$FILE_MEMORY_ID" = "null" ] || [ -z "$FILE_MEMORY_ID" ]; then
    exit 0
fi

# Search for recent user prompt in this session
RECENT_PROMPT_RESPONSE=$(curl -s "$MEMORY_API/memories/search" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"User:\", \"tags\": [\"user-prompt\", \"$SESSION_ID\"], \"limit\": 1}" 2>/dev/null)

RECENT_PROMPT_ID=$(echo "$RECENT_PROMPT_RESPONSE" | jq -r '.[0].memory.id' 2>/dev/null)

# Link file edit → user prompt (FOLLOWS relationship)
if [ "$RECENT_PROMPT_ID" != "null" ] && [ -n "$RECENT_PROMPT_ID" ]; then
    curl -s "$MEMORY_API/memories/link" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{\"source_id\": \"$FILE_MEMORY_ID\", \"target_id\": \"$RECENT_PROMPT_ID\", \"relation\": \"follows\"}" \
        >/dev/null 2>&1
fi

exit 0
