#!/bin/bash
# Validates PROJECT_CONTEXT.md health and coordination state
# Usage: ./validate-coordination.sh [project-root]

set -euo pipefail

PROJECT_ROOT="${1:-.}"
CONTEXT_FILE="${PROJECT_ROOT}/PROJECT_CONTEXT.md"

echo "🔍 Validating Agent Coordination..."

# Check PROJECT_CONTEXT.md exists
if [ ! -f "$CONTEXT_FILE" ]; then
  echo "❌ PROJECT_CONTEXT.md not found at $CONTEXT_FILE"
  echo "   Fix: Run 'cp ~/.claude/PROJECT_CONTEXT_TEMPLATE.md $CONTEXT_FILE'"
  exit 1
fi

echo "✅ PROJECT_CONTEXT.md found"

# Check for required sections
required_sections=(
  "## Agent Activity Log"
  "## Artifacts for Other Agents"
  "## Active Blockers"
  "## Shared Decisions"
)

missing_sections=0
for section in "${required_sections[@]}"; do
  if ! grep -q "$section" "$CONTEXT_FILE"; then
    echo "❌ Missing required section: $section"
    missing_sections=$((missing_sections + 1))
  else
    echo "✅ Section found: $section"
  fi
done

if [ $missing_sections -gt 0 ]; then
  echo "❌ Found $missing_sections missing sections"
  echo "   Fix: Update PROJECT_CONTEXT.md with missing sections from template"
  exit 1
fi

# Check for recent activity (last 7 days)
if [ "$(uname)" = "Darwin" ]; then
  # macOS
  if [ -n "$(find "$CONTEXT_FILE" -mtime +7 2>/dev/null || true)" ]; then
    echo "⚠️  PROJECT_CONTEXT.md hasn't been updated in 7+ days"
  else
    echo "✅ PROJECT_CONTEXT.md recently updated"
  fi
else
  # Linux
  if [ -n "$(find "$CONTEXT_FILE" -mtime +7 2>/dev/null || true)" ]; then
    echo "⚠️  PROJECT_CONTEXT.md hasn't been updated in 7+ days"
  else
    echo "✅ PROJECT_CONTEXT.md recently updated"
  fi
fi

# Check file size (warn if > 100KB)
size=$(wc -c < "$CONTEXT_FILE")
if [ "$size" -gt 102400 ]; then
  size_readable=$(echo "scale=1; $size / 1024" | bc)
  echo "⚠️  PROJECT_CONTEXT.md is large (${size_readable}KB). Consider archiving old content."
else
  size_readable=$(echo "scale=1; $size / 1024" | bc)
  echo "✅ PROJECT_CONTEXT.md size is reasonable (${size_readable}KB)"
fi

# Check for active blockers
blocker_count=$(grep -c "## Active Blockers" "$CONTEXT_FILE" || echo "0")
if grep -q "BLOCKER-.*OPEN" "$CONTEXT_FILE" 2>/dev/null; then
  echo "⚠️  Active blockers found - check PROJECT_CONTEXT.md"
else
  echo "✅ No active blockers"
fi

echo ""
echo "✅ Coordination validation passed"
exit 0
