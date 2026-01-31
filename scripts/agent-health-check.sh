#!/bin/bash
# Validates all agents are properly defined and accessible
# Usage: ./agent-health-check.sh

set -euo pipefail

AGENTS_DIR="${HOME}/.claude/agents"
CLAUDE_MD="${HOME}/.claude/CLAUDE.md"

echo "🔍 Checking Agent Health..."
echo ""

# Check if agents directory exists
if [ ! -d "$AGENTS_DIR" ]; then
  echo "❌ Agents directory not found: $AGENTS_DIR"
  echo "   Expected location: ~/.claude/agents/"
  exit 1
fi

# Expected agent count from CLAUDE.md
expected_count=42
if [ -f "$CLAUDE_MD" ]; then
  claude_agent_count=$(grep -c "^| \*\*" "$CLAUDE_MD" 2>/dev/null || echo "0")
  echo "📋 CLAUDE.md reports: $claude_agent_count agents"
else
  claude_agent_count=0
  echo "⚠️  CLAUDE.md not found at $CLAUDE_MD"
fi

# Count actual agent definition files
actual_count=$(find "$AGENTS_DIR" -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
echo "📁 Agent files found: $actual_count"

if [ "$actual_count" -ne "$expected_count" ]; then
  echo "⚠️  Expected $expected_count agents, found $actual_count files"
else
  echo "✅ Agent count matches expected: $actual_count/$expected_count"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Validating agent definition files..."
echo ""

# Check each agent file has required fields
agents_checked=0
agents_valid=0
agents_invalid=()

for agent_file in "$AGENTS_DIR"/*.md; do
  [ -e "$agent_file" ] || continue  # Skip if no .md files

  agents_checked=$((agents_checked + 1))
  agent_name=$(basename "$agent_file" .md)

  # Check for required frontmatter (YAML between --- markers)
  has_name=false
  has_description=false
  has_tools=false

  if grep -q "^name:" "$agent_file" 2>/dev/null; then
    has_name=true
  fi

  if grep -q "^description:" "$agent_file" 2>/dev/null; then
    has_description=true
  fi

  if grep -q "^tools:" "$agent_file" 2>/dev/null; then
    has_tools=true
  fi

  if $has_name && $has_description && $has_tools; then
    agents_valid=$((agents_valid + 1))
    echo "✅ Valid: $agent_name"
  else
    agents_invalid+=("$agent_name")
    echo "❌ Invalid: $agent_name"
    [ "$has_name" = false ] && echo "   - Missing: name"
    [ "$has_description" = false ] && echo "   - Missing: description"
    [ "$has_tools" = false ] && echo "   - Missing: tools"
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Summary:"
echo "  Total agents checked: $agents_checked"
echo "  Valid agents: $agents_valid"
echo "  Invalid agents: ${#agents_invalid[@]}"

if [ ${#agents_invalid[@]} -gt 0 ]; then
  echo ""
  echo "Invalid agent files:"
  for invalid_agent in "${agents_invalid[@]}"; do
    echo "  - $invalid_agent.md"
  done
fi

echo ""

# Cross-reference with CLAUDE.md
if [ -f "$CLAUDE_MD" ] && [ "$claude_agent_count" -ne "$actual_count" ]; then
  echo "⚠️  Mismatch: CLAUDE.md shows $claude_agent_count agents, but $actual_count definition files exist"
  echo "   Run: ~/.claude/scripts/claude-md-validator.sh for details"
fi

echo ""

if [ $agents_valid -eq $actual_count ] && [ $actual_count -eq $expected_count ]; then
  echo "✅ Agent health check passed"
  echo "   All $expected_count agents properly defined"
  exit 0
else
  echo "⚠️  Agent health check completed with warnings"
  echo "   Review issues above"
  exit 0
fi
