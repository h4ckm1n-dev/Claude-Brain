#!/bin/bash
# Context-Aware Memory Loader
# Triggers: PreToolUse (Write, Edit, Bash)
# Purpose: Show relevant memories BEFORE tool execution

MEMORY_API="http://localhost:8100"

# Health check - exit silently if service unavailable
if ! curl -sf "$MEMORY_API/health" >/dev/null 2>&1; then
    exit 0
fi

TOOL_TYPE="$1"
TOOL_INPUT="$2"

case "$TOOL_TYPE" in
    Write|Edit)
        # Extract file path from tool input
        FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.file_path' 2>/dev/null)

        if [ -z "$FILE_PATH" ] || [ "$FILE_PATH" = "null" ]; then
            exit 0
        fi

        FILENAME=$(basename "$FILE_PATH")

        # Search for previous edits to same file
        SEARCH_PAYLOAD=$(cat <<EOF
{
  "query": "$FILENAME",
  "tags": ["file-edit"],
  "limit": 3
}
EOF
)

        RESULTS=$(curl -s "$MEMORY_API/memories/search" \
            -H "Content-Type: application/json" \
            -d "$SEARCH_PAYLOAD" 2>/dev/null)

        RESULT_COUNT=$(echo "$RESULTS" | jq 'length' 2>/dev/null || echo 0)

        if [ "$RESULT_COUNT" -gt 0 ]; then
            echo "" >&2
            echo "╭─────────────────────────────────────────────────────────╮" >&2
            echo "│ 📁 Previous Edits to $FILENAME" >&2
            echo "╰─────────────────────────────────────────────────────────╯" >&2

            echo "$RESULTS" | jq -r '.[] |
                "  \(.created_at[0:16]): \(.content[0:60])..."' 2>/dev/null >&2

            echo "" >&2
        fi
        ;;

    Bash)
        # Extract command from tool input
        COMMAND=$(echo "$TOOL_INPUT" | jq -r '.command' 2>/dev/null)

        if [ -z "$COMMAND" ] || [ "$COMMAND" = "null" ]; then
            exit 0
        fi

        # Truncate command for search (first 100 chars)
        COMMAND_SHORT=$(echo "$COMMAND" | head -c 100)

        # Search for previous errors with same command
        SEARCH_PAYLOAD=$(cat <<EOF
{
  "query": "$COMMAND_SHORT",
  "type": "error",
  "limit": 3
}
EOF
)

        ERRORS=$(curl -s "$MEMORY_API/memories/search" \
            -H "Content-Type: application/json" \
            -d "$SEARCH_PAYLOAD" 2>/dev/null)

        ERROR_COUNT=$(echo "$ERRORS" | jq 'length' 2>/dev/null || echo 0)

        if [ "$ERROR_COUNT" -gt 0 ]; then
            echo "" >&2
            echo "╭─────────────────────────────────────────────────────────╮" >&2
            echo "│ ⚠️  This command has history:" >&2
            echo "╰─────────────────────────────────────────────────────────╯" >&2

            echo "$ERRORS" | jq -r '.[] |
                if .resolved == true then
                    "  ✅ RESOLVED (\(.created_at[0:16])): \(.solution // .content | .[0:50])..."
                else
                    "  ❌ UNRESOLVED (\(.created_at[0:16])): \(.error_message // .content | .[0:50])..."
                end' 2>/dev/null >&2

            echo "" >&2
        fi

        # Also search for successful patterns
        PATTERN_PAYLOAD=$(cat <<EOF
{
  "query": "$COMMAND_SHORT",
  "tags": ["solution", "pattern"],
  "limit": 2
}
EOF
)

        PATTERNS=$(curl -s "$MEMORY_API/memories/search" \
            -H "Content-Type: application/json" \
            -d "$PATTERN_PAYLOAD" 2>/dev/null)

        PATTERN_COUNT=$(echo "$PATTERNS" | jq 'length' 2>/dev/null || echo 0)

        if [ "$PATTERN_COUNT" -gt 0 ]; then
            echo "╭─────────────────────────────────────────────────────────╮" >&2
            echo "│ 💡 Known Solutions:" >&2
            echo "╰─────────────────────────────────────────────────────────╯" >&2

            echo "$PATTERNS" | jq -r '.[] |
                "  ✓ \(.content[0:60])..."' 2>/dev/null >&2

            echo "" >&2
        fi
        ;;
esac

exit 0
