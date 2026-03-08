#!/bin/bash
# LSP Checkpoint Reminder
# Triggers: PreToolUse (Bash)
# Purpose: Before test/build/commit, remind to check diagnostics on recently edited code files
# Replaces per-edit lsp-diagnostics-reminder.sh with a batched checkpoint model

EDIT_JOURNAL="/tmp/.claude-edit-journal.jsonl"
CHECKED_FILE="/tmp/.claude-lsp-checked.jsonl"

# Read hook input
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

if [ -z "$COMMAND" ] || [ "$COMMAND" = "null" ]; then
    exit 0
fi

# Match checkpoint patterns: test, build, commit, lint, typecheck
if ! echo "$COMMAND" | grep -qE '\b(pytest|jest|vitest|npm test|npm run test|npx test|yarn test|pnpm test|cargo test|go test|tsc|eslint|mypy|pyright|ruff check|npm run build|cargo build|go build|git commit|make test|make build|swift build|swift test)\b'; then
    exit 0
fi

# No journal → nothing to check
if [ ! -f "$EDIT_JOURNAL" ] || [ ! -s "$EDIT_JOURNAL" ]; then
    exit 0
fi

# LSP-supported code extensions
LSP_EXTENSIONS="py|pyi|go|mod|js|ts|jsx|tsx|mjs|cjs|rs|lua|sh|bash|swift|tf|tfvars|html|css|scss|less|kt|kts|zig|php"

# Collect unique edited files from journal that have LSP support
EDITED_FILES=$(jq -r '.file_path' "$EDIT_JOURNAL" 2>/dev/null | sort -u | while read -r fp; do
    EXT="${fp##*.}"
    if echo "$EXT" | grep -qE "^($LSP_EXTENSIONS)$"; then
        echo "$fp"
    fi
done)

if [ -z "$EDITED_FILES" ]; then
    exit 0
fi

# Filter out already-checked files
if [ -f "$CHECKED_FILE" ] && [ -s "$CHECKED_FILE" ]; then
    CHECKED_LIST=$(jq -r '.file_path' "$CHECKED_FILE" 2>/dev/null | sort -u)
    UNCHECKED=""
    while IFS= read -r fp; do
        if ! echo "$CHECKED_LIST" | grep -qxF "$fp"; then
            UNCHECKED="${UNCHECKED}${fp}"$'\n'
        fi
    done <<< "$EDITED_FILES"
    UNCHECKED=$(echo "$UNCHECKED" | sed '/^$/d')
else
    UNCHECKED="$EDITED_FILES"
fi

if [ -z "$UNCHECKED" ]; then
    exit 0
fi

# Count files and build message
FILE_COUNT=$(echo "$UNCHECKED" | wc -l | tr -d ' ')
FILE_LIST=$(echo "$UNCHECKED" | sed 's/^/  - /')

echo "Before running tests/build/commit, check LSP diagnostics on ${FILE_COUNT} edited file(s):"
echo "$FILE_LIST"
echo "Run mcp__cclsp__get_diagnostics on each to catch errors. Fix any problems before proceeding."
