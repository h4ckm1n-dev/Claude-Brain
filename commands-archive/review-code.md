# Quick Code Review

Fast code review without full PR workflow

**Usage:** `/review-code [file-path or "git"]`

**Input:** $ARGUMENTS

---

## Instructions

Perform a focused code review on specific files or git changes using the code-reviewer agent.

### 1. Determine Review Scope

Parse $ARGUMENTS:
- **Empty or "git"** → Review uncommitted git changes
- **File path** → Review specific file
- **Directory path** → Review all files in directory
- **"staged"** → Review only staged changes
- **"last-commit"** → Review last commit

### 2. Gather Code to Review

**For git changes (default):**
```bash
# Get uncommitted changes
git diff 2>/dev/null

# If no unstaged changes, check staged
if [ -z "$(git diff)" ]; then
  git diff --cached 2>/dev/null
fi

# If still empty
if [ -z "$(git diff)" ] && [ -z "$(git diff --cached)" ]; then
  echo "ℹ️  No uncommitted changes found"
  echo ""
  echo "Options:"
  echo "  • Review specific file: /review-code path/to/file.py"
  echo "  • Review last commit: /review-code last-commit"
  echo "  • Review directory: /review-code src/api/"
  exit 0
fi
```

**For specific file:**
```bash
# Read the file
Read: $ARGUMENTS
```

**For staged changes:**
```bash
git diff --cached 2>/dev/null
```

**For last commit:**
```bash
git diff HEAD~1 HEAD 2>/dev/null
```

**For directory:**
```bash
# Find all relevant code files
find $ARGUMENTS -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.tsx" -o -name "*.go" -o -name "*.rs" -o -name "*.java" \) 2>/dev/null
```

### 3. Launch code-reviewer Agent

Use Task tool to launch code-reviewer:

```yaml
subagent_type: code-reviewer
description: Review code changes
prompt: |
  Perform a focused code review on the following changes.

  **REVIEW SCOPE**: [git changes / specific file / directory]

  **CODE TO REVIEW**:
  [Include file content or git diff output]

  **REVIEW CRITERIA**:
  1. **Code Quality**
     - Readability and clarity
     - Naming conventions
     - Code organization
     - DRY principle adherence

  2. **Security**
     - Input validation
     - SQL injection risks
     - XSS vulnerabilities
     - Authentication/authorization issues
     - Sensitive data exposure

  3. **Best Practices**
     - Error handling
     - Logging appropriateness
     - Resource management
     - Performance considerations

  4. **Maintainability**
     - Documentation/comments
     - Code complexity
     - Test coverage
     - Technical debt

  5. **Standards Compliance**
     - Project conventions
     - Style guide adherence
     - Linting rules

  **OUTPUT FORMAT**:
  Provide review in this structure:

  ## Overview
  [Brief summary of changes]

  ## Critical Issues (❌)
  [Issues that must be fixed before merging]
  - [Issue with file:line reference]
  - [Issue with file:line reference]

  ## Warnings (⚠️)
  [Issues that should be addressed but not blocking]
  - [Warning with file:line reference]
  - [Warning with file:line reference]

  ## Suggestions (💡)
  [Nice-to-have improvements]
  - [Suggestion with file:line reference]
  - [Suggestion with file:line reference]

  ## Positive Observations (✅)
  [Things done well]
  - [Good practice observed]
  - [Good practice observed]

  ## Code Quality Score
  [X/10] - [Brief explanation]

  ## Recommendation
  [APPROVE / REQUEST CHANGES / NEEDS DISCUSSION]
```

### 4. Present Review Results

After agent completes, format and present results:

```
🔍 CODE REVIEW RESULTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Review Scope: [scope description]
📅 Reviewed: [timestamp]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Agent's review output]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Summary:
   Critical Issues: [count] ❌
   Warnings: [count] ⚠️
   Suggestions: [count] 💡

   Quality Score: [X/10]
   Recommendation: [APPROVE/REQUEST CHANGES/NEEDS DISCUSSION]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[If critical issues found:]
⚠️  NEXT STEPS:
   1. Fix critical issues (❌) before committing
   2. Address warnings (⚠️) if possible
   3. Consider suggestions (💡) for improvements
   4. Re-run review: /review-code

[If approved:]
✅ READY TO PROCEED:
   • All checks passed
   • No critical issues found
   • Code quality is good

   Next steps:
   • Commit changes: git add . && git commit -m "message"
   • Or create PR: /commit-push-pr
```

### 5. Offer Auto-Fix (Optional)

If agent can auto-fix issues:

```
Would you like me to automatically fix the issues found? (y/n)

[If yes:]
  • Launch refactoring-specialist for critical issues
  • Apply automated linting fixes
  • Re-run review to verify

[If no:]
  • Review output above
  • Fix manually
  • Re-run /review-code when ready
```

---

## Review Categories

### Security Review
Focus on security vulnerabilities:
- SQL injection
- XSS vulnerabilities
- CSRF protection
- Authentication bypass
- Authorization issues
- Sensitive data exposure
- Dependency vulnerabilities

### Performance Review
Focus on performance issues:
- N+1 queries
- Memory leaks
- Inefficient algorithms
- Unnecessary computations
- Resource leaks
- Caching opportunities

### Architecture Review
Focus on design patterns:
- SOLID principles
- Design patterns usage
- Separation of concerns
- Dependency injection
- Abstraction levels

---

## Examples

**Review git changes:**
```
/review-code
/review-code git
```

**Review specific file:**
```
/review-code src/api/users.py
/review-code components/LoginForm.tsx
```

**Review staged changes only:**
```
/review-code staged
```

**Review last commit:**
```
/review-code last-commit
```

**Review entire directory:**
```
/review-code src/api/
/review-code components/auth/
```

---

## Integration with Workflow

**Before commit:**
```bash
# Make changes
# ...

# Review before committing
/review-code

# Fix issues
# ...

# Commit
git add .
git commit -m "feat: add user authentication"
```

**Before creating PR:**
```bash
# Review all changes
/review-code

# If approved, create PR
/commit-push-pr
```

**During development:**
```bash
# Review specific file you're working on
/review-code src/services/auth.py

# Fix and continue
```

---

## Advanced Options

**Review with specific focus:**
Add focus instructions in prompt:
- "Focus on security" → Deep security analysis
- "Focus on performance" → Performance optimization
- "Focus on tests" → Test coverage and quality
- "Focus on style" → Code style and formatting

**Compare with main branch:**
```bash
git diff main..HEAD
```

**Review specific commit:**
```bash
git show <commit-hash>
```

---

## Error Handling

**If not a git repository:**
```
⚠️  Not a git repository

You can still review specific files:
   /review-code path/to/file.py
```

**If no changes to review:**
```
ℹ️  No changes found to review

Options:
   • Review specific file: /review-code [file-path]
   • Review last commit: /review-code last-commit
   • Review directory: /review-code [dir-path]
```

**If file doesn't exist:**
```
❌ File not found: [path]

Check the path and try again:
   /review-code [correct-path]
```

---

## Notes

- Quick and focused review without full PR overhead
- Automated analysis by specialized code-reviewer agent
- Actionable feedback with file:line references
- Can be run multiple times during development
- Complements but doesn't replace human code review
- Best used iteratively during development
- Results are not saved; re-run after fixes
