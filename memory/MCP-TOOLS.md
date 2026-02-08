# MCP Memory Tools Reference

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
