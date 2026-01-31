#!/bin/bash
# Validates that referenced artifacts actually exist
# Usage: ./validate-artifacts.sh [project-root]

set -euo pipefail

PROJECT_ROOT="${1:-.}"
CONTEXT_FILE="${PROJECT_ROOT}/PROJECT_CONTEXT.md"

echo "🔍 Validating Artifacts..."

# Check PROJECT_CONTEXT.md exists
if [ ! -f "$CONTEXT_FILE" ]; then
  echo "❌ PROJECT_CONTEXT.md not found at $CONTEXT_FILE"
  echo "   Fix: Run 'cp ~/.claude/PROJECT_CONTEXT_TEMPLATE.md $CONTEXT_FILE'"
  exit 1
fi

echo "✅ PROJECT_CONTEXT.md found"

# Extract artifact paths from PROJECT_CONTEXT.md
# Look for lines like: - `/path/to/artifact` or | `/path/to/artifact` |
# Using grep with Perl regex for better compatibility

artifacts=$(grep -oE '`(/[^`]+)`' "$CONTEXT_FILE" 2>/dev/null | sed 's/`//g' || true)

if [ -z "$artifacts" ]; then
  echo "ℹ️  No artifacts documented yet"
  exit 0
fi

echo "📋 Found documented artifacts:"
echo "$artifacts" | while IFS= read -r artifact; do
  echo "  - $artifact"
done
echo ""

missing=0
checked=0
while IFS= read -r artifact; do
  # Skip if empty line
  [ -z "$artifact" ] && continue

  checked=$((checked + 1))

  # Handle both absolute and relative paths
  if [[ "$artifact" = /* ]]; then
    # Absolute path
    full_path="$artifact"
  else
    # Relative path
    full_path="${PROJECT_ROOT}/${artifact}"
  fi

  if [ -f "$full_path" ] || [ -d "$full_path" ]; then
    echo "✅ Found: $artifact"
  else
    echo "❌ Missing: $artifact"
    missing=$((missing + 1))
  fi
done <<< "$artifacts"

echo ""
if [ $missing -gt 0 ]; then
  echo "❌ Validation failed: $missing/$checked artifacts missing"
  echo "   Fix: Create missing artifacts or update PROJECT_CONTEXT.md"
  exit 1
fi

echo "✅ All artifacts validated ($checked/$checked found)"
exit 0
