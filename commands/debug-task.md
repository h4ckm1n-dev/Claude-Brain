# Debug Failed Task

Systematic debugging workflow for failed tasks or errors

**Usage:** `/debug-task [description of issue]`

**Input:** $ARGUMENTS

---

## Instructions

Systematically debug and resolve issues using a structured approach with the debugger agent.

### 1. Gather Diagnostic Information

Collect comprehensive context about the failure:

#### 1.1 User-Provided Context
```
Issue Description: $ARGUMENTS

[If description is vague, ask for clarification:]
   • What were you trying to do?
   • What did you expect to happen?
   • What actually happened?
   • When did this start?
```

#### 1.2 Git Status
```bash
# Check current state
git status --short 2>/dev/null
git log -1 --oneline 2>/dev/null

# Check for uncommitted changes
uncommitted_changes=$(git diff --name-only 2>/dev/null | wc -l)
```

#### 1.3 Recent Errors
```bash
# Check recent logs
if [ -f "logs/error.log" ]; then
  tail -50 logs/error.log
fi

# Check application logs
if [ -f "logs/app.log" ]; then
  tail -50 logs/app.log
fi

# Check for Python tracebacks
if [ -d "__pycache__" ]; then
  find . -name "*.pyc" -mtime -1
fi
```

#### 1.4 PROJECT_CONTEXT.md History
```bash
# Check last agent activity
if [ -f "PROJECT_CONTEXT.md" ]; then
  grep -A 5 "^\*\*.*\*\* - \`.*\`" PROJECT_CONTEXT.md | tail -20

  # Check for blockers
  grep -i "blocker\|blocked\|error\|failed" PROJECT_CONTEXT.md
fi
```

#### 1.5 Environment Check
```bash
# Check tools and dependencies
bash ~/.claude/scripts/check-tools.sh 2>/dev/null

# Check for missing dependencies
if [ -f "requirements.txt" ]; then
  pip check 2>/dev/null
elif [ -f "package.json" ]; then
  npm ls --depth=0 2>/dev/null
fi
```

### 2. Categorize the Issue

Determine failure type:

```yaml
Error Categories:
  - SYNTAX_ERROR: Code doesn't compile/parse
  - TEST_FAILURE: Tests are failing
  - RUNTIME_ERROR: Crashes during execution
  - VALIDATION_ERROR: Validation loops failed
  - DEPENDENCY_ERROR: Missing or incompatible dependencies
  - CONFIGURATION_ERROR: Misconfiguration
  - AGENT_COORDINATION: Agent workflow issue
  - LOGIC_ERROR: Code runs but produces wrong results
```

Present diagnostic summary:
```
🔍 DIAGNOSTIC SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Issue: [User description]
Category: [Detected category]

📁 Environment:
   Working Directory: [path]
   Git Status: [clean / X files modified]
   Last Commit: [commit message]

🚨 Error Indicators:
   [Recent errors from logs]
   [Failed tests]
   [Blockers from PROJECT_CONTEXT.md]

👥 Recent Agent Activity:
   [Last 3 agent entries from PROJECT_CONTEXT.md]

🔧 Tools Status:
   [Available/Missing tools]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Analysis: [Initial assessment of problem]
```

### 3. Launch Debugger Agent

Use Task tool with comprehensive context:

```yaml
subagent_type: debugger
description: Debug [category] issue
prompt: |
  You are debugging a failed task. Use systematic debugging approach.

  **ISSUE DESCRIPTION**:
  [User's description from $ARGUMENTS]

  **DIAGNOSTIC CONTEXT**:
  [Include all gathered diagnostic info]

  **RECENT ACTIVITY**:
  [Last agent activities from PROJECT_CONTEXT.md]

  **YOUR TASK**:
  1. **Reproduce the issue**
     - Read relevant files
     - Identify the failing component
     - Understand the error

  2. **Root Cause Analysis**
     - Trace the error to its source
     - Identify all contributing factors
     - Check for related issues

  3. **Propose Solution**
     - Multiple approaches if applicable
     - Pros/cons of each approach
     - Recommended solution

  4. **Implement Fix**
     - Apply the fix
     - Add defensive code if needed
     - Update error handling

  5. **Validate Fix**
     - Run failing tests
     - Run related tests
     - Verify no new issues introduced

  6. **Document**
     - What was wrong
     - What was fixed
     - How to prevent in future

  **VALIDATION**:
  After fixing, run:
  [Category-specific validation commands]

  **UPDATE PROJECT_CONTEXT.md**:
  Add entry documenting:
  - Issue encountered
  - Root cause
  - Fix applied
  - Prevention strategy
```

### 4. Monitor Debug Process

Show progress updates as agent works:

```
🔧 DEBUGGING IN PROGRESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 1: Reproduction
   [Agent's reproduction steps and findings]

Phase 2: Root Cause Analysis
   [Agent's analysis]

Phase 3: Solution Design
   [Agent's proposed solutions]

Phase 4: Implementation
   [Agent's fix implementation]

Phase 5: Validation
   [Agent's validation results]
```

### 5. Present Debug Results

After agent completes:

```
✅ DEBUG COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 ISSUE IDENTIFIED:
[Root cause description]

Located in: [file:line references]

🔧 FIX APPLIED:
[Description of what was changed]

Files Modified:
   • [file1] - [change description]
   • [file2] - [change description]

✅ VALIDATION RESULTS:
[Test results, validation outcomes]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 LESSONS LEARNED:

Root Cause:
   [Detailed explanation]

Contributing Factors:
   • [Factor 1]
   • [Factor 2]

Prevention Strategy:
   • [How to prevent this in future]
   • [Checks to add]
   • [Best practices to follow]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 NEXT STEPS:

[If fully resolved:]
   ✅ Issue resolved and validated
   • Commit changes: git add . && git commit -m "fix: [description]"
   • Continue with your work

[If partially resolved:]
   ⚠️  Issue partially resolved, remaining work:
   • [Action item 1]
   • [Action item 2]

[If not resolved:]
   ❌ Unable to fully resolve, manual investigation needed:
   • [What to check]
   • [Where to look]
   • [Expert to consult]
```

---

## Debug Strategies by Category

### SYNTAX_ERROR
```yaml
Steps:
  1. Run linter/compiler to see exact error
  2. Check syntax at error location
  3. Fix syntax
  4. Re-run compiler/linter
  5. Validate

Commands:
  Python: ruff check . && mypy .
  TypeScript: npx tsc --noEmit
  JavaScript: npx eslint .
```

### TEST_FAILURE
```yaml
Steps:
  1. Run failing test in isolation
  2. Read test code and understand expectation
  3. Debug why actual != expected
  4. Fix implementation or test
  5. Re-run all tests

Commands:
  Python: pytest [test-file]::[test-name] -v
  JavaScript: npm test -- [test-file]
```

### RUNTIME_ERROR
```yaml
Steps:
  1. Get full stack trace
  2. Identify error location
  3. Add logging around error
  4. Reproduce with logging
  5. Fix root cause
  6. Remove debug logging

Commands:
  Check logs, add print/console.log, re-run
```

### DEPENDENCY_ERROR
```yaml
Steps:
  1. Check dependency versions
  2. Look for conflicts
  3. Update or pin versions
  4. Clear caches
  5. Reinstall

Commands:
  Python: pip check, pip install --force-reinstall
  JavaScript: npm audit fix, rm -rf node_modules && npm install
```

---

## Examples

**Debug test failure:**
```
/debug-task tests are failing after refactoring authentication
```

**Debug runtime error:**
```
/debug-task app crashes when user tries to login
```

**Debug build failure:**
```
/debug-task TypeScript compilation errors in production build
```

**Debug performance issue:**
```
/debug-task API endpoint is taking 5+ seconds to respond
```

**Debug deployment issue:**
```
/debug-task Docker container won't start in production
```

---

## Integration with Agent Workflow

**If agent chain failed:**
```bash
# Check which agent failed
grep -i "error\|failed" PROJECT_CONTEXT.md | tail -5

# Debug that agent's work
/debug-task [agent-name] failed during [task]
```

**After debugging:**
```bash
# Document in PROJECT_CONTEXT.md
# Update prevention strategies
# Share learnings with team
```

---

## Advanced Debugging

**Interactive debugging:**
```python
# Python
import pdb; pdb.set_trace()

# JavaScript
debugger;
```

**Remote debugging:**
```bash
# Attach debugger to running process
# Check remote logs
# Inspect production state
```

**Performance debugging:**
```bash
# Use performance-profiler agent
/quick-agent performance-profiler: identify bottleneck in [feature]
```

---

## Error Prevention

After resolving, consider:
1. **Add tests** to catch this type of error
2. **Add validation** to prevent invalid state
3. **Improve error messages** for faster debugging
4. **Document** in code comments
5. **Update CLAUDE.md** with learnings

---

## Notes

- Systematic approach prevents missing root cause
- Always validate fix before considering complete
- Document learnings for future prevention
- Update PROJECT_CONTEXT.md with resolution
- Consider if task descriptions need improvement to prevent similar issues
- Some issues may require domain specialist instead of debugger
