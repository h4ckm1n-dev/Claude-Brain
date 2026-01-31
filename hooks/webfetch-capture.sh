#!/bin/bash
# WebFetch Capture Hook - PostToolUse
# Automatically captures useful documentation from WebFetch results

MEMORY_API="http://localhost:8100"

# Read hook input from stdin
INPUT=$(cat)

# Parse tool name - only process WebFetch
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // .tool // "unknown"')
if [ "$TOOL_NAME" != "WebFetch" ]; then
    exit 0
fi

# Extract URL and content
URL=$(echo "$INPUT" | jq -r '.input.url // .arguments.url // ""')
OUTPUT=$(echo "$INPUT" | jq -r '.output // .result // ""')

# Skip if no URL or output
if [ -z "$URL" ] || [ -z "$OUTPUT" ] || [ "$OUTPUT" = "null" ]; then
    exit 0
fi

# Skip non-documentation URLs
case "$URL" in
    *google.com/search*|*bing.com*|*duckduckgo.com*)
        exit 0
        ;;
esac

# Detect documentation domains
DOC_DOMAINS="docs\.|documentation\.|api\.|developer\.|devdocs\.|readme\.|wiki\.|learn\.|guide"
IS_DOCS=false
if echo "$URL" | grep -qiE "$DOC_DOMAINS"; then
    IS_DOCS=true
fi

# Detect documentation content patterns
DOC_PATTERNS="API Reference|Documentation|Getting Started|Installation|Usage|Parameters|Returns|Example|Syntax|Configuration"
if echo "$OUTPUT" | grep -qiE "$DOC_PATTERNS"; then
    IS_DOCS=true
fi

# Only capture if it looks like documentation
if [ "$IS_DOCS" = false ]; then
    exit 0
fi

# Extract domain for tagging
DOMAIN=$(echo "$URL" | sed -E 's|https?://([^/]+).*|\1|' | sed 's/^www\.//')

# Truncate content to first 2000 chars for storage
CONTENT_PREVIEW=$(echo "$OUTPUT" | head -c 2000)

# Try to extract a title or heading
TITLE=$(echo "$OUTPUT" | grep -m1 -oE "^#+ .+" | sed 's/^#* //' | head -c 100)
if [ -z "$TITLE" ]; then
    TITLE="Documentation from $DOMAIN"
fi

# Get current project
PROJECT=$(basename "$(pwd)")

# Store as docs memory
curl -s -X POST "$MEMORY_API/memories" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
        --arg type "docs" \
        --arg content "$TITLE: $CONTENT_PREVIEW" \
        --arg source "$URL" \
        --arg project "$PROJECT" \
        --arg context "Fetched from: $URL" \
        --argjson tags "[\"auto-captured\", \"documentation\", \"$DOMAIN\"]" \
        '{type: $type, content: $content, source: $source, project: $project, context: $context, tags: $tags}'
    )" > /dev/null 2>&1

exit 0
