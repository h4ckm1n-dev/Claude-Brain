import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/lifecycle';
import type { MemoryState } from '../types/memory';

// Query keys
export const lifecycleKeys = {
  all: ['lifecycle'] as const,
  stats: () => [...lifecycleKeys.all, 'stats'] as const,
  stateHistory: (memoryId: string) => [...lifecycleKeys.all, 'state-history', memoryId] as const,
  transitions: (limit: number) => [...lifecycleKeys.all, 'transitions', limit] as const,
};

// Queries
export const useLifecycleStats = () => {
  return useQuery({
    queryKey: lifecycleKeys.stats(),
    queryFn: api.getLifecycleStats,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 30000, // Refresh every 30s
  });
};

export const useStateHistory = (memoryId: string) => {
  return useQuery({
    queryKey: lifecycleKeys.stateHistory(memoryId),
    queryFn: () => api.getStateHistory(memoryId),
    enabled: !!memoryId,
    staleTime: 5 * 60 * 1000,
  });
};

export const useRecentTransitions = (limit: number = 20) => {
  return useQuery({
    queryKey: lifecycleKeys.transitions(limit),
    queryFn: () => api.getRecentTransitions(limit),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 30000,
  });
};

// Mutations
export const useUpdateLifecycleStates = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.updateLifecycleStates,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: lifecycleKeys.all });
      queryClient.invalidateQueries({ queryKey: ['memories'] });
    },
  });
};

export const useTransitionMemoryState = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      memoryId,
      newState,
      reason,
      actor = 'user',
    }: {
      memoryId: string;
      newState: MemoryState;
      reason: string;
      actor?: string;
    }) => api.transitionMemoryState(memoryId, newState, reason, actor),
    onSuccess: (_, { memoryId }) => {
      queryClient.invalidateQueries({ queryKey: lifecycleKeys.stateHistory(memoryId) });
      queryClient.invalidateQueries({ queryKey: lifecycleKeys.stats() });
      queryClient.invalidateQueries({ queryKey: lifecycleKeys.all });
      queryClient.invalidateQueries({ queryKey: ['memories', 'detail', memoryId] });
      queryClient.invalidateQueries({ queryKey: ['audit'] });
    },
  });
};
