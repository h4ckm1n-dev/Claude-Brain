import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/temporal';

export const temporalKeys = {
  all: ['temporal'] as const,
  stats: (project?: string) => [...temporalKeys.all, 'stats', project] as const,
  validAt: (time: string, project?: string) => [...temporalKeys.all, 'valid-at', time, project] as const,
  obsolete: (limit?: number) => [...temporalKeys.all, 'obsolete', limit] as const,
  relatedAt: (memoryId: string, time: string) => [...temporalKeys.all, 'related-at', memoryId, time] as const,
};

export const useTemporalStats = (project?: string) =>
  useQuery({
    queryKey: temporalKeys.stats(project),
    queryFn: () => api.getTemporalStats(project),
    staleTime: 60000,
  });

export const useValidAt = (targetTime: string, limit?: number, project?: string) =>
  useQuery({
    queryKey: temporalKeys.validAt(targetTime, project),
    queryFn: () => api.getValidAt({ target_time: targetTime, limit, project }),
    enabled: !!targetTime,
  });

export const useObsoleteMemories = (limit?: number) =>
  useQuery({
    queryKey: temporalKeys.obsolete(limit),
    queryFn: () => api.getObsoleteMemories(limit),
    staleTime: 60000,
  });

export const useMarkObsolete = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ memoryId, validityEnd }: { memoryId: string; validityEnd?: string }) =>
      api.markObsolete(memoryId, validityEnd),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: temporalKeys.all });
    },
  });
};

export const useRelatedAt = (memoryId: string, targetTime: string, maxHops?: number, limit?: number) =>
  useQuery({
    queryKey: temporalKeys.relatedAt(memoryId, targetTime),
    queryFn: () => api.getRelatedAt(memoryId, { target_time: targetTime, max_hops: maxHops, limit }),
    enabled: !!memoryId && !!targetTime,
  });
