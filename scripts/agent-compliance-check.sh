#!/usr/bin/env bash
# Checks all 42 agent files for structural compliance
# Usage: ./agent-compliance-check.sh
# Exit codes: 0=all compliant or warnings only, 1=non-compliant agents found

set -euo pipefail

AGENTS_DIR="${HOME}/.claude/agents"
echo "🔍 Checking Agent Compliance..."
echo "====================================="
echo ""

if [ ! -d "$AGENTS_DIR" ]; then
  echo "❌ Agents directory not found: $AGENTS_DIR"
  exit 1
fi

compliant=0
warnings=0
non_compliant=0
total=0

# Check each agent file
for agent_file in "$AGENTS_DIR"/*.md; do
  # Skip if no files found
  [ -e "$agent_file" ] || continue

  total=$((total + 1))
  agent_name=$(basename "$agent_file")
  issues=()

  # Check 1: YAML frontmatter
  if ! grep -q "^---$" "$agent_file"; then
    issues+=("missing YAML frontmatter")
  else
    # Check for required frontmatter fields
    if ! grep -q "^name:" "$agent_file"; then
      issues+=("missing 'name' field")
    fi
    if ! grep -q "^description:" "$agent_file"; then
      issues+=("missing 'description' field")
    fi
    if ! grep -q "^model:" "$agent_file"; then
      issues+=("missing 'model' field")
    fi
  fi

  # Check 2: Team Collaboration Protocol
  if ! grep -q "# TEAM COLLABORATION PROTOCOL" "$agent_file" && \
     ! grep -q "## Team Collaboration Protocol" "$agent_file"; then
    issues+=("missing Team Collaboration Protocol")
  fi

  # Check 3: Execution Protocol
  if ! grep -q "# EXECUTION PROTOCOL" "$agent_file" && \
     ! grep -q "## Execution Protocol" "$agent_file"; then
    issues+=("missing Execution Protocol")
  fi

  # Check 4: Error Recovery Protocol
  if ! grep -q "# ERROR RECOVERY PROTOCOL" "$agent_file" && \
     ! grep -q "## Error Recovery Protocol" "$agent_file"; then
    issues+=("missing Error Recovery Protocol")
  fi

  # Categorize result
  if [ ${#issues[@]} -eq 0 ]; then
    echo "✅ $agent_name (all sections present)"
    compliant=$((compliant + 1))
  elif [ ${#issues[@]} -eq 1 ]; then
    echo "⚠️  $agent_name (missing: ${issues[0]})"
    warnings=$((warnings + 1))
  else
    echo "❌ $agent_name (missing: ${issues[*]})"
    non_compliant=$((non_compliant + 1))
  fi
done

echo ""
echo "====================================="
echo "Summary:"
echo "====================================="
echo "Total agents checked: $total"
echo ""

if [ $total -eq 0 ]; then
  echo "⚠️  No agent files found in $AGENTS_DIR"
  exit 1
fi

compliance_pct=$((compliant * 100 / total))
echo "Compliant: $compliant/$total agents ($compliance_pct%)"
if [ $warnings -gt 0 ]; then
  echo "Warnings: $warnings agents (1 issue each)"
fi
if [ $non_compliant -gt 0 ]; then
  echo "Non-compliant: $non_compliant agents (2+ issues)"
fi
echo ""

if [ $non_compliant -gt 0 ]; then
  echo "❌ $non_compliant agents need attention"
  echo ""
  echo "Recommendation: Update non-compliant agents to match template structure."
  echo "Template: ~/.claude/agents/code-architect.md"
  echo ""
  echo "Required sections:"
  echo "  1. YAML frontmatter (---) with name, description, model fields"
  echo "  2. # TEAM COLLABORATION PROTOCOL"
  echo "  3. # EXECUTION PROTOCOL"
  echo "  4. # ERROR RECOVERY PROTOCOL"
  exit 1
elif [ $warnings -gt 0 ]; then
  echo "⚠️  $warnings agents have minor issues"
  echo ""
  echo "Recommendation: Fix warnings to reach 100% compliance."
  echo "Template: ~/.claude/agents/code-architect.md"
  exit 0
else
  echo "✅ All agents compliant!"
  exit 0
fi
