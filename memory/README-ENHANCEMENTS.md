# Claude Brain - High-Value Enhancements

All improvements completed! Here's your enhanced memory system with **Advanced Brain Mode**.

---

## 🚀 Latest: Advanced Brain Mode (2026-01-30)

### **15/15 Brain Functions Operational**

Your memory system now has 3 new advanced features beyond the original Full Brain Mode:

#### **1. Emotional Weighting** 🎭
Automatically detects emotional significance in memories and boosts importance.

**Features:**
- Sentiment analysis using keyword detection
- Positive/negative keyword matching
- Intensity modifiers (very, extremely, really)
- Type-specific adjustments (errors, decisions)
- Scheduled job runs daily

**API:**
```bash
# Manual trigger
curl -X POST "http://localhost:8100/brain/emotional-analysis?limit=100"

# View coverage
curl "http://localhost:8100/brain/performance-metrics" | jq '.current.emotional_coverage'
```

#### **2. Interference Detection** 🔀
Finds and resolves contradictory memories automatically.

**Features:**
- Detects semantically similar but contradictory memories
- Auto-resolution (newer/higher importance wins)
- Creates SUPERSEDES relationships
- Maintains knowledge coherence
- Scheduled job runs weekly

**API:**
```bash
# Manual trigger
curl -X POST "http://localhost:8100/brain/detect-conflicts?limit=50"

# View conflicts
curl "http://localhost:8100/brain/performance-metrics" | jq '.conflicts'
```

#### **3. Meta-Learning** 🧠
Self-optimizes system parameters based on performance metrics.

**Features:**
- Tracks performance metrics (importance, access rate, coverage)
- Auto-tunes thresholds for better accuracy
- Saves historical metrics to JSON
- Self-improving system
- Scheduled job runs weekly

**API:**
```bash
# Manual trigger
curl -X POST "http://localhost:8100/brain/meta-learning"

# View metrics
curl "http://localhost:8100/brain/performance-metrics?days=7" | jq
```

#### **Dashboard Integration** 📊
New dashboard section displays:
- Emotional coverage (0-100%)
- Conflicts detected/resolved
- Average importance score
- Access rate
- 7-day performance trends
- System capabilities checklist

**View Dashboard:**
Open browser to: http://localhost:3000

---

## 🎯 What's New (Previous Enhancements)

### **1. Auto File Watcher** 📁
Automatically indexes new/modified documents in background.

**Start the watcher:**
```bash
# Run in background
nohup python3 ~/.claude/memory/scripts/watch_documents.py >> ~/.claude/memory/logs/watcher.log 2>&1 &

# Or run in foreground (with output)
python3 ~/.claude/memory/scripts/watch_documents.py

# Custom interval (check every 10 seconds)
python3 ~/.claude/memory/scripts/watch_documents.py --interval 10
```

**Check status:**
```bash
ps aux | grep watch_documents
tail -f ~/.claude/memory/logs/watcher.log
```

**Stop watcher:**
```bash
pkill -f watch_documents.py
```

---

### **2. Scheduled Memory Consolidation** 🧹
Auto-cleanup runs daily at 3 AM.

**Setup cron job:**
```bash
# Add to crontab
crontab -e

# Add this line:
0 3 * * * ~/.claude/memory/scripts/consolidate_memories.sh

# Or run manually:
~/.claude/memory/scripts/consolidate_memories.sh
```

**Check logs:**
```bash
tail ~/.claude/memory/logs/consolidation.log
```

---

### **3. Enhanced Error Capture** 🐛
Captures stack traces, error codes (HTTP, errno), file locations.

**Auto-enabled!** Errors now include:
- Full stack traces
- HTTP status codes (400, 404, 500, etc.)
- System error codes (ECONNREFUSED, ENOENT, etc.)
- File/line locations
- Better categorization

**Search errors:**
```bash
# Find all HTTP errors
mcp search_memory tags=["http-error"]

# Find permission errors with solutions
mcp search_memory tags=["permission"] type=error
```

---

### **4. Memory Pruning** 🗑️
Smart cleanup of old, low-value memories.

**Dry run (preview):**
```bash
python3 ~/.claude/memory/scripts/prune_memories.py --days 30
```

**Actually delete:**
```bash
python3 ~/.claude/memory/scripts/prune_memories.py --days 30 --execute
```

**What gets deleted:**
- ✅ Old unresolved errors (likely fixed elsewhere)
- ✅ Unused context (access_count = 0)
- ✅ Low usefulness score + no access

**What's protected:**
- ❌ Resolved errors (have solutions)
- ❌ Pinned memories
- ❌ Frequently accessed (5+ times)
- ❌ High usefulness (>0.7)
- ❌ Part of knowledge graph (has relations)
- ❌ Decisions & patterns (valuable long-term)

---

### **5. Session Timeline** 📊
See complete workflow chains: prompt → edit → error → solution.

**View last 24 hours:**
```bash
python3 ~/.claude/memory/scripts/session_timeline.py
```

**View last week:**
```bash
python3 ~/.claude/memory/scripts/session_timeline.py --hours 168
```

**Export as JSON:**
```bash
python3 ~/.claude/memory/scripts/session_timeline.py --json timeline.json
```

**Example output:**
```
┌─ Session: 2026-01-30 01:00
│  (12 memories: 3 context, 5 pattern, 2 error, 2 docs)
└─
  2026-01-30 01:05:23 💬 👤 How do I fix docker permission error?
  2026-01-30 01:06:15 📝 ✏️  File Edit: /etc/docker/daemon.json
  2026-01-30 01:07:02 ❌ 🐛 Command failed: docker ps
  2026-01-30 01:08:30 📝 ✅ Solution: docker ps succeeded
```

---

### **6. Automatic NLP Tagging** 🏷️
Extracts tech stack entities and auto-tags memories.

**Tag all memories:**
```bash
python3 ~/.claude/memory/scripts/nlp_tagger.py
```

**Tag specific count:**
```bash
python3 ~/.claude/memory/scripts/nlp_tagger.py --limit 500
```

**Auto-detected entities:**
- **Languages**: python, javascript, typescript, java, go, rust, ruby, php, c++, etc.
- **Frontend**: react, vue, angular, svelte, nextjs, vite, tailwind, etc.
- **Backend**: express, django, flask, fastapi, spring, rails, etc.
- **Databases**: postgresql, mongodb, redis, qdrant, supabase, etc.
- **Cloud**: aws, gcp, azure, docker, kubernetes, terraform, etc.
- **Libraries**: numpy, pandas, axios, lodash, langchain, openai, etc.
- **Errors**: HTTP codes (400, 404, 500), error codes (ECONNREFUSED, ENOENT)

**Better search accuracy:**
```bash
# Find all React-related memories
mcp search_memory tags=["react"]

# Find all database errors
mcp search_memory tags=["postgresql","mongodb"]
```

---

## 🚀 Quick Start Commands

**Start everything:**
```bash
# 1. Start memory service
cd ~/.claude/memory && docker compose up -d

# 2. Start file watcher
nohup python3 ~/.claude/memory/scripts/watch_documents.py >> ~/.claude/memory/logs/watcher.log 2>&1 &

# 3. Setup cron for consolidation
crontab -e
# Add: 0 3 * * * ~/.claude/memory/scripts/consolidate_memories.sh

# 4. Run NLP tagging (one-time)
python3 ~/.claude/memory/scripts/nlp_tagger.py

# 5. Open dashboard
open http://localhost:5173
```

**Maintenance:**
```bash
# View session timeline
python3 ~/.claude/memory/scripts/session_timeline.py

# Prune old memories (dry run)
python3 ~/.claude/memory/scripts/prune_memories.py --days 30

# Manual consolidation
~/.claude/memory/scripts/consolidate_memories.sh

# Check logs
tail -f ~/.claude/memory/logs/watcher.log
tail -f ~/.claude/memory/logs/consolidation.log
```

---

## 📁 File Locations

**Scripts:**
- `~/.claude/memory/scripts/watch_documents.py` - Auto file indexer
- `~/.claude/memory/scripts/consolidate_memories.sh` - Daily consolidation
- `~/.claude/memory/scripts/prune_memories.py` - Smart cleanup
- `~/.claude/memory/scripts/session_timeline.py` - Workflow timeline
- `~/.claude/memory/scripts/nlp_tagger.py` - Auto-tagging
- `~/.claude/memory/scripts/index_documents.py` - Manual indexer (enhanced)

**Hooks:**
- `~/.claude/hooks/error-resolution-detector.sh` - Auto-link solutions
- `~/.claude/hooks/context-loader.sh` - Pre-tool context loading
- `~/.claude/hooks/user-prompt-capture.sh` - Prompt tracking
- `~/.claude/hooks/file-edit-tracker.sh` - Edit tracking
- `~/.claude/hooks/smart-error-capture.sh` - Enhanced error capture
- `~/.claude/hooks/auto-memory-capture.sh` - Tool output capture

**Logs:**
- `~/.claude/memory/logs/watcher.log` - File watcher activity
- `~/.claude/memory/logs/consolidation.log` - Consolidation history

**Data:**
- `~/.claude/memory/data/watch-state.json` - Indexer state

**Dashboard:**
- URL: http://localhost:5173
- Name: **Claude Brain** 🧠
- Favicon: Purple-pink gradient brain icon

---

## 🎯 Workflow Examples

### **Example 1: Debugging Session**
```
User asks: "Why is my API returning 500 errors?"
  ↓ (captured as bug-report)
Claude edits: api/routes.ts
  ↓ (tracked & linked)
Error: npm test → 3 tests failing
  ↓ (captured with stack traces)
Claude fixes code
  ↓
Solution: npm test → all pass!
  ↓ (auto-linked, error marked resolved)
Timeline shows: prompt → edit → error → solution
```

### **Example 2: Auto-Indexing**
```
You create: ~/Documents/project-notes.md
  ↓ (watcher detects change in 30s)
File indexed: 5 chunks created
  ↓ (NLP tags extracted: markdown, project)
Now searchable: "project notes setup"
  ↓
Dashboard shows: new document indexed
```

### **Example 3: Smart Cleanup**
```
Weekly prune: --days 7 --execute
  ↓
Keeps: 50 resolved errors (have solutions)
Keeps: 100 decisions (valuable long-term)
Deletes: 200 old unresolved errors
Deletes: 150 unused context
  ↓
Result: 350 memories removed, 5MB freed
Dashboard shows: 2,200 total memories (was 2,550)
```

---

## 📊 Statistics

**Memory Capture:**
- User prompts: ✅ With intent detection
- File edits: ✅ Linked to prompts
- Errors: ✅ With stack traces + codes
- Solutions: ✅ Auto-linked to errors
- Tool outputs: ✅ Full 10KB (was 500 chars)
- Documents: ✅ Auto-indexed on change

**Memory Organization:**
- Auto-tags: ✅ 100+ tech entities
- Sessions: ✅ Hourly grouping
- Relations: ✅ FOLLOWS, FIXES links
- Quality: ✅ Access count, usefulness score
- Cleanup: ✅ Daily consolidation
- Pruning: ✅ Smart retention rules

**Search & Discovery:**
- Semantic search: ✅ Qdrant vector DB
- Hybrid search: ✅ Dense + sparse
- Tag filtering: ✅ Tech stack tags
- Timeline view: ✅ Workflow chains
- Knowledge graph: ✅ Neo4j relationships

---

## 🎉 What You Get

**Automatic:**
- ✅ New documents indexed within 30 seconds
- ✅ Errors auto-captured with full context
- ✅ Solutions auto-linked when commands succeed
- ✅ Memories auto-tagged with tech stack
- ✅ Daily consolidation removes duplicates
- ✅ Context loaded before you edit files

**On-Demand:**
- ✅ View complete session timelines
- ✅ Prune old low-value memories
- ✅ Search by tech stack tags
- ✅ Export workflow chains as JSON
- ✅ Manual re-indexing with progress bars

**Dashboard:**
- ✅ **Claude Brain** branding
- ✅ Real-time memory updates
- ✅ Beautiful purple brain logo
- ✅ Dark mode enabled by default

---

## 🔧 Troubleshooting

**File watcher not working:**
```bash
# Check if running
ps aux | grep watch_documents

# Check logs
tail -f ~/.claude/memory/logs/watcher.log

# Restart
pkill -f watch_documents.py
nohup python3 ~/.claude/memory/scripts/watch_documents.py >> ~/.claude/memory/logs/watcher.log 2>&1 &
```

**Consolidation not running:**
```bash
# Check crontab
crontab -l

# Run manually
~/.claude/memory/scripts/consolidate_memories.sh

# Check logs
tail ~/.claude/memory/logs/consolidation.log
```

**Memory service down:**
```bash
# Restart
cd ~/.claude/memory && docker compose restart

# Check logs
docker compose logs -f
```

---

## 📈 Future Enhancements (Not Yet Implemented)

Still want more? These are available but not yet built:

8. **Knowledge Graph Visualization** - Interactive graph UI
9. **Cross-Project Memory Sharing** - Global memories across projects
10. **Memory Quality Scoring** - 1-5 star ratings
11. **Voice Notes** - Audio transcription with Whisper
12. **Screenshot OCR** - Extract text from images
13. **Git Integration** - Link commits to decisions
14. **Real-time Collaboration** - Team knowledge base

Let me know if you want any of these!

---

**Built by: Claude (Sonnet 4.5)**
**Date: 2026-01-30**
**Project: Claude Brain Enhanced Memory System** 🧠
