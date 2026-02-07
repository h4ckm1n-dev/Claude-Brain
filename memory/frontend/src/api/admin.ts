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
  apiClient.get('/cache/stats').then(r => {
    const d = r.data;
    return {
      total_entries: d.total_entries ?? d.stores ?? d.total_queries ?? 0,
      hit_rate: d.hit_rate ?? 0,
      memory_usage: d.memory_usage ?? `${d.stores ?? 0}/${d.max_size ?? 0}`,
    } as CacheStats;
  });

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
  apiClient.get('/scheduler/status').then(r => {
    const d = r.data;
    const jobs = (d.jobs || []).map((j: any) => ({
      id: j.id,
      name: j.name,
      next_run: j.next_run ?? null,
      last_run: j.last_run ?? null,
      status: j.status ?? (d.running ? 'scheduled' : 'paused'),
    }));
    return { running: d.running ?? false, jobs } as SchedulerStatus;
  });

export const triggerScheduledJob = (jobId: string) =>
  apiClient.post(`/scheduler/jobs/${jobId}/trigger`).then(r => r.data);

export const triggerAllScheduledJobs = () =>
  apiClient.post('/scheduler/trigger-all').then(r => r.data);

// Database — combine /database/stats with /health/detailed for full picture
export const getDatabaseStats = async (): Promise<DatabaseStats> => {
  const [dbRes, healthRes] = await Promise.all([
    apiClient.get('/database/stats').catch(() => ({ data: {} })),
    apiClient.get('/health/detailed').catch(() => ({ data: {} })),
  ]);
  const db = dbRes.data;
  const deps = healthRes.data?.dependencies || {};
  const qdrantDetails = deps.qdrant?.details || {};
  const neo4jDetails = deps.neo4j?.details || {};
  return {
    total_memories: db.points_count ?? qdrantDetails.points_count ?? 0,
    total_relationships: neo4jDetails.relationships ?? 0,
    qdrant: {
      status: db.status ?? deps.qdrant?.status ?? 'unknown',
      collection: db.collection_name ?? qdrantDetails.collection ?? '',
      points: db.points_count ?? qdrantDetails.points_count ?? 0,
    },
    neo4j: {
      memory_nodes: neo4jDetails.memory_nodes ?? 0,
      project_nodes: neo4jDetails.project_nodes ?? 0,
      tag_nodes: neo4jDetails.tag_nodes ?? 0,
      relationships: neo4jDetails.relationships ?? 0,
    },
  };
};

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
  apiClient.get('/suggestions/stats', {
    params: { user_id: userId }
  }).then(r => {
    const d = r.data;
    const totalShown = d.total_shown ?? d.total_suggestions ?? 0;
    const totalUseful = d.total_useful ?? 0;
    const totalNotUseful = d.total_not_useful ?? 0;
    const total = totalUseful + totalNotUseful;
    return {
      total_shown: totalShown,
      total_useful: totalUseful,
      total_not_useful: totalNotUseful,
      usefulness_rate: d.usefulness_rate ?? (total > 0 ? totalUseful / total : 0),
    } as SuggestionStats;
  });

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
  apiClient.get('/health/detailed').then(r => {
    const d = r.data;
    const deps = d.dependencies || {};
    const uptimeSec = d.uptime_seconds ?? 0;
    const hours = Math.floor(uptimeSec / 3600);
    const mins = Math.floor((uptimeSec % 3600) / 60);
    return {
      status: d.status ?? 'unknown',
      qdrant: deps.qdrant ?? d.qdrant ?? {},
      neo4j: deps.neo4j ?? d.neo4j ?? {},
      scheduler: d.scheduler ?? {},
      uptime: d.uptime ?? (uptimeSec > 0 ? `${hours}h ${mins}m` : 'Just started'),
      features: d.features ?? {},
      performance: d.performance ?? {},
    } as DetailedHealth;
  });

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
