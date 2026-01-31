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
