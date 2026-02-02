import { apiClient } from './client';
import type {
  QualityStats,
  QualityTrend,
  PromotionCandidate,
} from '../types/memory';

// Get overall quality statistics
export const getQualityStats = () =>
  apiClient.get<QualityStats>('/quality/stats').then(r => r.data);

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
