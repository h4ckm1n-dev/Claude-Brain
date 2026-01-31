# Comprehensive Troubleshooting Guide

Detailed solutions for common agent coordination issues.

**Reference**: These detailed troubleshooting scenarios are extracted from CLAUDE.md to keep the main documentation concise. For quick fixes, see the [Troubleshooting Guide section in CLAUDE.md](../CLAUDE.md#-troubleshooting-guide).

---

## Issue: "Agent didn't understand what I need"

**Symptoms:**
- Agent asks for clarification
- Output doesn't match expectations
- Agent works on wrong files

**Solutions:**
```
❌ BAD:  "Fix the bug"
✅ GOOD: "Fix the TypeError in src/auth.ts:42 where user.email is undefined"

❌ BAD:  "Make it faster"
✅ GOOD: "Optimize the /api/products endpoint - currently 2.5s, need <500ms"

❌ BAD:  "Add tests"
✅ GOOD: "Add E2E tests for the checkout flow in tests/e2e/checkout.spec.ts"
```

**Prevention:**
- Provide file paths
- Include error messages
- Specify acceptance criteria
- Share relevant context

---

## Issue: "Agents are duplicating work"

**Symptoms:**
- Multiple agents modify same code
- Conflicting implementations
- Wasted effort

**Root Causes:**
1. PROJECT_CONTEXT.md not read
2. Unclear agent boundaries
3. Parallel execution without coordination

**Solutions:**
```
1. CHECK PROJECT_CONTEXT.md first:
   "Before starting, read PROJECT_CONTEXT.md to see what's been done"

2. CLEARLY ASSIGN domains:
   ✅ "backend-architect: API only, frontend-developer: UI only"
   ❌ "Both of you work on auth"

3. USE SEQUENTIAL when there's overlap:
   ✅ "backend-architect → then → frontend-developer"
   ❌ Launch both in parallel

4. REVIEW handoffs in PROJECT_CONTEXT.md:
   Each agent should document what they did
```

---

## Issue: "An agent needs output from another agent that hasn't run"

**Symptoms:**
- Agent asks for missing files
- Agent makes assumptions
- Blocker documented in PROJECT_CONTEXT.md

**Solutions:**
```
1. SWITCH TO SEQUENTIAL:
   If frontend needs API spec, run api-designer FIRST

2. CHECK EXECUTION ORDER:
   Review dependencies before launching agents

3. USE MOCKS for parallel work:
   Frontend can start with mock API if needed

4. READ ERROR MESSAGES:
   "Need /docs/api/auth.yaml" → Run api-designer first
```

**Example Fix:**
```
❌ WRONG ORDER:
   frontend-developer (needs API spec)
   api-designer (creates spec)

✅ CORRECT ORDER:
   api-designer (creates spec)
   frontend-developer (uses spec)
```

---

## Issue: "I want to modify what an agent did"

**Symptoms:**
- Agent's output is close but needs changes
- Want different approach
- Need adjustments

**Solutions:**

**Option 1: Direct Edit**
```
• Best for: Small changes (<20 lines)
• How: Edit files directly, commit changes
• Note: Update PROJECT_CONTEXT.md if significant
```

**Option 2: Re-run Agent**
```
• Best for: Major changes, different approach
• How: "backend-architect, refactor auth.ts to use Passport instead of custom JWT"
• Note: Provide specific guidance
```

**Option 3: Code Review**
```
• Best for: Uncertain about best fix
• How: "code-reviewer, review auth.ts and suggest improvements"
• Note: Get expert opinion first
```

---

## Issue: "Multiple agents modified the same file"

**Symptoms:**
- Git shows many changes to one file
- Conflicting modifications
- Unclear what changed

**This is NORMAL for:**
- Complex features spanning frontend/backend
- Refactoring + security fixes
- Sequential improvements

**Best Practices:**
```
1. REVIEW git diff before committing:
   git diff src/auth.ts

2. CHECK PROJECT_CONTEXT.md for reasoning:
   "Why did 3 agents touch this file?"

3. RUN code-reviewer if concerned:
   "code-reviewer, check src/auth.ts for conflicts"

4. TRUST THE LAST AGENT:
   Later agents see earlier changes (sequential)
   Agents don't lock files (parallel is OK)
```

---

## Issue: "Agent failed mid-task"

**Symptoms:**
- Error message from agent
- Partial completion
- Files in inconsistent state

**Recovery Steps:**
```
1. READ THE ERROR:
   Understanding why helps prevent repeat

2. CHECK what completed:
   Review git status, PROJECT_CONTEXT.md

3. DECIDE: Fix or Re-run?
   Small issue → debugger agent
   Large issue → Re-run original agent with fixes

4. DOCUMENT in PROJECT_CONTEXT.md:
   "backend-architect failed on auth.ts - missing dependency"
```

---

## Issue: "Workflow is taking too long"

**Symptoms:**
- Agents running sequentially when could be parallel
- Waiting for unnecessary dependencies
- Over-engineering

**Optimizations:**
```
1. IDENTIFY PARALLELIZABLE WORK:
   ❌ Sequential: frontend → backend → tests
   ✅ Parallel: frontend + backend → tests

2. USE MOCKS to unblock:
   Frontend can use mock API while backend builds

3. SKIP UNNECESSARY AGENTS:
   Simple feature? Maybe skip code-architect
   Internal tool? Maybe skip seo-specialist

4. BATCH REVIEWS:
   ❌ Review after each agent
   ✅ Review once at end (security + performance + code quality in parallel)
```

---

## Issue: "Can't find the right agent"

**Symptoms:**
- Unsure which agent to use
- Multiple agents seem applicable
- Agent descriptions are unclear

**Decision Framework:**
```
STEP 1: Match primary domain
   API work? → api-designer or backend-architect
   UI work? → frontend-developer or ui-designer

STEP 2: Consider specialization
   General API? → backend-architect
   API design/documentation? → api-designer

STEP 3: Check "When to Use" in agent list
   Each agent has specific triggers

STEP 4: Start with architect, then specialist
   Unsure? code-architect plans, then domain agent implements
```

**Common Confusions:**

| Confused About | Use This Agent | Not This Agent | Why |
|----------------|----------------|----------------|-----|
| API implementation | `backend-architect` | `api-designer` | Designer creates specs, architect implements |
| API documentation | `api-designer` | `technical-writer` | Designer knows API patterns better |
| UI implementation | `frontend-developer` | `ui-designer` | Designer creates design, developer implements |
| Security review | `security-practice-reviewer` | `code-reviewer` | Security specialist knows vulnerabilities |
| Code quality | `code-reviewer` | `refactoring-specialist` | Reviewer audits, refactorer fixes |

---

## Issue: "PROJECT_CONTEXT.md is getting huge"

**Symptoms:**
- File is 1000+ lines
- Hard to find information
- Outdated entries

**Maintenance:**
```
1. ARCHIVE old activity (monthly):
   Move completed sprints to PROJECT_ARCHIVE.md

2. KEEP RECENT ACTIVITY ONLY (last 2 weeks):
   Delete old agent logs

3. UPDATE shared decisions:
   Remove superseded decisions

4. CLEAN UP artifacts section:
   Remove references to deleted files

5. CONDENSE known issues:
   Group related issues
```

**Template for archiving:**
```markdown
## Agent Activity Log

<!-- RECENT (keep this) -->
**2025-11-02** - Recent work here...

<!-- ARCHIVE (move to PROJECT_ARCHIVE.md) -->
**2025-10-15** - Old work here...
```

---

## Issue: "Agents creating wrong files"

**Symptoms:**
- Files in unexpected locations
- Naming doesn't match conventions
- Multiple coordination files created

**Prevention:**
```
1. SPECIFY file paths explicitly:
   ❌ "Create an API spec"
   ✅ "Create API spec at /docs/api/users.yaml"

2. REFERENCE artifact locations:
   "Follow standard locations in PROJECT_CONTEXT.md"

3. ENFORCE single coordination file:
   If agent creates PHASE_1_PROGRESS.md, correct immediately
   "Update PROJECT_CONTEXT.md instead"
```

---

## Issue: "Agent coordination breakdown"

**Symptoms:**
- Agents not reading PROJECT_CONTEXT.md
- Missing handoffs
- No artifact documentation

**Diagnosis:**
```
CHECK PROJECT_CONTEXT.md for:
1. Is Activity Log being updated?
2. Are artifacts documented?
3. Are blockers listed?
4. Are next steps clear?
```

**Recovery:**
```
1. MANUALLY UPDATE PROJECT_CONTEXT.md:
   Document current state yourself

2. REMIND agents to update:
   "After completing, update PROJECT_CONTEXT.md with your changes"

3. REVIEW handoffs:
   Ensure each agent documents artifacts for next agent
```

---

**Back to main documentation**: [CLAUDE.md](../CLAUDE.md)
