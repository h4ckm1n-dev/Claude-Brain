#!/bin/bash
# Error Resolution Auto-Detector
# Triggers: PostToolUse (Bash SUCCESS, exit code 0)
# Purpose: Automatically detect when a previously failing command succeeds
#          and link the solution to the error memory

MEMORY_API="http://localhost:8100"

# Health check - exit if service unavailable
if ! curl -sf "$MEMORY_API/health" >/dev/null 2>&1; then
    exit 0
fi

# Read input from stdin (Claude Code hooks pass JSON on stdin)
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
OUTPUT=$(echo "$INPUT" | jq -r '.tool_response // ""')
EXIT_CODE=$(echo "$INPUT" | jq -r '.exit_code // 0')

# Only process successful commands
if [ "$EXIT_CODE" != "0" ]; then
    exit 0
fi

# Skip if no command
if [ -z "$COMMAND" ]; then
    exit 0
fi

# Search for unresolved errors with same/similar command (last 7 days)
SIMILAR_ERRORS=$(curl -s "$MEMORY_API/memories/search" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"$COMMAND\", \"type\": \"error\", \"limit\": 3}" 2>/dev/null)

# Filter to unresolved errors only
UNRESOLVED=$(echo "$SIMILAR_ERRORS" | jq '[.[] | select(.memory.resolved == false)]' 2>/dev/null)

ERROR_COUNT=$(echo "$UNRESOLVED" | jq 'length' 2>/dev/null || echo 0)

if [ "$ERROR_COUNT" -gt 0 ]; then
    # Get the most recent unresolved error
    ERROR_ID=$(echo "$UNRESOLVED" | jq -r '.[0].memory.id' 2>/dev/null)
    ERROR_CONTENT=$(echo "$UNRESOLVED" | jq -r '.[0].memory.content' 2>/dev/null | head -c 100)

    echo "🔍 Found unresolved error: $ERROR_CONTENT..." >&2

    # Create solution memory
    PROJECT=$(basename $(pwd) 2>/dev/null)
    SOLUTION_RESPONSE=$(curl -s "$MEMORY_API/memories" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{\"type\": \"pattern\", \"content\": \"Solution: $COMMAND succeeded\", \"context\": \"$OUTPUT\", \"tags\": [\"solution\", \"auto-linked\", \"error-resolved\"], \"project\": \"$PROJECT\"}" 2>/dev/null)

    SOLUTION_ID=$(echo "$SOLUTION_RESPONSE" | jq -r '.id' 2>/dev/null)

    if [ "$SOLUTION_ID" != "null" ] && [ -n "$SOLUTION_ID" ]; then
        echo "✅ Created solution memory: $SOLUTION_ID" >&2

        # Link solution → error (FIXES relationship)
        curl -s "$MEMORY_API/memories/link" \
            -X POST \
            -H "Content-Type: application/json" \
            -d "{\"source_id\": \"$SOLUTION_ID\", \"target_id\": \"$ERROR_ID\", \"relation\": \"fixes\"}" >/dev/null 2>&1

        echo "🔗 Linked solution → error (FIXES)" >&2

        # Mark error as resolved
        SOLUTION_TEXT=$(echo "$OUTPUT" | head -c 200)
        # URL encode the solution text
        SOLUTION_ENCODED=$(echo "$SOLUTION_TEXT" | jq -sRr @uri)
        curl -s "$MEMORY_API/memories/$ERROR_ID/resolve?solution=$SOLUTION_ENCODED" \
            -X POST >/dev/null 2>&1

        echo "✓ Marked error as resolved" >&2
        echo "" >&2
        echo "╭──────────────────────────────────────────────────────────╮" >&2
        echo "│ 🎉 Auto-resolved Error!                                  │" >&2
        echo "╰──────────────────────────────────────────────────────────╯" >&2
        echo "  Error: $(echo "$ERROR_CONTENT" | head -c 50)..." >&2
        echo "  Command: $COMMAND" >&2
        echo "  Solution ID: $SOLUTION_ID" >&2
        echo "" >&2
    fi
fi

exit 0
