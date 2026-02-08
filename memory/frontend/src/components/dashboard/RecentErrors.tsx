import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { AlertCircle, Archive, CheckCircle2, Clock, ExternalLink } from 'lucide-react';
import { Memory } from '../../types/memory';
import { formatDistanceToNow } from 'date-fns';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Link } from 'react-router-dom';
import { useArchiveMemory } from '../../hooks/useMemories';
import { useState } from 'react';
import * as api from '../../api/memories';
import { useQueryClient } from '@tanstack/react-query';
import { memoryKeys } from '../../hooks/useMemories';

interface RecentErrorsProps {
  memories?: Memory[];
}

export function RecentErrors({ memories }: RecentErrorsProps) {
  const unresolvedErrors = memories?.filter(
    m => m.type === 'error' && !m.resolved && !m.archived
  ).slice(0, 5) || [];

  const archiveMutation = useArchiveMemory();
  const queryClient = useQueryClient();
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const handleArchive = (id: string) => {
    archiveMutation.mutate(id);
  };

  const handleResolve = async (id: string) => {
    setResolvingId(id);
    try {
      await api.resolveMemory(id, 'Resolved from dashboard');
      queryClient.invalidateQueries({ queryKey: memoryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: memoryKeys.stats });
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <Card className="shadow-lg border-l-4 border-l-red-500">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <div>
              <CardTitle>Unresolved Errors</CardTitle>
              <CardDescription className="mt-1">Issues requiring attention</CardDescription>
            </div>
          </div>
          {unresolvedErrors.length > 0 && (
            <Badge variant="destructive" className="animate-pulse">
              {unresolvedErrors.length} Active
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {unresolvedErrors.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mb-4">
              <AlertCircle className="h-8 w-8 text-green-600" />
            </div>
            <div className="text-lg font-medium text-green-700 dark:text-green-300">
              All Clear!
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              No unresolved errors found
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {unresolvedErrors.map((error) => (
              <div
                key={error.id}
                className="p-4 border border-red-200 dark:border-red-800 rounded-lg bg-red-50 dark:bg-red-950/30 hover:bg-red-100 dark:hover:bg-red-950/50 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <p className="text-sm font-medium text-red-900 dark:text-red-100 line-clamp-2">
                        {error.content}
                      </p>
                    </div>

                    {error.error_message && (
                      <div className="mb-2 p-2 bg-red-100 dark:bg-red-900/40 rounded text-xs font-mono text-red-800 dark:text-red-200 overflow-x-auto">
                        {error.error_message}
                      </div>
                    )}

                    <div className="flex items-center justify-between mt-3">
                      <div className="flex items-center gap-4 text-xs text-red-700 dark:text-red-300">
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDistanceToNow(new Date(error.created_at), { addSuffix: true })}
                        </div>
                        {error.project && (
                          <Badge variant="outline" className="text-xs">
                            {error.project}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-xs h-7 text-green-700 hover:text-green-800 hover:bg-green-100 dark:text-green-400 dark:hover:bg-green-950/50"
                          onClick={() => handleResolve(error.id)}
                          disabled={resolvingId === error.id}
                          title="Mark as resolved"
                        >
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          Resolve
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-xs h-7 text-muted-foreground hover:text-foreground"
                          onClick={() => handleArchive(error.id)}
                          disabled={archiveMutation.isPending}
                          title="Archive this error"
                        >
                          <Archive className="h-3 w-3 mr-1" />
                          Archive
                        </Button>
                        <Link to={`/memories`}>
                          <Button variant="ghost" size="sm" className="text-xs h-7">
                            <ExternalLink className="h-3 w-3" />
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {unresolvedErrors.length > 0 && (
              <div className="pt-2 text-center">
                <Link to="/memories?type=error">
                  <Button variant="outline" size="sm" className="w-full">
                    View All Errors
                    <ExternalLink className="h-3 w-3 ml-2" />
                  </Button>
                </Link>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
