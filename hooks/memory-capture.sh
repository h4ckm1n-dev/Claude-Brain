#!/bin/bash
# Enhanced Memory Capture Hook - PostToolUse
# Captures tool outputs and stores relevant memories with pattern detection

MEMORY_API="http://localhost:8100"

# Read hook input from stdin
INPUT=$(cat)

# Parse tool name and output
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // .tool // "unknown"')
TOOL_OUTPUT=$(echo "$INPUT" | jq -r '.output // .result // ""')
TOOL_INPUT=$(echo "$INPUT" | jq -r '.input // .arguments // ""')

# Skip if no output or tool is excluded
if [ -z "$TOOL_OUTPUT" ] || [ "$TOOL_OUTPUT" = "null" ]; then
    exit 0
fi

# Skip certain tools that don't need memory capture
case "$TOOL_NAME" in
    "Read"|"Glob"|"Grep"|"LS"|"TodoWrite"|"WebFetch")
        # WebFetch is handled by webfetch-capture.sh
        exit 0
        ;;
esac

# Get project context
PROJECT=$(basename "$(pwd)")

# ===== ERROR DETECTION =====
ERROR_PATTERNS="error|Error|ERROR|failed|Failed|FAILED|exception|Exception|EXCEPTION|cannot|Cannot|CANNOT|not found|Not found|NOT FOUND|permission denied|Permission denied|ENOENT|EACCES|ModuleNotFoundError|ImportError|SyntaxError|TypeError|ValueError"

if echo "$TOOL_OUTPUT" | grep -qiE "$ERROR_PATTERNS"; then
    # Extract error message (first line containing error)
    ERROR_MSG=$(echo "$TOOL_OUTPUT" | grep -iE "$ERROR_PATTERNS" | head -1 | head -c 500)

    # Extract error type if present
    ERROR_TYPE=$(echo "$ERROR_MSG" | grep -oE "(ModuleNotFoundError|ImportError|SyntaxError|TypeError|ValueError|FileNotFoundError|PermissionError|ConnectionError|TimeoutError)" | head -1)

    # Build tags array
    TAGS='["auto-captured", "tool-error"]'
    if [ -n "$ERROR_TYPE" ]; then
        TAGS=$(echo "$TAGS" | jq --arg et "$ERROR_TYPE" '. + [$et]')
    fi

    # Check if similar error exists (for linking)
    SIMILAR_ERROR=$(curl -s -X POST "$MEMORY_API/memories/search" \
        -H "Content-Type: application/json" \
        -d "$(jq -n \
            --arg query "$ERROR_MSG" \
            --arg type "error" \
            '{query: $query, type: $type, limit: 1}'
        )" | jq -r '.[0].memory.id // ""')

    # Store error memory
    NEW_ERROR_ID=$(curl -s -X POST "$MEMORY_API/memories" \
        -H "Content-Type: application/json" \
        -d "$(jq -n \
            --arg type "error" \
            --arg content "Error during $TOOL_NAME: $ERROR_MSG" \
            --arg error_message "$ERROR_MSG" \
            --arg context "Tool: $TOOL_NAME, Input: $(echo "$TOOL_INPUT" | head -c 500)" \
            --arg project "$PROJECT" \
            --argjson tags "$TAGS" \
            '{type: $type, content: $content, error_message: $error_message, context: $context, project: $project, tags: $tags}'
        )" | jq -r '.id // ""')

    # Link to similar error if found
    if [ -n "$SIMILAR_ERROR" ] && [ -n "$NEW_ERROR_ID" ] && [ "$SIMILAR_ERROR" != "$NEW_ERROR_ID" ]; then
        curl -s -X POST "$MEMORY_API/memories/link" \
            -H "Content-Type: application/json" \
            -d "$(jq -n \
                --arg source_id "$NEW_ERROR_ID" \
                --arg target_id "$SIMILAR_ERROR" \
                '{source_id: $source_id, target_id: $target_id, relation_type: "related"}'
            )" > /dev/null 2>&1
    fi
fi

# ===== SUCCESS/SOLUTION DETECTION =====
SUCCESS_PATTERNS="successfully|created|installed|configured|deployed|completed|passed|✓|PASS"
FIX_PATTERNS="fix|fixed|resolved|working now|works now|solved|solution"

if echo "$TOOL_OUTPUT" | grep -qiE "$SUCCESS_PATTERNS"; then
    # Check if this might be fixing a previous error
    if echo "$TOOL_OUTPUT" | grep -qiE "$FIX_PATTERNS"; then
        # Extract what was fixed
        FIX_CONTEXT=$(echo "$TOOL_OUTPUT" | head -5 | head -c 500)

        # Store as learning
        SOLUTION_ID=$(curl -s -X POST "$MEMORY_API/memories" \
            -H "Content-Type: application/json" \
            -d "$(jq -n \
                --arg type "learning" \
                --arg content "Solution applied via $TOOL_NAME" \
                --arg context "$FIX_CONTEXT" \
                --arg project "$PROJECT" \
                --argjson tags '["auto-captured", "solution", "fix"]' \
                '{type: $type, content: $content, context: $context, project: $project, tags: $tags}'
            )" | jq -r '.id // ""')

        # Try to find and link to recent unresolved error
        RECENT_ERROR=$(curl -s -X POST "$MEMORY_API/memories/search" \
            -H "Content-Type: application/json" \
            -d '{"query": "error", "type": "error", "limit": 5}' \
            | jq -r '[.[] | select(.memory.resolved == false)] | .[0].memory.id // ""')

        if [ -n "$RECENT_ERROR" ] && [ -n "$SOLUTION_ID" ]; then
            # Link solution to error
            curl -s -X POST "$MEMORY_API/memories/link" \
                -H "Content-Type: application/json" \
                -d "$(jq -n \
                    --arg source_id "$SOLUTION_ID" \
                    --arg target_id "$RECENT_ERROR" \
                    '{source_id: $source_id, target_id: $target_id, relation_type: "fixes"}'
                )" > /dev/null 2>&1
        fi
    fi
fi

# ===== PATTERN DETECTION =====
# Detect commands that might be reusable patterns
if [ "$TOOL_NAME" = "Bash" ]; then
    COMMAND=$(echo "$TOOL_INPUT" | jq -r '.command // ""' | head -1)

    # Detect installation commands
    if echo "$COMMAND" | grep -qiE "^(npm install|pip install|brew install|apt install|cargo install)"; then
        curl -s -X POST "$MEMORY_API/memories" \
            -H "Content-Type: application/json" \
            -d "$(jq -n \
                --arg type "pattern" \
                --arg content "Installation command: $COMMAND" \
                --arg context "Used in project: $PROJECT" \
                --arg project "$PROJECT" \
                --argjson tags '["auto-captured", "installation", "command"]' \
                '{type: $type, content: $content, context: $context, project: $project, tags: $tags}'
            )" > /dev/null 2>&1
    fi

    # Detect Docker commands
    if echo "$COMMAND" | grep -qiE "^docker"; then
        curl -s -X POST "$MEMORY_API/memories" \
            -H "Content-Type: application/json" \
            -d "$(jq -n \
                --arg type "pattern" \
                --arg content "Docker command: $COMMAND" \
                --arg context "Output: $(echo "$TOOL_OUTPUT" | head -3 | head -c 200)" \
                --arg project "$PROJECT" \
                --argjson tags '["auto-captured", "docker", "command"]' \
                '{type: $type, content: $content, context: $context, project: $project, tags: $tags}'
            )" > /dev/null 2>&1
    fi
fi

exit 0
