#!/bin/bash
# Error Resolution Auto-Detector
# Triggers: PostToolUse (Bash SUCCESS, exit code 0)
# Purpose: Detect when a previously failing command succeeds,
#          collect file edits as resolution steps, mark error resolved
# Matching: 3-tier confidence (exact > args > base)

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
# PostToolUse provides: tool_response (object with stdout/stderr/interrupted/isImage)
# No exit_code field — PostToolUse only fires on SUCCESS, so no check needed
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
# tool_response is an object; extract stdout for success output
OUTPUT=$(echo "$INPUT" | jq -r '.tool_response.stdout // (.tool_response | tostring) // ""')

# Skip empty commands
if [ -z "$COMMAND" ]; then
    exit 0
fi

# Normalize current command for matching
CMD_NORMALIZED=$(echo "$COMMAND" | sed 's/^[[:space:]]*//' | head -c 120)
CMD_HASH=$(echo "$CMD_NORMALIZED" | md5 -q 2>/dev/null || echo "$CMD_NORMALIZED" | md5sum | cut -d' ' -f1)

# Extract binary and subcommand for tier-2 matching
CUR_BASE_CMD=$(echo "$CMD_NORMALIZED" | sed 's/^[A-Z_]*=[^ ]* //' | awk '{print $1}')
CUR_SUBCMD=$(echo "$CMD_NORMALIZED" | sed 's/^[A-Z_]*=[^ ]* //' | awk '{print $1, $2}' | head -c 60)

# Skip very common commands that aren't meaningful matches
case "$CUR_BASE_CMD" in
    ls|cat|echo|pwd|cd|head|tail|wc|date|true|false|which|type|env|export)
        exit 0
        ;;
esac

# Build tools whitelist for tier-3 (base command only) matching
# Only these tools are safe for loose base-command matching
is_build_tool() {
    case "$1" in
        npm|npx|yarn|pnpm|bun|pytest|python3|cargo|make|docker|go|tsc|eslint|webpack|vite|pip|pip3|poetry|mvn|gradle)
            return 0 ;;
        *)
            return 1 ;;
    esac
}

# 2a. Three-tier confidence matching — collect ALL matches across tiers
EXACT_MATCHES=""
ARGS_MATCHES=""
BASE_MATCHES=""

while IFS= read -r line; do
    [ -z "$line" ] && continue
    ENTRY_HASH=$(echo "$line" | jq -r '.cmd_hash // ""')
    ENTRY_SUBCMD=$(echo "$line" | jq -r '.subcmd // ""')
    ENTRY_BASE=$(echo "$line" | jq -r '.base_cmd // ""')

    # Tier 1: Exact cmd_hash match
    if [ "$ENTRY_HASH" = "$CMD_HASH" ]; then
        EXACT_MATCHES+="$line"$'\n'
        continue
    fi

    # Tier 2: Binary + subcommand prefix match
    # e.g., "git push" matches "git push --force" but NOT "git status"
    if [ -n "$ENTRY_SUBCMD" ] && [ -n "$CUR_SUBCMD" ] && [ "$ENTRY_SUBCMD" = "$CUR_SUBCMD" ]; then
        ARGS_MATCHES+="$line"$'\n'
        continue
    fi

    # Tier 3: Base command only (build tools whitelist)
    if [ -n "$ENTRY_BASE" ] && [ "$ENTRY_BASE" = "$CUR_BASE_CMD" ] && is_build_tool "$CUR_BASE_CMD"; then
        BASE_MATCHES+="$line"$'\n'
        continue
    fi
done < "$ERROR_JOURNAL"

# No matches at any tier
if [ -z "$EXACT_MATCHES" ] && [ -z "$ARGS_MATCHES" ] && [ -z "$BASE_MATCHES" ]; then
    exit 0
fi

# Collect file edits for resolution context (shared across all resolutions)
collect_edits_since() {
    local since_ts="$1"
    local edits=""
    if [ -f "$EDIT_JOURNAL" ] && [ -s "$EDIT_JOURNAL" ]; then
        edits=$(jq -c "select(.timestamp > \"$since_ts\")" "$EDIT_JOURNAL" 2>/dev/null)
    fi
    echo "$edits"
}

# 2c. Compute resolution duration from error timestamp to now
compute_duration() {
    local error_ts="$1"
    local now_epoch=$(date +%s)
    # Parse ISO timestamp to epoch
    local err_epoch=$(date -jf "%Y-%m-%dT%H:%M:%SZ" "$error_ts" +%s 2>/dev/null || \
                      date -d "$error_ts" +%s 2>/dev/null || echo "0")
    if [ "$err_epoch" -gt 0 ] 2>/dev/null; then
        local diff=$((now_epoch - err_epoch))
        if [ "$diff" -ge 3600 ]; then
            echo "$((diff / 3600))h$((diff % 3600 / 60))m (${diff}s)"
        elif [ "$diff" -ge 60 ]; then
            echo "$((diff / 60))m (${diff}s)"
        else
            echo "${diff}s"
        fi
    else
        echo "unknown"
    fi
}

# Process a single error resolution
resolve_error() {
    local entry="$1"
    local confidence="$2"

    local ERROR_ID=$(echo "$entry" | jq -r '.error_id')
    local ERROR_CMD=$(echo "$entry" | jq -r '.command')
    local ERROR_TYPE=$(echo "$entry" | jq -r '.error_type')
    local ERROR_SUMMARY=$(echo "$entry" | jq -r '.error_summary')
    local ERROR_TIMESTAMP=$(echo "$entry" | jq -r '.timestamp')
    local STACK_TRACE=$(echo "$entry" | jq -r '.stack_trace // ""' | head -c 500)

    # Verify error still exists and is unresolved
    local ERROR_CHECK=$(curl -s "$MEMORY_API/memories/$ERROR_ID" 2>/dev/null)
    local IS_RESOLVED=$(echo "$ERROR_CHECK" | jq -r '.resolved // false' 2>/dev/null)

    if [ "$IS_RESOLVED" = "true" ]; then
        # Already resolved, remove from journal (with lock to prevent race)
        local LOCKFILE="/tmp/.claude-error-journal.lock"
        if ( set -o noclobber; echo $$ > "$LOCKFILE" ) 2>/dev/null; then
            trap "rm -f '$LOCKFILE'" EXIT
            local TMP=$(mktemp)
            grep -v "\"error_id\":\"$ERROR_ID\"" "$ERROR_JOURNAL" > "$TMP" 2>/dev/null
            mv "$TMP" "$ERROR_JOURNAL"
            rm -f "$LOCKFILE"
            trap - EXIT
        fi
        return
    fi

    # Collect file edits since the error
    local EDITS=$(collect_edits_since "$ERROR_TIMESTAMP")
    local RESOLUTION_STEPS=""
    if [ -n "$EDITS" ]; then
        local EDIT_FILES=$(echo "$EDITS" | jq -r '.file_path' 2>/dev/null | sort -u)
        local EDIT_DETAILS=$(echo "$EDITS" | jq -r '"- \(.operation) \(.file_path): \(.snippet)"' 2>/dev/null | head -10)
        if [ -n "$EDIT_FILES" ]; then
            RESOLUTION_STEPS="Files modified to fix:\n$EDIT_DETAILS"
        fi
    fi

    # 2c. Resolution duration
    local DURATION=$(compute_duration "$ERROR_TIMESTAMP")

    # Build solution text
    local SOLUTION="Previously failed: $ERROR_CMD\n"
    SOLUTION+="Error was: $ERROR_SUMMARY\n\n"

    if [ -n "$STACK_TRACE" ] && [ ${#STACK_TRACE} -gt 20 ]; then
        SOLUTION+="Stack trace:\n$STACK_TRACE\n\n"
    fi

    if [ -n "$RESOLUTION_STEPS" ]; then
        SOLUTION+="Resolution steps:\n$RESOLUTION_STEPS\n\n"
    fi

    SOLUTION+="Verified by successful run: $CMD_NORMALIZED\n"
    # 2d. Confidence and duration in solution
    SOLUTION+="Match confidence: $confidence\n"
    SOLUTION+="Resolution time: $DURATION"

    # Add first line of success output as confirmation
    local SUCCESS_FIRST=$(echo "$OUTPUT" | head -3 | head -c 200)
    if [ -n "$SUCCESS_FIRST" ]; then
        SOLUTION+="\nOutput: $SUCCESS_FIRST"
    fi

    # Mark error as resolved with solution
    local SOLUTION_ENCODED=$(echo -e "$SOLUTION" | jq -sRr @uri)
    curl -s "$MEMORY_API/memories/$ERROR_ID/resolve?solution=$SOLUTION_ENCODED" \
        -X POST >/dev/null 2>&1

    # Remove resolved error from journal (with lock to prevent race)
    local LOCKFILE="/tmp/.claude-error-journal.lock"
    if ( set -o noclobber; echo $$ > "$LOCKFILE" ) 2>/dev/null; then
        trap "rm -f '$LOCKFILE'" EXIT
        local TMP=$(mktemp)
        grep -v "\"error_id\":\"$ERROR_ID\"" "$ERROR_JOURNAL" > "$TMP" 2>/dev/null
        mv "$TMP" "$ERROR_JOURNAL"
        rm -f "$LOCKFILE"
        trap - EXIT
    fi

    echo "Auto-resolved error (ID: $ERROR_ID, type: $ERROR_TYPE, confidence: $confidence)"
    echo "  Was: $ERROR_SUMMARY"
    echo "  Fix: $CMD_NORMALIZED"
    echo "  Duration: $DURATION"
}

# 2b. Process matches by tier — exact: no cap, args/base: cap at 3
RESOLVED_COUNT=0

# Tier 1: Exact matches (no cap)
if [ -n "$EXACT_MATCHES" ]; then
    while IFS= read -r entry; do
        [ -z "$entry" ] && continue
        resolve_error "$entry" "exact"
        RESOLVED_COUNT=$((RESOLVED_COUNT + 1))
    done <<< "$EXACT_MATCHES"
fi

# Tier 2: Args matches (cap at 3)
ARGS_COUNT=0
if [ -n "$ARGS_MATCHES" ]; then
    while IFS= read -r entry; do
        [ -z "$entry" ] && continue
        [ "$ARGS_COUNT" -ge 3 ] && break
        resolve_error "$entry" "args"
        ARGS_COUNT=$((ARGS_COUNT + 1))
        RESOLVED_COUNT=$((RESOLVED_COUNT + 1))
    done <<< "$ARGS_MATCHES"
fi

# Tier 3: Base matches (cap at 3)
BASE_COUNT=0
if [ -n "$BASE_MATCHES" ]; then
    while IFS= read -r entry; do
        [ -z "$entry" ] && continue
        [ "$BASE_COUNT" -ge 3 ] && break
        resolve_error "$entry" "base"
        BASE_COUNT=$((BASE_COUNT + 1))
        RESOLVED_COUNT=$((RESOLVED_COUNT + 1))
    done <<< "$BASE_MATCHES"
fi

if [ "$RESOLVED_COUNT" -gt 0 ]; then
    echo "Total errors resolved: $RESOLVED_COUNT"
fi

exit 0
