import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Label } from '../components/ui/label';
import { apiClient } from '../lib/api';
import type { AxiosResponse } from 'axios';
import { FileText, Search, Folder, FolderOpen, Trash2, BookOpen } from 'lucide-react';

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
}

interface DocumentStats {
  collection: string;
  total_chunks: number;
  status: string;
}

export default function Documents() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<DocumentResult[]>([]);
  const [searching, setSearching] = useState(false);

  // Get document stats
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

        {/* Stats Card */}
        <Card className="bg-[#0f0f0f] border-white/10">
          <CardHeader className="border-b border-white/5">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-blue-400" />
              <CardTitle className="text-white">Document Collection</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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

            {/* Results */}
            {results.length > 0 && (
              <div className="mt-6 space-y-4">
                <div className="flex items-center justify-between">
                  <Label className="text-white/90">Results ({results.length})</Label>
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
                        <p className="text-xs text-white/40 mb-2">
                          Chunk {doc.chunk_index + 1}/{doc.total_chunks} • {doc.folder}
                        </p>
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
