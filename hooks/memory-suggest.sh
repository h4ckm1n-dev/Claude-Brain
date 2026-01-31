#!/bin/bash
# Memory Suggestion Hook - Proactive surfacing at conversation start
# Triggered by: PreToolUse (first tool) or custom trigger
# Surfaces relevant memories based on current context
# Now with smart throttling to reduce notification fatigue

MEMORY_API="http://localhost:8100"

# Health check - gracefully exit if service is unavailable
if ! curl -sf "$MEMORY_API/health" >/dev/null 2>&1; then
    # Service is down - silently skip suggestions
    exit 0
fi

# Check if suggestions should be shown (respects user settings)
SHOULD_SHOW=$(curl -s "$MEMORY_API/suggestions/should-show" 2>/dev/null | jq -r '.should_show // true')
if [ "$SHOULD_SHOW" != "true" ]; then
    # Silently skip - user has throttled suggestions
    exit 0
fi

# Get current context
PROJECT_NAME=$(basename "$(pwd)" 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

# Get recent files (from git status or recent edits)
RECENT_FILES=$(git diff --name-only HEAD~5 2>/dev/null | head -5 | tr '\n' ',' | sed 's/,$//')

# Extract keywords from current directory structure
KEYWORDS=""
if [ -f "package.json" ]; then
    KEYWORDS="$KEYWORDS javascript node npm"
fi
if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
    KEYWORDS="$KEYWORDS python"
fi
if [ -f "Cargo.toml" ]; then
    KEYWORDS="$KEYWORDS rust"
fi
if [ -f "go.mod" ]; then
    KEYWORDS="$KEYWORDS golang"
fi
if [ -f "tsconfig.json" ]; then
    KEYWORDS="$KEYWORDS typescript"
fi
if [ -d ".git" ]; then
    KEYWORDS="$KEYWORDS git"
fi
if [ -f "docker-compose.yml" ] || [ -f "Dockerfile" ]; then
    KEYWORDS="$KEYWORDS docker"
fi

# Convert keywords to JSON array
KEYWORDS_JSON=$(echo "$KEYWORDS" | xargs -n1 | sort -u | jq -R -s -c 'split("\n") | map(select(length > 0))')

# Convert files to JSON array
FILES_JSON=$(echo "$RECENT_FILES" | tr ',' '\n' | jq -R -s -c 'split("\n") | map(select(length > 0))')

# Build request payload
PAYLOAD=$(jq -n \
    --arg project "$PROJECT_NAME" \
    --arg branch "$GIT_BRANCH" \
    --argjson keywords "$KEYWORDS_JSON" \
    --argjson files "$FILES_JSON" \
    '{
        project: $project,
        git_branch: (if $branch == "" then null else $branch end),
        keywords: $keywords,
        current_files: $files,
        limit: 5
    }')

# Call the suggest endpoint
RESPONSE=$(curl -s -X POST "$MEMORY_API/memories/suggest" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" 2>/dev/null)

# Check if we got suggestions
COUNT=$(echo "$RESPONSE" | jq -r '.count // 0')

if [ "$COUNT" -gt 0 ]; then
    # Store notification for UI
    NOTIF_PAYLOAD=$(jq -n \
        --arg count "$COUNT" \
        --argjson data "$RESPONSE" \
        '{
            type: "suggestion",
            title: "Memory Suggestions Available",
            message: ("Found " + $count + " relevant memories for your current context"),
            data: $data
        }')

    curl -s -X POST "$MEMORY_API/notifications" \
        -H "Content-Type: application/json" \
        -d "$NOTIF_PAYLOAD" >/dev/null 2>&1
    echo ""
    echo "╭──────────────────────────────────────────────────────────────╮"
    echo "│ 🧠 Memory Suggestions                                        │"
    echo "╰──────────────────────────────────────────────────────────────╯"
    echo ""

    echo "$RESPONSE" | jq -r '.suggestions[] | "  \(.reason)\n  └─ \(.content)\n     Tags: \(.tags | join(", "))\n     Score: \(.combined_score) | Accessed: \(.access_count)x\n"'

    echo "──────────────────────────────────────────────────────────────"
    echo "  Use search_memory() for more context"
    echo ""
fi
