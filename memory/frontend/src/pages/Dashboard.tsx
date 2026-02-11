import { lazy, Suspense, useState } from 'react';
import { useStats, useGraphStats, useMemories } from '../hooks/useMemories';
import { useDocumentStats } from '../hooks/useDocuments';
import { useQualityStats } from '../hooks/useQuality';
import { useLifecycleStats } from '../hooks/useLifecycle';
import { usePatternClusters } from '../hooks/useAnalytics';
import { useBrainMetrics } from '../hooks/useBrain';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Header } from '../components/layout/Header';
import { Database, AlertCircle, Network, TrendingUp, FileText, Brain, Sparkles, Zap, Star, GitBranch, Activity } from 'lucide-react';
import { Badge } from '../components/ui/badge';
import { formatDistanceToNow } from 'date-fns';
import type { Memory } from '../types/memory';
import { MemoryTypeBadge } from '../components/memory/MemoryTypeBadge';
import { ProjectBreakdown } from '../components/dashboard/ProjectBreakdown';
import { HealthIndicators } from '../components/dashboard/HealthIndicators';
import { RecentErrors } from '../components/dashboard/RecentErrors';
import { TypeBreakdown } from '../components/dashboard/TypeBreakdown';
import { QualityBadge } from '../components/QualityBadge';
import { StateDistribution } from '../components/StateBadge';
import { MemoryDetailPanel } from '../components/memory/MemoryDetailPanel';

const ActivityTimeline = lazy(() => import('../components/analytics/ActivityTimeline').then(m => ({ default: m.ActivityTimeline })));
const ImportanceDistribution = lazy(() => import('../components/analytics/ImportanceDistribution').then(m => ({ default: m.ImportanceDistribution })));
const EnhancedPieChart = lazy(() => import('../components/analytics/EnhancedPieChart').then(m => ({ default: m.EnhancedPieChart })));
const TagCloud = lazy(() => import('../components/analytics/TagCloud').then(m => ({ default: m.TagCloud })));

function ChartLoading() {
  return (
    <div className="h-[250px] flex items-center justify-center">
      <div className="h-6 w-6 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" />
    </div>
  );
}

export function Dashboard() {
  const [detailPanelId, setDetailPanelId] = useState<string | null>(null);
  const { data: stats, isLoading: statsLoading } = useStats();
  const { data: graphStats } = useGraphStats();
  const { data: documentStats } = useDocumentStats();
  const { data: allMemoriesData } = useMemories({ limit: 500 });
  const allMemories = allMemoriesData?.items;
  const { data: qualityStats } = useQualityStats();
  const { data: lifecycleStats } = useLifecycleStats();
  const { data: patternClusters } = usePatternClusters(3);
  const { data: brainMetrics } = useBrainMetrics();

  if (statsLoading) {
    return (
      <div>
        <Header title="Dashboard" />
        <div className="p-8 flex items-center justify-center h-64">
          <div className="relative">
            <div className="h-10 w-10 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" />
            <Brain className="h-5 w-5 text-blue-500 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
          </div>
        </div>
      </div>
    );
  }

  const avgQuality = (qualityStats?.avg_quality_score || qualityStats?.average_score || 0) * 100;

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <Header title="Dashboard" />
      <div className="p-4 sm:p-6 max-w-[1600px] mx-auto space-y-5">

        {/* ── Row 1: Compact Header ── */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-2.5 rounded-xl">
              <Brain className="h-7 w-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Claude Brain</h1>
              <p className="text-sm text-white/40">
                {stats?.total_memories || 0} memories &middot; {graphStats?.relationships || 0} connections &middot; {stats?.embedding_dim || 0}D vectors
              </p>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-2">
            {stats?.hybrid_search_enabled && (
              <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-xs">
                <Sparkles className="h-3 w-3 mr-1" />Hybrid Search
              </Badge>
            )}
            {graphStats?.enabled && (
              <Badge className="bg-purple-500/10 text-purple-400 border-purple-500/20 text-xs">
                <Network className="h-3 w-3 mr-1" />Graph
              </Badge>
            )}
          </div>
        </div>

        {/* ── Row 2: Key Metrics ── */}
        <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
          <MetricCard
            icon={<Database className="h-5 w-5 text-blue-400" />}
            label="Memories"
            value={stats?.total_memories || 0}
            sub={`${stats?.active_memories || 0} active`}
            color="blue"
          />
          <MetricCard
            icon={<Star className="h-5 w-5 text-amber-400" />}
            label="Avg Quality"
            value={`${avgQuality.toFixed(0)}%`}
            sub={`${qualityStats?.high_quality_count || 0} excellent`}
            color="amber"
          />
          <MetricCard
            icon={<Network className="h-5 w-5 text-emerald-400" />}
            label="Relationships"
            value={graphStats?.relationships || 0}
            sub={`${graphStats?.memory_nodes || 0} nodes`}
            color="emerald"
          />
          <MetricCard
            icon={<AlertCircle className="h-5 w-5 text-rose-400" />}
            label="Unresolved"
            value={stats?.unresolved_errors || 0}
            sub={stats?.unresolved_errors === 0 ? 'All clear' : 'Needs attention'}
            color="rose"
          />
        </div>

        {/* ── Row 3: Activity Timeline (full width) ── */}
        <Card className="bg-[#111] border-white/[0.06]">
          <CardHeader className="pb-2 pt-4 px-5">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-emerald-400" />
              <CardTitle className="text-sm font-medium text-white/70">Activity Timeline</CardTitle>
              <span className="text-xs text-white/30 ml-auto">Last 30 days</span>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            {allMemories && allMemories.length > 0 ? (
              <Suspense fallback={<ChartLoading />}>
                <ActivityTimeline memories={allMemories} />
              </Suspense>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-white/20 text-sm">No activity data</div>
            )}
          </CardContent>
        </Card>

        {/* ── Row 4: Quality + States + Patterns ── */}
        <div className="grid gap-4 lg:grid-cols-3">
          {/* Quality Distribution */}
          <Card className="bg-[#111] border-white/[0.06]">
            <CardHeader className="pb-2 pt-4 px-5">
              <div className="flex items-center gap-2">
                <Star className="h-4 w-4 text-amber-400" />
                <CardTitle className="text-sm font-medium text-white/70">Quality Distribution</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="px-5 pb-4">
              {qualityStats ? (
                <div className="space-y-2.5">
                  {(() => {
                    const distribution = qualityStats.quality_distribution || qualityStats.distribution || {};
                    const total = qualityStats.total_memories || qualityStats.total_count || 1;
                    const colors: Record<string, string> = {
                      excellent: 'bg-green-500', good: 'bg-blue-500', fair: 'bg-yellow-500',
                      moderate: 'bg-yellow-500', low: 'bg-orange-500', poor: 'bg-red-500', very_poor: 'bg-red-500',
                    };
                    return Object.entries(distribution).map(([tier, count]) => {
                      const pct = (count / total) * 100;
                      return (
                        <div key={tier} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-white/50 capitalize">{tier.replace('_', ' ')}</span>
                            <span className="text-white/30">{count} ({pct.toFixed(0)}%)</span>
                          </div>
                          <div className="w-full bg-white/[0.04] rounded-full h-1.5">
                            <div className={`h-1.5 rounded-full ${colors[tier] || 'bg-gray-500'}`} style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      );
                    });
                  })()}
                </div>
              ) : (
                <div className="h-40 flex items-center justify-center text-white/20 text-sm">Loading...</div>
              )}
            </CardContent>
          </Card>

          {/* Memory States */}
          <Card className="bg-[#111] border-white/[0.06]">
            <CardHeader className="pb-2 pt-4 px-5">
              <div className="flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-purple-400" />
                <CardTitle className="text-sm font-medium text-white/70">Memory States</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="px-5 pb-4">
              {lifecycleStats ? (
                <StateDistribution
                  distribution={lifecycleStats.state_distribution || lifecycleStats.distribution || {}}
                  total={lifecycleStats.total_memories || lifecycleStats.total || 0}
                  className="text-white/90"
                />
              ) : (
                <div className="h-40 flex items-center justify-center text-white/20 text-sm">Loading...</div>
              )}
            </CardContent>
          </Card>

          {/* Pattern Clusters */}
          <Card className="bg-[#111] border-white/[0.06]">
            <CardHeader className="pb-2 pt-4 px-5">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-emerald-400" />
                <CardTitle className="text-sm font-medium text-white/70">Pattern Clusters</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="px-5 pb-4">
              {patternClusters && patternClusters.length > 0 ? (
                <div className="space-y-2.5">
                  {patternClusters.slice(0, 4).map((cluster) => (
                    <div key={cluster.cluster_id} className="p-2.5 bg-white/[0.03] rounded-lg hover:bg-white/[0.06] transition-colors">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-white/80 truncate">{cluster.cluster_name}</span>
                        <QualityBadge score={cluster.avg_quality_score} size="sm" showScore={false} />
                      </div>
                      <p className="text-[11px] text-white/40 line-clamp-1 mb-1.5">{cluster.summary}</p>
                      <div className="flex items-center gap-1.5">
                        <Badge variant="outline" className="text-[10px] border-emerald-500/20 text-emerald-400 px-1.5 py-0">
                          {cluster.member_count} mem
                        </Badge>
                        {cluster.tags?.slice(0, 2).map((tag) => (
                          <Badge key={tag} variant="outline" className="text-[10px] border-white/10 text-white/40 px-1.5 py-0">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-40 flex flex-col items-center justify-center text-white/20 text-sm">
                  <Sparkles className="h-6 w-6 mb-2 opacity-20" />
                  <p>No patterns yet</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* ── Row 5: Charts ── */}
        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="bg-[#111] border-white/[0.06]">
            <CardHeader className="pb-2 pt-4 px-5">
              <CardTitle className="text-sm font-medium text-white/70">Memory Types</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-4">
              {allMemories?.length ? (
                <Suspense fallback={<ChartLoading />}><EnhancedPieChart memories={allMemories} /></Suspense>
              ) : <div className="h-[250px] flex items-center justify-center text-white/20 text-sm">No data</div>}
            </CardContent>
          </Card>
          <Card className="bg-[#111] border-white/[0.06]">
            <CardHeader className="pb-2 pt-4 px-5">
              <CardTitle className="text-sm font-medium text-white/70">Importance Distribution</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-4">
              {allMemories?.length ? (
                <Suspense fallback={<ChartLoading />}><ImportanceDistribution memories={allMemories} /></Suspense>
              ) : <div className="h-[250px] flex items-center justify-center text-white/20 text-sm">No data</div>}
            </CardContent>
          </Card>
          <Card className="bg-[#111] border-white/[0.06]">
            <CardHeader className="pb-2 pt-4 px-5">
              <CardTitle className="text-sm font-medium text-white/70">Tag Cloud</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-4">
              {allMemories?.length ? (
                <Suspense fallback={<ChartLoading />}><TagCloud memories={allMemories} /></Suspense>
              ) : <div className="h-[250px] flex items-center justify-center text-white/20 text-sm">No tags</div>}
            </CardContent>
          </Card>
        </div>

        {/* ── Row 6: Breakdowns ── */}
        <div className="grid gap-4 lg:grid-cols-2">
          <TypeBreakdown memories={allMemories} />
          <ProjectBreakdown memories={allMemories} />
        </div>

        {/* ── Row 7: Health + Errors + Brain ── */}
        <div className="grid gap-4 lg:grid-cols-3">
          <HealthIndicators memoryStats={stats} graphStats={graphStats} documentStats={documentStats} />
          <RecentErrors memories={allMemories} />

          {/* Brain Metrics */}
          <Card className="bg-[#111] border-white/[0.06]">
            <CardHeader className="pb-2 pt-4 px-5">
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-purple-400" />
                <CardTitle className="text-sm font-medium text-white/70">Brain Intelligence</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="px-5 pb-4">
              {brainMetrics ? (
                <div className="space-y-5">
                  {/* Performance Scores */}
                  <div className="space-y-3">
                    <p className="text-xs text-white/40 uppercase tracking-wider">Performance Scores</p>
                    <div className="grid grid-cols-3 gap-3">
                      <BrainStat label="Importance" value={Math.round(brainMetrics.avg_importance * 100)} unit="%" />
                      <BrainStat label="Access Rate" value={Math.round(brainMetrics.access_rate * 100)} unit="%" />
                      <BrainStat label="Emotional" value={Math.round(brainMetrics.emotional_coverage * 100)} unit="%" />
                    </div>
                  </div>

                  {/* Utility Distribution */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <p className="text-xs text-white/40 uppercase tracking-wider">Utility Distribution</p>
                      <span className="text-xs text-white/30">{brainMetrics.total_memories} memories</span>
                    </div>
                    <div className="flex h-4 rounded-lg overflow-hidden bg-white/[0.04]">
                      {brainMetrics.utility_high > 0 && (
                        <div className="bg-emerald-500 transition-all" style={{ width: `${(brainMetrics.utility_high / Math.max(brainMetrics.total_memories, 1)) * 100}%` }} />
                      )}
                      {brainMetrics.utility_medium > 0 && (
                        <div className="bg-amber-500 transition-all" style={{ width: `${(brainMetrics.utility_medium / Math.max(brainMetrics.total_memories, 1)) * 100}%` }} />
                      )}
                      {brainMetrics.utility_low > 0 && (
                        <div className="bg-rose-500 transition-all" style={{ width: `${(brainMetrics.utility_low / Math.max(brainMetrics.total_memories, 1)) * 100}%` }} />
                      )}
                    </div>
                    <div className="flex gap-5 text-xs">
                      <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /><span className="text-white/60">{brainMetrics.utility_high} high</span></span>
                      <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-amber-500" /><span className="text-white/60">{brainMetrics.utility_medium} medium</span></span>
                      <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-rose-500" /><span className="text-white/60">{brainMetrics.utility_low} low</span></span>
                    </div>
                  </div>

                  {/* Memory Types */}
                  {Object.keys(brainMetrics.type_distribution).length > 0 && (
                    <div className="space-y-3">
                      <p className="text-xs text-white/40 uppercase tracking-wider">Memory Types</p>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(brainMetrics.type_distribution)
                          .sort(([, a], [, b]) => b - a)
                          .map(([type, count]) => (
                            <span key={type} className="text-xs px-3 py-1.5 rounded-lg bg-white/[0.05] text-white/60">
                              {type} <span className="text-white/30 font-semibold">{count}</span>
                            </span>
                          ))}
                      </div>
                    </div>
                  )}

                  {/* Footer */}
                  <div className="flex items-center gap-4 pt-3 border-t border-white/[0.06] text-xs text-white/35">
                    <span>{brainMetrics.total_relationships.toLocaleString()} relationships</span>
                    <span>&middot;</span>
                    <span>{brainMetrics.conflicts_detected} conflicts detected</span>
                  </div>
                </div>
              ) : (
                <div className="h-40 flex items-center justify-center text-white/20 text-sm">Loading...</div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* ── Row 8: Recent Activity ── */}
        <Card className="bg-[#111] border-white/[0.06]">
          <CardHeader className="pb-0 pt-4 px-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-blue-400" />
                <CardTitle className="text-sm font-medium text-white/70">Recent Activity</CardTitle>
              </div>
              <span className="text-xs text-white/30">{allMemories?.length || 0} total</span>
            </div>
          </CardHeader>
          <CardContent className="px-0 pb-0">
            <div className="divide-y divide-white/[0.04]">
              {allMemories && allMemories.length > 0 ? (
                allMemories.slice(0, 6).map((memory: Memory) => (
                  <div
                    key={memory.id}
                    className="px-5 py-3 hover:bg-white/[0.03] transition-colors cursor-pointer"
                    onClick={() => setDetailPanelId(memory.id)}
                  >
                    <div className="flex items-start gap-3">
                      <MemoryTypeBadge type={memory.type} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-white/80 line-clamp-1">{memory.content}</p>
                        <div className="flex items-center gap-2 mt-1 text-xs text-white/30">
                          <span>{formatDistanceToNow(new Date(memory.created_at), { addSuffix: true })}</span>
                          {memory.project && (
                            <>
                              <span className="text-white/10">&middot;</span>
                              <span className="text-blue-400/70">{memory.project}</span>
                            </>
                          )}
                          {memory.tags?.slice(0, 2).map(tag => (
                            <Badge key={tag} variant="outline" className="text-[10px] border-white/[0.06] text-white/30 px-1.5 py-0">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="h-32 flex items-center justify-center text-white/20 text-sm">No recent memories</div>
              )}
            </div>
          </CardContent>
        </Card>

      </div>

      {detailPanelId && (
        <MemoryDetailPanel
          memoryId={detailPanelId}
          onClose={() => setDetailPanelId(null)}
          onNavigate={(id) => setDetailPanelId(id)}
        />
      )}
    </div>
  );
}

/* ── Compact metric card ── */
function MetricCard({ icon, label, value, sub, color }: {
  icon: React.ReactNode; label: string; value: number | string; sub: string; color: string;
}) {
  const ring = `ring-${color}-500/20`;
  const bg = `bg-${color}-500/10`;
  return (
    <Card className="bg-[#111] border-white/[0.06] hover:border-white/[0.12] transition-colors">
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${bg} ring-1 ${ring}`}>{icon}</div>
          <div className="min-w-0">
            <p className="text-xs text-white/40">{label}</p>
            <p className="text-2xl font-semibold text-white leading-tight">{typeof value === 'number' ? value.toLocaleString() : value}</p>
            <p className="text-[11px] text-white/30 truncate">{sub}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/* ── Brain metric stat ── */
function BrainStat({ label, value, unit, sub }: { label: string; value: number; unit?: string; sub?: string }) {
  const color = value >= 70 ? 'text-emerald-400' : value >= 40 ? 'text-amber-400' : 'text-rose-400';
  return (
    <div className="bg-white/[0.03] rounded-lg p-4">
      <p className="text-xs text-white/40 mb-2">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>
        {value}{unit}
      </p>
      {sub && <p className="text-[11px] text-white/25 mt-1">{sub}</p>}
    </div>
  );
}
