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
  apiClient.get('/analytics/error-trends', {
    params: { days }
  }).then(r => { const d = r.data; return (Array.isArray(d) ? d : d.clusters || d.trends || []) as ErrorTrend[]; });

// Get error spikes (sudden increases in errors)
export const getErrorSpikes = () =>
  apiClient.get<ErrorSpike[]>('/analytics/error-spikes').then(r => r.data);

// Get pattern clusters
export const getPatternClusters = (minClusterSize: number = 3) =>
  apiClient.get('/analytics/pattern-clusters', {
    params: { min_cluster_size: minClusterSize }
  }).then(r => { const d = r.data; return (Array.isArray(d) ? d : d.clusters || []) as PatternCluster[]; });

// Get knowledge gaps
export const getKnowledgeGaps = () =>
  apiClient.get('/analytics/knowledge-gaps').then(r => { const d = r.data; return (Array.isArray(d) ? d : d.gaps || []) as KnowledgeGap[]; });

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
  apiClient.get('/recommendations/documentation-topics', {
    params: { project, limit }
  }).then(r => { const d = r.data; return (Array.isArray(d) ? d : d.topics || []) as DocumentationTopic[]; });

// Get recommendation co-access stats
export const getRecommendationCoAccessStats = () =>
  apiClient.get('/recommendations/co-access/stats').then(r => r.data);

// Reset recommendation co-access
export const resetRecommendationCoAccess = () =>
  apiClient.post('/recommendations/co-access/reset').then(r => r.data);

// Get recurring patterns
export const getRecurringPatterns = (limit: number = 20) =>
  apiClient.get('/insights/recurring-patterns', {
    params: { limit }
  }).then(r => { const d = r.data; return (Array.isArray(d) ? d : d.patterns || []) as RecurringPattern[]; });

// Get expertise profile
export const getExpertiseProfile = () =>
  apiClient.get('/insights/expertise-profile').then(r => {
    const d = r.data;
    const levelMap: Record<string, number> = { expert: 10, proficient: 7, familiar: 4, beginner: 1 };
    let areas: Array<{ name: string; level: number; memory_count: number }>;
    if (Array.isArray(d.areas)) {
      areas = d.areas;
    } else if (d.expertise && typeof d.expertise === 'object' && !Array.isArray(d.expertise)) {
      areas = Object.entries(d.expertise).map(([name, info]: [string, any]) => ({
        name,
        level: typeof info.level === 'number' ? info.level : (levelMap[info.level] ?? 5),
        memory_count: info.memory_count ?? 0,
      }));
    } else {
      areas = [];
    }
    const expertIn = d.expert_in;
    const strongest = d.strongest
      || (Array.isArray(expertIn) && expertIn.length > 0 ? expertIn[0] : '')
      || (Array.isArray(d.proficient_in) && d.proficient_in.length > 0 ? d.proficient_in[0] : '')
      || (areas.length > 0 ? areas.reduce((a, b) => a.level > b.level ? a : b).name : '');
    const weakest = d.weakest
      || (areas.length > 0 ? areas.reduce((a, b) => a.level < b.level ? a : b).name : '');
    return {
      areas,
      strongest: Array.isArray(strongest) ? strongest.join(', ') : strongest,
      weakest,
      total_score: d.total_score ?? d.total_technologies ?? 0,
    } as ExpertiseProfile;
  });

// Get anomalies
export const getAnomalies = () =>
  apiClient.get('/insights/anomalies').then(r => { const d = r.data; return (Array.isArray(d) ? d : d.anomalies || []) as Anomaly[]; });

// Get insight error trends
export const getInsightErrorTrends = (days: number = 30) =>
  apiClient.get<InsightErrorTrend[]>('/insights/error-trends', {
    params: { days }
  }).then(r => r.data);

// Get insights summary
export const getInsightsSummary = (limit: number = 5) =>
  apiClient.get('/insights/summary', {
    params: { limit }
  }).then(r => {
    const d = r.data;
    // API returns {insights: [...], count} but we need InsightsSummary shape
    if (d.insights && !d.key_findings) {
      return { key_findings: d.insights || [], recommendations: [], health_score: 0, trends: {} } as InsightsSummary;
    }
    return d as InsightsSummary;
  });
