# Claude Brain - Memory System

Long-term memory for AI coding sessions. Never solve the same problem twice.

## Stack

- **Backend:** Python 3.11, FastAPI (`src/server.py`), Uvicorn
- **Vector DB:** Qdrant (hybrid: dense + sparse + cross-encoder reranking)
- **Graph DB:** Neo4j (knowledge relationships)
- **Frontend:** React 18, TypeScript, TailwindCSS, Vite (`frontend/`)
- **Embeddings:** nomic-embed-text-v1.5 (768-dim)

## Service Commands

```bash
cd ~/.claude/memory && docker compose up -d   # Start
docker compose restart claude-mem-service      # Restart (backend auto-reloads via volume mount)
docker compose build --no-cache && docker compose up -d  # Rebuild (after frontend changes)
curl http://localhost:8100/health              # Health check
```

- Dashboard: http://localhost:8100
- API docs: http://localhost:8100/docs
- If memory MCP tools fail, the service is likely down. Start it first.

## MCP Memory Tools

IMPORTANT: These tools are available in every session. Use them actively.

### Search & Retrieve

| Tool | Parameters | Use When |
|------|-----------|----------|
| `search_memory` | `query` (required), `type?`, `tags?`, `project?`, `limit?` (default 10) | Finding past solutions, decisions, errors, patterns |
| `search_documents` | `query` (required), `file_type?`, `folder?`, `limit?` | Searching indexed code files, markdown, PDFs |
| `get_context` | `project?`, `hours?` (default 24), `types?` | Session start — returns recent memories + documents |
| `suggest_memories` | `project?`, `keywords?`, `current_files?`, `git_branch?`, `limit?` | Proactive suggestions based on current work context |
| `find_related` | `memory_id` (required), `max_hops?` (1-3), `limit?` | Graph traversal to find connected memories |

### Store & Modify

| Tool | Parameters | Use When |
|------|-----------|----------|
| `store_memory` | `type` (required: error/decision/pattern/learning/docs/context), `content` (required), `tags?`, `project?`, `error_message?`, `solution?`, `prevention?`, `decision?`, `rationale?`, `alternatives?`, `context?` | After solving bugs, making decisions, discovering patterns |
| `bulk_store` | `memories[]` (array of {type, content, tags?, project?}) | Storing multiple related memories at once |
| `mark_resolved` | `memory_id` (required), `solution` (required) | Marking an error memory as resolved |
| `link_memories` | `source_id`, `target_id`, `relation` (required: causes/fixes/contradicts/supports/follows/related/supersedes/similar_to) | Creating knowledge graph relationships |
| `archive_memory` | `memory_id` (required) | Soft-delete (excluded from search, kept in DB) |
| `forget_memory` | `memory_id` (required) | Permanent delete (also removes from graph) |

### Analytics & Maintenance

| Tool | Parameters | Use When |
|------|-----------|----------|
| `memory_stats` | (none) | Collection overview (counts, graph stats) |
| `graph_stats` | (none) | Knowledge graph statistics (nodes, relationships) |
| `document_stats` | (none) | Document indexing statistics (chunks, collections) |
| `memory_timeline` | `project?`, `memory_type?`, `limit?` | Viewing memories chronologically with relationships |
| `consolidate_memories` | `older_than_days?` (default 7), `dry_run?` | Merging similar old memories, archiving low-value ones |

### Session Workflow (MANDATORY)

**ALWAYS do these steps. No exceptions.**

1. **Session Start — ALWAYS search brain first:**
   - `get_context(project="claude-memory")` to load recent work
   - `search_memory(query="[task keywords]")` for past solutions to the current problem
   - `suggest_memories(keywords=["relevant", "terms"])` for proactive context
   - Review any `<system-reminder>` suggestions provided automatically
   - Do NOT start coding until you have checked what the brain already knows

2. **During Work — search before solving:**
   - `search_memory(query="relevant keywords")` whenever encountering familiar problems
   - `search_documents(query="implementation details")` when looking for code patterns
   - Check brain BEFORE writing new code for any non-trivial problem

3. **Session End — ALWAYS save findings:**
   - `store_memory(type="error", ...)` for every error encountered and fixed
   - `store_memory(type="decision", ...)` for every architecture/design choice made
   - `store_memory(type="pattern", ...)` for reusable patterns discovered
   - `store_memory(type="docs", ...)` for any documentation researched or referenced online
   - `store_memory(type="learning", ...)` for insights gained during the session
   - `link_memories(...)` to connect related findings to existing knowledge
   - If you searched for external documentation, store a summary of what you found

## Memory Quality Rules

The API enforces quality validation (HTTP 422 on failure):

- **All types:** min 30 chars content, min 2 specific tags, min 5 words. No placeholders or generic tags.
- **error:** Requires `error_message` + either `solution` or `prevention`
- **decision:** Requires `rationale` explaining WHY
- **pattern:** Min 100 chars recommended with usage context
- **docs:** Include source URL and key points

Quality scoring weights: content richness (30%), access frequency (25%), maturity (15%), stability (10%), relationships (10%), user rating (10%).

## API Patterns

Full OpenAPI spec: http://localhost:8100/docs

### Core
- Memory CRUD + actions: `/memories/*` (CRUD, draft, bulk, search, suggest, link, pin, unpin, resolve, rate, reinforce, archive, versions, state, undo, restore, quality-leaderboard, quality-report)
- Context: `/context`, `/context/{project}`
- Search: `/search/unified`, `/query/enhance`
- Consolidation: `/consolidate`, `/consolidate/preview`

### Intelligence
- Brain: `/brain/*` (infer-relationships, update-importance, archive-low-utility, dream, replay, replay/project, replay/underutilized, reconsolidate, spaced-repetition, topics, emotional-analysis, detect-conflicts, meta-learning, performance-metrics, stats)
- Inference: `/inference/*` (run, co-access/stats, co-access/reset)
- Forgetting: `/forgetting/*` (update, stats, weak)

### Analytics & Insights
- Analytics: `/analytics/*` (error-trends, pattern-clusters, knowledge-gaps, comprehensive)
- Recommendations: `/recommendations/*` (patterns-for-error, preventive-patterns, documentation-topics, co-access, {memory_id})
- Insights: `/insights/*` (recurring-patterns, expertise-profile, anomalies, error-trends, summary)

### Quality & Lifecycle
- Quality: `/quality/*` (stats, update, promote-batch, promotion-candidates, {id}/rate, {id}/trend)
- Lifecycle: `/lifecycle/*` (stats, update, transitions)
- Audit: `/audit`, `/audit/{memory_id}`, `/audit/stats`

### Knowledge Graph & Temporal
- Graph: `/graph/*` (stats, related, solutions, timeline, project/{name}, contradictions, recommendations/{id})
- Temporal: `/temporal/*` (valid-at, obsolete, stats, mark-obsolete, related-at)

### Sessions & Documents
- Sessions: `/sessions/*` (stats, new, {id}/memories, {id}/consolidate, consolidate/batch)
- Documents: `/documents/*` (insert, search, stats, reset, {file_path} DELETE)
- Indexing: `/indexing/*` (folders GET/POST, reindex)

### Admin & Operations
- Health: `/health`, `/health/detailed`
- Scheduler: `/scheduler/status`, `/scheduler/jobs/{id}/trigger`
- Notifications: `/notifications/*` (CRUD, mark-read, stats)
- Export/Backup: `/export/memories`, `/backup`, `/backups`
- Cache: `/cache/stats`, `/cache/clear`
- Jobs: `/jobs/*` (list, prune, tag, {id}/cancel)
- Settings: `/settings` (GET/POST)
- Suggestions: `/suggestions/*` (should-show, feedback, stats)
- Database: `/database/stats`, `/database/reset`
- Processes: `/processes/watcher/*` (status, start, stop)
- Logs: `/logs/{name}` (read, clear)

## Development Notes

- Backend source is volume-mounted (`./src:/app/src`) — restart container to reload
- Frontend requires Docker rebuild after changes (`docker compose build --no-cache`)
- Tests: `pytest tests/` or `python3 ~/.claude/tests/memory-system-tests.py`
- 13 background scheduler jobs run automatically (consolidation, quality updates, state machine, relationship inference, memory replay, spaced repetition, etc.)
