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
  apiClient.get('/temporal/valid-at', { params }).then(r => { const d = r.data; return (Array.isArray(d) ? d : d.memories || []) as TemporalMemory[]; });

export const getObsoleteMemories = (limit?: number) =>
  apiClient.get('/temporal/obsolete', {
    params: { limit }
  }).then(r => { const d = r.data; return (Array.isArray(d) ? d : d.memories || []) as TemporalMemory[]; });

export const markObsolete = (memoryId: string, validityEnd?: string) =>
  apiClient.post(`/temporal/memories/${memoryId}/mark-obsolete`, null, {
    params: { validity_end: validityEnd }
  }).then(r => r.data);

export const getTemporalStats = (project?: string) =>
  apiClient.get('/temporal/stats', {
    params: { project }
  }).then(r => {
    const d = r.data;
    const vs = d.validity_stats || {};
    return {
      total_memories: vs.total_memories ?? d.total_memories ?? 0,
      valid_memories: vs.valid_count ?? d.valid_memories ?? 0,
      obsolete_memories: vs.obsolete_count ?? d.obsolete_memories ?? 0,
      avg_validity_days: vs.avg_validity_days ?? d.avg_validity_days ?? 0,
      oldest_valid: vs.oldest_valid ?? d.oldest_valid ?? '',
      newest_valid: vs.newest_valid ?? d.newest_valid ?? '',
    } as TemporalStats;
  });

export const getRelatedAt = (memoryId: string, params: {
  target_time: string;
  max_hops?: number;
  limit?: number;
}) =>
  apiClient.get(`/temporal/graph/${memoryId}/related-at`, { params }).then(r => { const d = r.data; return (Array.isArray(d) ? d : d.related || d.memories || []) as TemporalRelation[]; });
