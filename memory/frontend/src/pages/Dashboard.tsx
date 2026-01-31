import { lazy, Suspense } from 'react';
import { useStats, useGraphStats, useMemories } from '../hooks/useMemories';
import { useDocumentStats } from '../hooks/useDocuments';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Header } from '../components/layout/Header';
import { Database, Archive, AlertCircle, Network, TrendingUp, Activity, FileText, Sparkles } from 'lucide-react';
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

// Lazy load heavy chart components for better performance
const ActivityTimeline = lazy(() => import('../components/analytics/ActivityTimeline').then(m => ({ default: m.ActivityTimeline })));
const ImportanceDistribution = lazy(() => import('../components/analytics/ImportanceDistribution').then(m => ({ default: m.ImportanceDistribution })));
const EnhancedPieChart = lazy(() => import('../components/analytics/EnhancedPieChart').then(m => ({ default: m.EnhancedPieChart })));
const TagCloud = lazy(() => import('../components/analytics/TagCloud').then(m => ({ default: m.TagCloud })));
const AccessHeatmap = lazy(() => import('../components/analytics/AccessHeatmap').then(m => ({ default: m.AccessHeatmap })));
const DecayCurve = lazy(() => import('../components/analytics/DecayCurve').then(m => ({ default: m.DecayCurve })));

// Loading placeholder component
function ChartLoading() {
  return (
    <div className="h-[300px] flex items-center justify-center">
      <div className="animate-pulse flex flex-col items-center gap-2">
        <div className="h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-muted-foreground">Loading chart...</p>
      </div>
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
        <div className="p-6">
          <div className="flex items-center justify-center h-64">
            <div className="animate-pulse text-lg">Loading dashboard...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header title="Dashboard" />
      <div className="p-6 space-y-6">
        {/* Hero Section */}
        <div className="bg-gradient-to-br from-blue-600 via-purple-600 to-pink-600 rounded-2xl shadow-2xl p-8 text-white">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Sparkles className="h-8 w-8" />
                <h1 className="text-3xl font-bold">Claude Memory System</h1>
              </div>
              <p className="text-blue-100 text-lg">
                Intelligent long-term memory with vector search, knowledge graphs, and document indexing
              </p>
            </div>
            <div className="text-right">
              <div className="text-5xl font-bold">
                {((stats?.total_memories || 0) + (documentStats?.total_chunks || 0)).toLocaleString()}
              </div>
              <div className="text-blue-100 text-sm mt-1">Total Indexed Items</div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <QuickActions />

        {/* Top Stats Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="backdrop-blur-lg bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950 dark:to-blue-900 border-blue-200 dark:border-blue-800 shadow-xl shadow-blue-500/10 transition-all duration-300 hover:scale-105">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Memories</CardTitle>
              <Database className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-700 dark:text-blue-300">{stats?.total_memories || 0}</div>
              <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                {stats?.active_memories || 0} active
              </p>
            </CardContent>
          </Card>

          <Card className="backdrop-blur-lg bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950 dark:to-purple-900 border-purple-200 dark:border-purple-800 shadow-xl shadow-purple-500/10 transition-all duration-300 hover:scale-105">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Archived</CardTitle>
              <Archive className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-purple-700 dark:text-purple-300">{stats?.archived_memories || 0}</div>
              <p className="text-xs text-purple-600 dark:text-purple-400 mt-1">
                {stats?.archived_memories ? Math.round((stats.archived_memories / stats.total_memories) * 100) : 0}% of total
              </p>
            </CardContent>
          </Card>

          <Card className="backdrop-blur-lg bg-gradient-to-br from-red-50 to-red-100 dark:from-red-950 dark:to-red-900 border-red-200 dark:border-red-800 shadow-xl shadow-red-500/10 transition-all duration-300 hover:scale-105">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Unresolved Errors</CardTitle>
              <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-red-700 dark:text-red-300">{stats?.unresolved_errors || 0}</div>
              <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                Need attention
              </p>
            </CardContent>
          </Card>

          <Card className="backdrop-blur-lg bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950 dark:to-green-900 border-green-200 dark:border-green-800 shadow-xl shadow-green-500/10 transition-all duration-300 hover:scale-105">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Document Chunks</CardTitle>
              <FileText className="h-4 w-4 text-green-600 dark:text-green-400" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-700 dark:text-green-300">{documentStats?.total_chunks || 0}</div>
              <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                Indexed from documents
              </p>
            </CardContent>
          </Card>
        </div>

        {/* System Health & Storage */}
        <div className="grid gap-4 md:grid-cols-3">
          <HealthIndicators memoryStats={stats} graphStats={graphStats} documentStats={documentStats} />
          <StorageOverview memoryStats={stats} documentStats={documentStats} />
          <RecentErrors memories={allMemories} />
        </div>

        {/* Advanced Brain Features */}
        <div className="grid gap-4">
          <AdvancedBrainMetrics />
        </div>

        {/* Analysis Grid */}
        <div className="grid gap-4 md:grid-cols-2">
          <TypeBreakdown memories={allMemories} />
          <ProjectBreakdown memories={allMemories} />
        </div>

        {/* Visualizations */}
        <div className="space-y-6">
          {/* Activity Timeline */}
          <Card className="shadow-lg border-t-4 border-t-blue-500">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-blue-600" />
                <CardTitle>Memory Activity Timeline</CardTitle>
              </div>
              <CardDescription>Last 30 days of memory creation and access patterns</CardDescription>
            </CardHeader>
            <CardContent>
              {recentMemories && recentMemories.length > 0 ? (
                <Suspense fallback={<ChartLoading />}>
                  <ActivityTimeline memories={recentMemories} />
                </Suspense>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                  No activity data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Charts Row */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="shadow-lg border-t-4 border-t-amber-500">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-amber-600" />
                  <CardTitle>Importance Distribution</CardTitle>
                </div>
                <CardDescription>How memories are rated by importance</CardDescription>
              </CardHeader>
              <CardContent>
                {recentMemories && recentMemories.length > 0 ? (
                  <Suspense fallback={<ChartLoading />}>
                    <ImportanceDistribution memories={recentMemories} />
                  </Suspense>
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                    No data available
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="shadow-lg border-t-4 border-t-purple-500">
              <CardHeader>
                <CardTitle>Memory Types</CardTitle>
                <CardDescription>Distribution by type (interactive)</CardDescription>
              </CardHeader>
              <CardContent>
                {recentMemories && recentMemories.length > 0 ? (
                  <Suspense fallback={<ChartLoading />}>
                    <EnhancedPieChart memories={recentMemories} />
                  </Suspense>
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                    No data available
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="shadow-lg border-t-4 border-t-teal-500">
              <CardHeader>
                <CardTitle>Tag Cloud</CardTitle>
                <CardDescription>Most frequently used tags</CardDescription>
              </CardHeader>
              <CardContent>
                {recentMemories && recentMemories.length > 0 ? (
                  <Suspense fallback={<ChartLoading />}>
                    <TagCloud memories={recentMemories} />
                  </Suspense>
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                    No tags available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Recent Activity */}
          <Card className="shadow-lg border-t-4 border-t-indigo-500">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Recent Activity</CardTitle>
                  <CardDescription>Latest memories created</CardDescription>
                </div>
                <Badge variant="outline">{recentMemories?.length || 0} total</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {recentMemories && recentMemories.length > 0 ? (
                  recentMemories.slice(0, 10).map((memory: Memory) => (
                    <div key={memory.id} className="flex items-start gap-3 border-b border-gray-200 dark:border-gray-700 pb-3 last:border-0 transition-all duration-200 hover:bg-gray-50 dark:hover:bg-gray-800 p-3 rounded-lg">
                      <MemoryTypeBadge type={memory.type} className="mt-1" />
                      <div className="flex-1 space-y-1 min-w-0">
                        <p className="text-sm font-medium line-clamp-2">{memory.content}</p>
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-xs text-muted-foreground">
                            {formatDistanceToNow(new Date(memory.created_at), { addSuffix: true })}
                          </p>
                          {memory.project && (
                            <Badge variant="outline" className="text-xs">
                              {memory.project}
                            </Badge>
                          )}
                          {memory.tags && memory.tags.length > 0 && (
                            <Badge variant="secondary" className="text-xs">
                              {memory.tags[0]}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="h-[200px] flex items-center justify-center text-muted-foreground">
                    No recent memories
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Advanced Analytics Row */}
          <div className="grid gap-4 md:grid-cols-2">
            {/* Access Heatmap */}
            <Card className="shadow-lg border-t-4 border-t-emerald-500">
              <CardHeader>
                <CardTitle>Access Heatmap</CardTitle>
                <CardDescription>Memory access activity over the last 90 days</CardDescription>
              </CardHeader>
              <CardContent>
                {recentMemories && recentMemories.length > 0 ? (
                  <Suspense fallback={<ChartLoading />}>
                    <AccessHeatmap memories={recentMemories} />
                  </Suspense>
                ) : (
                  <div className="h-[200px] flex items-center justify-center text-muted-foreground">
                    No access data available
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Memory Decay Curve */}
            <Card className="shadow-lg border-t-4 border-t-rose-500">
              <CardHeader>
                <CardTitle>Memory Decay Curve</CardTitle>
                <CardDescription>How recency scores decay over time by memory type</CardDescription>
              </CardHeader>
              <CardContent>
                <Suspense fallback={<ChartLoading />}>
                  <DecayCurve />
                </Suspense>
              </CardContent>
            </Card>
          </div>

          {/* System Configuration */}
          <Card className="shadow-lg border-t-4 border-t-slate-500">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Network className="h-5 w-5 text-slate-600" />
                <CardTitle>System Configuration</CardTitle>
              </div>
              <CardDescription>Memory system technical details and capabilities</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950 dark:to-blue-900 rounded-lg">
                  <div className="text-xs text-blue-600 dark:text-blue-400 mb-1">Hybrid Search</div>
                  <div className="flex items-center gap-2">
                    <Badge variant={stats?.hybrid_search_enabled ? "default" : "outline"}>
                      {stats?.hybrid_search_enabled ? "Enabled" : "Disabled"}
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground mt-2">
                    Semantic + Keyword
                  </div>
                </div>

                <div className="p-4 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950 dark:to-purple-900 rounded-lg">
                  <div className="text-xs text-purple-600 dark:text-purple-400 mb-1">Vector Dimensions</div>
                  <div className="text-2xl font-bold text-purple-700 dark:text-purple-300">
                    {stats?.embedding_dim || 0}D
                  </div>
                  <div className="text-xs text-muted-foreground mt-2">
                    Embedding space
                  </div>
                </div>

                <div className="p-4 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950 dark:to-green-900 rounded-lg">
                  <div className="text-xs text-green-600 dark:text-green-400 mb-1">Knowledge Graph</div>
                  <div className="flex items-center gap-2">
                    <Badge variant={graphStats?.enabled ? "default" : "outline"}>
                      {graphStats?.enabled ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground mt-2">
                    {graphStats?.relationships || 0} edges
                  </div>
                </div>

                <div className="p-4 bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-950 dark:to-amber-900 rounded-lg">
                  <div className="text-xs text-amber-600 dark:text-amber-400 mb-1">Document Index</div>
                  <div className="flex items-center gap-2">
                    <Badge variant={documentStats?.status === 'green' ? "default" : "outline"}>
                      {documentStats?.status || 'Unknown'}
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground mt-2">
                    Auto-indexing active
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
