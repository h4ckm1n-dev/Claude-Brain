#!/bin/bash
# Plan Mode Reminder Hook
# Analyzes user prompts and generates strong planning reminders for complex tasks
# Output appears in <system-reminder> tags for Claude to see

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // ""')
REMINDER_FILE="/tmp/claude/plan-mode-reminder.txt"

# Create temp directory
mkdir -p /tmp/claude

# Clear previous reminder
> "$REMINDER_FILE"

# Exit if no prompt
if [ -z "$PROMPT" ]; then
    exit 0
fi

# Convert to lowercase for matching
PROMPT_LOWER=$(echo "$PROMPT" | tr '[:upper:]' '[:lower:]')

# High complexity indicators
HIGH_COMPLEXITY_PATTERNS=(
    "architect"
    "design"
    "structure"
    "refactor"
    "migrate"
    "new feature"
    "add feature"
    "implement feature"
    "authentication"
    "authorization"
    "oauth"
    "database schema"
    "migration"
    "api.*create"
    "api.*design"
    "api.*add"
    "endpoint.*create"
    "endpoint.*design"
    "complex"
    "complicated"
    "system-wide"
    "project-wide"
    "breaking change"
    "major change"
)

# Medium complexity indicators
MEDIUM_COMPLEXITY_PATTERNS=(
    "update.*and"
    "modify.*and"
    "multiple.*files"
    "multiple.*components"
    "across.*files"
    "integrate"
    "integration"
    "how should"
    "how could"
    "what.*best"
    "options for"
    "investigate"
    "explore"
    "not sure"
    "unclear"
    "unsure"
)

# Simple task indicators (skip planning)
SIMPLE_PATTERNS=(
    "fix typo"
    "typo in"
    "spelling"
    "update comment"
    "update documentation"
    "update readme"
    "add comment"
    "add log"
    "remove comment"
    "rename file"
    "delete file"
    "small fix"
    "quick fix"
)

# Check for simple indicators first
IS_SIMPLE=false
for pattern in "${SIMPLE_PATTERNS[@]}"; do
    if echo "$PROMPT_LOWER" | grep -qi "$pattern"; then
        IS_SIMPLE=true
        break
    fi
done

if [ "$IS_SIMPLE" = true ]; then
    exit 0  # Don't suggest planning for simple tasks
fi

# Check complexity
HIGH_MATCHES=0
MEDIUM_MATCHES=0

for pattern in "${HIGH_COMPLEXITY_PATTERNS[@]}"; do
    if echo "$PROMPT_LOWER" | grep -qi "$pattern"; then
        ((HIGH_MATCHES++))
    fi
done

for pattern in "${MEDIUM_COMPLEXITY_PATTERNS[@]}"; do
    if echo "$PROMPT_LOWER" | grep -qi "$pattern"; then
        ((MEDIUM_MATCHES++))
    fi
done

# Generate reminder based on complexity
if [ $HIGH_MATCHES -ge 2 ] || [ $HIGH_MATCHES -eq 1 ]; then
    # HIGH COMPLEXITY - Strong mandate
    cat > "$REMINDER_FILE" << 'EOF'
╔═══════════════════════════════════════════════════════════════╗
║  🎯 PLANNING REQUIRED: HIGH COMPLEXITY DETECTED               ║
╚═══════════════════════════════════════════════════════════════╝

This task has HIGH COMPLEXITY indicators.

⚠️  MANDATORY ACTION REQUIRED ⚠️

You MUST use EnterPlanMode() BEFORE starting work on this task.

WHY PLANNING IS CRITICAL:
  ✅ 76% token reduction (research-proven)
  ✅ Prevents costly mistakes from premature execution
  ✅ Gets user approval before major changes
  ✅ Ensures systematic, well-thought-out approach

REQUIRED WORKFLOW:
  1. search_memory(query="[keywords]", limit=10)  ← FIRST
  2. get_context(project="...", hours=24)         ← SECOND
  3. EnterPlanMode()                               ← THIRD - START PLANNING
  4. [Research: Read files, analyze codebase]
  5. [Create plan: Analysis → Options → Recommendation → Steps]
  6. ExitPlanMode()                                ← Get user approval
  7. [Delegate to specialized agents if needed]
  8. store_memory(...)                             ← Save results

⛔ DO NOT START READING FILES OR CODING WITHOUT PLANNING ⛔

Reference: ~/.claude/PLANNING_WORKFLOW_GUIDE.md
Research: Planning reduces token usage by 76% (2026 Opus 4.5 study)

──────────────────────────────────────────────────────────────
EOF

elif [ $MEDIUM_MATCHES -ge 2 ] || [ $MEDIUM_MATCHES -eq 1 ]; then
    # MEDIUM COMPLEXITY - Strong suggestion
    cat > "$REMINDER_FILE" << 'EOF'
╭───────────────────────────────────────────────────────────────╮
│  💡 PLANNING STRONGLY RECOMMENDED                             │
╰───────────────────────────────────────────────────────────────╯

This task shows MEDIUM-HIGH COMPLEXITY indicators.

📋 RECOMMENDED ACTION: Use EnterPlanMode()

Benefits of planning for this task:
  • 76% reduction in token usage
  • User approval before changes
  • Systematic approach with clear steps
  • Better architecture from deliberation

SUGGESTED WORKFLOW:
  1. search_memory() + get_context()  ← Check for past solutions
  2. EnterPlanMode()                   ← Plan the approach
  3. [Create structured plan]
  4. ExitPlanMode()                    ← Get approval
  5. [Execute systematically]
  6. store_memory()                    ← Save for future

Quick decision guide:
  ✅ USE PLAN MODE IF:
     - Affects 3+ files
     - Architecture decision needed
     - Uncertain about approach
     - Want user approval first

  ⏭️  WORK DIRECTLY IF:
     - Clear solution from memory search
     - Single file, simple change
     - Just applying known pattern

Reference: ~/.claude/PLANNING_WORKFLOW_GUIDE.md

──────────────────────────────────────────────────────────────
EOF
fi

# If reminder was generated, output it to Claude via stdout
if [ -s "$REMINDER_FILE" ]; then
    cat "$REMINDER_FILE"

    # Log to audit
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Plan mode reminder generated (HIGH: $HIGH_MATCHES, MEDIUM: $MEDIUM_MATCHES)" >> ~/.claude/logs/plan-mode-suggestions.log
fi

exit 0
