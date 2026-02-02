import { apiClient } from './client';
import type {
  AuditEntry,
  AuditStats,
  MemoryVersion,
  AuditAction,
} from '../types/memory';

// Get audit trail for a specific memory or global
export const getAuditTrail = (memoryId?: string, limit: number = 50, action?: AuditAction, actor?: string) =>
  apiClient.get<AuditEntry[]>(
    memoryId ? `/audit/${memoryId}` : '/audit',
    { params: { limit, action, actor } }
  ).then(r => r.data);

// Get audit statistics
export const getAuditStats = (memoryId?: string) =>
  apiClient.get<AuditStats>('/audit/stats', {
    params: { memory_id: memoryId }
  }).then(r => r.data);

// Get version history for a memory
export const getVersionHistory = (memoryId: string) =>
  apiClient.get<MemoryVersion[]>(`/memories/${memoryId}/versions`).then(r => r.data);

// Restore a memory to a previous version
export const restoreMemory = (memoryId: string, targetTimestamp: string, actor: string = 'user') =>
  apiClient.post(`/memories/${memoryId}/restore`, null, {
    params: { target_timestamp: targetTimestamp, actor }
  }).then(r => r.data);

// Undo the last change to a memory
export const undoLastChange = (memoryId: string, actor: string = 'user') =>
  apiClient.post(`/memories/${memoryId}/undo`, null, {
    params: { actor }
  }).then(r => r.data);
