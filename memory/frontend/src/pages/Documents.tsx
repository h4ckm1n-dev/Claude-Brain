import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Label } from '../components/ui/label';
import { apiClient } from '../lib/api';
import type { AxiosResponse } from 'axios';
import { FileText, Search, Folder, FolderOpen, Trash2 } from 'lucide-react';

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
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Documents</h1>
        <p className="text-muted-foreground mt-2">
          Search indexed files from your filesystem. Documents are separate from memories.
        </p>
      </div>

      {/* Stats Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-blue-600" />
            <CardTitle>Document Collection</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Total Chunks</p>
              <p className="text-2xl font-bold">{stats?.total_chunks || 0}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Collection</p>
              <p className="text-lg font-medium">{stats?.collection || 'documents'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Status</p>
              <Badge variant={stats?.status === 'green' ? 'default' : 'outline'}>
                {stats?.status || 'unknown'}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Search Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Search className="h-5 w-5 text-green-600" />
            <CardTitle>Search Documents</CardTitle>
          </div>
          <CardDescription>
            Find content in your indexed files
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <Input
              placeholder="Search for code, documentation, notes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="flex-1"
            />
            <Button onClick={handleSearch} disabled={searching || !searchQuery.trim()}>
              {searching ? 'Searching...' : 'Search'}
            </Button>
          </div>

          {/* Results */}
          {results.length > 0 && (
            <div className="mt-6 space-y-4">
              <div className="flex items-center justify-between">
                <Label>Results ({results.length})</Label>
              </div>

              {results.map((doc) => (
                <div
                  key={doc.id}
                  className="p-4 rounded-lg border hover:bg-muted/50 transition"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <p className="font-mono text-sm font-medium">{doc.file_path}</p>
                        <Badge variant="outline" className="text-xs">
                          {doc.file_type}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          Score: {doc.score.toFixed(2)}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mb-2">
                        Chunk {doc.chunk_index + 1}/{doc.total_chunks} • {doc.folder}
                      </p>
                    </div>
                  </div>

                  <div className="bg-muted/30 rounded p-3 text-sm font-mono whitespace-pre-wrap">
                    {doc.content.length > 300
                      ? doc.content.substring(0, 300) + '...'
                      : doc.content}
                  </div>
                </div>
              ))}
            </div>
          )}

          {results.length === 0 && searchQuery && !searching && (
            <div className="mt-6 text-center text-muted-foreground">
              <p>No documents found for "{searchQuery}"</p>
              <p className="text-sm mt-2">
                Try indexing folders or using different search terms
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
