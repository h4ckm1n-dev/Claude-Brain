import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/sessions';

export const sessionKeys = {
  all: ['sessions'] as const,
  stats: () => [...sessionKeys.all, 'stats'] as const,
  memories: (sessionId: string) => [...sessionKeys.all, 'memories', sessionId] as const,
};

export const useSessionStats = () =>
  useQuery({
    queryKey: sessionKeys.stats(),
    queryFn: api.getSessionStats,
    refetchInterval: 30000,
  });

export const useSessionMemories = (sessionId: string) =>
  useQuery({
    queryKey: sessionKeys.memories(sessionId),
    queryFn: () => api.getSessionMemories(sessionId),
    enabled: !!sessionId,
  });

export const useConsolidateSession = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.consolidateSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.all });
    },
  });
};

export const useBatchConsolidate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.batchConsolidateSessions,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.all });
    },
  });
};

export const useCreateSession = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.all });
    },
  });
};

export const useCloseSession = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.closeSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.all });
    },
  });
};

export const useDeleteSession = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.deleteSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.all });
    },
  });
};
