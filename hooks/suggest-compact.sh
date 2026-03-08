#!/bin/bash
# Strategic Compact Suggestion
# Triggers: PostToolUse (Write, Edit) — async
# Purpose: Track tool call count per session and suggest /compact at logical intervals

THRESHOLD=${COMPACT_THRESHOLD:-50}
REMIND_INTERVAL=25
SESSION_ID="${CLAUDE_SESSION_ID:-default}"
COUNTER_FILE="/tmp/.claude-tool-count-${SESSION_ID}"

# Read and increment counter
if [ -f "$COUNTER_FILE" ]; then
    COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo "0")
else
    COUNT=0
fi
COUNT=$((COUNT + 1))
echo "$COUNT" > "$COUNTER_FILE"

# Check if we should suggest compaction
if [ "$COUNT" -eq "$THRESHOLD" ]; then
    echo "You've made ${COUNT} tool calls this session. Consider running /compact to free context window before continuing."
elif [ "$COUNT" -gt "$THRESHOLD" ]; then
    SINCE_THRESHOLD=$((COUNT - THRESHOLD))
    REMAINDER=$((SINCE_THRESHOLD % REMIND_INTERVAL))
    if [ "$REMAINDER" -eq 0 ]; then
        echo "Reminder: ${COUNT} tool calls this session. Run /compact if working memory feels crowded."
    fi
fi

exit 0
