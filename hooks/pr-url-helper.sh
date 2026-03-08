#!/bin/bash
# PR URL Helper — PostToolUse (Bash) [async]
# Detects gh pr create output and suggests useful follow-up commands

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
OUTPUT=$(echo "$INPUT" | jq -r '.stdout // .output // ""')

# Only trigger on gh pr commands
if ! echo "$COMMAND" | grep -qE '\bgh\s+pr\s+create\b'; then
    exit 0
fi

# Extract PR URL from output
PR_URL=$(echo "$OUTPUT" | grep -oE 'https://github\.com/[^/]+/[^/]+/pull/[0-9]+' | head -1)

if [ -z "$PR_URL" ]; then
    exit 0
fi

# Extract PR number
PR_NUM=$(echo "$PR_URL" | grep -oE '[0-9]+$')

cat <<EOF
PR created: $PR_URL

Useful follow-up commands:
  gh pr view $PR_NUM              # View PR details
  gh pr checks $PR_NUM            # Check CI status
  gh pr diff $PR_NUM              # View PR diff
  gh pr merge $PR_NUM             # Merge when ready
EOF

exit 0
