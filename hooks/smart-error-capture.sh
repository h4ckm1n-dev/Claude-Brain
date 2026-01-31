#!/bin/bash
# Smart error capture - automatically saves errors with context
# Triggered on Bash tool errors (EXIT_CODE != 0)

MEMORY_API="http://localhost:8100"

# Health check - gracefully exit if service is unavailable
if ! curl -sf "$MEMORY_API/health" >/dev/null 2>&1; then
    exit 0
fi

COMMAND="$1"
ERROR_OUTPUT="$2"
EXIT_CODE="$3"

# Only capture if it's a real error
if [ "$EXIT_CODE" -eq 0 ]; then
    exit 0
fi

# Extract error type
detect_error_type() {
    local output="$1"

    if echo "$output" | grep -qiE "permission denied|EACCES"; then
        echo "permission"
    elif echo "$output" | grep -qiE "not found|ENOENT|command not found"; then
        echo "not-found"
    elif echo "$output" | grep -qiE "connection refused|ECONNREFUSED|timeout|ETIMEDOUT"; then
        echo "network"
    elif echo "$output" | grep -qiE "syntax error|parse error|SyntaxError"; then
        echo "syntax"
    elif echo "$output" | grep -qiE "type error|TypeError|undefined|null|ReferenceError"; then
        echo "type-error"
    elif echo "$output" | grep -qiE "400|401|403|404|500|502|503"; then
        echo "http-error"
    elif echo "$output" | grep -qiE "SIGTERM|SIGKILL|killed"; then
        echo "process-killed"
    else
        echo "generic"
    fi
}

ERROR_TYPE=$(detect_error_type "$ERROR_OUTPUT")

# Extract error codes (HTTP status, errno, etc)
extract_error_codes() {
    local output="$1"
    local codes=""

    # HTTP status codes
    HTTP_CODE=$(echo "$output" | grep -oE '\b[45][0-9]{2}\b' | head -1)
    if [ -n "$HTTP_CODE" ]; then
        codes="HTTP-$HTTP_CODE"
    fi

    # Errno codes (ECONNREFUSED, ENOENT, etc)
    ERRNO=$(echo "$output" | grep -oE 'E[A-Z]+' | head -1)
    if [ -n "$ERRNO" ]; then
        codes="${codes:+$codes,}$ERRNO"
    fi

    # Exit code
    codes="${codes:+$codes,}EXIT-$EXIT_CODE"

    echo "$codes"
}

ERROR_CODES=$(extract_error_codes "$ERROR_OUTPUT")

# Extract stack trace
extract_stack_trace() {
    local output="$1"

    # Look for common stack trace patterns
    if echo "$output" | grep -qE "(at |File |line |Traceback)"; then
        echo "$output" | grep -E "^\s+(at |File |line |\d+\s+\|)" | head -10
    else
        echo ""
    fi
}

STACK_TRACE=$(extract_stack_trace "$ERROR_OUTPUT")

# Extract file/line locations
ERROR_LOCATION=$(echo "$ERROR_OUTPUT" | grep -oE '[^/]+\.(ts|js|py|go|rs|java|cpp|c|h):[0-9]+' | head -1)

# Check if this error was seen before (dedup within 1 hour)
ERROR_HASH=$(echo "${COMMAND}${ERROR_TYPE}" | md5sum | cut -d' ' -f1)

# Search for similar errors
SIMILAR=$(curl -s "http://localhost:8100/memories/search" -X POST \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"${COMMAND} ${ERROR_TYPE}\",
        \"type\": \"error\",
        \"limit\": 1,
        \"min_score\": 0.9
    }" 2>/dev/null | jq '.[0].memory.id // empty' 2>/dev/null)

# Only save if not duplicate
if [ -z "$SIMILAR" ]; then
    # Prepare stack trace for JSON
    STACK_JSON=$(echo "$STACK_TRACE" | jq -Rs . 2>/dev/null || echo '""')

    curl -s http://localhost:8100/memories -X POST \
        -H "Content-Type: application/json" \
        -d "{
            \"type\": \"error\",
            \"content\": \"Command failed: ${COMMAND}\",
            \"error_message\": $(echo "$ERROR_OUTPUT" | head -c 1000 | jq -Rs .),
            \"stack_trace\": $STACK_JSON,
            \"tags\": [\"auto-captured\", \"${ERROR_TYPE}\", \"${ERROR_CODES}\"],
            \"context\": \"Error occurred on $(date '+%Y-%m-%d %H:%M'). Location: ${ERROR_LOCATION:-unknown}. Codes: ${ERROR_CODES}\"
        }" >/dev/null 2>&1

    # Store notification
    curl -s http://localhost:8100/notifications -X POST \
        -H "Content-Type: application/json" \
        -d "{
            \"type\": \"error\",
            \"title\": \"Error Captured\",
            \"message\": \"${ERROR_TYPE} error: ${COMMAND}\",
            \"data\": {
                \"command\": \"${COMMAND}\",
                \"error_type\": \"${ERROR_TYPE}\",
                \"exit_code\": ${EXIT_CODE}
            }
        }" >/dev/null 2>&1

    echo "⚠️  Error auto-captured to memory system (type: $ERROR_TYPE)"
fi

exit 0
