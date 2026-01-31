#!/bin/bash
# Intelligent session summary - captures ACTUAL work done
# Analyzes git commits, file changes, and commands to create meaningful summaries
# Triggered on Stop event

# Get current git branch for project context
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
PROJECT_DIR=$(basename "$(pwd)" 2>/dev/null || echo "unknown")

# Check if this is a valuable project (not temp/test directories)
if [[ "$PROJECT_DIR" =~ ^(tmp|temp|test|scratch|\.claude)$ ]] || [[ "$PROJECT_DIR" == "unknown" ]]; then
    exit 0
fi

# Check if memory service is available
if ! curl -sf http://localhost:8100/health >/dev/null 2>&1; then
    exit 0
fi

# Analyze session for SIGNIFICANT work
analyze_session() {
    local summary=""
    local significance=0

    # Check for git commits in this session
    RECENT_COMMITS=$(git log --since="30 minutes ago" --oneline 2>/dev/null | head -5)
    if [ -n "$RECENT_COMMITS" ]; then
        COMMIT_COUNT=$(echo "$RECENT_COMMITS" | wc -l | tr -d ' ')
        summary+="Made ${COMMIT_COUNT} commits: $(echo "$RECENT_COMMITS" | head -1 | cut -d' ' -f2-). "
        ((significance+=5))
    fi

    # Check for modified files
    MODIFIED_FILES=$(git status --short 2>/dev/null | wc -l | tr -d ' ')
    if [ "$MODIFIED_FILES" -gt 0 ]; then
        summary+="${MODIFIED_FILES} files modified. "
        ((significance+=2))
    fi

    # Check for new files
    NEW_FILES=$(git status --short 2>/dev/null | grep "^??" | wc -l | tr -d ' ')
    if [ "$NEW_FILES" -gt 0 ]; then
        summary+="Created ${NEW_FILES} new files. "
        ((significance+=3))
    fi

    # Check command history for patterns
    RECENT_COMMANDS=$(fc -ln -30 2>/dev/null | grep -v "^#" | tail -20)

    if echo "$RECENT_COMMANDS" | grep -qE "docker|deploy|compose"; then
        summary+="Docker/deployment work. "
        ((significance+=3))
    fi

    if echo "$RECENT_COMMANDS" | grep -qE "npm (install|run|build)"; then
        summary+="Build/dependency work. "
        ((significance+=2))
    fi

    if echo "$RECENT_COMMANDS" | grep -qE "curl.*api|curl.*localhost"; then
        summary+="API testing. "
        ((significance+=2))
    fi

    # Only return if significant work (score >= 5)
    if [ $significance -ge 5 ]; then
        echo "$summary"
    fi
}

SESSION_SUMMARY=$(analyze_session)

# Only save if there was MEANINGFUL work
if [ -n "$SESSION_SUMMARY" ]; then
    # Get file changes summary
    FILE_SUMMARY=$(git status --short 2>/dev/null | head -10 | sed 's/^/- /')

    FULL_CONTENT="Work session completed on ${PROJECT_DIR} (${GIT_BRANCH}):

${SESSION_SUMMARY}

Changed files:
${FILE_SUMMARY}"

    curl -s http://localhost:8100/memories -X POST \
        -H "Content-Type: application/json" \
        -d "{
            \"type\": \"context\",
            \"content\": \"${FULL_CONTENT}\",
            \"tags\": [\"work-session\", \"${PROJECT_DIR}\", \"${GIT_BRANCH}\"],
            \"project\": \"${PROJECT_DIR}\",
            \"context\": \"Session completed: $(date '+%Y-%m-%d %H:%M')\"
        }" >/dev/null 2>&1

    echo "✓ Work session summary saved to memory"
fi

exit 0
