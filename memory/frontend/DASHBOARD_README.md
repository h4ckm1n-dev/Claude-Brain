# Claude Memory System Dashboard

A production-ready React + TypeScript dashboard for managing and exploring the Claude Memory System.

## Features

### 6 Main Pages

1. **Dashboard** (`/`) - System overview with real-time stats
   - Total memories, active, archived counts
   - Unresolved errors tracking
   - Graph node statistics
   - Memory type distribution chart
   - Recent activity timeline
   - System configuration info

2. **Memories** (`/memories`) - Full CRUD memory management
   - Searchable, filterable table
   - Create new memories with type-specific fields
   - Edit existing memories
   - Pin/unpin (prevent decay)
   - Archive memories
   - Delete with confirmation
   - Pagination (50 per page)
   - Filter by type, project, tags

3. **Search** (`/search`) - Advanced search capabilities
   - Debounced search input
   - Three search modes:
     - **Hybrid** (best) - Dense + Sparse + RRF fusion
     - **Semantic** - Vector similarity only
     - **Keyword** - BM25 keyword matching
   - Filter by type
   - Relevance score display
   - Type-specific result cards (error, decision, pattern, etc.)

4. **Graph** (`/graph`) - Knowledge graph visualization
   - Interactive Cytoscape.js graph
   - Node colors by type (error=red, decision=green, pattern=blue)
   - Relationship edges with labels
   - Click nodes to view details
   - Force-directed layout
   - Legend for node types

5. **Suggestions** (`/suggestions`) - Context-aware recommendations
   - Input project name, keywords, files
   - Get relevant memories based on context
   - Reasoning display (why suggested)
   - Combined relevance score
   - Quick access to suggested memories

6. **Consolidation** (`/consolidation`) - Memory cleanup
   - Configure age threshold
   - Dry-run preview mode
   - Shows metrics:
     - Memories analyzed
     - Consolidated (merged similar)
     - Archived (low value)
     - Deleted (redundant)
     - Kept (high value)
   - Execute consolidation with confirmation

## Technology Stack

- **React 18.3+** - UI framework
- **TypeScript 5.0+** - Type safety
- **Vite 7.2+** - Build tool & dev server
- **React Router 6.20+** - Client-side routing
- **TanStack Query 5.0+** - API state management with caching
- **Axios 1.6+** - HTTP client
- **Tailwind CSS 3.4+** - Utility-first styling
- **shadcn/ui** - Accessible component library
- **Recharts 2.10+** - Charts (pie, line, bar)
- **Cytoscape.js 3.28+** - Knowledge graph visualization
- **React Hook Form 7.49+** - Form state management
- **Zod 3.22+** - Schema validation
- **date-fns 3.0+** - Date formatting
- **Lucide React** - Icon library

## Project Structure

```
frontend/
├── src/
│   ├── api/                    # API client & endpoints
│   │   ├── client.ts           # Axios instance
│   │   └── memories.ts         # Memory API functions
│   ├── components/
│   │   ├── layout/             # Layout components
│   │   │   ├── AppLayout.tsx   # Main layout with sidebar
│   │   │   ├── Sidebar.tsx     # Navigation sidebar
│   │   │   └── Header.tsx      # Page header
│   │   ├── ui/                 # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── select.tsx
│   │   │   ├── table.tsx
│   │   │   ├── badge.tsx
│   │   │   └── alert.tsx
│   │   └── memory/             # Memory-specific components
│   │       └── MemoryDialog.tsx # Create/Edit dialog
│   ├── hooks/                  # Custom React hooks
│   │   ├── useMemories.ts      # React Query hooks
│   │   └── useDebounce.ts      # Debounce hook
│   ├── pages/                  # Page components
│   │   ├── Dashboard.tsx
│   │   ├── Memories.tsx
│   │   ├── Search.tsx
│   │   ├── Graph.tsx
│   │   ├── Suggestions.tsx
│   │   └── Consolidation.tsx
│   ├── types/                  # TypeScript definitions
│   │   └── memory.ts           # Memory types, enums, interfaces
│   ├── lib/                    # Utility functions
│   │   └── utils.ts            # cn() for Tailwind class merging
│   ├── App.tsx                 # Root component with routing
│   ├── main.tsx                # Entry point
│   └── index.css               # Global styles + Tailwind
├── public/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── postcss.config.js
```

## Development

### Prerequisites

- Node.js 18+
- npm or yarn
- Memory API running on http://localhost:8100

### Setup

```bash
cd /Users/h4ckm1n/.claude/memory/frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Access at http://localhost:5173
```

### Environment Variables

Create `.env` file:

```env
VITE_API_URL=http://localhost:8100
```

For production (served from FastAPI), this can be empty or `/` (same origin).

## Production Build

### Build Frontend

```bash
npm run build
```

Output: `dist/` directory with optimized static files.

### Integrate with FastAPI

The Memory API server will serve the built dashboard.

Update `/Users/h4ckm1n/.claude/memory/src/server.py`:

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Add after creating app
FRONTEND_BUILD = os.path.join(os.path.dirname(__file__), "../frontend/dist")

# Serve static files
if os.path.exists(FRONTEND_BUILD):
    app.mount("/assets", StaticFiles(directory=f"{FRONTEND_BUILD}/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve React SPA for all non-API routes."""
        file_path = os.path.join(FRONTEND_BUILD, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        # Return index.html for client-side routing
        return FileResponse(os.path.join(FRONTEND_BUILD, "index.html"))
```

### Docker Multi-Stage Build

Update `Dockerfile`:

```dockerfile
# Stage 1: Build frontend
FROM node:20 AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python + FastAPI
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8100"]
```

### Access Dashboard

After building and deploying:

- **Development**: http://localhost:5173
- **Production**: http://localhost:8100

## API Integration

All API calls go through `/api/memories.ts` using Axios.

### Key Endpoints Used

- `GET /health` - System health check
- `GET /stats` - Memory statistics
- `GET /graph/stats` - Graph statistics
- `GET /memories` - List memories (with filters)
- `GET /memories/:id` - Get single memory
- `POST /memories` - Create memory
- `PUT /memories/:id` - Update memory
- `DELETE /memories/:id` - Delete memory
- `POST /memories/search` - Search memories (hybrid/semantic/keyword)
- `POST /memories/:id/pin` - Pin memory
- `POST /memories/:id/archive` - Archive memory
- `POST /memories/suggest` - Get suggestions
- `POST /consolidate` - Run consolidation
- `GET /graph/timeline` - Get graph data

## Type Safety

All API responses are typed using TypeScript interfaces in `src/types/memory.ts`:

- `Memory` - Complete memory object
- `MemoryCreate` - Create memory payload
- `SearchQuery` - Search request
- `SearchResult` - Search response with score
- `HealthResponse` - System health
- `StatsResponse` - Statistics
- `GraphStats` - Graph statistics
- `SuggestionRequest` - Suggestion request
- `Suggestion` - Suggestion response
- `ConsolidateRequest` - Consolidation config
- `ConsolidateResult` - Consolidation result

Enums:
- `MemoryType` - error, docs, decision, pattern, learning, context
- `MemoryTier` - episodic, semantic, procedural
- `RelationType` - causes, fixes, contradicts, supports, follows, related, supersedes, similar_to

## Features Implemented

### ✅ Core Features
- [x] Real-time system health monitoring (polling every 10s)
- [x] Full CRUD operations for memories
- [x] Advanced search (semantic, keyword, hybrid)
- [x] Knowledge graph visualization
- [x] Context-aware suggestions
- [x] Memory consolidation with dry-run
- [x] Type-specific fields (error, decision, pattern)
- [x] Pin/unpin memories
- [x] Archive memories
- [x] Pagination
- [x] Filtering by type, project, tags
- [x] Debounced search input
- [x] Loading states
- [x] Error handling

### 🎨 UI/UX
- [x] Responsive design (mobile-friendly)
- [x] Tailwind CSS utility classes
- [x] shadcn/ui component library
- [x] Sidebar navigation
- [x] Consistent layout
- [x] Color-coded memory types
- [x] Badge components
- [x] Card-based layout
- [x] Modal dialogs
- [x] Hover states
- [x] Transition animations

### ⚡ Performance
- [x] React Query caching
- [x] Automatic cache invalidation
- [x] Optimistic updates (mutations)
- [x] Debounced search (500ms)
- [x] Lazy loading
- [x] Code splitting (per page)
- [x] Vite HMR (Hot Module Replacement)

### ♿ Accessibility
- [x] Semantic HTML
- [x] ARIA labels
- [x] Keyboard navigation
- [x] Focus indicators
- [x] Screen reader compatible
- [x] Color contrast (WCAG AA)

## Performance Metrics

**Expected Performance:**
- Dashboard load: <2s
- Search results: <1s (with debounce)
- Graph rendering: <3s for 100 nodes
- Bundle size: ~250KB gzipped
- API response caching: 5s stale time

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Known Limitations

1. **Graph Page**: Limited to 100 nodes for performance
2. **Pagination**: Client-side only (no server-side cursor)
3. **Search**: Requires minimum 1 character query
4. **Consolidation**: No undo after execution (only dry-run preview)
5. **Real-time Updates**: Polling-based (not WebSocket)

## Future Enhancements

- [ ] Dark mode toggle
- [ ] Export memories to JSON/CSV
- [ ] Import memories from file
- [ ] Bulk operations (multi-select)
- [ ] Memory timeline view
- [ ] Advanced graph filters
- [ ] Search history
- [ ] Saved searches
- [ ] Keyboard shortcuts
- [ ] Toast notifications
- [ ] Error boundaries
- [ ] Skeleton loaders
- [ ] Infinite scroll
- [ ] WebSocket real-time updates

## Troubleshooting

### API Connection Failed

Check:
1. Memory API is running: `curl http://localhost:8100/health`
2. CORS is enabled in FastAPI
3. `.env` file has correct `VITE_API_URL`

### TypeScript Errors

Run:
```bash
npm run build
```

Fix any type errors before running dev server.

### Styles Not Loading

Ensure Tailwind is configured:
1. `tailwind.config.js` exists
2. `postcss.config.js` exists
3. `index.css` has Tailwind directives

### Graph Not Rendering

Check:
1. `cytoscape` is installed
2. Graph data has correct format
3. Container ref is attached
4. Browser console for errors

## Contributing

1. Follow TypeScript strict mode
2. Use shadcn/ui components
3. Maintain type safety
4. Add loading states
5. Handle errors gracefully
6. Keep components small (<300 lines)
7. Use React Query for API state
8. Follow Tailwind utility-first approach

## License

Part of Claude Memory System - Internal Tool

## Support

For issues or questions, check:
- Memory API logs: `/Users/h4ckm1n/.claude/memory/logs/`
- Browser console errors
- Network tab in DevTools
- FastAPI docs: http://localhost:8100/docs
