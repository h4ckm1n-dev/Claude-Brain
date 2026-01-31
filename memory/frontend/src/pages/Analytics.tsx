import { useMemo } from 'react';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { useStats, useMemories } from '../hooks/useMemories';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend } from 'recharts';
import type { Memory } from '../types/memory';
import { MemoryType } from '../types/memory';
import { TrendingUp, GitBranch, Zap, Target } from 'lucide-react';

export function Analytics() {
  const { data: stats } = useStats();
  const { data: memories } = useMemories({ limit: 500 });

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
    <div>
      <Header title="Analytics" />
      <div className="p-6 space-y-6">
        {/* Header Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950 dark:to-blue-900 border-blue-200 shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Insights</CardTitle>
              <Target className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-700">{memories?.length || 0}</div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950 dark:to-green-900 border-green-200 shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Importance</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-700">
                {memories ? ((memories.reduce((sum: number, m: Memory) => sum + m.importance_score, 0) / memories.length) * 100).toFixed(0) : 0}%
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950 dark:to-purple-900 border-purple-200 shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Relationships</CardTitle>
              <GitBranch className="h-4 w-4 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-purple-700">
                {memories?.reduce((sum: number, m: Memory) => sum + (m.relations?.length || 0), 0) || 0}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-950 dark:to-amber-900 border-amber-200 shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Resolution Rate</CardTitle>
              <Zap className="h-4 w-4 text-amber-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-amber-700">
                {(() => {
                  const errors = memories?.filter((m: Memory) => m.type === MemoryType.ERROR) || [];
                  const resolved = errors.filter((m: Memory) => m.resolved).length;
                  return errors.length > 0 ? Math.round((resolved / errors.length) * 100) : 0;
                })()}%
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Project Breakdown */}
        <Card className="shadow-xl">
          <CardHeader>
            <CardTitle>Project Breakdown</CardTitle>
            <CardDescription>Memory distribution across projects</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={projectData}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-45} textAnchor="end" height={100} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
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
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="shadow-xl">
            <CardHeader>
              <CardTitle>Memory Tier Flow</CardTitle>
              <CardDescription>Distribution across memory tiers</CardDescription>
            </CardHeader>
            <CardContent>
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
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="shadow-xl">
            <CardHeader>
              <CardTitle>Resolution Funnel</CardTitle>
              <CardDescription>Error resolution and decision lifecycle</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={resolutionData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                  <XAxis type="number" tick={{ fontSize: 12 }} />
                  <YAxis type="category" dataKey="stage" tick={{ fontSize: 11 }} width={150} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(255, 255, 255, 0.95)',
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
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
        <Card className="shadow-xl">
          <CardHeader>
            <CardTitle>Most Used Tags</CardTitle>
            <CardDescription>Top 15 tags by frequency</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={tagFrequency} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="tag" tick={{ fontSize: 11 }} width={120} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
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

        {/* Type Correlation Heatmap */}
        {correlationData.length > 0 && (
          <Card className="shadow-xl">
            <CardHeader>
              <CardTitle>Type Correlation Matrix</CardTitle>
              <CardDescription>Which memory types are connected to each other</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-6 gap-1 p-4">
                {Object.values(MemoryType).map((type1, i) => (
                  <div key={i} className="col-span-6 grid grid-cols-6 gap-1">
                    {i === 0 && (
                      <>
                        <div className="text-xs font-medium"></div>
                        {Object.values(MemoryType).map((type, j) => (
                          <div key={j} className="text-xs font-medium text-center truncate">
                            {type}
                          </div>
                        ))}
                      </>
                    )}
                    <div className="text-xs font-medium truncate">{type1}</div>
                    {Object.values(MemoryType).map((type2, j) => {
                      const correlation = correlationData.find(
                        c => c.from === type1 && c.to === type2
                      );
                      const value = correlation?.value || 0;
                      const maxValue = Math.max(...correlationData.map(c => c.value));
                      const intensity = maxValue > 0 ? value / maxValue : 0;
                      const bgColor = value === 0 ? '#f3f4f6' : `rgba(59, 130, 246, ${0.2 + intensity * 0.8})`;

                      return (
                        <div
                          key={j}
                          className="aspect-square rounded flex items-center justify-center text-xs font-medium transition-all duration-200 hover:scale-110 cursor-pointer"
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
