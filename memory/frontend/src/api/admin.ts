import { apiClient } from './client';

export interface CacheStats {
  total_entries: number;
  hit_rate: number;
  memory_usage: string;
}

export interface DatabaseStats {
  qdrant: Record<string, any>;
  neo4j: Record<string, any>;
  total_memories: number;
  total_relationships: number;
}

export interface NotificationStats {
  total: number;
  unread: number;
  by_type: Record<string, number>;
}

export interface SuggestionThrottleStatus {
  should_show: boolean;
  reason?: string;
  cooldown_remaining?: number;
}

export interface SuggestionStats {
  total_shown: number;
  total_useful: number;
  total_not_useful: number;
  usefulness_rate: number;
}

export interface BackupInfo {
  name: string;
  created_at: string;
  size: string;
  path: string;
}

export interface DetailedHealth {
  status: string;
  qdrant: Record<string, any>;
  neo4j: Record<string, any>;
  scheduler: Record<string, any>;
  uptime: string;
}

export interface SchedulerStatus {
  running: boolean;
  jobs: Array<{
    id: string;
    name: string;
    next_run: string;
    last_run?: string;
    status: string;
  }>;
}

export interface JobInfo {
  id: string;
  status: string;
  progress?: number;
  result?: any;
  error?: string;
  created_at: string;
}

// Cache
export const getCacheStats = () =>
  apiClient.get<CacheStats>('/cache/stats').then(r => r.data);

export const clearCache = () =>
  apiClient.post('/cache/clear').then(r => r.data);

// Jobs
export const getJobStatus = (jobId: string) =>
  apiClient.get<JobInfo>(`/jobs/${jobId}`).then(r => r.data);

export const listJobs = (limit: number = 20) =>
  apiClient.get<JobInfo[]>('/jobs', { params: { limit } }).then(r => r.data);

export const cancelJob = (jobId: string) =>
  apiClient.post(`/jobs/${jobId}/cancel`).then(r => r.data);

// Scheduler
export const getSchedulerStatus = () =>
  apiClient.get<SchedulerStatus>('/scheduler/status').then(r => r.data);

export const triggerScheduledJob = (jobId: string) =>
  apiClient.post(`/scheduler/jobs/${jobId}/trigger`).then(r => r.data);

// Database
export const getDatabaseStats = () =>
  apiClient.get<DatabaseStats>('/database/stats').then(r => r.data);

// Notifications
export const clearAllNotifications = () =>
  apiClient.delete('/notifications').then(r => r.data);

export const getNotificationStats = () =>
  apiClient.get<NotificationStats>('/notifications/stats').then(r => r.data);

// Suggestions
export const getSuggestionThrottleStatus = (userId?: string) =>
  apiClient.get<SuggestionThrottleStatus>('/suggestions/should-show', {
    params: { user_id: userId }
  }).then(r => r.data);

export const submitSuggestionFeedback = (userId: string, wasUseful: boolean) =>
  apiClient.post('/suggestions/feedback', null, {
    params: { user_id: userId, was_useful: wasUseful }
  }).then(r => r.data);

export const getSuggestionStats = (userId?: string) =>
  apiClient.get<SuggestionStats>('/suggestions/stats', {
    params: { user_id: userId }
  }).then(r => r.data);

// Export & Backup
export const exportMemories = (params?: {
  format?: string;
  type?: string;
  project?: string;
  date_from?: string;
  date_to?: string;
  tags?: string;
  include_relationships?: boolean;
}) =>
  apiClient.get('/export/memories', { params, responseType: 'blob' }).then(r => r.data);

export const createBackup = (backupName?: string) =>
  apiClient.post('/backup', null, { params: { backup_name: backupName } }).then(r => r.data);

export const listBackups = () =>
  apiClient.get<BackupInfo[]>('/backups').then(r => r.data);

// Health
export const getDetailedHealth = () =>
  apiClient.get<DetailedHealth>('/health/detailed').then(r => r.data);

// Indexing
export const triggerReindex = (folders?: string) =>
  apiClient.post('/indexing/reindex', null, { params: { folders } }).then(r => r.data);

export const getIndexingFolders = () =>
  apiClient.get<string[]>('/indexing/folders').then(r => r.data);

export const updateIndexingFolders = (folders: string[]) =>
  apiClient.post('/indexing/folders', { folders }).then(r => r.data);

// Processes
export const getWatcherStatus = () =>
  apiClient.get('/processes/watcher/status').then(r => r.data);

export const startWatcher = (interval: number = 60) =>
  apiClient.post('/processes/watcher/start', null, { params: { interval } }).then(r => r.data);

export const stopWatcher = () =>
  apiClient.post('/processes/watcher/stop').then(r => r.data);

// Logs
export const readLog = (logName: string, lines: number = 100) =>
  apiClient.get(`/logs/${logName}`, { params: { lines } }).then(r => r.data);

export const clearLog = (logName: string) =>
  apiClient.post(`/logs/${logName}/clear`).then(r => r.data);
