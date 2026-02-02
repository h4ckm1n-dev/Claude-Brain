import { useState } from 'react';
import { useDebounce } from '../hooks/useDebounce';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Search as SearchIcon, Filter, Sparkles, Zap } from 'lucide-react';
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
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]">
      <Header title="Search" />
      <div className="p-6 sm:p-8 max-w-[1800px] mx-auto space-y-6">
        {/* Hero Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-purple-500/10 via-blue-500/10 to-emerald-500/10 p-6 border border-white/5">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 via-transparent to-blue-500/5" />
          <div className="relative flex items-center gap-4">
            <div className="p-3 bg-purple-500/10 rounded-xl ring-1 ring-purple-500/20">
              <SearchIcon className="h-8 w-8 text-purple-400" />
            </div>
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-white">Search Memories</h1>
              <p className="text-white/60 mt-1 flex items-center gap-2">
                <Zap className="h-4 w-4 text-emerald-400" />
                Hybrid search with semantic understanding
              </p>
            </div>
          </div>
        </div>

        {/* Search Bar */}
        <Card className="bg-[#0f0f0f] border-white/10">
          <CardHeader className="border-b border-white/5">
            <CardTitle className="text-white">Intelligent Search</CardTitle>
          </CardHeader>
          <CardContent className="pt-6 space-y-4">
            <div className="flex gap-4 flex-wrap">
              <div className="flex-1 min-w-[300px] relative">
                <SearchIcon className="absolute left-3 top-3 h-4 w-4 text-white/30" />
                <Input
                  className="pl-10 bg-[#0a0a0a] border-white/10 text-white placeholder:text-white/30 focus:border-purple-500/50"
                  placeholder="Search memories..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
              <Button
                variant="outline"
                onClick={() => setShowFilters(!showFilters)}
                className={`bg-[#0a0a0a] border-white/10 text-white/90 hover:bg-white/5 transition-all ${
                  showFilters ? 'border-purple-500/50 bg-purple-500/10' : 'hover:border-purple-500/50'
                }`}
              >
                <Filter className="mr-2 h-4 w-4" />
                Filters
              </Button>
            </div>

            {showFilters && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-white/5">
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-2">Search Mode</label>
                  <Select
                    value={searchMode}
                    onChange={(e) => setSearchMode(e.target.value as any)}
                    className="bg-[#0a0a0a] border-white/10 text-white"
                  >
                    <option value="hybrid">Hybrid (Best)</option>
                    <option value="semantic">Semantic Only</option>
                    <option value="keyword">Keyword Only</option>
                  </Select>
                  <p className="text-xs text-white/40 mt-1">
                    {searchMode === 'hybrid' && 'Combines semantic and keyword search'}
                    {searchMode === 'semantic' && 'AI-powered meaning-based search'}
                    {searchMode === 'keyword' && 'Traditional text matching'}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-2">Type Filter</label>
                  <Select
                    value={typeFilter}
                    onChange={(e) => setTypeFilter(e.target.value as any)}
                    className="bg-[#0a0a0a] border-white/10 text-white"
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
            <Card className="bg-[#0f0f0f] border-white/10">
              <CardContent className="p-12 text-center">
                <Sparkles className="h-16 w-16 mx-auto mb-4 text-white/20" />
                <p className="text-white/50 text-lg mb-2">Start typing to search memories</p>
                <p className="text-white/30 text-sm">
                  Use natural language to find what you need
                </p>
              </CardContent>
            </Card>
          ) : isLoading ? (
            <Card className="bg-[#0f0f0f] border-white/10">
              <CardContent className="p-12 text-center">
                <div className="inline-flex items-center gap-3">
                  <div className="h-8 w-8 border-2 border-purple-500/20 border-t-purple-500 rounded-full animate-spin" />
                  <span className="text-white/50 text-lg">Searching...</span>
                </div>
              </CardContent>
            </Card>
          ) : !results || results.length === 0 ? (
            <Card className="bg-[#0f0f0f] border-white/10">
              <CardContent className="p-12 text-center">
                <SearchIcon className="h-16 w-16 mx-auto mb-4 text-white/20" />
                <p className="text-white/50 text-lg mb-2">No results found</p>
                <p className="text-white/30 text-sm">
                  Try different keywords or change search mode
                </p>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <div className="text-sm text-white/50">
                  Found <span className="text-white/90 font-semibold">{results.length}</span> results for "{debouncedQuery}"
                </div>
                <Badge className="bg-purple-500/10 text-purple-400 border-purple-500/20">
                  {searchMode === 'hybrid' ? 'Hybrid' : searchMode === 'semantic' ? 'Semantic' : 'Keyword'} Mode
                </Badge>
              </div>
              {results.map((result: SearchResult) => (
                <Card
                  key={result.memory.id}
                  className="bg-[#0f0f0f] border-white/10 hover:border-purple-500/50 hover:bg-white/5 transition-all duration-300 group"
                >
                  <CardHeader className="border-b border-white/5">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                          {result.memory.type}
                        </Badge>
                        <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                          Score: {result.score.toFixed(3)}
                        </Badge>
                        {result.memory.pinned && (
                          <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/20">
                            Pinned
                          </Badge>
                        )}
                      </div>
                      <span className="text-sm text-white/40">
                        {formatDistanceToNow(new Date(result.memory.created_at), { addSuffix: true })}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-6 space-y-4">
                    <p className="text-sm text-white/90 leading-relaxed">{result.memory.content}</p>

                    {result.memory.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {result.memory.tags.map((tag) => (
                          <Badge
                            key={tag}
                            className="text-xs bg-purple-500/10 text-purple-400 border-purple-500/20 hover:bg-purple-500/20 transition-colors"
                          >
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}

                    {result.memory.project && (
                      <div className="text-sm text-white/50">
                        <span className="text-white/40">Project: </span>
                        <span className="text-blue-400">{result.memory.project}</span>
                      </div>
                    )}

                    {result.memory.error_message && (
                      <div className="text-sm p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg">
                        <span className="font-medium text-rose-400">Error: </span>
                        <span className="text-white/70">{result.memory.error_message}</span>
                      </div>
                    )}

                    {result.memory.solution && (
                      <div className="text-sm p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                        <span className="font-medium text-emerald-400">Solution: </span>
                        <span className="text-white/70">{result.memory.solution}</span>
                      </div>
                    )}

                    <div className="flex items-center gap-6 text-xs text-white/40 pt-3 border-t border-white/5">
                      <span>
                        Importance: <span className="text-white/60">{result.memory.importance_score.toFixed(2)}</span>
                      </span>
                      <span>
                        Accessed: <span className="text-white/60">{result.memory.access_count} times</span>
                      </span>
                      <span>
                        Tier: <span className="text-white/60">{result.memory.memory_tier}</span>
                      </span>
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
