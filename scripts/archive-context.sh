#!/usr/bin/env bash
# Archives PROJECT_CONTEXT.md when it exceeds 1000 lines
# Usage: ./archive-context.sh [project-root]

set -euo pipefail

PROJECT_ROOT="${1:-.}"
CONTEXT_FILE="$PROJECT_ROOT/PROJECT_CONTEXT.md"
LINE_THRESHOLD=1000

if [ ! -f "$CONTEXT_FILE" ]; then
  echo "❌ PROJECT_CONTEXT.md not found at: $CONTEXT_FILE"
  exit 1
fi

LINE_COUNT=$(wc -l < "$CONTEXT_FILE")

if [ "$LINE_COUNT" -le "$LINE_THRESHOLD" ]; then
  echo "✅ PROJECT_CONTEXT.md size OK ($LINE_COUNT lines, threshold: $LINE_THRESHOLD)"
  exit 0
fi

echo "📦 Archiving PROJECT_CONTEXT.md ($LINE_COUNT lines > $LINE_THRESHOLD threshold)"

# Create archive filename
ARCHIVE_DATE=$(date +"%Y%m%d_%H%M%S")
ARCHIVE_FILE="$PROJECT_ROOT/PROJECT_CONTEXT_ARCHIVE_${ARCHIVE_DATE}.md"

# Move to archive
cp "$CONTEXT_FILE" "$ARCHIVE_FILE"
echo "✅ Archived to: $ARCHIVE_FILE"

# Keep last 200 lines of activity + header/structure
# CRITICAL: Preserve required sections
{
  # Extract and keep header section (up to first ## heading, excluding the ## line itself)
  sed -n '1,/^## /{/^## /!p;}' "$CONTEXT_FILE"

  # Add archive reference
  echo ""
  echo "**Previous Archives**: See PROJECT_CONTEXT_ARCHIVE_*.md files"
  echo ""
  echo "---"
  echo ""

  # Keep last 200 lines of activity
  tail -200 "$CONTEXT_FILE"
} > "${CONTEXT_FILE}.new"

mv "${CONTEXT_FILE}.new" "$CONTEXT_FILE"

NEW_LINE_COUNT=$(wc -l < "$CONTEXT_FILE")
echo "✅ PROJECT_CONTEXT.md refreshed (now $NEW_LINE_COUNT lines, was $LINE_COUNT lines)"
echo "✅ Archive contains full history: $ARCHIVE_FILE"
exit 0
