#!/usr/bin/env bash
# Pre-task validation: Run before any agent execution
# Calls existing validation scripts + adds size checks
# Usage: ./pre-task-validation.sh

set -euo pipefail

echo "🔍 Running Pre-Task Validation..."
echo ""

validation_passed=true

# 1. Check tools (existing script)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1/5: Tool Availability Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f ~/.claude/scripts/check-tools.sh ]; then
  if ~/.claude/scripts/check-tools.sh; then
    echo ""
  else
    echo "⚠️  Tool check completed with warnings (non-blocking)"
    echo ""
  fi
else
  echo "⚠️  check-tools.sh not found, skipping"
  echo ""
fi

# 2. Validate coordination (existing script)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2/5: Coordination Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f ~/.claude/scripts/validate-coordination.sh ]; then
  if ~/.claude/scripts/validate-coordination.sh; then
    echo ""
  else
    echo "❌ Coordination check failed"
    validation_passed=false
    echo ""
  fi
else
  echo "⚠️  validate-coordination.sh not found, skipping"
  echo ""
fi

# 3. Validate artifacts (existing script)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3/5: Artifact Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f ~/.claude/scripts/validate-artifacts.sh ]; then
  if ~/.claude/scripts/validate-artifacts.sh; then
    echo ""
  else
    echo "❌ Artifact check failed"
    validation_passed=false
    echo ""
  fi
else
  echo "⚠️  validate-artifacts.sh not found, skipping"
  echo ""
fi

# 4. NEW: Check PROJECT_CONTEXT.md size
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4/5: PROJECT_CONTEXT.md Size Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f PROJECT_CONTEXT.md ]; then
  LINE_COUNT=$(wc -l < PROJECT_CONTEXT.md)
  if [ "$LINE_COUNT" -gt 1000 ]; then
    echo "⚠️  PROJECT_CONTEXT.md has ${LINE_COUNT} lines (threshold: 1000)"
    echo "   Recommendation: Run ~/.claude/scripts/archive-context.sh"
    echo "   Continuing anyway (non-blocking warning)..."
  else
    echo "✅ PROJECT_CONTEXT.md size OK (${LINE_COUNT} lines)"
  fi
else
  echo "ℹ️  PROJECT_CONTEXT.md not found (will be created)"
fi
echo ""

# 5. NEW: Verify required sections in PROJECT_CONTEXT.md
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5/5: Required Sections Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f PROJECT_CONTEXT.md ]; then
  required=("## Agent Activity Log" "## Artifacts for Other Agents" "## Active Blockers")
  missing=0
  for section in "${required[@]}"; do
    if ! grep -q "$section" PROJECT_CONTEXT.md; then
      echo "⚠️  Missing section: $section"
      missing=$((missing + 1))
    else
      echo "✅ Section found: $section"
    fi
  done
  if [ $missing -gt 0 ]; then
    echo ""
    echo "❌ PROJECT_CONTEXT.md missing $missing required sections"
    echo "   Fix: Update from template ~/.claude/PROJECT_CONTEXT_TEMPLATE.md"
    validation_passed=false
  fi
else
  echo "ℹ️  PROJECT_CONTEXT.md not found - sections check skipped"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$validation_passed" = true ]; then
  echo "✅ Pre-task validation PASSED"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 0
else
  echo "❌ Pre-task validation FAILED"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "Fix the issues above before proceeding."
  exit 1
fi
