# Claude Code Agent Ecosystem

45 specialized agents for autonomous software development. Coordinate via PROJECT_CONTEXT.md.

> **CRITICAL LIMITATION**: Subagents cannot spawn other subagents. For nested workflows, return to main conversation and chain from there.

---

## 🎯 Quick Tool Reference

**Most Used Tools**:
```bash
# Security scanning (12 agents use this)
python3 ~/.claude/tools/security/secret-scanner.py .

# API/service health checks (13 agents use this)
~/.claude/tools/devops/service-health.sh https://api.example.com

# Code complexity analysis (11 agents use this)
python3 ~/.claude/tools/analysis/complexity-check.py src/

# Error log analysis (12 agents use this)
python3 ~/.claude/tools/data/log-analyzer.py /var/log/app.log

# Test coverage reporting (9 agents use this)
python3 ~/.claude/tools/testing/coverage-reporter.py coverage.xml

# Resource monitoring
python3 ~/.claude/tools/devops/resource-monitor.py

# SQL query optimization
python3 ~/.claude/tools/data/sql-explain.py "SELECT * FROM users WHERE..."

# Validate tool ecosystem
~/.claude/tools/core/health-check.sh
```

**Quick Lookup**: See which tools an agent has
```bash
~/.claude/scripts/agent-tools.sh backend-architect
~/.claude/scripts/agent-tools.sh test-engineer
```

**By Use Case**:
- 🔒 **Security**: secret-scanner.py, vuln-checker.sh, permission-auditor.py, cert-validator.sh
- 📊 **Code Quality**: complexity-check.py, duplication-detector.py, type-coverage.py, import-analyzer.py
- 🧪 **Testing**: coverage-reporter.py, test-selector.py, mutation-score.sh, flakiness-detector.py
- ⚡ **Performance**: resource-monitor.py, sql-explain.py, metrics-aggregator.py
- 🚀 **DevOps**: docker-manager.sh, service-health.sh, env-manager.py, ci-status.sh

All tools return JSON: `{"success": bool, "data": {}, "errors": []}`

---

## 🧠 Memory System (PROACTIVE USE REQUIRED)

Long-term memory via vector database. **Claude MUST proactively store valuable information.**

**Start Memory Service:**
```bash
cd ~/.claude/memory && docker compose up -d
```

**MCP Memory Tools** (use `store_memory` and `search_memory`):
| Tool | Description |
|------|-------------|
| `store_memory` | Save valuable knowledge (see criteria below) |
| `search_memory` | Search before starting tasks - check existing knowledge |
| `get_context` | Get relevant context for current project |
| `mark_resolved` | Mark error as fixed with solution |
| `link_memories` | Create relationship between memories |
| `memory_stats` | View memory statistics |

---

### WHEN TO STORE MEMORIES (Claude must do this automatically)

**ALWAYS store after:**
1. **WebFetch/WebSearch** - Save useful documentation, API references, library usage
2. **Solving a problem** - Save what didn't work AND what worked
3. **Making a decision** - Save architecture choices with rationale
4. **Discovering a pattern** - Save reusable code patterns
5. **Learning something new** - Save insights about user's tech stack
6. **Finding a workaround** - Save the workaround and why it was needed

**Memory Types & When to Use:**
| Type | Store When... | Example |
|------|---------------|---------|
| `docs` | Found useful documentation online | "React Query v5: use `enabled` flag for conditional queries" |
| `error` | Something failed (with/without solution) | "Vite path aliases need both tsconfig AND vite.config" |
| `decision` | Made an architecture/tech choice | "Chose Zustand over Redux - simpler API, less boilerplate" |
| `pattern` | Found reusable code pattern | "Error boundary with retry logic pattern" |
| `learning` | Learned about user's stack/preferences | "User prefers functional components over classes" |
| `context` | Important project context | "This project uses pnpm, not npm" |

**ALWAYS include:**
- Relevant `tags` for searchability
- `project` name when project-specific
- `context` explaining when/why this is useful

---

### SEARCH BEFORE WORKING

**Before starting any task, search memory for:**
- Previous errors in this area
- Existing patterns that apply
- User preferences and decisions
- Documentation already fetched

```
search_memory(query="[relevant topic]", limit=10)
```

---

### EXAMPLE MEMORY SAVES

**After WebFetch:**
```
store_memory(
  type="docs",
  content="Qdrant query_points() replaces search() in v1.7+. Use client.query_points(collection, query=vector, limit=N).points",
  tags=["qdrant", "python", "vector-db", "api-change"],
  source="https://qdrant.tech/documentation"
)
```

**After solving a problem:**
```
store_memory(
  type="error",
  content="sentence-transformers 2.x incompatible with huggingface_hub 0.20+",
  error_message="ImportError: cannot import name 'cached_download'",
  solution="Upgrade to sentence-transformers>=3.0.0",
  tags=["python", "sentence-transformers", "dependency-conflict"]
)
```

**After making a decision:**
```
store_memory(
  type="decision",
  content="Use Qdrant over ChromaDB for memory system",
  decision="Chose Qdrant",
  rationale="Better filtering, Rust performance, production-ready, Docker support",
  alternatives=["ChromaDB", "Pinecone", "pgvector"],
  tags=["architecture", "vector-db"]
)
```

**Learning about user's stack:**
```
store_memory(
  type="learning",
  content="User's Claude Code setup uses 45 specialized agents with Task tool routing",
  tags=["user-setup", "agents", "workflow"],
  project="claude-ecosystem"
)
```

---

### Memory Service Commands
```bash
# Start (required before using memory tools)
cd ~/.claude/memory && docker compose up -d

# Check health
curl http://localhost:8100/health

# View stats
curl http://localhost:8100/stats
```

---

## 🔄 Common Workflows

**New Feature**:
1. code-architect (design) → 2. backend-architect (implement) → 3. security-practice-reviewer (audit) → 4. test-engineer (tests) → 5. deployment-engineer (deploy)

**Bug Fix**:
1. debugger (investigate with log-analyzer.py, resource-monitor.py) → 2. domain-agent (fix) → 3. test-engineer (regression test)

**Code Quality**:
1. code-reviewer (assess with complexity-check.py, duplication-detector.py) → 2. refactoring-specialist (improve) → 3. test-engineer (validate)

**Performance**:
1. performance-profiler (profile with resource-monitor.py, metrics-aggregator.py) → 2. backend-architect (optimize with sql-explain.py) → 3. test-engineer (validate)

**Security Audit**:
1. security-practice-reviewer (scan with secret-scanner.py, vuln-checker.sh, permission-auditor.py, cert-validator.sh) → 2. code-reviewer (code review) → 3. deployment-engineer (infrastructure)

---

## Agent Invocation Rules

**Use specialized agent when**:
- Task involves 3+ files or multiple modules
- Requires domain expertise (API, security, performance, testing, deployment)
- Production code or infrastructure work
- Architecture/design decisions
- ANY keyword triggers (see Keyword Triggers table below)

**Work directly when**:
- Single file, <10 lines, trivial change
- No patterns or expertise needed
- Simple documentation update

---

## Keyword Triggers

When user message contains these keywords, auto-launch corresponding agent:

| Keywords | Agent |
|----------|-------|
| "API", "REST", "GraphQL", "endpoint" | api-designer |
| "frontend", "UI", "React", "Vue", "Angular" | frontend-developer |
| "backend", "server", "database" | backend-architect |
| "test", "testing", "TDD", "E2E" | test-engineer |
| "deploy", "CI/CD", "Docker", "Kubernetes" | deployment-engineer |
| "slow", "optimize", "performance" | performance-profiler |
| "security", "vulnerability", "auth" | security-practice-reviewer |
| "refactor", "clean up", "technical debt" | refactoring-specialist |
| "bug", "error", "broken", "not working" | debugger |
| "mobile", "iOS", "Android" | mobile-app-developer |
| "AI", "ML", "LLM", "model" | ai-engineer |
| "design", "architecture", "plan" | code-architect |
| "TypeScript", "type safety", "generic", "tsconfig" | typescript-expert |

---

## Agent Selection Logic

**Step 1: Check keyword triggers** (see table above)

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

**Edge case**: "Build", "create", "implement" requests → Use domain-specific agent

---

## All 43 Agents by Category

### Full-Stack Development (4 agents)

| Agent | When to Use | Key Capabilities |
|-------|-------------|------------------|
| **code-architect** | System design, architecture planning, folder structure | Scalable architecture, design patterns, tech stack selection |
| **backend-architect** | Server-side logic, APIs, databases | Backend systems, microservices, API implementation |
| **frontend-developer** | UI components, state management, frontend apps | React/Vue/Angular, responsive design, performance |
| **api-designer** | REST/GraphQL API design, documentation | Developer-friendly APIs, versioning, specifications |

### Language & Platform Specialists (6 agents)

| Agent | When to Use | Key Capabilities |
|-------|-------------|------------------|
| **python-expert** | Advanced Python, async/await, type safety | Python optimization, advanced features, refactoring |
| **typescript-expert** | Advanced TypeScript, type system, strict types | Type safety, generics, conditional types, production patterns |
| **mobile-app-developer** | Native iOS/Android apps | Swift, Kotlin, mobile architecture, app stores |
| **desktop-app-developer** | Cross-platform desktop apps | Electron, Tauri, system integration |
| **game-developer** | Games, game mechanics, physics | Unity, Godot, graphics, game optimization |
| **blockchain-developer** | Web3, smart contracts, DeFi | Solidity, Ethereum, NFTs, blockchain integration |

### DevOps & Infrastructure (3 agents)

| Agent | When to Use | Key Capabilities |
|-------|-------------|------------------|
| **deployment-engineer** | CI/CD, Docker, cloud deployment | Kubernetes, infrastructure as code, automation |
| **infrastructure-architect** | Cloud architecture, disaster recovery | AWS/GCP/Azure, high availability, scaling |
| **observability-engineer** | Logging, metrics, monitoring | Tracing, alerting, production debugging |

### Testing & Quality (4 agents)

| Agent | When to Use | Key Capabilities |
|-------|-------------|------------------|
| **test-engineer** | Comprehensive testing, TDD/BDD | Unit/integration/E2E tests, test strategies |
| **api-tester** | API testing, load testing | Performance tests, contract testing |
| **code-reviewer** | Code quality review, best practices | Security audit, maintainability, standards |
| **debugger** | Bug fixing, root cause analysis | Systematic debugging, error reproduction |

### AI & Machine Learning (2 agents)

| Agent | When to Use | Key Capabilities |
|-------|-------------|------------------|
| **ai-engineer** | AI/ML features, LLM integration | Recommendation systems, computer vision, automation |
| **ai-prompt-engineer** | LLM prompt optimization | Prompt templates, multi-step workflows, tuning |

### Data & Analytics (4 agents)

| Agent | When to Use | Key Capabilities |
|-------|-------------|------------------|
| **data-scientist** | Data analysis, SQL, BigQuery | Data workflows, insights extraction |
| **database-optimizer** | Schema design, query optimization | Indexing, performance tuning, SQL/NoSQL |
| **analytics-engineer** | Event tracking, analytics systems | Google Analytics, Mixpanel, data pipelines |
| **visualization-dashboard-builder** | Interactive dashboards, KPIs | Real-time monitoring, stakeholder reports |

### Performance & Security (3 agents)

| Agent | When to Use | Key Capabilities |
|-------|-------------|------------------|
| **performance-profiler** | Performance bottlenecks, optimization | Application profiling, stack-wide optimization |
| **security-practice-reviewer** | Security audits, vulnerability scanning | Compliance, security best practices |
| **math-checker** | Mathematical verification | Formula validation, computational accuracy |

### Design & UX (4 agents)

| Agent | When to Use | Key Capabilities |
|-------|-------------|------------------|
| **ui-designer** | Interface design, component libraries | Design systems, visual aesthetics |
| **ux-researcher** | User research, behavior analysis | Journey maps, user testing, needs assessment |
| **mobile-ux-optimizer** | Mobile-first experiences | Mobile usability, responsive adaptation |
| **accessibility-specialist** | WCAG compliance, screen readers | Keyboard navigation, universal accessibility |

### Content & Marketing (4 agents)

| Agent | When to Use | Key Capabilities |
|-------|-------------|------------------|
| **content-marketing-specialist** | Marketing copy, blogs, campaigns | Conversion-focused content, multi-platform strategy |
| **visual-storyteller** | Visual narratives, infographics | Presentations, complex idea communication |
| **technical-writer** | Technical docs, API docs, tutorials | Clear documentation, user guides |
| **seo-specialist** | SEO optimization, meta tags | Core Web Vitals, structured data, technical SEO |

### Code Management (3 agents)

| Agent | When to Use | Key Capabilities |
|-------|-------------|------------------|
| **refactoring-specialist** | Code cleanup, technical debt | Design patterns, legacy transformation |
| **migration-specialist** | Framework migrations, version upgrades | Safe incremental migrations, modernization |
| **localization-specialist** | i18n/l10n, multi-language support | Cultural adaptation, internationalization |

### Business Intelligence (4 agents)

| Agent | When to Use | Key Capabilities |
|-------|-------------|------------------|
| **finance-tracker** | Budget management, cost optimization | Revenue forecasting, financial analysis |
| **growth-hacker** | Viral growth, user acquisition | Data-driven experiments, scalable growth |
| **trend-researcher** | Market opportunities, viral content | Social media trends, emerging behaviors |
| **trading-bot-strategist** | Algorithmic trading, backtesting | Trading logic, risk management, performance analysis |

### Documentation & Support (2 agents)

| Agent | When to Use | Key Capabilities |
|-------|-------------|------------------|
| **codebase-documenter** | Service documentation, CLAUDE.md files | Comprehensive codebase analysis, documentation |
| **context7-docs-fetcher** | Fetch library/framework docs | Real-time documentation retrieval |

### Meta & Orchestration (2 agents)

| Agent | When to Use | Key Capabilities |
|-------|-------------|------------------|
| **workflow-coordinator** | Complex multi-agent workflows, 3+ agents, parallel execution | Agent spawning, result synthesis, conflict resolution |
| **error-coordinator** | Agent failures, workflow blocks, recovery needed | Error analysis, recovery strategies, workflow resumption |

---

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
- Architecture → Implementation → Testing → Hybrid (3 phases)

---

## Agent Coordination Rules

**If agent reports unclear task**: Request file paths, error messages, acceptance criteria from user

**If agents duplicate work**: Check PROJECT_CONTEXT.md, assign explicit file/domain boundaries

**If agent needs missing artifact**: Switch to sequential, run dependency agent first

**If agent fails mid-task**: Read error, check git status, decide re-run vs manual fix

**If workflow too slow**: Identify parallelizable work, consider mocks for unblocking

**If file conflicts**: Review git diff, check PROJECT_CONTEXT.md reasoning, trust last agent

**If wrong agent chosen**: Check "When to Use" descriptions, use keyword triggers

**If PROJECT_CONTEXT.md exceeds 1000 lines**: Archive old activity to PROJECT_ARCHIVE.md

---

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

---

## Validation & Error Recovery

**Validation scripts** (run during multi-agent workflows):
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

---

## Quick Reference

### Common Agent Chains

**AUTH**: code-architect → database-optimizer → backend-architect → security-practice-reviewer → frontend-developer → test-engineer

**API**: api-designer → backend-architect → api-tester → codebase-documenter

**FRONTEND**: ui-designer → frontend-developer → accessibility-specialist → test-engineer

**DEPLOY**: deployment-engineer → security-practice-reviewer → observability-engineer

**QUALITY**: (refactoring-specialist + security-practice-reviewer + performance-profiler) → test-engineer → code-reviewer

**AI**: ai-engineer → ai-prompt-engineer → backend-architect → frontend-developer → test-engineer

**DATA**: data-scientist → database-optimizer → backend-architect → visualization-dashboard-builder

**MOBILE**: code-architect → api-designer → mobile-app-developer → mobile-ux-optimizer → test-engineer

### Agent Selection Disambiguations

| Confused About | Use | Not | Reason |
|----------------|-----|-----|--------|
| API implementation | backend-architect | api-designer | Designer creates specs, architect implements |
| API documentation | api-designer | technical-writer | Designer knows API patterns |
| UI implementation | frontend-developer | ui-designer | Designer creates mockups, developer codes |
| Security review | security-practice-reviewer | code-reviewer | Security specialist knows vulnerabilities |
| Code quality | code-reviewer | refactoring-specialist | Reviewer audits, refactorer fixes |
| Database queries | database-optimizer | backend-architect | Optimizer focuses on performance tuning |
| Testing implementation | test-engineer | backend-architect | Test engineer creates comprehensive suites |
| Deployment config | deployment-engineer | backend-architect | Deployment focuses on CI/CD pipelines |
| Analytics dashboards | visualization-dashboard-builder | data-scientist | Builder creates UI, scientist analyzes data |
| Agent structure | code-architect | backend-architect | Architect designs systems, backend implements logic |
| Mobile UI patterns | mobile-ux-optimizer | ui-designer | Mobile-specific constraints and patterns |
| Performance issues | performance-profiler | code-reviewer | Profiler has specialized diagnostic tools |
| Bash scripts | backend-architect | deployment-engineer | Backend handles logic, deployment handles automation |
| Error handling | debugger | code-reviewer | Debugger specializes in root cause analysis |
| Content copy | content-marketing-specialist | technical-writer | Marketing focuses on conversion, writer on clarity |

### PROJECT_CONTEXT.md Commands

```bash
# Initialize
cp ~/.claude/PROJECT_CONTEXT_TEMPLATE.md ./PROJECT_CONTEXT.md

# View recent activity
grep -A 10 "Agent Activity Log" PROJECT_CONTEXT.md | head -20

# Check blockers
grep -A 5 "Blockers" PROJECT_CONTEXT.md

# List artifacts
grep -A 20 "Artifacts for Other Agents" PROJECT_CONTEXT.md
```

---

## Model Routing Strategy

Route tasks to appropriate models for cost/speed optimization:

| Model | Use For | Cost | Speed |
|-------|---------|------|-------|
| `haiku` | Simple fetch, documentation, straightforward writing | Lowest | Fastest |
| `sonnet` | Code review, testing, implementation | Medium | Fast |
| `inherit` (Opus) | Architecture, security, complex decisions | Highest | Thorough |

**Recommended Routing**:
- Quick research/fetch → `haiku`
- Standard implementation → `sonnet`
- Critical decisions → `inherit` (Opus 4.5)

---

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

---

## System Info

**Agents**: 45 specialized agents in `.claude/agents/`
**Template**: `~/.claude/PROJECT_CONTEXT_TEMPLATE.md`
**Version**: 3.1 (LLM-optimized)
**Last Updated**: 2026-01-26
**Total Agents**: 45

---

## Best Practices References

- [Claude Code Official Docs](https://code.claude.com/docs/en/sub-agents)
- [Anthropic Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Multi-Agent Patterns](https://rlancemartin.github.io/2026/01/09/agent_design/)
- [VoltAgent Collection](https://github.com/VoltAgent/awesome-claude-code-subagents)
