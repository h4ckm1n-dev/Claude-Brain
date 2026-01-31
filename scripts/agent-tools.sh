#!/usr/bin/env bash
# Agent Tool Lookup Helper
# Usage: agent-tools.sh <agent-name>

agent="$1"

if [ -z "$agent" ]; then
  echo "Usage: agent-tools.sh <agent-name>"
  echo ""
  echo "Examples:"
  echo "  agent-tools.sh backend-architect"
  echo "  agent-tools.sh test-engineer"
  echo "  agent-tools.sh security-practice-reviewer"
  exit 1
fi

agent_file="$HOME/.claude/agents/${agent}.md"

if [ ! -f "$agent_file" ]; then
  echo "❌ Agent not found: $agent"
  echo ""
  echo "Available agents:"
  ls -1 "$HOME/.claude/agents/" | sed 's/.md$//' | head -10
  echo "... and more"
  exit 1
fi

echo "🔧 Tools available for: $agent"
echo ""
grep -A 100 "## Available Custom Tools" "$agent_file" | \
  grep "~/.claude/tools/" | \
  sed 's/.*`\(~[^`]*\)`.*/\1/' | \
  sed 's/ <.*//' | \
  sort -u | \
  nl

echo ""
echo "Usage: Run tool with bash or python3"
echo "Example: python3 ~/.claude/tools/security/secret-scanner.py ."
