import { useState, useMemo, useEffect } from 'react';
import { useMemories, useDeleteMemory, usePinMemory, useArchiveMemory, useReinforceMemory, useForgettingStats, useWeakMemories, useQualityLeaderboard, useQualityReport } from '../hooks/useMemories';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Plus, Trash2, Pin, Archive, Edit, Search, Download, FileText, Database, Eye, Clock, TrendingUp, Zap, Award, AlertTriangle, CheckSquare, Square } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { Memory, MemoryType } from '../types/memory';
import { MemoryDialog } from '../components/memory/MemoryDialog';
import { MemoryDetailPanel } from '../components/memory/MemoryDetailPanel';
import { MemoryTypeBadge } from '../components/memory/MemoryTypeBadge';
import { QualityProgress } from '../components/QualityBadge';
import { StateBadge } from '../components/StateBadge';
import { exportToCSV, exportToJSON, exportToMarkdown } from '../utils/export';
import { bulkAction } from '../api/memories';

// Type-colored accent bars for card top edge
const TYPE_ACCENT: Record<string, string> = {
  error: 'bg-red-500',
  docs: 'bg-blue-500',
  decision: 'bg-emerald-500',
  pattern: 'bg-amber-500',
  learning: 'bg-purple-500',
  context: 'bg-slate-400',
};

const TYPE_HOVER_GLOW: Record<string, string> = {
  error: 'hover:shadow-red-500/10',
  docs: 'hover:shadow-blue-500/10',
  decision: 'hover:shadow-emerald-500/10',
  pattern: 'hover:shadow-amber-500/10',
  learning: 'hover:shadow-purple-500/10',
  context: 'hover:shadow-slate-500/5',
};

export function Memories() {
  const [page, setPage] = useState(0);
  const [limit] = useState(30);
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'created' | 'accessed' | 'count'>('created');
  const [accessFilter, setAccessFilter] = useState<'all' | 'never' | 'recent'>('all');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedMemory, setSelectedMemory] = useState<Memory | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [detailPanelId, setDetailPanelId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const bulkMutation = useMutation({
    mutationFn: ({ op, ids, tag }: { op: string; ids: string[]; tag?: string }) =>
      bulkAction(op, ids, tag),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      setSelectedIds(new Set());
    },
  });

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredMemories.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredMemories.map(m => m.id)));
    }
  };

  const { data, isLoading } = useMemories({
    type: typeFilter || undefined,
    limit,
    offset: page * limit,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  const deleteMemory = useDeleteMemory();
  const pinMemory = usePinMemory();
  const archiveMemory = useArchiveMemory();

  // Reset page when filters change
  useEffect(() => { setPage(0); }, [typeFilter, searchQuery, accessFilter]);

  const filteredMemories = useMemo(() => {
    let filtered = items.filter((m: Memory) =>
      !searchQuery || m.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.tags?.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
    );

    if (accessFilter === 'never') {
      filtered = filtered.filter(m => m.access_count === 0);
    } else if (accessFilter === 'recent') {
      const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
      filtered = filtered.filter(m => new Date(m.last_accessed) > oneDayAgo);
    }

    filtered.sort((a, b) => {
      if (sortBy === 'count') return b.access_count - a.access_count;
      if (sortBy === 'accessed') return new Date(b.last_accessed).getTime() - new Date(a.last_accessed).getTime();
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

    return filtered;
  }, [items, searchQuery, accessFilter, sortBy]);

  const accessStats = useMemo(() => {
    if (!filteredMemories.length) return { totalAccesses: 0, mostAccessed: null as Memory | null, neverAccessed: 0, avgAccess: 0 };
    const totalAccesses = filteredMemories.reduce((sum, m) => sum + m.access_count, 0);
    const neverAccessed = filteredMemories.filter(m => m.access_count === 0).length;
    const avgAccess = totalAccesses / filteredMemories.length;
    const mostAccessed = filteredMemories.reduce((max, m) => m.access_count > (max?.access_count || 0) ? m : max, filteredMemories[0]);
    return { totalAccesses, mostAccessed, neverAccessed, avgAccess };
  }, [filteredMemories]);

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this memory?')) {
      await deleteMemory.mutateAsync(id);
    }
  };

  const handleEdit = (memory: Memory) => {
    setSelectedMemory(memory);
    setDialogOpen(true);
  };

  const handleCreate = () => {
    setSelectedMemory(null);
    setDialogOpen(true);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]">
      <Header title="Memories" />
      <div className="p-4 sm:p-6 lg:p-8 max-w-[1800px] mx-auto space-y-5">

        {/* Hero Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-500/10 via-purple-500/10 to-emerald-500/10 p-5 border border-white/5">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-purple-500/5" />
          <div className="relative flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-4">
              <div className="p-2.5 bg-blue-500/10 rounded-xl ring-1 ring-blue-500/20">
                <Database className="h-6 w-6 text-blue-400" />
              </div>
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold text-white">Memory Management</h1>
                <p className="text-white/50 text-sm mt-0.5">
                  {total} memories{typeFilter && ` \u00b7 ${typeFilter}`}{filteredMemories.length !== items.length && ` \u00b7 ${filteredMemories.length} shown`}
                </p>
              </div>
            </div>
            <Button
              onClick={handleCreate}
              className="bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white border-0 shadow-lg shadow-purple-500/20"
            >
              <Plus className="mr-2 h-4 w-4" />
              Create Memory
            </Button>
          </div>
        </div>

        {/* Compact Stats Strip */}
        <div className="flex items-center gap-4 sm:gap-6 px-4 py-3 bg-[#0f0f0f] rounded-xl border border-white/[0.06] overflow-x-auto scrollbar-none">
          <div className="flex items-center gap-2 shrink-0">
            <Eye className="h-3.5 w-3.5 text-blue-400" />
            <span className="text-xs text-white/40">Views</span>
            <span className="text-sm font-semibold text-white">{accessStats.totalAccesses.toLocaleString()}</span>
          </div>
          <div className="w-px h-4 bg-white/10 shrink-0" />
          <div className="flex items-center gap-2 shrink-0">
            <Zap className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-xs text-white/40">Top</span>
            <span className="text-sm font-medium text-white">
              {accessStats.mostAccessed ? `${accessStats.mostAccessed.access_count}x` : 'N/A'}
            </span>
          </div>
          <div className="w-px h-4 bg-white/10 shrink-0" />
          <div className="flex items-center gap-2 shrink-0">
            <Clock className="h-3.5 w-3.5 text-gray-400" />
            <span className="text-xs text-white/40">Unused</span>
            <span className="text-sm font-semibold text-white">{accessStats.neverAccessed}</span>
            <span className="text-xs text-white/30">
              ({filteredMemories.length > 0 ? `${((accessStats.neverAccessed / filteredMemories.length) * 100).toFixed(0)}%` : '0%'})
            </span>
          </div>
          <div className="w-px h-4 bg-white/10 shrink-0" />
          <div className="flex items-center gap-2 shrink-0">
            <TrendingUp className="h-3.5 w-3.5 text-purple-400" />
            <span className="text-xs text-white/40">Avg</span>
            <span className="text-sm font-semibold text-white">{accessStats.avgAccess.toFixed(1)}</span>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30" />
            <Input
              placeholder="Search memories..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-[#0f0f0f] border-white/[0.08] text-white placeholder:text-white/30 focus:border-blue-500/50 h-9"
            />
          </div>
          <Select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="w-36 bg-[#0f0f0f] border-white/[0.08] text-white h-9"
          >
            <option value="">All Types</option>
            {Object.values(MemoryType).map((type) => (
              <option key={type} value={type}>{type}</option>
            ))}
          </Select>
          <Select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'created' | 'accessed' | 'count')}
            className="w-44 bg-[#0f0f0f] border-white/[0.08] text-white h-9"
          >
            <option value="created">Sort by Created</option>
            <option value="accessed">Sort by Accessed</option>
            <option value="count">Sort by Views</option>
          </Select>
          <Select
            value={accessFilter}
            onChange={(e) => setAccessFilter(e.target.value as 'all' | 'never' | 'recent')}
            className="w-44 bg-[#0f0f0f] border-white/[0.08] text-white h-9"
          >
            <option value="all">All Memories</option>
            <option value="never">Never Accessed</option>
            <option value="recent">Recent (24h)</option>
          </Select>
          <div className="flex gap-1.5">
            <Button
              variant="outline"
              size="sm"
              className="bg-[#0f0f0f] border-white/[0.08] text-white/70 hover:bg-white/5 hover:border-purple-500/30 h-9 px-3"
              onClick={() => exportToCSV(filteredMemories)}
              disabled={!filteredMemories.length}
            >
              <Download className="h-3.5 w-3.5 mr-1.5" />CSV
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="bg-[#0f0f0f] border-white/[0.08] text-white/70 hover:bg-white/5 hover:border-purple-500/30 h-9 px-3"
              onClick={() => exportToJSON(filteredMemories)}
              disabled={!filteredMemories.length}
            >
              <Download className="h-3.5 w-3.5 mr-1.5" />JSON
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="bg-[#0f0f0f] border-white/[0.08] text-white/70 hover:bg-white/5 hover:border-purple-500/30 h-9 px-3"
              onClick={() => exportToMarkdown(filteredMemories)}
              disabled={!filteredMemories.length}
            >
              <FileText className="h-3.5 w-3.5 mr-1.5" />MD
            </Button>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleSelectAll}
            className="text-white/50 hover:text-white h-9"
          >
            {selectedIds.size === filteredMemories.length && filteredMemories.length > 0
              ? <CheckSquare className="h-4 w-4" />
              : <Square className="h-4 w-4" />
            }
            <span className="ml-1.5 text-xs">Select all</span>
          </Button>
        </div>

        {/* Bulk Action Toolbar */}
        {selectedIds.size > 0 && (
          <div className="sticky top-0 z-10 flex items-center gap-3 p-3 bg-purple-500/10 border border-purple-500/30 rounded-xl backdrop-blur-sm">
            <span className="text-sm font-medium text-purple-300">
              {selectedIds.size} selected
            </span>
            <div className="flex gap-2 ml-auto flex-wrap">
              <Button size="sm" variant="outline" onClick={() => bulkMutation.mutate({ op: 'archive', ids: [...selectedIds] })} disabled={bulkMutation.isPending} className="bg-transparent border-purple-500/30 text-purple-400 hover:bg-purple-500/10">
                <Archive className="h-3.5 w-3.5 mr-1.5" />Archive
              </Button>
              <Button size="sm" variant="outline" onClick={() => bulkMutation.mutate({ op: 'pin', ids: [...selectedIds] })} disabled={bulkMutation.isPending} className="bg-transparent border-amber-500/30 text-amber-400 hover:bg-amber-500/10">
                <Pin className="h-3.5 w-3.5 mr-1.5" />Pin
              </Button>
              <Button size="sm" variant="outline" onClick={() => bulkMutation.mutate({ op: 'reinforce', ids: [...selectedIds] })} disabled={bulkMutation.isPending} className="bg-transparent border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10">
                <Zap className="h-3.5 w-3.5 mr-1.5" />Reinforce
              </Button>
              <Button size="sm" variant="outline" onClick={() => { if (confirm(`Delete ${selectedIds.size} memories permanently?`)) bulkMutation.mutate({ op: 'delete', ids: [...selectedIds] }); }} disabled={bulkMutation.isPending} className="bg-transparent border-rose-500/30 text-rose-400 hover:bg-rose-500/10">
                <Trash2 className="h-3.5 w-3.5 mr-1.5" />Delete
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setSelectedIds(new Set())} className="text-white/50 hover:text-white">
                Clear
              </Button>
            </div>
          </div>
        )}

        {/* Memory Cards Grid */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex items-center gap-3">
              <div className="h-6 w-6 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" />
              <span className="text-white/50">Loading memories...</span>
            </div>
          </div>
        ) : filteredMemories.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Database className="h-12 w-12 mb-3 text-white/20" />
            <p className="text-white/30">No memories found</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {filteredMemories.map((memory) => {
              const memoryState = (memory as any).state || 'episodic';
              const qualityScore = (memory as any).quality_score || 0;
              const isSelected = selectedIds.has(memory.id);

              return (
                <div
                  key={memory.id}
                  className={`
                    group relative rounded-xl overflow-hidden transition-all duration-200
                    bg-[#111111] border
                    ${isSelected
                      ? 'border-purple-500/40 shadow-lg shadow-purple-500/10 ring-1 ring-purple-500/20'
                      : 'border-white/[0.08] hover:border-white/[0.15]'
                    }
                    hover:shadow-xl ${TYPE_HOVER_GLOW[memory.type] || 'hover:shadow-white/5'}
                    hover:-translate-y-0.5
                  `}
                >
                  {/* Type accent strip */}
                  <div className={`h-1 w-full ${TYPE_ACCENT[memory.type] || 'bg-gray-500'}`} />

                  <div className="p-4 space-y-3">
                    {/* Header: badges + quality circle */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <MemoryTypeBadge type={memory.type} />
                        <StateBadge state={memoryState} size="sm" />
                        {memory.pinned && (
                          <Pin className="h-3 w-3 text-amber-400 shrink-0" />
                        )}
                      </div>
                      <QualityProgress score={qualityScore} size={32} showLabel={false} />
                    </div>

                    {/* Content - click to open detail panel */}
                    <p
                      className="text-sm text-white/80 leading-relaxed line-clamp-3 cursor-pointer hover:text-white transition-colors"
                      onClick={() => setDetailPanelId(memory.id)}
                    >
                      {memory.content}
                    </p>

                    {/* Tags */}
                    {memory.tags?.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {memory.tags.slice(0, 5).map((tag) => (
                          <span
                            key={tag}
                            className="text-[11px] px-2 py-0.5 rounded-full bg-purple-500/[0.08] text-purple-300/70 border border-purple-500/[0.12] leading-tight"
                          >
                            {tag}
                          </span>
                        ))}
                        {memory.tags.length > 5 && (
                          <span className="text-[11px] px-2 py-0.5 rounded-full bg-white/[0.04] text-white/30 border border-white/[0.06] leading-tight">
                            +{memory.tags.length - 5}
                          </span>
                        )}
                      </div>
                    )}

                    {/* Footer: meta + hover actions */}
                    <div className="flex items-center justify-between pt-2.5 border-t border-white/[0.04]">
                      <div className="flex items-center gap-1.5 text-[11px] text-white/40 min-w-0 overflow-hidden">
                        {memory.project && (
                          <>
                            <span className="text-blue-400/60 truncate max-w-[80px]">{memory.project}</span>
                            <span className="text-white/10">&middot;</span>
                          </>
                        )}
                        <span className="shrink-0">
                          {formatDistanceToNow(new Date(memory.created_at), { addSuffix: true })}
                        </span>
                        {memory.access_count > 0 && (
                          <>
                            <span className="text-white/10">&middot;</span>
                            <span className="shrink-0 tabular-nums">{memory.access_count}x</span>
                          </>
                        )}
                      </div>
                      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleEdit(memory); }}
                          className="p-1.5 rounded-lg hover:bg-white/[0.06] text-white/40 hover:text-blue-400 transition-colors"
                          title="Edit"
                        >
                          <Edit className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); pinMemory.mutate(memory.id); }}
                          className="p-1.5 rounded-lg hover:bg-white/[0.06] text-white/40 hover:text-amber-400 transition-colors"
                          title={memory.pinned ? 'Unpin' : 'Pin'}
                        >
                          <Pin className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); archiveMemory.mutate(memory.id); }}
                          className="p-1.5 rounded-lg hover:bg-white/[0.06] text-white/40 hover:text-purple-400 transition-colors"
                          title="Archive"
                        >
                          <Archive className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDelete(memory.id); }}
                          className="p-1.5 rounded-lg hover:bg-white/[0.06] text-white/40 hover:text-rose-400 transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Selection checkbox - top-left overlay */}
                  <div
                    className={`absolute top-3 left-3 z-10 ${
                      isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                    } transition-opacity duration-150`}
                  >
                    <button
                      onClick={(e) => { e.stopPropagation(); toggleSelect(memory.id); }}
                      className="p-0.5 rounded bg-black/60 backdrop-blur-sm"
                    >
                      {isSelected
                        ? <CheckSquare className="h-4 w-4 text-purple-400" />
                        : <Square className="h-4 w-4 text-white/40 hover:text-white/70" />
                      }
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-white/50">
            {total > 0
              ? `Showing ${page * limit + 1}\u2013${Math.min((page + 1) * limit, total)} of ${total}`
              : 'No memories'}
          </p>
          <div className="flex items-center gap-3">
            <span className="text-sm text-white/40">
              Page {page + 1} of {totalPages}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="bg-[#0f0f0f] border-white/10 text-white/90 hover:bg-white/5 hover:border-blue-500/50"
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                className="bg-[#0f0f0f] border-white/10 text-white/90 hover:bg-white/5 hover:border-blue-500/50"
                onClick={() => setPage(page + 1)}
                disabled={(page + 1) >= totalPages}
              >
                Next
              </Button>
            </div>
          </div>
        </div>

        {/* Bottom Sections */}
        <ForgettingCurveSection />
        <QualityLeaderboardSection />
      </div>

      <MemoryDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        memory={selectedMemory}
      />

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

// --- Forgetting Curve Section ---

function ForgettingCurveSection() {
  const { data: stats } = useForgettingStats();
  const { data: weakMemories } = useWeakMemories(0.3, 20);
  const reinforce = useReinforceMemory();

  return (
    <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl">
      <CardHeader>
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-400" />
          <CardTitle className="text-white">Forgetting Curve</CardTitle>
        </div>
        <CardDescription className="text-white/60">Weak memories needing reinforcement</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
              <p className="text-xs text-white/50">Total</p>
              <p className="text-lg font-bold text-white">{stats.total_memories}</p>
            </div>
            <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
              <p className="text-xs text-white/50">Avg Strength</p>
              <p className="text-lg font-bold text-white">{((stats.avg_strength ?? 0) * 100).toFixed(0)}%</p>
            </div>
            <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
              <p className="text-xs text-white/50">Weak</p>
              <p className="text-lg font-bold text-amber-400">{stats.weak_count}</p>
            </div>
            <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
              <p className="text-xs text-white/50">Decay</p>
              <p className="text-lg font-bold text-white">{(stats.decay_rate ?? 0).toFixed(3)}</p>
            </div>
          </div>
        )}
        <div className="space-y-2 max-h-[300px] overflow-y-auto">
          {weakMemories?.map((memory) => (
            <div key={memory.id} className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5">
              <div className="flex-1 min-w-0 mr-3">
                <div className="flex items-center gap-2 mb-1">
                  <Badge className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs">{memory.type}</Badge>
                  <div className="w-16 h-2 bg-white/10 rounded-full overflow-hidden">
                    <div className="h-full bg-amber-500 rounded-full" style={{ width: `${memory.strength * 100}%` }} />
                  </div>
                  <span className="text-xs text-white/40">{((memory.strength ?? 0) * 100).toFixed(0)}%</span>
                </div>
                <p className="text-sm text-white/70 line-clamp-1">{memory.content}</p>
              </div>
              <Button size="sm" onClick={() => reinforce.mutate({ id: memory.id, boostAmount: 0.2 })} disabled={reinforce.isPending}
                className="bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30 shrink-0">
                <Zap className="h-3 w-3 mr-1" /> Reinforce
              </Button>
            </div>
          ))}
          {(!weakMemories || weakMemories.length === 0) && (
            <p className="text-white/50 text-center py-4">No weak memories found</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// --- Quality Leaderboard Section ---

function QualityLeaderboardSection() {
  const { data: leaderboard } = useQualityLeaderboard(20);
  const { data: report } = useQualityReport();

  return (
    <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Award className="h-5 w-5 text-yellow-400" />
          <CardTitle className="text-white">Quality Leaderboard</CardTitle>
        </div>
        <CardDescription className="text-white/60">Top-rated memories by quality</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {report && (
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
              <p className="text-xs text-white/50">Avg Quality</p>
              <p className="text-lg font-bold text-white">{((report.avg_quality ?? 0) * 100).toFixed(0)}%</p>
            </div>
            <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
              <p className="text-xs text-white/50">Total</p>
              <p className="text-lg font-bold text-white">{report.total_memories}</p>
            </div>
            <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5 text-center">
              <p className="text-xs text-white/50">Issues</p>
              <p className="text-lg font-bold text-amber-400">{report.top_issues?.length ?? 0}</p>
            </div>
          </div>
        )}
        <div className="space-y-2 max-h-[300px] overflow-y-auto">
          {leaderboard?.map((entry, i) => (
            <div key={entry.id} className="flex items-center gap-3 p-3 rounded-lg bg-[#0a0a0a] border border-white/5">
              <span className={`text-lg font-bold w-8 text-center ${
                i === 0 ? 'text-yellow-400' : i === 1 ? 'text-gray-300' : i === 2 ? 'text-amber-600' : 'text-white/30'
              }`}>{i + 1}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Badge className="bg-blue-500/20 text-blue-300 border border-blue-500/30 text-xs">{entry.type}</Badge>
                  <QualityProgress score={entry.quality_score} size={24} showLabel={false} />
                </div>
                <p className="text-sm text-white/70 line-clamp-1">{entry.content}</p>
              </div>
              <span className="text-xs text-white/40 shrink-0">{entry.access_count} views</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
