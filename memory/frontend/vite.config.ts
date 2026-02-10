import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Core service (memories CRUD, consolidation, forgetting, embed)
      '/memories': 'http://claude-mem-core:8100',
      '/consolidate': 'http://claude-mem-core:8100',
      '/forgetting': 'http://claude-mem-core:8100',
      '/migrate': 'http://claude-mem-core:8100',
      '/embed': 'http://claude-mem-core:8100',
      // Search service
      '/search': 'http://claude-mem-search:8103',
      '/context': 'http://claude-mem-search:8103',
      '/query': 'http://claude-mem-search:8103',
      // Graph service
      '/graph': 'http://claude-mem-graph:8104',
      // Brain service
      '/brain': 'http://claude-mem-brain:8105',
      '/inference': 'http://claude-mem-brain:8105',
      // Quality service
      '/quality': 'http://claude-mem-quality:8106',
      '/lifecycle': 'http://claude-mem-quality:8106',
      // Analytics service
      '/analytics': 'http://claude-mem-analytics:8107',
      '/recommendations': 'http://claude-mem-analytics:8107',
      '/insights': 'http://claude-mem-analytics:8107',
      // Admin service (health, stats, settings, jobs, logs, etc.)
      '/health': 'http://claude-mem-admin:8108',
      '/stats': 'http://claude-mem-admin:8108',
      '/notifications': 'http://claude-mem-admin:8108',
      '/settings': 'http://claude-mem-admin:8108',
      '/processes': 'http://claude-mem-admin:8108',
      '/jobs': 'http://claude-mem-admin:8108',
      '/logs': 'http://claude-mem-admin:8108',
      '/database': 'http://claude-mem-admin:8108',
      '/documents': 'http://claude-mem-admin:8108',
      '/indexing': 'http://claude-mem-admin:8108',
      '/sessions': 'http://claude-mem-admin:8108',
      '/temporal': 'http://claude-mem-admin:8108',
      '/audit': 'http://claude-mem-admin:8108',
      '/docs': 'http://claude-mem-admin:8108',
      '/openapi.json': 'http://claude-mem-admin:8108',
      // Worker service (scheduler)
      '/scheduler': 'http://claude-mem-worker:8101',
      // WebSocket
      '/ws': {
        target: 'http://claude-mem-core:8100',
        ws: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-charts': ['recharts'],
          'vendor-graph': ['cytoscape'],
          'vendor-query': ['@tanstack/react-query'],
        }
      }
    }
  }
})
