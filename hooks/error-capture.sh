#!/bin/bash
# Error Capture Hook - Notification
# Captures error notifications

MEMORY_API="http://localhost:8100"

# Read hook input from stdin
INPUT=$(cat)

# Parse notification
MESSAGE=$(echo "$INPUT" | jq -r '.message // .notification // ""')
LEVEL=$(echo "$INPUT" | jq -r '.level // "error"')

# Only capture errors and warnings
if [ "$LEVEL" != "error" ] && [ "$LEVEL" != "warning" ]; then
    exit 0
fi

# Skip empty messages
if [ -z "$MESSAGE" ] || [ "$MESSAGE" = "null" ]; then
    exit 0
fi

# Get current project
PROJECT=$(basename "$(pwd)")

# Store error notification
curl -s -X POST "$MEMORY_API/memories" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
        --arg type "error" \
        --arg content "Notification ($LEVEL): $MESSAGE" \
        --arg error_message "$MESSAGE" \
        --arg project "$PROJECT" \
        --argjson tags '["auto-captured", "notification"]' \
        '{type: $type, content: $content, error_message: $error_message, project: $project, tags: $tags}'
    )" > /dev/null 2>&1

exit 0
