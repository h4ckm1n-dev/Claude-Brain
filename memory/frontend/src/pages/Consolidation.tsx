import { useState } from 'react';
import { useConsolidateMemories } from '../hooks/useMemories';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Badge } from '../components/ui/badge';
import { Archive, AlertCircle, CheckCircle } from 'lucide-react';
import { ConsolidateRequest, ConsolidateResult } from '../types/memory';

export function Consolidation() {
  const [request, setRequest] = useState<ConsolidateRequest>({
    older_than_days: 7,
    dry_run: true,
  });

  const [result, setResult] = useState<ConsolidateResult | null>(null);

  const consolidate = useConsolidateMemories();

  const handleConsolidate = async () => {
    try {
      const data = await consolidate.mutateAsync(request);
      setResult(data);
    } catch (error) {
      console.error('Consolidation failed:', error);
    }
  };

  return (
    <div>
      <Header title="Consolidation" />
      <div className="p-6 space-y-6">
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Consolidation merges similar memories and archives old, low-value ones.
            Run in dry-run mode first to preview changes.
          </AlertDescription>
        </Alert>

        <Card>
          <CardHeader>
            <CardTitle>Consolidation Configuration</CardTitle>
            <CardDescription>
              Configure memory consolidation settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Age Threshold (days)
              </label>
              <Input
                type="number"
                value={request.older_than_days}
                onChange={(e) => setRequest({ ...request, older_than_days: parseInt(e.target.value) })}
                min={1}
                max={365}
              />
              <p className="text-xs text-muted-foreground mt-1">
                Only consolidate memories older than this many days
              </p>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="dry-run"
                checked={request.dry_run}
                onChange={(e) => setRequest({ ...request, dry_run: e.target.checked })}
                className="rounded border-input"
              />
              <label htmlFor="dry-run" className="text-sm font-medium">
                Dry Run (preview only, no changes)
              </label>
            </div>

            <Button
              onClick={handleConsolidate}
              disabled={consolidate.isPending}
              className="w-full"
            >
              <Archive className="mr-2 h-4 w-4" />
              {request.dry_run ? 'Preview Consolidation' : 'Run Consolidation'}
            </Button>
          </CardContent>
        </Card>

        {result && (
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <CardTitle>
                  {result.dry_run ? 'Consolidation Preview' : 'Consolidation Complete'}
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="text-center p-4 bg-muted rounded-lg">
                  <div className="text-2xl font-bold">{result.analyzed}</div>
                  <div className="text-xs text-muted-foreground">Analyzed</div>
                </div>
                <div className="text-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <div className="text-2xl font-bold">{result.consolidated}</div>
                  <div className="text-xs text-muted-foreground">Consolidated</div>
                </div>
                <div className="text-center p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                  <div className="text-2xl font-bold">{result.archived}</div>
                  <div className="text-xs text-muted-foreground">Archived</div>
                </div>
                <div className="text-center p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                  <div className="text-2xl font-bold">{result.deleted}</div>
                  <div className="text-xs text-muted-foreground">Deleted</div>
                </div>
                <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <div className="text-2xl font-bold">{result.kept}</div>
                  <div className="text-xs text-muted-foreground">Kept</div>
                </div>
              </div>

              {result.dry_run && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    This was a dry run. No changes were made to your memories.
                    Uncheck "Dry Run" and run again to apply these changes.
                  </AlertDescription>
                </Alert>
              )}

              {!result.dry_run && (
                <Alert>
                  <CheckCircle className="h-4 w-4" />
                  <AlertDescription>
                    Consolidation completed successfully. Your memories have been optimized.
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
