#!/bin/bash
# Smart Git Commit Hook
# Analyzes session context to generate intelligent commit messages
# Uses file tracking and session summaries for better commit messages

LOG_FILE="$HOME/.claude/logs/auto-git.log"
SESSION_FILE="/tmp/claude/current-session-summary.txt"
EDIT_TRACKER="$HOME/.claude/logs/file-edits.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Configuration - can be set in environment
AUTO_COMMIT_SMART=${CLAUDE_AUTO_COMMIT_SMART:-true}
AUTO_PUSH=${CLAUDE_AUTO_PUSH:-false}

if [ "$AUTO_COMMIT_SMART" != "true" ]; then
    exit 0
fi

# Check if in git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    exit 0
fi

# Check for changes
if git diff --quiet && git diff --cached --quiet; then
    exit 0
fi

# Try to extract session summary for commit message
SESSION_SUMMARY=""
if [ -f "$SESSION_FILE" ]; then
    SESSION_SUMMARY=$(head -3 "$SESSION_FILE" | grep -v "^#" | grep -v "^$")
fi

# Analyze changed files to determine type of work
CHANGED_FILES=$(git status --short)

# Detect type of changes
HAS_TESTS=$(echo "$CHANGED_FILES" | grep -c -E "(test|spec)\.(ts|js|py|go)")
HAS_DOCS=$(echo "$CHANGED_FILES" | grep -c -E "(README|CHANGELOG|\.md$)")
HAS_CONFIG=$(echo "$CHANGED_FILES" | grep -c -E "(package\.json|requirements\.txt|Cargo\.toml|go\.mod|\.env\.example)")
HAS_FRONTEND=$(echo "$CHANGED_FILES" | grep -c -E "\.(tsx?|jsx?|vue|svelte)$")
HAS_BACKEND=$(echo "$CHANGED_FILES" | grep -c -E "(server|api|route|controller|service)\.(ts|js|py|go)")
HAS_HOOKS=$(echo "$CHANGED_FILES" | grep -c -E "hooks/.*\.sh$")
HAS_AGENTS=$(echo "$CHANGED_FILES" | grep -c -E "agents/.*\.md$")

# Determine commit type
COMMIT_TYPE="chore"
SCOPE=""

if [ "$HAS_TESTS" -gt 0 ]; then
    COMMIT_TYPE="test"
    SCOPE="tests"
elif [ "$HAS_DOCS" -gt 0 ]; then
    COMMIT_TYPE="docs"
    SCOPE="documentation"
elif [ "$HAS_CONFIG" -gt 0 ]; then
    COMMIT_TYPE="chore"
    SCOPE="config"
elif [ "$HAS_FRONTEND" -gt 0 ] && [ "$HAS_BACKEND" -gt 0 ]; then
    COMMIT_TYPE="feat"
    SCOPE="full-stack"
elif [ "$HAS_FRONTEND" -gt 0 ]; then
    COMMIT_TYPE="feat"
    SCOPE="frontend"
elif [ "$HAS_BACKEND" -gt 0 ]; then
    COMMIT_TYPE="feat"
    SCOPE="backend"
elif [ "$HAS_HOOKS" -gt 0 ]; then
    COMMIT_TYPE="feat"
    SCOPE="hooks"
elif [ "$HAS_AGENTS" -gt 0 ]; then
    COMMIT_TYPE="docs"
    SCOPE="agents"
fi

# Extract main changed file for description
MAIN_FILE=$(echo "$CHANGED_FILES" | head -1 | awk '{print $2}' | xargs basename)

# Build commit message
if [ -n "$SESSION_SUMMARY" ]; then
    # Use session summary if available
    COMMIT_MSG="$COMMIT_TYPE($SCOPE): $SESSION_SUMMARY"
else
    # Generate from file changes
    FILE_COUNT=$(echo "$CHANGED_FILES" | wc -l | tr -d ' ')

    if [ "$FILE_COUNT" -eq 1 ]; then
        COMMIT_MSG="$COMMIT_TYPE($SCOPE): update $MAIN_FILE"
    else
        COMMIT_MSG="$COMMIT_TYPE($SCOPE): update $FILE_COUNT files"
    fi
fi

# Add detailed body
COMMIT_BODY=""

# Add changed files summary
COMMIT_BODY="$COMMIT_BODY
Changed files:
$(echo "$CHANGED_FILES" | head -10 | sed 's/^/  /')"

# Add session context if available
if [ -f "$SESSION_FILE" ]; then
    CONTEXT=$(tail -5 "$SESSION_FILE" | grep -v "^#" | grep -v "^$")
    if [ -n "$CONTEXT" ]; then
        COMMIT_BODY="$COMMIT_BODY

Session context:
$(echo "$CONTEXT" | sed 's/^/  /')"
    fi
fi

# Full commit message
FULL_MSG="$COMMIT_MSG

$COMMIT_BODY

Co-Authored-By: Claude <noreply@anthropic.com>"

# Stage and commit
log "📦 Smart commit: $COMMIT_TYPE($SCOPE)"
git add -A

git commit -m "$FULL_MSG" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    COMMIT_HASH=$(git rev-parse --short HEAD)
    log "✅ Smart commit created: $COMMIT_HASH"
    log "   Type: $COMMIT_TYPE, Scope: $SCOPE"

    # Auto-push if enabled
    if [ "$AUTO_PUSH" = "true" ]; then
        CURRENT_BRANCH=$(git branch --show-current)

        if git rev-parse --abbrev-ref --symbolic-full-name @{u} > /dev/null 2>&1; then
            log "🚀 Pushing to remote..."
            git push > /dev/null 2>&1

            if [ $? -eq 0 ]; then
                log "✅ Pushed to origin/$CURRENT_BRANCH"
            else
                log "❌ Failed to push"
            fi
        else
            log "⏭️  No upstream branch configured"
        fi
    fi
else
    log "❌ Failed to create commit"
    exit 1
fi

log "────────────────────────────────────────"
exit 0
