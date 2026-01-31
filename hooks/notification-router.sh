#!/bin/bash
# Claude Code Notification Router
# Intelligently routes notifications to the fancy notification system
# based on content analysis

NOTIFY_SCRIPT="${HOME}/.claude/hooks/notify.sh"

# Read notification from environment or stdin
if [ -n "${CLAUDE_NOTIFICATION:-}" ]; then
    MESSAGE="$CLAUDE_NOTIFICATION"
else
    MESSAGE=$(cat 2>/dev/null || echo "")
fi

# Skip empty
if [ -z "$MESSAGE" ]; then
    exit 0
fi

# Detect notification type based on content keywords
detect_type() {
    local msg="$1"
    local lower_msg=$(echo "$msg" | tr '[:upper:]' '[:lower:]')

    # Success patterns
    if echo "$lower_msg" | grep -qE '(success|complet|finish|done|pass|built|created|saved|commit)'; then
        echo "success"
        return
    fi

    # Error patterns
    if echo "$lower_msg" | grep -qE '(error|fail|crash|exception|denied|reject|abort|fatal)'; then
        echo "error"
        return
    fi

    # Warning patterns
    if echo "$lower_msg" | grep -qE '(warn|caution|deprecat|attention|notice)'; then
        echo "warning"
        return
    fi

    # Build/compile patterns
    if echo "$lower_msg" | grep -qE '(build|compil|bundl|webpack|vite|esbuild)'; then
        echo "build"
        return
    fi

    # Test patterns
    if echo "$lower_msg" | grep -qE '(test|spec|jest|pytest|vitest|mocha)'; then
        echo "test"
        return
    fi

    # Deploy patterns
    if echo "$lower_msg" | grep -qE '(deploy|publish|release|ship|push)'; then
        echo "deploy"
        return
    fi

    # Agent patterns
    if echo "$lower_msg" | grep -qE '(agent|subagent|task tool)'; then
        echo "agent"
        return
    fi

    # Default to info
    echo "info"
}

# Detect type
TYPE=$(detect_type "$MESSAGE")

# Call notify.sh with positional arguments (more robust than JSON)
"$NOTIFY_SCRIPT" "$TYPE" "Claude Code" "$MESSAGE" "" 2>/dev/null || {
    # Fallback to basic osascript if notify.sh fails
    osascript -e "display notification \"$MESSAGE\" with title \"Claude Code\" sound name \"Pop\"" 2>/dev/null || true
}
