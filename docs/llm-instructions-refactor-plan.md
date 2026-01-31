# CLAUDE.md Refactoring Plan - LLM Instructions Optimization

**Date**: 2025-11-03
**Agent**: refactoring-specialist
**Purpose**: Transform CLAUDE.md from hybrid human/LLM documentation into concise LLM-focused instructions

---

## Executive Summary

### Current State Analysis
- **File**: `/Users/h4ckm1n/.claude/CLAUDE.md`
- **Current Lines**: 608
- **Previous Reduction**: From 1,463 → 608 (manually, treated as human docs)
- **Target Lines**: ~500-600 (pure LLM instructions)
- **Key Issue**: Still contains human-facing content, verbose examples, external doc links

### Critical Understanding
**CLAUDE.md is NOT documentation for humans** - it is:
- System prompt loaded into every Claude Code conversation
- Decision logic for when/how to launch agents
- Concise patterns and rules for LLM execution
- Configuration for autonomous agent coordination

### Reduction Approach
**Total Potential Reduction**: ~230 lines
**Result**: 608 - 230 = ~378 lines (core LLM instructions)
**With preserved content**: ~500-550 lines (well under 800 target ✅)

---

## Section-by-Section Analysis

### Section 1: Header & Table of Contents (Lines 1-18)
**Type**: Navigation (human-focused)
**Current Lines**: 18
**Target Lines**: 5
**Reduction**: 13 lines

**Current Content**:
```markdown
# Claude Code Agent Ecosystem

**42 specialized agents for autonomous software development** | [Quick Start](#-quick-start-in-30-seconds) | [Agent Finder](#-agent-finder) | [Workflows](#-multi-agent-workflows)

---

## Table of Contents

1. [Quick Start (30 seconds)](#-quick-start-in-30-seconds)
2. [Agent Finder - Choose the Right Agent](#-agent-finder)
3. [When to Use Agents (Decision Tree)](#-when-to-use-agents-decision-tree)
...
```

**Issue**:
- Human-facing navigation aids (TOC, emoji anchors)
- Marketing tagline ("42 specialized agents")
- LLM doesn't need table of contents

**Recommended LLM Version**:
```markdown
# Claude Code Agent System

42 autonomous agents for software development. Coordinate via PROJECT_CONTEXT.md.

---
```

**Why**: LLM needs title and basic context only. No navigation needed.

---

### Section 2: Quick Start (Lines 21-50)
**Type**: Mixed (tutorial-style with some logic)
**Current Lines**: 30
**Target Lines**: 10
**Reduction**: 20 lines

**Current Content**:
```markdown
## ⚡ Quick Start (30 seconds)

### First Time Using Agents?

```
1. Type your task normally: "Build a user authentication system"
2. I'll automatically select and launch the right agents
3. All agents coordinate through PROJECT_CONTEXT.md in your project
4. Review the results, provide feedback, iterate
```

### The 3-Second Rule

**Before doing ANY task, ask:**
- Is this complex (3+ files)?
- Does it need expertise (API, security, performance)?
- Is it production code?

**YES to any?** → **USE AN AGENT** (I'll choose the right one)
**NO to all?** → I can work directly
```

**Issues**:
- Tutorial-style numbered instructions ("First Time Using Agents?")
- Human-facing phrases ("Type your task normally")
- Verbose decision logic that could be concise rules
- "3-Second Rule" branding (human-focused)

**Recommended LLM Version**:
```markdown
## Agent Usage Rules

**Use agent when task involves**:
- 3+ files or multiple modules
- Specialized expertise (API, security, performance, testing)
- Production code or deployment
- Architecture/design decisions
- ANY keyword triggers (see Agent Selection Keywords)

**Work directly when**:
- <10 lines, single file, trivial change
- No patterns/expertise needed
```

**Reduction Details**:
- Remove: Tutorial-style intro (8 lines)
- Remove: "First Time Using Agents?" section (4 lines)
- Remove: "3-Second Rule" branding (3 lines)
- Remove: "Most Common Agent Chains" table (moved to Quick Reference)
- Keep: Decision logic (condensed to 10 lines)

---

### Section 3: Agent Finder (Lines 53-112)
**Type**: Human browsing interface
**Current Lines**: 60
**Target Lines**: 15
**Reduction**: 45 lines

**Current Content**:
```markdown
## 🎯 Agent Finder

**Type what you need, find your agent instantly:**

### "I need to build..."

- **Backend API** → `backend-architect` or `api-designer`
- **Frontend UI** → `frontend-developer`
- **Mobile app** → `mobile-app-developer`
...

### "I need to fix/improve..."

- **Bug or error** → `debugger`
- **Legacy code** → `refactoring-specialist`
...
```

**Issues**:
- Human browsing categories ("I need to build...", "I need to fix...")
- Verbose navigation designed for users to scan
- Redundant with keyword auto-triggers section
- Repetitive "→" mappings that could be in a table

**Recommended LLM Version**:
```markdown
## Agent Selection Keywords

**Keyword triggers** (if user request contains these, use corresponding agent):

| Keywords | Agent |
|----------|-------|
| "API", "REST", "GraphQL", "endpoint" | api-designer |
| "frontend", "UI", "React", "Vue", "Angular" | frontend-developer |
| "backend", "server" | backend-architect |
| "database", "schema", "query" | database-optimizer |
| "test", "testing", "TDD", "E2E" | test-engineer |
| "deploy", "CI/CD", "Docker", "Kubernetes" | deployment-engineer |
| "slow", "optimize", "performance" | performance-profiler |
| "security", "vulnerability", "auth" | security-practice-reviewer |
| "refactor", "clean up", "technical debt" | refactoring-specialist |
| "bug", "error", "broken", "not working" | debugger |
| "mobile", "iOS", "Android" | mobile-app-developer |
| "AI", "ML", "LLM", "model" | ai-engineer |
```

**Reduction Details**:
- Remove: 6 category headers ("I need to build...", etc.) - 12 lines
- Remove: Verbose explanatory text - 8 lines
- Consolidate: All keyword mappings into single table - 60 → 15 lines

---

### Section 4: Decision Tree (Lines 115-172)
**Type**: Mixed (visual decision tree + keyword table)
**Current Lines**: 58
**Target Lines**: 25
**Reduction**: 33 lines

**Current Content**:
```markdown
## 📊 When to Use Agents (Decision Tree)

```
USER REQUEST RECEIVED
         |
         v
Does it involve code/infrastructure/design?
         |
    YES  |  NO → Answer directly
         v
Is it TRIVIAL? (<10 lines, single file, simple fix)
...
```

### Keyword Auto-Triggers
...
```

**Issues**:
- ASCII art decision tree (visual for humans, not executable)
- Verbose flow chart with many branches
- Keyword table duplicates Agent Finder section

**Recommended LLM Version**:
```markdown
## Agent Selection Logic

**Step 1: Check keyword triggers** (see Agent Selection Keywords table)

**Step 2: Apply complexity rules**:
- Trivial (<10 lines, single file, no expertise) → Work directly (OPTIONAL)
- Complex OR requires expertise → USE AGENT (MANDATORY)

**Mandatory agent triggers**:
- Architecture/design work
- API implementation
- Database work
- Security review
- Testing (unit/integration/E2E)
- Deployment/infrastructure
- Performance optimization
- Production code
- 3+ files

**Edge case**: Build/create/implement requests → Use domain-specific agent
```

**Reduction Details**:
- Remove: ASCII art decision tree (35 lines)
- Remove: Duplicate keyword table (already in Agent Finder) - 18 lines
- Keep: Condensed decision logic (25 lines)

---

### Section 5: All 42 Agents by Category (Lines 175-278)
**Type**: Essential LLM reference
**Current Lines**: 104
**Target Lines**: 104 (KEEP AS-IS)
**Reduction**: 0 lines

**Analysis**: This is **core LLM instruction** - Claude needs:
- All 42 agent names
- "When to Use" triggers
- "Key Capabilities" for selection logic

**No changes recommended** - this is exactly what LLM needs to select agents.

---

### Section 6: Multi-Agent Workflows (Lines 281-322)
**Type**: Mixed (patterns + link to detailed examples)
**Current Lines**: 42
**Target Lines**: 20
**Reduction**: 22 lines

**Current Content**:
```markdown
## 🔄 Multi-Agent Workflows

### Common Workflow Patterns

**Full-Stack Feature Development** (Sequential):
```
code-architect → database-optimizer → api-designer → backend-architect → frontend-developer → test-engineer
```

**Production Deployment** (Hybrid):
```
deployment-engineer → (security-practice-reviewer + observability-engineer) → validation
```
...

### When to Use Each Pattern

| Pattern | Use When | Example |
|---------|----------|---------|
| **Sequential Chain** | Each agent needs previous output | API design → Implementation → Testing |
| **Parallel Execution** | Agents work independently | Frontend + Backend + SEO |

**For detailed examples with step-by-step breakdowns**: See [Workflow Examples](docs/workflow-examples.md)
```

**Issues**:
- Link to external docs (Claude doesn't need to read workflow-examples.md)
- Verbose pattern explanations with redundant examples
- "When to Use" table duplicates agent descriptions

**Recommended LLM Version**:
```markdown
## Multi-Agent Execution Modes

**Sequential**: Launch agents in order when output dependencies exist
- Pattern: A → B → C (B needs A's output, C needs B's output)
- Example: api-designer → backend-architect → test-engineer

**Parallel**: Launch agents simultaneously when work is independent
- Pattern: (A + B + C) → D (A/B/C work independently, D integrates)
- Example: (frontend-developer + backend-architect + seo-specialist)

**Hybrid**: Combine sequential phases with parallel execution
- Pattern: (A → B) → (C + D + E) → F
- Example: Architecture phase → Implementation (parallel) → Testing

**Selection logic**:
- Backend needs DB schema → Sequential (database-optimizer → backend-architect)
- Frontend needs API spec → Sequential (api-designer → frontend-developer)
- Frontend + Backend with mocks → Parallel (no dependencies)
- Multiple reviews → Parallel (security + performance + code-quality)
```

**Reduction Details**:
- Remove: Link to workflow-examples.md (2 lines)
- Remove: "When to Use" table (8 lines)
- Remove: Verbose pattern descriptions (12 lines)
- Keep: Concise execution mode rules (20 lines)

---

### Section 7: Troubleshooting Guide (Lines 325-364)
**Type**: Human guide with examples
**Current Lines**: 40
**Target Lines**: 12
**Reduction**: 28 lines

**Current Content**:
```markdown
## 🔧 Troubleshooting Guide

### Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| **Agent didn't understand** | Provide file paths, error messages, specific requirements |
| **Agents duplicating work** | Check PROJECT_CONTEXT.md first, assign clear boundaries |
...

### Common Issues

**Issue**: Agent asks for clarification
```
❌ BAD:  "Fix the bug"
✅ GOOD: "Fix the TypeError in src/auth.ts:42 where user.email is undefined"
```

**For comprehensive troubleshooting**: See [Detailed Troubleshooting Guide](docs/troubleshooting-detailed.md)
```

**Issues**:
- Human-facing examples (❌ BAD vs ✅ GOOD)
- Link to external troubleshooting-detailed.md
- Tutorial-style issue walkthroughs
- "Quick Fixes" table could be decision rules

**Recommended LLM Version**:
```markdown
## Agent Coordination Rules

**If agent reports unclear task**: Request file paths, error messages, acceptance criteria from user
**If agents duplicate work**: Check PROJECT_CONTEXT.md, assign explicit file/domain boundaries
**If agent needs missing artifact**: Switch to sequential, run dependency agent first
**If agent fails mid-task**: Read error, check git status, decide re-run vs manual fix
**If workflow too slow**: Identify parallelizable work, consider mocks for unblocking
**If file conflicts**: Review git diff, check PROJECT_CONTEXT.md reasoning, trust last agent
**If wrong agent chosen**: Check "When to Use" descriptions, use keyword triggers
**If PROJECT_CONTEXT.md exceeds 1000 lines**: Archive old activity to PROJECT_ARCHIVE.md
```

**Reduction Details**:
- Remove: Quick Fixes table (redundant, 16 lines)
- Remove: Common Issues examples (BAD vs GOOD, 12 lines)
- Remove: Link to troubleshooting-detailed.md (2 lines)
- Keep: Concise decision rules (12 lines)

---

### Section 8: Advanced Coordination (Lines 367-408)
**Type**: Mixed (patterns + artifact structure)
**Current Lines**: 42
**Target Lines**: 25
**Reduction**: 17 lines

**Current Content**:
```markdown
## 🚀 Advanced Coordination

### Agent Communication Patterns

| Pattern | When to Use | Structure |
|---------|-------------|-----------|
| **Sequential Chain** | Each agent needs previous output | A → B → C → D |
| **Parallel Execution** | Independent work areas | (A + B + C) → D |

### Artifact Management

**Standard Locations**:
```
project-root/
├── docs/
│   ├── api/              # OpenAPI specs
│   ├── database/         # Schema, ERD
...
```

**For detailed coordination patterns**: See [Coordination Guide](docs/coordination-improvements.md)
```

**Issues**:
- Link to coordination-improvements.md
- Patterns table duplicates Multi-Agent Workflows section
- Verbose artifact directory structure

**Recommended LLM Version**:
```markdown
## Artifact Management

**Standard locations** (agents read/write artifacts here):
```
/docs/api/              - API specs (api-designer → frontend/mobile/tester)
/docs/database/         - Schema, ERD (database-optimizer → backend)
/docs/architecture/     - System design, ADRs (code-architect → all)
/docs/design/           - UI/UX, mockups (ui-designer → frontend)
/tests/fixtures/        - Test data (test-engineer → all)
/config/templates/      - Config examples (deployment-engineer → all)
```

**Naming conventions**:
- Version in name: `/docs/api/auth-v2.yaml`
- Date in name: `/docs/database/schema-2025-11.sql`
- Quantity in name: `/tests/fixtures/users-10-sample.json`

**PROJECT_CONTEXT.md sections agents must update**:
- Agent Activity Log (after completing work)
- Artifacts for Other Agents (when creating files for next agent)
- Active Blockers (when blocked on dependencies)
- Shared Decisions (when making architectural choices)
```

**Reduction Details**:
- Remove: Communication Patterns table (duplicates, 8 lines)
- Remove: Link to coordination-improvements.md (2 lines)
- Remove: PROJECT_CONTEXT.md best practices table (7 lines, move to artifact section)
- Condense: Artifact structure to essentials (42 → 25 lines)

---

### Section 9: Error Recovery & Validation (Lines 411-451)
**Type**: Validation protocol (LLM needs this)
**Current Lines**: 41
**Target Lines**: 30
**Reduction**: 11 lines

**Current Content**:
```markdown
## 🛡️ Error Recovery & Validation

### Validation Scripts

**Location**: `~/.claude/scripts/`

| Script | Purpose | Usage |
|--------|---------|-------|
| `validate-coordination.sh` | Check PROJECT_CONTEXT.md health | Before starting work |
| `validate-artifacts.sh` | Verify artifacts exist | After completing work |

### Error Recovery Protocol (All Agents)

**3-Tier System**:

| Tier | For | Action |
|------|-----|--------|
| **Tier 1** | Transient errors | Auto-retry (max 3, exponential backoff) |
| **Tier 2** | Validation failures | Auto-fix and re-validate (max 2) |
| **Tier 3** | Permanent blockers | Document and STOP |

**For comprehensive validation documentation**: See [Error Recovery Guide](docs/execute-prp-enhancement.md)
```

**Issues**:
- Link to execute-prp-enhancement.md (could be removed or condensed)
- Verbose table explanations

**Recommended LLM Version**:
```markdown
## Validation & Error Recovery

**Validation scripts** (run automatically in execute-prp):
- `~/.claude/scripts/check-tools.sh` - Verify tools available (Phase 0)
- `~/.claude/scripts/validate-coordination.sh` - Check PROJECT_CONTEXT.md health (Phase 0)
- `~/.claude/scripts/validate-artifacts.sh` - Verify artifacts exist (after each agent)

**Error recovery tiers** (agents must follow):
- **Tier 1** (Transient): Network errors, file locks → Auto-retry max 3x with backoff
- **Tier 2** (Validation): Test failures, linting errors → Auto-fix and re-validate max 2x
- **Tier 3** (Blocker): Missing dependencies, tool unavailable → Document in PROJECT_CONTEXT.md and STOP (never silently fail)

**Agents must update PROJECT_CONTEXT.md**:
- Validation Timestamps (pre/post-task results)
- Error Recovery Log (how errors were handled)
- Coordination Metrics (handoff success rate, retry rate)
```

**Reduction Details**:
- Remove: Link to execute-prp-enhancement.md (1 line)
- Condense: Tables to bullet lists (10 lines saved)

---

### Section 10: Quick Reference (Lines 454-530)
**Type**: Mixed (LLM needs some, humans need some)
**Current Lines**: 77
**Target Lines**: 40
**Reduction**: 37 lines

**Current Content**:
```markdown
## 📋 Quick Reference

### Invoking Agents

```markdown
SINGLE AGENT:
"I'll use the Task tool with subagent_type='backend-architect' to build the API"

SEQUENTIAL:
"I'll run these agents in sequence:
1. api-designer - create spec
2. backend-architect - implement API
3. api-tester - test endpoints"
```

### Agent Selection Cheat Sheet

| Task Type | First Choice | Alternative | Use Both When |
|-----------|-------------|-------------|---------------|
| New API | api-designer | backend-architect | Design first, then implement |
| Fix bug | debugger | refactoring-specialist | Bug fix + code improvement |
...

### Common Agent Chains (Copy-Paste Ready)

```
AUTHENTICATION SYSTEM:
code-architect → database-optimizer → backend-architect → security-practice-reviewer → frontend-developer → test-engineer
...
```

### PROJECT_CONTEXT.md Quick Commands

```bash
# Initialize PROJECT_CONTEXT.md
cp ~/.claude/PROJECT_CONTEXT_TEMPLATE.md ./PROJECT_CONTEXT.md
```
```

**Issues**:
- "Invoking Agents" section is verbose example of what Claude already does
- Some agent chains are useful, but many are obvious
- Bash commands are useful (keep)

**Recommended LLM Version**:
```markdown
## Quick Reference

### Common Agent Chains

**Authentication**: code-architect → database-optimizer → backend-architect → security-practice-reviewer → frontend-developer → test-engineer
**API Development**: api-designer → backend-architect → api-tester → codebase-documenter
**Frontend Feature**: ui-designer → frontend-developer → accessibility-specialist → test-engineer
**Production Deploy**: deployment-engineer → security-practice-reviewer → observability-engineer
**Code Quality**: (refactoring-specialist + security-practice-reviewer + performance-profiler) → test-engineer → code-reviewer
**AI Feature**: ai-engineer → ai-prompt-engineer → backend-architect → frontend-developer → test-engineer

### Agent Selection Disambiguations

| Confused About | Use | Not | Reason |
|----------------|-----|-----|--------|
| API implementation | backend-architect | api-designer | Designer creates specs, architect implements |
| API documentation | api-designer | technical-writer | Designer knows API patterns |
| UI implementation | frontend-developer | ui-designer | Designer creates mockups, developer codes |
| Security review | security-practice-reviewer | code-reviewer | Security specialist knows vulnerabilities |
| Code quality | code-reviewer | refactoring-specialist | Reviewer audits, refactorer fixes |

### PROJECT_CONTEXT.md Commands

```bash
# Initialize
cp ~/.claude/PROJECT_CONTEXT_TEMPLATE.md ./PROJECT_CONTEXT.md

# View recent activity
grep -A 10 "Agent Activity Log" PROJECT_CONTEXT.md | head -20

# Check blockers
grep -A 5 "Blockers" PROJECT_CONTEXT.md
```
```

**Reduction Details**:
- Remove: "Invoking Agents" verbose examples (15 lines)
- Condense: Agent chains to one-liners (reduce from 25 to 8 lines)
- Keep: Agent Selection table (useful disambiguations)
- Keep: Bash commands (essential reference)
- Total reduction: 77 → 40 lines

---

### Section 11: Additional Resources (Lines 533-553)
**Type**: Human documentation links
**Current Lines**: 21
**Target Lines**: 5
**Reduction**: 16 lines

**Current Content**:
```markdown
## 📖 Additional Resources

### Files in This Repository

- **CLAUDE.md** (this file) - Main documentation
- **PROJECT_CONTEXT_TEMPLATE.md** - Template for agent coordination
- **agents/** - 42 individual agent definition files

### Commands

```bash
/help              # Claude Code documentation
/memory            # Persist project context across sessions
```

### Getting Help

- **Issues**: https://github.com/anthropics/claude-code/issues
- **Agent files**: `.claude/agents/`
- **Ask me**: I'm here to help! Just ask: "Which agent should I use for X?"

---

**Version**: 2.1
**Last Updated**: 2025-11-03
**Total Agents**: 42
**Maintained by**: Claude Code Team
**Changes**: Refactored for conciseness - detailed examples in separate docs
```

**Issues**:
- Human-facing help links (GitHub issues, "Ask me")
- Version/maintenance footer (not needed by LLM)
- Verbose resource descriptions

**Recommended LLM Version**:
```markdown
## System Info

**Agents**: 42 specialized agents in `.claude/agents/`
**Template**: `~/.claude/PROJECT_CONTEXT_TEMPLATE.md`
**Version**: 2.2 (LLM-optimized)
```

**Reduction Details**:
- Remove: GitHub links, "Getting Help" (10 lines)
- Remove: Verbose file descriptions (6 lines)
- Keep: Essential system paths (5 lines)

---

### Section 12: Agent Definition Schema (Lines 563-608)
**Type**: Technical reference (LLM needs for agent metadata)
**Current Lines**: 46
**Target Lines**: 35
**Reduction**: 11 lines

**Current Content**:
```markdown
## Agent Definition Schema (For Reference)

Each agent is defined in `.claude/agents/[agent-name].md`:

```yaml
---
name: agent-name
description: When to use this agent
tools: Read, Write, Bash, etc.
model: inherit
color: blue
---
[Agent instructions in markdown]
```

**Tool Options**: Read, Write, Edit, MultiEdit, Bash, Grep, Glob, WebSearch, WebFetch, Task, All tools
**Models**: inherit, haiku, sonnet, opus
**Colors**: blue, green, purple, orange, red, yellow, pink, cyan, violet, slate

### Complete Agent Metadata

| Agent | Tools | Model | Color |
|-------|-------|-------|-------|
| code-architect | All tools | inherit | blue |
| backend-architect | Write, Read, MultiEdit, Bash, Grep | inherit | green |
...
| [... 22 more agents ...] | See full table in original doc | inherit | various |
```

**Issues**:
- Incomplete agent metadata table (shows 20, says "22 more agents")
- Verbose YAML schema explanation

**Recommended LLM Version**:
```markdown
## Agent Metadata Reference

**Agent definition structure** (`.claude/agents/[name].md`):
- **tools**: Read, Write, Edit, MultiEdit, Bash, Grep, Glob, WebSearch, WebFetch, Task, All tools
- **model**: inherit, haiku, sonnet, opus
- **color**: blue, green, purple, orange, red, yellow, pink, cyan, violet, slate

**Key agent tool configurations**:
- code-architect: All tools (comprehensive planning)
- backend-architect: Write, Read, MultiEdit, Bash, Grep (implementation)
- security-practice-reviewer: Read, Grep, Glob, Bash, WebSearch (audit)
- test-engineer: Bash, Read, Write, Grep, MultiEdit (testing)
- deployment-engineer: Write, Read, MultiEdit, Bash, Grep (deployment)
- debugger: Read, Edit, Bash, Grep, Glob (debugging)

**For full metadata**: See individual agent files in `.claude/agents/`
```

**Reduction Details**:
- Remove: Incomplete agent metadata table (15 lines)
- Condense: YAML schema to bullet list (5 lines saved)
- Add: Key agent tool highlights for common selections
- Total: 46 → 35 lines

---

## Human Documentation to Remove/Extract

### External Documentation Links (Remove from CLAUDE.md)

Claude doesn't need to read these files - they're for humans:

1. **Line 321**: `**For detailed examples with step-by-step breakdowns**: See [Workflow Examples](docs/workflow-examples.md)`
   - **Action**: Remove link (Claude doesn't need 60-line workflow walkthroughs)
   - **File exists**: `/Users/h4ckm1n/.claude/docs/workflow-examples.md` (307 lines)
   - **Keep file**: Yes (useful for humans browsing)

2. **Line 364**: `**For comprehensive troubleshooting**: See [Detailed Troubleshooting Guide](docs/troubleshooting-detailed.md)`
   - **Action**: Remove link (Claude doesn't need step-by-step human guides)
   - **File exists**: `/Users/h4ckm1n/.claude/docs/troubleshooting-detailed.md` (343 lines)
   - **Keep file**: Yes (useful for humans)

3. **Line 407**: `**For detailed coordination patterns**: See [Coordination Guide](docs/coordination-improvements.md)`
   - **Action**: Remove link
   - **File exists**: `/Users/h4ckm1n/.claude/docs/coordination-improvements.md` (10KB)
   - **Keep file**: Yes

4. **Line 450**: `**For comprehensive validation documentation**: See [Error Recovery Guide](docs/execute-prp-enhancement.md)`
   - **Action**: Remove link
   - **File exists**: `/Users/h4ckm1n/.claude/docs/execute-prp-enhancement.md` (12KB)
   - **Keep file**: Yes

**Total link removals**: 4 lines

### Human-Facing Phrases to Remove

1. **Lines 23-30**: "First Time Using Agents?" tutorial
2. **Line 32**: "The 3-Second Rule" branding
3. **Line 55**: "Type what you need, find your agent instantly:"
4. **Lines 57-111**: "I need to..." category structure
5. **Line 343-346**: ❌ BAD vs ✅ GOOD examples
6. **Line 552**: "Ask me: I'm here to help!"

**Pattern to eliminate**: Tutorial-style, first-person, marketing language

---

## Sections to Preserve As-Is

### 1. All 42 Agents by Category (Lines 175-278, 104 lines)
**Why**: Core LLM reference for agent selection
- Agent names, triggers, capabilities essential for Claude to choose correctly
- No reduction possible without losing functionality

### 2. Keyword Auto-Triggers Table (Lines 154-172, 19 lines)
**Why**: Executable decision logic
- Direct keyword → agent mappings Claude uses for auto-selection
- Already concise, no verbose explanations

### 3. Agent Metadata (Lines 584-608, partial)
**Why**: Technical configuration reference
- Tool/model/color info needed for agent invocation
- Can condense incomplete table, but need to preserve core metadata

---

## Reduction Strategy Summary

### Total Line Reduction Breakdown

| Section | Current | Target | Savings | Priority |
|---------|---------|--------|---------|----------|
| Header & TOC | 18 | 5 | 13 | HIGH |
| Quick Start | 30 | 10 | 20 | HIGH |
| Agent Finder | 60 | 15 | 45 | HIGH |
| Decision Tree | 58 | 25 | 33 | HIGH |
| **All 42 Agents** | **104** | **104** | **0** | **PRESERVE** |
| Multi-Agent Workflows | 42 | 20 | 22 | MEDIUM |
| Troubleshooting | 40 | 12 | 28 | HIGH |
| Advanced Coordination | 42 | 25 | 17 | MEDIUM |
| Error Recovery | 41 | 30 | 11 | LOW |
| Quick Reference | 77 | 40 | 37 | MEDIUM |
| Additional Resources | 21 | 5 | 16 | HIGH |
| Agent Schema | 46 | 35 | 11 | LOW |
| **External Links** | **4** | **0** | **4** | **HIGH** |
| **TOTAL** | **583** | **326** | **257** | - |

**Note**: Total current lines (583) excludes the 104 lines of agent tables that must be preserved.

### Final Line Count Calculation

**Current CLAUDE.md**: 608 lines
**Preserved content** (All 42 Agents): 104 lines
**Reducible content**: 608 - 104 = 504 lines
**After reduction**: 326 lines (concise LLM instructions)
**Final total**: 104 + 326 = **430 lines**

**Result**: 430 lines (well under 800 target ✅, 71% reduction from 1,463 original)

---

## Implementation Strategy

### Phase 1: Analysis (COMPLETE)
- ✅ Read CLAUDE.md completely (608 lines)
- ✅ Identify LLM instructions vs human documentation
- ✅ Map specific line ranges for each section
- ✅ Calculate reduction targets (257 lines removable)
- ✅ Create this refactoring plan

### Phase 2: Content Evaluation (Next Agent)
**Agent**: technical-writer
**Task**: Evaluate if any human-facing content should be extracted or just removed
**Decision Points**:
1. Are workflow-examples.md and troubleshooting-detailed.md sufficient for human reference?
2. Should any removed content be documented elsewhere?
3. Are there any LLM instructions hidden in verbose sections that must be preserved?

### Phase 3: Refactoring Implementation (After Evaluation)
**Agent**: refactoring-specialist (second pass)
**Task**: Apply reductions to CLAUDE.md
**Steps**:
1. Remove header/TOC navigation (save 13 lines)
2. Condense Quick Start to rules (save 20 lines)
3. Replace Agent Finder with keyword table (save 45 lines)
4. Condense Decision Tree to logic (save 33 lines)
5. **PRESERVE All 42 Agents section** (0 line change)
6. Condense Multi-Agent Workflows (save 22 lines)
7. Replace Troubleshooting with rules (save 28 lines)
8. Condense Advanced Coordination (save 17 lines)
9. Streamline Error Recovery (save 11 lines)
10. Reduce Quick Reference (save 37 lines)
11. Minimize Additional Resources (save 16 lines)
12. Condense Agent Schema (save 11 lines)
13. Remove all 4 external doc links (save 4 lines)

**Validation after each step**:
- Run `grep -c "^##" CLAUDE.md` (verify section structure)
- Run `wc -l CLAUDE.md` (track line reduction)
- Search for agent names (verify all 42 still present)

### Phase 4: Validation (Final)
**Agent**: code-reviewer
**Task**: Verify no LLM instruction loss
**Checks**:
- ✅ All 42 agents documented
- ✅ Agent selection logic preserved
- ✅ Keyword triggers intact
- ✅ Execution mode rules clear
- ✅ Artifact management instructions present
- ✅ Validation protocol documented
- ✅ No human-facing prose remaining
- ✅ No external documentation links
- ✅ Final line count: 400-500 lines

---

## LLM Instruction Preservation Checklist

**Critical elements that MUST be preserved**:

- [x] All 42 agent names, "When to Use", "Key Capabilities"
- [x] Keyword trigger mappings (API → api-designer, etc.)
- [x] Agent usage rules (when to use agent vs work directly)
- [x] Sequential vs Parallel execution logic
- [x] Artifact standard locations and naming conventions
- [x] PROJECT_CONTEXT.md update requirements
- [x] Validation script paths and usage
- [x] Error recovery tier system
- [x] Common agent chains (authentication, API, deploy, etc.)
- [x] Agent tool/model/color metadata
- [x] Coordination rules (what to do when agents conflict, fail, etc.)

**What can be removed without impact**:

- [x] Tutorial-style introductions ("First Time Using Agents?")
- [x] Human-facing navigation (TOC, emoji anchors)
- [x] Verbose examples (❌ BAD vs ✅ GOOD)
- [x] External documentation links (Claude doesn't read them)
- [x] Marketing language ("42 specialized agents for...")
- [x] Explanatory prose ("Type what you need...")
- [x] Redundant tables (when content duplicates other sections)
- [x] ASCII art diagrams (decision tree flowchart)
- [x] Version/maintenance footer information

---

## Success Metrics

### Before (Current State)
- **Lines**: 608
- **LLM Focus**: Medium (still has human-facing content)
- **External Links**: 4 links to human docs
- **Redundancy**: High (Agent Finder + Decision Tree + Workflows all explain similar concepts)
- **Verbosity**: High (tutorial-style, examples for humans)

### After (Target)
- **Lines**: 430 (71% reduction from original 1,463)
- **LLM Focus**: High (pure decision logic and patterns)
- **External Links**: 0 (Claude doesn't need them)
- **Redundancy**: Low (each section serves distinct LLM purpose)
- **Verbosity**: Low (concise rules and executable instructions)

### Validation Criteria
- [ ] All 42 agents still documented with selection criteria
- [ ] Keyword triggers preserved for auto-agent-selection
- [ ] Execution mode logic (sequential/parallel/hybrid) clear
- [ ] Artifact management instructions complete
- [ ] Coordination rules actionable (if X, then Y)
- [ ] No tutorial-style or human-browsing content
- [ ] No links to external documentation files
- [ ] Line count: 400-500 (under 800 target)

---

## Risk Assessment

### Low Risk Changes (Safe to implement immediately)
1. Remove header/TOC (Claude doesn't use navigation)
2. Remove external documentation links (Claude doesn't read those files)
3. Remove human-facing phrases ("Type what you need...")
4. Remove redundant sections (Agent Finder duplicates keywords)
5. Remove verbose examples (❌ BAD vs ✅ GOOD)

### Medium Risk Changes (Verify with technical-writer)
1. Condensing Multi-Agent Workflows (ensure patterns remain clear)
2. Replacing Troubleshooting with rules (ensure all scenarios covered)
3. Condensing Quick Reference (ensure essential chains preserved)

### High Risk Changes (Must preserve carefully)
1. Agent Selection Logic (decision tree → concise rules)
   - **Risk**: Claude might miss edge cases
   - **Mitigation**: Preserve all mandatory triggers, keyword mappings
2. Artifact Management (condensing locations/conventions)
   - **Risk**: Agents might create files in wrong locations
   - **Mitigation**: Keep all standard paths, just remove verbose explanations

**Zero Risk Areas** (never modify):
- All 42 Agents by Category (lines 175-278)
- Agent metadata (tools, models, colors)

---

## Next Steps

1. **technical-writer** reviews this plan and confirms:
   - Human content (workflow-examples.md, troubleshooting-detailed.md) is sufficient
   - No additional extraction needed
   - All removals are safe

2. **refactoring-specialist** (second pass) implements reductions:
   - Apply all "Low Risk" changes immediately
   - Apply "Medium Risk" changes with validation after each
   - Apply "High Risk" changes carefully with checkpoint validations

3. **code-reviewer** validates final CLAUDE.md:
   - No LLM instruction loss
   - All agent selection logic intact
   - Line count target met (400-500 lines)
   - No human-facing content remains

---

## Artifact Information

**Created**: `/Users/h4ckm1n/.claude/docs/llm-instructions-refactor-plan.md`
**For Agents**: technical-writer (evaluation) → refactoring-specialist (implementation) → code-reviewer (validation)
**Purpose**: Comprehensive refactoring plan to transform CLAUDE.md into concise LLM instructions
**Format**: Markdown with line-by-line analysis and reduction strategy
**Status**: COMPLETE - Ready for technical-writer evaluation

---

**END OF REFACTORING PLAN**
