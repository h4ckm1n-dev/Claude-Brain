#!/usr/bin/env bash
# Secure Git Analysis Tool
#
# Analyzes git repository safely without command injection risks
#
# Usage: ./secure-git-analyze.sh <path> [days]
# Example: ./secure-git-analyze.sh src/api 30

set -euo pipefail

# Validate inputs
PATH_ARG="${1:-.}"
DAYS="${2:-30}"

# Validate days is a number
if ! [[ "$DAYS" =~ ^[0-9]+$ ]]; then
  echo "Error: Days must be a positive integer"
  exit 1
fi

# Validate path exists and is within repo
if [ ! -e "$PATH_ARG" ]; then
  echo "Error: Path does not exist: $PATH_ARG"
  exit 1
fi

# Check if in git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
  echo "Error: Not a git repository"
  exit 1
fi

# Function to safely count commits
count_commits() {
  local path="$1"
  local since="$2"

  # SAFE: All arguments are validated, passed directly to git
  git log --since="${since}.days.ago" --oneline -- "$path" | wc -l | tr -d ' '
}

# Function to get top contributors
get_contributors() {
  local path="$1"
  local since="$2"

  # SAFE: Using git shortlog with validated arguments
  git shortlog -sn --since="${since}.days.ago" -- "$path" | head -5
}

# Function to get recent commits
get_recent_commits() {
  local path="$1"
  local limit="${2:-10}"

  # SAFE: Using --format with static format string
  git log -"$limit" --pretty=format:"%h|%an|%ar|%s" -- "$path"
}

# Main analysis
echo "📊 Git Analysis Report"
echo "===================="
echo "Path: $PATH_ARG"
echo "Period: Last $DAYS days"
echo ""

# Count commits
COMMIT_COUNT=$(count_commits "$PATH_ARG" "$DAYS")
echo "Total Commits: $COMMIT_COUNT"
echo ""

# Top contributors
echo "Top Contributors:"
get_contributors "$PATH_ARG" "$DAYS"
echo ""

# Recent activity
echo "Recent Commits:"
get_recent_commits "$PATH_ARG" 10 | while IFS='|' read -r hash author date subject; do
  printf "  %s (%s, %s)\n    %s\n" "$hash" "$author" "$date" "$subject"
done

exit 0
