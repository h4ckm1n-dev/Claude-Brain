#!/bin/bash
# Analyzes agent usage from PROJECT_CONTEXT.md
# Usage: ./agent-analytics.sh [project-root]

set -euo pipefail

PROJECT_ROOT="${1:-.}"
CONTEXT_FILE="$PROJECT_ROOT/PROJECT_CONTEXT.md"
CLAUDE_MD="${HOME}/.claude/CLAUDE.md"

echo "📊 Agent Usage Analytics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if PROJECT_CONTEXT.md exists
if [ ! -f "$CONTEXT_FILE" ]; then
  echo "ℹ️  PROJECT_CONTEXT.md not found at: $CONTEXT_FILE"
  echo "   No agent activity to analyze yet"
  echo ""
  echo "📋 Available Agents from CLAUDE.md:"

  if [ -f "$CLAUDE_MD" ]; then
    total_agents=$(grep -c "^| \*\*" "$CLAUDE_MD" 2>/dev/null || echo "0")
    echo "   Total: $total_agents agents available"
  fi

  exit 0
fi

echo "📁 Analyzing: $CONTEXT_FILE"
echo ""

# Count agent mentions in activity log
echo "🏆 Top 10 Most Used Agents:"
agent_usage=$(grep -E "^\*\*[0-9]{4}-[0-9]{2}-[0-9]{2}" "$CONTEXT_FILE" 2>/dev/null | \
  grep -oE "\`[a-z-]+\`" | \
  sed 's/`//g' | \
  sort | uniq -c | sort -rn | head -10)

if [ -z "$agent_usage" ]; then
  echo "   (No agent executions logged yet)"
else
  echo "$agent_usage" | awk '{printf "  %2d uses: %s\n", $1, $2}'
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 Agents by Category (from CLAUDE.md):"
echo ""

# Extract from CLAUDE.md if available
if [ -f "$CLAUDE_MD" ]; then
  categories=(
    "Full-Stack Development"
    "Language & Platform"
    "DevOps & Infrastructure"
    "Testing & Quality"
    "AI & Machine Learning"
    "Data & Analytics"
    "Performance & Security"
    "Design & UX"
    "Content & Marketing"
    "Code Management"
    "Business Intelligence"
    "Documentation & Support"
  )

  for category in "${categories[@]}"; do
    # Try to count agents in each category
    count=$(sed -n "/### $category/,/^### /p" "$CLAUDE_MD" 2>/dev/null | grep -c "^| \*\*" || echo "0")
    if [ "$count" -gt 0 ]; then
      printf "  %-30s %d agents\n" "$category:" "$count"
    fi
  done

  total=$(grep -c "^| \*\*" "$CLAUDE_MD" 2>/dev/null || echo "0")
  echo ""
  echo "  Total Available: $total agents"
else
  echo "  (CLAUDE.md not found)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📅 Recent Activity:"
echo ""

# Count recent activity (last 7 days)
seven_days_ago=$(date -v-7d +%Y-%m-%d 2>/dev/null || date -d "7 days ago" +%Y-%m-%d 2>/dev/null || echo "unknown")

if [ "$seven_days_ago" != "unknown" ]; then
  recent=$(grep -c "$seven_days_ago\|$(date -v-6d +%Y-%m-%d 2>/dev/null || echo '')\|$(date -v-5d +%Y-%m-%d 2>/dev/null || echo '')\|$(date -v-4d +%Y-%m-%d 2>/dev/null || echo '')\|$(date -v-3d +%Y-%m-%d 2>/dev/null || echo '')\|$(date -v-2d +%Y-%m-%d 2>/dev/null || echo '')\|$(date -v-1d +%Y-%m-%d 2>/dev/null || echo '')\|$(date +%Y-%m-%d)" "$CONTEXT_FILE" 2>/dev/null || echo "0")
  echo "  Last 7 days: $recent agent executions"
else
  # Fallback: just count entries from this month
  current_month=$(date +%Y-%m)
  recent=$(grep -c "$current_month" "$CONTEXT_FILE" 2>/dev/null || echo "0")
  echo "  This month: $recent agent executions"
fi

# Count total executions
total_executions=$(grep -c "^\*\*[0-9]{4}-[0-9]{2}-[0-9]{2}" "$CONTEXT_FILE" 2>/dev/null || echo "0")
echo "  All time: $total_executions agent executions"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Success Metrics:"
echo ""

# Count completed vs in-progress
completed=$(grep -c "Status.*COMPLETE" "$CONTEXT_FILE" 2>/dev/null || echo "0")
in_progress=$(grep -c "Status.*In Progress" "$CONTEXT_FILE" 2>/dev/null || echo "0")
blockers=$(grep -c "BLOCKER-.*OPEN" "$CONTEXT_FILE" 2>/dev/null || echo "0")

echo "  Completed tasks: $completed"
echo "  In progress: $in_progress"
echo "  Active blockers: $blockers"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Analytics complete"
