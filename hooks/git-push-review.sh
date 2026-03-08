#!/bin/bash
# Git Push Review Reminder — PreToolUse (Bash)
# Reminds to review changes before pushing to remote

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

# Only trigger on git push (not --force checks, that's block-destructive-commands.sh)
if ! echo "$COMMAND" | grep -qE '\bgit\s+push\b'; then
    exit 0
fi

# Skip if it's a dry-run
if echo "$COMMAND" | grep -qE '\-\-dry-run'; then
    exit 0
fi

# Check if there are unpushed commits to review
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ -z "$BRANCH" ]; then
    exit 0
fi

# Get upstream tracking branch
UPSTREAM=$(git rev-parse --abbrev-ref "@{upstream}" 2>/dev/null)
if [ -z "$UPSTREAM" ]; then
    # No upstream — first push, just remind
    echo "First push for branch '$BRANCH'. Make sure all changes are committed and reviewed."
    exit 0
fi

# Count unpushed commits
AHEAD=$(git rev-list --count "$UPSTREAM..HEAD" 2>/dev/null)
if [ "$AHEAD" = "0" ]; then
    exit 0
fi

echo "Pushing $AHEAD commit(s) on '$BRANCH'. Review with: git log --oneline $UPSTREAM..HEAD"

exit 0
