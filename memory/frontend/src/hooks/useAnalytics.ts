import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/analytics';

// Query keys
export const analyticsKeys = {
  all: ['analytics'] as const,
  errorTrends: (days: number) => [...analyticsKeys.all, 'error-trends', days] as const,
  errorSpikes: () => [...analyticsKeys.all, 'error-spikes'] as const,
  patternClusters: (minSize: number) => [...analyticsKeys.all, 'pattern-clusters', minSize] as const,
  knowledgeGaps: () => [...analyticsKeys.all, 'knowledge-gaps'] as const,
  recommendations: (memoryId?: string, query?: string, limit?: number) =>
    [...analyticsKeys.all, 'recommendations', { memoryId, query, limit }] as const,
  recurringErrors: (days: number) => [...analyticsKeys.all, 'recurring-errors', days] as const,
  resolutionTimes: () => [...analyticsKeys.all, 'resolution-times'] as const,
  expertiseClusters: () => [...analyticsKeys.all, 'expertise-clusters'] as const,
};

// Queries
export const useErrorTrends = (days: number = 30) => {
  return useQuery({
    queryKey: analyticsKeys.errorTrends(days),
    queryFn: () => api.getErrorTrends(days),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
};

export const useErrorSpikes = () => {
  return useQuery({
    queryKey: analyticsKeys.errorSpikes(),
    queryFn: api.getErrorSpikes,
    staleTime: 10 * 60 * 1000,
  });
};

export const usePatternClusters = (minClusterSize: number = 3) => {
  return useQuery({
    queryKey: analyticsKeys.patternClusters(minClusterSize),
    queryFn: () => api.getPatternClusters(minClusterSize),
    staleTime: 10 * 60 * 1000,
  });
};

export const useKnowledgeGaps = () => {
  return useQuery({
    queryKey: analyticsKeys.knowledgeGaps(),
    queryFn: api.getKnowledgeGaps,
    staleTime: 10 * 60 * 1000,
  });
};

export const useRecommendations = (memoryId?: string, query?: string, limit: number = 10) => {
  return useQuery({
    queryKey: analyticsKeys.recommendations(memoryId, query, limit),
    queryFn: () => api.getRecommendations(memoryId, query, limit),
    enabled: !!(memoryId || query),
    staleTime: 5 * 60 * 1000,
  });
};

export const useRecurringErrors = (days: number = 30) => {
  return useQuery({
    queryKey: analyticsKeys.recurringErrors(days),
    queryFn: () => api.getRecurringErrors(days),
    staleTime: 10 * 60 * 1000,
  });
};

export const useResolutionTimes = () => {
  return useQuery({
    queryKey: analyticsKeys.resolutionTimes(),
    queryFn: api.getResolutionTimes,
    staleTime: 10 * 60 * 1000,
  });
};

export const useExpertiseClusters = () => {
  return useQuery({
    queryKey: analyticsKeys.expertiseClusters(),
    queryFn: api.getExpertiseClusters,
    staleTime: 10 * 60 * 1000,
  });
};

// Mutations
export const useCalculateSeverity = () => {
  return useMutation({
    mutationFn: ({ errorMessage, context }: { errorMessage: string; context?: string }) =>
      api.calculateSeverity(errorMessage, context),
  });
};

export const useTriggerPatternDetection = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.triggerPatternDetection,
    onSuccess: () => {
      // Invalidate pattern-related queries after manual trigger
      queryClient.invalidateQueries({ queryKey: analyticsKeys.patternClusters() });
      queryClient.invalidateQueries({ queryKey: analyticsKeys.knowledgeGaps() });
    },
  });
};
