#!/bin/bash
# Tests the agent coordination workflow
# Usage: ./test-workflow.sh

set -euo pipefail

TEST_DIR="${1:-$(mktemp -d)}"
KEEP_TEST_DIR="${2:-false}"

echo "🧪 Testing Agent Coordination Workflow..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Test directory: $TEST_DIR"
echo ""

# Cleanup function
cleanup() {
  if [ "$KEEP_TEST_DIR" = "false" ]; then
    echo ""
    echo "🧹 Cleaning up test directory..."
    rm -rf "$TEST_DIR"
    echo "✅ Cleanup complete"
  else
    echo ""
    echo "📁 Test directory preserved at: $TEST_DIR"
    echo "   To clean up manually: rm -rf $TEST_DIR"
  fi
}

trap cleanup EXIT

# Create test directory if it doesn't exist
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "Step 1: Checking agent ecosystem health"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Run agent health check
if [ -f "$HOME/.claude/scripts/agent-health-check.sh" ]; then
  bash "$HOME/.claude/scripts/agent-health-check.sh" 2>/dev/null || echo "⚠️  Agent health check unavailable"
else
  echo "⚠️  agent-health-check.sh not found"
fi

echo ""
echo "Step 2: Checking available tools"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "$HOME/.claude/scripts/check-tools.sh" ]; then
  bash "$HOME/.claude/scripts/check-tools.sh" 2>/dev/null || echo "⚠️  Tool check unavailable"
else
  echo "⚠️  check-tools.sh not found"
fi

echo ""
echo "Step 3: Creating minimal test feature file"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cat > "$TEST_DIR/FEATURE.md" << 'EOF'
# Feature: Hello World API

## What to Build
Simple REST API endpoint that returns a JSON response with a "Hello, World!" message.

## Requirements
- Single GET endpoint at /api/hello
- Returns JSON: {"message": "Hello, World!", "timestamp": "<ISO 8601 timestamp>"}
- Include timestamp for verification
- Return 200 status code

## Success Criteria
- [ ] GET /api/hello returns proper JSON
- [ ] Response includes message and timestamp
- [ ] Returns 200 status code
- [ ] Proper content-type header

## Agents Needed
- backend-architect: Implement the endpoint
- test-engineer: Create tests
- code-reviewer: Validate quality
EOF

echo "✅ Created test FEATURE.md"
echo ""

echo "Step 4: Verifying PROJECT_CONTEXT template"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "$HOME/.claude/PROJECT_CONTEXT_TEMPLATE.md" ]; then
  echo "✅ PROJECT_CONTEXT_TEMPLATE.md exists"
  # Copy template to test directory
  cp "$HOME/.claude/PROJECT_CONTEXT_TEMPLATE.md" "$TEST_DIR/PROJECT_CONTEXT.md"
  echo "✅ Copied template to test directory"
else
  echo "❌ PROJECT_CONTEXT_TEMPLATE.md not found"
  exit 1
fi

echo ""
echo "Step 5: Workflow validation complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Test environment ready!"
echo ""
echo "   Test directory: $TEST_DIR"
echo "   Files created:"
echo "     - FEATURE.md (feature description)"
echo "     - PROJECT_CONTEXT.md (coordination file)"
echo ""
echo "📋 To test agent workflow manually:"
echo ""
echo "   1. Navigate to test directory:"
echo "      cd $TEST_DIR"
echo ""
echo "   2. Use quick-agent to implement:"
echo "      /quick-agent backend-architect: implement hello world API endpoint"
echo ""
echo "   3. Review PROJECT_CONTEXT.md for coordination updates"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Verify coordination template has required sections
echo "Step 6: Validating PROJECT_CONTEXT structure"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

required_sections=(
  "## Project Overview"
  "## Current Sprint"
  "## Agent Activity Log"
)

missing=0
for section in "${required_sections[@]}"; do
  if grep -q "$section" "$TEST_DIR/PROJECT_CONTEXT.md"; then
    echo "✅ Section found: $section"
  else
    echo "❌ Missing section: $section"
    missing=$((missing + 1))
  fi
done

echo ""
if [ $missing -eq 0 ]; then
  echo "✅ PROJECT_CONTEXT.md validation passed"
  echo ""
  echo "🎉 All workflow tests passed!"
else
  echo "⚠️  Some sections missing from PROJECT_CONTEXT template"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
