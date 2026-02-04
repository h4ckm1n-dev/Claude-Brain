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

// --- New Analytics Endpoints ---

export interface ComprehensiveAnalytics {
  error_trends: ErrorTrend[];
  pattern_clusters: PatternCluster[];
  knowledge_gaps: KnowledgeGap[];
  expertise_clusters: ExpertiseCluster[];
  resolution_times: ResolutionTime;
  summary: Record<string, any>;
}

export interface RecurringPattern {
  pattern: string;
  occurrences: number;
  first_seen: string;
  last_seen: string;
  related_errors: string[];
  suggested_solution?: string;
}

export interface ExpertiseProfile {
  areas: Array<{ name: string; level: number; memory_count: number }>;
  strongest: string;
  weakest: string;
  total_score: number;
}

export interface Anomaly {
  id: string;
  content: string;
  type: string;
  anomaly_type: string;
  severity: number;
  reason: string;
}

export interface InsightErrorTrend {
  date: string;
  count: number;
  severity_avg: number;
  categories: Record<string, number>;
}

export interface InsightsSummary {
  key_findings: string[];
  recommendations: string[];
  health_score: number;
  trends: Record<string, string>;
}

export interface DocumentationTopic {
  topic: string;
  priority: number;
  related_memories: number;
  coverage_gap: number;
}

export interface PreventivePattern {
  pattern: string;
  applicability: number;
  source_memories: string[];
}

// Get comprehensive analytics
export const getComprehensiveAnalytics = () =>
  apiClient.get<ComprehensiveAnalytics>('/analytics/comprehensive').then(r => r.data);

// Get patterns for an error
export const getPatternsForError = (data: { error_tags?: string[]; error_content?: string; limit?: number }) =>
  apiClient.post('/recommendations/patterns-for-error', null, {
    params: { error_tags: data.error_tags?.join(','), error_content: data.error_content, limit: data.limit }
  }).then(r => r.data);

// Get preventive patterns
export const getPreventivePatterns = (searchQuery?: string, queryTags?: string[], limit?: number) =>
  apiClient.get<PreventivePattern[]>('/recommendations/preventive-patterns', {
    params: { search_query: searchQuery, query_tags: queryTags?.join(','), limit }
  }).then(r => r.data);

// Get documentation topics
export const getDocumentationTopics = (project?: string, limit?: number) =>
  apiClient.get<DocumentationTopic[]>('/recommendations/documentation-topics', {
    params: { project, limit }
  }).then(r => r.data);

// Get recommendation co-access stats
export const getRecommendationCoAccessStats = () =>
  apiClient.get('/recommendations/co-access/stats').then(r => r.data);

// Reset recommendation co-access
export const resetRecommendationCoAccess = () =>
  apiClient.post('/recommendations/co-access/reset').then(r => r.data);

// Get recurring patterns
export const getRecurringPatterns = (limit: number = 20) =>
  apiClient.get<RecurringPattern[]>('/insights/recurring-patterns', {
    params: { limit }
  }).then(r => r.data);

// Get expertise profile
export const getExpertiseProfile = () =>
  apiClient.get<ExpertiseProfile>('/insights/expertise-profile').then(r => r.data);

// Get anomalies
export const getAnomalies = () =>
  apiClient.get<Anomaly[]>('/insights/anomalies').then(r => r.data);

// Get insight error trends
export const getInsightErrorTrends = (days: number = 30) =>
  apiClient.get<InsightErrorTrend[]>('/insights/error-trends', {
    params: { days }
  }).then(r => r.data);

// Get insights summary
export const getInsightsSummary = (limit: number = 5) =>
  apiClient.get<InsightsSummary>('/insights/summary', {
    params: { limit }
  }).then(r => r.data);
