import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './components/layout/AppLayout';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Dashboard } from './pages/Dashboard';
import { Memories } from './pages/Memories';
import { Search } from './pages/Search';
import { Graph } from './pages/Graph';
import { Suggestions } from './pages/Suggestions';
import { Analytics } from './pages/Analytics';
import { Settings } from './pages/Settings';
import { BrainIntelligence } from './pages/BrainIntelligence';
import Documents from './pages/Documents';
import { Sessions } from './pages/Sessions';
import { SystemAdmin } from './pages/SystemAdmin';
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
          <Route index element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
          <Route path="memories" element={<ErrorBoundary><Memories /></ErrorBoundary>} />
          <Route path="documents" element={<ErrorBoundary><Documents /></ErrorBoundary>} />
          <Route path="search" element={<ErrorBoundary><Search /></ErrorBoundary>} />
          <Route path="graph" element={<ErrorBoundary><Graph /></ErrorBoundary>} />
          <Route path="analytics" element={<ErrorBoundary><Analytics /></ErrorBoundary>} />
          <Route path="brain" element={<ErrorBoundary><BrainIntelligence /></ErrorBoundary>} />
          <Route path="suggestions" element={<ErrorBoundary><Suggestions /></ErrorBoundary>} />
          <Route path="sessions" element={<ErrorBoundary><Sessions /></ErrorBoundary>} />
          <Route path="admin" element={<ErrorBoundary><SystemAdmin /></ErrorBoundary>} />
          <Route path="settings" element={<ErrorBoundary><Settings /></ErrorBoundary>} />
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
