#!/bin/bash
# WebSearch Capture Hook - PostToolUse
# Automatically captures web search results into memory for future reference
#
# WebSearch tool_response format (different from WebFetch!):
#   {
#     "query": "search terms",
#     "results": [
#       {"tool_use_id": "...", "content": [{"title":"...", "url":"..."}, ...]},
#       "Based on the search results, here's what I found..."   <-- text summary
#     ],
#     "durationSeconds": 1.23
#   }

MEMORY_API="http://localhost:8100"
DEBUG_LOG="/tmp/websearch-hook-debug.log"

# Read hook input from stdin
INPUT=$(cat)

# Only process WebSearch
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // "unknown"')
if [ "$TOOL_NAME" != "WebSearch" ]; then
    exit 0
fi

# Extract search query
QUERY=$(echo "$INPUT" | jq -r '.tool_input.query // ""')

# Extract text summary from tool_response.results
# results is an array: [links_object, text_string, ...]
# Text elements are raw strings (not objects) — filter for strings only
SEARCH_TEXT=$(echo "$INPUT" | jq -r '
    [.tool_response.results[]? | select(type == "string")] | join("\n\n")
' 2>/dev/null)

# Extract URLs from the structured links object
URLS=$(echo "$INPUT" | jq -r '
    [.tool_response.results[]? | select(type == "object") | .content[]? | .url // empty] | join("\n")
' 2>/dev/null)

# Debug logging
echo "=== $(date -Iseconds) ===" >> "$DEBUG_LOG"
echo "QUERY: $QUERY" >> "$DEBUG_LOG"
echo "TEXT_LENGTH: ${#SEARCH_TEXT}" >> "$DEBUG_LOG"
echo "URL_COUNT: $(echo "$URLS" | grep -c 'http')" >> "$DEBUG_LOG"

# Skip if no query or empty text
if [ -z "$QUERY" ] || [ -z "$SEARCH_TEXT" ] || [ "$SEARCH_TEXT" = "null" ]; then
    echo "SKIP: empty query or text" >> "$DEBUG_LOG"
    exit 0
fi

# Skip very short responses (errors, empty results)
if [ "${#SEARCH_TEXT}" -lt 100 ]; then
    echo "SKIP: text too short (${#SEARCH_TEXT} chars)" >> "$DEBUG_LOG"
    exit 0
fi

# Health check — exit silently if memory service unavailable
if ! curl -sf "$MEMORY_API/health" >/dev/null 2>&1; then
    echo "SKIP: memory service unavailable" >> "$DEBUG_LOG"
    exit 0
fi

# Dedup: Check for existing docs memory with same search query
EXISTING=$(curl -s -X POST "$MEMORY_API/memories/search" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
        --arg query "web-search $QUERY" \
        --arg type "docs" \
        '{query: $query, type: $type, limit: 3}'
    )" 2>/dev/null)

ALREADY_EXISTS=$(echo "$EXISTING" | jq -r --arg q "$QUERY" '
    [.[] | select(
        (.memory.context // "" | contains($q))
    )] | length
' 2>/dev/null)

if [ "$ALREADY_EXISTS" != "0" ] && [ "$ALREADY_EXISTS" != "null" ] && [ -n "$ALREADY_EXISTS" ]; then
    echo "SKIP: duplicate found" >> "$DEBUG_LOG"
    exit 0
fi

# Get first URL and top domains for tagging
FIRST_URL=$(echo "$URLS" | head -1)
DOMAINS=$(echo "$URLS" | head -5 | sed -E 's|https?://([^/]+).*|\1|' | sed 's/^www\.//' | sort -u | head -3)

# Build tags
TAGS='["auto-captured", "web-search"'
for domain in $DOMAINS; do
    CLEAN_DOMAIN=$(echo "$domain" | tr -dc 'a-zA-Z0-9.-')
    if [ -n "$CLEAN_DOMAIN" ]; then
        TAGS="$TAGS, \"$CLEAN_DOMAIN\""
    fi
done
TAGS="$TAGS]"

# Truncate content to 4000 chars
CONTENT_PREVIEW=$(echo "$SEARCH_TEXT" | head -c 4000)

# Get current project from cwd
PROJECT=$(echo "$INPUT" | jq -r '.cwd // ""' | xargs basename 2>/dev/null)
if [ -z "$PROJECT" ] || [ "$PROJECT" = "/" ]; then
    PROJECT=$(basename "$(pwd)")
fi

# Build URL list for context
URL_LIST=$(echo "$URLS" | head -5 | tr '\n' ' ')

# Store as docs memory
STORE_RESULT=$(curl -s -w "\n%{http_code}" -X POST "$MEMORY_API/memories" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
        --arg type "docs" \
        --arg content "Web search: $QUERY — $CONTENT_PREVIEW" \
        --arg source "${FIRST_URL:-websearch}" \
        --arg project "$PROJECT" \
        --arg context "Web search for: $QUERY. Sources: $URL_LIST" \
        --argjson tags "$TAGS" \
        '{type: $type, content: $content, source: $source, project: $project, context: $context, tags: $tags}'
    )" 2>/dev/null)

HTTP_CODE=$(echo "$STORE_RESULT" | tail -1)
echo "STORE_HTTP: $HTTP_CODE" >> "$DEBUG_LOG"

if [ "$HTTP_CODE" = "200" ]; then
    echo "SUCCESS: stored web search for '$QUERY'" >> "$DEBUG_LOG"
else
    BODY=$(echo "$STORE_RESULT" | head -n -1)
    echo "FAILED: $BODY" >> "$DEBUG_LOG"
fi

exit 0
