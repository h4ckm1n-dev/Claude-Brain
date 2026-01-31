#!/usr/bin/env python3
"""
Auto-Suggest Plan Mode Hook
Analyzes user requests and strongly suggests EnterPlanMode for complex tasks
Runs on UserPromptSubmit hook to influence Claude before it starts working
"""

import sys
import json
import re

# Complexity indicators - tasks that should use plan mode
COMPLEXITY_INDICATORS = {
    # Architecture & Design
    "high": [
        r'\b(architect|design|structure|refactor|migrate|redesign)\b',
        r'\b(new feature|add feature|implement feature)\b',
        r'\b(authentication|authorization|oauth|security)\b',
        r'\b(database schema|migration|model)\b',
        r'\b(api|endpoint|route)\s+(design|create|add|new)',
        r'\b(complex|complicated|sophisticated)\b',
    ],

    # Multi-file/module work
    "medium": [
        r'\bupdate.*and.*\b',  # "update X and Y"
        r'\bmodify.*and.*\b',  # "modify X and Y"
        r'\bmultiple\s+(files|components|modules)\b',
        r'\bacross\s+(files|components|modules)\b',
        r'\b(frontend|backend).*and.*(frontend|backend)\b',
        r'\b(integrate|integration)\b',
    ],

    # Uncertainty/exploration
    "medium": [
        r'\bhow (should|could|can) (i|we)\b',
        r'\bwhat.*best (way|approach|practice)\b',
        r'\boptions? (for|to)\b',
        r'\b(investigate|explore|research)\b',
        r'\b(not sure|unclear|unsure)\b',
    ],

    # Scale indicators
    "high": [
        r'\b(all|every|entire)\s+(file|component|module)\b',
        r'\b(system-wide|project-wide|codebase)\b',
        r'\b(breaking change|major change)\b',
    ]
}

# Simple task indicators - probably don't need plan mode
SIMPLE_INDICATORS = [
    r'\b(fix typo|typo in|spelling)\b',
    r'\bupdate (comment|documentation|readme)\b',
    r'\badd (comment|log|print)\b',
    r'\bremove (comment|log|print)\b',
    r'\b(rename|delete) (file|variable)\b',
    r'\bsmall (fix|change|tweak)\b',
    r'\bquick (fix|change)\b',
]

def analyze_complexity(prompt: str) -> dict:
    """
    Analyze prompt complexity and return recommendation.

    Returns:
        {
            "complexity": "high" | "medium" | "low",
            "confidence": 0.0-1.0,
            "indicators": [list of matched patterns],
            "should_plan": bool
        }
    """
    prompt_lower = prompt.lower()

    # Check for simple indicators first
    simple_matches = []
    for pattern in SIMPLE_INDICATORS:
        if re.search(pattern, prompt_lower):
            simple_matches.append(pattern)

    if simple_matches:
        return {
            "complexity": "low",
            "confidence": 0.9,
            "indicators": simple_matches,
            "should_plan": False
        }

    # Check complexity indicators
    high_matches = []
    medium_matches = []

    for pattern in COMPLEXITY_INDICATORS.get("high", []):
        if re.search(pattern, prompt_lower):
            high_matches.append(pattern)

    for pattern in COMPLEXITY_INDICATORS.get("medium", []):
        if re.search(pattern, prompt_lower):
            medium_matches.append(pattern)

    # Determine complexity
    if len(high_matches) >= 2:
        return {
            "complexity": "high",
            "confidence": 0.95,
            "indicators": high_matches,
            "should_plan": True
        }
    elif len(high_matches) >= 1:
        return {
            "complexity": "high",
            "confidence": 0.85,
            "indicators": high_matches,
            "should_plan": True
        }
    elif len(medium_matches) >= 2:
        return {
            "complexity": "medium",
            "confidence": 0.75,
            "indicators": medium_matches,
            "should_plan": True
        }
    elif len(medium_matches) >= 1:
        return {
            "complexity": "medium",
            "confidence": 0.6,
            "indicators": medium_matches,
            "should_plan": True
        }
    else:
        return {
            "complexity": "low",
            "confidence": 0.7,
            "indicators": [],
            "should_plan": False
        }

def generate_plan_suggestion(analysis: dict, prompt: str) -> str:
    """Generate a strong suggestion to use plan mode."""

    if not analysis["should_plan"]:
        return ""

    complexity = analysis["complexity"]
    confidence = analysis["confidence"]

    if complexity == "high" and confidence >= 0.85:
        return f"""
╔═══════════════════════════════════════════════════════════════╗
║  🎯 PLANNING RECOMMENDATION: MANDATORY                        ║
╚═══════════════════════════════════════════════════════════════╝

This task shows HIGH COMPLEXITY indicators (confidence: {confidence:.0%}):
  → Architecture/design work detected
  → Multiple components/files likely affected
  → Significant impact on codebase

📋 REQUIRED ACTION: Use EnterPlanMode() BEFORE starting work

WHY THIS MATTERS:
  ✅ Planning reduces token usage by 76%
  ✅ Prevents costly mistakes from premature execution
  ✅ Gets user approval before major changes
  ✅ Ensures systematic, well-thought-out approach

WORKFLOW:
  1. search_memory(query="[keywords]", limit=10)  ← Find past solutions
  2. get_context(project="...", hours=24)         ← Get recent context
  3. EnterPlanMode()                               ← START PLANNING
  4. [Research phase: Read files, analyze codebase]
  5. [Create comprehensive plan]
  6. ExitPlanMode()                                ← Get approval
  7. [Delegate to specialized agents]
  8. store_memory(...)                             ← Save results

⚠️  DO NOT START CODING WITHOUT A PLAN FOR THIS TASK ⚠️

Reference: ~/.claude/PLANNING_WORKFLOW_GUIDE.md
"""

    elif complexity == "medium" or (complexity == "high" and confidence < 0.85):
        return f"""
╭───────────────────────────────────────────────────────────────╮
│  💡 PLANNING RECOMMENDED                                      │
╰───────────────────────────────────────────────────────────────╯

This task shows MEDIUM-HIGH COMPLEXITY (confidence: {confidence:.0%}):
  → Multiple components or uncertainty detected
  → Planning would likely improve results

📋 SUGGESTED ACTION: Consider EnterPlanMode()

Benefits:
  • 76% token reduction vs direct coding
  • User approval before changes
  • Systematic approach with clear steps

Quick decision:
  ✅ Use plan mode IF: 3+ files, architecture decision, or uncertain approach
  ⏭️  Work directly IF: Clear solution already known from memory

Reference: ~/.claude/PLANNING_WORKFLOW_GUIDE.md
"""

    return ""

def main():
    """Main hook execution."""
    try:
        # Read hook input from stdin
        hook_input = json.load(sys.stdin)

        # Extract user prompt
        user_prompt = hook_input.get("userPrompt", "")

        if not user_prompt:
            # No prompt to analyze, pass through
            json.dump(hook_input, sys.stdout, indent=2)
            return

        # Analyze complexity
        analysis = analyze_complexity(user_prompt)

        # Generate suggestion if needed
        suggestion = generate_plan_suggestion(analysis, user_prompt)

        if suggestion:
            # Inject suggestion into context
            # This will appear as additional context for Claude
            hook_input["additionalContext"] = suggestion

            # Log to stderr for debugging (won't appear to user)
            print(f"[auto-suggest-planmode] Complexity: {analysis['complexity']}, Confidence: {analysis['confidence']:.0%}, Should plan: {analysis['should_plan']}", file=sys.stderr)

        # Output modified hook input
        json.dump(hook_input, sys.stdout, indent=2)

    except Exception as e:
        # On error, pass through original input
        print(f"[auto-suggest-planmode] Error: {e}", file=sys.stderr)
        try:
            hook_input = json.load(sys.stdin)
            json.dump(hook_input, sys.stdout, indent=2)
        except:
            json.dump({}, sys.stdout)

if __name__ == "__main__":
    main()
