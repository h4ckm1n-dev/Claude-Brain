import { Header } from '../components/layout/Header';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Alert, AlertDescription } from '../components/ui/alert';
import { useQuery } from '@tanstack/react-query';
import { getTimeline, getMemories } from '../api/memories';
import { AlertCircle, Network } from 'lucide-react';
import { EnhancedCytoscapeGraph } from '../components/graph/EnhancedCytoscapeGraph';
import { useMemo } from 'react';

export function Graph() {
  const { data: timelineData, isLoading, error } = useQuery({
    queryKey: ['graph', 'timeline'],
    queryFn: () => getTimeline(undefined, undefined, 200),
  });

  const { data: memories } = useQuery({
    queryKey: ['memories', 'all'],
    queryFn: () => getMemories({ limit: 200 }),
  });

  // Transform timeline data into Cytoscape elements
  const graphElements = useMemo(() => {
    if (!timelineData?.timeline) return [];

    const nodes: any[] = [];
    const edges: any[] = [];
    const nodeIds = new Set<string>();

    timelineData.timeline.forEach((item: any) => {
      // Add memory as node
      if (!nodeIds.has(item.id)) {
        nodes.push({
          data: {
            id: item.id,
            label: item.preview?.substring(0, 50) + '...' || item.type,
            type: item.type,
          }
        });
        nodeIds.add(item.id);
      }

      // Add relationships as edges
      if (item.relationships && Array.isArray(item.relationships)) {
        item.relationships.forEach((rel: any) => {
          if (rel.target_id) {
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

            // Add edge
            edges.push({
              data: {
                id: `${item.id}-${rel.target_id}`,
                source: item.id,
                target: rel.target_id,
                type: rel.type || 'RELATED',
              }
            });
          }
        });
      }
    });

    return [...nodes, ...edges];
  }, [timelineData]);

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

        <Alert className="bg-purple-500/10 border-purple-500/30 backdrop-blur-sm">
          <AlertCircle className="h-4 w-4 text-purple-400" />
          <AlertDescription className="text-purple-200">
            Interactive knowledge graph. Hover nodes to see connections, click to view details. Use controls to navigate and customize the view.
          </AlertDescription>
        </Alert>

        <Card className="h-[calc(100vh-320px)] bg-[#0f0f0f] border border-white/10 shadow-2xl">
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
      </div>
    </div>
  );
}
