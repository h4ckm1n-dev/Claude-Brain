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
  Info,
  Activity,
  Sparkles,
  Target,
  Clock,
  Repeat,
  Moon,
  Layers,
  Network,
} from 'lucide-react';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Slider } from '../components/ui/slider';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { apiClient } from '../lib/api';
import { AuditTimeline } from '../components/AuditTimeline';
import { useUpdateQualityScores } from '../hooks/useQuality';
import { useUpdateLifecycleStates } from '../hooks/useLifecycle';
import { useTriggerPatternDetection } from '../hooks/useAnalytics';
import {
  useSpacedRepetition,
  useTopics,
  useTopicTimeline,
  useReplay,
  useProjectReplay,
  useUnderutilizedReplay,
  useDream,
  useCoAccessStats,
  useResetCoAccess,
  useReconsolidate,
} from '../hooks/useBrain';

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

  // Phase 3-4: Manual triggers for intelligence systems
  const updateQualityScores = useUpdateQualityScores();
  const updateLifecycleStates = useUpdateLifecycleStates();
  const triggerPatternDetection = useTriggerPatternDetection();

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
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]">
      <Header title="Brain Intelligence" />

      <div className="p-6 space-y-6">
        {/* Hero Section */}
        <div className="bg-gradient-to-br from-blue-600 via-cyan-600 to-indigo-600 rounded-2xl p-8 shadow-2xl">
          <div className="flex items-center gap-4 mb-4">
            <div className="p-4 bg-white/20 backdrop-blur-sm rounded-xl">
              <Brain className="h-10 w-10 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">Brain Intelligence System</h1>
              <p className="text-blue-100 mt-1">
                Autonomous learning, adaptive importance, and intelligent forgetting
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            <div className="bg-white/10 backdrop-blur rounded-xl p-4 border border-white/20">
              <p className="text-sm text-blue-100">Total Memories</p>
              <p className="text-3xl font-bold text-white">{totalMemories.toLocaleString()}</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-xl p-4 border border-white/20">
              <p className="text-sm text-blue-100">Auto-Linked Relationships</p>
              <p className="text-3xl font-bold text-white">{(brainStats?.relationships || 0).toLocaleString()}</p>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-xl p-4 border border-white/20">
              <p className="text-sm text-blue-100">High-Utility Memories</p>
              <p className="text-3xl font-bold text-white">{(utilityDist?.high || 0).toLocaleString()}</p>
            </div>
          </div>
        </div>

        {/* Feature Status */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="bg-[#0f0f0f] border border-white/10 border-l-4 border-l-emerald-500 shadow-xl hover:shadow-emerald-500/10 transition-all">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg text-white">
                <TrendingUp className="h-5 w-5 text-emerald-400" />
                Adaptive Learning
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Badge className="mb-2 bg-emerald-500 text-white">Active</Badge>
              <p className="text-sm text-white/70">
                Importance scores adapt based on access patterns and usage
              </p>
            </CardContent>
          </Card>

          <Card className="bg-[#0f0f0f] border border-white/10 border-l-4 border-l-blue-500 shadow-xl hover:shadow-blue-500/10 transition-all">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg text-white">
                <LinkIcon className="h-5 w-5 text-blue-400" />
                Auto-Linking
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Badge className="mb-2 bg-blue-500 text-white">Active</Badge>
              <p className="text-sm text-white/70">
                Creates FIXES, RELATED, TEMPORAL relationships automatically
              </p>
            </CardContent>
          </Card>

          <Card className="bg-[#0f0f0f] border border-white/10 border-l-4 border-l-orange-500 shadow-xl hover:shadow-orange-500/10 transition-all">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg text-white">
                <Archive className="h-5 w-5 text-orange-400" />
                Smart Forgetting
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Badge className="mb-2 bg-orange-500 text-white">Active</Badge>
              <p className="text-sm text-white/70">
                Archives low-utility memories intelligently, not just by age
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Utility Distribution */}
        {utilityDist && (
          <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-amber-500/10 transition-all">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <Zap className="h-5 w-5 text-amber-400" />
                Memory Utility Distribution
              </CardTitle>
              <CardDescription className="text-white/60">
                Based on access patterns, relationships, and importance scores
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* High Utility */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-white/90">High Utility (≥0.7)</span>
                    <span className="text-sm text-white/60">
                      {utilityDist.high} memories ({((utilityDist.high / totalMemories) * 100).toFixed(1)}%)
                    </span>
                  </div>
                  <div className="w-full bg-[#0a0a0a] rounded-full h-3 border border-white/5">
                    <div
                      className="bg-gradient-to-r from-emerald-500 to-green-500 h-3 rounded-full transition-all duration-500 shadow-lg shadow-emerald-500/30"
                      style={{ width: `${(utilityDist.high / totalMemories) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Medium Utility */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-white/90">Medium Utility (0.3-0.7)</span>
                    <span className="text-sm text-white/60">
                      {utilityDist.medium} memories ({((utilityDist.medium / totalMemories) * 100).toFixed(1)}%)
                    </span>
                  </div>
                  <div className="w-full bg-[#0a0a0a] rounded-full h-3 border border-white/5">
                    <div
                      className="bg-gradient-to-r from-amber-500 to-yellow-500 h-3 rounded-full transition-all duration-500 shadow-lg shadow-amber-500/30"
                      style={{ width: `${(utilityDist.medium / totalMemories) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Low Utility */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-white/90">Low Utility (&lt;0.3)</span>
                    <span className="text-sm text-white/60">
                      {utilityDist.low} memories ({((utilityDist.low / totalMemories) * 100).toFixed(1)}%)
                    </span>
                  </div>
                  <div className="w-full bg-[#0a0a0a] rounded-full h-3 border border-white/5">
                    <div
                      className="bg-gradient-to-r from-orange-500 to-red-500 h-3 rounded-full transition-all duration-500 shadow-lg shadow-red-500/30"
                      style={{ width: `${(utilityDist.low / totalMemories) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Phase 3-4: Manual Triggers for Intelligence Systems */}
        <Card className="bg-[#0f0f0f] border-white/10 shadow-xl hover:shadow-purple-500/10 transition-all">
          <CardHeader className="border-b border-white/5">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-purple-400" />
              <CardTitle className="text-white">Manual Intelligence Triggers</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Manually trigger Phase 3-4 intelligence systems
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-gradient-to-br from-emerald-500/10 to-green-500/10 border border-emerald-500/20">
                <div className="flex items-center gap-2 mb-3">
                  <Target className="h-5 w-5 text-emerald-400" />
                  <h3 className="font-medium text-white">Pattern Detection</h3>
                </div>
                <p className="text-xs text-white/60 mb-4">
                  Analyze memory patterns and create clusters
                </p>
                <Button
                  onClick={() => triggerPatternDetection.mutate()}
                  disabled={triggerPatternDetection.isPending}
                  className="w-full bg-emerald-500 hover:bg-emerald-600 text-white"
                  size="sm"
                >
                  {triggerPatternDetection.isPending ? (
                    <>
                      <RefreshCw className="mr-2 h-3 w-3 animate-spin" />
                      Running...
                    </>
                  ) : (
                    <>
                      <Play className="mr-2 h-3 w-3" />
                      Run Detection
                    </>
                  )}
                </Button>
                {triggerPatternDetection.isSuccess && (
                  <Badge className="mt-2 w-full bg-emerald-500/20 text-emerald-300">
                    ✓ Complete
                  </Badge>
                )}
              </div>

              <div className="p-4 rounded-lg bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-blue-500/20">
                <div className="flex items-center gap-2 mb-3">
                  <TrendingUp className="h-5 w-5 text-blue-400" />
                  <h3 className="font-medium text-white">Quality Scores</h3>
                </div>
                <p className="text-xs text-white/60 mb-4">
                  Update memory quality scores system-wide
                </p>
                <Button
                  onClick={() => updateQualityScores.mutate()}
                  disabled={updateQualityScores.isPending}
                  className="w-full bg-blue-500 hover:bg-blue-600 text-white"
                  size="sm"
                >
                  {updateQualityScores.isPending ? (
                    <>
                      <RefreshCw className="mr-2 h-3 w-3 animate-spin" />
                      Updating...
                    </>
                  ) : (
                    <>
                      <Play className="mr-2 h-3 w-3" />
                      Update Scores
                    </>
                  )}
                </Button>
                {updateQualityScores.isSuccess && (
                  <Badge className="mt-2 w-full bg-blue-500/20 text-blue-300">
                    ✓ Complete
                  </Badge>
                )}
              </div>

              <div className="p-4 rounded-lg bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-500/20">
                <div className="flex items-center gap-2 mb-3">
                  <Activity className="h-5 w-5 text-purple-400" />
                  <h3 className="font-medium text-white">Memory States</h3>
                </div>
                <p className="text-xs text-white/60 mb-4">
                  Update lifecycle states for all memories
                </p>
                <Button
                  onClick={() => updateLifecycleStates.mutate()}
                  disabled={updateLifecycleStates.isPending}
                  className="w-full bg-purple-500 hover:bg-purple-600 text-white"
                  size="sm"
                >
                  {updateLifecycleStates.isPending ? (
                    <>
                      <RefreshCw className="mr-2 h-3 w-3 animate-spin" />
                      Updating...
                    </>
                  ) : (
                    <>
                      <Play className="mr-2 h-3 w-3" />
                      Update States
                    </>
                  )}
                </Button>
                {updateLifecycleStates.isSuccess && (
                  <Badge className="mt-2 w-full bg-purple-500/20 text-purple-300">
                    ✓ Complete
                  </Badge>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Phase 3-4: Recent Audit Activity */}
        <Card className="bg-[#0f0f0f] border-white/10 shadow-xl hover:shadow-amber-500/10 transition-all">
          <CardHeader className="border-b border-white/5">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-amber-400" />
              <CardTitle className="text-white">Recent Audit Activity</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Latest system changes and intelligence operations
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <AuditTimeline limit={20} />
          </CardContent>
        </Card>

        {/* Action Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Relationship Inference */}
          <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-blue-500/10 transition-all">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <LinkIcon className="h-5 w-5 text-blue-400" />
                Infer Relationships
              </CardTitle>
              <CardDescription className="text-white/60">
                Automatically create links between related memories
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2 p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
                <Label className="text-white/90">Lookback Days: {lookbackDays}</Label>
                <div className="w-full">
                  <Slider
                    value={[lookbackDays]}
                    onValueChange={(v) => setLookbackDays(v[0])}
                    min={7}
                    max={90}
                    step={1}
                  />
                </div>
                <p className="text-xs text-white/50">
                  Search for solutions created within this many days after errors
                </p>
              </div>

              <Button
                onClick={() => relationshipMutation.mutate()}
                disabled={relationshipMutation.isPending}
                className="w-full bg-blue-500 hover:bg-blue-600 text-white shadow-lg shadow-blue-500/20"
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
                <div className="rounded-lg bg-blue-500/10 border border-blue-500/30 p-4 space-y-2">
                  <p className="text-sm font-medium text-blue-300">Results:</p>
                  <div className="grid grid-cols-2 gap-2 text-sm text-white/90">
                    <div>FIXES links:</div>
                    <div className="font-bold">{relationshipMutation.data.fixes_links}</div>
                    <div>RELATED links:</div>
                    <div className="font-bold">{relationshipMutation.data.related_links}</div>
                    <div>TEMPORAL links:</div>
                    <div className="font-bold">{relationshipMutation.data.temporal_links}</div>
                    <div className="col-span-2 pt-2 border-t border-blue-500/30">
                      Total: <span className="font-bold">{relationshipMutation.data.total_links}</span>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Adaptive Importance */}
          <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-emerald-500/10 transition-all">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <TrendingUp className="h-5 w-5 text-emerald-400" />
                Update Importance Scores
              </CardTitle>
              <CardDescription className="text-white/60">
                Recalculate importance based on access patterns
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2 p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
                <Label className="text-white/90">Batch Size: {importanceLimit}</Label>
                <div className="w-full">
                  <Slider
                    value={[importanceLimit]}
                    onValueChange={(v) => setImportanceLimit(v[0])}
                    min={10}
                    max={500}
                    step={10}
                  />
                </div>
                <p className="text-xs text-white/50">
                  Number of memories to update per run
                </p>
              </div>

              <Button
                onClick={() => importanceMutation.mutate()}
                disabled={importanceMutation.isPending}
                className="w-full bg-emerald-500 hover:bg-emerald-600 text-white shadow-lg shadow-emerald-500/20"
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
                <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/30 p-4">
                  <p className="text-sm font-medium text-emerald-300">
                    Updated {importanceMutation.data.updated} memories
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Utility Archival */}
          <Card className="lg:col-span-2 bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-orange-500/10 transition-all">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <Archive className="h-5 w-5 text-orange-400" />
                Utility-Based Archival
              </CardTitle>
              <CardDescription className="text-white/60">
                Archive low-utility memories intelligently
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2 p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
                  <Label className="text-white/90">Utility Threshold: {utilityThreshold.toFixed(2)}</Label>
                  <div className="w-full">
                    <Slider
                      value={[utilityThreshold]}
                      onValueChange={(v) => setUtilityThreshold(v[0])}
                      min={0.1}
                      max={0.9}
                      step={0.05}
                    />
                  </div>
                  <p className="text-xs text-white/50">
                    Archive if utility score &lt; this value (lower = more aggressive)
                  </p>
                </div>

                <div className="space-y-2 p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
                  <Label className="text-white/90">Max Archive: {archiveMax}</Label>
                  <div className="w-full">
                    <Slider
                      value={[archiveMax]}
                      onValueChange={(v) => setArchiveMax(v[0])}
                      min={10}
                      max={500}
                      step={10}
                    />
                  </div>
                  <p className="text-xs text-white/50">
                    Maximum memories to archive in one run
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                <Switch
                  checked={dryRun}
                  onCheckedChange={setDryRun}
                />
                <Label htmlFor="dry-run" className="cursor-pointer text-amber-200">
                  Dry Run (preview only, don't actually archive)
                </Label>
              </div>

              <Button
                onClick={() => archivalMutation.mutate()}
                disabled={archivalMutation.isPending}
                variant={dryRun ? 'outline' : 'default'}
                className={`w-full ${
                  dryRun
                    ? 'bg-[#0a0a0a] border-white/10 text-white/90 hover:bg-white/5'
                    : 'bg-orange-500 hover:bg-orange-600 text-white shadow-lg shadow-orange-500/20'
                }`}
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
                    ? 'bg-blue-500/10 border border-blue-500/30'
                    : 'bg-orange-500/10 border border-orange-500/30'
                }`}>
                  <p className="text-sm font-medium mb-2 text-white/90">
                    {archivalMutation.data.dry_run ? 'Preview:' : 'Archived:'}
                  </p>
                  <p className="text-2xl font-bold text-white">
                    {archivalMutation.data.archived} memories
                  </p>
                  <p className="text-xs text-white/60 mt-2">
                    Threshold: {archivalMutation.data.threshold.toFixed(2)}
                    {archivalMutation.data.dry_run && ' (no changes made)'}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Spaced Repetition Section */}
        <SpacedRepetitionSection />

        {/* Topic Discovery Section */}
        <TopicDiscoverySection />

        {/* Memory Replay Section */}
        <MemoryReplaySection />

        {/* Co-Access Intelligence Section */}
        <CoAccessSection />

        {/* Info Card */}
        <Card className="bg-[#0f0f0f] border border-white/10 border-l-4 border-l-blue-500 shadow-xl hover:shadow-blue-500/10 transition-all">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <Info className="h-5 w-5 text-blue-400" />
              About Brain Intelligence
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-white/70">
              The Brain Intelligence system makes your memory autonomous and adaptive:
            </p>
            <ul className="text-sm space-y-2 ml-4 list-disc text-white/70">
              <li>
                <strong className="text-white/90">Adaptive Learning</strong>: Importance scores evolve based on how often memories are accessed
              </li>
              <li>
                <strong className="text-white/90">Auto-Linking</strong>: Creates relationships automatically (FIXES errors, RELATED concepts, TEMPORAL sequences)
              </li>
              <li>
                <strong className="text-white/90">Smart Forgetting</strong>: Archives based on utility (access + relationships + importance), not just age
              </li>
              <li>
                <strong className="text-white/90">Protected Memories</strong>: Decisions, patterns, and resolved errors are never archived
              </li>
            </ul>
            <p className="text-sm text-white/70">
              These features run automatically every 24 hours when the scheduler is enabled. Use this page to run them manually.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Sub-components for new brain features

function SpacedRepetitionSection() {
  const { data: items, isLoading } = useSpacedRepetition(20);
  const reconsolidate = useReconsolidate();

  return (
    <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-green-400" />
          <CardTitle className="text-white">Spaced Repetition</CardTitle>
        </div>
        <CardDescription className="text-white/60">
          Memories due for review to strengthen retention
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 max-h-[400px] overflow-y-auto">
        {isLoading && <p className="text-white/50">Loading...</p>}
        {items?.map((item) => (
          <div key={item.id} className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5">
            <div className="flex-1 min-w-0 mr-3">
              <div className="flex items-center gap-2 mb-1">
                <Badge className="bg-green-500/20 text-green-300 border border-green-500/30 text-xs">
                  {item.type}
                </Badge>
                <span className="text-xs text-white/40">
                  strength: {(item.strength * 100).toFixed(0)}%
                </span>
                <span className="text-xs text-white/40">
                  reviews: {item.review_count}
                </span>
              </div>
              <p className="text-sm text-white/80 line-clamp-1">{item.content}</p>
            </div>
            <Button
              size="sm"
              onClick={() => reconsolidate.mutate({ memoryId: item.id, accessContext: 'spaced-repetition-review' })}
              disabled={reconsolidate.isPending}
              className="bg-green-500/20 text-green-300 border border-green-500/30 hover:bg-green-500/30"
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              Review
            </Button>
          </div>
        ))}
        {items?.length === 0 && (
          <p className="text-white/50 text-center py-4">No memories due for review</p>
        )}
      </CardContent>
    </Card>
  );
}

function TopicDiscoverySection() {
  const [selectedTopic, setSelectedTopic] = useState<string>('');
  const { data: topics, isLoading } = useTopics();
  const { data: timeline } = useTopicTimeline(selectedTopic, 30);

  return (
    <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Layers className="h-5 w-5 text-purple-400" />
          <CardTitle className="text-white">Topic Discovery</CardTitle>
        </div>
        <CardDescription className="text-white/60">
          Automatically discovered topic clusters from your memories
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading && <p className="text-white/50">Loading topics...</p>}
        <div className="flex flex-wrap gap-2">
          {topics?.map((topic) => (
            <button
              key={topic.name}
              onClick={() => setSelectedTopic(selectedTopic === topic.name ? '' : topic.name)}
              className={`px-3 py-2 rounded-lg text-sm transition-all ${
                selectedTopic === topic.name
                  ? 'bg-purple-500/30 text-purple-200 border border-purple-500/50'
                  : 'bg-[#0a0a0a] text-white/60 border border-white/10 hover:border-purple-500/30'
              }`}
            >
              {topic.name}
              <Badge className="ml-2 bg-white/10 text-white/50 border-0 text-xs">{topic.size}</Badge>
            </button>
          ))}
        </div>
        {topics?.length === 0 && (
          <p className="text-white/50 text-center py-4">No topics discovered yet</p>
        )}

        {selectedTopic && timeline && timeline.length > 0 && (
          <div className="mt-4 space-y-2">
            <h4 className="text-sm font-medium text-purple-300">Timeline: {selectedTopic}</h4>
            {timeline.map((entry, i) => (
              <div key={i} className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-white/40">{new Date(entry.date).toLocaleDateString()}</span>
                  <Badge className="bg-purple-500/20 text-purple-300 border border-purple-500/30 text-xs">
                    {entry.count} memories
                  </Badge>
                </div>
                {entry.memories.slice(0, 2).map((m) => (
                  <p key={m.id} className="text-xs text-white/60 line-clamp-1">{m.content}</p>
                ))}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MemoryReplaySection() {
  const [replayProject, setReplayProject] = useState('');
  const replay = useReplay();
  const projectReplay = useProjectReplay();
  const underutilizedReplay = useUnderutilizedReplay();
  const dream = useDream();

  const lastResult = replay.data || projectReplay.data || underutilizedReplay.data;
  const isPending = replay.isPending || projectReplay.isPending || underutilizedReplay.isPending || dream.isPending;

  return (
    <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Repeat className="h-5 w-5 text-amber-400" />
          <CardTitle className="text-white">Memory Replay</CardTitle>
        </div>
        <CardDescription className="text-white/60">
          Replay memories to strengthen connections and discover new insights
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <Button
            onClick={() => replay.mutate({})}
            disabled={isPending}
            className="bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30"
          >
            <Play className="h-4 w-4 mr-2" />
            Random Replay
          </Button>
          <Button
            onClick={() => underutilizedReplay.mutate({})}
            disabled={isPending}
            className="bg-orange-500/20 text-orange-300 border border-orange-500/30 hover:bg-orange-500/30"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Underutilized Replay
          </Button>
        </div>

        <div className="flex gap-2">
          <input
            value={replayProject}
            onChange={(e) => setReplayProject(e.target.value)}
            placeholder="Project name for replay"
            className="flex-1 px-3 py-2 rounded-lg bg-[#0a0a0a] border border-white/10 text-white text-sm"
          />
          <Button
            onClick={() => projectReplay.mutate({ project: replayProject })}
            disabled={isPending || !replayProject}
            className="bg-blue-500/20 text-blue-300 border border-blue-500/30 hover:bg-blue-500/30"
          >
            Project Replay
          </Button>
        </div>

        <Button
          onClick={() => dream.mutate(60)}
          disabled={isPending}
          className="w-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/30"
        >
          <Moon className="h-4 w-4 mr-2" />
          {dream.isPending ? 'Dreaming...' : 'Dream Mode (60s)'}
        </Button>

        {dream.data && (
          <div className="p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/30">
            <p className="text-sm text-indigo-200">
              Found {dream.data.connections_found} new connections in {dream.data.duration_seconds}s
            </p>
            {dream.data.insights?.length > 0 && (
              <ul className="mt-2 space-y-1">
                {dream.data.insights.map((insight, i) => (
                  <li key={i} className="text-xs text-indigo-300/80">- {insight}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {lastResult && lastResult.memories && lastResult.memories.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm text-amber-300">Replayed {lastResult.replayed} memories:</p>
            {lastResult.memories.slice(0, 5).map((m) => (
              <div key={m.id} className="p-2 rounded bg-[#0a0a0a] border border-white/5">
                <div className="flex items-center gap-2 mb-1">
                  <Badge className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs">{m.type}</Badge>
                </div>
                <p className="text-xs text-white/70 line-clamp-1">{m.content}</p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CoAccessSection() {
  const { data: stats, isLoading } = useCoAccessStats();
  const resetCoAccess = useResetCoAccess();

  return (
    <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Network className="h-5 w-5 text-cyan-400" />
            <CardTitle className="text-white">Co-Access Intelligence</CardTitle>
          </div>
          <Button
            size="sm"
            onClick={() => resetCoAccess.mutate()}
            disabled={resetCoAccess.isPending}
            variant="outline"
            className="border-red-500/30 text-red-300 hover:bg-red-500/20"
          >
            Reset
          </Button>
        </div>
        <CardDescription className="text-white/60">
          Memories frequently accessed together may have implicit relationships
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading && <p className="text-white/50">Loading...</p>}
        <div className="p-3 rounded-lg bg-[#0a0a0a] border border-white/5">
          <p className="text-sm text-white/60">Total Co-Access Pairs</p>
          <p className="text-2xl font-bold text-white">{stats?.total_pairs ?? 0}</p>
        </div>
        {stats?.top_pairs && stats.top_pairs.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm text-cyan-300">Top Co-Accessed Pairs:</p>
            {stats.top_pairs.slice(0, 5).map((pair, i) => (
              <div key={i} className="flex items-center justify-between p-2 rounded bg-[#0a0a0a] border border-white/5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-white/60">{pair.memory_a.slice(0, 8)}</span>
                  <span className="text-xs text-cyan-400">---</span>
                  <span className="text-xs font-mono text-white/60">{pair.memory_b.slice(0, 8)}</span>
                </div>
                <Badge className="bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-xs">
                  {pair.co_access_count}x
                </Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
