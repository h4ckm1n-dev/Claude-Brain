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

// --- New Brain Endpoints ---

export interface SpacedRepetitionItem {
  id: string;
  content: string;
  type: string;
  next_review: string;
  strength: number;
  review_count: number;
}

export interface Topic {
  name: string;
  size: number;
  keywords: string[];
  memories: string[];
}

export interface TopicTimelineEntry {
  date: string;
  count: number;
  memories: Array<{ id: string; content: string }>;
}

export interface ReplayResult {
  success: boolean;
  replayed: number;
  memories: Array<{ id: string; content: string; type: string }>;
}

export interface DreamResult {
  success: boolean;
  connections_found: number;
  insights: string[];
  duration_seconds: number;
}

export interface InferenceResult {
  success: boolean;
  relationships_inferred: number;
  details: Array<{ source: string; target: string; relation: string; confidence: number }>;
}

export interface CoAccessStats {
  total_pairs: number;
  top_pairs: Array<{ memory_a: string; memory_b: string; co_access_count: number }>;
}

// Reconsolidate a memory
export const reconsolidateMemory = (memoryId: string, accessContext?: string, coAccessedIds?: string[]) =>
  apiClient.post(`/brain/reconsolidate/${memoryId}`, null, {
    params: { access_context: accessContext, co_accessed_ids: coAccessedIds?.join(',') }
  }).then(r => r.data);

// Get spaced repetition items
export const getSpacedRepetition = (limit: number = 20) =>
  apiClient.get('/brain/spaced-repetition', {
    params: { limit }
  }).then(r => { const d = r.data; return (Array.isArray(d) ? d : d.candidates || []) as SpacedRepetitionItem[]; });

// Get discovered topics
export const getTopics = (minClusterSize?: number, maxTopics?: number) =>
  apiClient.get('/brain/topics', {
    params: { min_cluster_size: minClusterSize, max_topics: maxTopics }
  }).then(r => {
    const d = r.data;
    const raw = Array.isArray(d) ? d : d.topics || [];
    return raw.map((t: any) => ({
      name: t.name || t.topic || t.representative_term || '',
      size: t.size ?? 0,
      keywords: t.keywords || t.sample_content || [],
      memories: t.memories || t.memory_ids || [],
    })) as Topic[];
  });

// Get topic timeline
export const getTopicTimeline = (topicName: string, limit: number = 50) =>
  apiClient.get(`/brain/topics/timeline/${encodeURIComponent(topicName)}`, {
    params: { limit }
  }).then(r => {
    const d = r.data;
    const raw = Array.isArray(d) ? d : d.timeline || d.entries || [];
    // API returns flat entries {id, content, created_at, type, importance}
    // Group by date for the expected TopicTimelineEntry shape
    if (raw.length > 0 && raw[0].created_at && !raw[0].memories) {
      const grouped: Record<string, { id: string; content: string }[]> = {};
      for (const entry of raw) {
        const date = (entry.created_at || entry.date || '').split('T')[0];
        if (!grouped[date]) grouped[date] = [];
        grouped[date].push({ id: entry.id || '', content: entry.content || '' });
      }
      return Object.entries(grouped)
        .sort(([a], [b]) => b.localeCompare(a))
        .map(([date, memories]) => ({ date, count: memories.length, memories })) as TopicTimelineEntry[];
    }
    return raw as TopicTimelineEntry[];
  });

// Trigger memory replay
export const triggerReplay = (count?: number, importanceThreshold?: number) =>
  apiClient.post<ReplayResult>('/brain/replay', null, {
    params: { count, importance_threshold: importanceThreshold }
  }).then(r => r.data);

// Trigger project replay
export const triggerProjectReplay = (project: string, count?: number) =>
  apiClient.post<ReplayResult>(`/brain/replay/project/${encodeURIComponent(project)}`, null, {
    params: { count }
  }).then(r => r.data);

// Trigger underutilized replay
export const triggerUnderutilizedReplay = (days?: number, count?: number) =>
  apiClient.post<ReplayResult>('/brain/replay/underutilized', null, {
    params: { days, count }
  }).then(r => r.data);

// Trigger dream mode
export const triggerDream = (duration?: number) =>
  apiClient.post<DreamResult>('/brain/dream', null, {
    params: { duration }
  }).then(r => r.data);

// Run relationship inference
export const runInference = (inferenceType?: string) =>
  apiClient.post<InferenceResult>('/inference/run', null, {
    params: { inference_type: inferenceType }
  }).then(r => r.data);

// Get co-access stats
export const getCoAccessStats = () =>
  apiClient.get('/inference/co-access/stats').then(r => {
    const d = r.data;
    return {
      total_pairs: d.total_pairs ?? d.total_pairs_tracked ?? 0,
      top_pairs: d.top_pairs || [],
    } as CoAccessStats;
  });

// Reset co-access tracker
export const resetCoAccess = () =>
  apiClient.post('/inference/co-access/reset').then(r => r.data);

// Brain stats
export const getBrainStats = () =>
  apiClient.get('/brain/stats').then(r => r.data);

// Infer relationships
export const inferRelationships = (lookbackDays: number = 7) =>
  apiClient.post('/brain/infer-relationships', null, {
    params: { lookback_days: lookbackDays }
  }).then(r => r.data);

// Update importance scores
export const updateImportance = (limit: number = 100) =>
  apiClient.post('/brain/update-importance', null, {
    params: { limit }
  }).then(r => r.data);

// Archive low utility memories
export const archiveLowUtility = (threshold?: number, maxArchive?: number, dryRun?: boolean) =>
  apiClient.post('/brain/archive-low-utility', null, {
    params: { threshold, max_archive: maxArchive, dry_run: dryRun }
  }).then(r => r.data);
