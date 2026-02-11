import { useState, useMemo } from 'react';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import {
  useSessionStats,
  useSessionMemories,
  useConsolidateSession,
  useBatchConsolidate,
  useCreateSession,
  useCloseSession,
  useDeleteSession,
} from '../hooks/useSessions';
import { MemoryDetailPanel } from '../components/memory/MemoryDetailPanel';
import { MemoryTypeBadge } from '../components/memory/MemoryTypeBadge';
import { formatDistanceToNow, intervalToDuration } from 'date-fns';
import type { RecentSession, SessionMemory } from '../api/sessions';
import {
  Clock,
  Layers,
  Plus,
  ChevronDown,
  ChevronRight,
  Combine,
  Database,
  Activity,
  Square,
  Trash2,
  Search,
  Timer,
  FolderOpen,
  Filter,
} from 'lucide-react';

// Type color maps matching the rest of the dashboard
const TYPE_COLORS: Record<string, { bg: string; dot: string; ring: string }> = {
  error: { bg: 'bg-red-500', dot: 'bg-red-500', ring: 'ring-red-500/30' },
  docs: { bg: 'bg-blue-500', dot: 'bg-blue-500', ring: 'ring-blue-500/30' },
  decision: { bg: 'bg-emerald-500', dot: 'bg-emerald-500', ring: 'ring-emerald-500/30' },
  pattern: { bg: 'bg-amber-500', dot: 'bg-amber-500', ring: 'ring-amber-500/30' },
  learning: { bg: 'bg-purple-500', dot: 'bg-purple-500', ring: 'ring-purple-500/30' },
  context: { bg: 'bg-slate-500', dot: 'bg-slate-500', ring: 'ring-slate-500/30' },
};

function humanizeDuration(start: string, end: string): string {
  if (!start || !end) return '';
  try {
    const dur = intervalToDuration({ start: new Date(start), end: new Date(end) });
    const parts: string[] = [];
    if (dur.days && dur.days > 0) parts.push(`${dur.days}d`);
    if (dur.hours && dur.hours > 0) parts.push(`${dur.hours}h`);
    if (dur.minutes && dur.minutes > 0) parts.push(`${dur.minutes}m`);
    return parts.length > 0 ? parts.join(' ') : '<1m';
  } catch {
    return '';
  }
}

function TypeBreakdownBar({ breakdown, total }: { breakdown: Record<string, number>; total: number }) {
  if (!breakdown || total === 0) return null;
  return (
    <div className="flex w-full h-1.5 rounded-full overflow-hidden bg-white/5">
      {Object.entries(breakdown).map(([type, count]) => {
        const colors = TYPE_COLORS[type] || TYPE_COLORS.context;
        const pct = (count / total) * 100;
        return (
          <div
            key={type}
            className={`${colors.bg} transition-all`}
            style={{ width: `${pct}%` }}
            title={`${type}: ${count}`}
          />
        );
      })}
    </div>
  );
}

function SessionMemoryTimeline({
  memories,
  onMemoryClick,
}: {
  memories: SessionMemory[];
  onMemoryClick: (id: string) => void;
}) {
  if (!memories || memories.length === 0) {
    return (
      <p className="text-white/50 text-sm text-center py-4">No memories in this session</p>
    );
  }

  return (
    <div className="relative pl-6 space-y-3">
      {/* Vertical connecting line */}
      <div className="absolute left-[11px] top-2 bottom-2 w-0.5 bg-white/[0.06]" />

      {memories.map((memory) => {
        const colors = TYPE_COLORS[memory.type] || TYPE_COLORS.context;
        return (
          <button
            key={memory.id}
            onClick={() => onMemoryClick(memory.id)}
            className="relative w-full text-left group"
          >
            {/* Type-colored dot */}
            <div
              className={`absolute -left-6 top-3 w-[15px] h-[15px] rounded-full ${colors.dot} ring-2 ${colors.ring} ring-offset-1 ring-offset-[#0a0a0a]`}
            />

            {/* Memory card */}
            <div className="p-3 rounded-lg border border-white/5 bg-[#0f0f0f] hover:border-white/15 hover:bg-[#131313] transition-all">
              <div className="flex items-center gap-2 mb-1.5">
                <MemoryTypeBadge type={memory.type} />
                <span className="text-xs text-white/40">
                  {(() => {
                    try {
                      return formatDistanceToNow(new Date(memory.created_at), { addSuffix: true });
                    } catch {
                      return memory.created_at;
                    }
                  })()}
                </span>
                {memory.project && (
                  <>
                    <span className="text-white/20">·</span>
                    <span className="text-xs text-blue-400">{memory.project}</span>
                  </>
                )}
              </div>
              <p className="text-sm text-white/80 line-clamp-2 group-hover:text-white/90 transition-colors">
                {memory.content}
              </p>
              {memory.tags?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {memory.tags.slice(0, 4).map((tag) => (
                    <Badge
                      key={tag}
                      className="text-xs bg-white/5 text-white/50 border border-white/10"
                    >
                      {tag}
                    </Badge>
                  ))}
                  {memory.tags.length > 4 && (
                    <span className="text-xs text-white/30">+{memory.tags.length - 4}</span>
                  )}
                </div>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}

type StatusFilter = 'all' | 'active' | 'consolidated';

export function Sessions() {
  const [expandedSession, setExpandedSession] = useState<string | null>(null);
  const [newProject, setNewProject] = useState('');
  const [detailPanelId, setDetailPanelId] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [projectFilter, setProjectFilter] = useState<string>('');

  const { data: stats, isLoading: statsLoading } = useSessionStats();
  const { data: sessionMemories } = useSessionMemories(expandedSession || '');
  const consolidateSession = useConsolidateSession();
  const batchConsolidate = useBatchConsolidate();
  const createSession = useCreateSession();
  const closeSession = useCloseSession();
  const deleteSession = useDeleteSession();

  // Derive unique projects from sessions
  const uniqueProjects = useMemo(() => {
    if (!stats?.recent_sessions) return [];
    const projects = new Set<string>();
    for (const s of stats.recent_sessions) {
      if (s.project) projects.add(s.project);
    }
    return Array.from(projects).sort();
  }, [stats?.recent_sessions]);

  // Filtered sessions
  const filteredSessions = useMemo(() => {
    if (!stats?.recent_sessions) return [];
    return stats.recent_sessions.filter((s) => {
      // Status filter
      if (statusFilter !== 'all' && s.status !== statusFilter) return false;
      // Project filter
      if (projectFilter && s.project !== projectFilter) return false;
      // Search filter
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchesId = s.session_id.toLowerCase().includes(q);
        const matchesProject = s.project?.toLowerCase().includes(q);
        if (!matchesId && !matchesProject) return false;
      }
      return true;
    });
  }, [stats?.recent_sessions, statusFilter, projectFilter, searchQuery]);

  const handleCreateSession = () => {
    createSession.mutate(newProject || undefined);
    setNewProject('');
  };

  const statusTabs: { key: StatusFilter; label: string; count: number }[] = [
    { key: 'all', label: 'All', count: stats?.recent_sessions?.length ?? 0 },
    {
      key: 'active',
      label: 'Active',
      count: stats?.recent_sessions?.filter((s) => s.status === 'active').length ?? 0,
    },
    {
      key: 'consolidated',
      label: 'Consolidated',
      count: stats?.recent_sessions?.filter((s) => s.status === 'consolidated').length ?? 0,
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]">
      <Header title="Sessions" />
      <div className="p-4 sm:p-8 space-y-6 max-w-[1800px] mx-auto">
        {/* Hero */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-teal-500/10 via-cyan-500/10 to-blue-500/10 p-6 border border-white/5">
          <div className="absolute inset-0 bg-gradient-to-br from-teal-500/5 via-transparent to-cyan-500/5" />
          <div className="relative flex items-center gap-4">
            <div className="p-3 bg-teal-500/10 rounded-xl ring-1 ring-teal-500/20">
              <Clock className="h-8 w-8 text-teal-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">Session Management</h1>
              <p className="text-white/60 mt-1">
                Track coding sessions and consolidate session memories
              </p>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-teal-500/20 rounded-lg">
                  <Layers className="h-5 w-5 text-teal-400" />
                </div>
                <div>
                  <p className="text-xs text-white/50">Total Sessions</p>
                  <p className="text-2xl font-bold text-white">
                    {statsLoading ? '...' : stats?.total_sessions ?? 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <Activity className="h-5 w-5 text-green-400" />
                </div>
                <div>
                  <p className="text-xs text-white/50">Active</p>
                  <p className="text-2xl font-bold text-white">
                    {statsLoading ? '...' : stats?.active_sessions ?? 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <Database className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-xs text-white/50">Avg Memories/Session</p>
                  <p className="text-2xl font-bold text-white">
                    {statsLoading ? '...' : (stats?.avg_memories_per_session ?? 0).toFixed(1)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <Combine className="h-5 w-5 text-purple-400" />
                </div>
                <div>
                  <p className="text-xs text-white/50">Consolidation Rate</p>
                  <p className="text-2xl font-bold text-white">
                    {statsLoading ? '...' : ((stats?.consolidation_rate ?? 0) * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-3">
          <div className="flex gap-2 flex-1 min-w-[250px]">
            <Input
              value={newProject}
              onChange={(e) => setNewProject(e.target.value)}
              placeholder="Project name (optional)"
              className="bg-[#0f0f0f] border-white/10 text-white"
            />
            <Button
              onClick={handleCreateSession}
              disabled={createSession.isPending}
              className="bg-teal-500 hover:bg-teal-600 text-white whitespace-nowrap"
            >
              <Plus className="mr-2 h-4 w-4" />
              New Session
            </Button>
          </div>
          <Button
            onClick={() => batchConsolidate.mutate(24)}
            disabled={batchConsolidate.isPending}
            className="bg-purple-500 hover:bg-purple-600 text-white"
          >
            <Combine className="mr-2 h-4 w-4" />
            {batchConsolidate.isPending ? 'Consolidating...' : 'Batch Consolidate All'}
          </Button>
        </div>

        {batchConsolidate.data && (
          <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-xl">
            <p className="text-purple-200">
              Processed {batchConsolidate.data.sessions_processed} sessions,
              consolidated {batchConsolidate.data.total_memories_consolidated} memories
            </p>
          </div>
        )}

        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-3 p-4 bg-[#0f0f0f] border border-white/10 rounded-xl">
          {/* Status tabs */}
          <div className="flex gap-1 p-1 bg-white/5 rounded-lg">
            {statusTabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setStatusFilter(tab.key)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  statusFilter === tab.key
                    ? 'bg-teal-500 text-white shadow-sm'
                    : 'text-white/50 hover:text-white/80 hover:bg-white/5'
                }`}
              >
                {tab.label}
                <span className="ml-1.5 text-[10px] opacity-70">({tab.count})</span>
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search session ID or project..."
              className="pl-9 bg-[#0a0a0a] border-white/10 text-white text-sm h-9"
            />
          </div>

          {/* Project dropdown */}
          <div className="relative">
            <FolderOpen className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30 pointer-events-none z-10" />
            <select
              value={projectFilter}
              onChange={(e) => setProjectFilter(e.target.value)}
              className="pl-9 pr-8 h-9 rounded-md bg-[#0a0a0a] border border-white/10 text-white text-sm appearance-none cursor-pointer focus:outline-none focus:ring-1 focus:ring-teal-500/50"
            >
              <option value="">All Projects</option>
              {uniqueProjects.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
            <Filter className="absolute right-2 top-1/2 -translate-y-1/2 h-3 w-3 text-white/30 pointer-events-none" />
          </div>

          {/* Active filter count */}
          {(statusFilter !== 'all' || searchQuery || projectFilter) && (
            <button
              onClick={() => {
                setStatusFilter('all');
                setSearchQuery('');
                setProjectFilter('');
              }}
              className="text-xs text-white/40 hover:text-white/70 transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Session List */}
        <div className="space-y-3">
          {filteredSessions.length === 0 && (
            <div className="text-center py-12 text-white/40">
              <Layers className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">
                {stats?.recent_sessions?.length === 0
                  ? 'No sessions found'
                  : 'No sessions match your filters'}
              </p>
            </div>
          )}

          {filteredSessions.map((session: RecentSession) => {
            const isExpanded = expandedSession === session.session_id;
            const duration = humanizeDuration(session.created_at, session.last_activity);

            return (
              <div
                key={session.session_id}
                className="border border-white/[0.08] rounded-xl overflow-hidden bg-[#0f0f0f] hover:border-white/[0.15] transition-all"
              >
                {/* Type breakdown mini-bar */}
                {session.type_breakdown && (
                  <TypeBreakdownBar
                    breakdown={session.type_breakdown}
                    total={session.memory_count}
                  />
                )}

                {/* Session card header */}
                <button
                  onClick={() =>
                    setExpandedSession(isExpanded ? null : session.session_id)
                  }
                  className="w-full p-4 text-left"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-white/40 flex-shrink-0" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-white/40 flex-shrink-0" />
                      )}

                      {/* Project badge */}
                      {session.project ? (
                        <Badge className="bg-blue-500/15 text-blue-400 border border-blue-500/25 text-xs flex-shrink-0">
                          {session.project}
                        </Badge>
                      ) : (
                        <span className="text-xs text-white/30 italic flex-shrink-0">
                          no project
                        </span>
                      )}

                      {/* Session ID */}
                      <span className="text-sm font-mono text-white/60 truncate">
                        {session.session_id.replace('session_', '').slice(0, 12)}
                      </span>

                      {/* Memory count badge */}
                      <Badge className="bg-white/5 text-white/60 border border-white/10 text-xs flex-shrink-0">
                        {session.memory_count} {session.memory_count === 1 ? 'memory' : 'memories'}
                      </Badge>

                      {/* Status badge */}
                      <Badge
                        className={`text-xs flex-shrink-0 ${
                          session.status === 'active'
                            ? 'bg-green-500/15 text-green-400 border border-green-500/25'
                            : 'bg-white/5 text-white/40 border border-white/10'
                        }`}
                      >
                        {session.status}
                      </Badge>

                      {/* Type breakdown legend (small) */}
                      {session.type_breakdown && (
                        <div className="hidden lg:flex items-center gap-1.5 flex-shrink-0">
                          {Object.entries(session.type_breakdown).map(([type, count]) => {
                            const colors = TYPE_COLORS[type] || TYPE_COLORS.context;
                            return (
                              <span
                                key={type}
                                className="flex items-center gap-1 text-[10px] text-white/40"
                                title={`${type}: ${count}`}
                              >
                                <span
                                  className={`inline-block w-2 h-2 rounded-full ${colors.dot}`}
                                />
                                {count}
                              </span>
                            );
                          })}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-3 flex-shrink-0">
                      {/* Duration chip */}
                      {duration && (
                        <span className="flex items-center gap-1 text-xs text-white/40">
                          <Timer className="h-3 w-3" />
                          {duration}
                        </span>
                      )}

                      {/* Relative date */}
                      <span className="text-xs text-white/30">
                        {(() => {
                          try {
                            return formatDistanceToNow(
                              new Date(session.last_activity || session.created_at),
                              { addSuffix: true }
                            );
                          } catch {
                            return '';
                          }
                        })()}
                      </span>

                      {/* Action buttons — hover reveal */}
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        {session.status === 'active' && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              closeSession.mutate(session.session_id);
                            }}
                            disabled={closeSession.isPending}
                            className="h-7 px-2 text-red-400 hover:bg-red-500/10"
                            title="Stop & Save"
                          >
                            <Square className="h-3 w-3" />
                          </Button>
                        )}
                        {session.status !== 'consolidated' && session.memory_count >= 2 && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              consolidateSession.mutate(session.session_id);
                            }}
                            disabled={consolidateSession.isPending}
                            className="h-7 px-2 text-purple-400 hover:bg-purple-500/10"
                            title="Consolidate"
                          >
                            <Combine className="h-3 w-3" />
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (
                              confirm(
                                `Delete session ${session.session_id.slice(0, 12)}... and all its memories?`
                              )
                            ) {
                              deleteSession.mutate(session.session_id);
                            }
                          }}
                          disabled={deleteSession.isPending}
                          className="h-7 px-2 text-red-400 hover:bg-red-500/10"
                          title="Delete"
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </button>

                {/* Expanded: Memory Timeline */}
                {isExpanded && (
                  <div className="border-t border-white/5 p-4 bg-[#0a0a0a]">
                    {/* Action buttons visible in expanded state */}
                    <div className="flex gap-2 mb-4">
                      {session.status === 'active' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => closeSession.mutate(session.session_id)}
                          disabled={closeSession.isPending}
                          className="border-red-500/30 text-red-300 hover:bg-red-500/20"
                        >
                          <Square className="h-3 w-3 mr-1" />
                          {closeSession.isPending ? 'Closing...' : 'Stop & Save'}
                        </Button>
                      )}
                      {session.status !== 'consolidated' && session.memory_count >= 2 && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => consolidateSession.mutate(session.session_id)}
                          disabled={consolidateSession.isPending}
                          className="border-purple-500/30 text-purple-300 hover:bg-purple-500/20"
                        >
                          <Combine className="h-3 w-3 mr-1" />
                          Consolidate
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          if (
                            confirm(
                              `Delete session ${session.session_id.slice(0, 12)}... and all its memories?`
                            )
                          ) {
                            deleteSession.mutate(session.session_id);
                          }
                        }}
                        disabled={deleteSession.isPending}
                        className="border-red-500/30 text-red-400 hover:bg-red-500/20"
                      >
                        <Trash2 className="h-3 w-3 mr-1" />
                        Delete
                      </Button>
                    </div>

                    <SessionMemoryTimeline
                      memories={sessionMemories || []}
                      onMemoryClick={(id) => setDetailPanelId(id)}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Memory Detail Panel */}
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
