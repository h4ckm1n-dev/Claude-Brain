#!/bin/bash
# Archives old PROJECT_CONTEXT.md entries (>30 days)
# Usage: ./cleanup-context.sh [project-root]

set -euo pipefail

PROJECT_ROOT="${1:-.}"
CONTEXT_FILE="$PROJECT_ROOT/PROJECT_CONTEXT.md"
ARCHIVE_FILE="$PROJECT_ROOT/PROJECT_ARCHIVE.md"

echo "🗂️  PROJECT_CONTEXT.md Cleanup Utility"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if PROJECT_CONTEXT.md exists
if [ ! -f "$CONTEXT_FILE" ]; then
  echo "ℹ️  PROJECT_CONTEXT.md not found at: $CONTEXT_FILE"
  echo "   Nothing to clean up"
  exit 0
fi

echo "📁 Analyzing: $CONTEXT_FILE"

# Check file size
size=$(wc -c < "$CONTEXT_FILE")
size_kb=$(echo "scale=1; $size / 1024" | bc)
lines=$(wc -l < "$CONTEXT_FILE")

echo "   Size: ${size_kb}KB ($lines lines)"

# Size thresholds
size_ok=51200      # 50KB
size_warning=102400 # 100KB

if [ "$size" -lt "$size_ok" ]; then
  echo "✅ File size OK (${size_kb}KB < 50KB)"
  echo "   No cleanup needed yet"
  exit 0
elif [ "$size" -lt "$size_warning" ]; then
  echo "⚠️  File size moderate (${size_kb}KB)"
  echo "   Consider archiving soon"
else
  echo "⚠️  File size large (${size_kb}KB > 100KB)"
  echo "   Archiving recommended"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Archive Strategy:"
echo ""

# Calculate cutoff date (30 days ago)
thirty_days_ago=$(date -v-30d +%Y-%m-%d 2>/dev/null || date -d "30 days ago" +%Y-%m-%d 2>/dev/null || echo "unknown")

if [ "$thirty_days_ago" = "unknown" ]; then
  echo "⚠️  Unable to calculate date (platform compatibility issue)"
  echo "   Please manually archive old entries"
  exit 0
fi

echo "📅 Archive entries older than: $thirty_days_ago"

# Count old entries
old_entries=$(grep -c "^\*\*[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]" "$CONTEXT_FILE" 2>/dev/null | \
  awk -v cutoff="$thirty_days_ago" '{
    # This is a simplified count - actual filtering would be more complex
    print $1
  }' || echo "0")

echo "   Estimated old entries: ~$old_entries"

# Check if archive file exists
if [ -f "$ARCHIVE_FILE" ]; then
  archive_size=$(wc -c < "$ARCHIVE_FILE")
  archive_size_kb=$(echo "scale=1; $archive_size / 1024" | bc)
  echo "📦 Existing archive: ${archive_size_kb}KB"
else
  echo "📦 No archive file yet (will create: $ARCHIVE_FILE)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Recommended Actions:"
echo ""
echo "1. Manual Review:"
echo "   - Review PROJECT_CONTEXT.md"
echo "   - Identify completed sprints/features from >30 days ago"
echo "   - Check for outdated decisions or issues"
echo ""
echo "2. Archive Old Content:"
echo "   - Create/append to: $ARCHIVE_FILE"
echo "   - Move agent activity logs from >30 days ago"
echo "   - Move resolved issues and completed features"
echo "   - Keep recent decisions and active work"
echo ""
echo "3. What to Keep in PROJECT_CONTEXT.md:"
echo "   ✅ Current sprint goals"
echo "   ✅ Active agent work (last 30 days)"
echo "   ✅ Recent decisions still relevant"
echo "   ✅ Active blockers"
echo "   ✅ Artifacts for current work"
echo ""
echo "4. What to Archive:"
echo "   📦 Agent activity >30 days old"
echo "   📦 Completed sprints"
echo "   📦 Resolved issues"
echo "   📦 Superseded decisions"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create archive file header if doesn't exist
if [ ! -f "$ARCHIVE_FILE" ]; then
  echo ""
  echo "Creating archive file template..."

  cat > "$ARCHIVE_FILE" <<EOF
# PROJECT_CONTEXT.md Archive

This file contains archived entries from PROJECT_CONTEXT.md that are no longer actively needed but should be preserved for historical reference.

## Archive Policy

- Entries older than 30 days
- Completed sprints and features
- Resolved issues
- Superseded decisions

---

## Archived $(date +%Y-%m-%d)

(Manual archiving - review PROJECT_CONTEXT.md and move old content here)

---

EOF

  echo "✅ Created: $ARCHIVE_FILE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  Note: This script provides guidance only"
echo "   Manual review and archiving recommended to preserve context"
echo ""
echo "Next Steps:"
echo "  1. Review $CONTEXT_FILE"
echo "  2. Move old content to $ARCHIVE_FILE"
echo "  3. Keep last 30 days of activity in PROJECT_CONTEXT.md"
echo ""
echo "✅ Cleanup analysis complete"
