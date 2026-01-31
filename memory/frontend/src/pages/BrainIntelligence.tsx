import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Brain,
  Zap,
  Link as LinkIcon,
  Archive,
  TrendingUp,
  RefreshCw,
  Play,
  Info
} from 'lucide-react';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Slider } from '../components/ui/slider';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { apiClient } from '../lib/api';

interface BrainStats {
  total_memories: number;
  relationships: number;
  utility_distribution: {
    high: number;
    medium: number;
    low: number;
  };
  adaptive_features: {
    importance_scoring: boolean;
    relationship_inference: boolean;
    utility_archival: boolean;
  };
}

interface RelationshipResult {
  success: boolean;
  fixes_links: number;
  related_links: number;
  temporal_links: number;
  total_links: number;
}

interface ImportanceResult {
  success: boolean;
  updated: number;
  limit: number;
}

interface ArchivalResult {
  success: boolean;
  archived: number;
  threshold: number;
  dry_run: boolean;
}

export function BrainIntelligence() {
  const queryClient = useQueryClient();

  // State for parameters
  const [lookbackDays, setLookbackDays] = useState(30);
  const [importanceLimit, setImportanceLimit] = useState(100);
  const [utilityThreshold, setUtilityThreshold] = useState(0.3);
  const [archiveMax, setArchiveMax] = useState(100);
  const [dryRun, setDryRun] = useState(true);

  // Query brain stats
  const { data: brainStats, isLoading: statsLoading } = useQuery<BrainStats>({
    queryKey: ['brain', 'stats'],
    queryFn: () => apiClient.get('/brain/stats').then(r => r.data),
    refetchInterval: 30000, // Refresh every 30s
  });

  // Mutation for relationship inference
  const relationshipMutation = useMutation<RelationshipResult>({
    mutationFn: () =>
      apiClient.post(`/brain/infer-relationships?lookback_days=${lookbackDays}`).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brain', 'stats'] });
      queryClient.invalidateQueries({ queryKey: ['graph', 'stats'] });
    },
  });

  // Mutation for importance update
  const importanceMutation = useMutation<ImportanceResult>({
    mutationFn: () =>
      apiClient.post(`/brain/update-importance?limit=${importanceLimit}`).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brain', 'stats'] });
    },
  });

  // Mutation for utility archival
  const archivalMutation = useMutation<ArchivalResult>({
    mutationFn: () =>
      apiClient.post(
        `/brain/archive-low-utility?threshold=${utilityThreshold}&max_archive=${archiveMax}&dry_run=${dryRun}`
      ).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brain', 'stats'] });
    },
  });

  const totalMemories = brainStats?.total_memories || 0;
  const utilityDist = brainStats?.utility_distribution;

  return (
    <div className="min-h-screen bg-background">
      <Header title="Brain Intelligence" />

      <div className="p-6 space-y-6">
        {/* Hero Section */}
        <div className="bg-gradient-to-br from-purple-600 via-pink-600 to-red-600 rounded-lg p-8 text-white shadow-lg">
          <div className="flex items-center gap-4 mb-4">
            <Brain className="h-12 w-12" />
            <div>
              <h1 className="text-3xl font-bold">Brain Intelligence System</h1>
              <p className="text-purple-100 mt-1">
                Autonomous learning, adaptive importance, and intelligent forgetting
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            <div className="bg-white/10 backdrop-blur rounded-lg p-4">
              <p className="text-sm text-purple-100">Total Memories</p>
              <p className="text-3xl font-bold">{totalMemories.toLocaleString()}</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-4">
              <p className="text-sm text-purple-100">Auto-Linked Relationships</p>
              <p className="text-3xl font-bold">{(brainStats?.relationships || 0).toLocaleString()}</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-4">
              <p className="text-sm text-purple-100">High-Utility Memories</p>
              <p className="text-3xl font-bold">{(utilityDist?.high || 0).toLocaleString()}</p>
            </div>
          </div>
        </div>

        {/* Feature Status */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="border-l-4 border-l-green-500">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <TrendingUp className="h-5 w-5 text-green-600" />
                Adaptive Learning
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Badge variant="default" className="mb-2">Active</Badge>
              <p className="text-sm text-muted-foreground">
                Importance scores adapt based on access patterns and usage
              </p>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-blue-500">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <LinkIcon className="h-5 w-5 text-blue-600" />
                Auto-Linking
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Badge variant="default" className="mb-2">Active</Badge>
              <p className="text-sm text-muted-foreground">
                Creates FIXES, RELATED, TEMPORAL relationships automatically
              </p>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-orange-500">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Archive className="h-5 w-5 text-orange-600" />
                Smart Forgetting
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Badge variant="default" className="mb-2">Active</Badge>
              <p className="text-sm text-muted-foreground">
                Archives low-utility memories intelligently, not just by age
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Utility Distribution */}
        {utilityDist && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-amber-600" />
                Memory Utility Distribution
              </CardTitle>
              <CardDescription>
                Based on access patterns, relationships, and importance scores
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* High Utility */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">High Utility (≥0.7)</span>
                    <span className="text-sm text-muted-foreground">
                      {utilityDist.high} memories ({((utilityDist.high / totalMemories) * 100).toFixed(1)}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                    <div
                      className="bg-gradient-to-r from-green-500 to-emerald-500 h-3 rounded-full transition-all duration-500"
                      style={{ width: `${(utilityDist.high / totalMemories) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Medium Utility */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">Medium Utility (0.3-0.7)</span>
                    <span className="text-sm text-muted-foreground">
                      {utilityDist.medium} memories ({((utilityDist.medium / totalMemories) * 100).toFixed(1)}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                    <div
                      className="bg-gradient-to-r from-yellow-500 to-amber-500 h-3 rounded-full transition-all duration-500"
                      style={{ width: `${(utilityDist.medium / totalMemories) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Low Utility */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">Low Utility (&lt;0.3)</span>
                    <span className="text-sm text-muted-foreground">
                      {utilityDist.low} memories ({((utilityDist.low / totalMemories) * 100).toFixed(1)}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                    <div
                      className="bg-gradient-to-r from-orange-500 to-red-500 h-3 rounded-full transition-all duration-500"
                      style={{ width: `${(utilityDist.low / totalMemories) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Action Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Relationship Inference */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LinkIcon className="h-5 w-5 text-blue-600" />
                Infer Relationships
              </CardTitle>
              <CardDescription>
                Automatically create links between related memories
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Lookback Days: {lookbackDays}</Label>
                <div className="w-full">
                  <Slider
                    value={[lookbackDays]}
                    onValueChange={(v) => setLookbackDays(v[0])}
                    min={7}
                    max={90}
                    step={1}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Search for solutions created within this many days after errors
                </p>
              </div>

              <Button
                onClick={() => relationshipMutation.mutate()}
                disabled={relationshipMutation.isPending}
                className="w-full"
              >
                {relationshipMutation.isPending ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Inferring...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Run Inference
                  </>
                )}
              </Button>

              {relationshipMutation.data && (
                <div className="rounded-lg bg-blue-50 dark:bg-blue-950 p-4 space-y-2">
                  <p className="text-sm font-medium text-blue-900 dark:text-blue-100">Results:</p>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>FIXES links:</div>
                    <div className="font-bold">{relationshipMutation.data.fixes_links}</div>
                    <div>RELATED links:</div>
                    <div className="font-bold">{relationshipMutation.data.related_links}</div>
                    <div>TEMPORAL links:</div>
                    <div className="font-bold">{relationshipMutation.data.temporal_links}</div>
                    <div className="col-span-2 pt-2 border-t border-blue-200 dark:border-blue-800">
                      Total: <span className="font-bold">{relationshipMutation.data.total_links}</span>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Adaptive Importance */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-green-600" />
                Update Importance Scores
              </CardTitle>
              <CardDescription>
                Recalculate importance based on access patterns
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Batch Size: {importanceLimit}</Label>
                <div className="w-full">
                  <Slider
                    value={[importanceLimit]}
                    onValueChange={(v) => setImportanceLimit(v[0])}
                    min={10}
                    max={500}
                    step={10}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Number of memories to update per run
                </p>
              </div>

              <Button
                onClick={() => importanceMutation.mutate()}
                disabled={importanceMutation.isPending}
                className="w-full"
              >
                {importanceMutation.isPending ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Updating...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Update Scores
                  </>
                )}
              </Button>

              {importanceMutation.data && (
                <div className="rounded-lg bg-green-50 dark:bg-green-950 p-4">
                  <p className="text-sm font-medium text-green-900 dark:text-green-100">
                    Updated {importanceMutation.data.updated} memories
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Utility Archival */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Archive className="h-5 w-5 text-orange-600" />
                Utility-Based Archival
              </CardTitle>
              <CardDescription>
                Archive low-utility memories intelligently
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Utility Threshold: {utilityThreshold.toFixed(2)}</Label>
                  <div className="w-full">
                    <Slider
                      value={[utilityThreshold]}
                      onValueChange={(v) => setUtilityThreshold(v[0])}
                      min={0.1}
                      max={0.9}
                      step={0.05}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Archive if utility score &lt; this value (lower = more aggressive)
                  </p>
                </div>

                <div className="space-y-2">
                  <Label>Max Archive: {archiveMax}</Label>
                  <div className="w-full">
                    <Slider
                      value={[archiveMax]}
                      onValueChange={(v) => setArchiveMax(v[0])}
                      min={10}
                      max={500}
                      step={10}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Maximum memories to archive in one run
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 p-4 bg-yellow-50 dark:bg-yellow-950 rounded-lg">
                <Switch
                  checked={dryRun}
                  onCheckedChange={setDryRun}
                />
                <Label htmlFor="dry-run" className="cursor-pointer">
                  Dry Run (preview only, don't actually archive)
                </Label>
              </div>

              <Button
                onClick={() => archivalMutation.mutate()}
                disabled={archivalMutation.isPending}
                variant={dryRun ? 'outline' : 'default'}
                className="w-full"
              >
                {archivalMutation.isPending ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    {dryRun ? 'Preview Archival' : 'Archive Memories'}
                  </>
                )}
              </Button>

              {archivalMutation.data && (
                <div className={`rounded-lg p-4 ${
                  archivalMutation.data.dry_run
                    ? 'bg-blue-50 dark:bg-blue-950'
                    : 'bg-orange-50 dark:bg-orange-950'
                }`}>
                  <p className="text-sm font-medium mb-2">
                    {archivalMutation.data.dry_run ? 'Preview:' : 'Archived:'}
                  </p>
                  <p className="text-2xl font-bold">
                    {archivalMutation.data.archived} memories
                  </p>
                  <p className="text-xs text-muted-foreground mt-2">
                    Threshold: {archivalMutation.data.threshold.toFixed(2)}
                    {archivalMutation.data.dry_run && ' (no changes made)'}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Info Card */}
        <Card className="border-l-4 border-l-purple-500">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Info className="h-5 w-5 text-purple-600" />
              About Brain Intelligence
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              The Brain Intelligence system makes your memory autonomous and adaptive:
            </p>
            <ul className="text-sm space-y-2 ml-4 list-disc text-muted-foreground">
              <li>
                <strong>Adaptive Learning</strong>: Importance scores evolve based on how often memories are accessed
              </li>
              <li>
                <strong>Auto-Linking</strong>: Creates relationships automatically (FIXES errors, RELATED concepts, TEMPORAL sequences)
              </li>
              <li>
                <strong>Smart Forgetting</strong>: Archives based on utility (access + relationships + importance), not just age
              </li>
              <li>
                <strong>Protected Memories</strong>: Decisions, patterns, and resolved errors are never archived
              </li>
            </ul>
            <p className="text-sm text-muted-foreground">
              These features run automatically every 24 hours when the scheduler is enabled. Use this page to run them manually.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
