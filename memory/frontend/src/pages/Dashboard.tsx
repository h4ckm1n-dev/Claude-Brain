import { lazy, Suspense } from 'react';
import { useStats, useGraphStats, useMemories } from '../hooks/useMemories';
import { useDocumentStats } from '../hooks/useDocuments';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Header } from '../components/layout/Header';
import { Database, Archive, AlertCircle, Network, TrendingUp, Activity, FileText, Brain, Sparkles, Zap } from 'lucide-react';
import { Badge } from '../components/ui/badge';
import { formatDistanceToNow } from 'date-fns';
import type { Memory } from '../types/memory';
import { MemoryTypeBadge } from '../components/memory/MemoryTypeBadge';
import { StorageOverview } from '../components/dashboard/StorageOverview';
import { ProjectBreakdown } from '../components/dashboard/ProjectBreakdown';
import { HealthIndicators } from '../components/dashboard/HealthIndicators';
import { RecentErrors } from '../components/dashboard/RecentErrors';
import { QuickActions } from '../components/dashboard/QuickActions';
import { TypeBreakdown } from '../components/dashboard/TypeBreakdown';
import { AdvancedBrainMetrics } from '../components/dashboard/AdvancedBrainMetrics';

// Lazy load charts
const ActivityTimeline = lazy(() => import('../components/analytics/ActivityTimeline').then(m => ({ default: m.ActivityTimeline })));
const ImportanceDistribution = lazy(() => import('../components/analytics/ImportanceDistribution').then(m => ({ default: m.ImportanceDistribution })));
const EnhancedPieChart = lazy(() => import('../components/analytics/EnhancedPieChart').then(m => ({ default: m.EnhancedPieChart })));
const TagCloud = lazy(() => import('../components/analytics/TagCloud').then(m => ({ default: m.TagCloud })));

function ChartLoading() {
  return (
    <div className="h-[300px] flex items-center justify-center">
      <div className="h-8 w-8 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" />
    </div>
  );
}

export function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useStats();
  const { data: graphStats } = useGraphStats();
  const { data: documentStats } = useDocumentStats();
  const { data: recentMemories } = useMemories({ limit: 100 });
  const { data: allMemories } = useMemories({ limit: 500 });

  if (statsLoading) {
    return (
      <div>
        <Header title="Dashboard" />
        <div className="p-8">
          <div className="flex items-center justify-center h-64">
            <div className="relative">
              <div className="h-12 w-12 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" />
              <Sparkles className="h-6 w-6 text-blue-500 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  const totalItems = (stats?.total_memories || 0) + (documentStats?.total_chunks || 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]">
      <Header title="Dashboard" />
      <div className="p-6 sm:p-8 max-w-[1800px] mx-auto space-y-8">

        {/* Hero Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-500/10 via-purple-500/10 to-emerald-500/10 p-8 border border-white/5">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-purple-500/5" />
          <div className="relative flex items-center gap-6">
            <div className="relative">
              <div className="absolute inset-0 bg-blue-500/20 rounded-2xl blur-xl" />
              <div className="relative bg-gradient-to-br from-blue-500 to-purple-500 p-4 rounded-2xl">
                <Brain className="h-12 w-12 text-white" />
              </div>
            </div>
            <div className="flex-1">
              <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-emerald-400 bg-clip-text text-transparent">
                Claude Brain
              </h1>
              <p className="text-lg text-white/60 mt-2 flex items-center gap-2">
                <Zap className="h-4 w-4 text-emerald-400" />
                {totalItems.toLocaleString()} indexed items
                <span className="text-white/40">•</span>
                <span className="text-purple-400">{stats?.active_memories || 0} active memories</span>
              </p>
            </div>
            <div className="hidden lg:flex items-center gap-3">
              {stats?.hybrid_search_enabled && (
                <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20">
                  <Sparkles className="h-3 w-3 mr-1" />
                  Hybrid Search
                </Badge>
              )}
              {graphStats?.enabled && (
                <Badge className="bg-purple-500/10 text-purple-400 border-purple-500/20 hover:bg-purple-500/20">
                  <Network className="h-3 w-3 mr-1" />
                  Knowledge Graph
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* Key Metrics Grid */}
        <div className="grid gap-4 sm:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
          {/* Memories Card */}
          <div className="group relative">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-blue-600 rounded-2xl opacity-20 group-hover:opacity-40 transition blur" />
            <Card className="relative bg-[#0f0f0f] border-white/10 hover:border-blue-500/50 transition-all duration-300 overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl" />
              <CardContent className="pt-6 relative">
                <div className="flex items-start justify-between mb-4">
                  <div className="p-3 bg-blue-500/10 rounded-xl ring-1 ring-blue-500/20">
                    <Database className="h-6 w-6 text-blue-400" />
                  </div>
                  <Badge variant="outline" className="border-blue-500/20 text-blue-400">
                    Active
                  </Badge>
                </div>
                <p className="text-sm text-white/50 mb-1">Total Memories</p>
                <p className="text-4xl font-bold text-white mb-2">{stats?.total_memories || 0}</p>
                <p className="text-xs text-blue-400">
                  {stats?.active_memories || 0} active • {stats?.archived_memories || 0} archived
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Documents Card */}
          <div className="group relative">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-500 to-purple-600 rounded-2xl opacity-20 group-hover:opacity-40 transition blur" />
            <Card className="relative bg-[#0f0f0f] border-white/10 hover:border-purple-500/50 transition-all duration-300 overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full blur-3xl" />
              <CardContent className="pt-6 relative">
                <div className="flex items-start justify-between mb-4">
                  <div className="p-3 bg-purple-500/10 rounded-xl ring-1 ring-purple-500/20">
                    <FileText className="h-6 w-6 text-purple-400" />
                  </div>
                  <Badge variant="outline" className="border-purple-500/20 text-purple-400">
                    Indexed
                  </Badge>
                </div>
                <p className="text-sm text-white/50 mb-1">Document Chunks</p>
                <p className="text-4xl font-bold text-white mb-2">{documentStats?.total_chunks || 0}</p>
                <p className="text-xs text-purple-400">
                  {((documentStats?.total_chunks || 0) / 1000).toFixed(1)}K chunks indexed
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Knowledge Graph Card */}
          <div className="group relative">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500 to-emerald-600 rounded-2xl opacity-20 group-hover:opacity-40 transition blur" />
            <Card className="relative bg-[#0f0f0f] border-white/10 hover:border-emerald-500/50 transition-all duration-300 overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/10 rounded-full blur-3xl" />
              <CardContent className="pt-6 relative">
                <div className="flex items-start justify-between mb-4">
                  <div className="p-3 bg-emerald-500/10 rounded-xl ring-1 ring-emerald-500/20">
                    <Network className="h-6 w-6 text-emerald-400" />
                  </div>
                  <Badge variant="outline" className="border-emerald-500/20 text-emerald-400">
                    Live
                  </Badge>
                </div>
                <p className="text-sm text-white/50 mb-1">Relationships</p>
                <p className="text-4xl font-bold text-white mb-2">{graphStats?.relationships || 0}</p>
                <p className="text-xs text-emerald-400">
                  {((graphStats?.memory_nodes || 0) + (graphStats?.project_nodes || 0) + (graphStats?.tag_nodes || 0))} nodes connected
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Unresolved Errors Card */}
          <div className="group relative">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-rose-500 to-rose-600 rounded-2xl opacity-20 group-hover:opacity-40 transition blur" />
            <Card className="relative bg-[#0f0f0f] border-white/10 hover:border-rose-500/50 transition-all duration-300 overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/10 rounded-full blur-3xl" />
              <CardContent className="pt-6 relative">
                <div className="flex items-start justify-between mb-4">
                  <div className="p-3 bg-rose-500/10 rounded-xl ring-1 ring-rose-500/20">
                    <AlertCircle className="h-6 w-6 text-rose-400" />
                  </div>
                  <Badge variant="outline" className="border-rose-500/20 text-rose-400">
                    {stats?.unresolved_errors === 0 ? 'Healthy' : 'Alert'}
                  </Badge>
                </div>
                <p className="text-sm text-white/50 mb-1">Unresolved</p>
                <p className="text-4xl font-bold text-white mb-2">{stats?.unresolved_errors || 0}</p>
                <p className="text-xs text-rose-400">
                  {stats?.unresolved_errors === 0 ? 'All systems nominal' : 'Needs attention'}
                </p>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Quick Actions */}
        <QuickActions />

        {/* Advanced Analytics */}
        <Card className="bg-[#0f0f0f] border-white/10 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 via-transparent to-blue-500/5 pointer-events-none" />
          <CardHeader className="border-b border-white/5 relative">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/10 rounded-lg">
                <Sparkles className="h-5 w-5 text-purple-400" />
              </div>
              <div>
                <CardTitle className="text-2xl font-bold text-white">Advanced Analytics</CardTitle>
                <CardDescription className="text-white/50">In-depth visualization of memory patterns</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-8 relative">
            <div className="grid gap-6 lg:grid-cols-3">
              <Card className="bg-[#0a0a0a] border-white/10">
                <CardHeader className="border-b border-white/5">
                  <CardTitle className="text-lg font-semibold text-white">Importance Distribution</CardTitle>
                </CardHeader>
                <CardContent className="pt-6">
                  {recentMemories && recentMemories.length > 0 ? (
                    <Suspense fallback={<ChartLoading />}>
                      <ImportanceDistribution memories={recentMemories} />
                    </Suspense>
                  ) : (
                    <div className="h-[250px] flex items-center justify-center text-white/30 text-sm">
                      No data available
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="bg-[#0a0a0a] border-white/10">
                <CardHeader className="border-b border-white/5">
                  <CardTitle className="text-lg font-semibold text-white">Memory Types</CardTitle>
                </CardHeader>
                <CardContent className="pt-6">
                  {recentMemories && recentMemories.length > 0 ? (
                    <Suspense fallback={<ChartLoading />}>
                      <EnhancedPieChart memories={recentMemories} />
                    </Suspense>
                  ) : (
                    <div className="h-[250px] flex items-center justify-center text-white/30 text-sm">
                      No data available
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="bg-[#0a0a0a] border-white/10">
                <CardHeader className="border-b border-white/5">
                  <CardTitle className="text-lg font-semibold text-white">Tag Cloud</CardTitle>
                </CardHeader>
                <CardContent className="pt-6">
                  {recentMemories && recentMemories.length > 0 ? (
                    <Suspense fallback={<ChartLoading />}>
                      <TagCloud memories={recentMemories} />
                    </Suspense>
                  ) : (
                    <div className="h-[250px] flex items-center justify-center text-white/30 text-sm">
                      No tags available
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </CardContent>
        </Card>

        {/* System Health & Storage */}
        <div className="grid gap-6 lg:grid-cols-3">
          <HealthIndicators memoryStats={stats} graphStats={graphStats} documentStats={documentStats} />
          <StorageOverview memoryStats={stats} documentStats={documentStats} />
          <RecentErrors memories={allMemories} />
        </div>

        {/* Recent Activity */}
        <Card className="bg-[#0f0f0f] border-white/10 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-purple-500/5 pointer-events-none" />
          <CardHeader className="border-b border-white/5 relative">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <Activity className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <CardTitle className="text-2xl font-bold text-white">Recent Activity</CardTitle>
                  <CardDescription className="text-white/50">Latest memories created</CardDescription>
                </div>
              </div>
              <Badge variant="outline" className="border-blue-500/20 text-blue-400">
                {recentMemories?.length || 0} items
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-0 relative">
            <div className="divide-y divide-white/5">
              {recentMemories && recentMemories.length > 0 ? (
                recentMemories.slice(0, 8).map((memory: Memory) => (
                  <div
                    key={memory.id}
                    className="p-4 hover:bg-white/5 transition-all duration-200 group cursor-pointer"
                  >
                    <div className="flex items-start gap-4">
                      <div className="mt-1">
                        <MemoryTypeBadge type={memory.type} />
                      </div>
                      <div className="flex-1 min-w-0 space-y-2">
                        <p className="text-sm text-white/90 line-clamp-2 group-hover:text-white transition-colors">
                          {memory.content}
                        </p>
                        <div className="flex items-center gap-3 text-xs">
                          <span className="text-white/40">
                            {formatDistanceToNow(new Date(memory.created_at), { addSuffix: true })}
                          </span>
                          {memory.project && (
                            <>
                              <span className="text-white/20">•</span>
                              <span className="text-blue-400">{memory.project}</span>
                            </>
                          )}
                          {memory.tags && memory.tags.length > 0 && (
                            <>
                              <span className="text-white/20">•</span>
                              <div className="flex gap-1">
                                {memory.tags.slice(0, 3).map(tag => (
                                  <Badge
                                    key={tag}
                                    variant="outline"
                                    className="text-xs border-purple-500/20 text-purple-400 hover:bg-purple-500/10"
                                  >
                                    {tag}
                                  </Badge>
                                ))}
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="h-48 flex flex-col items-center justify-center text-white/30">
                  <Archive className="h-12 w-12 mb-3 opacity-20" />
                  <p>No recent memories</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Advanced Brain Metrics */}
        <AdvancedBrainMetrics />

        {/* Analytics Grid */}
        <div className="grid gap-6 lg:grid-cols-2">
          <TypeBreakdown memories={allMemories} />
          <ProjectBreakdown memories={allMemories} />
        </div>

        {/* Activity Timeline */}
        <Card className="bg-[#0f0f0f] border-white/10 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 via-transparent to-blue-500/5 pointer-events-none" />
          <CardHeader className="border-b border-white/5 relative">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-500/10 rounded-lg">
                <TrendingUp className="h-5 w-5 text-emerald-400" />
              </div>
              <div>
                <CardTitle className="text-2xl font-bold text-white">Activity Timeline</CardTitle>
                <CardDescription className="text-white/50">Memory creation over the last 30 days</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-6 relative">
            {recentMemories && recentMemories.length > 0 ? (
              <Suspense fallback={<ChartLoading />}>
                <ActivityTimeline memories={recentMemories} />
              </Suspense>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-white/30">
                No activity data
              </div>
            )}
          </CardContent>
        </Card>


        {/* System Configuration */}
        <Card className="bg-[#0f0f0f] border-white/10 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-amber-500/5 via-transparent to-rose-500/5 pointer-events-none" />
          <CardHeader className="border-b border-white/5 relative">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-500/10 rounded-lg">
                <Zap className="h-5 w-5 text-amber-400" />
              </div>
              <CardTitle className="text-2xl font-bold text-white">System Configuration</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="pt-8 relative">
            <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  <p className="text-sm text-white/50">Hybrid Search</p>
                </div>
                <Badge
                  className={
                    stats?.hybrid_search_enabled
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      : "bg-white/5 text-white/30 border-white/10"
                  }
                >
                  {stats?.hybrid_search_enabled ? "Enabled" : "Disabled"}
                </Badge>
                <p className="text-xs text-white/30">Semantic + Keyword</p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-blue-400 animate-pulse" />
                  <p className="text-sm text-white/50">Vector Space</p>
                </div>
                <p className="text-3xl font-bold text-white">{stats?.embedding_dim || 0}D</p>
                <p className="text-xs text-white/30">Embedding dimensions</p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-purple-400 animate-pulse" />
                  <p className="text-sm text-white/50">Knowledge Graph</p>
                </div>
                <Badge
                  className={
                    graphStats?.enabled
                      ? "bg-purple-500/10 text-purple-400 border-purple-500/20"
                      : "bg-white/5 text-white/30 border-white/10"
                  }
                >
                  {graphStats?.enabled ? "Active" : "Inactive"}
                </Badge>
                <p className="text-xs text-white/30">{graphStats?.relationships || 0} connections</p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                  <p className="text-sm text-white/50">Document Index</p>
                </div>
                <Badge
                  className={
                    documentStats?.status === 'green'
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      : "bg-white/5 text-white/30 border-white/10"
                  }
                >
                  {documentStats?.status || 'Unknown'}
                </Badge>
                <p className="text-xs text-white/30">Auto-indexing active</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
