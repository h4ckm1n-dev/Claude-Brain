import { useState, useMemo } from 'react';
import { Header } from '../components/layout/Header';
import { useQuery } from '@tanstack/react-query';
import { getTimeline, getMemories } from '../api/memories';
import { getProjectGraph } from '../api/graph';
import { Filter, X, Network } from 'lucide-react';
import { ForceGraphView } from '../components/graph/ForceGraphView';

const MEMORY_TYPES = ['error', 'decision', 'pattern', 'docs', 'learning', 'context'];
const RELATIONSHIP_TYPES = ['FIXES', 'CAUSES', 'SUPPORTS', 'RELATED', 'FOLLOWS', 'SUPERSEDES', 'SIMILAR_TO', 'CONTRADICTS'];
const EDGE_WEIGHTS: Record<string, number> = {
  FIXES: 4, SUPPORTS: 3, SUPERSEDES: 3, CAUSES: 3, CONTRADICTS: 2,
  FOLLOWS: 2, RELATED: 1.5, SIMILAR_TO: 1,
};

const TYPE_COLORS: Record<string, string> = {
  error: 'bg-red-500/20 text-red-400 border-red-500/30',
  decision: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  pattern: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  docs: 'bg-violet-500/20 text-violet-400 border-violet-500/30',
  learning: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  context: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
};

const REL_COLORS: Record<string, string> = {
  FIXES: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  CAUSES: 'bg-red-500/20 text-red-400 border-red-500/30',
  SUPPORTS: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  RELATED: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  FOLLOWS: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  SUPERSEDES: 'bg-violet-500/20 text-violet-400 border-violet-500/30',
  SIMILAR_TO: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  CONTRADICTS: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
};

export function Graph() {
  const [typeFilters, setTypeFilters] = useState<Set<string>>(new Set(MEMORY_TYPES));
  const [relFilters, setRelFilters] = useState<Set<string>>(new Set(RELATIONSHIP_TYPES));
  const [projectFilter, setProjectFilter] = useState<string>('');
  const [filtersOpen, setFiltersOpen] = useState(false);

  const { data: timelineData, isLoading: timelineLoading, error: timelineError } = useQuery({
    queryKey: ['graph', 'timeline'],
    queryFn: () => getTimeline(undefined, undefined, 200),
    enabled: !projectFilter,
  });

  const { data: projectGraphData, isLoading: projectLoading } = useQuery({
    queryKey: ['graph', 'project', projectFilter],
    queryFn: () => getProjectGraph(projectFilter),
    enabled: !!projectFilter,
  });

  const { data: memoriesData } = useQuery({
    queryKey: ['memories', 'all'],
    queryFn: () => getMemories({ limit: 200 }),
  });
  const memories = memoriesData?.items;

  const availableProjects = useMemo(() => {
    if (!memories) return [];
    const projects = new Set(memories.filter(m => m.project).map(m => m.project!));
    return Array.from(projects).sort();
  }, [memories]);

  const isLoading = projectFilter ? projectLoading : timelineLoading;
  const error = projectFilter ? null : timelineError;

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

  const graphData = useMemo(() => {
    const nodes: any[] = [];
    const links: any[] = [];

    if (projectFilter && projectGraphData) {
      projectGraphData.nodes
        .filter((n: any) => n.type && typeFilters.has(n.type))
        .forEach((n: any) => {
          nodes.push({ id: n.id, label: n.label || n.type, type: n.type, project: n.project });
        });

      const nodeIds = new Set(nodes.map(n => n.id));
      projectGraphData.edges
        .filter((e: any) => {
          const relType = (e.relation || 'related').toUpperCase();
          return relFilters.has(relType) && nodeIds.has(e.source) && nodeIds.has(e.target);
        })
        .forEach((e: any) => {
          const relType = (e.relation || 'related').toUpperCase();
          links.push({
            source: e.source,
            target: e.target,
            type: relType,
            relation: (e.relation || 'related').toLowerCase(),
            weight: EDGE_WEIGHTS[relType] || 1,
          });
        });

      return { nodes, links };
    }

    if (!timelineData?.timeline) return { nodes: [], links: [] };

    const nodeIds = new Set<string>();

    timelineData.timeline.forEach((item: any) => {
      if (!item.type || !typeFilters.has(item.type)) return;
      if (projectFilter && item.project && item.project !== projectFilter) return;

      if (!nodeIds.has(item.id)) {
        nodes.push({
          id: item.id,
          label: item.preview?.substring(0, 50) + '...' || item.type,
          type: item.type,
          project: item.project,
        });
        nodeIds.add(item.id);
      }

      if (item.relationships && Array.isArray(item.relationships)) {
        item.relationships.forEach((rel: any) => {
          if (!rel.target_id) return;
          const relType = (rel.type || 'RELATED').toUpperCase();
          if (!relFilters.has(relType)) return;

          if (!nodeIds.has(rel.target_id)) {
            nodes.push({
              id: rel.target_id,
              label: rel.target_type || 'Memory',
              type: rel.target_type || 'unknown',
            });
            nodeIds.add(rel.target_id);
          }

          links.push({
            source: item.id,
            target: rel.target_id,
            type: relType,
            relation: relType.toLowerCase(),
            weight: EDGE_WEIGHTS[relType] || 1,
          });
        });
      }
    });

    return { nodes, links };
  }, [timelineData, projectGraphData, typeFilters, relFilters, projectFilter]);

  const nodeCount = graphData.nodes.length;
  const edgeCount = graphData.links.length;

  return (
    <div className="h-screen bg-[#050508] flex flex-col overflow-hidden">
      <Header title="Knowledge Graph" />

      <div className="flex-1 relative overflow-hidden">
        {/* Radial gradient background */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: 'radial-gradient(ellipse at 50% 40%, rgba(124, 58, 237, 0.06) 0%, rgba(59, 130, 246, 0.02) 30%, transparent 70%)',
          }}
        />

        {/* Filter toggle */}
        <button
          onClick={() => setFiltersOpen(!filtersOpen)}
          className={`absolute top-4 left-4 z-30 w-10 h-10 flex items-center justify-center rounded-xl
            transition-all duration-200 ${
              filtersOpen
                ? 'bg-white/[0.12] text-white border border-white/[0.12]'
                : 'bg-[#0c0c14]/90 backdrop-blur-xl text-white/50 hover:text-white border border-white/[0.06] hover:border-white/[0.1]'
            }`}
          title="Toggle Filters"
        >
          {filtersOpen ? <X className="h-4 w-4" /> : <Filter className="h-4 w-4" />}
        </button>

        {/* Floating filter panel */}
        {filtersOpen && (
          <div className="absolute top-4 left-16 z-30 w-72 max-h-[calc(100vh-140px)] overflow-y-auto
            bg-[#0c0c14]/95 backdrop-blur-xl border border-white/[0.06] rounded-xl
            shadow-[0_8px_32px_rgba(0,0,0,0.5)] p-4 space-y-4">

            <div className="flex items-center justify-between">
              <span className="text-[11px] text-white/30 font-medium uppercase tracking-wider">Filters</span>
              <div className="flex gap-2 text-[11px] font-mono">
                <span className="text-violet-400/70">{nodeCount} nodes</span>
                <span className="text-white/20">&middot;</span>
                <span className="text-white/30">{edgeCount} edges</span>
              </div>
            </div>

            <div>
              <span className="text-[11px] text-white/40 font-medium mb-2 block uppercase tracking-wider">Project</span>
              <select
                value={projectFilter}
                onChange={(e) => setProjectFilter(e.target.value)}
                className="w-full h-8 rounded-lg bg-white/[0.05] border border-white/[0.08] text-sm text-white/80 px-2
                  focus:outline-none focus:border-violet-500/40 transition-colors"
                style={{ colorScheme: 'dark' }}
              >
                <option value="">All projects</option>
                {availableProjects.map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>

            <div>
              <span className="text-[11px] text-white/40 font-medium mb-2 block uppercase tracking-wider">Memory Types</span>
              <div className="flex flex-wrap gap-1.5">
                {MEMORY_TYPES.map(type => (
                  <button
                    key={type}
                    onClick={() => toggleTypeFilter(type)}
                    className={`px-2.5 py-1 text-[11px] rounded-lg border transition-all duration-150 ${
                      typeFilters.has(type)
                        ? TYPE_COLORS[type]
                        : 'bg-white/[0.03] text-white/25 border-white/[0.06] hover:border-white/[0.1]'
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <span className="text-[11px] text-white/40 font-medium mb-2 block uppercase tracking-wider">Relations</span>
              <div className="flex flex-wrap gap-1.5">
                {RELATIONSHIP_TYPES.map(rel => (
                  <button
                    key={rel}
                    onClick={() => toggleRelFilter(rel)}
                    className={`px-2.5 py-1 text-[11px] rounded-lg border transition-all duration-150 ${
                      relFilters.has(rel)
                        ? REL_COLORS[rel]
                        : 'bg-white/[0.03] text-white/25 border-white/[0.06] hover:border-white/[0.1]'
                    }`}
                  >
                    {rel.toLowerCase().replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Graph */}
        {isLoading ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center space-y-4">
              <div className="w-12 h-12 rounded-full border-2 border-violet-500/30 border-t-violet-500 animate-spin mx-auto" />
              <p className="text-white/40 text-sm">Loading graph&hellip;</p>
            </div>
          </div>
        ) : error ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center space-y-3">
              <Network className="h-12 w-12 text-red-500/50 mx-auto" />
              <p className="text-red-400/80 text-sm">Failed to load graph data</p>
              <p className="text-white/30 text-xs">Make sure the service is running</p>
            </div>
          </div>
        ) : graphData.nodes.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center space-y-3">
              <Network className="h-12 w-12 text-white/15 mx-auto" />
              <p className="text-white/40 text-sm">No graph data</p>
              <p className="text-white/20 text-xs">Create memories with relationships to visualize them</p>
            </div>
          </div>
        ) : (
          <ForceGraphView
            graphData={graphData}
            memories={memories}
          />
        )}
      </div>
    </div>
  );
}
