import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Brain, Sparkles, GitMerge, TrendingUp, Zap } from 'lucide-react';
import { useBrainMetrics, usePerformanceMetrics } from '../../hooks/useBrain';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';

export function AdvancedBrainMetrics() {
  const { data: brainMetrics, isLoading } = useBrainMetrics();
  const { data: perfMetrics } = usePerformanceMetrics(7);

  if (isLoading || !brainMetrics) {
    return (
      <Card className="lg:col-span-3">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-purple-600" />
            Advanced Brain Features
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse">Loading advanced metrics...</div>
        </CardContent>
      </Card>
    );
  }

  // Calculate health scores
  const emotionalScore = Math.round(brainMetrics.emotional_coverage * 100);
  const importanceScore = Math.round(brainMetrics.avg_importance * 100);
  const accessScore = Math.round(brainMetrics.access_rate * 100);

  // Get health status based on scores
  const getHealthStatus = (score: number) => {
    if (score >= 70) return { label: 'Excellent', color: 'text-green-600' };
    if (score >= 50) return { label: 'Good', color: 'text-blue-600' };
    if (score >= 30) return { label: 'Fair', color: 'text-yellow-600' };
    return { label: 'Low', color: 'text-red-600' };
  };

  const emotionalStatus = getHealthStatus(emotionalScore);
  const importanceStatus = getHealthStatus(importanceScore);
  const accessStatus = getHealthStatus(accessScore);

  return (
    <Card className="lg:col-span-3 bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-950 dark:to-pink-950 border-l-4 border-purple-500">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            <CardTitle>Advanced Brain Features</CardTitle>
            <Badge variant="outline" className="ml-2 bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300">
              15/15 Functions
            </Badge>
          </div>
          <Sparkles className="h-5 w-5 text-pink-500 animate-pulse" />
        </div>
        <CardDescription>
          Emotionally aware, self-correcting, and self-optimizing memory system
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Metrics Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {/* Emotional Weighting */}
          <div className="bg-white dark:bg-gray-950 rounded-lg p-4 shadow-sm border border-purple-200 dark:border-purple-800">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-purple-600" />
                <span className="text-sm font-medium">Emotional Coverage</span>
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {emotionalScore}%
              </div>
              <Progress value={emotionalScore} className="h-2" />
              <div className={`text-xs font-medium ${emotionalStatus.color}`}>
                {emotionalStatus.label}
              </div>
              <p className="text-xs text-muted-foreground">
                Memories analyzed for emotional significance
              </p>
            </div>
          </div>

          {/* Conflict Resolution */}
          <div className="bg-white dark:bg-gray-950 rounded-lg p-4 shadow-sm border border-pink-200 dark:border-pink-800">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <GitMerge className="h-4 w-4 text-pink-600" />
                <span className="text-sm font-medium">Conflict Resolution</span>
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-2xl font-bold text-pink-600 dark:text-pink-400">
                {brainMetrics.conflicts_resolved}
              </div>
              <div className="text-xs text-muted-foreground">
                {brainMetrics.conflicts_detected} detected
              </div>
              <p className="text-xs text-muted-foreground">
                Contradictory memories auto-resolved
              </p>
            </div>
          </div>

          {/* Adaptive Importance */}
          <div className="bg-white dark:bg-gray-950 rounded-lg p-4 shadow-sm border border-blue-200 dark:border-blue-800">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-medium">Avg Importance</span>
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {importanceScore}%
              </div>
              <Progress value={importanceScore} className="h-2" />
              <div className={`text-xs font-medium ${importanceStatus.color}`}>
                {importanceStatus.label}
              </div>
              <p className="text-xs text-muted-foreground">
                Self-tuning importance scores
              </p>
            </div>
          </div>

          {/* Access Rate */}
          <div className="bg-white dark:bg-gray-950 rounded-lg p-4 shadow-sm border border-green-200 dark:border-green-800">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-green-600" />
                <span className="text-sm font-medium">Access Rate</span>
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {accessScore}%
              </div>
              <Progress value={accessScore} className="h-2" />
              <div className={`text-xs font-medium ${accessStatus.color}`}>
                {accessStatus.label}
              </div>
              <p className="text-xs text-muted-foreground">
                Memories actively used
              </p>
            </div>
          </div>
        </div>

        {/* Performance Trends */}
        {perfMetrics?.history && perfMetrics.history.length > 1 && (
          <div className="bg-white dark:bg-gray-950 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-800">
            <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              7-Day Performance Trends
            </h4>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-xs text-muted-foreground mb-1">Emotional Coverage</div>
                <div className="text-sm font-medium">
                  {Math.round((perfMetrics.history[perfMetrics.history.length - 1]?.emotional_coverage || 0) * 100)}%
                  <span className="text-xs text-green-600 ml-1">
                    ↑ {Math.round(((perfMetrics.history[perfMetrics.history.length - 1]?.emotional_coverage || 0) -
                        (perfMetrics.history[0]?.emotional_coverage || 0)) * 100)}%
                  </span>
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Avg Importance</div>
                <div className="text-sm font-medium">
                  {Math.round((perfMetrics.history[perfMetrics.history.length - 1]?.avg_importance || 0) * 100)}%
                  <span className="text-xs text-green-600 ml-1">
                    ↑ {Math.round(((perfMetrics.history[perfMetrics.history.length - 1]?.avg_importance || 0) -
                        (perfMetrics.history[0]?.avg_importance || 0)) * 100)}%
                  </span>
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Access Rate</div>
                <div className="text-sm font-medium">
                  {Math.round((perfMetrics.history[perfMetrics.history.length - 1]?.access_rate || 0) * 100)}%
                  <span className="text-xs text-green-600 ml-1">
                    ↑ {Math.round(((perfMetrics.history[perfMetrics.history.length - 1]?.access_rate || 0) -
                        (perfMetrics.history[0]?.access_rate || 0)) * 100)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* System Status */}
        <div className="bg-gradient-to-r from-purple-100 to-pink-100 dark:from-purple-900 dark:to-pink-900 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Brain className="h-4 w-4 text-purple-600" />
            <h4 className="text-sm font-medium">System Capabilities</h4>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
            <div className="flex items-center gap-1">
              <span className="text-green-600">✓</span> Emotional Weighting
            </div>
            <div className="flex items-center gap-1">
              <span className="text-green-600">✓</span> Conflict Detection
            </div>
            <div className="flex items-center gap-1">
              <span className="text-green-600">✓</span> Meta-Learning
            </div>
            <div className="flex items-center gap-1">
              <span className="text-green-600">✓</span> Memory Reconsolidation
            </div>
            <div className="flex items-center gap-1">
              <span className="text-green-600">✓</span> Spaced Repetition
            </div>
            <div className="flex items-center gap-1">
              <span className="text-green-600">✓</span> Adaptive Importance
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
