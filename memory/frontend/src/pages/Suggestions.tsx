import { useState } from 'react';
import { useSuggestions } from '../hooks/useMemories';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Lightbulb, Sparkles } from 'lucide-react';
import { SuggestionRequest } from '../types/memory';

export function Suggestions() {
  const [request, setRequest] = useState<SuggestionRequest>({
    project: '',
    keywords: [],
    limit: 10,
  });

  const [keywordInput, setKeywordInput] = useState('');

  const { data: suggestionsData, refetch } = useSuggestions(request);

  const handleSearch = () => {
    const keywords = keywordInput.split(',').map(k => k.trim()).filter(Boolean);
    setRequest({ ...request, keywords });
    refetch();
  };

  return (
    <div>
      <Header title="Suggestions" />
      <div className="p-6 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Context-Aware Memory Suggestions</CardTitle>
            <CardDescription>
              Get relevant memories based on your current context
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Project</label>
              <Input
                value={request.project}
                onChange={(e) => setRequest({ ...request, project: e.target.value })}
                placeholder="e.g., my-app"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Keywords (comma-separated)</label>
              <Input
                value={keywordInput}
                onChange={(e) => setKeywordInput(e.target.value)}
                placeholder="e.g., authentication, error, typescript"
              />
            </div>
            <Button onClick={handleSearch}>
              <Sparkles className="mr-2 h-4 w-4" />
              Get Suggestions
            </Button>
          </CardContent>
        </Card>

        {suggestionsData && (
          <div className="space-y-4">
            <div className="text-sm text-muted-foreground">
              Found {suggestionsData.count} relevant suggestions
            </div>

            {suggestionsData.suggestions.map((suggestion) => (
              <Card key={suggestion.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <Lightbulb className="h-5 w-5 text-yellow-500" />
                      <Badge variant="outline">{suggestion.type}</Badge>
                      <Badge variant="secondary">
                        Score: {suggestion.combined_score.toFixed(2)}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                    <p className="text-sm font-medium">Why this is suggested:</p>
                    <p className="text-sm mt-1">{suggestion.reason}</p>
                  </div>

                  <p className="text-sm">{suggestion.content}</p>

                  {suggestion.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {suggestion.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}

                  <div className="text-xs text-muted-foreground pt-2 border-t">
                    Accessed {suggestion.access_count} times
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
