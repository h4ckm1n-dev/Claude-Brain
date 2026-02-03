import { apiClient } from './client';
import type {
  QualityStats,
  QualityTrend,
  PromotionCandidate,
} from '../types/memory';

// Get overall quality statistics - normalize backend field names
export const getQualityStats = () =>
  apiClient.get<any>('/quality/stats').then(r => {
    const data = r.data || {};
    const dist = data.quality_distribution || data.distribution || {};
    return {
      ...data,
      total_memories: data.total_memories || data.total_count || 0,
      avg_quality_score: data.avg_quality_score || data.average_score || 0,
      quality_distribution: {
        excellent: dist.excellent || 0,
        good: dist.good || 0,
        fair: dist.fair || dist.moderate || 0,
        poor: dist.poor || 0,
        very_poor: dist.very_poor || dist.low || 0,
      },
    } as QualityStats;
  });

// Get quality trend for a specific memory
export const getQualityTrend = (memoryId: string) =>
  apiClient.get<QualityTrend>(`/quality/${memoryId}/trend`).then(r => r.data);

// Trigger quality score update for all memories
export const updateQualityScores = () =>
  apiClient.post('/quality/update').then(r => r.data);

// Get promotion candidates
export const getPromotionCandidates = (limit: number = 10) =>
  apiClient.get<PromotionCandidate[]>('/quality/promotion-candidates', {
    params: { limit }
  }).then(r => r.data);

// Promote a batch of memories
export const promoteBatch = (memoryIds: string[]) =>
  apiClient.post('/quality/promote-batch', { memory_ids: memoryIds }).then(r => r.data);

// Rate a memory (user feedback)
export const rateMemory = (memoryId: string, rating: number, feedback?: string) =>
  apiClient.post(`/quality/${memoryId}/rate`, { rating, feedback }).then(r => r.data);
