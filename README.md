# Claude Brain

Long-term memory system for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Stores errors, decisions, patterns, and learnings across sessions so you never solve the same problem twice.

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## What Is This

Claude Brain gives Claude Code persistent memory backed by vector search (Qdrant), a knowledge graph (Neo4j), and neuroscience-inspired features like adaptive forgetting, memory reconsolidation, and spaced repetition. It runs as three Docker containers on your local machine and integrates with Claude Code via MCP.

## Quick Start

```bash
git clone https://github.com/h4ckm1n-dev/Claude-Brain.git
cd Claude-Brain/memory
docker compose up -d
```

This starts three containers:

| Container | Port | Purpose |
|-----------|------|---------|
| `claude-mem-qdrant` | 6333 | Vector database (Qdrant) |
| `claude-mem-neo4j` | 7474 / 7687 | Knowledge graph (Neo4j 5 Community) |
| `claude-mem-service` | 8100 | FastAPI server + React dashboard |

**Access points:**
- Dashboard: http://localhost:8100
- API docs: http://localhost:8100/docs
- Qdrant UI: http://localhost:6333/dashboard
- Neo4j Browser: http://localhost:7474

## Architecture

```
┌───────────────────────────────────────────────────────┐
│                    Claude Code CLI                      │
│              (MCP client via memory bridge)             │
└──────────────────────┬────────────────────────────────┘
                       │ MCP protocol (stdio)
                       ▼
┌───────────────────────────────────────────────────────┐
│              MCP Bridge (Node.js)                       │
│        Exposes 33 tools + 3 resources to Claude        │
└──────────────────────┬────────────────────────────────┘
                       │ HTTP (localhost:8100)
                       ▼
┌───────────────────────────────────────────────────────┐
│              FastAPI Server (Python 3.11)               │
│    11 routers · 144 endpoints · 13 scheduler jobs      │
│    React dashboard served as static SPA                 │
├───────────┬───────────────────────────┬───────────────┤
│  Qdrant   │        Neo4j              │  Scheduler    │
│  Vector   │    Knowledge Graph        │  (APScheduler)│
│  Search   │  8 relationship types     │  13 bg jobs   │
│  768-dim  │  temporal validity        │               │
└───────────┴───────────────────────────┴───────────────┘
```

## Core Features

### Hybrid Search

Combines dense and sparse retrieval with learned fusion weights:

- **Dense vectors**: `nomic-ai/nomic-embed-text-v1.5` (768 dimensions) via sentence-transformers
- **Sparse vectors**: `Qdrant/bm42-all-minilm-l6-v2-attentions` via fastembed
- **Fusion**: Query-type-aware RRF (conceptual queries favor dense, exact-match queries favor sparse)
- **Reranking**: Cross-encoder reranker for final result ordering
- **Query enhancement**: Synonym expansion and typo correction before search

### Knowledge Graph

Neo4j stores relationships between memories with 8 relationship types:

| Relationship | Meaning |
|-------------|---------|
| `CAUSES` | Memory A caused the situation in Memory B |
| `FIXES` | Memory A contains the fix for Memory B |
| `CONTRADICTS` | Memories conflict with each other |
| `SUPPORTS` | Memories reinforce each other |
| `FOLLOWS` | Temporal sequence |
| `RELATED` | General association |
| `SUPERSEDES` | Newer decision replaces older one |
| `SIMILAR_TO` | Near-duplicate (used for dedup linking) |

Additional graph features:
- Temporal validity windows on relationships (valid_from / valid_to)
- Automatic relationship inference (error-solution, semantic, temporal, causal)
- Contradiction detection via cycle analysis
- Graph-based recommendations (collaborative filtering on shared neighbors)

### Neuroscience-Inspired Memory

Memories are not static records. They have a lifecycle:

**Lifecycle states**: `EPISODIC` → `STAGING` → `SEMANTIC` → `PROCEDURAL` (and `ARCHIVED` → `PURGED`)

- **Adaptive forgetting** (FadeMem-inspired): Memory strength decays over time based on access patterns. Low-strength memories are archived, then purged.
- **Reconsolidation**: When a memory is accessed, it is "reconsolidated" — strength is refreshed, and context may be updated.
- **Spaced repetition**: Memories due for review are identified and reconsolidated on a schedule to prevent decay.
- **Memory replay** (sleep mode): Random important and underutilized memories are replayed periodically, simulating REM sleep consolidation.
- **Dream mode**: Rapid random memory replay to discover unexpected connections.
- **Emotional weighting**: Memories with emotional markers (error frustration, breakthrough excitement) get weighted scoring.
- **Interference detection**: Weekly scan for conflicting memories that create confusion, with resolution suggestions.

### Quality System

- **Quality scores** computed from: access frequency, recency, rating, content length, tag count, relationship count
- **Tier promotion**: Memories are automatically promoted through lifecycle states based on quality thresholds
- **5-star rating**: Manual quality feedback adjusts importance scoring
- **Utility-based archival**: Low-utility memories are archived automatically

### Background Scheduler Jobs

13 jobs run automatically via APScheduler:

| Job | Interval | Purpose |
|-----|----------|---------|
| Memory Consolidation | 24h | Merge similar old memories |
| Adaptive Forgetting | 24h | Decay memory strength, archive/purge weak memories |
| Session Consolidation | 12h | Summarize completed work sessions |
| Quality Score Update | 24h | Recalculate quality scores for all memories |
| Memory State Machine | 12h | Evaluate and execute lifecycle state transitions |
| Relationship Inference | 24h | Discover error→solution, semantic, and temporal links |
| Adaptive Importance | 24h | Recalculate importance scores in batch |
| Utility-Based Archival | 24h | Archive low-utility memories |
| Memory Replay | 12h | Replay important and underutilized memories |
| Spaced Repetition | 6h | Review memories due for reconsolidation |
| Emotional Analysis | 24h | Analyze and weight emotional content |
| Interference Detection | Weekly | Find and resolve conflicting memories |
| Meta-Learning | Weekly | Track performance metrics and tune parameters |

## Claude Code Integration

### MCP Tools (33)

Claude Code accesses the memory system through an MCP bridge that exposes these tools:

| Tool | Purpose |
|------|---------|
| `store_memory` | Store a single memory (error, decision, pattern, learning, docs, context) |
| `bulk_store` | Store multiple memories in one call |
| `search_memory` | Hybrid semantic + keyword search with cross-encoder reranking |
| `search_documents` | Search indexed files (code, markdown, PDFs) |
| `get_context` | Get recent memories relevant to current work |
| `suggest_memories` | Proactive suggestions based on current files, branch, keywords |
| `find_related` | Graph traversal from a memory node |
| `link_memories` | Create a relationship between two memories |
| `mark_resolved` | Mark an error memory as resolved |
| `reinforce_memory` | Boost a memory's strength to prevent decay |
| `pin_memory` | Pin a memory so it never decays |
| `unpin_memory` | Unpin a memory to allow normal decay |
| `archive_memory` | Soft-delete (excluded from search, retrievable) |
| `forget_memory` | Permanent delete |
| `get_weak_memories` | Find fading memories that may be archived soon |
| `memory_stats` | Collection statistics |
| `graph_stats` | Knowledge graph statistics |
| `document_stats` | Document index statistics |
| `memory_timeline` | Chronological view with relationships |
| `consolidate_memories` | Trigger memory consolidation |
| `consolidate_session` | Consolidate a work session into summary |
| `new_session` | Start a new session context |
| `export_memories` | Export as JSON, CSV, or Obsidian markdown |
| `brain_dream` | Rapid random memory replay |
| `brain_detect_conflicts` | Find contradicting memories |
| `brain_replay` | Replay important memories to strengthen them |
| `run_inference` | Discover new relationships automatically |
| `temporal_query` | Query what was known at a specific point in time |
| `error_trends` | Analyze recurring error patterns and clusters |
| `knowledge_gaps` | Detect topics with thin knowledge coverage |
| `query_enhance` | Improve search query with synonyms and typo correction |
| `graph_contradictions` | Find contradicting memory pairs in the graph |
| `graph_recommendations` | Graph-based memory recommendations |

The MCP bridge also exposes 3 resources: Recent Memories, Unresolved Errors, and Knowledge Graph Overview.

### Hooks (22 scripts, 6 active events)

Shell scripts that execute on Claude Code lifecycle events. Active hooks from `settings.json`:

| Event | Hook | Purpose |
|-------|------|---------|
| `Stop` | `session-summary.sh` | Save session summary to memory on conversation end |
| `PreToolUse` (Write/Edit) | `protect-sensitive-files.sh` | Block edits to sensitive files |
| `PreToolUse` (Bash) | `block-destructive-commands.sh` | Block dangerous shell commands |
| `PostToolUse` (WebFetch) | `webfetch-capture.sh` | Capture fetched URLs for reference |
| `PostToolUse` (Write/Edit) | `memory-capture.sh` | Auto-capture file change context to memory |
| `PostToolUse` (Write/Edit) | `file-edit-tracker.sh` | Track which files were modified in session |
| `PostToolUse` (Bash) | `error-resolution-detector.sh` | Detect when errors get resolved |
| `PostToolUse` (Bash) | `smart-error-capture.sh` | Capture command errors to memory |
| `UserPromptSubmit` | `plan-mode-reminder.sh` | Remind about plan mode for complex tasks |
| `Notification` | `notification-router.sh` | Route notifications to system notifier |
| `PreCompact` | `pre-compact-memory-save.sh` | Save context to memory before context compaction |

22 hook scripts total in the `hooks/` directory (some inactive/experimental).

### Custom Agents (11)

Specialized sub-agents for Claude Code's agent teams:

`backend-architect` · `test-engineer` · `debugger` · `api-designer` · `database-optimizer` · `refactoring-specialist` · `infrastructure-architect` · `typescript-expert` · `deployment-engineer` · `python-expert` · `performance-profiler`

### Slash Commands (7)

| Command | Purpose |
|---------|---------|
| `/validate` | Run validation checks on current project |
| `/status` | Show project status dashboard |
| `/quick-review` | Lightweight code review of uncommitted changes |
| `/debug-task` | Debug a failed task |
| `/init-project` | Initialize project for agent ecosystem |
| `/context-clean` | Clean project context |
| `/memory-health` | Check memory system health and statistics |

### Skills (4)

| Skill | Purpose |
|-------|---------|
| `memory-search` | Search memories from conversation |
| `memory-save` | Save findings to memory |
| `memory-stats` | View memory statistics |
| `archive` | Archive old memories |

### Statusline

A custom statusline command (`statusline-command.sh`) displays memory system stats in the Claude Code status bar.

## Dashboard

The React dashboard at http://localhost:8100 has 13 pages:

| Page | What It Shows |
|------|---------------|
| Dashboard | Overview with memory counts, types, recent activity |
| Memories | Browse, filter, and manage individual memories |
| Search | Full-text and semantic search interface |
| Graph | Interactive knowledge graph visualization |
| Analytics | Memory trends, type distribution, project breakdown |
| Sessions | Work session history and summaries |
| Temporal | Time-travel queries — what was known at a specific date |
| Brain Intelligence | Neuroscience features: replay, dream, inference, conflicts |
| Consolidation | Merge similar memories, view consolidation history |
| Documents | Indexed file browser and search |
| Suggestions | Proactive memory suggestions |
| System Admin | Scheduler status, job management, database health |
| Settings | Configuration and preferences |

## API Reference

11 routers with 144 total endpoints. Key groups:

### Memories (`/memories`)
- `POST /memories` — Store a memory
- `POST /memories/bulk` — Store multiple memories
- `GET /memories/{id}` — Get memory by ID
- `PUT /memories/{id}` — Update a memory
- `DELETE /memories/{id}` — Delete a memory
- `POST /memories/{id}/rate` — Rate a memory (1-5 stars)

### Search (`/search`)
- `GET /search` — Hybrid search with query, type, project, tag filters
- `POST /search/advanced` — Advanced search with full filter options

### Brain (`/brain`)
- `POST /brain/dream` — Trigger dream mode (random replay)
- `POST /brain/replay` — Replay important memories
- `POST /brain/inference` — Run relationship inference
- `GET /brain/conflicts` — Detect contradictions
- `GET /brain/error-trends` — Error pattern analysis
- `GET /brain/knowledge-gaps` — Find thin knowledge areas

### Quality (`/quality`)
- `GET /quality/{id}` — Get memory quality score
- `GET /quality/{id}/trend` — Quality score trend over time
- `GET /quality/leaderboard` — Highest-quality memories

### Graph (`/graph`)
- `GET /graph/related/{id}` — Find related memories via graph traversal
- `GET /graph/stats` — Graph statistics
- `GET /graph/contradictions` — Contradiction detection
- `GET /graph/recommendations/{id}` — Graph-based recommendations

### Other Routers
- **Analytics** (`/analytics`) — Trends, distributions, expertise profiling
- **Temporal** (`/temporal`) — Time-travel queries, temporal graph traversal
- **Sessions** (`/sessions`) — Session management, consolidation
- **Documents** (`/documents`) — File indexing and search
- **Admin** (`/admin`) — Scheduler, health, reindex, reset, migration
- **Audit** (`/audit`) — Audit trail and change history

Full API docs: http://localhost:8100/docs

## Installation & Configuration

### Docker Compose (recommended)

```bash
cd Claude-Brain/memory
docker compose up -d
```

Environment variables (set in `docker-compose.yml`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `QDRANT_HOST` | `claude-mem-qdrant` | Qdrant hostname |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `NEO4J_URI` | `bolt://claude-mem-neo4j:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `memory_graph_2024` | Neo4j password |
| `LOG_LEVEL` | `INFO` | Logging level |
| `SCHEDULER_ENABLED` | `true` | Enable background scheduler jobs |

### Local Development

Run databases in Docker, API server locally:

```bash
# Start databases only
cd Claude-Brain/memory
docker compose up -d claude-mem-qdrant claude-mem-neo4j

# Run API server
pip install -r requirements.txt
python -m src.server

# Run frontend in dev mode (separate terminal)
cd frontend
npm install
npm run dev  # http://localhost:5173 with hot reload
```

**Note**: Backend source is volume-mounted — restart the container to reload code changes. Frontend requires a Docker rebuild (`docker compose build --no-cache && docker compose up -d`) after changes.

### Claude Code MCP Setup

Create or edit `~/.claude/.mcp.json` (or your project's `.mcp.json`):

```json
{
  "memory": {
    "command": "node",
    "args": ["/path/to/Claude-Brain/mcp/memory-mcp/dist/index.js"],
    "env": {
      "MEMORY_API_URL": "http://localhost:8100"
    }
  }
}
```

Then restart Claude Code. The 33 memory tools will appear in tool listings.

## Troubleshooting

### Service won't start

```bash
# Check containers
docker compose ps

# Check ports are free
lsof -i :8100   # FastAPI
lsof -i :6333   # Qdrant
lsof -i :7687   # Neo4j

# Restart
docker compose down && docker compose up -d

# Check logs
docker compose logs claude-mem-service
```

### MCP tools not appearing in Claude Code

1. Verify the service is running: `curl http://localhost:8100/health`
2. Check your `.mcp.json` path is correct
3. Restart Claude Code after changing `.mcp.json`

### Search returns no results

```bash
# Check health (includes embedding model status)
curl http://localhost:8100/health

# Verify collection exists
curl http://localhost:6333/collections
```

### Dashboard not loading

The dashboard is built into the Docker image and served as a static SPA at port 8100. If you see API JSON instead of the dashboard, rebuild the image:

```bash
cd Claude-Brain/memory
docker compose build --no-cache && docker compose up -d
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Server | Python 3.11, FastAPI, Uvicorn, Pydantic |
| Vector Database | Qdrant (HNSW indexing, hybrid dense+sparse) |
| Knowledge Graph | Neo4j 5 Community (APOC plugin) |
| Dense Embeddings | nomic-ai/nomic-embed-text-v1.5 (768-dim) |
| Sparse Embeddings | Qdrant/bm42-all-minilm-l6-v2-attentions |
| Scheduler | APScheduler (13 background jobs) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts |
| MCP Bridge | Node.js TypeScript (stdio transport) |
| Containerization | Docker Compose (3 services) |

## License

MIT — see [LICENSE](LICENSE).

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push to your branch and open a Pull Request

Issues: https://github.com/h4ckm1n-dev/Claude-Brain/issues
