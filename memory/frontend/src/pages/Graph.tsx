import { Header } from '../components/layout/Header';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Alert, AlertDescription } from '../components/ui/alert';
import { useQuery } from '@tanstack/react-query';
import { getTimeline, getMemories } from '../api/memories';
import { AlertCircle } from 'lucide-react';
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
    <div className="h-screen flex flex-col">
      <Header title="Knowledge Graph" />
      <div className="flex-1 p-6 space-y-6 overflow-hidden">
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Interactive knowledge graph. Hover nodes to see connections, click to view details. Use controls to navigate and customize the view.
          </AlertDescription>
        </Alert>

        <Card className="h-[calc(100vh-220px)] shadow-xl">
          <CardHeader>
            <CardTitle>Memory Network Visualization</CardTitle>
          </CardHeader>
          <CardContent className="h-[calc(100%-80px)]">
            {isLoading ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center space-y-4">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
                  <p className="text-muted-foreground">Loading graph...</p>
                </div>
              </div>
            ) : error ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center space-y-2">
                  <AlertCircle className="h-12 w-12 text-red-500 mx-auto" />
                  <p className="text-destructive">Failed to load graph data</p>
                  <p className="text-sm text-muted-foreground">
                    Make sure the graph service is running
                  </p>
                </div>
              </div>
            ) : !graphElements || graphElements.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center space-y-2">
                  <p className="text-muted-foreground">No graph data available</p>
                  <p className="text-sm text-muted-foreground">
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
        <Card className="shadow-lg">
          <CardHeader>
            <CardTitle>Legend</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium mb-2">Memory Types</h4>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded-full bg-[#ef4444]" />
                    <span className="text-sm">Error</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded-full bg-[#22c55e]" />
                    <span className="text-sm">Decision</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded-full bg-[#3b82f6]" />
                    <span className="text-sm">Pattern</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded-full bg-[#a855f7]" />
                    <span className="text-sm">Docs</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded-full bg-[#f59e0b]" />
                    <span className="text-sm">Learning</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded-full bg-[#6b7280]" />
                    <span className="text-sm">Context</span>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-2">Relationship Types</h4>
                <div className="grid grid-cols-2 md:grid-cols-2 gap-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-0.5 bg-[#22c55e]" />
                    <span className="text-sm">Fixes</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-0.5 bg-[#ef4444] border-dashed border-t" />
                    <span className="text-sm">Causes</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-0.5 bg-[#6b7280] border-dotted border-t" />
                    <span className="text-sm">Related</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-1 bg-[#3b82f6]" />
                    <span className="text-sm">Supersedes</span>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-2">Node Indicators</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex items-center gap-2">
                    <div className="relative">
                      <div className="w-5 h-5 rounded-full bg-gray-400" />
                      <div className="absolute inset-0 rounded-full border-2 border-amber-500" />
                    </div>
                    <span className="text-sm">Pinned Memory</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="relative">
                      <div className="w-5 h-5 rounded-full bg-gray-400" />
                      <div className="absolute inset-0 rounded-full border-2 border-red-500 animate-pulse" />
                    </div>
                    <span className="text-sm">Unresolved Error</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-5 rounded-full bg-gray-400" />
                    <span className="text-sm">High Importance (larger)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-gray-300" />
                    <span className="text-sm">Low Recency (faded)</span>
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
