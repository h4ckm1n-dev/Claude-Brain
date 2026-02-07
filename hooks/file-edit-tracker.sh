#!/bin/bash
# File Edit Tracker
# Triggers: PostToolUse (Write, Edit)
# Purpose: Track file edits with session context and diff info

MEMORY_API="http://localhost:8100"
EDIT_JOURNAL="/tmp/.claude-edit-journal.jsonl"

# Health check - exit silently if service unavailable
if ! curl -sf "$MEMORY_API/health" >/dev/null 2>&1; then
    exit 0
fi

INPUT=$(cat)
OPERATION=$(echo "$INPUT" | jq -r '.tool_name // "unknown"')
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input // ""')
TOOL_OUTPUT=$(echo "$INPUT" | jq -r '.tool_response // ""')

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

# Use real session ID from env if available, fallback to date-based
SESSION_ID="${MEMORY_SESSION_ID:-session-$(date +%Y%m%d%H)}"
PROJECT_DIR=$(basename "$(pwd)" 2>/dev/null || echo "unknown")

# 3a. Capture old_string + new_string for Edit, full content for Write
if [ "$OPERATION" = "Write" ]; then
    CONTENT=$(echo "$TOOL_INPUT" | jq -r '.content' 2>/dev/null | head -c 500)
    SNIPPET_FOR_JOURNAL=$(echo "$CONTENT" | tr '\n' ' ' | head -c 300)
elif [ "$OPERATION" = "Edit" ]; then
    OLD_STRING=$(echo "$TOOL_INPUT" | jq -r '.old_string // ""' 2>/dev/null | head -c 300)
    NEW_STRING=$(echo "$TOOL_INPUT" | jq -r '.new_string // ""' 2>/dev/null | head -c 300)
    CONTENT="$NEW_STRING"

    # 3a. Build diff-style snippet: REPLACED: ... -> WITH: ...
    OLD_ONELINE=$(echo "$OLD_STRING" | tr '\n' ' ' | head -c 300)
    NEW_ONELINE=$(echo "$NEW_STRING" | tr '\n' ' ' | head -c 300)
    SNIPPET_FOR_JOURNAL="REPLACED: $OLD_ONELINE -> WITH: $NEW_ONELINE"
else
    CONTENT=$(echo "$TOOL_INPUT" | jq -r '.new_string // .content // ""' 2>/dev/null | head -c 500)
    SNIPPET_FOR_JOURNAL=$(echo "$CONTENT" | tr '\n' ' ' | head -c 300)
fi

if [ -z "$CONTENT" ] || [ "$CONTENT" = "null" ]; then
    exit 0
fi

# Skip trivial edits (< 50 chars of content)
CONTENT_LEN=${#CONTENT}
if [ "$CONTENT_LEN" -lt 50 ]; then
    exit 0
fi

# Prepare tags
EXT="${FILE_PATH##*.}"
TAGS="[\"file-edit\", \"$OPERATION\", \"$SESSION_ID\", \"$PROJECT_DIR\"]"
if [ -n "$EXT" ] && [ "$EXT" != "$FILE_PATH" ]; then
    TAGS="[\"file-edit\", \"$OPERATION\", \"$SESSION_ID\", \"$PROJECT_DIR\", \"$EXT\"]"
fi

# 3b. Write to edit journal — 300-char snippets with old/new for Edit ops
# Truncate final snippet to 300 chars in case REPLACED: old -> WITH: new exceeds it
SNIPPET_FOR_JOURNAL=$(echo "$SNIPPET_FOR_JOURNAL" | head -c 300)
jq -cn \
    --arg file_path "$FILE_PATH" \
    --arg operation "$OPERATION" \
    --arg snippet "$SNIPPET_FOR_JOURNAL" \
    --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{file_path: $file_path, operation: $operation, snippet: $snippet, timestamp: $timestamp}' \
    >> "$EDIT_JOURNAL"

# Prune edit journal entries older than 2h
# Use lockfile to prevent race with concurrent append/prune
LOCKFILE="/tmp/.claude-edit-journal.lock"
if [ -f "$EDIT_JOURNAL" ]; then
    CUTOFF=$(date -u -v-2H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '2 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
    if [ -n "$CUTOFF" ]; then
        if ( set -o noclobber; echo $$ > "$LOCKFILE" ) 2>/dev/null; then
            trap "rm -f '$LOCKFILE'" EXIT
            TMP=$(mktemp)
            jq -c "select(.timestamp > \"$CUTOFF\")" "$EDIT_JOURNAL" > "$TMP" 2>/dev/null
            mv "$TMP" "$EDIT_JOURNAL"
            rm -f "$LOCKFILE"
            trap - EXIT
        fi
    fi
fi

# Create file edit memory
curl -s "$MEMORY_API/memories" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
        --arg type "pattern" \
        --arg content "File $OPERATION: $FILE_PATH" \
        --arg context "$CONTENT" \
        --argjson tags "$TAGS" \
        --arg project "$PROJECT_DIR" \
        --arg source "$FILE_PATH" \
        --arg session_id "$SESSION_ID" \
        '{type: $type, content: $content, context: $context, tags: $tags, project: $project, source: $source, session_id: $session_id}'
    )" > /dev/null 2>&1

exit 0
