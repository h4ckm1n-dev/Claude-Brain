import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/memories';
import type { MemoryCreate, SearchQuery, SuggestionRequest, ConsolidateRequest } from '../types/memory';

// Query keys
export const memoryKeys = {
  all: ['memories'] as const,
  lists: () => [...memoryKeys.all, 'list'] as const,
  list: (filters: string) => [...memoryKeys.lists(), filters] as const,
  details: () => [...memoryKeys.all, 'detail'] as const,
  detail: (id: string) => [...memoryKeys.details(), id] as const,
  search: (query: SearchQuery) => [...memoryKeys.all, 'search', query] as const,
  suggestions: (req: SuggestionRequest) => [...memoryKeys.all, 'suggestions', req] as const,
  stats: ['stats'] as const,
  health: ['health'] as const,
  graphStats: ['graph', 'stats'] as const,
};

// Queries
export const useMemories = (params?: any) => {
  return useQuery({
    queryKey: memoryKeys.list(JSON.stringify(params)),
    queryFn: () => api.getMemories(params),
  });
};

export const useMemory = (id: string) => {
  return useQuery({
    queryKey: memoryKeys.detail(id),
    queryFn: () => api.getMemory(id),
    enabled: !!id,
  });
};

export const useSearchMemories = (query: SearchQuery) => {
  return useQuery({
    queryKey: memoryKeys.search(query),
    queryFn: () => api.searchMemories(query),
    enabled: query.query.length > 0,
  });
};

export const useStats = () => {
  return useQuery({
    queryKey: memoryKeys.stats,
    queryFn: api.getStats,
    refetchInterval: 30000, // Refresh every 30s
  });
};

export const useHealth = () => {
  return useQuery({
    queryKey: memoryKeys.health,
    queryFn: api.getHealth,
    refetchInterval: 10000, // Refresh every 10s
  });
};

export const useGraphStats = () => {
  return useQuery({
    queryKey: memoryKeys.graphStats,
    queryFn: api.getGraphStats,
    refetchInterval: 30000,
  });
};

export const useSuggestions = (request: SuggestionRequest) => {
  return useQuery({
    queryKey: memoryKeys.suggestions(request),
    queryFn: () => api.getSuggestions(request),
  });
};

// Mutations
export const useCreateMemory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: MemoryCreate) => api.createMemory(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: memoryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: memoryKeys.stats });
    },
  });
};

export const useUpdateMemory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<any> }) => api.updateMemory(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: memoryKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: memoryKeys.lists() });
    },
  });
};

export const useDeleteMemory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteMemory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: memoryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: memoryKeys.stats });
    },
  });
};

export const usePinMemory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.pinMemory(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: memoryKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: memoryKeys.lists() });
    },
  });
};

export const useArchiveMemory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.archiveMemory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: memoryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: memoryKeys.stats });
    },
  });
};

export const useConsolidateMemories = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: ConsolidateRequest) => api.consolidateMemories(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: memoryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: memoryKeys.stats });
    },
  });
};

// --- New Memory Hooks ---

export const useDraftMemory = () =>
  useMutation({
    mutationFn: (data: MemoryCreate) => api.draftMemory(data),
  });

export const useBulkStore = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (memories: MemoryCreate[]) => api.bulkStoreMemories(memories),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: memoryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: memoryKeys.stats });
    },
  });
};

export const useReinforceMemory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, boostAmount }: { id: string; boostAmount?: number }) =>
      api.reinforceMemory(id, boostAmount),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: memoryKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: memoryKeys.lists() });
    },
  });
};

export const useMemoryVersions = (id: string) =>
  useQuery({
    queryKey: [...memoryKeys.detail(id), 'versions'],
    queryFn: () => api.getMemoryVersions(id),
    enabled: !!id,
  });

export const useSpecificVersion = (id: string, version: number) =>
  useQuery({
    queryKey: [...memoryKeys.detail(id), 'versions', version],
    queryFn: () => api.getSpecificVersion(id, version),
    enabled: !!id && version >= 0,
  });

export const useRestoreVersion = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, version }: { id: string; version: number }) =>
      api.restoreVersion(id, version),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: memoryKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: memoryKeys.lists() });
    },
  });
};

export const useVersionDiff = (id: string, v1: number, v2: number) =>
  useQuery({
    queryKey: [...memoryKeys.detail(id), 'diff', v1, v2],
    queryFn: () => api.diffVersions(id, v1, v2),
    enabled: !!id && v1 >= 0 && v2 >= 0 && v1 !== v2,
  });

export const useConsolidationPreview = (olderThanDays?: number) =>
  useQuery({
    queryKey: ['consolidation', 'preview', olderThanDays],
    queryFn: () => api.getConsolidationPreview(olderThanDays),
    staleTime: 60000,
  });

export const useForgettingStats = () =>
  useQuery({
    queryKey: ['forgetting', 'stats'],
    queryFn: api.getForgettingStats,
    staleTime: 60000,
  });

export const useWeakMemories = (strengthThreshold?: number, limit?: number) =>
  useQuery({
    queryKey: ['forgetting', 'weak', strengthThreshold, limit],
    queryFn: () => api.getWeakMemories(strengthThreshold, limit),
    staleTime: 60000,
  });

export const useTriggerForgetting = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (maxUpdates?: number) => api.triggerForgettingUpdate(maxUpdates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['forgetting'] });
      queryClient.invalidateQueries({ queryKey: memoryKeys.lists() });
    },
  });
};

export const useQualityLeaderboard = (limit?: number, memoryType?: string) =>
  useQuery({
    queryKey: ['memories', 'quality-leaderboard', limit, memoryType],
    queryFn: () => api.getQualityLeaderboard(limit, memoryType),
    staleTime: 60000,
  });

export const useQualityReport = () =>
  useQuery({
    queryKey: ['memories', 'quality-report'],
    queryFn: api.getQualityReport,
    staleTime: 60000,
  });
