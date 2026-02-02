
# ⛔⛔⛔ STOP - READ THIS FIRST ⛔⛔⛔

## 🚨 PRE-FLIGHT CHECKLIST - COMPLETE IN ORDER 🚨

**STEP 0: CHECK FOR AUTOMATED RECOMMENDATIONS**
Look for these in <system-reminder> tags (appears BEFORE CLAUDE.md):
- 🧠 Memory suggestions (from memory-suggest.sh hook)
- 🎯 Plan mode reminders (from plan-mode-reminder.sh hook)

**IF YOU SEE A PLAN MODE REMINDER WITH "PLANNING REQUIRED" OR "PLANNING RECOMMENDED":**
→ You MUST follow the workflow described in that reminder
→ Do NOT proceed with reading files or coding until you EnterPlanMode()
→ This is NOT optional - the hook analyzed the task and determined planning is critical

---

**STEP 1: MEMORY PROTOCOL (MANDATORY - NO EXCEPTIONS)**

```
╔════════════════════════════════════════════════════════════╗
║  MEMORY PROTOCOL - EXECUTE IMMEDIATELY                     ║
║                                                             ║
║  1. search_memory(query="[user request]", limit=10)        ║
║  2. get_context(project="[project]", hours=24)             ║
║  3. Review <system-reminder> memory suggestions            ║
║                                                             ║
║  ⚠️  DO NOT SKIP - THIS IS A BLOCKING REQUIREMENT         ║
╚════════════════════════════════════════════════════════════╝
```

**If you proceed without completing steps 1-3 above, you are VIOLATING PROTOCOL and will cause:**
- ❌ Repeated work on solved problems
- ❌ Lost knowledge from previous sessions
- ❌ User frustration and loss of trust
- ❌ Wasted time debugging known issues

**The user has configured AUTOMATED MEMORY HOOKS. You will receive memory suggestions in `<system-reminder>` tags at session start. USING THEM IS MANDATORY, NOT OPTIONAL.**

---

# Claude Code Agent Ecosystem

47 specialized agents for autonomous software development. Coordinate via PROJECT_CONTEXT.md.

> **CRITICAL LIMITATION**: Subagents cannot spawn other subagents. For nested workflows, return to main conversation and chain from there.

---

# 🔥 MEMORY ENFORCEMENT PROTOCOL 🔥

## ⛔ ABSOLUTE REQUIREMENTS - NON-NEGOTIABLE ⛔

### PHASE 1: SESSION START (DO THIS FIRST - ALWAYS)

**EVERY SINGLE SESSION MUST START WITH:**

```javascript
// STEP 1: SEARCH MEMORY - BLOCKING REQUIREMENT
search_memory(query="[extract keywords from user's request]", limit=10)

// STEP 2: SEARCH DOCUMENTS IF CODE-RELATED - RECOMMENDED
// If the task involves code, also search documents
search_documents(query="[relevant code search]", limit=5)

// STEP 3: GET PROJECT CONTEXT - BLOCKING REQUIREMENT
// Note: get_context() now includes both memories AND documents
get_context(project="[project name if known]", hours=24)

// STEP 4: REVIEW SUGGESTIONS - MANDATORY
// Read memory suggestions from <system-reminder> tags
// These are AUTO-PROVIDED by the system - USE THEM
```

**❌ VIOLATION CHECKPOINTS:**
- Starting to read files WITHOUT searching memory first = **VIOLATION**
- Running commands WITHOUT reviewing context first = **VIOLATION**
- Proposing solutions WITHOUT checking past solutions = **VIOLATION**
- Ignoring `<system-reminder>` memory suggestions = **VIOLATION**

**✅ CORRECT BEHAVIOR:**
```
User: "Fix the authentication bug"

WRONG ❌:
Claude: [Reads files immediately]
Claude: [Starts debugging]

RIGHT ✅:
Claude: [Calls search_memory("authentication bug fix")]
Claude: [Calls get_context(project="app-name")]
Claude: [Reviews memory suggestions]
Claude: [Finds: "Auth bug fixed in session X with solution Y"]
Claude: [Applies known solution OR builds on previous work]
```

### PHASE 2: DURING WORK (CONTINUOUS VIGILANCE)

**BEFORE SENDING ANY RESPONSE, ASK YOURSELF:**

```
┌─────────────────────────────────────────────────────────┐
│ SELF-AUDIT CHECKLIST (MANDATORY BEFORE EVERY RESPONSE)  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ❓ Q1: Did I search memory BEFORE starting?            │
│    → If NO: STOP, search NOW, review results           │
│                                                          │
│ ❓ Q2: Did I fix a bug or solve a problem?             │
│    → If YES: Call store_memory() NOW                   │
│                                                          │
│ ❓ Q3: Did I make an architecture decision?            │
│    → If YES: Call store_memory() NOW                   │
│                                                          │
│ ❓ Q4: Did I discover a reusable pattern?              │
│    → If YES: Call store_memory() NOW                   │
│                                                          │
│ ❓ Q5: Did I use WebFetch/WebSearch?                   │
│    → If YES: Call store_memory() NOW                   │
│                                                          │
│ ⚠️  IF Q1 = NO: DO NOT PROCEED                         │
│ ⚠️  IF Q2-Q5 = YES BUT NOT STORED: DO NOT SEND         │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### PHASE 3: SESSION END (MANDATORY STORAGE)

**EVERY SOLUTION/DECISION/PATTERN MUST BE STORED:**

```javascript
// IMMEDIATE storage required when:
store_memory({
  type: "error|docs|decision|pattern|learning",
  content: "[DETAILED description - min 30 chars]",
  tags: ["[SPECIFIC tags]", "[SEARCHABLE tags]"],  // Min 2 tags
  project: "[project name]",

  // TYPE-SPECIFIC required fields:
  // ERROR: error_message + (solution OR prevention)
  // DECISION: rationale + alternatives
  // DOCS: source URL
})
```

**STORAGE TRIGGERS (AUTO-STORE REQUIRED):**
1. ✅ Fixed bug/error → `type="error"` with solution
2. ✅ Made architecture choice → `type="decision"` with rationale
3. ✅ Found reusable pattern → `type="pattern"` with examples
4. ✅ Fetched documentation → `type="docs"` with source
5. ✅ Learned about codebase → `type="learning"` with context
6. ✅ Applied workaround → `type="learning"` with why

**❌ NEVER:**
- Complete work without storing
- Store placeholder/test memories
- Use generic-only tags ("misc", "temp")
- Skip context/rationale fields

**✅ ALWAYS:**
- Store IMMEDIATELY after solving
- Include WHY, not just WHAT
- Use specific, searchable tags
- Reference memory IDs when building on past work

---

## 🚫 ZERO TOLERANCE POLICY 🚫

**IF THE USER ASKS "Why didn't you use memory?" = YOU FAILED**

When this happens, you MUST:
1. ❗ Acknowledge failure explicitly
2. ❗ Search memory NOW for relevant context
3. ❗ Store the solution you SHOULD have stored
4. ❗ Explain your protocol violation
5. ❗ Promise to follow PHASE 1-3 next time

**This should NEVER happen. The system provides automated memory suggestions. If you ignore them, you are directly violating instructions.**

---

## 🧠 Memory System Reference

**MCP Memory Tools** (available via MCP server):
| Tool | When | Required? |
|------|------|-----------|
| `search_memory` | START of EVERY session | ✅ MANDATORY |
| `search_documents` | When searching codebase/files | ⚡ RECOMMENDED |
| `get_context` | START of EVERY session | ✅ MANDATORY |
| `store_memory` | AFTER solving ANY problem | ✅ MANDATORY |
| `mark_resolved` | Mark error as fixed | Optional |
| `link_memories` | Create relationships | Optional |

### Documents vs Memories: When to Use Which

**Memories** (structured knowledge):
- Errors you encountered and their solutions
- Architecture decisions and rationale
- Patterns and best practices
- Documentation you saved with context
- Learnings from development

**Documents** (filesystem content):
- Code files (.py, .ts, .js, etc.)
- Markdown documentation (.md)
- Configuration files (.json, .yaml)
- PDFs and other reference materials
- Raw file content without metadata

**Best Practice - Search Both:**
```javascript
// 1. Search memories (structured knowledge)
search_memory(query="authentication bug", limit=10)

// 2. Search documents (code/files)
search_documents(query="authentication implementation", limit=5)

// 3. get_context() now includes both automatically
get_context(project="myapp", hours=24)
```

### Memory Quality Requirements (ENFORCED)

**UNIVERSAL (ALL TYPES):**
- ✅ Min 30 characters content
- ✅ Min 2 descriptive tags
- ✅ Min 5 words
- ❌ No placeholders ("test", "todo", "tbd")
- ❌ No generic-only tags

**TYPE-SPECIFIC:**
- **error**: MUST include `solution` OR `prevention` + `error_message`
- **decision**: MUST include `rationale` (WHY decision was made)
- **pattern**: Min 100 chars recommended, include usage context
- **docs**: Include `source` URL, summarize key points

**Quality validation is ENFORCED. Low-quality memories will be REJECTED with HTTP 422.**

### Memory Service Commands

```bash
# Start service (REQUIRED before work)
cd ~/.claude/memory && docker compose up -d

# Check health
curl http://localhost:8100/health

# If service DOWN = work CANNOT proceed
```

---

## 📋 PLANNING-FIRST WORKFLOW (2026 BEST PRACTICE)

### CRITICAL: Separate Planning from Execution

**Research shows that planning before coding reduces token usage by 76% while achieving better results.** Always follow this pattern for complex tasks:

```
┌─────────────────────────────────────────────────────────┐
│ READ → PLAN → DELEGATE → EXECUTE → STORE               │
└─────────────────────────────────────────────────────────┘
```

### When to Use EnterPlanMode

**MANDATORY for complex tasks:**
- ✅ New features affecting 3+ files
- ✅ Architecture/design decisions
- ✅ Multiple valid implementation approaches
- ✅ Tasks where you'd normally ask user for clarification
- ✅ Refactoring or code modifications
- ✅ Unclear requirements needing exploration

**OPTIONAL for simple tasks:**
- ❌ Single file, <10 lines
- ❌ Bug fix with known solution from memory
- ❌ Trivial changes (typos, docs)

### The Planning Workflow

**Step 1: Memory + Research Phase**
```javascript
// 1. Search memory FIRST (mandatory)
search_memory(query="[task keywords]", limit=10)
get_context(project="[project]", hours=24)

// 2. Enter plan mode
EnterPlanMode()

// 3. Read files (plan mode allows read-only access)
Read, Glob, Grep, LS - gather all context

// 4. Research if needed
WebFetch, WebSearch - get external knowledge
```

**Step 2: Plan Creation**
```markdown
In plan mode, create comprehensive plan covering:

## Analysis
- Current state (what exists)
- Requirements (what's needed)
- Constraints (limitations)
- Past solutions (from memory search)

## Approach
- Option 1: [Pros/Cons]
- Option 2: [Pros/Cons]
- RECOMMENDED: [Why this option]

## Implementation Steps
1. [Specific file/change]
2. [Specific file/change]
3. [Testing strategy]
4. [Validation approach]

## Dependencies
- Files to modify
- Agents to delegate to
- External dependencies
```

**Step 3: Delegation Strategy**
```javascript
// After plan approval, delegate to specialized agents

// Example delegation chain:
Task(subagent_type="code-architect", ...)     // Design
→ Task(subagent_type="backend-architect", ...) // Implement
→ Task(subagent_type="test-engineer", ...)     // Test
→ Task(subagent_type="code-reviewer", ...)     // Review
```

**Step 4: Execution & Storage**
```javascript
// Execute the plan
[Agent work happens]

// MANDATORY: Store results
store_memory({
  type: "decision|pattern|learning",
  content: "[what was decided/discovered]",
  tags: [...],
  project: "..."
})
```

### Planning Best Practices from Research

**Keep plans concise:**
- Focus on WHAT and WHY, not HOW (agents handle HOW)
- Reference external docs instead of copying (`Read docs/architecture.md`)
- Use file:line pointers instead of code snippets

**Use AskUserQuestion for clarity:**
- If multiple approaches are equally valid
- If requirements are ambiguous
- BEFORE creating plan, not after

**Model routing for planning:**
- Use `inherit` (Opus) for complex architecture decisions
- Use `sonnet` for standard feature planning
- Reserve `haiku` for simple documentation tasks

### Anti-Patterns to Avoid

❌ **DON'T**: Start coding immediately without plan
❌ **DON'T**: Skip memory search before planning
❌ **DON'T**: Create 10-page detailed implementation plans (keep under 2 pages)
❌ **DON'T**: Plan without reading existing code first
❌ **DON'T**: Execute without user approval on complex changes

✅ **DO**: Search memory → Plan → Get approval → Delegate → Execute → Store
✅ **DO**: Keep plans focused on strategy, not tactics
✅ **DO**: Reference existing patterns from memory
✅ **DO**: Use progressive disclosure (link to detailed docs)

---

## 🎯 Quick Tool Reference

**🚨 MANDATORY FIRST:**
```javascript
search_memory(query="[user request keywords]", limit=10)
get_context(project="[project name]", hours=24)
```

**Development Tools:**
```bash
# Security
python3 ~/.claude/tools/security/secret-scanner.py .

# Service health
~/.claude/tools/devops/service-health.sh https://api.example.com

# Code complexity
python3 ~/.claude/tools/analysis/complexity-check.py src/

# Error logs
python3 ~/.claude/tools/data/log-analyzer.py /var/log/app.log

# Test coverage
python3 ~/.claude/tools/testing/coverage-reporter.py coverage.xml
```

**By Use Case:**
- 🧠 **MEMORY (DO THIS FIRST)**: search_memory, get_context, store_memory
- 🔒 **Security**: secret-scanner.py, vuln-checker.sh
- 📊 **Code Quality**: complexity-check.py, duplication-detector.py
- 🧪 **Testing**: coverage-reporter.py, test-selector.py
- ⚡ **Performance**: resource-monitor.py, sql-explain.py
- 🚀 **DevOps**: docker-manager.sh, service-health.sh

---

## 🔄 Workflows (MEMORY + PLANNING FIRST)

> **ALL WORKFLOWS: SEARCH MEMORY → PLAN → DELEGATE → EXECUTE → STORE**

### Standard Workflow Pattern (2026 Best Practice)

```
1. SEARCH     → search_memory() + get_context()
2. PLAN       → EnterPlanMode() for complex tasks
3. DELEGATE   → Task(subagent_type="...") to specialists
4. EXECUTE    → Agents implement the plan
5. STORE      → store_memory() results + decisions
```

### Workflow Examples

**New Feature (Complex):**
```
SEARCH → EnterPlanMode → code-architect (design)
       → AskUserQuestion (if needed)
       → ExitPlanMode (get approval)
       → backend-architect (implement)
       → test-engineer (validate)
       → code-reviewer (review)
       → STORE (decision + pattern)
```

**Bug Fix (Simple with known solution):**
```
SEARCH → [Find solution in memory]
       → Apply fix directly
       → STORE (mark original error as resolved)
```

**Bug Fix (Unknown issue):**
```
SEARCH → EnterPlanMode → debugger (investigate)
       → [Identify root cause]
       → ExitPlanMode (plan fix)
       → domain-agent (implement)
       → test-engineer (regression test)
       → STORE (error + solution)
```

**Code Quality (Refactoring):**
```
SEARCH → EnterPlanMode → code-reviewer (assess)
       → [Create refactoring plan]
       → ExitPlanMode (approve)
       → refactoring-specialist (execute)
       → test-engineer (validate)
       → STORE (pattern + learnings)
```

**Performance (Optimization):**
```
SEARCH → EnterPlanMode → performance-profiler (analyze)
       → [Identify bottlenecks]
       → ExitPlanMode (optimization strategy)
       → backend-architect (optimize)
       → test-engineer (benchmark)
       → STORE (pattern + metrics)
```

**Security (Audit & Fix):**
```
SEARCH → EnterPlanMode → security-practice-reviewer (scan)
       → [Catalog vulnerabilities]
       → ExitPlanMode (remediation plan)
       → domain-agents (fix)
       → test-engineer (validate)
       → STORE (vulnerabilities + fixes)
```

---

## Agent Invocation Rules

**Use specialized agent when:**
- 3+ files or multiple modules
- Domain expertise needed (API, security, performance, testing, deployment)
- Production code or infrastructure
- Architecture/design decisions
- ANY keyword trigger (see Keyword Triggers)

**Work directly when:**
- Single file, <10 lines, trivial change
- No patterns or expertise needed

---

## Keyword Triggers

| Keywords | Agent |
|----------|-------|
| "API", "REST", "GraphQL" | api-designer |
| "frontend", "UI", "React", "Vue" | frontend-developer |
| "backend", "server", "database" | backend-architect |
| "test", "testing", "TDD" | test-engineer |
| "deploy", "CI/CD", "Docker" | deployment-engineer |
| "optimize", "performance" | performance-profiler |
| "security", "vulnerability" | security-practice-reviewer |
| "refactor", "technical debt" | refactoring-specialist |
| "bug", "error", "broken" | debugger |
| "mobile", "iOS", "Android" | mobile-app-developer |
| "AI", "ML", "LLM" | ai-engineer |
| "design", "architecture" | code-architect |
| "TypeScript", "type safety" | typescript-expert |

---

## All 47 Agents by Category

### Full-Stack (4)
**code-architect**, **backend-architect**, **frontend-developer**, **api-designer**

### Language Specialists (6)
**python-expert**, **typescript-expert**, **mobile-app-developer**, **desktop-app-developer**, **game-developer**, **blockchain-developer**

### DevOps & Infrastructure (3)
**deployment-engineer**, **infrastructure-architect**, **observability-engineer**

### Testing & Quality (4)
**test-engineer**, **api-tester**, **code-reviewer**, **debugger**

### AI & ML (2)
**ai-engineer**, **ai-prompt-engineer**

### Data & Analytics (4)
**data-scientist**, **database-optimizer**, **analytics-engineer**, **visualization-dashboard-builder**

### Performance & Security (3)
**performance-profiler**, **security-practice-reviewer**, **math-checker**

### Design & UX (4)
**ui-designer**, **ux-researcher**, **mobile-ux-optimizer**, **accessibility-specialist**

### Content & Marketing (4)
**content-marketing-specialist**, **visual-storyteller**, **technical-writer**, **seo-specialist**

### Code Management (3)
**refactoring-specialist**, **migration-specialist**, **localization-specialist**

### Business Intelligence (4)
**finance-tracker**, **growth-hacker**, **trend-researcher**, **trading-bot-strategist**

### Documentation (2)
**codebase-documenter**, **context7-docs-fetcher**

### Meta & Orchestration (4)
**workflow-coordinator**, **error-coordinator**, **memory-curator**, **memory-extractor**

---

## Multi-Agent Execution

**Sequential**: A → B → C (dependencies)
**Parallel**: (A + B + C) → D (independent)
**Hybrid**: (A → B) → (C + D + E) → F (mixed)

---

## Agent Coordination

- Unclear task → Request details
- Duplicate work → Check PROJECT_CONTEXT.md
- Missing artifact → Run dependency agent first
- Agent fails → Check error, decide retry vs manual
- Too slow → Identify parallelizable work
- PROJECT_CONTEXT.md > 1000 lines → Archive to PROJECT_ARCHIVE.md

---

## Artifact Management

```
/docs/api/          - API specs
/docs/database/     - Schemas
/docs/architecture/ - Design docs
/docs/design/       - UI/UX
/tests/fixtures/    - Test data
/config/templates/  - Config examples
```

---

## Validation & Error Recovery

**Scripts:**
- `~/.claude/scripts/check-tools.sh`
- `~/.claude/scripts/validate-coordination.sh`
- `~/.claude/scripts/validate-artifacts.sh`

**Tiers:**
- **Tier 1** (Transient): Auto-retry max 3x
- **Tier 2** (Validation): Auto-fix max 2x
- **Tier 3** (Blocker): Document and STOP

---

## Model Routing

| Model | Use For | Cost | Speed |
|-------|---------|------|-------|
| `haiku` | Simple fetch, docs, writing | Lowest | Fastest |
| `sonnet` | Code review, testing, implementation | Medium | Fast |
| `inherit` (Opus) | Architecture, security, complex | Highest | Thorough |

---

## 📚 Progressive Disclosure (Reference External Docs)

**To preserve context space, detailed information is in separate files:**

### Architecture & Design
- `~/.claude/agents/*.md` - All 47 agent definitions and capabilities
- `~/.claude/PROJECT_CONTEXT_TEMPLATE.md` - Multi-agent coordination template
- `~/.claude/MEMORY_WORKFLOW.md` - Detailed memory system workflow
- `~/.claude/MEMORY_IMPROVEMENTS.md` - Memory system enhancements (9 tools)

### Scripts & Tools
- `~/.claude/scripts/` - 20+ automation scripts (see Quick Tool Reference)
- `~/.claude/tests/` - Test suites including memory-system-tests.py
- `~/.claude/hooks/` - Automated verification hooks

### Memory System
- Start service: `cd ~/.claude/memory && docker compose up -d`
- Dashboard: `python3 ~/.claude/scripts/memory-dashboard.py`
- Tests: `python3 ~/.claude/tests/memory-system-tests.py`
- Full docs: `~/.claude/memory/README.md`

**When you need details, READ these files instead of asking user.**

---

## System Info

**WHY**: Autonomous software development with long-term memory
**WHAT**: 47 specialized agents + memory system + 20+ automation tools
**HOW**: Search memory → Plan → Delegate → Execute → Store

**Agents**: 47 specialized agents in `.claude/agents/`
**Template**: `~/.claude/PROJECT_CONTEXT_TEMPLATE.md`
**Version**: 4.0 (Planning-First + Memory Integration)
**Last Updated**: 2026-02-01

---

## Best Practices

- [Claude Code Docs](https://code.claude.com/docs/en/sub-agents)
- [Anthropic Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Multi-Agent Patterns](https://rlancemartin.github.io/2026/01/09/agent_design/)
- [VoltAgent Collection](https://github.com/VoltAgent/awesome-claude-code-subagents)
