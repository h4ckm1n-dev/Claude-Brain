import { apiClient } from './client';
import type {
  LifecycleStats,
  StateHistory,
  StateTransition,
  MemoryState,
} from '../types/memory';

// Get lifecycle statistics - normalize backend field names
export const getLifecycleStats = () =>
  apiClient.get<any>('/lifecycle/stats').then(r => {
    const data = r.data || {};
    return {
      ...data,
      total_memories: data.total_memories || data.total || 0,
      state_distribution: data.state_distribution || data.distribution || {},
    } as LifecycleStats;
  });

// Trigger lifecycle state updates for all memories
export const updateLifecycleStates = () =>
  apiClient.post('/lifecycle/update').then(r => r.data);

// Manually transition a memory state
export const transitionMemoryState = (
  memoryId: string,
  newState: MemoryState,
  reason: string,
  actor: string = 'user'
) =>
  apiClient.post(`/memories/${memoryId}/state`, null, {
    params: { new_state: newState, reason, actor }
  }).then(r => r.data);

// Get state history for a specific memory
// Backend returns { memory_id, current_state, state_changed_at, state_history: [] }
// Frontend expects { memory_id, transitions: [] }
export const getStateHistory = (memoryId: string) =>
  apiClient.get<any>(`/memories/${memoryId}/state-history`).then(r => {
    const data = r.data || {};
    return {
      memory_id: data.memory_id || memoryId,
      transitions: data.transitions || data.state_history || [],
    } as StateHistory;
  });

// Get recent state transitions
export const getRecentTransitions = (limit: number = 20) =>
  apiClient.get<StateTransition[]>('/lifecycle/transitions', {
    params: { limit }
  }).then(r => r.data);
