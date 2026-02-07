#!/bin/bash
# Smart error capture - automatically saves errors with context
# Triggers: PostToolUseFailure (Bash) — only fires when command FAILS
# Writes to error journal for resolution detector to match against

MEMORY_API="http://localhost:8100"
ERROR_JOURNAL="/tmp/.claude-error-journal.jsonl"

# Health check - gracefully exit if service is unavailable
if ! curl -sf "$MEMORY_API/health" >/dev/null 2>&1; then
    exit 0
fi

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
# PostToolUseFailure provides .error (string) — no .tool_response
ERROR_OUTPUT=$(echo "$INPUT" | jq -r '.error // ""')

# Skip empty
if [ -z "$COMMAND" ] || [ -z "$ERROR_OUTPUT" ]; then
    exit 0
fi

# Extract error type from error text
detect_error_type() {
    local output="$1"

    if echo "$output" | grep -qiE "permission denied|EACCES"; then
        echo "permission"
    elif echo "$output" | grep -qiE "not found|ENOENT|command not found|No such file"; then
        echo "not-found"
    elif echo "$output" | grep -qiE "connection refused|ECONNREFUSED|timeout|ETIMEDOUT"; then
        echo "network"
    elif echo "$output" | grep -qiE "syntax error|parse error|SyntaxError"; then
        echo "syntax"
    elif echo "$output" | grep -qiE "type error|TypeError|undefined|null|ReferenceError"; then
        echo "type-error"
    elif echo "$output" | grep -qiE "ImportError|ModuleNotFoundError"; then
        echo "import-error"
    elif echo "$output" | grep -qiE "400|401|403|404|500|502|503"; then
        echo "http-error"
    elif echo "$output" | grep -qiE "SIGTERM|SIGKILL|killed"; then
        echo "process-killed"
    else
        echo "generic"
    fi
}

ERROR_TYPE=$(detect_error_type "$ERROR_OUTPUT")

# Extract first meaningful error line for content
ERROR_FIRST_LINE=$(echo "$ERROR_OUTPUT" | grep -iE "error|fail|exception|denied|refused|not found|Traceback" | tail -1 | head -c 200)
if [ -z "$ERROR_FIRST_LINE" ]; then
    ERROR_FIRST_LINE=$(echo "$ERROR_OUTPUT" | tail -1 | head -c 200)
fi

# Extract error codes
HTTP_CODE=$(echo "$ERROR_OUTPUT" | grep -oE '\b[45][0-9]{2}\b' | head -1)
ERRNO=$(echo "$ERROR_OUTPUT" | grep -oE 'E[A-Z]{3,}' | head -1)
ERROR_CODES="${HTTP_CODE:+HTTP-$HTTP_CODE}${ERRNO:+${HTTP_CODE:+,}$ERRNO}"

# Extract file/line locations
ERROR_LOCATION=$(echo "$ERROR_OUTPUT" | grep -oE '[^/]+\.(ts|js|py|go|rs|java|cpp|c|h):[0-9]+' | head -1)

# Generate prevention hint based on error type
generate_prevention() {
    case "$1" in
        permission) echo "Check file/directory permissions before access. Use ls -la to verify." ;;
        not-found) echo "Verify paths and package names exist before referencing. Use which/type for commands." ;;
        network) echo "Check service health and port availability before connecting. Use curl health endpoints." ;;
        syntax) echo "Validate syntax before running. Use linters or --check flags." ;;
        type-error) echo "Verify variable types and null checks. Review function signatures." ;;
        import-error) echo "Verify module is installed (pip list, npm ls). Check import path spelling." ;;
        http-error) echo "Check API endpoint, auth tokens, and request payload format." ;;
        process-killed) echo "Monitor resource usage. Check for OOM or timeout conditions." ;;
        *) echo "Review command arguments and environment before executing." ;;
    esac
}

PREVENTION=$(generate_prevention "$ERROR_TYPE")

# Search for similar recent errors (dedup — skip if same error already stored)
SIMILAR=$(curl -s "$MEMORY_API/memories/search" -X POST \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg q "$COMMAND $ERROR_FIRST_LINE" '{query: $q, type: "error", limit: 1, min_score: 0.9}')" \
    2>/dev/null | jq -r '.[0].memory.id // empty' 2>/dev/null)

# Only save if not duplicate
if [ -z "$SIMILAR" ]; then
    PROJECT_DIR=$(basename "$(pwd)" 2>/dev/null || echo "unknown")

    # Store error memory with descriptive content
    RESPONSE=$(curl -s "$MEMORY_API/memories" -X POST \
        -H "Content-Type: application/json" \
        -d "$(jq -n \
            --arg type "error" \
            --arg content "$ERROR_TYPE error in '$COMMAND': $ERROR_FIRST_LINE" \
            --arg error_message "$(echo "$ERROR_OUTPUT" | head -c 1000)" \
            --arg prevention "$PREVENTION" \
            --argjson tags "$(jq -n --arg t1 "auto-captured" --arg t2 "$ERROR_TYPE" '[$t1, $t2]')" \
            --arg context "Command: $COMMAND | Location: ${ERROR_LOCATION:-unknown} | Date: $(date '+%Y-%m-%d %H:%M')" \
            --arg project "$PROJECT_DIR" \
            '{type: $type, content: $content, error_message: $error_message, prevention: $prevention, tags: $tags, context: $context, project: $project}'
        )" 2>/dev/null)

    ERROR_ID=$(echo "$RESPONSE" | jq -r '.id // empty' 2>/dev/null)

    if [ -n "$ERROR_ID" ] && [ "$ERROR_ID" != "null" ]; then
        # Write to error journal for resolution detector
        CMD_NORMALIZED=$(echo "$COMMAND" | sed 's/^[[:space:]]*//' | head -c 120)
        CMD_HASH=$(echo "$CMD_NORMALIZED" | md5 -q 2>/dev/null || echo "$CMD_NORMALIZED" | md5sum | cut -d' ' -f1)

        jq -n \
            --arg error_id "$ERROR_ID" \
            --arg command "$CMD_NORMALIZED" \
            --arg cmd_hash "$CMD_HASH" \
            --arg error_type "$ERROR_TYPE" \
            --arg error_summary "$ERROR_FIRST_LINE" \
            --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            '{error_id: $error_id, command: $command, cmd_hash: $cmd_hash, error_type: $error_type, error_summary: $error_summary, timestamp: $timestamp}' \
            >> "$ERROR_JOURNAL"

        # Prune journal entries older than 24h
        CUTOFF=$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
        if [ -n "$CUTOFF" ] && [ -f "$ERROR_JOURNAL" ]; then
            TMP=$(mktemp)
            jq -c "select(.timestamp > \"$CUTOFF\")" "$ERROR_JOURNAL" > "$TMP" 2>/dev/null
            mv "$TMP" "$ERROR_JOURNAL"
        fi

        echo "Error auto-captured (ID: $ERROR_ID, type: $ERROR_TYPE)"
    fi
fi

exit 0
