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
