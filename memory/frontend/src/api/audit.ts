import { apiClient } from './client';
import type {
  AuditEntry,
  AuditStats,
  MemoryVersion,
  AuditAction,
} from '../types/memory';

// Get audit trail for a specific memory or global
export const getAuditTrail = (memoryId?: string, limit: number = 50, action?: AuditAction, actor?: string) =>
  apiClient.get<{ total_entries: number; offset: number; limit: number; entries: AuditEntry[] }>(
    memoryId ? `/audit/${memoryId}` : '/audit',
    { params: { limit, action, actor } }
  ).then(r => r.data.entries);

// Get audit statistics - normalize response since backend may return incomplete data
export const getAuditStats = (memoryId?: string) =>
  apiClient.get<any>('/audit/stats', {
    params: { memory_id: memoryId }
  }).then(r => {
    const data = r.data || {};
    return {
      total_entries: data.total_entries || 0,
      by_action: data.by_action || {},
      by_actor: data.by_actor || {},
      activity_by_day: data.activity_by_day || [],
      recent_activity: data.recent_activity || data.entries || [],
    } as AuditStats;
  });

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
