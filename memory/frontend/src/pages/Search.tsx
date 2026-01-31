import { useState } from 'react';
import { useDebounce } from '../hooks/useDebounce';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Search as SearchIcon, Filter } from 'lucide-react';
import { searchMemories } from '../api/memories';
import { useQuery } from '@tanstack/react-query';
import { SearchQuery, MemoryType, SearchResult } from '../types/memory';
import { formatDistanceToNow } from 'date-fns';

export function Search() {
  const [query, setQuery] = useState('');
  const [searchMode, setSearchMode] = useState<'semantic' | 'keyword' | 'hybrid'>('hybrid');
  const [typeFilter, setTypeFilter] = useState<MemoryType | ''>('');
  const [showFilters, setShowFilters] = useState(false);

  const debouncedQuery = useDebounce(query, 500);

  const searchQuery: SearchQuery = {
    query: debouncedQuery,
    search_mode: searchMode,
    type: typeFilter || undefined,
    limit: 20,
  };

  const { data: results, isLoading } = useQuery({
    queryKey: ['search', debouncedQuery, searchMode, typeFilter],
    queryFn: () => searchMemories(searchQuery),
    enabled: debouncedQuery.length > 0,
  });

  return (
    <div>
      <Header title="Search" />
      <div className="p-6 space-y-6">
        {/* Search Bar */}
        <Card>
          <CardHeader>
            <CardTitle>Search Memories</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-1 relative">
                <SearchIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  className="pl-10"
                  placeholder="Search memories..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
              <Button
                variant="outline"
                onClick={() => setShowFilters(!showFilters)}
              >
                <Filter className="mr-2 h-4 w-4" />
                Filters
              </Button>
            </div>

            {showFilters && (
              <div className="grid grid-cols-2 gap-4 pt-2 border-t">
                <div>
                  <label className="block text-sm font-medium mb-2">Search Mode</label>
                  <Select
                    value={searchMode}
                    onChange={(e) => setSearchMode(e.target.value as any)}
                  >
                    <option value="hybrid">Hybrid (Best)</option>
                    <option value="semantic">Semantic Only</option>
                    <option value="keyword">Keyword Only</option>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Type Filter</label>
                  <Select
                    value={typeFilter}
                    onChange={(e) => setTypeFilter(e.target.value as any)}
                  >
                    <option value="">All Types</option>
                    {Object.values(MemoryType).map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </Select>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Search Results */}
        <div className="space-y-4">
          {debouncedQuery.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center text-muted-foreground">
                Enter a search query to find memories
              </CardContent>
            </Card>
          ) : isLoading ? (
            <Card>
              <CardContent className="p-8 text-center text-muted-foreground">
                Searching...
              </CardContent>
            </Card>
          ) : !results || results.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center text-muted-foreground">
                No results found for "{debouncedQuery}"
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="text-sm text-muted-foreground">
                Found {results.length} results for "{debouncedQuery}"
              </div>
              {results.map((result: SearchResult) => (
                <Card key={result.memory.id} className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{result.memory.type}</Badge>
                        <Badge variant="secondary">
                          Score: {result.score.toFixed(3)}
                        </Badge>
                      </div>
                      <span className="text-sm text-muted-foreground">
                        {formatDistanceToNow(new Date(result.memory.created_at), { addSuffix: true })}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm">{result.memory.content}</p>

                    {result.memory.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {result.memory.tags.map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}

                    {result.memory.project && (
                      <div className="text-sm text-muted-foreground">
                        Project: {result.memory.project}
                      </div>
                    )}

                    {result.memory.error_message && (
                      <div className="text-sm p-2 bg-muted rounded">
                        <span className="font-medium">Error: </span>
                        {result.memory.error_message}
                      </div>
                    )}

                    {result.memory.solution && (
                      <div className="text-sm p-2 bg-green-50 dark:bg-green-900/20 rounded">
                        <span className="font-medium">Solution: </span>
                        {result.memory.solution}
                      </div>
                    )}

                    <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t">
                      <span>Importance: {result.memory.importance_score.toFixed(2)}</span>
                      <span>Accessed: {result.memory.access_count} times</span>
                      <span>Tier: {result.memory.memory_tier}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
