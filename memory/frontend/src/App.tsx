import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './components/layout/AppLayout';
import { Dashboard } from './pages/Dashboard';
import { Memories } from './pages/Memories';
import { Search } from './pages/Search';
import { Graph } from './pages/Graph';
import { Suggestions } from './pages/Suggestions';
import { Consolidation } from './pages/Consolidation';
import { Analytics } from './pages/Analytics';
import { Settings } from './pages/Settings';
import { BrainIntelligence } from './pages/BrainIntelligence';
import Documents from './pages/Documents';
import { useWebSocket } from './hooks/useWebSocket';
import { useTheme } from './hooks/useTheme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5000,
    },
  },
});

function AppContent() {
  // Enable real-time WebSocket updates
  useWebSocket();

  // Apply dark mode based on browser/system preferences
  useTheme();

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="memories" element={<Memories />} />
          <Route path="documents" element={<Documents />} />
          <Route path="search" element={<Search />} />
          <Route path="graph" element={<Graph />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="brain" element={<BrainIntelligence />} />
          <Route path="suggestions" element={<Suggestions />} />
          <Route path="consolidation" element={<Consolidation />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

export default App;
