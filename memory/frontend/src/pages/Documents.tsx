import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Label } from '../components/ui/label';
import { apiClient } from '../lib/api';
import type { AxiosResponse } from 'axios';
import { FileText, Search, Folder, FolderOpen, Trash2, BookOpen, Eye, Clock, TrendingUp, Zap } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface DocumentResult {
  id: string;
  score: number;
  file_path: string;
  file_type: string;
  folder: string;
  content: string;
  chunk_index: number;
  total_chunks: number;
  modified_at: string | null;
  access_count: number;
  last_accessed: string | null;
}

interface DocumentStats {
  collection: string;
  total_chunks: number;
  status: string;
  total_accesses: number;
  never_accessed: number;
  avg_access: number;
  most_accessed_file: string | null;
  max_access_count: number;
}

export default function Documents() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<DocumentResult[]>([]);
  const [searching, setSearching] = useState(false);

  // Get document stats (now includes access metrics)
  const { data: stats } = useQuery<DocumentStats>({
    queryKey: ['documents', 'stats'],
    queryFn: () => apiClient.get('/documents/stats').then((r: AxiosResponse) => r.data),
  });

  // Search mutation
  const searchMutation = useMutation({
    mutationFn: (query: string) =>
      apiClient.post('/documents/search', null, {
        params: { query, limit: 20 },
      }),
    onSuccess: (response: AxiosResponse) => {
      setResults(response.data.results || []);
      setSearching(false);
      // Refetch stats to get updated access counts
      queryClient.invalidateQueries({ queryKey: ['documents', 'stats'] });
    },
    onError: () => {
      setSearching(false);
    },
  });

  const handleSearch = () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    searchMutation.mutate(searchQuery);
  };

  // Get access badge style based on count
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

  // Group results by file path and get most accessed
  const popularDocuments = useMemo(() => {
    const fileMap = new Map<string, DocumentResult>();

    results.forEach(doc => {
      const existing = fileMap.get(doc.file_path);
      if (!existing || doc.access_count > existing.access_count) {
        fileMap.set(doc.file_path, doc);
      }
    });

    return Array.from(fileMap.values())
      .sort((a, b) => b.access_count - a.access_count)
      .slice(0, 5);
  }, [results]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]">
      <div className="p-6 sm:p-8 max-w-[1800px] mx-auto space-y-6">
        {/* Hero Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-amber-500/10 via-orange-500/10 to-rose-500/10 p-6 border border-white/5">
          <div className="absolute inset-0 bg-gradient-to-br from-amber-500/5 via-transparent to-rose-500/5" />
          <div className="relative flex items-center gap-4">
            <div className="p-3 bg-amber-500/10 rounded-xl ring-1 ring-amber-500/20">
              <BookOpen className="h-8 w-8 text-amber-400" />
            </div>
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-white">Documents</h1>
              <p className="text-white/60 mt-1">
                Search indexed files from your filesystem. Documents are separate from memories.
              </p>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="bg-[#0f0f0f] border-white/10">
            <CardHeader className="border-b border-white/5">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-blue-400" />
                <CardTitle className="text-white">Document Collection</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
                  <p className="text-sm text-white/50 mb-1">Total Chunks</p>
                  <p className="text-3xl font-bold text-white">{stats?.total_chunks || 0}</p>
                </div>
                <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
                  <p className="text-sm text-white/50 mb-1">Collection</p>
                  <p className="text-lg font-medium text-white">{stats?.collection || 'documents'}</p>
                </div>
                <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
                  <p className="text-sm text-white/50 mb-1">Status</p>
                  <Badge
                    className={
                      stats?.status === 'green'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-white/5 text-white/50 border-white/10'
                    }
                  >
                    {stats?.status || 'unknown'}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-[#0f0f0f] border-white/10">
            <CardHeader className="border-b border-white/5">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-purple-400" />
                <CardTitle className="text-white">Access Statistics</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-4 rounded-lg bg-gradient-to-br from-blue-500/10 to-blue-500/5 border border-blue-500/20">
                  <div className="flex items-center gap-2 mb-2">
                    <Eye className="h-4 w-4 text-blue-400" />
                    <p className="text-xs text-white/70">Total</p>
                  </div>
                  <p className="text-2xl font-bold text-white">{stats?.total_accesses?.toLocaleString() || 0}</p>
                </div>
                <div className="p-4 rounded-lg bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border border-emerald-500/20">
                  <div className="flex items-center gap-2 mb-2">
                    <Zap className="h-4 w-4 text-emerald-400" />
                    <p className="text-xs text-white/70">Most</p>
                  </div>
                  <p className="text-lg font-bold text-white">{stats?.max_access_count || 0}x</p>
                </div>
                <div className="p-4 rounded-lg bg-gradient-to-br from-gray-500/10 to-gray-500/5 border border-gray-500/20">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="h-4 w-4 text-gray-400" />
                    <p className="text-xs text-white/70">Never</p>
                  </div>
                  <p className="text-2xl font-bold text-white">{stats?.never_accessed || 0}</p>
                </div>
                <div className="p-4 rounded-lg bg-gradient-to-br from-purple-500/10 to-purple-500/5 border border-purple-500/20">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp className="h-4 w-4 text-purple-400" />
                    <p className="text-xs text-white/70">Avg</p>
                  </div>
                  <p className="text-2xl font-bold text-white">{stats?.avg_access?.toFixed(1) || '0.0'}</p>
                </div>
              </div>
              {stats?.most_accessed_file && (
                <div className="mt-4 p-3 rounded-lg bg-[#0a0a0a] border border-emerald-500/20">
                  <p className="text-xs text-white/50 mb-1">Most Accessed File</p>
                  <p className="text-sm font-mono text-emerald-400 truncate">{stats.most_accessed_file}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Document Quality Metrics */}
        <Card className="bg-[#0f0f0f] border-white/10">
          <CardHeader className="border-b border-white/5">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-amber-400" />
              <CardTitle className="text-white">Document Quality Metrics</CardTitle>
            </div>
            <CardDescription className="text-white/50">
              Health indicators based on document access patterns and coverage
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            {stats && stats.total_chunks > 0 ? (
              <div className="space-y-6">
                {/* Quality Gauges Row */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {/* Coverage Score */}
                  {(() => {
                    const accessedCount = stats.total_chunks - (stats.never_accessed || 0);
                    const coveragePercent = stats.total_chunks > 0
                      ? Math.round((accessedCount / stats.total_chunks) * 100)
                      : 0;
                    return (
                      <div className={`p-5 rounded-xl border ${
                        coveragePercent >= 70
                          ? 'bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border-emerald-500/20'
                          : coveragePercent >= 40
                          ? 'bg-gradient-to-br from-amber-500/10 to-amber-500/5 border-amber-500/20'
                          : 'bg-gradient-to-br from-red-500/10 to-red-500/5 border-red-500/20'
                      }`}>
                        <p className="text-xs font-medium text-white/50 uppercase tracking-wider mb-2">Coverage</p>
                        <div className="flex items-end gap-2 mb-3">
                          <span className={`text-4xl font-bold ${
                            coveragePercent >= 70 ? 'text-emerald-400' : coveragePercent >= 40 ? 'text-amber-400' : 'text-red-400'
                          }`}>{coveragePercent}%</span>
                          <span className="text-xs text-white/40 mb-1">of docs accessed</span>
                        </div>
                        <div className="w-full h-2 bg-[#0a0a0a] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${
                              coveragePercent >= 70 ? 'bg-emerald-500' : coveragePercent >= 40 ? 'bg-amber-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${coveragePercent}%` }}
                          />
                        </div>
                        <p className="text-xs text-white/40 mt-2">{accessedCount} of {stats.total_chunks} chunks used</p>
                      </div>
                    );
                  })()}

                  {/* Engagement Score */}
                  {(() => {
                    const avgAccess = stats.avg_access || 0;
                    const isHigh = avgAccess >= 5;
                    const isMedium = avgAccess >= 1;
                    return (
                      <div className={`p-5 rounded-xl border ${
                        isHigh
                          ? 'bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border-emerald-500/20'
                          : isMedium
                          ? 'bg-gradient-to-br from-amber-500/10 to-amber-500/5 border-amber-500/20'
                          : 'bg-gradient-to-br from-red-500/10 to-red-500/5 border-red-500/20'
                      }`}>
                        <p className="text-xs font-medium text-white/50 uppercase tracking-wider mb-2">Engagement</p>
                        <div className="flex items-end gap-2 mb-3">
                          <span className={`text-4xl font-bold ${
                            isHigh ? 'text-emerald-400' : isMedium ? 'text-amber-400' : 'text-red-400'
                          }`}>{(avgAccess ?? 0).toFixed(1)}</span>
                          <span className="text-xs text-white/40 mb-1">avg accesses/doc</span>
                        </div>
                        <Badge className={
                          isHigh
                            ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                            : isMedium
                            ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                            : 'bg-red-500/20 text-red-300 border-red-500/30'
                        }>
                          {isHigh ? 'High' : isMedium ? 'Medium' : 'Low'} Engagement
                        </Badge>
                        <p className="text-xs text-white/40 mt-2">{stats.total_accesses?.toLocaleString() || 0} total lookups</p>
                      </div>
                    );
                  })()}

                  {/* Stale Content */}
                  {(() => {
                    const stalePercent = stats.total_chunks > 0
                      ? Math.round(((stats.never_accessed || 0) / stats.total_chunks) * 100)
                      : 0;
                    return (
                      <div className={`p-5 rounded-xl border ${
                        stalePercent <= 30
                          ? 'bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border-emerald-500/20'
                          : stalePercent <= 60
                          ? 'bg-gradient-to-br from-amber-500/10 to-amber-500/5 border-amber-500/20'
                          : 'bg-gradient-to-br from-red-500/10 to-red-500/5 border-red-500/20'
                      }`}>
                        <p className="text-xs font-medium text-white/50 uppercase tracking-wider mb-2">Freshness</p>
                        <div className="flex items-end gap-2 mb-3">
                          <span className={`text-4xl font-bold ${
                            stalePercent <= 30 ? 'text-emerald-400' : stalePercent <= 60 ? 'text-amber-400' : 'text-red-400'
                          }`}>{stats.never_accessed || 0}</span>
                          <span className="text-xs text-white/40 mb-1">stale chunks</span>
                        </div>
                        <div className="w-full h-2 bg-[#0a0a0a] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${
                              stalePercent <= 30 ? 'bg-emerald-500' : stalePercent <= 60 ? 'bg-amber-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${100 - stalePercent}%` }}
                          />
                        </div>
                        <p className="text-xs text-white/40 mt-2">{stalePercent}% never accessed</p>
                      </div>
                    );
                  })()}
                </div>

                {/* Overall Health Summary */}
                {(() => {
                  const accessedCount = stats.total_chunks - (stats.never_accessed || 0);
                  const coveragePercent = stats.total_chunks > 0 ? (accessedCount / stats.total_chunks) * 100 : 0;
                  const avgAccess = stats.avg_access || 0;
                  const stalePercent = stats.total_chunks > 0 ? ((stats.never_accessed || 0) / stats.total_chunks) * 100 : 0;
                  const healthScore = Math.round((coveragePercent * 0.4 + Math.min(avgAccess * 10, 100) * 0.3 + (100 - stalePercent) * 0.3));
                  const healthLabel = healthScore >= 70 ? 'Healthy' : healthScore >= 40 ? 'Needs Attention' : 'Underutilized';
                  return (
                    <div className={`p-4 rounded-xl flex items-center justify-between border ${
                      healthScore >= 70
                        ? 'bg-gradient-to-r from-emerald-500/10 via-emerald-500/5 to-transparent border-emerald-500/20'
                        : healthScore >= 40
                        ? 'bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent border-amber-500/20'
                        : 'bg-gradient-to-r from-red-500/10 via-red-500/5 to-transparent border-red-500/20'
                    }`}>
                      <div className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full animate-pulse ${
                          healthScore >= 70 ? 'bg-emerald-500' : healthScore >= 40 ? 'bg-amber-500' : 'bg-red-500'
                        }`} />
                        <div>
                          <p className="text-sm font-medium text-white">
                            Overall Document Health:{' '}
                            <span className={
                              healthScore >= 70 ? 'text-emerald-400' : healthScore >= 40 ? 'text-amber-400' : 'text-red-400'
                            }>{healthLabel}</span>
                          </p>
                          <p className="text-xs text-white/40">Score based on coverage (40%), engagement (30%), and freshness (30%)</p>
                        </div>
                      </div>
                      <span className={`text-2xl font-bold ${
                        healthScore >= 70 ? 'text-emerald-400' : healthScore >= 40 ? 'text-amber-400' : 'text-red-400'
                      }`}>{healthScore}</span>
                    </div>
                  );
                })()}
              </div>
            ) : (
              <div className="text-center py-8">
                <FileText className="h-12 w-12 mx-auto mb-3 text-white/20" />
                <p className="text-sm text-white/50 mb-2">No documents indexed yet</p>
                <p className="text-xs text-white/30">Index some files to see quality metrics here</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Search Card */}
        <Card className="bg-[#0f0f0f] border-white/10">
          <CardHeader className="border-b border-white/5">
            <div className="flex items-center gap-2">
              <Search className="h-5 w-5 text-emerald-400" />
              <CardTitle className="text-white">Search Documents</CardTitle>
            </div>
            <CardDescription className="text-white/50">
              Find content in your indexed files
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="flex gap-3 flex-wrap">
              <div className="flex-1 min-w-[300px] relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-white/30" />
                <Input
                  placeholder="Search for code, documentation, notes..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="pl-10 bg-[#0a0a0a] border-white/10 text-white placeholder:text-white/30 focus:border-emerald-500/50"
                />
              </div>
              <Button
                onClick={handleSearch}
                disabled={searching || !searchQuery.trim()}
                className="bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white border-0"
              >
                {searching ? 'Searching...' : 'Search'}
              </Button>
            </div>

            {/* Popular Documents */}
            {popularDocuments.length > 0 && (
              <div className="mt-6">
                <div className="flex items-center gap-2 mb-4">
                  <Zap className="h-5 w-5 text-amber-400" />
                  <Label className="text-white/90">Popular Documents ({popularDocuments.length})</Label>
                </div>
                <div className="grid grid-cols-1 gap-3">
                  {popularDocuments.map((doc) => (
                    <div
                      key={doc.id}
                      className="p-3 rounded-lg bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20 hover:border-amber-500/40 transition-colors"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <p className="font-mono text-sm font-medium text-white/90 truncate">{doc.file_path}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge className={`text-xs ${getAccessBadgeStyle(doc.access_count)}`}>
                              {getAccessIcon(doc.access_count)} {doc.access_count}x
                            </Badge>
                            {doc.last_accessed && (
                              <span className="text-xs text-white/40">
                                {formatDistanceToNow(new Date(doc.last_accessed), { addSuffix: true })}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Results */}
            {results.length > 0 && (
              <div className="mt-6 space-y-4">
                <div className="flex items-center justify-between">
                  <Label className="text-white/90">All Results ({results.length})</Label>
                </div>

                {results.map((doc) => (
                  <div
                    key={doc.id}
                    className="p-4 rounded-lg border border-white/10 hover:bg-white/5 hover:border-emerald-500/50 transition-all duration-300 bg-[#0a0a0a]"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                          <FileText className="h-4 w-4 text-white/40" />
                          <p className="font-mono text-sm font-medium text-white/90">{doc.file_path}</p>
                          <Badge className="text-xs bg-blue-500/10 text-blue-400 border-blue-500/20">
                            {doc.file_type}
                          </Badge>
                          <span className="text-xs text-white/40">
                            Score: {doc.score.toFixed(2)}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 mb-2 flex-wrap">
                          <p className="text-xs text-white/40">
                            Chunk {doc.chunk_index + 1}/{doc.total_chunks} • {doc.folder}
                          </p>
                          <Badge className={`text-xs ${getAccessBadgeStyle(doc.access_count)}`}>
                            {getAccessIcon(doc.access_count)} Accessed {doc.access_count}x
                          </Badge>
                          {doc.last_accessed && (
                            <span className="text-xs text-white/40">
                              • Last seen {formatDistanceToNow(new Date(doc.last_accessed), { addSuffix: true })}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="bg-[#0f0f0f] border border-white/5 rounded-lg p-3 text-sm font-mono whitespace-pre-wrap text-white/80">
                      {doc.content.length > 300
                        ? doc.content.substring(0, 300) + '...'
                        : doc.content}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {results.length === 0 && searchQuery && !searching && (
              <div className="mt-6 text-center p-12">
                <FileText className="h-16 w-16 mx-auto mb-4 text-white/20" />
                <p className="text-white/50">No documents found for "{searchQuery}"</p>
                <p className="text-sm text-white/30 mt-2">
                  Try indexing folders or using different search terms
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
