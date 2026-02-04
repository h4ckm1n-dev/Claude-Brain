import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getBrainMetrics,
  getPerformanceMetrics,
  runEmotionalAnalysis,
  runConflictDetection,
  runMetaLearning,
} from '../api/brain';

// Fetch combined brain metrics
export function useBrainMetrics() {
  return useQuery({
    queryKey: ['brain', 'metrics'],
    queryFn: getBrainMetrics,
    refetchInterval: 60000, // Refresh every minute
  });
}

// Fetch performance metrics with history
export function usePerformanceMetrics(days: number = 7) {
  return useQuery({
    queryKey: ['brain', 'performance', days],
    queryFn: () => getPerformanceMetrics(days),
    refetchInterval: 300000, // Refresh every 5 minutes
  });
}

// Manually trigger emotional analysis
export function useEmotionalAnalysis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (limit?: number) => runEmotionalAnalysis(limit),
    onSuccess: () => {
      // Invalidate brain metrics to refetch
      queryClient.invalidateQueries({ queryKey: ['brain'] });
    },
  });
}

// Manually trigger conflict detection
export function useConflictDetection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (limit?: number) => runConflictDetection(limit),
    onSuccess: () => {
      // Invalidate brain metrics to refetch
      queryClient.invalidateQueries({ queryKey: ['brain'] });
    },
  });
}

// Manually trigger meta-learning
export function useMetaLearning() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: runMetaLearning,
    onSuccess: () => {
      // Invalidate brain metrics to refetch
      queryClient.invalidateQueries({ queryKey: ['brain'] });
    },
  });
}

// --- New Brain Hooks ---

import {
  getSpacedRepetition,
  getTopics,
  getTopicTimeline,
  triggerReplay,
  triggerProjectReplay,
  triggerUnderutilizedReplay,
  triggerDream,
  reconsolidateMemory,
  runInference,
  getCoAccessStats,
  resetCoAccess,
  getBrainStats,
  inferRelationships,
  updateImportance,
  archiveLowUtility,
} from '../api/brain';

export function useSpacedRepetition(limit: number = 20) {
  return useQuery({
    queryKey: ['brain', 'spaced-repetition', limit],
    queryFn: () => getSpacedRepetition(limit),
    staleTime: 60000,
  });
}

export function useTopics(minClusterSize?: number, maxTopics?: number) {
  return useQuery({
    queryKey: ['brain', 'topics', minClusterSize, maxTopics],
    queryFn: () => getTopics(minClusterSize, maxTopics),
    staleTime: 300000,
  });
}

export function useTopicTimeline(topicName: string, limit?: number) {
  return useQuery({
    queryKey: ['brain', 'topics', 'timeline', topicName, limit],
    queryFn: () => getTopicTimeline(topicName, limit),
    enabled: !!topicName,
    staleTime: 300000,
  });
}

export function useReplay() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ count, importanceThreshold }: { count?: number; importanceThreshold?: number } = {}) =>
      triggerReplay(count, importanceThreshold),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brain'] });
    },
  });
}

export function useProjectReplay() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ project, count }: { project: string; count?: number }) =>
      triggerProjectReplay(project, count),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brain'] });
    },
  });
}

export function useUnderutilizedReplay() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ days, count }: { days?: number; count?: number } = {}) =>
      triggerUnderutilizedReplay(days, count),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brain'] });
    },
  });
}

export function useDream() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (duration?: number) => triggerDream(duration),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brain'] });
    },
  });
}

export function useReconsolidate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ memoryId, accessContext, coAccessedIds }: {
      memoryId: string;
      accessContext?: string;
      coAccessedIds?: string[];
    }) => reconsolidateMemory(memoryId, accessContext, coAccessedIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brain'] });
      queryClient.invalidateQueries({ queryKey: ['memories'] });
    },
  });
}

export function useInference() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (inferenceType?: string) => runInference(inferenceType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brain'] });
      queryClient.invalidateQueries({ queryKey: ['graph'] });
    },
  });
}

export function useCoAccessStats() {
  return useQuery({
    queryKey: ['brain', 'co-access', 'stats'],
    queryFn: getCoAccessStats,
    staleTime: 60000,
  });
}

export function useResetCoAccess() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resetCoAccess,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brain', 'co-access'] });
    },
  });
}

export function useBrainStatsQuery() {
  return useQuery({
    queryKey: ['brain', 'stats'],
    queryFn: getBrainStats,
    staleTime: 60000,
  });
}

export function useInferRelationships() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (lookbackDays?: number) => inferRelationships(lookbackDays),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brain'] });
      queryClient.invalidateQueries({ queryKey: ['graph'] });
    },
  });
}

export function useUpdateImportance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (limit?: number) => updateImportance(limit),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brain'] });
      queryClient.invalidateQueries({ queryKey: ['memories'] });
    },
  });
}

export function useArchiveLowUtility() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ threshold, maxArchive, dryRun }: {
      threshold?: number;
      maxArchive?: number;
      dryRun?: boolean;
    } = {}) => archiveLowUtility(threshold, maxArchive, dryRun),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brain'] });
      queryClient.invalidateQueries({ queryKey: ['memories'] });
    },
  });
}
