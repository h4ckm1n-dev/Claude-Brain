#!/bin/bash
# Validates CLAUDE.md structure and content
# Usage: ./claude-md-validator.sh

set -euo pipefail

CLAUDE_MD="${HOME}/.claude/CLAUDE.md"

if [ ! -f "$CLAUDE_MD" ]; then
  echo "❌ CLAUDE.md not found at: $CLAUDE_MD"
  exit 1
fi

echo "🔍 Validating CLAUDE.md..."
echo "   File: $CLAUDE_MD"
echo ""

# Check agent count
agent_count=$(grep -c "^| \*\*" "$CLAUDE_MD" 2>/dev/null || echo "0")
expected_agents=42

if [ "$agent_count" -ne "$expected_agents" ]; then
  echo "❌ Expected $expected_agents agents, found $agent_count"
else
  echo "✅ Agent count: $agent_count/$expected_agents"
fi

# Check required sections for LLM instructions
required_sections=(
  "# Claude Code Agent Ecosystem"
  "## Agent Invocation Rules"
  "## Keyword Triggers"
  "## All 42 Agents by Category"
  "## Multi-Agent Execution Modes"
  "## Agent Coordination Rules"
)

echo ""
echo "Checking required sections..."
missing=0
for section in "${required_sections[@]}"; do
  if grep -q "^$section" "$CLAUDE_MD"; then
    echo "✅ Found: $section"
  else
    echo "❌ Missing: $section"
    missing=$((missing + 1))
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Content Quality Checks..."
echo ""

# Check for human-facing content that shouldn't be there
warnings=0

if grep -q "I need to" "$CLAUDE_MD"; then
  echo "⚠️  Found human-facing phrase: 'I need to'"
  warnings=$((warnings + 1))
fi

if grep -q "Type what you need" "$CLAUDE_MD"; then
  echo "⚠️  Found human-facing phrase: 'Type what you need'"
  warnings=$((warnings + 1))
fi

if grep -q "First Time Using" "$CLAUDE_MD"; then
  echo "⚠️  Found tutorial-style section: 'First Time Using'"
  warnings=$((warnings + 1))
fi

# Check for external doc links (Claude doesn't need these in system prompt)
external_links=$(grep -c "docs/workflow-examples.md\|docs/troubleshooting-detailed.md" "$CLAUDE_MD" 2>/dev/null || echo "0")
if [ "$external_links" -gt 0 ]; then
  echo "⚠️  Found $external_links external documentation links"
  echo "   (Claude doesn't need to read these in system prompt)"
  warnings=$((warnings + 1))
fi

# Check for ASCII art (verbose for system prompt)
if grep -q "USER REQUEST RECEIVED" "$CLAUDE_MD" || grep -q "↓" "$CLAUDE_MD"; then
  echo "⚠️  Found ASCII art decision tree (verbose for LLM)"
  warnings=$((warnings + 1))
fi

if [ $warnings -eq 0 ]; then
  echo "✅ No human-facing content detected"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "File Size Analysis..."
echo ""

# Check line count
lines=$(wc -l < "$CLAUDE_MD")
size=$(wc -c < "$CLAUDE_MD")
size_kb=$(echo "scale=1; $size / 1024" | bc)

echo "📏 Line count: $lines"
echo "📦 File size: ${size_kb}KB"

if [ "$lines" -gt 850 ]; then
  echo "⚠️  Warning: CLAUDE.md is $lines lines (recommended: <850)"
  echo "   This is loaded as system prompt every conversation"
  echo "   Consider reducing verbose sections"
elif [ "$lines" -lt 200 ]; then
  echo "⚠️  Warning: CLAUDE.md is only $lines lines"
  echo "   Might be missing essential agent information"
else
  echo "✅ Line count within optimal range (200-850)"
fi

# Check version
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if grep -q "^\*\*Version\*\*:" "$CLAUDE_MD"; then
  version=$(grep "^\*\*Version\*\*:" "$CLAUDE_MD" | head -1)
  echo "📌 $version"
else
  echo "⚠️  No version information found"
fi

if grep -q "^\*\*Last Updated\*\*:" "$CLAUDE_MD"; then
  updated=$(grep "^\*\*Last Updated\*\*:" "$CLAUDE_MD" | head -1)
  echo "📅 $updated"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Final verdict
if [ $missing -eq 0 ] && [ "$agent_count" -eq "$expected_agents" ] && [ $warnings -eq 0 ]; then
  echo "✅ CLAUDE.md validation passed"
  echo "   Ready for use as LLM system prompt"
  exit 0
elif [ $missing -gt 0 ]; then
  echo "❌ CLAUDE.md validation failed"
  echo "   Missing $missing required sections"
  exit 1
else
  echo "⚠️  CLAUDE.md validation completed with warnings"
  echo "   Missing sections: $missing"
  echo "   Content warnings: $warnings"
  echo "   Review recommended"
  exit 0
fi
