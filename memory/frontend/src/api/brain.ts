import { apiClient } from './client';

// Advanced Brain Mode API Types
export interface BrainMetrics {
  emotional_coverage: number;
  conflicts_detected: number;
  conflicts_resolved: number;
  avg_importance: number;
  access_rate: number;
  total_memories: number;
  last_updated: string;
}

export interface PerformanceMetrics {
  total_memories: number;
  avg_importance: number;
  access_rate: number;
  emotional_coverage: number;
  type_distribution: Record<string, number>;
  timestamp: string;
}

export interface MetricsHistory {
  success: boolean;
  current: PerformanceMetrics;
  history: PerformanceMetrics[];
}

export interface EmotionalAnalysisResult {
  success: boolean;
  analyzed: number;
  timestamp: string;
}

export interface ConflictDetectionResult {
  success: boolean;
  conflicts_detected: number;
  conflicts_resolved: number;
  timestamp: string;
}

export interface MetaLearningResult {
  success: boolean;
  metrics: PerformanceMetrics;
  tuned_parameters: Record<string, number>;
  timestamp: string;
}

// Get combined brain metrics (custom endpoint aggregating all metrics)
export const getBrainMetrics = async (): Promise<BrainMetrics> => {
  try {
    // Fetch performance metrics
    const metricsResponse = await apiClient.get<MetricsHistory>('/brain/performance-metrics?days=1');
    const current = metricsResponse.data.current;

    // Return combined metrics
    return {
      emotional_coverage: current.emotional_coverage || 0,
      conflicts_detected: 0, // Will be populated after first run
      conflicts_resolved: 0,
      avg_importance: current.avg_importance || 0.5,
      access_rate: current.access_rate || 0,
      total_memories: current.total_memories || 0,
      last_updated: current.timestamp || new Date().toISOString()
    };
  } catch (error) {
    console.error('Failed to fetch brain metrics:', error);
    return {
      emotional_coverage: 0,
      conflicts_detected: 0,
      conflicts_resolved: 0,
      avg_importance: 0.5,
      access_rate: 0,
      total_memories: 0,
      last_updated: new Date().toISOString()
    };
  }
};

// Get performance metrics with history
export const getPerformanceMetrics = (days: number = 7) =>
  apiClient.get<MetricsHistory>(`/brain/performance-metrics?days=${days}`).then(r => r.data);

// Manually trigger emotional analysis
export const runEmotionalAnalysis = (limit: number = 100) =>
  apiClient.post<EmotionalAnalysisResult>(`/brain/emotional-analysis?limit=${limit}`).then(r => r.data);

// Manually trigger conflict detection
export const runConflictDetection = (limit: number = 50) =>
  apiClient.post<ConflictDetectionResult>(`/brain/detect-conflicts?limit=${limit}`).then(r => r.data);

// Manually trigger meta-learning
export const runMetaLearning = () =>
  apiClient.post<MetaLearningResult>('/brain/meta-learning').then(r => r.data);
