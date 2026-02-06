# Interactive Agent Selector

Find the right agent(s) for your task with smart recommendations

**Usage:** `/agent-select task description`

**Input:** $ARGUMENTS

---

## Instructions

Analyze the user's task description and recommend the best agent(s) to handle it, including suggestions for agent chains when multiple agents are needed.

### 1. Analyze Task Description

Extract key information from $ARGUMENTS:
- **Domain**: Frontend, backend, database, testing, security, etc.
- **Complexity**: Simple fix, feature implementation, architecture design
- **Keywords**: API, UI, test, deploy, optimize, debug, etc.
- **Scope**: Single file, multiple files, full feature

### 2. Check Keyword Triggers

Match against keyword triggers from CLAUDE.md:

```yaml
Keywords → Agent Mapping:
  - "API", "REST", "GraphQL", "endpoint" → api-designer
  - "frontend", "UI", "React", "Vue", "Angular" → frontend-developer
  - "backend", "server", "database" → backend-architect
  - "test", "testing", "TDD", "E2E" → test-engineer
  - "deploy", "CI/CD", "Docker", "Kubernetes" → deployment-engineer
  - "slow", "optimize", "performance" → performance-profiler
  - "security", "vulnerability", "auth" → security-practice-reviewer
  - "refactor", "clean up", "technical debt" → refactoring-specialist
  - "bug", "error", "broken", "not working" → debugger
  - "mobile", "iOS", "Android" → mobile-app-developer
  - "AI", "ML", "LLM", "model" → ai-engineer
  - "design", "architecture", "plan" → code-architect
  - "TypeScript", "type safety" → typescript-expert
  - "Python", "async" → python-expert
```

### 3. Use Agent Selector Script

```bash
# Run the agent selector helper script
bash ~/.claude/scripts/agent-selector-helper.sh "$ARGUMENTS" 2>/dev/null || echo "Script unavailable, using manual analysis"
```

### 4. Determine Agent Recommendations

Based on the analysis, recommend:

**Single Agent Tasks:**
- Single file modification → Specific domain agent
- Code review → code-reviewer
- Bug fix → debugger
- Quick optimization → Relevant specialist

**Multi-Agent Chains (Sequential):**
- API feature → api-designer → backend-architect → test-engineer
- Full-stack feature → code-architect → backend-architect → frontend-developer → test-engineer
- Database migration → database-optimizer → backend-architect → test-engineer
- Security audit → security-practice-reviewer → refactoring-specialist (if issues)

**Multi-Agent Chains (Parallel):**
- Frontend + Backend (with mocks) → (frontend-developer + backend-architect) → test-engineer
- Multiple reviews → (security-practice-reviewer + code-reviewer + performance-profiler)

### 5. Generate Recommendations

Present recommendations in this format:

```
🎯 AGENT RECOMMENDATIONS FOR YOUR TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Task Analysis:
   Domain: [Backend/Frontend/Full-Stack/Infrastructure/etc]
   Complexity: [Simple/Medium/Complex]
   Estimated Scope: [Single file/Multiple files/Full feature]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🥇 PRIMARY RECOMMENDATION

Agent: [agent-name]
Match Score: [percentage]%

Why This Agent:
   • [Reason 1 - domain expertise]
   • [Reason 2 - tools available]
   • [Reason 3 - typical use case match]

Tools Available:
   [List: Write, Read, MultiEdit, Bash, Grep, etc.]

Example Tasks:
   • [Similar task example 1]
   • [Similar task example 2]

Quick Launch:
   /quick-agent [agent-name]: [suggested refined task description]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🥈 ALTERNATIVE OPTIONS

[If applicable, show 1-2 alternative agents with brief reasoning]

Agent: [agent-name-2]
Match Score: [percentage]%
Why: [Brief explanation]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[If multi-agent chain recommended:]

🔗 RECOMMENDED AGENT CHAIN

This task appears complex and may benefit from multiple agents:

Sequential Chain (Run in order):
   1. [agent-1] → [What they do]
   2. [agent-2] → [What they do]
   3. [agent-3] → [What they do]

Why This Chain:
   • [Reason for sequence]
   • [Dependencies between agents]
   • [Expected outcome]

How to Execute:
   Option A - Claude Code Plan Mode (Recommended):
      Describe the feature to Claude Code and let it
      plan and orchestrate agents automatically

   Option B - Manual Sequential:
      /quick-agent [agent-1]: [task for agent 1]
      # Wait for completion
      /quick-agent [agent-2]: [task for agent 2]
      # Wait for completion
      /quick-agent [agent-3]: [task for agent 3]

[If parallel execution possible:]

Parallel Execution (Run simultaneously):
   • [agent-1] + [agent-2] (independent work)
   • Then: [agent-3] (integration)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 DECISION GUIDE

Use /quick-agent if:
   ✅ Single domain (frontend OR backend, not both)
   ✅ Small scope (< 3 files)
   ✅ Clear requirements
   ✅ No architecture decisions needed

Use Claude Code Plan Mode if:
   ❌ Multiple domains (frontend AND backend)
   ❌ Large scope (≥ 3 files or new modules)
   ❌ Requires design/architecture
   ❌ Needs multiple agents coordinated

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 LEARN MORE

View agent details: /list-agents [category]
See all agents: /list-agents
Agent usage stats: /agent-metrics
```

---

## Example Outputs

**Example 1: Simple Bug Fix**
```
Input: /agent-select fix login button not responding on mobile

Output:
🎯 PRIMARY RECOMMENDATION
Agent: debugger
Match Score: 95%

Why This Agent:
   • Specializes in bug fixing and root cause analysis
   • Systematic debugging approach
   • Good for reproduction and permanent fixes

Quick Launch:
   /quick-agent debugger: fix login button not responding on mobile
```

**Example 2: New API Endpoint**
```
Input: /agent-select create new user profile API endpoint with validation

Output:
🎯 RECOMMENDED AGENT CHAIN
Sequential Chain:
   1. api-designer → Design API spec (OpenAPI)
   2. backend-architect → Implement endpoint + validation
   3. test-engineer → Create API tests

How to Execute:
   Describe the feature to Claude Code or run:
   /quick-agent api-designer: design user profile API spec
```

**Example 3: Performance Issue**
```
Input: /agent-select app is slow, need to optimize

Output:
🎯 PRIMARY RECOMMENDATION
Agent: performance-profiler
Match Score: 90%

Why This Agent:
   • Specializes in bottleneck identification
   • Application profiling expertise
   • Stack-wide optimization

Quick Launch:
   /quick-agent performance-profiler: profile app and identify performance bottlenecks
```

---

## Disambiguation Logic

When task is ambiguous, ask clarifying questions:

```
🤔 I need more information to recommend the best agent:

Your task: "[task description]"

Please clarify:
   1. Is this frontend, backend, or full-stack?
   2. Is this a new feature or fixing existing code?
   3. Approximate scope: single file, few files, or entire module?
   4. Any specific technologies involved?

Or provide more details:
   /agent-select [more detailed description]
```

---

## Special Cases

**API-related tasks:**
- "create API" → api-designer + backend-architect chain
- "document API" → api-designer
- "test API" → api-tester
- "implement API" → backend-architect

**UI-related tasks:**
- "design UI" → ui-designer
- "implement UI" → frontend-developer
- "mobile UI" → mobile-ux-optimizer
- "accessible UI" → accessibility-specialist

**Testing tasks:**
- "write tests" → test-engineer
- "test API" → api-tester
- "E2E tests" → test-engineer

**Database tasks:**
- "design schema" → database-optimizer
- "optimize queries" → database-optimizer
- "migration" → migration-specialist

---

## Notes

- Match score is based on keyword match, agent capabilities, and task complexity
- Agent chains are recommended for tasks requiring >2 agents
- Quick launch commands are provided for immediate execution
- Decision guide helps choose between quick-agent and Plan mode
