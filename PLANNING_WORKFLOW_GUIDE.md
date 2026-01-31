# Planning-First Workflow Guide

**Version**: 4.0
**Date**: 2026-02-01
**Status**: ✅ Production Ready

---

## 📖 Overview

This guide documents the enhanced planning-first workflow integrated into CLAUDE.md v4.0, based on comprehensive research of 2026 industry best practices.

---

## 🔍 Research Summary

### Sources Analyzed

1. **HumanLayer Blog** - "Writing a Good CLAUDE.md"
   - LLMs can follow 150-200 instructions consistently
   - Keep CLAUDE.md under 300 lines (ideally <60)
   - Use WHY, WHAT, HOW structure
   - Progressive disclosure strategy

2. **ClaudeLog** - "Plan Mode Mechanics"
   - Plan mode separates research from execution
   - 76% token reduction with Opus 4.5 planning
   - Available tools: Read, LS, Glob, Grep, WebFetch, WebSearch
   - Restricted tools: Edit, Write, Bash, state-modifying MCP

3. **GitHub Community** - Sub-Agent Delegation Setup (tomas-rampas)
   - Specialized agent architecture: Plan → Read → Make → Test → Review
   - "NEVER execute directly unless told" - always delegate
   - Cost optimization: Opus for planning, Haiku for lightweight, Sonnet for dev

4. **Dometrain Blog** - Creating the Perfect CLAUDE.md
   - CLAUDE.md is "persistent memory" for agents
   - Document workflows, commands, standards, terminology
   - Reference external files to preserve context
   - Treat as living documentation

### Key Research Findings

**Planning Benefits:**
- 76% reduction in token usage (Opus 4.5 study)
- Better results through deliberation before action
- Prevents costly mistakes by getting approval first
- Enables systematic problem-solving

**Memory Integration:**
- Searching memory BEFORE planning builds on past knowledge
- Avoids re-solving solved problems
- Ensures consistency with previous decisions
- Compounds knowledge over time

**Progressive Disclosure:**
- Reference external docs instead of inline examples
- Keeps context focused on current task
- Prevents bloat that causes LLMs to ignore instructions
- Allows deep-dive when needed

---

## 🎯 The Enhanced Workflow

### Core Pattern

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│  1. SEARCH MEMORY     → Leverage past knowledge         │
│  2. PLAN              → Think before acting             │
│  3. DELEGATE          → Route to specialists            │
│  4. EXECUTE           → Implement systematically        │
│  5. STORE             → Save for future                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Phase 1: Memory Search (MANDATORY)

**Always starts with:**
```javascript
search_memory(query="[task keywords]", limit=10)
get_context(project="[project name]", hours=24)
// Review <system-reminder> suggestions
```

**Benefits:**
- Finds existing solutions (avoid reinventing)
- Discovers related decisions (maintain consistency)
- Identifies patterns to reuse
- Surfaces known issues to avoid

**Example:**
```
User: "Add authentication to the API"

Claude: [Calls search_memory("API authentication oauth jwt")]
Result: Found 3 memories:
  1. "Decision: Use JWT for API auth" (019c14f8...)
  2. "Pattern: JWT refresh token implementation" (019c15a2...)
  3. "Error: JWT expiry bug fix" (019c1603...)

Claude: [Builds on existing JWT decision instead of choosing new approach]
```

---

### Phase 2: Planning (MANDATORY for Complex Tasks)

**When to use EnterPlanMode:**

✅ **YES - Use EnterPlanMode:**
- New features affecting 3+ files
- Architecture/design decisions
- Multiple valid implementation approaches
- Refactoring or code modifications
- Tasks where you'd ask user for clarification
- Unclear requirements needing exploration

❌ **NO - Work Directly:**
- Single file, <10 lines
- Bug fix with known solution from memory
- Trivial changes (typos, docs)

**Planning Workflow:**

**Step 1: Enter plan mode**
```javascript
EnterPlanMode()
```

**Step 2: Research Phase (Read-only)**
```javascript
// Read existing code
Read("path/to/file.ts")
Glob("**/*.ts")
Grep("pattern", "src/")

// Research external knowledge
WebFetch("https://docs.example.com/api")
WebSearch("best practices for X")

// Use specialized agents for analysis
Task(subagent_type="Explore", prompt="How does authentication work in this codebase?")
```

**Step 3: Create Structured Plan**
```markdown
## Analysis
### Current State
- What exists now
- What's working
- What's missing

### Requirements
- What user asked for
- Implicit requirements
- Constraints and limitations

### Past Solutions (from memory)
- Memory ID: 019c14f8 - Similar solution for feature X
- Key insight: Use pattern Y instead of Z

## Approach Options

### Option 1: [Name]
**Pros:**
- Benefit 1
- Benefit 2

**Cons:**
- Drawback 1
- Drawback 2

### Option 2: [Name]
**Pros:** ...
**Cons:** ...

### RECOMMENDED: Option 1
**Rationale:**
- Builds on existing pattern from memory 019c14f8
- Consistent with past decision about architecture
- Lower risk because it's been validated before

## Implementation Steps
1. Modify `src/auth/jwt.ts` to add refresh logic
2. Update `src/middleware/auth.ts` to validate refresh tokens
3. Create migration for refresh_tokens table
4. Add tests in `tests/auth.test.ts`
5. Update API documentation

## Delegation Strategy
- code-architect: Review overall design
- database-optimizer: Design refresh_tokens schema
- backend-architect: Implement JWT refresh logic
- security-practice-reviewer: Audit security implications
- test-engineer: Create comprehensive test suite

## Success Criteria
- Refresh tokens work with 24h expiry
- No security vulnerabilities introduced
- All tests pass
- Documentation updated
```

**Step 4: Exit plan mode and get approval**
```javascript
ExitPlanMode()
// User reviews plan and approves
```

---

### Phase 3: Delegation (Agent Routing)

**Delegation Principles (from research):**

1. **NEVER execute directly unless told** - Always route to specialists
2. **Use specialized agents** - Leverage domain expertise
3. **Optimize model usage** - Opus for architecture, Sonnet for dev, Haiku for lightweight

**Standard Delegation Chains:**

**New Feature:**
```
code-architect (design)
  ↓
backend-architect (implement)
  ↓
test-engineer (validate)
  ↓
code-reviewer (review)
```

**Bug Fix:**
```
debugger (investigate)
  ↓
domain-agent (fix)
  ↓
test-engineer (regression test)
```

**Security Audit:**
```
security-practice-reviewer (scan)
  ↓
backend-architect (fix vulnerabilities)
  ↓
test-engineer (validate)
  ↓
code-reviewer (final check)
```

**Delegation Code Example:**
```javascript
// Sequential delegation
Task(subagent_type="code-architect",
     prompt="Design refresh token architecture",
     model="inherit")  // Use Opus for architecture

// Wait for completion, then next agent
Task(subagent_type="backend-architect",
     prompt="Implement refresh token logic based on architecture",
     model="sonnet")  // Use Sonnet for implementation

// Parallel delegation (independent work)
[
  Task(subagent_type="test-engineer", ...),
  Task(subagent_type="security-practice-reviewer", ...),
  Task(subagent_type="code-reviewer", ...)
]
```

---

### Phase 4: Execution (Agent Work)

**Agents execute the plan systematically:**

1. **Read plan artifacts** - Agents access shared plan documents
2. **Follow implementation steps** - Execute in defined order
3. **Coordinate via PROJECT_CONTEXT.md** - Log activity and artifacts
4. **Validate incrementally** - Test after each major change

**Example Execution Flow:**
```
[code-architect completes design]
  → Writes: /docs/architecture/refresh-tokens.md
  → Updates: PROJECT_CONTEXT.md with design decisions

[backend-architect reads architecture doc]
  → Implements: src/auth/jwt-refresh.ts
  → Updates: PROJECT_CONTEXT.md with implementation notes

[test-engineer reads implementation]
  → Creates: tests/auth/jwt-refresh.test.ts
  → Validates: All tests pass
  → Updates: PROJECT_CONTEXT.md with test results
```

---

### Phase 5: Storage (MANDATORY)

**After work completes, store results:**

```javascript
// Store architecture decisions
store_memory({
  type: "decision",
  content: "Use JWT refresh tokens with 24h expiry for API authentication",
  decision: "Chose refresh token pattern over short-lived tokens",
  rationale: "Better UX (users stay logged in), more secure (can revoke tokens), industry standard pattern",
  alternatives: ["Short-lived tokens only", "Session-based auth", "OAuth2 flow"],
  tags: ["jwt", "authentication", "api", "security", "decision"],
  project: "api-project"
})

// Store implementation patterns
store_memory({
  type: "pattern",
  content: "JWT refresh token implementation pattern: Store refresh tokens in DB with user_id, token hash, expiry, and revoked flag. Access token in memory only. Refresh endpoint validates refresh token and issues new access token. Middleware checks access token first, falls back to refresh if expired.",
  tags: ["jwt", "refresh-token", "pattern", "authentication", "api"],
  project: "api-project"
})

// Link to original decision
link_memories(
  source_id="019c14f8...",  // Original auth decision
  target_id="019c1603...",  // New refresh token implementation
  relation="builds_on"
)
```

**Why storage is critical:**
- Future sessions avoid re-planning same feature
- Patterns become reusable templates
- Decisions maintain consistency
- Knowledge compounds over time

---

## 📊 Benefits Quantified

Based on research and implementation:

**Token Efficiency:**
- 76% reduction in token usage (Opus 4.5 planning study)
- Reduced context bloat from 1231 lines → 404 lines CLAUDE.md
- Progressive disclosure saves ~50KB per session

**Quality Improvements:**
- Fewer mistakes from deliberation before action
- Consistency through memory integration
- Better architecture from specialized agents
- Comprehensive testing through systematic delegation

**Time Savings:**
- Avoid re-solving solved problems (memory search)
- Faster implementation with clear plans
- Reduced rework from approval before coding
- Automated validation through agent chains

---

## 🎓 Best Practices

### Planning Best Practices

**Keep plans concise:**
- 1-2 pages maximum
- Focus on WHAT and WHY, not HOW (agents handle HOW)
- Reference files instead of copying code
- Use bullet points, not paragraphs

**Structure plans clearly:**
- Analysis → Options → Recommendation → Steps → Delegation
- Include past solutions from memory search
- Explain rationale for chosen approach
- Define success criteria

**Get user buy-in:**
- Present plan before executing
- Use AskUserQuestion for ambiguity
- Acknowledge trade-offs explicitly
- Explain why option was chosen

### Delegation Best Practices

**Choose right specialist:**
- Match task to agent expertise
- Use keyword triggers for routing
- Consider model costs (Opus vs Sonnet vs Haiku)
- Chain agents for complex workflows

**Coordinate effectively:**
- Sequential: When outputs depend on each other
- Parallel: When work is independent
- Hybrid: Mix of both for complex features
- Document handoffs in PROJECT_CONTEXT.md

**Validate systematically:**
- Test after each major change
- Security review for auth/data changes
- Code review before merging
- Performance profiling for optimizations

### Memory Best Practices

**Search thoroughly:**
- Extract keywords from user request
- Search multiple variations
- Review all results, not just top match
- Check get_context for recent work

**Store comprehensively:**
- Store decisions (architecture choices)
- Store patterns (reusable solutions)
- Store learnings (insights about codebase)
- Link related memories for graph

**Build knowledge graph:**
- Link new memories to related old ones
- Use specific relationships (fixes, builds_on, supersedes)
- Run auto-link-memories.py weekly
- Visualize with knowledge-graph-viz.py

---

## 🔧 Integration with Existing Tools

### Memory System Tools

All existing memory tools integrate seamlessly:

**Dashboard:**
```bash
python3 ~/.claude/scripts/memory-dashboard.py
```

**Compliance:**
```bash
python3 ~/.claude/scripts/agent-compliance-scoring.py
```

**Auto-linking:**
```bash
python3 ~/.claude/scripts/auto-link-memories.py
```

**Testing:**
```bash
python3 ~/.claude/tests/memory-system-tests.py
```

### Verification Hooks

Post-execution hook verifies protocol:
```bash
~/.claude/hooks/post-execution-memory-verify.sh
```

Checks:
- ✅ search_memory called at start
- ✅ store_memory called at end
- ✅ Planning used for complex tasks

---

## 📈 Success Metrics

Track these metrics to measure effectiveness:

**Compliance Metrics:**
- Memory search rate: Target 100% (every session)
- Memory storage rate: Target 85%+ (every solution)
- Planning usage: Target 70%+ (complex tasks)

**Quality Metrics:**
- Repeat issues: Target <5% (knowledge reused)
- First-time-right: Target 80%+ (planning effectiveness)
- Agent coordination: Target 90%+ (delegation success)

**Efficiency Metrics:**
- Token usage: Target 76% reduction (vs no planning)
- Time to solution: Track before/after planning adoption
- Rework rate: Target <10% (get it right first time)

---

## 🚀 Next Steps

### Immediate Actions

1. **Read this guide** - Understand the planning workflow
2. **Try EnterPlanMode** - Use it on next complex task
3. **Review workflows** - Study examples in CLAUDE.md
4. **Check compliance** - Run agent-compliance-scoring.py

### Continuous Improvement

**Weekly:**
- Review compliance scores
- Run auto-link-memories.py
- Check memory dashboard

**Monthly:**
- Analyze planning effectiveness
- Review stale memories (refresh-system.py)
- Update external docs as needed

**Quarterly:**
- Full memory system audit
- Knowledge graph visualization
- Update CLAUDE.md based on learnings

---

## 📚 Related Documentation

- **CLAUDE.md** - Main configuration file (v4.0)
- **MEMORY_WORKFLOW.md** - Detailed memory system guide
- **MEMORY_IMPROVEMENTS.md** - 9 enhancement tools
- **PROJECT_CONTEXT_TEMPLATE.md** - Multi-agent coordination
- **~/.claude/agents/*.md** - 47 agent definitions

---

## 🤝 Contributing

To improve this workflow:

1. Try it on real tasks
2. Document what works/doesn't
3. Propose enhancements
4. Store learnings in memory system
5. Update this guide

---

## 📖 Research References

**Sources:**
- [HumanLayer: Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [ClaudeLog: Plan Mode Mechanics](https://claudelog.com/mechanics/plan-mode/)
- [GitHub: Sub-Agent Delegation Setup](https://gist.github.com/tomas-rampas/a79213bb4cf59722e45eab7aa45f155c)
- [Dometrain: Creating the Perfect CLAUDE.md](https://dometrain.com/blog/creating-the-perfect-claudemd-for-claude-code/)
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)

**Key Findings:**
- Planning reduces token usage by 76%
- LLMs can follow 150-200 instructions consistently
- Progressive disclosure prevents context bloat
- Memory integration ensures consistency

---

**Version**: 4.0
**Last Updated**: 2026-02-01
**Status**: ✅ Production Ready
**Maintainer**: Claude Code Agent Ecosystem
