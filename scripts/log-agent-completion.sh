#!/usr/bin/env bash
# Helper for consistent agent logging
# Usage: ./log-agent-completion.sh <agent-name> "<tasks-completed>" "<files-modified>" "<artifacts-created>"

set -euo pipefail

AGENT_NAME="${1:-}"
TASKS="${2:-}"
FILES="${3:-}"
ARTIFACTS="${4:-}"

if [ -z "$AGENT_NAME" ] || [ -z "$TASKS" ] || [ -z "$FILES" ]; then
  echo "Usage: $0 <agent-name> \"<tasks>\" \"<files>\" [\"<artifacts>\"]"
  echo ""
  echo "Example:"
  echo "  $0 backend-architect \"Implemented API endpoints\" \"src/api.py, src/routes.py\" \"docs/api/spec.yaml\""
  exit 2
fi

CONTEXT_FILE="${PROJECT_ROOT:-.}/PROJECT_CONTEXT.md"

if [ ! -f "$CONTEXT_FILE" ]; then
  echo "❌ PROJECT_CONTEXT.md not found at: $CONTEXT_FILE"
  echo "   Set PROJECT_ROOT environment variable or run from project directory"
  exit 1
fi

# Validate agent name format (lowercase with hyphens)
if ! [[ "$AGENT_NAME" =~ ^[a-z]+(-[a-z]+)*$ ]]; then
  echo "⚠️  Warning: Agent name should be lowercase with hyphens (e.g., 'backend-architect')"
fi

# Format entry with consistent timestamp
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M")

# Append to PROJECT_CONTEXT.md
cat >> "$CONTEXT_FILE" <<EOF

**$TIMESTAMP** - \`$AGENT_NAME\`
- **Completed**: $TASKS
- **Files Modified**: $FILES
${ARTIFACTS:+- **Artifacts Created**: $ARTIFACTS}
EOF

echo "✅ Logged completion for: $AGENT_NAME"
echo "   Timestamp: $TIMESTAMP"
echo "   Location: $CONTEXT_FILE"
exit 0
