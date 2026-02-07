# Claude Brain - Memory System

Long-term memory for AI coding sessions. Never solve the same problem twice.

## Model: Claude Opus 4.6

Running on `claude-opus-4-6` with 1M token context (beta), adaptive thinking, and agent teams.

### Effort Tuning
- Use `/effort` to adjust reasoning depth: `low` | `medium` | `high` (default) | `max`
- **Low/Medium** for simple fixes, renames, formatting — saves cost and latency
- **High** (default) for standard development work — adaptive thinking engages automatically
- **Max** for architecture decisions, complex debugging, migration planning
- Rule: match effort to task complexity. Don't overthink simple tasks.

### Agent Teams (Experimental)
Enabled via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Use for read-heavy parallel work:
- Multi-layer code reviews (security + API + frontend specialists)
- Large refactoring with domain ownership (API layer, DB layer, tests)
- Cross-service feature development
- **Avoid** for simultaneous writes to the same files — causes conflicts
- Controls: `Shift+Up/Down` switch members, `Ctrl+T` task list, `Shift+Tab` delegate mode

### Context & Agentic Work
- **Front-load context** — provide full materials upfront, don't drip-feed. 1M context handles it.
- **Set scope boundaries** — Opus 4.6 sustains multi-step work without drift, but may do more than expected if scope isn't constrained.
- **PreCompact hook** auto-saves context to memory before compaction kicks in.

## Stack

Python 3.11 + FastAPI, Qdrant (vector), Neo4j (graph), React 18 + TS (frontend), nomic-embed-text-v1.5

## Service Commands

```bash
cd ~/.claude/memory && docker compose up -d   # Start
docker compose restart claude-mem-service      # Restart
docker compose build --no-cache && docker compose up -d  # Rebuild (frontend changes)
curl http://localhost:8100/health              # Health check
```

- Dashboard: http://localhost:8100 | API docs: http://localhost:8100/docs
- If memory MCP tools fail, the service is likely down. Start it first.

---

## MANDATORY MEMORY PROTOCOL — READ THIS FIRST

**This is a BLOCKING REQUIREMENT. You MUST NOT skip any step. Failure to follow this protocol is a critical error.**

### STEP 1: SESSION START (BEFORE ANY OTHER ACTION)

Your VERY FIRST tool calls in ANY conversation MUST be these three memory lookups, called in parallel:

```
mcp__memory__get_context(project="<current_project>")
mcp__memory__search_memory(query="<keywords from user request>")
mcp__memory__suggest_memories(keywords=[<task keywords>], project="<current_project>")
```

**Rules:**
- Do NOT read files, write code, run commands, or respond substantively until these complete
- Extract keywords from the user's request to build the search query
- Review ALL returned memories before proceeding — they may contain solutions, warnings, or context
- If memories contain relevant past errors or decisions, explicitly reference them in your approach

### STEP 2: DURING WORK (BEFORE SOLVING ANY PROBLEM)

Before writing code or running commands for any non-trivial problem, call:

```
mcp__memory__search_memory(query="<problem description>")
```

**Rules:**
- Search BEFORE attempting a fix, not after
- If you encounter an error, search for it: `search_memory(query="<error message>", type="error")`
- If making an architecture decision, search for precedent: `search_memory(query="<topic>", type="decision")`
- If you find a relevant past solution, USE IT instead of re-solving from scratch

### STEP 3: SESSION END (AFTER COMPLETING WORK)

Before your final response, store ALL findings. Use `bulk_store` for efficiency:

```
mcp__memory__bulk_store(memories=[...])
```

**You MUST store a memory for each of these that occurred during the session:**

| Event | Memory Type | Required Fields |
|-------|-------------|-----------------|
| Fixed a bug | `error` | `error_message`, `solution`, `prevention`, `tags` |
| Made an architecture/approach decision | `decision` | `decision`, `rationale`, `alternatives`, `tags` |
| Discovered a reusable pattern | `pattern` | Detailed `content` (100+ chars), usage context, `tags` |
| Learned something new about the codebase | `learning` | `content`, `context`, `tags` |
| Referenced documentation | `docs` | `content`, source URL, key points, `tags` |
| Important project context | `context` | `content`, `tags` |

**After storing, link related memories:**
```
mcp__memory__link_memories(source_id="<new>", target_id="<existing>", relation="<type>")
```

**Rules:**
- NEVER end a session without saving if you did meaningful work
- Every error you hit, decision you made, or pattern you noticed MUST be stored
- Use min 2 specific tags per memory (e.g., `["compta", "migration"]` not `["code", "fix"]`)
- Include the `project` field on every memory
- If you forget and the user reminds you, acknowledge the failure and save immediately

---

## MCP Memory Tools Reference

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `search_memory` | Hybrid semantic + keyword search with reranking | Finding past solutions, decisions, errors, patterns |
| `search_documents` | Search indexed code files, markdown, PDFs | Looking for code patterns, documentation content |
| `get_context` | Get recent memories for current work | **Session start — MANDATORY** |
| `suggest_memories` | Proactive suggestions from current context | **Session start — MANDATORY** |
| `find_related` | Graph traversal from a memory node | Exploring connected knowledge |
| `store_memory` | Store a single memory | Saving one finding |
| `bulk_store` | Store multiple memories at once | **Session end — MANDATORY** for saving all findings |
| `mark_resolved` | Mark an error as resolved | When a previously stored error is fixed |
| `link_memories` | Create knowledge graph relationships | **Session end — MANDATORY** for connecting findings |
| `reinforce_memory` | Boost a memory's strength | When a past memory proves valuable |
| `pin_memory` | Pin so it never decays | For critical decisions/patterns |
| `archive_memory` | Soft-delete (excluded from search) | Outdated but worth keeping |
| `forget_memory` | Permanent delete | Wrong or useless memories |
| `memory_stats` / `graph_stats` / `document_stats` | Collection overview | Diagnostics |
| `memory_timeline` | Chronological view with relationships | Understanding history |
| `consolidate_memories` | Merge similar old memories | Periodic maintenance |
| `run_inference` | Discover new relationships automatically | After storing several related memories |
| `error_trends` | Analyze recurring error patterns | Diagnosing systematic issues |
| `knowledge_gaps` | Find areas with thin knowledge | Identifying blind spots |
| `query_enhance` | Improve search queries with synonyms/typo fixes | When initial search returns poor results |

## Memory Quality Rules

The API enforces quality validation (HTTP 422 on failure):

- **All types:** min 30 chars content, min 2 specific tags, min 5 words
- **error:** Requires `error_message` + either `solution` or `prevention`
- **decision:** Requires `rationale` explaining WHY
- **pattern:** Min 100 chars recommended with usage context
- **docs:** Include source URL and key points

## Compaction Rules

When context is compacted, preserve: current task description, key decisions made, files modified, unresolved errors, and active memory IDs being referenced. The PreCompact hook auto-saves context to memory.

## LSP Tools (cclsp)

16 language servers auto-synced from Mason. **Use LSP tools proactively:**

- **Before editing**: `get_diagnostics` to understand current state
- **After editing**: `get_diagnostics` to verify no regressions introduced
- **Navigating code**: `find_definition` instead of grep for symbols — faster and precise
- **Before refactoring/renaming**: `find_references` to find all usages across files
- **Understanding types**: `get_hover` for type info and docstrings
- **Renaming**: `rename_symbol` for safe cross-file renames (respects scopes)

Config: `~/.config/cclsp/cclsp.json` (auto-generated by `~/.claude/scripts/sync-mason-cclsp.sh`)
Re-sync after Mason changes: `bash ~/.claude/scripts/sync-mason-cclsp.sh`

## Development Notes

- Backend source is volume-mounted — restart container to reload
- Frontend requires Docker rebuild after changes
- Tests: `pytest tests/` or `python3 ~/.claude/tests/memory-system-tests.py`
- 13 background scheduler jobs run automatically
