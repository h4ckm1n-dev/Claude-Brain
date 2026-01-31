# Troubleshooting Guide

Common issues and solutions for the Claude Code Memory System.

---

## 🔍 Quick Diagnostics

Run this health check first:

```bash
cd ~/.claude/memory

# Full system health
curl http://localhost:8100/health/detailed | jq

# Check specific components
curl http://localhost:8100/health | jq '.qdrant'          # "connected"
curl http://localhost:8100/health | jq '.graph_enabled'   # true/false
curl http://localhost:8100/cache/stats | jq               # Cache metrics
docker compose ps                                           # Container status
```

---

## ⚠️ Common Issues

### 1. API Not Responding (503 Error)

**Symptoms:**
- `curl http://localhost:8100/health` fails
- "Connection refused" errors
- Frontend shows "Service Unavailable"

**Diagnosis:**
```bash
# Check if API is running
docker compose ps | grep api

# Check API logs
docker compose logs api | tail -50

# Check port availability
lsof -i :8100
```

**Solutions:**

**A. Port already in use:**
```bash
# Kill process using port 8100
lsof -i :8100 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Or change port in docker-compose.yml
# ports: ["8101:8100"]  # Use 8101 instead
docker compose up -d
```

**B. API crashed:**
```bash
# Check error logs
docker compose logs api | grep -i error

# Common fix: restart
docker compose restart api

# Nuclear option: rebuild
docker compose down
docker compose up -d --build
```

**C. Qdrant not ready:**
```bash
# API waits for Qdrant - check if Qdrant is healthy
curl http://localhost:6333/collections

# If fails, restart Qdrant
docker compose restart qdrant
docker compose restart api  # After Qdrant is up
```

---

### 2. Search Returns No Results

**Symptoms:**
- Memories exist but search finds nothing
- `curl /memories` returns data, `/memories/search` returns `[]`

**Diagnosis:**
```bash
# Check memory count
curl http://localhost:8100/stats | jq '.total_memories'

# Test embedding generation
curl -X POST http://localhost:8100/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}' | jq '.dimensions'
# Expected: 768 (nomic-embed-text-v1.5)

# Check if embeddings exist in Qdrant
docker compose exec qdrant sh -c "curl localhost:6333/collections/memories"
```

**Solutions:**

**A. Embeddings not generated:**
```bash
# Re-embed all memories (migration)
curl -X POST http://localhost:8100/migrate | jq

# This will:
# 1. Create new collection with proper vectors
# 2. Re-embed all memories
# 3. Swap collections
# Time: ~1 min per 1000 memories
```

**B. Search threshold too high:**
```bash
# Lower min_score in search query
curl -X POST http://localhost:8100/memories/search \
  -d '{"query": "test", "min_score": 0.5}' | jq
# Default: 0.7 (may be too strict)

# Check if results exist with lower threshold
curl -X POST http://localhost:8100/memories/search \
  -d '{"query": "test", "min_score": 0.3}' | jq
```

**C. Embedding model mismatch:**
```bash
# Check current model
curl http://localhost:8100/health | jq '.embedding_model'
# Expected: "nomic-ai/nomic-embed-text-v1.5"

# If different, re-migrate:
docker compose down
docker compose up -d
curl -X POST http://localhost:8100/migrate
```

---

### 3. WebSocket Not Connecting

**Symptoms:**
- Frontend console shows WebSocket errors
- No real-time updates
- "WebSocket connection failed" messages

**Diagnosis:**
```bash
# Check if WebSocket endpoint exists
curl -I http://localhost:8100/ws
# Should return: 426 Upgrade Required (correct for WS endpoint)

# Check active connections
curl http://localhost:8100/health/detailed | jq '.performance.active_websocket_connections'

# Test WebSocket with wscat (install: npm install -g wscat)
wscat -c ws://localhost:8100/ws
# Should connect and show: Connected
```

**Solutions:**

**A. CORS blocking WebSocket:**
```bash
# Check .env CORS settings
grep CORS_ORIGINS .env

# Add frontend origin if missing
echo "CORS_ORIGINS=http://localhost:5173,http://localhost:3000" >> .env
docker compose restart api
```

**B. Reverse proxy issues:**
```bash
# If using nginx/Apache, ensure WebSocket upgrade headers:
# Upgrade: websocket
# Connection: Upgrade

# Example nginx config:
# location /ws {
#   proxy_pass http://localhost:8100;
#   proxy_http_version 1.1;
#   proxy_set_header Upgrade $http_upgrade;
#   proxy_set_header Connection "Upgrade";
# }
```

**C. Browser blocking:**
```bash
# Mixed content (HTTPS site → WS:// endpoint)
# Use WSS:// instead of WS:// for HTTPS sites

# Frontend: Change WebSocket URL
# From: ws://localhost:8100/ws
# To:   wss://your-domain.com/ws
```

---

### 4. Cache Not Working (Low Hit Rate)

**Symptoms:**
- Cache hit rate < 30%
- `curl /cache/stats` shows low `hit_rate`
- Search always slow (no cache speedup)

**Diagnosis:**
```bash
# Check cache stats
curl http://localhost:8100/cache/stats | jq

# Check threshold
grep CACHE_SIMILARITY_THRESHOLD .env

# Test cache: search same query twice
time curl -X POST http://localhost:8100/memories/search \
  -d '{"query": "docker error"}' > /dev/null
# First: ~500ms

time curl -X POST http://localhost:8100/memories/search \
  -d '{"query": "docker error"}' > /dev/null
# Second: should be <50ms if cached
```

**Solutions:**

**A. Threshold too high:**
```bash
# Lower threshold in .env
echo "CACHE_SIMILARITY_THRESHOLD=0.87" >> .env
docker compose restart api

# Recommended values:
# 0.87: Balanced (4x hit rate) ✅
# 0.85: Aggressive (high hits, less precise)
# 0.90: Conservative (fewer hits, very precise)
# 0.95: Strict (original, low hit rate)
```

**B. Cache disabled:**
```bash
# Check search calls use_cache=true
curl -X POST http://localhost:8100/memories/search \
  -d '{"query": "test", "use_cache": true}' | jq

# Verify cache collection exists
docker compose exec qdrant sh -c "curl localhost:6333/collections/query_cache"
```

**C. TTL too short:**
```bash
# Increase cache TTL (default: 24 hours)
echo "CACHE_TTL=86400" >> .env  # 24 hours
docker compose restart api

# Clear old cache
curl -X POST http://localhost:8100/cache/clear
```

---

### 5. Memory Not Captured by Hooks

**Symptoms:**
- Bash errors not saved automatically
- WebFetch documentation not stored
- Hooks seem to run but no memories created

**Diagnosis:**
```bash
# Check if hooks are enabled
ls -la ~/.claude/hooks/*.sh

# Test hook directly
bash ~/.claude/hooks/smart-error-capture.sh \
  "docker ps" \
  "Error: Cannot connect to Docker daemon" \
  "1"

# Check hook output
# Should show: "💾 Error captured: ..."

# Verify memory was created
curl http://localhost:8100/memories?type=error | jq 'length'
```

**Solutions:**

**A. Service unavailable:**
```bash
# Hooks have health checks - if API is down, they silently exit
curl http://localhost:8100/health
# If fails, start API:
docker compose up -d
```

**B. Deduplication blocking:**
```bash
# Hooks deduplicate within 1 hour by default
# Wait 1 hour or adjust threshold in hook:

# Edit hook: ~/.claude/hooks/smart-error-capture.sh
# Line ~45: Change min_score from 0.9 to 0.95
# Higher = stricter dedup (allows more similar errors)
```

**C. Settings disabled capture:**
```bash
# Check user settings
curl http://localhost:8100/settings | jq

# Re-enable in frontend:
# http://localhost:5173/settings
# Toggle "Bash Error Capture" ON
```

---

### 6. Frontend Build Errors

**Symptoms:**
- `npm run build` fails
- TypeScript errors
- Module not found errors

**Diagnosis:**
```bash
cd frontend

# Check Node version
node --version  # Should be 18+

# Check dependencies
npm list --depth=0 | grep UNMET
```

**Solutions:**

**A. Outdated dependencies:**
```bash
# Clear and reinstall
rm -rf node_modules package-lock.json
npm install

# Update dependencies
npm update
```

**B. TypeScript errors:**
```bash
# Check for type errors
npm run type-check

# Common fix: regenerate types
npm run build
```

**C. Missing environment variables:**
```bash
# Create .env.local if needed
echo "VITE_API_URL=http://localhost:8100" > .env.local
```

---

### 7. High Memory Usage

**Symptoms:**
- Docker container using > 4GB RAM
- System slowdown
- OOM (out of memory) errors

**Diagnosis:**
```bash
# Check memory usage
docker stats --no-stream

# Check Qdrant memory
docker compose exec qdrant sh -c "curl localhost:6333/metrics"

# Check collection size
curl http://localhost:8100/stats | jq '.total_memories'
```

**Solutions:**

**A. Too many memories:**
```bash
# Archive old memories (soft delete)
# Frontend: Memories page → Select → Archive

# Or consolidate duplicates
curl -X POST http://localhost:8100/consolidate \
  -d '{"older_than_days": 30}' | jq

# Or delete old archived
# (Manual: requires DB access)
```

**B. Cache too large:**
```bash
# Clear cache
curl -X POST http://localhost:8100/cache/clear

# Reduce max entries in .env
echo "MAX_CACHE_ENTRIES=500" >> .env
docker compose restart api
```

**C. Increase Docker limits:**
```bash
# Edit docker-compose.yml, add to services:
# api:
#   deploy:
#     resources:
#       limits:
#         memory: 2G

docker compose up -d
```

---

### 8. Slow Search (> 1 second)

**Symptoms:**
- Search takes > 1 second
- API response slow
- Timeout errors

**Diagnosis:**
```bash
# Time a search
time curl -X POST http://localhost:8100/memories/search \
  -d '{"query": "test", "limit": 10}' | jq > /dev/null

# Check reranking status
curl http://localhost:8100/health | jq '.features.cross_encoder_reranking'

# Check memory count
curl http://localhost:8100/stats | jq '.total_memories'
```

**Solutions:**

**A. Disable reranking for speed:**
```bash
# Reranking adds 50-100ms but improves accuracy 30-50%
# Disable if speed > accuracy:

curl -X POST http://localhost:8100/memories/search \
  -d '{"query": "test", "use_reranking": false}' | jq

# Or set in .env:
echo "RERANKING_ENABLED=false" >> .env
docker compose restart api
```

**B. Reduce candidate limit:**
```bash
# Lower limit = faster search
curl -X POST http://localhost:8100/memories/search \
  -d '{"query": "test", "limit": 5}' | jq  # Instead of 50
```

**C. Use exact match for known terms:**
```bash
# Enable query understanding for auto-routing
echo "USE_QUERY_UNDERSTANDING=true" >> .env
docker compose restart api

# Exact matches will use sparse-only (faster)
curl -X POST http://localhost:8100/memories/search \
  -d '{"query": "ECONNREFUSED"}' | jq
```

---

## 🛠️ Advanced Debugging

### Enable Debug Logging

```bash
# .env
LOG_LEVEL=DEBUG

docker compose restart api

# View logs
docker compose logs -f api | grep DEBUG
```

### Check Qdrant Directly

```bash
# List collections
curl http://localhost:6333/collections | jq

# Get collection info
curl http://localhost:6333/collections/memories | jq

# Count points
curl http://localhost:6333/collections/memories/points/count | jq

# Search directly (bypasses API)
curl -X POST http://localhost:6333/collections/memories/points/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": [0.1, 0.2, ...],  # 768-dim vector
    "limit": 5
  }' | jq
```

### Check Neo4j (if enabled)

```bash
# Open Cypher shell
docker compose exec neo4j cypher-shell -u neo4j -p <password>

# Count memory nodes
MATCH (m:Memory) RETURN count(m);

# Show relationships
MATCH (m1:Memory)-[r]->(m2:Memory) RETURN m1, r, m2 LIMIT 10;
```

### Profile Slow Queries

```bash
# Add timing to search
time curl -X POST http://localhost:8100/memories/search \
  -d '{"query": "test"}' -w "\n%{time_total}s\n" | jq

# Check cache impact
curl -X POST http://localhost:8100/cache/clear
time curl -X POST http://localhost:8100/memories/search -d '{"query": "test"}'  # Cold
time curl -X POST http://localhost:8100/memories/search -d '{"query": "test"}'  # Warm
```

---

## 🆘 Nuclear Options

When all else fails:

### Full Reset

```bash
cd ~/.claude/memory

# Stop everything
docker compose down -v  # ⚠️ Deletes all data!

# Clean start
docker compose up -d

# Verify health
curl http://localhost:8100/health | jq
```

### Backup & Restore

```bash
# Backup
curl http://localhost:8100/memories > backup.json

# Reset system
docker compose down -v
docker compose up -d

# Restore
cat backup.json | jq -c '.[]' | while read memory; do
  curl -X POST http://localhost:8100/memories \
    -H "Content-Type: application/json" \
    -d "$memory"
done
```

---

## 📞 Get Help

Still stuck? Check:

1. **Logs:** `docker compose logs -f`
2. **Health:** `curl http://localhost:8100/health/detailed | jq`
3. **GitHub Issues:** Report bugs with logs attached
4. **Discord:** Join Claude community for help

---

**Most issues are fixed by:** `docker compose restart` 😉
