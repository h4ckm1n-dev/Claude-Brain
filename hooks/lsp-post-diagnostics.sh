#!/bin/bash
# LSP Post-Diagnostics Marker
# Triggers: PostToolUse (mcp__cclsp__get_diagnostics)
# Purpose: Mark files as "checked" after diagnostics run, so checkpoint won't re-flag them

CHECKED_FILE="/tmp/.claude-lsp-checked.jsonl"
LOCKFILE="/tmp/.claude-lsp-checked.lock"

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.uri // ""')

if [ -z "$FILE_PATH" ] || [ "$FILE_PATH" = "null" ]; then
    exit 0
fi

# Acquire lock
if ! ( set -o noclobber; echo $$ > "$LOCKFILE" ) 2>/dev/null; then
    exit 0
fi
trap "rm -f '$LOCKFILE'" EXIT

# Append checked entry
jq -cn \
    --arg file_path "$FILE_PATH" \
    --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{file_path: $file_path, timestamp: $timestamp}' \
    >> "$CHECKED_FILE"

# Prune entries older than 4 hours
if [ -f "$CHECKED_FILE" ]; then
    CUTOFF=$(date -u -v-4H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '4 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
    if [ -n "$CUTOFF" ]; then
        TMP=$(mktemp)
        jq -c "select(.timestamp > \"$CUTOFF\")" "$CHECKED_FILE" > "$TMP" 2>/dev/null
        mv "$TMP" "$CHECKED_FILE"
    fi
fi

rm -f "$LOCKFILE"
trap - EXIT
exit 0
