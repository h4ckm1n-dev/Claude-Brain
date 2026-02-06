#!/bin/bash
# Block Destructive Commands - PreToolUse (Bash)
# Blocks rm -rf /, force-push to main, DROP DATABASE/TABLE

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

if [ -z "$COMMAND" ] || [ "$COMMAND" = "null" ]; then
    exit 0
fi

BLOCKED=false
REASON=""

# Block rm -rf / or rm -rf ~ (catastrophic deletions)
if echo "$COMMAND" | grep -qE 'rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|--force\s+)*(\/|~|\$HOME)\s*$'; then
    BLOCKED=true
    REASON="Blocked: 'rm -rf /' or 'rm -rf ~' would destroy the filesystem."
fi

# Block force-push to main/master
if echo "$COMMAND" | grep -qE 'git\s+push\s+.*--force.*\s+(main|master)'; then
    BLOCKED=true
    REASON="Blocked: force-push to main/master can destroy shared history."
fi
if echo "$COMMAND" | grep -qE 'git\s+push\s+.*\s+(main|master)\s+.*--force'; then
    BLOCKED=true
    REASON="Blocked: force-push to main/master can destroy shared history."
fi

# Block DROP DATABASE / DROP TABLE
if echo "$COMMAND" | grep -qiE 'DROP\s+(DATABASE|TABLE)\s'; then
    BLOCKED=true
    REASON="Blocked: DROP DATABASE/TABLE is destructive and irreversible."
fi

if [ "$BLOCKED" = true ]; then
    echo "{\"decision\": \"block\", \"reason\": \"$REASON\"}"
    exit 0
fi

exit 0
