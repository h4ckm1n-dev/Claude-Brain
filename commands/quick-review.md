---
description: "Lightweight code review of uncommitted changes"
---

# Quick Review

Run a quick code review on the current uncommitted changes. Focus on:

1. Run `git diff` to see all unstaged changes, and `git diff --cached` for staged changes
2. Analyze the diff for:
   - Bugs or logic errors
   - Security vulnerabilities (injection, XSS, hardcoded secrets, etc.)
   - Style issues or inconsistencies with surrounding code
   - Missing error handling at system boundaries
   - Accidental debug code (console.log, print statements, TODO/FIXME)
3. Report findings grouped by severity: critical, warning, suggestion
4. If no issues found, confirm the changes look clean

Keep the review concise. Only flag real issues, not style preferences.
