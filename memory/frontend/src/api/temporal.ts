import { apiClient } from './client';

export interface TemporalStats {
  total_memories: number;
  valid_memories: number;
  obsolete_memories: number;
  avg_validity_days: number;
  oldest_valid: string;
  newest_valid: string;
}

export interface TemporalMemory {
  id: string;
  content: string;
  type: string;
  valid_from: string;
  valid_to?: string;
  is_obsolete: boolean;
  tags: string[];
  project?: string;
}

export interface TemporalRelation {
  id: string;
  content: string;
  type: string;
  relation: string;
  valid_at: string;
  score: number;
}

export const getValidAt = (params: {
  target_time: string;
  limit?: number;
  project?: string;
}) =>
  apiClient.get<TemporalMemory[]>('/temporal/valid-at', { params }).then(r => r.data);

export const getObsoleteMemories = (limit?: number) =>
  apiClient.get<TemporalMemory[]>('/temporal/obsolete', {
    params: { limit }
  }).then(r => r.data);

export const markObsolete = (memoryId: string, validityEnd?: string) =>
  apiClient.post(`/temporal/memories/${memoryId}/mark-obsolete`, null, {
    params: { validity_end: validityEnd }
  }).then(r => r.data);

export const getTemporalStats = (project?: string) =>
  apiClient.get<TemporalStats>('/temporal/stats', {
    params: { project }
  }).then(r => r.data);

export const getRelatedAt = (memoryId: string, params: {
  target_time: string;
  max_hops?: number;
  limit?: number;
}) =>
  apiClient.get<TemporalRelation[]>(`/temporal/graph/${memoryId}/related-at`, { params }).then(r => r.data);
