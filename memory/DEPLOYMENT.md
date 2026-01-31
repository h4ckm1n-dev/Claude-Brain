# 🚀 Claude Memory Dashboard - Deployment Guide

Complete guide for running the Claude Memory System with the beautiful React dashboard.

---

## 📋 Table of Contents

- [Quick Start (Development)](#quick-start-development)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Environment Configuration](#environment-configuration)
- [Troubleshooting](#troubleshooting)

---

## ⚡ Quick Start (Development)

The fastest way to get started with separate frontend and backend servers.

### Prerequisites

- Node.js 20+ (for frontend)
- Python 3.11+ (for backend)
- Docker (for Qdrant and Neo4j)

### Step 1: Start Infrastructure

```bash
cd /Users/h4ckm1n/.claude/memory
docker compose up -d
```

This starts:
- **Qdrant** (vector database) at http://localhost:6333
- **Neo4j** (knowledge graph) at http://localhost:7474
- **Memory Service** (FastAPI) at http://localhost:8100

### Step 2: Start Frontend Dev Server

```bash
cd frontend
npm install   # First time only
npm run dev
```

**Dashboard URL**: http://localhost:5173

The frontend dev server:
- ✅ Hot module replacement (instant updates)
- ✅ TypeScript type checking
- ✅ Fast refresh on save
- ✅ Source maps for debugging

### Step 3: Verify Everything Works

```bash
# Check API health
curl http://localhost:8100/health

# Check Qdrant
curl http://localhost:6333/collections

# Check Neo4j
curl http://localhost:7474
```

Open http://localhost:5173 and you should see the dashboard!

---

## 🏭 Production Deployment

Single unified deployment where FastAPI serves both API and dashboard.

### Option 1: Local Production Build

**Step 1: Build Frontend**

```bash
cd /Users/h4ckm1n/.claude/memory/frontend
npm run build
```

This creates an optimized production bundle in `frontend/dist/`.

**Step 2: Start Services**

```bash
cd /Users/h4ckm1n/.claude/memory
docker compose up -d
```

**Dashboard URL**: http://localhost:8100

The FastAPI server now serves:
- `/health`, `/stats`, `/memories/*` → API endpoints
- `/`, `/dashboard`, `/graph`, etc. → React dashboard (SPA)
- `/assets/*` → Static files (JS, CSS, images)

### Option 2: Docker Multi-Stage Build

**Step 1: Rebuild Docker Image**

```bash
cd /Users/h4ckm1n/.claude/memory
docker compose build claude-mem-service
```

This uses the multi-stage Dockerfile:
1. Stage 1: Builds React frontend with Node
2. Stage 2: Copies built files into Python image

**Step 2: Start Services**

```bash
docker compose up -d
```

**Dashboard URL**: http://localhost:8100

---

## 🐳 Docker Deployment

### Full Stack with Dashboard

The updated `docker-compose.yml` and `Dockerfile` now include the dashboard.

**Build and start everything**:

```bash
cd /Users/h4ckm1n/.claude/memory

# Build with dashboard included
docker compose build

# Start all services
docker compose up -d

# View logs
docker compose logs -f claude-mem-service
```

**Services**:
- Dashboard + API: http://localhost:8100
- Qdrant UI: http://localhost:6333/dashboard
- Neo4j Browser: http://localhost:7474

### Rebuild After Dashboard Changes

If you modify the dashboard:

```bash
# Option 1: Rebuild Docker image (includes frontend build)
docker compose build claude-mem-service
docker compose up -d

# Option 2: Build locally and restart (faster for dev)
cd frontend
npm run build
cd ..
docker compose restart claude-mem-service
```

---

## 🔧 Environment Configuration

### Frontend Environment Variables

Create `frontend/.env`:

```env
# API base URL (default: same origin in production)
VITE_API_URL=http://localhost:8100

# Optional: Enable debug mode
VITE_DEBUG=false
```

### Backend Environment Variables

Already configured in `docker-compose.yml`:

```yaml
environment:
  - QDRANT_HOST=claude-mem-qdrant
  - QDRANT_PORT=6333
  - NEO4J_URI=bolt://claude-mem-neo4j:7687
  - NEO4J_USER=neo4j
  - NEO4J_PASSWORD=memory_graph_2024
  - LOG_LEVEL=INFO
```

---

## 🎨 Dashboard Features

Once running, the dashboard provides:

### 7 Pages

1. **Dashboard** (`/`) - Overview with stats and charts
2. **Memories** (`/memories`) - Full CRUD operations
3. **Search** (`/search`) - Hybrid search (semantic + keyword)
4. **Graph** (`/graph`) - Interactive knowledge graph
5. **Suggestions** (`/suggestions`) - Context-aware recommendations
6. **Consolidation** (`/consolidation`) - Memory cleanup
7. **Analytics** (`/analytics`) - Advanced insights

### Key Features

- ✅ Real-time stats and health monitoring
- ✅ Beautiful charts (Recharts + custom visualizations)
- ✅ Interactive graph visualization (Cytoscape)
- ✅ Advanced search with 3 modes
- ✅ Memory CRUD with type-specific fields
- ✅ Dark theme with glass morphism effects
- ✅ Responsive design (desktop, tablet, mobile)
- ✅ Keyboard shortcuts
- ✅ Export functionality

---

## 🔍 Troubleshooting

### Dashboard shows "API connection failed"

**Check API health**:
```bash
curl http://localhost:8100/health
```

If this fails:
```bash
# Check if service is running
docker ps | grep claude-mem

# View logs
docker compose logs claude-mem-service

# Restart service
docker compose restart claude-mem-service
```

### Frontend dev server won't start

**Error: `EADDRINUSE: address already in use`**

Solution:
```bash
# Kill process on port 5173
lsof -ti:5173 | xargs kill -9

# Or use a different port
npm run dev -- --port 5174
```

**Error: `Module not found`**

Solution:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Docker build fails with "frontend not found"

Make sure `frontend/` directory exists:
```bash
ls -la /Users/h4ckm1n/.claude/memory/frontend
```

If missing, the Dockerfile will skip dashboard (API still works).

### Static files not serving in production

**Check build exists**:
```bash
ls -la /Users/h4ckm1n/.claude/memory/frontend/dist
```

**Rebuild frontend**:
```bash
cd frontend
npm run build
```

**Verify server.py has static file serving**:
```bash
grep -A 5 "FRONTEND_BUILD" src/server.py
```

### Memory service crashes on startup

**Common causes**:
1. Qdrant not running → `docker compose up -d claude-mem-qdrant`
2. Port 8100 in use → `lsof -ti:8100 | xargs kill -9`
3. Python dependencies missing → `pip install -r requirements.txt`

**Check logs**:
```bash
docker compose logs claude-mem-service
```

---

## 📊 Performance Tuning

### Frontend Optimization

- **Code splitting**: Enabled automatically (React Router lazy loading)
- **Bundle size**: ~250KB gzipped (optimized)
- **Caching**: React Query with 30s stale time
- **Images**: Lazy loaded

### Backend Optimization

- **CORS**: Enabled for `*` (restrict in production!)
- **Response caching**: React Query client-side
- **Connection pooling**: Qdrant client reuse
- **Embedding cache**: Models cached in Docker layer

---

## 🔒 Security Considerations

### Development

- CORS set to `*` (allows all origins)
- No authentication required
- Suitable for local development only

### Production Recommendations

1. **Restrict CORS**:
```python
# In src/server.py
allow_origins=["https://your-domain.com"]
```

2. **Add Authentication**:
- API key in headers
- OAuth integration
- JWT tokens

3. **HTTPS Only**:
- Use reverse proxy (nginx, Caddy)
- SSL certificates (Let's Encrypt)

4. **Rate Limiting**:
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

---

## 📈 Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8100/health

# Qdrant health
curl http://localhost:6333/collections

# Neo4j health
curl http://localhost:7474
```

### Metrics

Available at `/stats` endpoint:
```bash
curl http://localhost:8100/stats | jq
```

Response includes:
- Total memories
- Active vs archived
- Memory types breakdown
- Unresolved errors count

### Dashboard Performance

Check browser console for:
- API response times
- Chart render times
- Memory usage

---

## 🚢 Deployment Checklist

Before going to production:

- [ ] Frontend built: `cd frontend && npm run build`
- [ ] Docker images built: `docker compose build`
- [ ] Environment variables configured
- [ ] CORS origins restricted
- [ ] Health checks passing
- [ ] Backup strategy in place
- [ ] Monitoring set up
- [ ] SSL certificates configured (if public)
- [ ] Rate limiting enabled (if public)
- [ ] Documentation updated

---

## 🎯 Next Steps

1. **Development**: `cd frontend && npm run dev`
2. **Production**: `npm run build && docker compose up -d`
3. **Access**: http://localhost:8100
4. **Enjoy**: Beautiful memory visualization! 🧠✨

For more details, see:
- `frontend/DASHBOARD_README.md` - Complete dashboard guide
- `frontend/QUICK_START.md` - 5-minute quick start
- `CLAUDE.md` - Project overview
