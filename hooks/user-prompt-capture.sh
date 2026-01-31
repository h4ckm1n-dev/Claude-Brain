#!/bin/bash
# User Prompt Capture
# Triggers: UserPromptSubmit (BEFORE memory-suggest.sh)
# Purpose: Capture user prompts with intent detection and session tracking

MEMORY_API="http://localhost:8100"

# Health check - exit silently if service unavailable
if ! curl -sf "$MEMORY_API/health" >/dev/null 2>&1; then
    exit 0
fi

USER_PROMPT="$1"

# Skip empty prompts
if [ -z "$USER_PROMPT" ]; then
    exit 0
fi

# Skip very short prompts (< 5 chars)
if [ ${#USER_PROMPT} -lt 5 ]; then
    exit 0
fi

# Generate hourly session ID for workflow tracking
SESSION_ID="session-$(date +%Y%m%d%H)"

# Get current project context
PROJECT_DIR=$(basename "$(pwd)" 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

# Detect intent based on keywords
INTENT="general"
PROMPT_LOWER=$(echo "$USER_PROMPT" | tr '[:upper:]' '[:lower:]')

if echo "$PROMPT_LOWER" | grep -qE "(error|fail|broken|bug|crash|issue|problem|not working|doesn't work)"; then
    INTENT="bug-report"
elif echo "$PROMPT_LOWER" | grep -qE "(how|what|why|when|where|which|explain|tell me|\?)"; then
    INTENT="question"
elif echo "$PROMPT_LOWER" | grep -qE "(add|create|implement|build|make|develop|feature|new)"; then
    INTENT="feature-request"
elif echo "$PROMPT_LOWER" | grep -qE "(refactor|clean|improve|optimize|update|change|modify)"; then
    INTENT="improvement"
elif echo "$PROMPT_LOWER" | grep -qE "(test|spec|unittest|e2e|integration)"; then
    INTENT="testing"
elif echo "$PROMPT_LOWER" | grep -qE "(deploy|release|ship|publish|launch)"; then
    INTENT="deployment"
elif echo "$PROMPT_LOWER" | grep -qE "(review|check|audit|verify|validate)"; then
    INTENT="review"
fi

# Prepare tags
TAGS="[\"user-prompt\", \"$INTENT\", \"$SESSION_ID\", \"$PROJECT_DIR\"]"

# Add git branch tag if available
if [ "$GIT_BRANCH" != "main" ] && [ -n "$GIT_BRANCH" ]; then
    TAGS="[\"user-prompt\", \"$INTENT\", \"$SESSION_ID\", \"$PROJECT_DIR\", \"$GIT_BRANCH\"]"
fi

# Truncate very long prompts (keep first 1000 chars)
PROMPT_CONTENT=$(echo "$USER_PROMPT" | head -c 1000)

# Prepare context
CONTEXT="Session: $SESSION_ID\nProject: $PROJECT_DIR\nBranch: $GIT_BRANCH\nIntent: $INTENT"

# Save prompt memory
curl -s "$MEMORY_API/memories" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{\"type\": \"context\", \"content\": \"User: $PROMPT_CONTENT\", \"tags\": $TAGS, \"project\": \"$PROJECT_DIR\", \"context\": \"$CONTEXT\"}" \
    >/dev/null 2>&1

exit 0
