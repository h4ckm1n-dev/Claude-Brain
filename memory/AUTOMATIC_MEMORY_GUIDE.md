# 🧠 Automatic Memory System Guide

## Overview

Your Claude Code memory system is now **fully automatic** - it captures valuable information and proactively surfaces relevant memories without manual intervention.

---

## ✅ What Gets Automatically Captured

### 1. **Documentation Fetches** (WebFetch)
- Every useful webpage/documentation you fetch
- Automatically tagged with source URL
- Saved as `type: docs`

**Example**: Fetch React docs → Auto-saved with tags `[webfetch, react, auto-captured]`

### 2. **Successful Commands** (Bash)
- Deployment commands (`docker`, `npm`, `git`)
- Installation commands (`npm install`, `pip install`)
- Configuration changes
- Saved as `type: pattern`

**Example**: `docker compose up -d` → Auto-saved as deployment pattern

### 3. **Errors & Failures** (Smart Error Capture)
- Command failures with exit code != 0
- Error type auto-detected (permission, network, syntax, etc.)
- Deduplicated (won't save same error twice within 1 hour)
- Saved as `type: error`

**Example**: Permission denied error → Auto-captured with solution suggestions

### 4. **Agent Task Results** (Task tool)
- Output from specialized agents
- Important decisions and implementations
- Saved as `type: learning`

**Example**: Frontend-developer agent completes → Auto-saved

### 5. **Session Summaries** (on Stop)
- Work done during session
- Project context (git branch, directory)
- Detected activities (debugging, deployment, configuration)
- Saved as `type: context`

**Example**: Session end → Summary saved with branch and activities

---

## 🎯 What Gets Automatically Loaded

### 1. **Before User Prompts** (UserPromptSubmit hook)
- Searches for relevant memories based on:
  - Current project directory
  - Git branch
  - Keywords in your message
  - Recently modified files
- Displays top 5 suggestions with scores

**Example Output**:
```
╭──────────────────────────────────────────────────────────────╮
│ 🧠 Relevant Memories Found (3)                               │
╰──────────────────────────────────────────────────────────────╯

  📌 ERROR
  └─ Docker permission denied on socket - use sudo or add user to docker group
     Tags: docker, permission, auto-captured
     Score: 0.9 | Accessed: 5x

  💡 Use search_memory() for more details
```

### 2. **Before Task Execution** (PreToolUse for Task)
- Analyzes task description
- Searches for related patterns/errors/docs
- Shows context before agent starts work

### 3. **Context-Aware Suggestions**
- API endpoint: `/memories/suggest`
- Factors considered:
  - **Project** (current directory)
  - **Git branch** (feature/main/etc)
  - **Current files** (what you're working on)
  - **Keywords** (from task description)
  - **Combined score** (importance × relevance × recency)

---

## 🔧 How It Works (Technical)

### Automatic Capture Pipeline

```
Tool Execution → PostToolUse Hook → auto-memory-capture.sh
                                         ↓
                                   Memory Analysis
                                   - Type detection
                                   - Deduplication
                                   - Tag extraction
                                         ↓
                                   POST /memories
                                         ↓
                                   Saved to Qdrant + Neo4j
```

### Automatic Retrieval Pipeline

```
User Message → UserPromptSubmit Hook → memory-suggest.sh
                                           ↓
                                      Extract Context
                                      - Keywords
                                      - Project
                                      - Git branch
                                      - Files
                                           ↓
                                      POST /memories/suggest
                                           ↓
                                      Ranked Results
                                      (importance × relevance × recency)
                                           ↓
                                      Display to User
```

---

## 📊 Memory Scoring System

Memories are automatically ranked using:

```
combined_score = (importance × 0.4) + (relevance × 0.35) + (recency × 0.25)
```

**Importance** (heuristic-based):
- `error` → 0.8 (high value)
- `decision` → 0.9 (critical)
- `pattern` → 0.7 (reusable)
- `docs` → 0.5 (reference)
- `learning` → 0.6 (contextual)
- `context` → 0.4 (ephemeral)

**Relevance**:
- Cosine similarity to current query
- Boosted by keyword matches

**Recency**:
- Exponential decay: `e^(-0.005 × hours)`
- Half-life ≈ 6 days

---

## 🎛️ Configuration

### Enable/Disable Auto-Capture

**Disable for specific tools**:
Edit `~/.claude/settings.json`, remove hooks for specific matchers:

```json
{
  "hooks": {
    "PostToolUse": [
      // Comment out or remove the WebFetch hook to disable auto-capture
      // {
      //   "matcher": "WebFetch",
      //   "hooks": [...]
      // }
    ]
  }
}
```

**Adjust capture thresholds**:
Edit `~/.claude/hooks/auto-memory-capture.sh`:

```bash
# Only capture commands with specific patterns
if echo "$COMMAND" | grep -qE "docker|npm|git|deploy|install|configure"; then
    # Save it
fi
```

### Customize Suggestions

**Change suggestion count**:
Edit `~/.claude/hooks/pre-task-memory-loader.sh`:

```bash
\"limit\": 5  # Change to 3, 10, etc.
```

**Filter by specific types**:
```bash
curl -s http://localhost:8100/memories/suggest -X POST \
    -d "{
        \"project\": \"${PROJECT_DIR}\",
        \"type\": \"error\",  # Only show errors
        \"limit\": 5
    }"
```

---

## 🚀 Advanced Usage

### Manual Memory Operations

Even with auto-capture, you can still manually manage memories:

**Search for specific topic**:
```bash
curl http://localhost:8100/memories/search -X POST \
    -d '{"query": "docker deployment", "limit": 10}'
```

**Link related memories**:
```bash
curl http://localhost:8100/memories/link -X POST \
    -d '{
        "source_id": "error-id",
        "target_id": "solution-id",
        "relation_type": "FIXES"
    }'
```

**Mark error as resolved**:
```bash
curl http://localhost:8100/memories/{id}/resolve -X POST \
    -d '{"solution": "Added user to docker group"}'
```

### Consolidation (Cleanup)

Run weekly to merge similar memories:

```bash
curl http://localhost:8100/consolidate -X POST \
    -d '{"older_than_days": 7, "dry_run": false}'
```

Or use the `/archive` skill (uses Haiku for intelligent cleanup):
```bash
/archive
```

---

## 📈 Monitoring Memory System

### Check Statistics

```bash
curl http://localhost:8100/stats | jq
```

**Output**:
```json
{
  "total_memories": 64,
  "active_memories": 58,
  "archived_memories": 6,
  "by_type": {
    "error": 15,
    "docs": 20,
    "pattern": 12,
    "learning": 8,
    "decision": 5,
    "context": 4
  },
  "unresolved_errors": 3
}
```

### View Dashboard

Open http://localhost:8100 in browser:
- **Dashboard**: Real-time stats and charts
- **Memories**: Full CRUD interface
- **Search**: Advanced search with filters
- **Graph**: Knowledge graph visualization
- **Analytics**: Detailed insights

---

## 🎯 Best Practices

### 1. **Trust the Auto-Capture**
- Let the system capture naturally
- Don't manually save everything
- The hooks are optimized for signal vs noise

### 2. **Review Suggestions Proactively**
- When you see suggestions at conversation start, read them
- Use `search_memory()` to dive deeper
- Link related memories using the dashboard

### 3. **Clean Up Periodically**
- Run `/archive` monthly
- Review and delete low-value memories
- Consolidate similar patterns

### 4. **Leverage Graph Relationships**
- When you solve an error, link it to the solution
- Create `SUPERSEDES` relationships for updated decisions
- Use `RELATED` for connected patterns

### 5. **Tag Strategically**
- Auto-tags are good, but add custom tags for important memories
- Use project-specific tags (`my-app`, `production`, etc.)
- Tag by technology (`react`, `docker`, `python`)

---

## 🐛 Troubleshooting

### "Memory not being captured"

**Check if service is running**:
```bash
curl http://localhost:8100/health
```

**Check hook execution**:
```bash
tail -f ~/.claude/audit.log
```

**Test hook manually**:
```bash
~/.claude/hooks/auto-memory-capture.sh WebFetch '{"url":"test"}' 0
```

### "Too many irrelevant suggestions"

**Increase relevance threshold**:
Edit search queries to add `min_score: 0.8` (only high-confidence matches).

**Filter by project**:
Suggestions are already project-aware, but you can make it stricter.

### "Memory service down"

**Restart Docker**:
```bash
cd ~/.claude/memory
docker compose restart claude-mem-service
```

**Check logs**:
```bash
docker logs claude-mem-service
```

---

## 📚 Related Docs

- [DEPLOYMENT_VERIFIED.md](./DEPLOYMENT_VERIFIED.md) - System status
- [IMPLEMENTATION_COMPLETE.md](./IMPLEMENTATION_COMPLETE.md) - Features
- [frontend/DASHBOARD_README.md](./frontend/DASHBOARD_README.md) - UI guide
- [Plan file](../plans/*.md) - Full implementation plan

---

## ✨ What's Next

Your memory system now:
- ✅ **Captures** valuable information automatically
- ✅ **Surfaces** relevant memories proactively
- ✅ **Scores** memories by importance × relevance × recency
- ✅ **Deduplicates** similar entries
- ✅ **Links** related knowledge in a graph
- ✅ **Visualizes** everything in a beautiful dashboard

**You're ready!** Just use Claude Code normally - the memory system works invisibly in the background, learning from your work and helping you avoid repeating mistakes.

**Pro tip**: Open the dashboard (http://localhost:8100) in a browser tab and keep it visible while you work. You'll see memories being captured in real-time!

