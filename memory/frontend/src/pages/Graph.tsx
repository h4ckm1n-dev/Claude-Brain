import { useState, useMemo } from 'react';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { useQuery } from '@tanstack/react-query';
import { getTimeline, getMemories } from '../api/memories';
import { AlertCircle, Network, Sparkles, Target, Filter, AlertTriangle, Lightbulb } from 'lucide-react';
import { EnhancedCytoscapeGraph } from '../components/graph/EnhancedCytoscapeGraph';
import { useLifecycleStats } from '../hooks/useLifecycle';
import { usePatternClusters } from '../hooks/useAnalytics';
import { StateBadge } from '../components/StateBadge';
import { QualityBadge } from '../components/QualityBadge';
import { getProjectGraph, getContradictions, findSolutions, getGraphRecommendations } from '../api/graph';

const MEMORY_TYPES = ['error', 'decision', 'pattern', 'docs', 'learning', 'context'];
const RELATIONSHIP_TYPES = ['FIXES', 'CAUSES', 'SUPPORTS', 'RELATED', 'FOLLOWS', 'SUPERSEDES', 'SIMILAR_TO', 'CONTRADICTS'];
const EDGE_WEIGHTS: Record<string, number> = {
  FIXES: 4, SUPPORTS: 3, SUPERSEDES: 3, CAUSES: 3, CONTRADICTS: 2,
  FOLLOWS: 2, RELATED: 1.5, SIMILAR_TO: 1,
};

export function Graph() {
  const [typeFilters, setTypeFilters] = useState<Set<string>>(new Set(MEMORY_TYPES));
  const [relFilters, setRelFilters] = useState<Set<string>>(new Set(RELATIONSHIP_TYPES));
  const [projectFilter, setProjectFilter] = useState<string>('');

  const { data: timelineData, isLoading, error } = useQuery({
    queryKey: ['graph', 'timeline'],
    queryFn: () => getTimeline(undefined, undefined, 200),
  });

  const { data: memories } = useQuery({
    queryKey: ['memories', 'all'],
    queryFn: () => getMemories({ limit: 200 }),
  });

  // Phase 3-4: Lifecycle and pattern data
  const { data: lifecycleStats } = useLifecycleStats();
  const { data: patternClusters } = usePatternClusters(3);

  const toggleTypeFilter = (type: string) => {
    setTypeFilters(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const toggleRelFilter = (rel: string) => {
    setRelFilters(prev => {
      const next = new Set(prev);
      if (next.has(rel)) next.delete(rel);
      else next.add(rel);
      return next;
    });
  };

  // Transform timeline data into Cytoscape elements with filtering
  const graphElements = useMemo(() => {
    if (!timelineData?.timeline) return [];

    const nodes: any[] = [];
    const edges: any[] = [];
    const nodeIds = new Set<string>();
    const visibleNodeIds = new Set<string>();

    // First pass: identify visible nodes based on type filter
    timelineData.timeline.forEach((item: any) => {
      if (!typeFilters.has(item.type)) return;
      if (projectFilter && item.project && item.project !== projectFilter) return;

      if (!nodeIds.has(item.id)) {
        nodes.push({
          data: {
            id: item.id,
            label: item.preview?.substring(0, 50) + '...' || item.type,
            type: item.type,
          }
        });
        nodeIds.add(item.id);
        visibleNodeIds.add(item.id);
      }

      // Add relationships as edges
      if (item.relationships && Array.isArray(item.relationships)) {
        item.relationships.forEach((rel: any) => {
          if (!rel.target_id) return;
          const relType = (rel.type || 'RELATED').toUpperCase();
          if (!relFilters.has(relType)) return;

          // Add target node if not exists
          if (!nodeIds.has(rel.target_id)) {
            nodes.push({
              data: {
                id: rel.target_id,
                label: rel.target_type || 'Memory',
                type: rel.target_type || 'unknown',
              }
            });
            nodeIds.add(rel.target_id);
          }

          // Add edge with weight
          edges.push({
            data: {
              id: `${item.id}-${rel.target_id}`,
              source: item.id,
              target: rel.target_id,
              type: relType,
              weight: EDGE_WEIGHTS[relType] || 1,
            }
          });
        });
      }
    });

    return [...nodes, ...edges];
  }, [timelineData, typeFilters, relFilters, projectFilter]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a] flex flex-col">
      <Header title="Knowledge Graph" />
      <div className="flex-1 p-6 space-y-6 overflow-hidden">
        {/* Hero Section */}
        <div className="bg-gradient-to-br from-purple-600 via-violet-600 to-fuchsia-600 rounded-2xl p-8 shadow-2xl">
          <div className="flex items-center gap-4">
            <div className="p-4 bg-white/20 backdrop-blur-sm rounded-xl">
              <Network className="h-10 w-10 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">Knowledge Graph</h1>
              <p className="text-purple-100 mt-1">
                Interactive visualization of memory relationships and connections
              </p>
            </div>
          </div>
        </div>

        {/* Filter Toolbar */}
        <Card className="bg-[#0f0f0f] border-white/10">
          <CardContent className="py-4 space-y-3">
            <div className="flex items-center gap-2 flex-wrap">
              <Filter className="h-4 w-4 text-white/50" />
              <span className="text-xs text-white/50 font-medium mr-2">Types:</span>
              {MEMORY_TYPES.map((type) => {
                const colors: Record<string, string> = {
                  error: 'bg-red-500/20 text-red-400 border-red-500/30',
                  decision: 'bg-green-500/20 text-green-400 border-green-500/30',
                  pattern: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
                  docs: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
                  learning: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
                  context: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
                };
                return (
                  <button
                    key={type}
                    onClick={() => toggleTypeFilter(type)}
                    className={`px-2.5 py-1 text-xs rounded-lg border transition-all ${
                      typeFilters.has(type)
                        ? colors[type]
                        : 'bg-white/5 text-white/30 border-white/10 opacity-50'
                    }`}
                  >
                    {type}
                  </button>
                );
              })}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Network className="h-4 w-4 text-white/50" />
              <span className="text-xs text-white/50 font-medium mr-2">Relations:</span>
              {RELATIONSHIP_TYPES.map((rel) => {
                const relColors: Record<string, string> = {
                  FIXES: 'bg-green-500/20 text-green-400 border-green-500/30',
                  CAUSES: 'bg-red-500/20 text-red-400 border-red-500/30',
                  SUPPORTS: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
                  RELATED: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
                  FOLLOWS: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
                  SUPERSEDES: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
                  SIMILAR_TO: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
                  CONTRADICTS: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
                };
                return (
                  <button
                    key={rel}
                    onClick={() => toggleRelFilter(rel)}
                    className={`px-2.5 py-1 text-xs rounded-lg border transition-all ${
                      relFilters.has(rel)
                        ? relColors[rel]
                        : 'bg-white/5 text-white/30 border-white/10 opacity-50'
                    }`}
                  >
                    {rel.toLowerCase().replace('_', ' ')} ({EDGE_WEIGHTS[rel] || 1}px)
                  </button>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card className="h-[calc(100vh-420px)] bg-[#0f0f0f] border border-white/10 shadow-2xl">
          <CardHeader className="border-b border-white/10">
            <CardTitle className="text-white flex items-center gap-2">
              <Network className="h-5 w-5 text-purple-400" />
              Memory Network Visualization
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[calc(100%-80px)] p-0">
            {isLoading ? (
              <div className="h-full flex items-center justify-center bg-[#0a0a0a]">
                <div className="text-center space-y-4">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto" />
                  <p className="text-white/70">Loading graph...</p>
                </div>
              </div>
            ) : error ? (
              <div className="h-full flex items-center justify-center bg-[#0a0a0a]">
                <div className="text-center space-y-2">
                  <AlertCircle className="h-12 w-12 text-red-500 mx-auto" />
                  <p className="text-red-400">Failed to load graph data</p>
                  <p className="text-sm text-white/50">
                    Make sure the graph service is running
                  </p>
                </div>
              </div>
            ) : !graphElements || graphElements.length === 0 ? (
              <div className="h-full flex items-center justify-center bg-[#0a0a0a]">
                <div className="text-center space-y-2">
                  <Network className="h-12 w-12 text-white/30 mx-auto" />
                  <p className="text-white/70">No graph data available</p>
                  <p className="text-sm text-white/50">
                    Create some memories with relationships to see them here
                  </p>
                </div>
              </div>
            ) : (
              <EnhancedCytoscapeGraph
                elements={graphElements}
                memories={memories}
              />
            )}
          </CardContent>
        </Card>

        {/* Phase 3-4: State-Colored Graph Insights */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* State Distribution */}
          {lifecycleStats && (
            <Card className="lg:col-span-2 bg-[#0f0f0f] border-white/10 shadow-xl hover:shadow-purple-500/10 transition-all">
              <CardHeader className="border-b border-white/5">
                <div className="flex items-center gap-2">
                  <Target className="h-5 w-5 text-purple-400" />
                  <CardTitle className="text-white">Graph State Distribution</CardTitle>
                </div>
                <CardDescription className="text-white/60">
                  Memory lifecycle states in the knowledge graph
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                  {Object.entries(lifecycleStats.state_distribution || lifecycleStats.distribution || {}).map(([state, count]) => (
                    <div key={state} className="flex flex-col items-center gap-2 p-4 rounded-lg bg-[#0a0a0a] border border-white/5 hover:border-white/10 transition-colors">
                      <StateBadge state={state} size="sm" showIcon={true} />
                      <Badge className="bg-white/10 text-white/90 font-mono">
                        {count as number} nodes
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Pattern Clusters */}
          {patternClusters && patternClusters.length > 0 && (
            <Card className="bg-[#0f0f0f] border-white/10 shadow-xl hover:shadow-amber-500/10 transition-all">
              <CardHeader className="border-b border-white/5">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-amber-400" />
                  <CardTitle className="text-white">Pattern Clusters</CardTitle>
                </div>
                <CardDescription className="text-white/60">
                  Detected memory groupings by similarity
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6 space-y-3">
                {patternClusters.map((cluster, index) => (
                  <div
                    key={index}
                    className="p-4 rounded-lg bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-amber-500/20 hover:border-amber-500/40 transition-all"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2 flex-wrap">
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
                    </div>
                    <p className="text-sm text-white/90 mb-2 font-medium">
                      {cluster.cluster_name}
                    </p>
                    <p className="text-xs text-white/60 mb-2">
                      {cluster.summary}
                    </p>
                    {cluster.tags?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {cluster.tags?.slice(0, 5).map((tag, i) => (
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
              </CardContent>
            </Card>
          )}
        </div>

        {/* Legend Card */}
        <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl">
          <CardHeader className="border-b border-white/10">
            <CardTitle className="text-white">Legend</CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium mb-3 text-white/90">Memory Types</h4>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <div className="w-5 h-5 rounded-full bg-[#ef4444] shadow-lg shadow-red-500/30" />
                    <span className="text-sm text-white/90">Error</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <div className="w-5 h-5 rounded-full bg-[#22c55e] shadow-lg shadow-green-500/30" />
                    <span className="text-sm text-white/90">Decision</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <div className="w-5 h-5 rounded-full bg-[#3b82f6] shadow-lg shadow-blue-500/30" />
                    <span className="text-sm text-white/90">Pattern</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <div className="w-5 h-5 rounded-full bg-[#a855f7] shadow-lg shadow-purple-500/30" />
                    <span className="text-sm text-white/90">Docs</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <div className="w-5 h-5 rounded-full bg-[#f59e0b] shadow-lg shadow-amber-500/30" />
                    <span className="text-sm text-white/90">Learning</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <div className="w-5 h-5 rounded-full bg-[#6b7280] shadow-lg shadow-gray-500/30" />
                    <span className="text-sm text-white/90">Context</span>
                  </div>
                </div>
              </div>

              <div className="border-t border-white/10 pt-4">
                <h4 className="text-sm font-medium mb-3 text-white/90">Relationship Types</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <div className="w-8 h-0.5 bg-[#22c55e] shadow-sm shadow-green-500/30" />
                    <span className="text-sm text-white/90">Fixes</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <div className="w-8 h-0.5 bg-[#ef4444] border-dashed border-t shadow-sm shadow-red-500/30" />
                    <span className="text-sm text-white/90">Causes</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <div className="w-8 h-0.5 bg-[#6b7280] border-dotted border-t shadow-sm shadow-gray-500/30" />
                    <span className="text-sm text-white/90">Related</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <div className="w-8 h-1 bg-[#3b82f6] shadow-sm shadow-blue-500/30" />
                    <span className="text-sm text-white/90">Supersedes</span>
                  </div>
                </div>
              </div>

              {/* Phase 3-4: Memory States */}
              <div className="border-t border-white/10 pt-4">
                <h4 className="text-sm font-medium mb-3 text-white/90">Memory States (Phase 3-4)</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <StateBadge state="episodic" size="sm" showIcon={false} />
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <StateBadge state="staging" size="sm" showIcon={false} />
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <StateBadge state="semantic" size="sm" showIcon={false} />
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <StateBadge state="procedural" size="sm" showIcon={false} />
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <StateBadge state="archived" size="sm" showIcon={false} />
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <StateBadge state="purged" size="sm" showIcon={false} />
                  </div>
                </div>
              </div>

              <div className="border-t border-white/10 pt-4">
                <h4 className="text-sm font-medium mb-3 text-white/90">Node Indicators</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <div className="relative">
                      <div className="w-5 h-5 rounded-full bg-purple-500/50" />
                      <div className="absolute inset-0 rounded-full border-2 border-amber-500 shadow-lg shadow-amber-500/30" />
                    </div>
                    <span className="text-sm text-white/90">Pinned Memory</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <div className="relative">
                      <div className="w-5 h-5 rounded-full bg-purple-500/50" />
                      <div className="absolute inset-0 rounded-full border-2 border-red-500 animate-pulse shadow-lg shadow-red-500/30" />
                    </div>
                    <span className="text-sm text-white/90">Unresolved Error</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <div className="w-8 h-5 rounded-full bg-purple-500/50 shadow-lg shadow-purple-500/30" />
                    <span className="text-sm text-white/90">High Importance (larger)</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 rounded bg-[#0a0a0a] border border-white/5">
                    <div className="w-3 h-3 rounded-full bg-purple-500/20" />
                    <span className="text-sm text-white/90">Low Recency (faded)</span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Contradictions Panel */}
        <ContradictionsPanel />

        {/* Graph Solutions Finder */}
        <GraphSolutionsFinder />
      </div>
    </div>
  );
}

function ContradictionsPanel() {
  const { data: contradictions, isLoading } = useQuery({
    queryKey: ['graph', 'contradictions'],
    queryFn: getContradictions,
    staleTime: 300000,
  });

  if (isLoading || !contradictions || contradictions.length === 0) return null;

  return (
    <Card className="bg-[#0f0f0f] border border-white/10 border-l-4 border-l-red-500 shadow-xl">
      <CardHeader>
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-red-400" />
          <CardTitle className="text-white">Contradictions</CardTitle>
        </div>
        <CardDescription className="text-white/60">
          Memory pairs that contain conflicting information
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 max-h-[300px] overflow-y-auto">
        {contradictions.map((c, i) => (
          <div key={i} className="p-3 rounded-lg bg-[#0a0a0a] border border-red-500/20">
            <div className="grid grid-cols-2 gap-3">
              <div className="p-2 rounded bg-white/5">
                <Badge className="bg-blue-500/20 text-blue-300 border border-blue-500/30 text-xs mb-1">{c.memory_a.type}</Badge>
                <p className="text-xs text-white/70 line-clamp-2">{c.memory_a.content}</p>
              </div>
              <div className="p-2 rounded bg-white/5">
                <Badge className="bg-blue-500/20 text-blue-300 border border-blue-500/30 text-xs mb-1">{c.memory_b.type}</Badge>
                <p className="text-xs text-white/70 line-clamp-2">{c.memory_b.content}</p>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function GraphSolutionsFinder() {
  const [errorId, setErrorId] = useState('');
  const { data: solutions, refetch } = useQuery({
    queryKey: ['graph', 'solutions', errorId],
    queryFn: () => findSolutions(errorId),
    enabled: false,
  });

  return (
    <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-green-400" />
          <CardTitle className="text-white">Find Solutions</CardTitle>
        </div>
        <CardDescription className="text-white/60">
          Enter an error memory ID to find linked solutions
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Input
            value={errorId}
            onChange={(e) => setErrorId(e.target.value)}
            placeholder="Error memory ID"
            className="bg-[#0a0a0a] border-white/10 text-white"
          />
          <Button
            onClick={() => refetch()}
            disabled={!errorId}
            className="bg-green-500 hover:bg-green-600 text-white"
          >
            Find
          </Button>
        </div>
        {solutions?.solutions && solutions.solutions.length > 0 && (
          <div className="space-y-2">
            {solutions.solutions.map((sol) => (
              <div key={sol.id} className="p-3 rounded-lg bg-green-500/10 border border-green-500/30">
                <div className="flex items-center gap-2 mb-1">
                  <Badge className="bg-green-500/20 text-green-300 border border-green-500/30 text-xs">{sol.relation}</Badge>
                  <span className="text-xs text-white/40">score: {(sol.score ?? 0).toFixed(2)}</span>
                </div>
                <p className="text-sm text-white/80">{sol.content}</p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
