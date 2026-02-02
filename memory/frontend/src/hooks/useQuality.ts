import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/quality';

// Query keys
export const qualityKeys = {
  all: ['quality'] as const,
  stats: () => [...qualityKeys.all, 'stats'] as const,
  trend: (memoryId: string) => [...qualityKeys.all, 'trend', memoryId] as const,
  promotionCandidates: (limit: number) => [...qualityKeys.all, 'promotion-candidates', limit] as const,
};

// Queries
export const useQualityStats = () => {
  return useQuery({
    queryKey: qualityKeys.stats(),
    queryFn: api.getQualityStats,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 30000, // Refresh every 30s
  });
};

export const useQualityTrend = (memoryId: string) => {
  return useQuery({
    queryKey: qualityKeys.trend(memoryId),
    queryFn: () => api.getQualityTrend(memoryId),
    enabled: !!memoryId,
    staleTime: 5 * 60 * 1000,
  });
};

export const usePromotionCandidates = (limit: number = 10) => {
  return useQuery({
    queryKey: qualityKeys.promotionCandidates(limit),
    queryFn: () => api.getPromotionCandidates(limit),
    staleTime: 5 * 60 * 1000,
  });
};

// Mutations
export const useUpdateQualityScores = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.updateQualityScores,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qualityKeys.all });
      queryClient.invalidateQueries({ queryKey: ['memories'] });
    },
  });
};

export const usePromoteBatch = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (memoryIds: string[]) => api.promoteBatch(memoryIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qualityKeys.all });
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['lifecycle'] });
    },
  });
};

export const useRateMemory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ memoryId, rating, feedback }: { memoryId: string; rating: number; feedback?: string }) =>
      api.rateMemory(memoryId, rating, feedback),
    onSuccess: (_, { memoryId }) => {
      queryClient.invalidateQueries({ queryKey: qualityKeys.trend(memoryId) });
      queryClient.invalidateQueries({ queryKey: qualityKeys.stats() });
      queryClient.invalidateQueries({ queryKey: ['memories', 'detail', memoryId] });
    },
  });
};
