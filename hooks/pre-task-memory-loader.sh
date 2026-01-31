#!/bin/bash
# Proactive memory loader - surfaces relevant memories before starting work
# Triggered by PreToolUse for Task tool

MEMORY_API="http://localhost:8100"

# Health check - gracefully exit if service is unavailable
if ! curl -sf "$MEMORY_API/health" >/dev/null 2>&1; then
    exit 0
fi

TASK_PROMPT="$1"

# Extract keywords from task prompt
extract_keywords() {
    echo "$1" | \
        tr '[:upper:]' '[:lower:]' | \
        grep -oE '\b[a-z]{4,}\b' | \
        grep -vE '^(that|this|with|from|have|been|were|will|should|would|could)$' | \
        head -10 | \
        tr '\n' ' '
}

KEYWORDS=$(extract_keywords "$TASK_PROMPT")

# Get current context
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
PROJECT_DIR=$(basename "$(pwd)" 2>/dev/null || echo "")
CURRENT_FILES=$(git diff --name-only HEAD 2>/dev/null | tr '\n' ',' | head -c 200)

# Search for relevant memories
SUGGESTIONS=$(curl -s http://localhost:8100/memories/suggest -X POST \
    -H "Content-Type: application/json" \
    -d "{
        \"project\": \"${PROJECT_DIR}\",
        \"keywords\": $(echo "$KEYWORDS" | jq -R 'split(" ") | map(select(length > 0))'),
        \"git_branch\": \"${GIT_BRANCH}\",
        \"current_files\": $(echo "$CURRENT_FILES" | jq -R 'split(",") | map(select(length > 0))'),
        \"limit\": 5
    }" 2>/dev/null)

# Display suggestions if found
COUNT=$(echo "$SUGGESTIONS" | jq '.count // 0' 2>/dev/null || echo 0)

if [ "$COUNT" -gt 0 ]; then
    echo "╭──────────────────────────────────────────────────────────────╮"
    echo "│ 🧠 Relevant Memories Found ($COUNT)                              │"
    echo "╰──────────────────────────────────────────────────────────────╯"
    echo ""

    echo "$SUGGESTIONS" | jq -r '.suggestions[] |
        "  📌 \(.type | ascii_upcase)\n" +
        "  └─ \(.content[0:80])...\n" +
        "     Tags: \(.tags | join(", "))\n" +
        "     Score: \(.combined_score | tostring[0:3]) | Accessed: \(.access_count)x\n"' 2>/dev/null

    echo "──────────────────────────────────────────────────────────────"
    echo "  💡 Use search_memory() for more details"
    echo ""
fi

exit 0
