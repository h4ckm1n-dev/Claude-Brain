import { apiClient } from './client';
import type {
  ErrorTrend,
  PatternCluster,
  KnowledgeGap,
  Recommendation,
  ErrorSpike,
  RecurringError,
  ResolutionTime,
  ExpertiseCluster,
} from '../types/memory';

// Get error trends over time
export const getErrorTrends = (days: number = 30) =>
  apiClient.get<ErrorTrend[]>('/analytics/error-trends', {
    params: { days }
  }).then(r => r.data);

// Get error spikes (sudden increases in errors)
export const getErrorSpikes = () =>
  apiClient.get<ErrorSpike[]>('/analytics/error-spikes').then(r => r.data);

// Get pattern clusters
export const getPatternClusters = (minClusterSize: number = 3) =>
  apiClient.get<PatternCluster[]>('/analytics/pattern-clusters', {
    params: { min_cluster_size: minClusterSize }
  }).then(r => r.data);

// Get knowledge gaps
export const getKnowledgeGaps = () =>
  apiClient.get<KnowledgeGap[]>('/analytics/knowledge-gaps').then(r => r.data);

// Get recommendations
export const getRecommendations = (
  memoryId?: string,
  query?: string,
  limit: number = 10
) =>
  apiClient.get<Recommendation[]>('/recommendations', {
    params: { memory_id: memoryId, query, limit }
  }).then(r => r.data);

// Get recurring errors
export const getRecurringErrors = (days: number = 30) =>
  apiClient.get<RecurringError[]>('/analytics/recurring-errors', {
    params: { days }
  }).then(r => r.data);

// Get resolution time statistics
export const getResolutionTimes = () =>
  apiClient.get<ResolutionTime>('/analytics/resolution-times').then(r => r.data);

// Calculate severity for an error
export const calculateSeverity = (errorMessage: string, context?: string) =>
  apiClient.post<{ severity: number; factors: Record<string, number> }>(
    '/analytics/calculate-severity',
    { error_message: errorMessage, context }
  ).then(r => r.data);

// Get expertise clusters
export const getExpertiseClusters = () =>
  apiClient.get<ExpertiseCluster[]>('/analytics/expertise-clusters').then(r => r.data);

// Trigger pattern detection manually (runs on-demand via analytics endpoint)
export const triggerPatternDetection = () =>
  apiClient.get('/analytics/pattern-clusters', {
    params: { min_cluster_size: 2 }
  }).then(r => r.data);
