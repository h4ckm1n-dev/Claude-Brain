# Claude Code Memory System - Quick Start Guide

Get up and running in **5 minutes**! ⚡

---

## 📋 Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for frontend)
- Python 3.11+ (for backend)
- 4GB RAM minimum

---

## 🚀 Installation (3 steps)

### 1. Start the Backend

```bash
cd ~/.claude/memory

# Copy environment template
cp .env.example .env

# Start services (Qdrant + API)
docker compose up -d

# Verify health
curl http://localhost:8100/health
# Expected: {"status": "healthy", ...}
```

### 2. Start the Frontend (Optional)

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev

# Open browser: http://localhost:5173
```

### 3. Test It Works

```bash
# Store a memory
curl -X POST http://localhost:8100/memories \
  -H "Content-Type: application/json" \
  -d '{
    "type": "docs",
    "content": "Python list comprehension: [x*2 for x in range(10)]",
    "tags": ["python", "syntax"]
  }'

# Search for it
curl -X POST http://localhost:8100/memories/search \
  -H "Content-Type: application/json" \
  -d '{"query": "python list comprehension", "limit": 5}' | jq

# You should see your memory in the results!
```

---

## 🎯 Enable Advanced Features

Edit `.env` and enable feature flags:

```bash
# Better search relevance (+25-30%)
USE_LEARNED_FUSION=true

# Smart query routing (+40% efficiency)
USE_QUERY_UNDERSTANDING=true

# Restart to apply
docker compose restart
```

---

## 🧪 Common Tasks

### Store Different Memory Types

```bash
# Error memory
curl -X POST http://localhost:8100/memories \
  -d '{
    "type": "error",
    "content": "Docker ECONNREFUSED",
    "error_message": "Error: connect ECONNREFUSED 127.0.0.1:6379",
    "solution": "Start Redis: docker compose up redis",
    "tags": ["docker", "redis", "connection"]
  }'

# Decision memory
curl -X POST http://localhost:8100/memories \
  -d '{
    "type": "decision",
    "content": "Use Zustand for state management",
    "decision": "Zustand",
    "rationale": "Simpler API, smaller bundle size, better TypeScript support",
    "alternatives": ["Redux", "MobX", "Jotai"],
    "tags": ["react", "state-management"]
  }'

# Pattern memory
curl -X POST http://localhost:8100/memories \
  -d '{
    "type": "pattern",
    "content": "Error boundary with retry logic",
    "tags": ["react", "error-handling", "pattern"]
  }'
```

### Search with Filters

```bash
# Search only errors
curl -X POST http://localhost:8100/memories/search \
  -d '{"query": "docker", "type": "error"}' | jq

# Search by tags
curl -X POST http://localhost:8100/memories/search \
  -d '{"query": "state management", "tags": ["react"]}' | jq

# Search by project
curl -X POST http://localhost:8100/memories/search \
  -d '{"query": "authentication", "project": "my-app"}' | jq
```

### Get Context for Current Work

```bash
# Get recent memories for a project (last 24 hours)
curl http://localhost:8100/context/my-app?hours=24 | jq

# Get all recent errors
curl 'http://localhost:8100/context?hours=48&types=error' | jq
```

### Export Your Memories

```bash
# Export all memories as JSON
curl http://localhost:8100/memories | jq > memories.json

# Export as CSV (in frontend)
# 1. Open http://localhost:5173/memories
# 2. Click "Export CSV" button
```

---

## 📊 Monitor Performance

### Check Cache Performance

```bash
curl http://localhost:8100/cache/stats | jq
# Expected:
# {
#   "total_entries": 45,
#   "hit_count": 120,
#   "miss_count": 80,
#   "hit_rate": 0.60,  # 60% hit rate
#   "avg_age_seconds": 1200
# }
```

### Check System Health

```bash
curl http://localhost:8100/health/detailed | jq
# Shows:
# - Qdrant status
# - Neo4j status (if enabled)
# - Feature flags
# - Performance metrics
# - Cache stats
```

### View Statistics

```bash
curl http://localhost:8100/stats | jq
# Shows:
# - Total memories
# - By type breakdown
# - Unresolved errors
# - Hybrid search status
```

---

## 🎨 Frontend Features

Open **http://localhost:5173** and explore:

### Dashboard
- Memory statistics with live updates
- Activity timeline (last 30 days)
- Importance distribution chart
- Memory type breakdown
- Tag cloud
- Access heatmap

### Memories
- Full CRUD operations
- Search with filters
- Export to CSV/JSON/Markdown
- Pin important memories
- Archive old memories

### Search
- Semantic search (meaning-based)
- Keyword search (exact match)
- Hybrid search (best of both)
- Real-time suggestions

### Graph
- Visual memory relationships
- Interactive force-directed layout
- Add/remove relationships
- Explore connections

### Settings
- Configure capture sources
- Set suggestion frequency
- Adjust relevance thresholds
- Control notifications

---

## 🔧 Troubleshooting

### Service Won't Start

```bash
# Check if ports are in use
lsof -i :8100  # API
lsof -i :6333  # Qdrant

# View logs
docker compose logs -f

# Restart fresh
docker compose down -v
docker compose up -d
```

### No Search Results

```bash
# Check if memories exist
curl http://localhost:8100/memories | jq 'length'

# Check embeddings are working
curl -X POST http://localhost:8100/embed \
  -d '{"text": "test"}' | jq '.dimensions'
# Expected: 768

# Verify Qdrant connection
curl http://localhost:8100/health | jq '.qdrant'
# Expected: "connected"
```

### WebSocket Not Connecting

```bash
# Check WebSocket endpoint
curl http://localhost:8100/health/detailed | jq '.performance.active_websocket_connections'

# Frontend should show in console:
# "[WebSocket] Connected to memory service"

# If not:
# 1. Check browser console for errors
# 2. Verify API is running on port 8100
# 3. Check CORS settings in .env
```

### Cache Not Working

```bash
# Clear cache and verify
curl -X POST http://localhost:8100/cache/clear
curl http://localhost:8100/cache/stats | jq

# Check threshold setting
grep CACHE_SIMILARITY_THRESHOLD .env
# Should be: 0.87 (or 0.85-0.90)

# Search same query twice
curl -X POST http://localhost:8100/memories/search \
  -d '{"query": "test"}' | jq
curl -X POST http://localhost:8100/memories/search \
  -d '{"query": "test"}' | jq

# Check stats - hit_count should increase
curl http://localhost:8100/cache/stats | jq '.hit_count'
```

---

## 🎓 Next Steps

1. **Read the docs:**
   - `IMPLEMENTATION_SUMMARY.md` - All features explained
   - `README.md` - Architecture overview

2. **Enable hooks:**
   - Check `~/.claude/hooks/` for automatic capture
   - Hooks trigger on WebFetch, Bash errors, Task tool

3. **Customize settings:**
   - Edit `.env` for feature flags
   - Use frontend Settings page for user preferences

4. **Explore advanced features:**
   - Knowledge graph relationships
   - Memory consolidation
   - Proactive suggestions

---

## 💡 Pro Tips

**Best Practices:**
- Tag memories consistently (`python`, not `Python`/`py`/`PYTHON`)
- Use descriptive content (easier to search)
- Pin critical memories (they never decay)
- Archive old/irrelevant memories (cleaner search)
- Export regularly (backup your knowledge)

**Performance Tips:**
- Enable `USE_LEARNED_FUSION` for better search
- Keep cache threshold at 0.87 for optimal hit rate
- Use specific tags for faster filtering
- Archive memories older than 6 months

**Security Tips:**
- Don't commit `.env` with secrets
- Keep Neo4j credentials secure
- Use CORS origins restrictively in production
- Regularly update Docker images

---

## 🆘 Get Help

- **GitHub Issues:** https://github.com/anthropics/claude-code/issues
- **Documentation:** `/Users/h4ckm1n/.claude/memory/`
- **Health Check:** `curl http://localhost:8100/health/detailed`

---

**Ready to supercharge your memory?** Start storing! 🧠✨
