#!/bin/bash
# Context7 Documentation Capture Hook - PostToolUse
# Automatically stores library docs fetched via Context7 MCP into memory

MEMORY_API="http://localhost:8100"

# Read hook input from stdin
INPUT=$(cat)

# Only process get-library-docs (not resolve-library-id)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // "unknown"')
if [ "$TOOL_NAME" != "mcp__context7__get-library-docs" ]; then
    exit 0
fi

# Extract input parameters (Claude Code uses tool_input / tool_response)
LIBRARY_ID=$(echo "$INPUT" | jq -r '.tool_input.context7CompatibleLibraryID // ""')
TOPIC=$(echo "$INPUT" | jq -r '.tool_input.topic // ""')
TOKENS=$(echo "$INPUT" | jq -r '.tool_input.tokens // 5000')

# Extract documentation output (tool_response is an array of {type, text} objects)
DOC_OUTPUT=$(echo "$INPUT" | jq -r '[.tool_response[]? | .text // empty] | join("\n\n---\n\n")')

# Skip if no library ID or empty output
if [ -z "$LIBRARY_ID" ] || [ -z "$DOC_OUTPUT" ] || [ "$DOC_OUTPUT" = "null" ]; then
    exit 0
fi

# Skip very short responses (errors, empty results)
DOC_LENGTH=${#DOC_OUTPUT}
if [ "$DOC_LENGTH" -lt 200 ]; then
    exit 0
fi

# Health check — exit silently if memory service unavailable
if ! curl -sf "$MEMORY_API/health" >/dev/null 2>&1; then
    exit 0
fi

# Build a dedup key from library + topic
DEDUP_QUERY="context7 $LIBRARY_ID"
if [ -n "$TOPIC" ] && [ "$TOPIC" != "null" ]; then
    DEDUP_QUERY="context7 $LIBRARY_ID $TOPIC"
fi

# Check for existing docs memory with same library+topic
EXISTING=$(curl -s -X POST "$MEMORY_API/memories/search" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
        --arg query "$DEDUP_QUERY" \
        --arg type "docs" \
        '{query: $query, type: $type, limit: 3}'
    )" 2>/dev/null)

# Check if we already have docs for this exact library+topic combo
ALREADY_EXISTS=$(echo "$EXISTING" | jq -r --arg lib "$LIBRARY_ID" --arg topic "${TOPIC:-}" '
    [.[] | select(
        (.memory.source // "" | contains($lib)) and
        (($topic == "") or (.memory.tags // [] | any(. == $topic)))
    )] | length
' 2>/dev/null)

if [ "$ALREADY_EXISTS" != "0" ] && [ "$ALREADY_EXISTS" != "null" ] && [ -n "$ALREADY_EXISTS" ]; then
    exit 0
fi

# Extract library name from ID (e.g., "/vercel/next.js" -> "next.js")
LIB_NAME=$(echo "$LIBRARY_ID" | sed 's|.*/||')
LIB_ORG=$(echo "$LIBRARY_ID" | sed 's|^/||' | sed 's|/.*||')

# Build title
TITLE="$LIB_NAME documentation"
if [ -n "$TOPIC" ] && [ "$TOPIC" != "null" ]; then
    TITLE="$LIB_NAME documentation: $TOPIC"
fi

# Truncate content to 8000 chars (enough for useful reference, fits quality requirements)
CONTENT_PREVIEW=$(echo "$DOC_OUTPUT" | head -c 8000)

# Build tags
TAGS="[\"context7\", \"documentation\", \"auto-captured\", \"$LIB_NAME\""
if [ -n "$LIB_ORG" ] && [ "$LIB_ORG" != "$LIB_NAME" ]; then
    TAGS="$TAGS, \"$LIB_ORG\""
fi
if [ -n "$TOPIC" ] && [ "$TOPIC" != "null" ]; then
    TAGS="$TAGS, \"$TOPIC\""
fi
TAGS="$TAGS]"

# Get current project
PROJECT=$(basename "$(pwd)")

# Build context
CONTEXT="Fetched via Context7 MCP (${LIBRARY_ID})"
if [ -n "$TOPIC" ] && [ "$TOPIC" != "null" ]; then
    CONTEXT="$CONTEXT, topic: $TOPIC"
fi
CONTEXT="$CONTEXT. Tokens: $TOKENS"

# Store as docs memory
curl -s -X POST "$MEMORY_API/memories" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
        --arg type "docs" \
        --arg content "$TITLE — $CONTENT_PREVIEW" \
        --arg source "context7://$LIBRARY_ID" \
        --arg project "$PROJECT" \
        --arg context "$CONTEXT" \
        --argjson tags "$TAGS" \
        '{type: $type, content: $content, source: $source, project: $project, context: $context, tags: $tags}'
    )" > /dev/null 2>&1

exit 0
