#!/bin/bash
# Error Resolution Auto-Detector
# Triggers: PostToolUse (Bash SUCCESS, exit code 0)
# Purpose: Detect when a previously failing command succeeds,
#          collect file edits as resolution steps, mark error resolved

MEMORY_API="http://localhost:8100"
ERROR_JOURNAL="/tmp/.claude-error-journal.jsonl"
EDIT_JOURNAL="/tmp/.claude-edit-journal.jsonl"

# Health check - exit if service unavailable
if ! curl -sf "$MEMORY_API/health" >/dev/null 2>&1; then
    exit 0
fi

# No error journal = no errors to resolve
if [ ! -f "$ERROR_JOURNAL" ] || [ ! -s "$ERROR_JOURNAL" ]; then
    exit 0
fi

# Read input
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
OUTPUT=$(echo "$INPUT" | jq -r '.tool_response // ""')
EXIT_CODE=$(echo "$INPUT" | jq -r '.exit_code // 0')

# Only process successful commands
if [ "$EXIT_CODE" != "0" ]; then
    exit 0
fi

# Skip empty commands
if [ -z "$COMMAND" ]; then
    exit 0
fi

# Normalize current command for matching
CMD_NORMALIZED=$(echo "$COMMAND" | sed 's/^[[:space:]]*//' | head -c 120)
CMD_HASH=$(echo "$CMD_NORMALIZED" | md5 -q 2>/dev/null || echo "$CMD_NORMALIZED" | md5sum | cut -d' ' -f1)

# Strategy 1: Exact hash match (same command that failed now succeeds)
MATCH=$(grep "\"cmd_hash\":\"$CMD_HASH\"" "$ERROR_JOURNAL" 2>/dev/null | tail -1)

# Strategy 2: Base command match (same binary, similar args)
if [ -z "$MATCH" ]; then
    # Extract base command (first word, skip env vars and cd)
    BASE_CMD=$(echo "$CMD_NORMALIZED" | sed 's/^[A-Z_]*=[^ ]* //' | awk '{print $1}')

    # Skip very common commands that aren't meaningful matches
    case "$BASE_CMD" in
        ls|cat|echo|pwd|cd|head|tail|wc|date|true|false)
            exit 0
            ;;
    esac

    # Search journal for entries with same base command
    if [ -n "$BASE_CMD" ]; then
        MATCH=$(grep "\"command\":\"[^\"]*$BASE_CMD" "$ERROR_JOURNAL" 2>/dev/null | tail -1)
    fi
fi

# No match found
if [ -z "$MATCH" ]; then
    exit 0
fi

# Extract error details from journal
ERROR_ID=$(echo "$MATCH" | jq -r '.error_id')
ERROR_CMD=$(echo "$MATCH" | jq -r '.command')
ERROR_TYPE=$(echo "$MATCH" | jq -r '.error_type')
ERROR_SUMMARY=$(echo "$MATCH" | jq -r '.error_summary')
ERROR_TIMESTAMP=$(echo "$MATCH" | jq -r '.timestamp')

# Verify error still exists and is unresolved
ERROR_CHECK=$(curl -s "$MEMORY_API/memories/$ERROR_ID" 2>/dev/null)
IS_RESOLVED=$(echo "$ERROR_CHECK" | jq -r '.resolved // false' 2>/dev/null)

if [ "$IS_RESOLVED" = "true" ]; then
    # Already resolved, remove from journal
    TMP=$(mktemp)
    grep -v "\"error_id\":\"$ERROR_ID\"" "$ERROR_JOURNAL" > "$TMP" 2>/dev/null
    mv "$TMP" "$ERROR_JOURNAL"
    exit 0
fi

# Collect file edits since the error as resolution steps
RESOLUTION_STEPS=""
if [ -f "$EDIT_JOURNAL" ] && [ -s "$EDIT_JOURNAL" ]; then
    # Get edits after the error timestamp
    EDITS=$(jq -c "select(.timestamp > \"$ERROR_TIMESTAMP\")" "$EDIT_JOURNAL" 2>/dev/null)

    if [ -n "$EDITS" ]; then
        EDIT_FILES=$(echo "$EDITS" | jq -r '.file_path' 2>/dev/null | sort -u)
        EDIT_DETAILS=$(echo "$EDITS" | jq -r '"- \(.operation) \(.file_path): \(.snippet)"' 2>/dev/null | head -10)

        if [ -n "$EDIT_FILES" ]; then
            RESOLUTION_STEPS="Files modified to fix:\n$EDIT_DETAILS"
        fi
    fi
fi

# Build solution text with actual resolution steps
SOLUTION="Previously failed: $ERROR_CMD\n"
SOLUTION+="Error was: $ERROR_SUMMARY\n\n"

if [ -n "$RESOLUTION_STEPS" ]; then
    SOLUTION+="Resolution steps:\n$RESOLUTION_STEPS\n\n"
fi

SOLUTION+="Verified by successful run: $CMD_NORMALIZED"

# Add first line of success output as confirmation
SUCCESS_FIRST=$(echo "$OUTPUT" | head -3 | head -c 200)
if [ -n "$SUCCESS_FIRST" ]; then
    SOLUTION+="\nOutput: $SUCCESS_FIRST"
fi

# Mark error as resolved with solution
SOLUTION_ENCODED=$(echo -e "$SOLUTION" | jq -sRr @uri)
curl -s "$MEMORY_API/memories/$ERROR_ID/resolve?solution=$SOLUTION_ENCODED" \
    -X POST >/dev/null 2>&1

# Remove resolved error from journal
TMP=$(mktemp)
grep -v "\"error_id\":\"$ERROR_ID\"" "$ERROR_JOURNAL" > "$TMP" 2>/dev/null
mv "$TMP" "$ERROR_JOURNAL"

echo "Auto-resolved error (ID: $ERROR_ID, type: $ERROR_TYPE)"
echo "  Was: $ERROR_SUMMARY"
echo "  Fix: $CMD_NORMALIZED"

exit 0
