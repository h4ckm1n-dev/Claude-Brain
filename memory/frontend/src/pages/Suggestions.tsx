import { useState } from 'react';
import { useSuggestions } from '../hooks/useMemories';
import { useRecommendations } from '../hooks/useAnalytics';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Lightbulb, Sparkles, Brain } from 'lucide-react';
import { SuggestionRequest } from '../types/memory';
import { QualityBadge } from '../components/QualityBadge';

export function Suggestions() {
  const [request, setRequest] = useState<SuggestionRequest>({
    project: '',
    keywords: [],
    limit: 10,
  });

  const [keywordInput, setKeywordInput] = useState('');

  const { data: suggestionsData, refetch } = useSuggestions(request);

  // Phase 3-4: Pattern-based recommendations
  const { data: patternRecommendations } = useRecommendations(undefined, keywordInput, 10);

  const handleSearch = () => {
    const keywords = keywordInput.split(',').map(k => k.trim()).filter(Boolean);
    setRequest({ ...request, keywords });
    refetch();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]">
      <Header title="Suggestions" />
      <div className="p-6 space-y-6">
        {/* Hero Section */}
        <div className="bg-gradient-to-br from-amber-600 via-yellow-600 to-orange-600 rounded-2xl p-8 shadow-2xl">
          <div className="flex items-center gap-4">
            <div className="p-4 bg-white/20 backdrop-blur-sm rounded-xl">
              <Lightbulb className="h-10 w-10 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">Smart Suggestions</h1>
              <p className="text-amber-100 mt-1">
                Context-aware memory recommendations based on your current work
              </p>
            </div>
          </div>
        </div>

        <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-amber-500/10 transition-all">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-amber-400" />
              <CardTitle className="text-white">Context-Aware Memory Suggestions</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Get relevant memories based on your current context
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <label className="block text-sm font-medium mb-2 text-white/90">Project</label>
              <Input
                value={request.project}
                onChange={(e) => setRequest({ ...request, project: e.target.value })}
                placeholder="e.g., my-app"
                className="bg-[#0f0f0f] border-white/10 text-white"
              />
            </div>
            <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <label className="block text-sm font-medium mb-2 text-white/90">Keywords (comma-separated)</label>
              <Input
                value={keywordInput}
                onChange={(e) => setKeywordInput(e.target.value)}
                placeholder="e.g., authentication, error, typescript"
                className="bg-[#0f0f0f] border-white/10 text-white"
              />
            </div>
            <Button
              onClick={handleSearch}
              className="w-full bg-amber-500 hover:bg-amber-600 text-white shadow-lg shadow-amber-500/20"
            >
              <Sparkles className="mr-2 h-4 w-4" />
              Get Suggestions
            </Button>
          </CardContent>
        </Card>

        {suggestionsData && (
          <>
            <div className="flex items-center justify-between p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl backdrop-blur-sm">
              <div className="flex items-center gap-2">
                <Lightbulb className="h-5 w-5 text-amber-400" />
                <span className="text-amber-200">
                  Found {suggestionsData.count} relevant suggestion{suggestionsData.count !== 1 ? 's' : ''}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4">
              {suggestionsData.suggestions.map((suggestion) => (
                <Card
                  key={suggestion.id}
                  className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-amber-500/20 hover:border-amber-500/30 transition-all"
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Lightbulb className="h-5 w-5 text-amber-400" />
                        <Badge className="bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          {suggestion.type}
                        </Badge>
                        <Badge className="bg-blue-500/20 text-blue-300 border border-blue-500/30">
                          Score: {(suggestion.combined_score ?? 0).toFixed(2)}
                        </Badge>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                      <p className="text-sm font-medium text-amber-300">Why this is suggested:</p>
                      <p className="text-sm mt-1 text-amber-200/90">{suggestion.reason}</p>
                    </div>

                    <p className="text-sm text-white/90 leading-relaxed">{suggestion.content}</p>

                    {suggestion.tags?.length > 0 && (
                      <div className="flex flex-wrap gap-2 pt-2 border-t border-white/5">
                        {suggestion.tags?.map((tag) => (
                          <Badge
                            key={tag}
                            className="text-xs bg-[#0a0a0a] text-white/70 border border-white/10 hover:border-amber-500/30 transition-colors"
                          >
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}

                    <div className="flex items-center gap-2 text-xs text-white/50 pt-2 border-t border-white/5">
                      <span>Accessed {suggestion.access_count} times</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </>
        )}

        {/* Phase 3-4: Pattern-based Recommendations */}
        {patternRecommendations && patternRecommendations.length > 0 && (
          <>
            <Card className="bg-[#0f0f0f] border-white/10">
              <CardHeader className="border-b border-white/5">
                <div className="flex items-center gap-2">
                  <Brain className="h-5 w-5 text-purple-400" />
                  <CardTitle className="text-white">Pattern-based Recommendations</CardTitle>
                </div>
                <CardDescription className="text-white/60">
                  High-quality memories detected through pattern analysis
                </CardDescription>
              </CardHeader>
            </Card>

            <div className="grid grid-cols-1 gap-4">
              {patternRecommendations
                .filter(rec => rec.quality_score > 0.7)
                .map((rec) => (
                  <Card
                    key={rec.memory_id}
                    className="bg-[#0f0f0f] border border-white/10 hover:border-purple-500/50 hover:bg-white/5 transition-all"
                  >
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Brain className="h-4 w-4 text-purple-400" />
                          <QualityBadge score={(rec.quality_score ?? 0) * 100} size="sm" />
                          <Badge className="bg-purple-500/10 text-purple-400 border-purple-500/20">
                            Relevance: {(rec.relevance_score ?? 0).toFixed(2)}
                          </Badge>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="p-3 bg-purple-500/10 border border-purple-500/20 rounded-lg">
                        <p className="text-sm font-medium text-purple-300">Why recommended:</p>
                        <p className="text-sm mt-1 text-purple-200/90">{rec.reason}</p>
                      </div>

                      <p className="text-sm text-white/90 leading-relaxed">{rec.content}</p>

                      {rec.tags?.length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-2 border-t border-white/5">
                          {rec.tags?.map((tag) => (
                            <Badge
                              key={tag}
                              className="text-xs bg-purple-500/10 text-purple-400 border-purple-500/20"
                            >
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
            </div>
          </>
        )}

        {!suggestionsData && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="p-6 bg-amber-500/10 border border-amber-500/30 rounded-2xl mb-4">
              <Lightbulb className="h-12 w-12 text-amber-400 mx-auto" />
            </div>
            <h3 className="text-xl font-semibold text-white/90 mb-2">
              Get Personalized Suggestions
            </h3>
            <p className="text-white/60 max-w-md">
              Enter a project name or keywords above to get relevant memory suggestions based on your context
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
