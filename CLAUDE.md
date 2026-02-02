# Claude Brain - Memory-First Development

## WHY (Project Purpose)

This is Claude Brain, a long-term memory system for AI coding sessions. It prevents repeat work, preserves decisions across sessions, and builds knowledge through automatic relationship inference. Memory is the primary product.

**The goal:** Never solve the same problem twice. Every bug fix, architecture decision, and pattern learned should be searchable and reusable across all future sessions.

---

## WHAT (Tech Stack & Architecture)

### Stack
- **Backend:** Python 3.11, FastAPI, Uvicorn
- **Vector Storage:** Qdrant (hybrid search: dense + sparse + reranking)
- **Graph Database:** Neo4j (relationships, knowledge graph)
- **Frontend:** React 18, TypeScript, TailwindCSS, Vite
- **Models:** nomic-embed-text-v1.5 (768-dim), BM42 (sparse), cross-encoder reranker

### Project Structure
```
src/              # Backend: server.py, collections.py, graph.py, etc.
frontend/         # React dashboard with Analytics, Memories, Graph pages
scripts/          # Maintenance and admin scripts
tests/            # Test suites
docker-compose.yml
```

### Key Patterns
- **Brain endpoints:** `/brain/*` (intelligence features)
- **Memory endpoints:** `/memories`, `/search`
- **Graph endpoints:** `/graph/stats`, `/graph/traverse`
- **Frontend hooks:** `useMemories()`, `useGraphStats()`, `useBrain*()`

### Database Decisions
- PostgreSQL for relational data backend
- Qdrant for vector storage (chosen over ChromaDB)
- Neo4j for knowledge graph relationships

---

## HOW (Memory-First Workflow)

### Every Session Start

**1. Check automated recommendations**
Look for `<system-reminder>` tags containing:
- 🧠 Memory suggestions (from memory-suggest.sh hook)
- 🎯 Plan mode reminders (from plan-mode-reminder.sh hook)

**2. Use MCP memory tools:**
```javascript
search_memory(query="[task keywords]", limit=10)
get_context(project="claude-memory", hours=24)
```

**3. Review suggestions before starting work**
The system provides automated memory suggestions. Use them to avoid repeating past work.

### During Work

**For complex tasks** (3+ files, architecture decisions, unclear requirements):
- Use `EnterPlanMode()` to plan before implementing
- Read existing code before modifying
- Search memory when you encounter similar problems

**For simple tasks** (<10 lines, single file, trivial changes):
- Work directly without plan mode
- Still check memory for past solutions

**Always:**
- Avoid over-engineering - keep solutions simple and focused
- Only make changes that are directly requested or clearly necessary
- Read files before proposing modifications

### Every Session End

Store what you learned using `store_memory()`:

**Errors:**
```javascript
store_memory({
  type: "error",
  content: "Description of the error and fix",
  error_message: "The error message",
  solution: "How it was fixed",
  prevention: "How to avoid it in future",
  tags: ["specific", "searchable", "tags"],
  project: "claude-memory"
})
```

**Decisions:**
```javascript
store_memory({
  type: "decision",
  content: "What was decided",
  rationale: "Why this decision was made",
  alternatives: ["Option A", "Option B"],
  tags: ["decision", "architecture"],
  project: "claude-memory"
})
```

**Patterns:**
```javascript
store_memory({
  type: "pattern",
  content: "Reusable pattern or best practice",
  context: "When and how to use it",
  tags: ["pattern", "best-practice"],
  project: "claude-memory"
})
```

**Documentation:**
```javascript
store_memory({
  type: "docs",
  content: "Summary of documentation",
  source: "https://source-url.com",
  tags: ["docs", "reference"],
  project: "claude-memory"
})
```

---

## Memory System Reference

### MCP Memory Tools

| Tool | When to Use |
|------|-------------|
| `search_memory` | Start of every session, when encountering similar problems |
| `search_documents` | When searching codebase/files (code, markdown, PDFs) |
| `get_context` | Start of every session (includes both memories and documents) |
| `store_memory` | After solving problems, making decisions, discovering patterns |
| `mark_resolved` | Mark an error memory as resolved |
| `link_memories` | Create relationships between memories |

### Documents vs Memories

**Memories** (structured knowledge):
- Errors and their solutions
- Architecture decisions with rationale
- Patterns and best practices
- Documentation with context
- Learnings from development

**Documents** (filesystem content):
- Code files (.py, .ts, .js, etc.)
- Markdown documentation (.md)
- Configuration files (.json, .yaml)
- PDFs and reference materials
- Raw file content without metadata

**Best Practice - Search Both:**
```javascript
// 1. Search memories (structured knowledge)
search_memory(query="authentication bug", limit=10)

// 2. Search documents (code/files)
search_documents(query="authentication implementation", limit=5)

// 3. get_context() includes both automatically
get_context(project="claude-memory", hours=24)
```

### Memory Quality Standards

**All memory types:**
- Minimum: 30 characters content, 2 specific tags, 5 words
- No placeholders ("test", "todo", "tbd")
- No generic-only tags ("misc", "general")

**Type-specific requirements:**
- **error**: Must include `error_message`, plus `solution` OR `prevention`
- **decision**: Must include `rationale` explaining WHY
- **pattern**: Minimum 100 chars recommended, include usage context
- **docs**: Include `source` URL and key points

Quality validation is enforced by the API (HTTP 422 on violation).

---

## Service Management

### Start Service
```bash
cd ~/.claude/memory && docker compose up -d
```

### Health Check
```bash
curl http://localhost:8100/health
```

### Dashboard
http://localhost:8100

### Check if Service is Running
If memory tools fail, the service may be down. Start it before continuing work.

---

## Development Workflows

### Frontend Development
```bash
cd frontend && npm run dev
# Then rebuild: docker compose build --no-cache && docker compose up -d
```

### Backend Changes
```bash
# Service auto-reloads with volume mount: ./src:/app/src
docker compose restart claude-mem-service
```

### Run Tests
```bash
pytest tests/
python3 ~/.claude/tests/memory-system-tests.py
```

---

## Planning-First Workflow (2026 Best Practice)

Research shows planning before coding reduces token usage by 76% while achieving better results.

### When to Use EnterPlanMode

**Use plan mode for:**
- ✅ New features affecting 3+ files
- ✅ Architecture/design decisions
- ✅ Multiple valid implementation approaches
- ✅ Tasks where you'd need to ask user for clarification
- ✅ Refactoring or code modifications
- ✅ Unclear requirements needing exploration

**Skip plan mode for:**
- ❌ Single file, <10 lines
- ❌ Bug fix with known solution from memory
- ❌ Trivial changes (typos, docs)

### The Planning Process

```
1. SEARCH → search_memory() + get_context()
2. PLAN   → EnterPlanMode() for complex tasks
3. READ   → Gather context with Read, Glob, Grep
4. CREATE → Write plan with Analysis, Approach, Steps
5. APPROVE→ ExitPlanMode() to get user approval
6. EXECUTE→ Implement the plan
7. STORE  → store_memory() results and decisions
```

### Planning Best Practices

- Keep plans concise (under 2 pages)
- Focus on WHAT and WHY, not HOW
- Reference external docs instead of copying
- Use file:line pointers instead of code snippets
- Ask questions with `AskUserQuestion` if approach is ambiguous

---

## Tools & Scripts Reference

**Memory Tools:**
- `~/.claude/scripts/memory-dashboard.py` - Memory system dashboard
- `~/.claude/tests/memory-system-tests.py` - Memory system tests

**Development Tools:**
```bash
# Security
python3 ~/.claude/tools/security/secret-scanner.py .

# Service health
~/.claude/tools/devops/service-health.sh https://api.example.com

# Code complexity
python3 ~/.claude/tools/analysis/complexity-check.py src/

# Test coverage
python3 ~/.claude/tools/testing/coverage-reporter.py coverage.xml
```

**All tools:** See `~/.claude/tools/` directory for complete list

---

## Documentation & References

### Internal Documentation
- Full system docs: `~/.claude/memory/README.md`
- Memory improvements: `~/.claude/MEMORY_IMPROVEMENTS.md`
- Backend code: `src/server.py` (main FastAPI app)

### API Documentation
- http://localhost:8100/docs (Swagger UI)
- http://localhost:8100/redoc (ReDoc)

### External Resources
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [Anthropic Engineering Blog](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Writing a Good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)

---

## System Info

**Version:** 5.0 (Simplified, Memory-First, 2026 Best Practices)
**Last Updated:** 2026-02-02
**Context:** Memory system is primary product, use built-in Plan/Explore agents
**Philosophy:** Progressive disclosure - reference external docs instead of embedding everything

---

## Quick Examples

### Store an Error Solution
```javascript
store_memory({
  type: "error",
  content: "Frontend Analytics page showing 0 relationships",
  error_message: "useGraphStats hook not being called",
  solution: "Added useGraphStats() import and used graphStats?.relationships",
  tags: ["react", "frontend", "analytics", "graph-stats"],
  project: "claude-memory"
})
```

### Search for Past Solutions
```javascript
search_memory({
  query: "docker build cache frontend",
  type: "error",  // Optional: filter by type
  limit: 5
})
```

### Get Recent Context
```javascript
get_context({
  project: "claude-memory",
  hours: 24  // Last 24 hours of work
})
```

### Link Related Memories
```javascript
link_memories({
  source_id: "019c1234-...",
  target_id: "019c5678-...",
  relation: "fixes"  // causes, fixes, contradicts, supports, related, etc.
})
```
