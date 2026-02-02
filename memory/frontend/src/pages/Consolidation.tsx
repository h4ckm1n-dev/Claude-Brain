import { useState } from 'react';
import { useConsolidateMemories } from '../hooks/useMemories';
import { useQualityStats } from '../hooks/useQuality';
import { useLifecycleStats } from '../hooks/useLifecycle';
import { useAuditTrail } from '../hooks/useAudit';
import { AuditTimeline } from '../components/AuditTimeline';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Badge } from '../components/ui/badge';
import { Archive, AlertCircle, CheckCircle, Trash2, TrendingUp, Clock } from 'lucide-react';
import { ConsolidateRequest, ConsolidateResult, AuditAction } from '../types/memory';

export function Consolidation() {
  const [request, setRequest] = useState<ConsolidateRequest>({
    older_than_days: 7,
    dry_run: true,
  });

  const [result, setResult] = useState<ConsolidateResult | null>(null);

  const consolidate = useConsolidateMemories();

  // Phase 3-4: Consolidation impact metrics
  const { data: qualityStats } = useQualityStats();
  const { data: lifecycleStats } = useLifecycleStats();
  const { data: auditEntries } = useAuditTrail(undefined, 10);

  const handleConsolidate = async () => {
    try {
      const data = await consolidate.mutateAsync(request);
      setResult(data);
    } catch (error) {
      console.error('Consolidation failed:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]">
      <Header title="Consolidation" />
      <div className="p-6 space-y-6">
        {/* Hero Section */}
        <div className="bg-gradient-to-br from-rose-600 via-pink-600 to-fuchsia-600 rounded-2xl p-8 shadow-2xl">
          <div className="flex items-center gap-4">
            <div className="p-4 bg-white/20 backdrop-blur-sm rounded-xl">
              <Archive className="h-10 w-10 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">Memory Consolidation</h1>
              <p className="text-rose-100 mt-1">
                Merge similar memories and archive low-value ones to optimize storage
              </p>
            </div>
          </div>
        </div>

        <Alert className="bg-rose-500/10 border-rose-500/30 backdrop-blur-sm">
          <AlertCircle className="h-4 w-4 text-rose-400" />
          <AlertDescription className="text-rose-200">
            Consolidation merges similar memories and archives old, low-value ones.
            Run in dry-run mode first to preview changes.
          </AlertDescription>
        </Alert>

        {/* Phase 3-4: Consolidation Impact Stats */}
        {lifecycleStats && qualityStats && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="bg-[#0f0f0f] border-white/10 border-l-4 border-l-yellow-500">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-white/90">Memories in Staging</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold text-white">
                    {lifecycleStats.state_distribution.staging || 0}
                  </span>
                  <Badge className="bg-yellow-500/20 text-yellow-300 border-yellow-500/30">
                    Staging ⏳
                  </Badge>
                </div>
                <p className="text-xs text-white/50 mt-2">
                  Memories under review for consolidation
                </p>
              </CardContent>
            </Card>

            <Card className="bg-[#0f0f0f] border-white/10 border-l-4 border-l-blue-500">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-white/90">Average Quality Score</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold text-white">
                    {qualityStats.avg_quality_score.toFixed(1)}%
                  </span>
                  <TrendingUp className="h-5 w-5 text-blue-400" />
                </div>
                <p className="text-xs text-white/50 mt-2">
                  Overall memory quality across system
                </p>
              </CardContent>
            </Card>

            <Card className="bg-[#0f0f0f] border-white/10 border-l-4 border-l-purple-500">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-white/90">Episodic Memories</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold text-white">
                    {lifecycleStats.state_distribution.episodic || 0}
                  </span>
                  <Badge className="bg-purple-500/20 text-purple-300 border-purple-500/30">
                    Episodic 🆕
                  </Badge>
                </div>
                <p className="text-xs text-white/50 mt-2">
                  New memories awaiting consolidation
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Phase 3-4: Recent Consolidations */}
        <Card className="bg-[#0f0f0f] border-white/10">
          <CardHeader className="border-b border-white/5">
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-amber-400" />
              <CardTitle className="text-white">Recent Consolidations</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Latest memory consolidation activities
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <AuditTimeline
              limit={10}
              filterAction={AuditAction.CONSOLIDATION}
            />
          </CardContent>
        </Card>

        <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-rose-500/10 transition-all">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Trash2 className="h-5 w-5 text-rose-400" />
              <CardTitle className="text-white">Consolidation Configuration</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Configure memory consolidation settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <label className="block text-sm font-medium mb-2 text-white/90">
                Age Threshold (days)
              </label>
              <Input
                type="number"
                value={request.older_than_days}
                onChange={(e) => setRequest({ ...request, older_than_days: parseInt(e.target.value) })}
                min={1}
                max={365}
                className="bg-[#0f0f0f] border-white/10 text-white"
              />
              <p className="text-xs text-white/50 mt-1">
                Only consolidate memories older than this many days
              </p>
            </div>

            <div className="flex items-center gap-2 p-4 rounded-lg bg-rose-500/10 border border-rose-500/30">
              <input
                type="checkbox"
                id="dry-run"
                checked={request.dry_run}
                onChange={(e) => setRequest({ ...request, dry_run: e.target.checked })}
                className="rounded border-rose-500/30 text-rose-500 focus:ring-rose-500"
              />
              <label htmlFor="dry-run" className="text-sm font-medium text-rose-200">
                Dry Run (preview only, no changes)
              </label>
            </div>

            <Button
              onClick={handleConsolidate}
              disabled={consolidate.isPending}
              className={`w-full ${
                request.dry_run
                  ? 'bg-blue-500 hover:bg-blue-600'
                  : 'bg-rose-500 hover:bg-rose-600'
              } text-white shadow-lg ${
                request.dry_run ? 'shadow-blue-500/20' : 'shadow-rose-500/20'
              }`}
            >
              <Archive className="mr-2 h-4 w-4" />
              {request.dry_run ? 'Preview Consolidation' : 'Run Consolidation'}
            </Button>
          </CardContent>
        </Card>

        {result && (
          <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl">
            <CardHeader className={`border-b ${
              result.dry_run ? 'border-blue-500/30 bg-blue-500/5' : 'border-emerald-500/30 bg-emerald-500/5'
            }`}>
              <div className="flex items-center gap-2">
                <CheckCircle className={`h-5 w-5 ${result.dry_run ? 'text-blue-400' : 'text-emerald-400'}`} />
                <CardTitle className="text-white">
                  {result.dry_run ? 'Consolidation Preview' : 'Consolidation Complete'}
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-6">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="text-center p-4 bg-[#0a0a0a] border border-white/10 rounded-lg">
                  <div className="text-2xl font-bold text-white">{result.analyzed}</div>
                  <div className="text-xs text-white/50 mt-1">Analyzed</div>
                </div>
                <div className="text-center p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                  <div className="text-2xl font-bold text-blue-300">{result.consolidated}</div>
                  <div className="text-xs text-blue-200/70 mt-1">Consolidated</div>
                </div>
                <div className="text-center p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                  <div className="text-2xl font-bold text-amber-300">{result.archived}</div>
                  <div className="text-xs text-amber-200/70 mt-1">Archived</div>
                </div>
                <div className="text-center p-4 bg-rose-500/10 border border-rose-500/30 rounded-lg">
                  <div className="text-2xl font-bold text-rose-300">{result.deleted}</div>
                  <div className="text-xs text-rose-200/70 mt-1">Deleted</div>
                </div>
                <div className="text-center p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                  <div className="text-2xl font-bold text-emerald-300">{result.kept}</div>
                  <div className="text-xs text-emerald-200/70 mt-1">Kept</div>
                </div>
              </div>

              {result.dry_run && (
                <Alert className="bg-blue-500/10 border-blue-500/30">
                  <AlertCircle className="h-4 w-4 text-blue-400" />
                  <AlertDescription className="text-blue-200">
                    This was a dry run. No changes were made to your memories.
                    Uncheck "Dry Run" and run again to apply these changes.
                  </AlertDescription>
                </Alert>
              )}

              {!result.dry_run && (
                <Alert className="bg-emerald-500/10 border-emerald-500/30">
                  <CheckCircle className="h-4 w-4 text-emerald-400" />
                  <AlertDescription className="text-emerald-200">
                    Consolidation completed successfully. Your memories have been optimized.
                  </AlertDescription>
                </Alert>
              )}

              {/* Details breakdown */}
              <div className="pt-4 border-t border-white/10">
                <h3 className="text-sm font-semibold text-white/90 mb-3">Process Details</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5">
                    <span className="text-white/70">Total memories processed</span>
                    <Badge className="bg-white/10 text-white">{result.analyzed}</Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5">
                    <span className="text-white/70">Consolidation rate</span>
                    <Badge className="bg-blue-500/20 text-blue-300">
                      {result.analyzed > 0 ? ((result.consolidated / result.analyzed) * 100).toFixed(1) : 0}%
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5">
                    <span className="text-white/70">Archival rate</span>
                    <Badge className="bg-amber-500/20 text-amber-300">
                      {result.analyzed > 0 ? ((result.archived / result.analyzed) * 100).toFixed(1) : 0}%
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5">
                    <span className="text-white/70">Retention rate</span>
                    <Badge className="bg-emerald-500/20 text-emerald-300">
                      {result.analyzed > 0 ? ((result.kept / result.analyzed) * 100).toFixed(1) : 0}%
                    </Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {!result && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="p-6 bg-rose-500/10 border border-rose-500/30 rounded-2xl mb-4">
              <Archive className="h-12 w-12 text-rose-400 mx-auto" />
            </div>
            <h3 className="text-xl font-semibold text-white/90 mb-2">
              Ready to Consolidate
            </h3>
            <p className="text-white/60 max-w-md">
              Configure the settings above and run consolidation to optimize your memory storage
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
