# Claude Brain - Memory System

Long-term memory for AI coding sessions. Never solve the same problem twice.

## Model: Claude Opus 4.6

Running on `claude-opus-4-6` — 200K context window.

### Key Capabilities
- **Adaptive thinking** (`type: "adaptive"`) — replaces deprecated `budget_tokens`. Engages automatically at high/max effort.
- **128K output tokens** — doubled from 64K. Long code generation and full-file rewrites supported.
- **Compaction API** (beta) — automatic context summarization when approaching limits.
- **Breaking change**: prefill of assistant messages no longer supported.

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
- **Front-load context** — provide full materials upfront, don't drip-feed.
- **Set scope boundaries** — Opus 4.6 sustains multi-step work without drift, but may do more than expected if scope isn't constrained.
- **PreCompact hook** auto-saves context to memory before compaction kicks in.

## Claude Agent SDK

Use Agent SDK for CI/CD, pipelines, and programmatic automation. Use CLI for interactive work.

- **Install**: `pip install claude-agent-sdk` (Python) | `npm install @anthropic-ai/claude-agent-sdk` (TS)
- **Core API**: `query()` async generator (one-shot) | `ClaudeSDKClient` (multi-turn sessions)
- **Key options**: `allowed_tools`, `permission_mode`, `hooks` (HookMatcher), `mcp_servers`, `agents` (AgentDefinition), `max_turns`, `max_budget_usd`, `system_prompt`, `can_use_tool` callback
- **Permission modes**: `default` | `acceptEdits` | `bypassPermissions` (CI/CD) | `plan`
- **Custom tools**: `@tool` decorator + `create_sdk_mcp_server()` for in-process MCP tools
- **Sessions**: `resume=session_id`, `fork_session=True` for conversation continuity
- **Pattern**: gather context (Read/Glob/Grep) → act (Edit/Write/Bash) → verify (tests) → repeat
- **Docs**: [Overview](https://platform.claude.com/docs/en/agent-sdk/overview) | [Python](https://github.com/anthropics/claude-agent-sdk-python) | [TypeScript](https://github.com/anthropics/claude-agent-sdk-typescript)

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

| Event | Memory Type | **All Required Fields** |
|-------|-------------|------------------------|
| Fixed a bug | `error` | `content`(50+), `error_message`, `solution`, `prevention`, `context`, `tags`(3+), `project` |
| Architecture/approach decision | `decision` | `content`(50+), `rationale`, `alternatives`(list), `context`, `tags`(3+), `project` |
| Reusable pattern | `pattern` | `content`(100+), `context`, `tags`(3+), `project` |
| Learned something new | `learning` | `content`(50+), `context`, `tags`(3+), `project` |
| Documentation reference | `docs` | `content`(50+), `source`(URL), `tags`(3+), `project` |
| Project context | `context` | `content`(50+), `tags`(3+), `project` |

**After storing, link related memories:**
```
mcp__memory__link_memories(source_id="<new>", target_id="<existing>", relation="<type>")
```

**Rules:**
- NEVER end a session without saving if you did meaningful work
- Every error you hit, decision you made, or pattern you noticed MUST be stored
- Use min **3 specific tags** per memory (e.g., `["qdrant", "api", "data-loss"]` not `["code", "fix"]`)
- Include the `project` field on **every** memory
- Include `context` on **every** error, decision, and pattern (explains the situation)
- Error memories need ALL THREE: `error_message` + `solution` + `prevention`
- Decision memories need BOTH: `rationale` + `alternatives` list
- The API runs **strict enforcement** — incomplete memories are rejected with 422
- If you forget and the user reminds you, acknowledge the failure and save immediately

---

## MCP Memory Tools

Mandatory: `get_context`, `suggest_memories` (session start) | `bulk_store`, `link_memories` (session end).
Search: `search_memory` (semantic+keyword), `search_documents` (code/files), `find_related` (graph).
Manage: `store_memory`, `mark_resolved`, `reinforce_memory`, `pin_memory`, `archive_memory`, `forget_memory`.
Analytics: `memory_stats`, `graph_stats`, `error_trends`, `knowledge_gaps`, `run_inference`, `query_enhance`.
Full reference: `~/.claude/memory/MCP-TOOLS.md`

## Memory Quality Rules (STRICT enforcement)

The API runs **strict mode** — low-quality memories are rejected at store time (HTTP 422):

- **All types:** min 50 chars content, min 3 specific tags, min 10 words, `project` required
- **error:** ALL required: `error_message` + `solution` + `prevention` + `context`
- **decision:** ALL required: `rationale` + `alternatives` (list) + `context`
- **pattern:** Min 100 chars content + `context` explaining when to use it
- **docs:** `source` URL/reference required
- **Tags:** Generic tags (`bug`, `fix`, `code`, `update`) don't count — use specific ones
- A complete memory scores 0.70+ at creation. Incomplete ones are rejected.

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
