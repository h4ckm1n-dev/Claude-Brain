import { apiClient } from './client';
import type {
  Memory,
  MemoryCreate,
  SearchQuery,
  SearchResult,
  HealthResponse,
  StatsResponse,
  GraphStats,
  SuggestionRequest,
  Suggestion,
  ConsolidateRequest,
  ConsolidateResult,
} from '../types/memory';

// Health & Stats
export const getHealth = () =>
  apiClient.get<HealthResponse>('/health').then(r => r.data);

export const getStats = () =>
  apiClient.get<StatsResponse>('/stats').then(r => r.data);

export const getGraphStats = () =>
  apiClient.get<GraphStats>('/graph/stats').then(r => r.data);

// CRUD Operations
export const getMemories = (params?: {
  type?: string;
  project?: string;
  limit?: number;
  offset?: number;
}) => apiClient.get<Memory[]>('/memories', { params }).then(r => r.data);

export const getMemory = (id: string) =>
  apiClient.get<Memory>(`/memories/${id}`).then(r => r.data);

export const createMemory = (data: MemoryCreate) =>
  apiClient.post<Memory>('/memories', data).then(r => r.data);

export const updateMemory = (id: string, data: Partial<Memory>) =>
  apiClient.put<Memory>(`/memories/${id}`, data).then(r => r.data);

export const deleteMemory = (id: string) =>
  apiClient.delete(`/memories/${id}`);

// Search
export const searchMemories = (query: SearchQuery) =>
  apiClient.post<SearchResult[]>('/memories/search', query).then(r => r.data);

// Special Operations
export const pinMemory = (id: string) =>
  apiClient.post(`/memories/${id}/pin`).then(r => r.data);

export const unpinMemory = (id: string) =>
  apiClient.post(`/memories/${id}/unpin`).then(r => r.data);

export const archiveMemory = (id: string) =>
  apiClient.post(`/memories/${id}/archive`).then(r => r.data);

export const resolveMemory = (id: string, solution: string) =>
  apiClient.post(`/memories/${id}/resolve`, { solution }).then(r => r.data);

export const linkMemories = (sourceId: string, targetId: string, relationType: string) =>
  apiClient.post('/memories/link', { source_id: sourceId, target_id: targetId, relation_type: relationType }).then(r => r.data);

// Context & Suggestions
export const getContext = (project?: string, hours?: number, types?: string) =>
  apiClient.get<Memory[]>('/context', { params: { project, hours, types } }).then(r => r.data);

export const getSuggestions = (request: SuggestionRequest) =>
  apiClient.post<{ suggestions: Suggestion[]; count: number }>('/memories/suggest', request).then(r => r.data);

// Consolidation
export const consolidateMemories = (request: ConsolidateRequest) =>
  apiClient.post<ConsolidateResult>('/consolidate', request).then(r => r.data);

// Graph Operations
export const getRelatedMemories = (memoryId: string, maxHops?: number, limit?: number) =>
  apiClient.post<Memory[]>(`/memories/related/${memoryId}`, { max_hops: maxHops, limit }).then(r => r.data);

export const getTimeline = (project?: string, memoryType?: string, limit?: number) =>
  apiClient.get<any>('/graph/timeline', { params: { project, memory_type: memoryType, limit } }).then(r => r.data);

// --- New Memory Endpoints ---

export interface DraftResult {
  preview: Memory;
  quality_score: number;
  quality_details: Record<string, number>;
  suggestions: string[];
}

export interface MemoryVersion {
  version: number;
  content: string;
  changed_at: string;
  changes: string[];
}

export interface VersionDiff {
  version_a: number;
  version_b: number;
  changes: Array<{ field: string; old_value: any; new_value: any }>;
}

export interface ForgettingStats {
  total_memories: number;
  avg_strength: number;
  weak_count: number;
  decay_rate: number;
  last_update: string;
}

export interface WeakMemory {
  id: string;
  content: string;
  type: string;
  strength: number;
  last_accessed: string;
  access_count: number;
}

export interface QualityLeaderboardEntry {
  id: string;
  content: string;
  type: string;
  quality_score: number;
  access_count: number;
}

export interface QualityReport {
  total_memories: number;
  avg_quality: number;
  distribution: Record<string, number>;
  top_issues: string[];
  recommendations: string[];
}

export interface ConsolidationPreview {
  candidates: Array<{ id: string; content: string; reason: string }>;
  estimated_consolidations: number;
  estimated_archives: number;
}

// Draft a memory (preview quality before saving)
export const draftMemory = (data: MemoryCreate) =>
  apiClient.post<DraftResult>('/memories/draft', data).then(r => r.data);

// Bulk store memories
export const bulkStoreMemories = (memories: MemoryCreate[]) =>
  apiClient.post<Memory[]>('/memories/bulk', memories).then(r => r.data);

// Reinforce a memory
export const reinforceMemory = (id: string, boostAmount?: number) =>
  apiClient.post(`/memories/${id}/reinforce`, null, {
    params: { boost_amount: boostAmount }
  }).then(r => r.data);

// Get memory versions
export const getMemoryVersions = (id: string) =>
  apiClient.get<MemoryVersion[]>(`/memories/${id}/versions`).then(r => r.data);

// Get specific version
export const getSpecificVersion = (id: string, version: number) =>
  apiClient.get<MemoryVersion>(`/memories/${id}/versions/${version}`).then(r => r.data);

// Restore a version
export const restoreVersion = (id: string, version: number) =>
  apiClient.post(`/memories/${id}/versions/${version}/restore`).then(r => r.data);

// Diff two versions
export const diffVersions = (id: string, v1: number, v2: number) =>
  apiClient.get<VersionDiff>(`/memories/${id}/versions/${v1}/diff/${v2}`).then(r => r.data);

// Consolidation preview
export const getConsolidationPreview = (olderThanDays?: number) =>
  apiClient.get<ConsolidationPreview>('/consolidate/preview', {
    params: { older_than_days: olderThanDays }
  }).then(r => r.data);

// Forgetting stats
export const getForgettingStats = () =>
  apiClient.get('/forgetting/stats').then(r => {
    const d = r.data;
    return {
      total_memories: d.total_memories ?? 0,
      avg_strength: d.avg_strength ?? d.median_strength ?? 0,
      weak_count: d.weak_count ?? d.below_archive_threshold ?? 0,
      decay_rate: d.decay_rate ?? d.avg_decay_rate ?? 0,
      last_update: d.last_update || '',
    } as ForgettingStats;
  });

// Get weak memories
export const getWeakMemories = (strengthThreshold?: number, limit?: number) =>
  apiClient.get('/forgetting/weak', {
    params: { strength_threshold: strengthThreshold, limit }
  }).then(r => { const d = r.data; return (Array.isArray(d) ? d : d.memories || d.weak_memories || []) as WeakMemory[]; });

// Trigger forgetting update
export const triggerForgettingUpdate = (maxUpdates?: number) =>
  apiClient.post('/forgetting/update', null, {
    params: { max_updates: maxUpdates }
  }).then(r => r.data);

// Quality leaderboard
export const getQualityLeaderboard = (limit?: number, memoryType?: string) =>
  apiClient.get('/memories/quality-leaderboard', {
    params: { limit, memory_type: memoryType }
  }).then(r => { const d = r.data; return (Array.isArray(d) ? d : d.leaderboard || []) as QualityLeaderboardEntry[]; });

// Quality report
export const getQualityReport = () =>
  apiClient.get('/memories/quality-report').then(r => {
    const d = r.data;
    return {
      total_memories: d.total_memories ?? 0,
      avg_quality: d.avg_quality ?? d.avg_rating ?? d.coverage ?? 0,
      distribution: d.distribution ?? d.rating_distribution ?? {},
      top_issues: d.top_issues || [],
      recommendations: d.recommendations || [],
    } as QualityReport;
  });
