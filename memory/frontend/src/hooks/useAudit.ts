import { useQuery, useMutation, useQueryClient } from '@tantml/react-query';
import * as api from '../api/audit';
import type { AuditAction } from '../types/memory';

// Query keys
export const auditKeys = {
  all: ['audit'] as const,
  trail: (memoryId?: string, limit?: number, action?: AuditAction, actor?: string) =>
    [...auditKeys.all, 'trail', { memoryId, limit, action, actor }] as const,
  stats: (memoryId?: string) => [...auditKeys.all, 'stats', memoryId] as const,
  versions: (memoryId: string) => [...auditKeys.all, 'versions', memoryId] as const,
};

// Queries
export const useAuditTrail = (
  memoryId?: string,
  limit: number = 50,
  action?: AuditAction,
  actor?: string
) => {
  return useQuery({
    queryKey: auditKeys.trail(memoryId, limit, action, actor),
    queryFn: () => api.getAuditTrail(memoryId, limit, action, actor),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

export const useAuditStats = (memoryId?: string) => {
  return useQuery({
    queryKey: auditKeys.stats(memoryId),
    queryFn: () => api.getAuditStats(memoryId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useRestorableVersions = (memoryId: string) => {
  return useQuery({
    queryKey: auditKeys.versions(memoryId),
    queryFn: () => api.getVersionHistory(memoryId),
    enabled: !!memoryId,
    staleTime: 5 * 60 * 1000,
  });
};

// Mutations
export const useRestoreMemory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      memoryId,
      targetTimestamp,
      actor = 'user',
    }: {
      memoryId: string;
      targetTimestamp: string;
      actor?: string;
    }) => api.restoreMemory(memoryId, targetTimestamp, actor),
    onSuccess: (_, { memoryId }) => {
      queryClient.invalidateQueries({ queryKey: auditKeys.trail(memoryId) });
      queryClient.invalidateQueries({ queryKey: auditKeys.versions(memoryId) });
      queryClient.invalidateQueries({ queryKey: ['memories', 'detail', memoryId] });
      queryClient.invalidateQueries({ queryKey: ['memories', 'list'] });
    },
  });
};

export const useUndoLastChange = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ memoryId, actor = 'user' }: { memoryId: string; actor?: string }) =>
      api.undoLastChange(memoryId, actor),
    onSuccess: (_, { memoryId }) => {
      queryClient.invalidateQueries({ queryKey: auditKeys.trail(memoryId) });
      queryClient.invalidateQueries({ queryKey: auditKeys.versions(memoryId) });
      queryClient.invalidateQueries({ queryKey: ['memories', 'detail', memoryId] });
      queryClient.invalidateQueries({ queryKey: ['memories', 'list'] });
    },
  });
};
