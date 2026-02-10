import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // API routes — proxy to backend
      '/memories': 'http://claude-mem-api:8100',
      '/documents': 'http://claude-mem-api:8100',
      '/health': 'http://claude-mem-api:8100',
      '/stats': 'http://claude-mem-api:8100',
      '/graph': 'http://claude-mem-api:8100',
      '/context': 'http://claude-mem-api:8100',
      '/consolidate': 'http://claude-mem-api:8100',
      '/migrate': 'http://claude-mem-api:8100',
      '/embed': 'http://claude-mem-api:8100',
      '/notifications': 'http://claude-mem-api:8100',
      '/settings': 'http://claude-mem-api:8100',
      '/processes': 'http://claude-mem-api:8100',
      '/jobs': 'http://claude-mem-api:8100',
      '/logs': 'http://claude-mem-api:8100',
      '/scheduler': 'http://claude-mem-api:8100',
      '/database': 'http://claude-mem-api:8100',
      '/indexing': 'http://claude-mem-api:8100',
      '/brain': 'http://claude-mem-api:8100',
      '/docs': 'http://claude-mem-api:8100',
      '/openapi.json': 'http://claude-mem-api:8100',
      // WebSocket proxy
      '/ws': {
        target: 'http://claude-mem-api:8100',
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
