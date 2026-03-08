#!/bin/bash
# Debug Statement Checker
# Triggers: Stop
# Purpose: Check modified files for leftover debug statements before session ends

# Get modified files from git (staged + unstaged)
MODIFIED=$(git diff --name-only HEAD 2>/dev/null; git diff --name-only 2>/dev/null)
MODIFIED=$(echo "$MODIFIED" | sort -u)

if [ -z "$MODIFIED" ]; then
    exit 0
fi

WARNINGS=""

while IFS= read -r file; do
    [ -f "$file" ] || continue

    case "$file" in
        # Skip test files, configs, scripts, fixtures
        *test*|*spec*|*__mocks__*|*.config.*|*scripts/*|*.json|*.yaml|*.yml|*.toml|*fixture*)
            continue
            ;;
        # Check JS/TS for console.log
        *.js|*.ts|*.jsx|*.tsx|*.mjs|*.cjs)
            HITS=$(grep -cn 'console\.log\b' "$file" 2>/dev/null)
            if [ "$HITS" -gt 0 ] 2>/dev/null; then
                WARNINGS="${WARNINGS}\n  ${file}: ${HITS} console.log statement(s)"
            fi
            ;;
        # Check Python for breakpoint/pdb
        *.py)
            HITS=$(grep -cn 'breakpoint()\|pdb\.set_trace()\|import pdb' "$file" 2>/dev/null)
            if [ "$HITS" -gt 0 ] 2>/dev/null; then
                WARNINGS="${WARNINGS}\n  ${file}: debugger statement(s)"
            fi
            ;;
        # Check Rust for dbg!
        *.rs)
            HITS=$(grep -cn 'dbg!' "$file" 2>/dev/null)
            if [ "$HITS" -gt 0 ] 2>/dev/null; then
                WARNINGS="${WARNINGS}\n  ${file}: ${HITS} dbg! macro(s)"
            fi
            ;;
    esac
done <<< "$MODIFIED"

if [ -n "$WARNINGS" ]; then
    echo -e "Debug statements found in modified files:${WARNINGS}"
    echo "Consider removing these before committing."
fi

exit 0
