import { useState } from 'react';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import {
  useDetailedHealth,
  useCacheStats,
  useClearCache,
  useDatabaseStats,
  useSchedulerStatus,
  useTriggerScheduledJob,
  useNotificationStats,
  useClearAllNotifications,
  useExportMemories,
  useCreateBackup,
  useBackups,
  useJobs,
  useCancelJob,
  useSuggestionStats,
  useTriggerReindex,
} from '../hooks/useAdmin';
import {
  Shield,
  Database,
  HardDrive,
  Clock,
  Bell,
  Download,
  Archive,
  Play,
  XCircle,
  Trash2,
  RefreshCw,
  Activity,
  Server,
  Zap,
} from 'lucide-react';

export function SystemAdmin() {
  const [backupName, setBackupName] = useState('');
  const [exportFormat, setExportFormat] = useState('json');
  const [reindexFolders, setReindexFolders] = useState('');

  const { data: health } = useDetailedHealth();
  const { data: cacheStats } = useCacheStats();
  const { data: dbStats } = useDatabaseStats();
  const { data: scheduler } = useSchedulerStatus();
  const { data: notifStats } = useNotificationStats();
  const { data: jobs } = useJobs(20);
  const { data: backups } = useBackups();
  const { data: suggestionStats } = useSuggestionStats();

  const clearCache = useClearCache();
  const triggerJob = useTriggerScheduledJob();
  const clearNotifications = useClearAllNotifications();
  const exportMemories = useExportMemories();
  const createBackup = useCreateBackup();
  const cancelJob = useCancelJob();
  const triggerReindex = useTriggerReindex();

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]">
      <Header title="System Admin" />
      <div className="p-6 space-y-6">
        {/* Hero */}
        <div className="bg-gradient-to-br from-red-600 via-rose-600 to-pink-600 rounded-2xl p-8 shadow-2xl">
          <div className="flex items-center gap-4">
            <div className="p-4 bg-white/20 backdrop-blur-sm rounded-xl">
              <Shield className="h-10 w-10 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">System Administration</h1>
              <p className="text-red-100 mt-1">
                Advanced system management, monitoring, and maintenance
              </p>
            </div>
          </div>
        </div>

        {/* System Health */}
        <Card className="bg-[#0f0f0f] border border-white/10">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-green-400" />
              <CardTitle className="text-white">System Health</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-white/60">Status</span>
                  <Badge className={
                    health?.status === 'healthy'
                      ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                      : 'bg-red-500/20 text-red-300 border border-red-500/30'
                  }>
                    {health?.status ?? 'unknown'}
                  </Badge>
                </div>
                <p className="text-xs text-white/40">Uptime: {health?.uptime ?? '...'}</p>
              </div>
              <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-white/60">Qdrant</span>
                  <Badge className={
                    health?.qdrant?.status === 'healthy'
                      ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                      : 'bg-red-500/20 text-red-300 border border-red-500/30'
                  }>
                    {health?.qdrant?.status ?? 'unknown'}
                  </Badge>
                </div>
                <p className="text-xs text-white/50">
                  {health?.qdrant?.details?.points_count ?? '?'} points
                </p>
              </div>
              <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-white/60">Neo4j</span>
                  <Badge className={
                    health?.neo4j?.status === 'healthy'
                      ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                      : 'bg-red-500/20 text-red-300 border border-red-500/30'
                  }>
                    {health?.neo4j?.status ?? 'unknown'}
                  </Badge>
                </div>
                <p className="text-xs text-white/50">
                  {health?.neo4j?.details?.memory_nodes ?? '?'} nodes, {health?.neo4j?.details?.relationships ?? '?'} relationships
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Cache Management */}
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-amber-400" />
                  <CardTitle className="text-white">Cache</CardTitle>
                </div>
                <Button
                  size="sm"
                  onClick={() => clearCache.mutate()}
                  disabled={clearCache.isPending}
                  className="bg-amber-500 hover:bg-amber-600 text-white"
                >
                  <Trash2 className="h-3 w-3 mr-1" />
                  Clear
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
                  <p className="text-xs text-white/50">Entries</p>
                  <p className="text-lg font-bold text-white">{cacheStats?.total_entries ?? 0}</p>
                </div>
                <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
                  <p className="text-xs text-white/50">Hit Rate</p>
                  <p className="text-lg font-bold text-white">
                    {((cacheStats?.hit_rate ?? 0) * 100).toFixed(0)}%
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
                  <p className="text-xs text-white/50">Memory</p>
                  <p className="text-lg font-bold text-white">{cacheStats?.memory_usage ?? '0'}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Database Stats */}
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5 text-blue-400" />
                <CardTitle className="text-white">Database</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
                  <p className="text-xs text-white/50">Memories</p>
                  <p className="text-lg font-bold text-white">{dbStats?.total_memories ?? 0}</p>
                </div>
                <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
                  <p className="text-xs text-white/50">Relationships</p>
                  <p className="text-lg font-bold text-white">{dbStats?.total_relationships ?? 0}</p>
                </div>
              </div>
              {dbStats?.neo4j && (
                <div className="grid grid-cols-3 gap-2">
                  <div className="p-2 rounded bg-[#0a0a0a] border border-white/5 text-center">
                    <p className="text-xs text-white/40">Memory Nodes</p>
                    <p className="text-sm font-bold text-blue-300">{dbStats.neo4j.memory_nodes ?? 0}</p>
                  </div>
                  <div className="p-2 rounded bg-[#0a0a0a] border border-white/5 text-center">
                    <p className="text-xs text-white/40">Projects</p>
                    <p className="text-sm font-bold text-green-300">{dbStats.neo4j.project_nodes ?? 0}</p>
                  </div>
                  <div className="p-2 rounded bg-[#0a0a0a] border border-white/5 text-center">
                    <p className="text-xs text-white/40">Tags</p>
                    <p className="text-sm font-bold text-purple-300">{dbStats.neo4j.tag_nodes ?? 0}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Notification Management */}
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bell className="h-5 w-5 text-purple-400" />
                  <CardTitle className="text-white">Notifications</CardTitle>
                </div>
                <Button
                  size="sm"
                  onClick={() => clearNotifications.mutate()}
                  disabled={clearNotifications.isPending}
                  className="bg-purple-500 hover:bg-purple-600 text-white"
                >
                  <Trash2 className="h-3 w-3 mr-1" />
                  Clear All
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
                  <p className="text-xs text-white/50">Total</p>
                  <p className="text-lg font-bold text-white">{notifStats?.total ?? 0}</p>
                </div>
                <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
                  <p className="text-xs text-white/50">Unread</p>
                  <p className="text-lg font-bold text-amber-400">{notifStats?.unread ?? 0}</p>
                </div>
              </div>
              {notifStats?.by_type && Object.keys(notifStats.by_type).length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {Object.entries(notifStats.by_type).map(([type, count]) => (
                    <Badge key={type} className="bg-white/5 text-white/60 border border-white/10">
                      {type}: {count}
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Suggestion Intelligence */}
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Server className="h-5 w-5 text-teal-400" />
                <CardTitle className="text-white">Suggestion Intelligence</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
                  <p className="text-xs text-white/50">Total Shown</p>
                  <p className="text-lg font-bold text-white">{suggestionStats?.total_shown ?? 0}</p>
                </div>
                <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
                  <p className="text-xs text-white/50">Usefulness Rate</p>
                  <p className="text-lg font-bold text-teal-400">
                    {((suggestionStats?.usefulness_rate ?? 0) * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
                  <p className="text-xs text-white/50">Useful</p>
                  <p className="text-sm font-bold text-green-400">{suggestionStats?.total_useful ?? 0}</p>
                </div>
                <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
                  <p className="text-xs text-white/50">Not Useful</p>
                  <p className="text-sm font-bold text-red-400">{suggestionStats?.total_not_useful ?? 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Scheduler Control */}
        <Card className="bg-[#0f0f0f] border border-white/10">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-blue-400" />
              <CardTitle className="text-white">Scheduler Jobs</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              View and trigger scheduled background jobs
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-[400px] overflow-y-auto">
              {scheduler?.jobs?.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5"
                >
                  <div className="flex items-center gap-3">
                    <Badge className={
                      job.status === 'running'
                        ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                        : 'bg-white/10 text-white/50 border border-white/10'
                    }>
                      {job.status}
                    </Badge>
                    <div>
                      <p className="text-sm text-white/80">{job.name}</p>
                      <p className="text-xs text-white/40">
                        Next: {job.next_run ? new Date(job.next_run).toLocaleString() : 'N/A'}
                      </p>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => triggerJob.mutate(job.id)}
                    disabled={triggerJob.isPending}
                    className="border-blue-500/30 text-blue-300 hover:bg-blue-500/20"
                  >
                    <Play className="h-3 w-3 mr-1" />
                    Trigger
                  </Button>
                </div>
              ))}
              {(!scheduler?.jobs || scheduler.jobs.length === 0) && (
                <p className="text-white/50 text-center py-4">No scheduled jobs</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Active Jobs */}
        <Card className="bg-[#0f0f0f] border border-white/10">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-green-400" />
              <CardTitle className="text-white">Active Jobs</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-[300px] overflow-y-auto">
              {jobs?.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5"
                >
                  <div className="flex items-center gap-3">
                    <Badge className={
                      job.status === 'running'
                        ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                        : job.status === 'completed'
                          ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                          : job.status === 'failed'
                            ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                            : 'bg-white/10 text-white/50 border border-white/10'
                    }>
                      {job.status}
                    </Badge>
                    <div>
                      <p className="text-sm font-mono text-white/80">{job.id.slice(0, 12)}...</p>
                      <p className="text-xs text-white/40">
                        {new Date(job.created_at).toLocaleString()}
                      </p>
                    </div>
                    {job.progress !== undefined && (
                      <div className="w-24 h-2 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-green-500 rounded-full"
                          style={{ width: `${job.progress}%` }}
                        />
                      </div>
                    )}
                  </div>
                  {job.status === 'running' && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => cancelJob.mutate(job.id)}
                      disabled={cancelJob.isPending}
                      className="border-red-500/30 text-red-300 hover:bg-red-500/20"
                    >
                      <XCircle className="h-3 w-3 mr-1" />
                      Cancel
                    </Button>
                  )}
                </div>
              ))}
              {(!jobs || jobs.length === 0) && (
                <p className="text-white/50 text-center py-4">No active jobs</p>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Export & Backup */}
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Download className="h-5 w-5 text-green-400" />
                <CardTitle className="text-white">Export & Backup</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm text-white/60 mb-2">Export Format</label>
                <div className="flex gap-2">
                  {['json', 'csv', 'obsidian'].map((fmt) => (
                    <Button
                      key={fmt}
                      size="sm"
                      variant={exportFormat === fmt ? 'default' : 'outline'}
                      onClick={() => setExportFormat(fmt)}
                      className={exportFormat === fmt
                        ? 'bg-green-500 text-white'
                        : 'border-white/10 text-white/60'
                      }
                    >
                      {fmt.toUpperCase()}
                    </Button>
                  ))}
                </div>
                <Button
                  onClick={() => exportMemories.mutate({ format: exportFormat })}
                  disabled={exportMemories.isPending}
                  className="w-full mt-3 bg-green-500 hover:bg-green-600 text-white"
                >
                  <Download className="mr-2 h-4 w-4" />
                  Export Memories
                </Button>
              </div>

              <div className="border-t border-white/5 pt-4">
                <label className="block text-sm text-white/60 mb-2">Create Backup</label>
                <div className="flex gap-2">
                  <Input
                    value={backupName}
                    onChange={(e) => setBackupName(e.target.value)}
                    placeholder="Backup name (optional)"
                    className="bg-[#0a0a0a] border-white/10 text-white"
                  />
                  <Button
                    onClick={() => {
                      createBackup.mutate(backupName || undefined);
                      setBackupName('');
                    }}
                    disabled={createBackup.isPending}
                    className="bg-blue-500 hover:bg-blue-600 text-white whitespace-nowrap"
                  >
                    <Archive className="mr-2 h-4 w-4" />
                    Backup
                  </Button>
                </div>
              </div>

              {backups && backups.length > 0 && (
                <div className="border-t border-white/5 pt-4">
                  <p className="text-sm text-white/60 mb-2">Recent Backups</p>
                  <div className="space-y-2 max-h-[200px] overflow-y-auto">
                    {backups.map((backup) => (
                      <div
                        key={backup.name}
                        className="flex items-center justify-between p-2 rounded bg-[#0a0a0a] border border-white/5"
                      >
                        <div>
                          <p className="text-sm text-white/80">{backup.name}</p>
                          <p className="text-xs text-white/40">
                            {new Date(backup.created_at).toLocaleString()} - {backup.size}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Document Reindex */}
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardHeader>
              <div className="flex items-center gap-2">
                <HardDrive className="h-5 w-5 text-orange-400" />
                <CardTitle className="text-white">Document Indexing</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm text-white/60 mb-2">Reindex Folders</label>
                <div className="flex gap-2">
                  <Input
                    value={reindexFolders}
                    onChange={(e) => setReindexFolders(e.target.value)}
                    placeholder="Folder paths (comma-separated, optional)"
                    className="bg-[#0a0a0a] border-white/10 text-white"
                  />
                  <Button
                    onClick={() => triggerReindex.mutate(reindexFolders || undefined)}
                    disabled={triggerReindex.isPending}
                    className="bg-orange-500 hover:bg-orange-600 text-white whitespace-nowrap"
                  >
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Reindex
                  </Button>
                </div>
              </div>
              {triggerReindex.isSuccess && (
                <p className="text-sm text-green-400">Reindex triggered successfully</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
