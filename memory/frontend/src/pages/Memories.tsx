import { useState, useRef, useMemo } from 'react';
// import { useVirtualizer } from '@tanstack/react-virtual';
import { useMemories, useDeleteMemory, usePinMemory, useArchiveMemory, useReinforceMemory, useDraftMemory, useBulkStore, useForgettingStats, useWeakMemories, useQualityLeaderboard, useQualityReport } from '../hooks/useMemories';
import { useQualityTrend } from '../hooks/useQuality';
import { useStateHistory } from '../hooks/useLifecycle';
import { useAuditTrail } from '../hooks/useAudit';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Plus, Trash2, Pin, Archive, Edit, Search, Download, FileText, Database, Eye, Clock, TrendingUp, Zap, ChevronDown, ChevronRight, Upload, Award, AlertTriangle, BarChart3 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { Memory, MemoryType } from '../types/memory';
import { MemoryDialog } from '../components/memory/MemoryDialog';
import { MemoryTypeBadge } from '../components/memory/MemoryTypeBadge';
import { QualityBadge } from '../components/QualityBadge';
import { StateBadge, StateTimeline } from '../components/StateBadge';
import { AuditTimeline } from '../components/AuditTimeline';
import { exportToCSV, exportToJSON, exportToMarkdown } from '../utils/export';

export function Memories() {
  const [page, setPage] = useState(0);
  const [limit] = useState(50);
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'created' | 'accessed' | 'count'>('created');
  const [accessFilter, setAccessFilter] = useState<'all' | 'never' | 'recent'>('all');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedMemory, setSelectedMemory] = useState<Memory | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [expandedTab, setExpandedTab] = useState<Record<string, 'audit' | 'state' | 'quality'>>({});
  const tableContainerRef = useRef<HTMLDivElement>(null);

  const toggleRowExpansion = (memoryId: string) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(memoryId)) {
        next.delete(memoryId);
      } else {
        next.add(memoryId);
        if (!expandedTab[memoryId]) {
          setExpandedTab(prev => ({ ...prev, [memoryId]: 'audit' }));
        }
      }
      return next;
    });
  };

  const { data: memories, isLoading } = useMemories({
    type: typeFilter || undefined,
    limit,
    offset: page * limit,
  });

  const deleteMemory = useDeleteMemory();
  const pinMemory = usePinMemory();
  const archiveMemory = useArchiveMemory();

  const filteredMemories = useMemo(() => {
    let filtered = memories?.filter((m: Memory) =>
      !searchQuery || m.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.tags?.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
    ) || [];

    // Apply access filter
    if (accessFilter === 'never') {
      filtered = filtered.filter(m => m.access_count === 0);
    } else if (accessFilter === 'recent') {
      const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
      filtered = filtered.filter(m => new Date(m.last_accessed) > oneDayAgo);
    }

    // Sort memories
    filtered.sort((a, b) => {
      if (sortBy === 'count') {
        return b.access_count - a.access_count;
      } else if (sortBy === 'accessed') {
        return new Date(b.last_accessed).getTime() - new Date(a.last_accessed).getTime();
      } else {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });

    return filtered;
  }, [memories, searchQuery, accessFilter, sortBy]);

  // Calculate access statistics
  const accessStats = useMemo(() => {
    if (!filteredMemories.length) {
      return {
        totalAccesses: 0,
        mostAccessed: null,
        neverAccessed: 0,
        avgAccess: 0,
      };
    }

    const totalAccesses = filteredMemories.reduce((sum, m) => sum + m.access_count, 0);
    const neverAccessed = filteredMemories.filter(m => m.access_count === 0).length;
    const avgAccess = totalAccesses / filteredMemories.length;
    const mostAccessed = filteredMemories.reduce((max, m) =>
      m.access_count > (max?.access_count || 0) ? m : max
    , filteredMemories[0]);

    return {
      totalAccesses,
      mostAccessed,
      neverAccessed,
      avgAccess,
    };
  }, [filteredMemories]);

  // Temporarily disabled virtual scrolling due to missing dependency
  // const rowVirtualizer = useVirtualizer({
  //   count: filteredMemories.length,
  //   getScrollElement: () => tableContainerRef.current,
  //   estimateSize: () => 80,
  //   overscan: 5,
  // });

  // Get access count badge style
  const getAccessBadgeStyle = (count: number) => {
    if (count === 0) {
      return 'bg-gray-500/10 text-gray-400 border-gray-500/20';
    } else if (count <= 5) {
      return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    } else if (count <= 20) {
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    } else {
      return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    }
  };

  const getAccessIcon = (count: number) => {
    if (count === 0) return '💤';
    if (count <= 5) return '🔹';
    if (count <= 20) return '✅';
    return '🔥';
  };

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
      <div className="p-6 sm:p-8 max-w-[1800px] mx-auto space-y-6">
        {/* Hero Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-500/10 via-purple-500/10 to-emerald-500/10 p-6 border border-white/5">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-purple-500/5" />
          <div className="relative flex items-center gap-4">
            <div className="p-3 bg-blue-500/10 rounded-xl ring-1 ring-blue-500/20">
              <Database className="h-8 w-8 text-blue-400" />
            </div>
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-white">Memory Management</h1>
              <p className="text-white/60 mt-1">
                {filteredMemories.length} memories
                {typeFilter && ` • Filtered by ${typeFilter}`}
              </p>
            </div>
          </div>
        </div>

        {/* Access Statistics Panel */}
        <Card className="bg-[#0f0f0f] border-white/10">
          <CardHeader className="border-b border-white/5">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-purple-400" />
              <CardTitle className="text-white">Access Statistics</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="p-4 rounded-lg bg-gradient-to-br from-blue-500/10 to-blue-500/5 border border-blue-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <Eye className="h-4 w-4 text-blue-400" />
                  <p className="text-sm text-white/70">Total Accesses</p>
                </div>
                <p className="text-3xl font-bold text-white">{accessStats.totalAccesses.toLocaleString()}</p>
              </div>
              <div className="p-4 rounded-lg bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border border-emerald-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="h-4 w-4 text-emerald-400" />
                  <p className="text-sm text-white/70">Most Accessed</p>
                </div>
                <p className="text-lg font-medium text-white truncate">
                  {accessStats.mostAccessed ? `${accessStats.mostAccessed.content.substring(0, 30)}...` : 'N/A'}
                </p>
                <p className="text-xs text-white/50 mt-1">
                  {accessStats.mostAccessed ? `${accessStats.mostAccessed.access_count}x` : ''}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-gradient-to-br from-gray-500/10 to-gray-500/5 border border-gray-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="h-4 w-4 text-gray-400" />
                  <p className="text-sm text-white/70">Never Accessed</p>
                </div>
                <p className="text-3xl font-bold text-white">{accessStats.neverAccessed}</p>
                <p className="text-xs text-white/50 mt-1">
                  {filteredMemories.length > 0 ? `${((accessStats.neverAccessed / filteredMemories.length) * 100).toFixed(1)}%` : '0%'}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-gradient-to-br from-purple-500/10 to-purple-500/5 border border-purple-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="h-4 w-4 text-purple-400" />
                  <p className="text-sm text-white/70">Avg Accesses</p>
                </div>
                <p className="text-3xl font-bold text-white">{accessStats.avgAccess.toFixed(1)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Filters and Actions */}
        <Card className="bg-[#0f0f0f] border-white/10">
          <CardHeader className="border-b border-white/5">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <CardTitle className="text-white">Filters & Export</CardTitle>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  className="bg-[#0a0a0a] border-white/10 text-white/90 hover:bg-white/5 hover:border-purple-500/50"
                  onClick={() => exportToCSV(filteredMemories)}
                  disabled={filteredMemories.length === 0}
                >
                  <Download className="mr-2 h-4 w-4" />
                  CSV
                </Button>
                <Button
                  variant="outline"
                  className="bg-[#0a0a0a] border-white/10 text-white/90 hover:bg-white/5 hover:border-purple-500/50"
                  onClick={() => exportToJSON(filteredMemories)}
                  disabled={filteredMemories.length === 0}
                >
                  <Download className="mr-2 h-4 w-4" />
                  JSON
                </Button>
                <Button
                  variant="outline"
                  className="bg-[#0a0a0a] border-white/10 text-white/90 hover:bg-white/5 hover:border-purple-500/50"
                  onClick={() => exportToMarkdown(filteredMemories)}
                  disabled={filteredMemories.length === 0}
                >
                  <FileText className="mr-2 h-4 w-4" />
                  MD
                </Button>
                <Button
                  onClick={handleCreate}
                  className="bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white border-0"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Create Memory
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="flex gap-4 flex-wrap">
              <div className="flex-1 min-w-[200px] relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-white/30" />
                <Input
                  placeholder="Search memories..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-[#0a0a0a] border-white/10 text-white placeholder:text-white/30 focus:border-blue-500/50"
                />
              </div>
              <Select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="w-40 bg-[#0a0a0a] border-white/10 text-white"
              >
                <option value="">All Types</option>
                {Object.values(MemoryType).map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </Select>
              <Select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'created' | 'accessed' | 'count')}
                className="w-48 bg-[#0a0a0a] border-white/10 text-white"
              >
                <option value="created">Sort by Created</option>
                <option value="accessed">Sort by Last Accessed</option>
                <option value="count">Sort by Access Count</option>
              </Select>
              <Select
                value={accessFilter}
                onChange={(e) => setAccessFilter(e.target.value as 'all' | 'never' | 'recent')}
                className="w-48 bg-[#0a0a0a] border-white/10 text-white"
              >
                <option value="all">All Memories</option>
                <option value="never">Never Accessed</option>
                <option value="recent">Recently Accessed (24h)</option>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Memories Table */}
        <Card className="bg-[#0f0f0f] border-white/10 overflow-hidden">
          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-8 text-center">
                <div className="inline-flex items-center gap-3">
                  <div className="h-6 w-6 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" />
                  <span className="text-white/50">Loading memories...</span>
                </div>
              </div>
            ) : filteredMemories.length === 0 ? (
              <div className="p-8 text-center">
                <Database className="h-12 w-12 mx-auto mb-3 text-white/20" />
                <p className="text-white/30">No memories found</p>
              </div>
            ) : (
              <div ref={tableContainerRef} className="overflow-x-auto max-h-[600px] overflow-y-auto">
                <Table className="min-w-full">
                <TableHeader>
                  <TableRow className="border-b border-white/5 hover:bg-transparent">
                    <TableHead className="w-8"></TableHead>
                    <TableHead className="text-white/70">Type</TableHead>
                    <TableHead className="text-white/70">State</TableHead>
                    <TableHead className="text-white/70">Quality</TableHead>
                    <TableHead className="text-white/70">Content</TableHead>
                    <TableHead className="text-white/70">Tags</TableHead>
                    <TableHead className="text-white/70">Project</TableHead>
                    <TableHead className="text-white/70">Created</TableHead>
                    <TableHead className="text-white/70">Score</TableHead>
                    <TableHead className="text-white/70">Accesses</TableHead>
                    <TableHead className="text-white/70">Last Accessed</TableHead>
                    <TableHead className="text-right text-white/70">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredMemories.map((memory) => {
                    const isExpanded = expandedRows.has(memory.id);
                    const activeTab = expandedTab[memory.id] || 'audit';
                    // Assuming memory has state and quality_score fields from backend
                    const memoryState = (memory as any).state || 'episodic';
                    const qualityScore = (memory as any).quality_score || 0;

                    return (
                      <>
                        <TableRow
                          key={memory.id}
                          className="border-b border-white/5 hover:bg-white/5 transition-colors"
                        >
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => toggleRowExpansion(memory.id)}
                              className="h-6 w-6 text-white/50 hover:text-white/90"
                            >
                              {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                            </Button>
                          </TableCell>
                          <TableCell>
                            <MemoryTypeBadge type={memory.type} />
                          </TableCell>
                          <TableCell>
                            <StateBadge state={memoryState} size="sm" />
                          </TableCell>
                          <TableCell>
                            <QualityBadge score={qualityScore} size="sm" showScore={false} />
                          </TableCell>
                          <TableCell className="max-w-md">
                            <div className="line-clamp-2 text-white/90">
                              {memory.pinned && <Pin className="inline h-3 w-3 mr-1 text-amber-400" />}
                              {memory.content}
                            </div>
                          </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {memory.tags?.slice(0, 3).map((tag) => (
                            <Badge key={tag} className="text-xs bg-purple-500/10 text-purple-400 border-purple-500/20">
                              {tag}
                            </Badge>
                          ))}
                          {memory.tags?.length > 3 && (
                            <Badge className="text-xs bg-white/5 text-white/50 border-white/10">
                              +{(memory.tags?.length ?? 0) - 3}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-white/70">{memory.project || '-'}</TableCell>
                      <TableCell className="text-sm text-white/50">
                        {formatDistanceToNow(new Date(memory.created_at), { addSuffix: true })}
                      </TableCell>
                      <TableCell>
                        <span className="text-sm font-medium text-white/90">
                          {(memory.importance_score ?? 0).toFixed(2)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge className={`text-xs ${getAccessBadgeStyle(memory.access_count)}`}>
                          {getAccessIcon(memory.access_count)} {memory.access_count}x
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-white/50">
                        {memory.access_count === 0
                          ? 'Never'
                          : formatDistanceToNow(new Date(memory.last_accessed), { addSuffix: true })}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(memory)}
                            className="hover:bg-white/10 text-white/70 hover:text-blue-400"
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => pinMemory.mutate(memory.id)}
                            disabled={pinMemory.isPending}
                            className="hover:bg-white/10 text-white/70 hover:text-amber-400"
                          >
                            <Pin className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => archiveMemory.mutate(memory.id)}
                            disabled={archiveMemory.isPending}
                            className="hover:bg-white/10 text-white/70 hover:text-purple-400"
                          >
                            <Archive className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(memory.id)}
                            disabled={deleteMemory.isPending}
                            className="hover:bg-white/10 text-white/70 hover:text-rose-400"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                          </TableCell>
                        </TableRow>

                        {/* Expandable Row Details */}
                        {isExpanded && (
                          <TableRow key={`${memory.id}-expanded`} className="border-b border-white/5">
                            <TableCell colSpan={12} className="bg-[#0a0a0a]/50">
                              <div className="p-4 space-y-4">
                                {/* Tabs */}
                                <div className="flex gap-2 border-b border-white/10 pb-2">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setExpandedTab(prev => ({ ...prev, [memory.id]: 'audit' }))}
                                    className={activeTab === 'audit' ? 'bg-white/10 text-white' : 'text-white/50'}
                                  >
                                    Audit History
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setExpandedTab(prev => ({ ...prev, [memory.id]: 'state' }))}
                                    className={activeTab === 'state' ? 'bg-white/10 text-white' : 'text-white/50'}
                                  >
                                    State History
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setExpandedTab(prev => ({ ...prev, [memory.id]: 'quality' }))}
                                    className={activeTab === 'quality' ? 'bg-white/10 text-white' : 'text-white/50'}
                                  >
                                    Quality Trend
                                  </Button>
                                </div>

                                {/* Tab Content */}
                                {activeTab === 'audit' && (
                                  <ExpandedAuditTab memoryId={memory.id} />
                                )}
                                {activeTab === 'state' && (
                                  <ExpandedStateTab memoryId={memory.id} />
                                )}
                                {activeTab === 'quality' && (
                                  <ExpandedQualityTab memoryId={memory.id} />
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </>
                    );
                  })}
                </TableBody>
              </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pagination */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-white/50">
            Showing {page * limit + 1} to {Math.min((page + 1) * limit, filteredMemories.length)} of {filteredMemories.length}
          </p>
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
              disabled={filteredMemories.length < limit}
            >
              Next
            </Button>
          </div>
        </div>

        {/* Forgetting Curve & Quality Sections */}
        <ForgettingCurveSection />
        <QualityLeaderboardSection />
      </div>

      <MemoryDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        memory={selectedMemory}
      />
    </div>
  );
}

// Helper Components for Expandable Tabs

function ExpandedAuditTab({ memoryId }: { memoryId: string }) {
  return (
    <div className="max-h-[400px] overflow-y-auto">
      <AuditTimeline memoryId={memoryId} limit={5} />
    </div>
  );
}

function ExpandedStateTab({ memoryId }: { memoryId: string }) {
  const { data: stateHistory, isLoading } = useStateHistory(memoryId);

  if (isLoading) {
    return <div className="text-center py-4 text-white/50">Loading state history...</div>;
  }

  if (!stateHistory?.transitions?.length) {
    return <div className="text-center py-4 text-white/50">No state transitions recorded</div>;
  }

  return (
    <div className="max-h-[400px] overflow-y-auto">
      <StateTimeline transitions={stateHistory.transitions} />
    </div>
  );
}

function ExpandedQualityTab({ memoryId }: { memoryId: string }) {
  const { data: qualityTrend, isLoading } = useQualityTrend(memoryId);

  if (isLoading) {
    return <div className="text-center py-4 text-white/50">Loading quality trend...</div>;
  }

  if (!qualityTrend?.trend_data?.length) {
    return <div className="text-center py-4 text-white/50">No quality trend data available</div>;
  }

  return (
    <div className="max-h-[400px] overflow-y-auto space-y-3">
      {qualityTrend.trend_data.map((entry, index) => (
        <div key={index} className="flex items-start gap-3 p-3 bg-white/5 rounded-lg">
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-white">
                Quality: {((entry.quality_score ?? 0) * 100).toFixed(1)}%
              </span>
              <span className="text-xs text-white/50">
                {new Date(entry.timestamp).toLocaleString()}
              </span>
            </div>
            <p className="text-xs text-white/70">{entry.reason}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// --- New Memory Feature Sections ---

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
          <div className="grid grid-cols-4 gap-3">
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
                className="bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30">
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
                  <QualityBadge score={entry.quality_score * 100} size="sm" />
                </div>
                <p className="text-sm text-white/70 line-clamp-1">{entry.content}</p>
              </div>
              <span className="text-xs text-white/40">{entry.access_count} views</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
