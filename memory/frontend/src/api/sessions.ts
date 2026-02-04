import { apiClient } from './client';

export interface SessionStats {
  total_sessions: number;
  active_sessions: number;
  avg_memories_per_session: number;
  consolidation_rate: number;
  recent_sessions: Array<{
    session_id: string;
    memory_count: number;
    created_at: string;
    status: string;
  }>;
}

export interface SessionMemory {
  id: string;
  type: string;
  content: string;
  created_at: string;
  tags: string[];
  project?: string;
}

export interface ConsolidationResult {
  session_id: string;
  memories_consolidated: number;
  summary: string;
  status: string;
}

export interface BatchConsolidationResult {
  sessions_processed: number;
  total_memories_consolidated: number;
  results: ConsolidationResult[];
}

export interface NewSessionResult {
  session_id: string;
  created_at: string;
  project?: string;
}

export const getSessionStats = () =>
  apiClient.get<SessionStats>('/sessions/stats').then(r => r.data);

export const getSessionMemories = (sessionId: string) =>
  apiClient.get<SessionMemory[]>(`/sessions/${sessionId}/memories`).then(r => r.data);

export const consolidateSession = (sessionId: string) =>
  apiClient.post<ConsolidationResult>(`/sessions/${sessionId}/consolidate`).then(r => r.data);

export const batchConsolidateSessions = (olderThanHours?: number) =>
  apiClient.post<BatchConsolidationResult>('/sessions/consolidate/batch', null, {
    params: { older_than_hours: olderThanHours }
  }).then(r => r.data);

export const createSession = (project?: string) =>
  apiClient.post<NewSessionResult>('/sessions/new', null, {
    params: { project }
  }).then(r => r.data);
