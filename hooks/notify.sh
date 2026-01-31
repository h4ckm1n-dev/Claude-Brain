#!/bin/bash
# Claude Code Fancy Notifications - Catppuccin Mocha Edition
# A beautiful macOS notification system for Claude Code
#
# Usage:
#   ./notify.sh success "Title" "Message" "Subtitle"
#   ./notify.sh error "Title" "Message"
#   ./notify.sh info "Title" "Message"

# Configuration - Sounds for different notification types
SOUND_SUCCESS="Glass"
SOUND_ERROR="Basso"
SOUND_WARNING="Purr"
SOUND_INFO="Pop"
SOUND_TASK="Submarine"

# Catppuccin Mocha themed emojis
EMOJI_SUCCESS="✓"
EMOJI_ERROR="✗"
EMOJI_WARNING="⚠"
EMOJI_INFO="ℹ"
EMOJI_TASK="⚡"
EMOJI_AGENT="⚙"
EMOJI_COMPLETE="✨"
EMOJI_BUILD="🔨"
EMOJI_TEST="🧪"
EMOJI_DEPLOY="🚀"

# Parse positional arguments
TYPE="${1:-info}"
TITLE="${2:-Claude Code}"
MESSAGE="${3:-}"
SUBTITLE="${4:-}"

# Skip empty notifications
if [ -z "$MESSAGE" ]; then
    exit 0
fi

# Get emoji and sound based on type
case "$TYPE" in
    success|complete|done)
        EMOJI="$EMOJI_SUCCESS"
        SOUND="$SOUND_SUCCESS"
        ;;
    error|fail|failed)
        EMOJI="$EMOJI_ERROR"
        SOUND="$SOUND_ERROR"
        ;;
    warning|warn)
        EMOJI="$EMOJI_WARNING"
        SOUND="$SOUND_WARNING"
        ;;
    task|working|progress)
        EMOJI="$EMOJI_TASK"
        SOUND="$SOUND_TASK"
        ;;
    agent)
        EMOJI="$EMOJI_AGENT"
        SOUND="$SOUND_INFO"
        ;;
    build)
        EMOJI="$EMOJI_BUILD"
        SOUND="$SOUND_SUCCESS"
        ;;
    test)
        EMOJI="$EMOJI_TEST"
        SOUND="$SOUND_INFO"
        ;;
    deploy)
        EMOJI="$EMOJI_DEPLOY"
        SOUND="$SOUND_SUCCESS"
        ;;
    celebrate)
        EMOJI="$EMOJI_COMPLETE"
        SOUND="$SOUND_SUCCESS"
        ;;
    *)
        EMOJI="$EMOJI_INFO"
        SOUND="$SOUND_INFO"
        ;;
esac

# Escape special characters for AppleScript
escape_applescript() {
    local str="$1"
    str="${str//\\/\\\\}"
    str="${str//\"/\\\"}"
    str="${str//$'\n'/ }"
    echo "$str"
}

DISPLAY_TITLE=$(escape_applescript "$EMOJI $TITLE")
DISPLAY_MESSAGE=$(escape_applescript "$MESSAGE")
DISPLAY_SUBTITLE=$(escape_applescript "$SUBTITLE")

# Log notification
mkdir -p "${HOME}/.claude/logs"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$TYPE] $TITLE: $MESSAGE" >> "${HOME}/.claude/logs/notifications.log" 2>/dev/null || true

# Send notification using osascript
if [ -n "$SUBTITLE" ]; then
    osascript -e "display notification \"$DISPLAY_MESSAGE\" with title \"$DISPLAY_TITLE\" subtitle \"$DISPLAY_SUBTITLE\" sound name \"$SOUND\"" 2>/dev/null || true
else
    osascript -e "display notification \"$DISPLAY_MESSAGE\" with title \"$DISPLAY_TITLE\" sound name \"$SOUND\"" 2>/dev/null || true
fi
