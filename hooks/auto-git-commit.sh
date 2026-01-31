#!/bin/bash
# Auto Git Commit Hook
# Automatically commits and optionally pushes changes when Claude finishes a task
# Runs on Stop hook (when Claude finishes responding)

# Configuration
AUTO_COMMIT_ENABLED=${CLAUDE_AUTO_COMMIT:-true}
AUTO_PUSH_ENABLED=${CLAUDE_AUTO_PUSH:-false}  # Set to true to auto-push
MIN_FILES_CHANGED=${CLAUDE_MIN_FILES_CHANGED:-1}
LOG_FILE="$HOME/.claude/logs/auto-git.log"

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Exit if auto-commit is disabled
if [ "$AUTO_COMMIT_ENABLED" != "true" ]; then
    exit 0
fi

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log "⏭️  Not in a git repository, skipping auto-commit"
    exit 0
fi

# Check for unstaged/staged changes
if git diff --quiet && git diff --cached --quiet; then
    log "⏭️  No changes to commit"
    exit 0
fi

# Get list of changed files
CHANGED_FILES=$(git status --short | wc -l | tr -d ' ')

if [ "$CHANGED_FILES" -lt "$MIN_FILES_CHANGED" ]; then
    log "⏭️  Only $CHANGED_FILES file(s) changed, minimum is $MIN_FILES_CHANGED"
    exit 0
fi

# Get summary of changes
MODIFIED_FILES=$(git status --short | grep '^ M' | awk '{print $2}' | head -5)
NEW_FILES=$(git status --short | grep '^??' | awk '{print $2}' | head -5)
DELETED_FILES=$(git status --short | grep '^ D' | awk '{print $2}' | head -5)

# Count changes by type
MODIFIED_COUNT=$(git status --short | grep '^ M' | wc -l | tr -d ' ')
NEW_COUNT=$(git status --short | grep '^??' | wc -l | tr -d ' ')
DELETED_COUNT=$(git status --short | grep '^ D' | wc -l | tr -d ' ')

log "📊 Changes detected:"
log "   Modified: $MODIFIED_COUNT files"
log "   New: $NEW_COUNT files"
log "   Deleted: $DELETED_COUNT files"

# Generate intelligent commit message
COMMIT_MSG="Auto-commit: Claude Code session $(date '+%Y-%m-%d %H:%M')"

if [ "$MODIFIED_COUNT" -gt 0 ]; then
    COMMIT_MSG="$COMMIT_MSG

Modified files ($MODIFIED_COUNT):
$(echo "$MODIFIED_FILES" | head -5 | sed 's/^/  - /')"
fi

if [ "$NEW_COUNT" -gt 0 ]; then
    COMMIT_MSG="$COMMIT_MSG

New files ($NEW_COUNT):
$(echo "$NEW_FILES" | head -5 | sed 's/^/  - /')"
fi

if [ "$DELETED_COUNT" -gt 0 ]; then
    COMMIT_MSG="$COMMIT_MSG

Deleted files ($DELETED_COUNT):
$(echo "$DELETED_FILES" | head -5 | sed 's/^/  - /')"
fi

# Add Claude Code attribution
COMMIT_MSG="$COMMIT_MSG

Co-Authored-By: Claude <noreply@anthropic.com>"

# Stage all changes
log "📦 Staging changes..."
git add -A

if [ $? -ne 0 ]; then
    log "❌ Failed to stage changes"
    exit 1
fi

# Create commit
log "💾 Creating commit..."
git commit -m "$COMMIT_MSG" > /dev/null 2>&1

if [ $? -ne 0 ]; then
    log "❌ Failed to create commit"
    exit 1
fi

COMMIT_HASH=$(git rev-parse --short HEAD)
log "✅ Commit created: $COMMIT_HASH"

# Auto-push if enabled
if [ "$AUTO_PUSH_ENABLED" = "true" ]; then
    # Check if we have a remote
    if ! git remote -v | grep -q origin; then
        log "⚠️  No remote 'origin' found, skipping push"
        exit 0
    fi

    # Get current branch
    CURRENT_BRANCH=$(git branch --show-current)

    if [ -z "$CURRENT_BRANCH" ]; then
        log "⚠️  Not on a branch, skipping push"
        exit 0
    fi

    # Check if branch has upstream
    if ! git rev-parse --abbrev-ref --symbolic-full-name @{u} > /dev/null 2>&1; then
        log "⚠️  No upstream branch, skipping push"
        log "   Set upstream with: git push -u origin $CURRENT_BRANCH"
        exit 0
    fi

    log "🚀 Pushing to remote..."
    git push > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        log "✅ Pushed to origin/$CURRENT_BRANCH"
    else
        log "❌ Failed to push to remote"
        exit 1
    fi
else
    log "⏭️  Auto-push disabled (set CLAUDE_AUTO_PUSH=true to enable)"
fi

log "────────────────────────────────────────"
exit 0
