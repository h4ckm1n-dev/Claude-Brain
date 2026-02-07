import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/admin';

export const adminKeys = {
  all: ['admin'] as const,
  cache: () => [...adminKeys.all, 'cache'] as const,
  database: () => [...adminKeys.all, 'database'] as const,
  scheduler: () => [...adminKeys.all, 'scheduler'] as const,
  jobs: (limit?: number) => [...adminKeys.all, 'jobs', limit] as const,
  notifications: () => [...adminKeys.all, 'notifications'] as const,
  notificationStats: () => [...adminKeys.all, 'notification-stats'] as const,
  suggestions: () => [...adminKeys.all, 'suggestions'] as const,
  suggestionStats: () => [...adminKeys.all, 'suggestion-stats'] as const,
  backups: () => [...adminKeys.all, 'backups'] as const,
  health: () => [...adminKeys.all, 'health'] as const,
  indexingFolders: () => [...adminKeys.all, 'indexing-folders'] as const,
  watcher: () => [...adminKeys.all, 'watcher'] as const,
};

// Cache
export const useCacheStats = () =>
  useQuery({
    queryKey: adminKeys.cache(),
    queryFn: api.getCacheStats,
    staleTime: 30000,
  });

export const useClearCache = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.clearCache,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.cache() });
    },
  });
};

// Jobs
export const useJobs = (limit: number = 20) =>
  useQuery({
    queryKey: adminKeys.jobs(limit),
    queryFn: () => api.listJobs(limit),
    refetchInterval: 10000,
  });

export const useCancelJob = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.cancelJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.jobs() });
    },
  });
};

// Scheduler
export const useSchedulerStatus = () =>
  useQuery({
    queryKey: adminKeys.scheduler(),
    queryFn: api.getSchedulerStatus,
    refetchInterval: 30000,
  });

export const useTriggerScheduledJob = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.triggerScheduledJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.scheduler() });
      queryClient.invalidateQueries({ queryKey: adminKeys.jobs() });
    },
  });
};

export const useTriggerAllScheduledJobs = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.triggerAllScheduledJobs,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.scheduler() });
      queryClient.invalidateQueries({ queryKey: adminKeys.jobs() });
    },
  });
};

// Database
export const useDatabaseStats = () =>
  useQuery({
    queryKey: adminKeys.database(),
    queryFn: api.getDatabaseStats,
    staleTime: 60000,
  });

// Notifications
export const useNotificationStats = () =>
  useQuery({
    queryKey: adminKeys.notificationStats(),
    queryFn: api.getNotificationStats,
    refetchInterval: 30000,
  });

export const useClearAllNotifications = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.clearAllNotifications,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.notifications() });
      queryClient.invalidateQueries({ queryKey: adminKeys.notificationStats() });
    },
  });
};

// Suggestions
export const useSuggestionThrottle = (userId?: string) =>
  useQuery({
    queryKey: [...adminKeys.suggestions(), userId],
    queryFn: () => api.getSuggestionThrottleStatus(userId),
    staleTime: 60000,
  });

export const useSuggestionFeedback = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, wasUseful }: { userId: string; wasUseful: boolean }) =>
      api.submitSuggestionFeedback(userId, wasUseful),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.suggestions() });
      queryClient.invalidateQueries({ queryKey: adminKeys.suggestionStats() });
    },
  });
};

export const useSuggestionStats = (userId?: string) =>
  useQuery({
    queryKey: [...adminKeys.suggestionStats(), userId],
    queryFn: () => api.getSuggestionStats(userId),
    staleTime: 60000,
  });

// Export & Backup
export const useExportMemories = () =>
  useMutation({
    mutationFn: api.exportMemories,
  });

export const useCreateBackup = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createBackup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.backups() });
    },
  });
};

export const useBackups = () =>
  useQuery({
    queryKey: adminKeys.backups(),
    queryFn: api.listBackups,
    staleTime: 60000,
  });

// Health
export const useDetailedHealth = () =>
  useQuery({
    queryKey: adminKeys.health(),
    queryFn: api.getDetailedHealth,
    refetchInterval: 30000,
  });

// Indexing
export const useTriggerReindex = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.triggerReindex,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
};

export const useIndexingFolders = () =>
  useQuery({
    queryKey: adminKeys.indexingFolders(),
    queryFn: api.getIndexingFolders,
  });

export const useUpdateIndexingFolders = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.updateIndexingFolders,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.indexingFolders() });
    },
  });
};

// Watcher
export const useWatcherStatus = () =>
  useQuery({
    queryKey: adminKeys.watcher(),
    queryFn: api.getWatcherStatus,
    refetchInterval: 15000,
  });

export const useStartWatcher = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.startWatcher,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.watcher() });
    },
  });
};

export const useStopWatcher = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.stopWatcher,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.watcher() });
    },
  });
};
