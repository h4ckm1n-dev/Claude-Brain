import { useMemo } from 'react';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { useStats, useMemories, useGraphStats } from '../hooks/useMemories';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend, Sankey, Rectangle } from 'recharts';
import type { Memory } from '../types/memory';
import { MemoryType } from '../types/memory';
import { TrendingUp, GitBranch, Zap, Target, BarChart3, Award, Activity, Brain, Calendar } from 'lucide-react';
import { useQualityStats } from '../hooks/useQuality';
import { useLifecycleStats } from '../hooks/useLifecycle';
import { usePatternClusters } from '../hooks/useAnalytics';
import { useAuditStats } from '../hooks/useAudit';
import { QualityBadge } from '../components/QualityBadge';
import { AuditTimeline } from '../components/AuditTimeline';

export function Analytics() {
  const { data: stats } = useStats();
  const { data: memories } = useMemories({ limit: 500 });
  const { data: graphStats } = useGraphStats(); // Fetch graph stats for relationship count

  // Phase 3-4: Intelligence analytics
  const { data: qualityStats } = useQualityStats();
  const { data: lifecycleStats } = useLifecycleStats();
  const { data: patternClusters } = usePatternClusters(3);
  const { data: auditStats } = useAuditStats();

  // Project breakdown data
  const projectData = useMemo(() => {
    if (!memories) return [];

    const projectMap = new Map<string, { count: number; importance: number }>();

    memories.forEach((memory: Memory) => {
      const project = memory.project || 'No Project';
      const current = projectMap.get(project) || { count: 0, importance: 0 };
      projectMap.set(project, {
        count: current.count + 1,
        importance: current.importance + memory.importance_score,
      });
    });

    return Array.from(projectMap.entries())
      .map(([name, data]) => ({
        name,
        count: data.count,
        avgImportance: data.count > 0 ? data.importance / data.count : 0,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);
  }, [memories]);

  // Memory tier flow data
  const tierData = useMemo(() => {
    if (!stats?.by_tier) return [];

    return Object.entries(stats.by_tier).map(([tier, count]) => ({
      tier: tier.charAt(0).toUpperCase() + tier.slice(1),
      count,
    }));
  }, [stats]);

  // Type correlation matrix
  const correlationData = useMemo(() => {
    if (!memories) return [];

    const types = Object.values(MemoryType);
    const cooccurrence = new Map<string, number>();

    memories.forEach((memory: Memory) => {
      const relatedTypes = new Set<MemoryType>();
      memory.relations?.forEach(rel => {
        const relatedMemory = memories.find((m: Memory) => m.id === rel.target_id);
        if (relatedMemory) {
          relatedTypes.add(relatedMemory.type);
        }
      });

      relatedTypes.forEach(relType => {
        const key = `${memory.type}-${relType}`;
        cooccurrence.set(key, (cooccurrence.get(key) || 0) + 1);
      });
    });

    const matrix: any[] = [];
    types.forEach(type1 => {
      types.forEach(type2 => {
        const key = `${type1}-${type2}`;
        const value = cooccurrence.get(key) || 0;
        if (value > 0) {
          matrix.push({
            from: type1,
            to: type2,
            value,
          });
        }
      });
    });

    return matrix;
  }, [memories]);

  // Resolution rate data
  const resolutionData = useMemo(() => {
    if (!memories) return [];

    const errorMemories = memories.filter((m: Memory) => m.type === MemoryType.ERROR);
    const resolved = errorMemories.filter((m: Memory) => m.resolved).length;
    const unresolved = errorMemories.length - resolved;

    const decisionMemories = memories.filter((m: Memory) => m.type === MemoryType.DECISION);
    const superseded = decisionMemories.filter((m: Memory) =>
      m.relations?.some(r => r.relation_type === 'supersedes')
    ).length;
    const active = decisionMemories.length - superseded;

    return [
      { stage: 'Errors Created', value: errorMemories.length, color: '#ef4444' },
      { stage: 'Errors Resolved', value: resolved, color: '#22c55e' },
      { stage: 'Decisions Made', value: decisionMemories.length, color: '#3b82f6' },
      { stage: 'Decisions Superseded', value: superseded, color: '#6b7280' },
    ];
  }, [memories]);

  // Tag usage frequency
  const tagFrequency = useMemo(() => {
    if (!memories) return [];

    const tagMap = new Map<string, number>();
    memories.forEach((memory: Memory) => {
      memory.tags.forEach(tag => {
        tagMap.set(tag, (tagMap.get(tag) || 0) + 1);
      });
    });

    return Array.from(tagMap.entries())
      .map(([tag, count]) => ({ tag, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 15);
  }, [memories]);

  const getProjectColor = (index: number) => {
    const colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#a855f7', '#ec4899', '#06b6d4', '#8b5cf6'];
    return colors[index % colors.length];
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]">
      <Header title="Analytics" />
      <div className="p-6 sm:p-8 max-w-[1800px] mx-auto space-y-6">
        {/* Hero Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-500/10 via-blue-500/10 to-purple-500/10 p-6 border border-white/5">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 via-transparent to-purple-500/5" />
          <div className="relative flex items-center gap-4">
            <div className="p-3 bg-emerald-500/10 rounded-xl ring-1 ring-emerald-500/20">
              <BarChart3 className="h-8 w-8 text-emerald-400" />
            </div>
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-white">Analytics Dashboard</h1>
              <p className="text-white/60 mt-1">
                Deep insights into your memory patterns and usage
              </p>
            </div>
          </div>
        </div>

        {/* Header Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          <div className="group relative">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-blue-600 rounded-2xl opacity-20 group-hover:opacity-40 transition blur" />
            <Card className="relative bg-[#0f0f0f] border-white/10 hover:border-blue-500/50 transition-all duration-300 overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl" />
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative">
                <CardTitle className="text-sm font-medium text-white/70">Total Insights</CardTitle>
                <Target className="h-4 w-4 text-blue-400" />
              </CardHeader>
              <CardContent className="relative">
                <div className="text-3xl font-bold text-white">{memories?.length || 0}</div>
              </CardContent>
            </Card>
          </div>

          <div className="group relative">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500 to-emerald-600 rounded-2xl opacity-20 group-hover:opacity-40 transition blur" />
            <Card className="relative bg-[#0f0f0f] border-white/10 hover:border-emerald-500/50 transition-all duration-300 overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/10 rounded-full blur-3xl" />
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative">
                <CardTitle className="text-sm font-medium text-white/70">Avg Importance</CardTitle>
                <TrendingUp className="h-4 w-4 text-emerald-400" />
              </CardHeader>
              <CardContent className="relative">
                <div className="text-3xl font-bold text-white">
                  {memories ? ((memories.reduce((sum: number, m: Memory) => sum + m.importance_score, 0) / memories.length) * 100).toFixed(0) : 0}%
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="group relative">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-500 to-purple-600 rounded-2xl opacity-20 group-hover:opacity-40 transition blur" />
            <Card className="relative bg-[#0f0f0f] border-white/10 hover:border-purple-500/50 transition-all duration-300 overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full blur-3xl" />
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative">
                <CardTitle className="text-sm font-medium text-white/70">Relationships</CardTitle>
                <GitBranch className="h-4 w-4 text-purple-400" />
              </CardHeader>
              <CardContent className="relative">
                <div className="text-3xl font-bold text-white">
                  {graphStats?.relationships || 0}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="group relative">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-amber-500 to-amber-600 rounded-2xl opacity-20 group-hover:opacity-40 transition blur" />
            <Card className="relative bg-[#0f0f0f] border-white/10 hover:border-amber-500/50 transition-all duration-300 overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/10 rounded-full blur-3xl" />
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative">
                <CardTitle className="text-sm font-medium text-white/70">Resolution Rate</CardTitle>
                <Zap className="h-4 w-4 text-amber-400" />
              </CardHeader>
              <CardContent className="relative">
                <div className="text-3xl font-bold text-white">
                  {(() => {
                    const errors = memories?.filter((m: Memory) => m.type === MemoryType.ERROR) || [];
                    const resolved = errors.filter((m: Memory) => m.resolved).length;
                    return errors.length > 0 ? Math.round((resolved / errors.length) * 100) : 0;
                  })()}%
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Project Breakdown */}
        <Card className="bg-[#0f0f0f] border-white/10 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-purple-500/5 pointer-events-none" />
          <CardHeader className="border-b border-white/5 relative">
            <CardTitle className="text-white">Project Breakdown</CardTitle>
            <CardDescription className="text-white/50">Memory distribution across projects</CardDescription>
          </CardHeader>
          <CardContent className="pt-6 relative">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={projectData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }}
                  angle={-45}
                  textAnchor="end"
                  height={100}
                  stroke="rgba(255,255,255,0.1)"
                />
                <YAxis
                  tick={{ fontSize: 12, fill: 'rgba(255,255,255,0.5)' }}
                  stroke="rgba(255,255,255,0.1)"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(15, 15, 15, 0.95)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    color: 'white',
                  }}
                />
                <Bar dataKey="count" radius={[8, 8, 0, 0]} animationDuration={800}>
                  {projectData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={getProjectColor(index)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Memory Tier Distribution & Resolution Funnel */}
        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="bg-[#0f0f0f] border-white/10 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 via-transparent to-blue-500/5 pointer-events-none" />
            <CardHeader className="border-b border-white/5 relative">
              <CardTitle className="text-white">Memory Tier Flow</CardTitle>
              <CardDescription className="text-white/50">Distribution across memory tiers</CardDescription>
            </CardHeader>
            <CardContent className="pt-6 relative">
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={tierData}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    dataKey="count"
                    label={(entry: any) => `${entry.tier}: ${entry.count}`}
                    animationBegin={0}
                    animationDuration={800}
                  >
                    <Cell fill="#3b82f6" />
                    <Cell fill="#22c55e" />
                    <Cell fill="#f59e0b" />
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(15, 15, 15, 0.95)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '8px',
                      color: 'white',
                    }}
                  />
                  <Legend wrapperStyle={{ color: 'rgba(255,255,255,0.7)' }} />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="bg-[#0f0f0f] border-white/10 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 via-transparent to-rose-500/5 pointer-events-none" />
            <CardHeader className="border-b border-white/5 relative">
              <CardTitle className="text-white">Resolution Funnel</CardTitle>
              <CardDescription className="text-white/50">Error resolution and decision lifecycle</CardDescription>
            </CardHeader>
            <CardContent className="pt-6 relative">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={resolutionData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis
                    type="number"
                    tick={{ fontSize: 12, fill: 'rgba(255,255,255,0.5)' }}
                    stroke="rgba(255,255,255,0.1)"
                  />
                  <YAxis
                    type="category"
                    dataKey="stage"
                    tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }}
                    width={150}
                    stroke="rgba(255,255,255,0.1)"
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(15, 15, 15, 0.95)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '8px',
                      color: 'white',
                    }}
                  />
                  <Bar dataKey="value" radius={[0, 8, 8, 0]} animationDuration={800}>
                    {resolutionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Tag Frequency */}
        <Card className="bg-[#0f0f0f] border-white/10 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-amber-500/5 via-transparent to-purple-500/5 pointer-events-none" />
          <CardHeader className="border-b border-white/5 relative">
            <CardTitle className="text-white">Most Used Tags</CardTitle>
            <CardDescription className="text-white/50">Top 15 tags by frequency</CardDescription>
          </CardHeader>
          <CardContent className="pt-6 relative">
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={tagFrequency} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis
                  type="number"
                  tick={{ fontSize: 12, fill: 'rgba(255,255,255,0.5)' }}
                  stroke="rgba(255,255,255,0.1)"
                />
                <YAxis
                  type="category"
                  dataKey="tag"
                  tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }}
                  width={120}
                  stroke="rgba(255,255,255,0.1)"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(15, 15, 15, 0.95)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    color: 'white',
                  }}
                />
                <Bar dataKey="count" radius={[0, 8, 8, 0]} animationDuration={800}>
                  {tagFrequency.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={getProjectColor(index)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Phase 3-4: Quality Distribution */}
        {qualityStats && (
          <Card className="bg-[#0f0f0f] border-white/10 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 via-transparent to-blue-500/5 pointer-events-none" />
            <CardHeader className="border-b border-white/5 relative">
              <div className="flex items-center gap-2">
                <Award className="h-5 w-5 text-emerald-400" />
                <CardTitle className="text-white">Quality Distribution</CardTitle>
              </div>
              <CardDescription className="text-white/50">
                Phase 3-4 memory quality tracking across 5 tiers
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6 relative">
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-gradient-to-r from-emerald-500/10 to-green-500/10 border border-emerald-500/20">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-white/90">Average Quality Score</span>
                    <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-500/30">
                      {qualityStats.avg_quality_score.toFixed(1)}%
                    </Badge>
                  </div>
                  <div className="w-full bg-[#0a0a0a] rounded-full h-3 border border-white/5">
                    <div
                      className="bg-gradient-to-r from-emerald-500 to-green-500 h-3 rounded-full transition-all duration-500"
                      style={{ width: `${qualityStats.avg_quality_score}%` }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                  <div className="p-3 rounded-lg bg-gradient-to-br from-green-500/10 to-emerald-500/10 border border-green-500/20 text-center">
                    <div className="text-2xl font-bold text-white mb-1">
                      {qualityStats.quality_distribution.excellent}
                    </div>
                    <div className="text-xs text-green-300 mb-1">Excellent</div>
                    <div className="text-xs text-white/50">80-100%</div>
                  </div>
                  <div className="p-3 rounded-lg bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-blue-500/20 text-center">
                    <div className="text-2xl font-bold text-white mb-1">
                      {qualityStats.quality_distribution.good}
                    </div>
                    <div className="text-xs text-blue-300 mb-1">Good</div>
                    <div className="text-xs text-white/50">60-80%</div>
                  </div>
                  <div className="p-3 rounded-lg bg-gradient-to-br from-yellow-500/10 to-amber-500/10 border border-yellow-500/20 text-center">
                    <div className="text-2xl font-bold text-white mb-1">
                      {qualityStats.quality_distribution.fair}
                    </div>
                    <div className="text-xs text-yellow-300 mb-1">Fair</div>
                    <div className="text-xs text-white/50">40-60%</div>
                  </div>
                  <div className="p-3 rounded-lg bg-gradient-to-br from-orange-500/10 to-red-500/10 border border-orange-500/20 text-center">
                    <div className="text-2xl font-bold text-white mb-1">
                      {qualityStats.quality_distribution.poor}
                    </div>
                    <div className="text-xs text-orange-300 mb-1">Poor</div>
                    <div className="text-xs text-white/50">20-40%</div>
                  </div>
                  <div className="p-3 rounded-lg bg-gradient-to-br from-red-500/10 to-rose-500/10 border border-red-500/20 text-center">
                    <div className="text-2xl font-bold text-white mb-1">
                      {qualityStats.quality_distribution.very_poor}
                    </div>
                    <div className="text-xs text-red-300 mb-1">Very Poor</div>
                    <div className="text-xs text-white/50">&lt;20%</div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-3 border-t border-white/10">
                  <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                    <div className="text-xs text-white/70 mb-1">High Quality</div>
                    <div className="text-xl font-bold text-emerald-300">
                      {qualityStats.high_quality_count}
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                    <div className="text-xs text-white/70 mb-1">Needs Review</div>
                    <div className="text-xl font-bold text-amber-300">
                      {qualityStats.needs_improvement_count}
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Phase 3-4: State Transition Flow */}
        {lifecycleStats && (
          <Card className="bg-[#0f0f0f] border-white/10 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 via-transparent to-pink-500/5 pointer-events-none" />
            <CardHeader className="border-b border-white/5 relative">
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-purple-400" />
                <CardTitle className="text-white">State Transition Flow</CardTitle>
              </div>
              <CardDescription className="text-white/50">
                Phase 3-4 lifecycle state machine transitions
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6 relative">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
                {Object.entries(lifecycleStats.state_distribution || lifecycleStats.distribution || {}).map(([state, count]) => (
                  <div
                    key={state}
                    className="p-4 rounded-lg bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-500/20 text-center"
                  >
                    <div className="text-2xl font-bold text-white mb-1">{count}</div>
                    <div className="text-xs text-purple-300 capitalize">{state}</div>
                  </div>
                ))}
              </div>

              {lifecycleStats.transition_flow && lifecycleStats.transition_flow.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-white/90 mb-3">Recent Transitions</h4>
                  {lifecycleStats.transition_flow.slice(0, 10).map((flow, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5 hover:border-purple-500/30 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <Badge className="bg-purple-500/20 text-purple-300 border-purple-500/30 capitalize">
                          {flow.from_state}
                        </Badge>
                        <span className="text-white/50">→</span>
                        <Badge className="bg-pink-500/20 text-pink-300 border-pink-500/30 capitalize">
                          {flow.to_state}
                        </Badge>
                      </div>
                      <Badge className="bg-white/10 text-white/90">{flow.count}x</Badge>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-6 p-4 rounded-lg bg-purple-500/10 border border-purple-500/20">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-white/70 mb-1">Avg Time in Episodic</div>
                    <div className="text-lg font-bold text-white">
                      {(lifecycleStats.avg_time_in_episodic_hours || 0).toFixed(1)}h
                    </div>
                  </div>
                  <div>
                    <div className="text-white/70 mb-1">Avg Time to Semantic</div>
                    <div className="text-lg font-bold text-white">
                      {(lifecycleStats.avg_time_to_semantic_hours || 0).toFixed(1)}h
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Phase 3-4: Pattern Clusters */}
        {patternClusters && patternClusters.length > 0 && (
          <Card className="bg-[#0f0f0f] border-white/10 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-amber-500/5 via-transparent to-orange-500/5 pointer-events-none" />
            <CardHeader className="border-b border-white/5 relative">
              <div className="flex items-center gap-2">
                <Brain className="h-5 w-5 text-amber-400" />
                <CardTitle className="text-white">Detected Pattern Clusters</CardTitle>
              </div>
              <CardDescription className="text-white/50">
                Phase 3-4 automatic pattern detection and clustering
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6 relative">
              <div className="space-y-4">
                {patternClusters.map((cluster, index) => (
                  <div
                    key={index}
                    className="p-5 rounded-xl bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-amber-500/20 hover:border-amber-500/40 transition-all"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge className="bg-amber-500/20 text-amber-300 border-amber-500/30">
                            Cluster {index + 1}
                          </Badge>
                          <QualityBadge
                            score={cluster.avg_quality_score * 100}
                            size="sm"
                            showScore={true}
                          />
                          <span className="text-xs text-white/60">
                            {cluster.member_count} members
                          </span>
                        </div>
                        <h4 className="font-semibold text-white mb-1">{cluster.cluster_name}</h4>
                        <p className="text-sm text-white/70">{cluster.summary}</p>
                      </div>
                    </div>
                    {cluster.tags.length > 0 && (
                      <div className="flex flex-wrap gap-2 pt-3 border-t border-white/10">
                        {cluster.tags.map((tag, i) => (
                          <Badge
                            key={i}
                            className="text-xs bg-[#0a0a0a] text-white/70 border border-white/10"
                          >
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Phase 3-4: Recent Audit Activity */}
        <Card className="bg-[#0f0f0f] border-white/10 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-cyan-500/5 pointer-events-none" />
          <CardHeader className="border-b border-white/5 relative">
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-blue-400" />
              <CardTitle className="text-white">Recent Audit Activity</CardTitle>
            </div>
            <CardDescription className="text-white/50">
              Phase 3-4 audit trail and system changes
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6 relative">
            {auditStats && (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
                <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-center">
                  <div className="text-2xl font-bold text-white mb-1">
                    {auditStats.total_entries}
                  </div>
                  <div className="text-xs text-blue-300">Total Entries</div>
                </div>
                <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-center">
                  <div className="text-2xl font-bold text-white mb-1">
                    {Object.values(auditStats.by_action).reduce((a, b) => a + b, 0)}
                  </div>
                  <div className="text-xs text-emerald-300">Total Actions</div>
                </div>
                <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20 text-center">
                  <div className="text-2xl font-bold text-white mb-1">
                    {Object.keys(auditStats.by_actor).length}
                  </div>
                  <div className="text-xs text-purple-300">Unique Actors</div>
                </div>
              </div>
            )}
            <AuditTimeline limit={15} />
          </CardContent>
        </Card>

        {/* Type Correlation Heatmap */}
        {correlationData.length > 0 && (
          <Card className="bg-[#0f0f0f] border-white/10 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-rose-500/5 via-transparent to-blue-500/5 pointer-events-none" />
            <CardHeader className="border-b border-white/5 relative">
              <CardTitle className="text-white">Type Correlation Matrix</CardTitle>
              <CardDescription className="text-white/50">Which memory types are connected to each other</CardDescription>
            </CardHeader>
            <CardContent className="pt-6 relative">
              <div className="grid grid-cols-6 gap-1 p-4">
                {Object.values(MemoryType).map((type1, i) => (
                  <div key={i} className="col-span-6 grid grid-cols-6 gap-1">
                    {i === 0 && (
                      <>
                        <div className="text-xs font-medium text-white/70"></div>
                        {Object.values(MemoryType).map((type, j) => (
                          <div key={j} className="text-xs font-medium text-center truncate text-white/70">
                            {type}
                          </div>
                        ))}
                      </>
                    )}
                    <div className="text-xs font-medium truncate text-white/70">{type1}</div>
                    {Object.values(MemoryType).map((type2, j) => {
                      const correlation = correlationData.find(
                        c => c.from === type1 && c.to === type2
                      );
                      const value = correlation?.value || 0;
                      const maxValue = Math.max(...correlationData.map(c => c.value));
                      const intensity = maxValue > 0 ? value / maxValue : 0;
                      const bgColor = value === 0 ? 'rgba(255,255,255,0.05)' : `rgba(59, 130, 246, ${0.2 + intensity * 0.8})`;

                      return (
                        <div
                          key={j}
                          className="aspect-square rounded flex items-center justify-center text-xs font-medium transition-all duration-200 hover:scale-110 cursor-pointer text-white"
                          style={{ backgroundColor: bgColor }}
                          title={`${type1} → ${type2}: ${value} connections`}
                        >
                          {value > 0 ? value : ''}
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
