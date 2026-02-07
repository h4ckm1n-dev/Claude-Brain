#!/bin/bash
# Memory Capture Hook - PostToolUse
# Captures file edit patterns from Write/Edit tool outputs
# NOTE: Bash error capture is handled by smart-error-capture.sh
#       Solution detection is handled by error-resolution-detector.sh

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

# Only process Write and Edit tools for pattern detection
# All other tools are handled by specialized hooks
case "$TOOL_NAME" in
    "Write"|"Edit")
        # Continue to pattern detection below
        ;;
    *)
        exit 0
        ;;
esac

# Get project context
PROJECT=$(basename "$(pwd)")

# ===== FILE EDIT PATTERN DETECTION =====
# Detect installation commands in file content (e.g., Dockerfiles, scripts)
FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.file_path // ""' | head -1)

if [ -n "$FILE_PATH" ] && [ "$FILE_PATH" != "null" ]; then
    # Detect Dockerfile patterns
    if echo "$FILE_PATH" | grep -qiE "Dockerfile|docker-compose"; then
        curl -s -X POST "$MEMORY_API/memories" \
            -H "Content-Type: application/json" \
            -d "$(jq -n \
                --arg type "pattern" \
                --arg content "Docker configuration: $FILE_PATH" \
                --arg context "Modified via $TOOL_NAME" \
                --arg project "$PROJECT" \
                --argjson tags '["auto-captured", "docker", "infrastructure"]' \
                '{type: $type, content: $content, context: $context, project: $project, tags: $tags}'
            )" > /dev/null 2>&1
    fi

    # Detect CI/CD config patterns
    if echo "$FILE_PATH" | grep -qiE "\.github/workflows|\.gitlab-ci|Jenkinsfile|\.circleci"; then
        curl -s -X POST "$MEMORY_API/memories" \
            -H "Content-Type: application/json" \
            -d "$(jq -n \
                --arg type "pattern" \
                --arg content "CI/CD configuration: $FILE_PATH" \
                --arg context "Modified via $TOOL_NAME" \
                --arg project "$PROJECT" \
                --argjson tags '["auto-captured", "ci-cd", "infrastructure"]' \
                '{type: $type, content: $content, context: $context, project: $project, tags: $tags}'
            )" > /dev/null 2>&1
    fi
fi

exit 0
