import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Activity, CheckCircle, AlertTriangle, XCircle, Zap } from 'lucide-react';
import { StatsResponse, GraphStats } from '../../types/memory';
import { DocumentStats } from '../../api/documents';
import { Badge } from '../ui/badge';

interface HealthIndicatorsProps {
  memoryStats?: StatsResponse;
  graphStats?: GraphStats;
  documentStats?: DocumentStats;
}

export function HealthIndicators({ memoryStats, graphStats, documentStats }: HealthIndicatorsProps) {
  // Calculate health scores
  const memoryHealth = memoryStats ? (memoryStats.unresolved_errors === 0 ? 100 : Math.max(0, 100 - (memoryStats.unresolved_errors / memoryStats.total_memories) * 100)) : 0;
  const graphHealth = graphStats?.enabled ? 100 : 0;
  const documentHealth = documentStats?.status === 'green' ? 100 : documentStats?.status === 'error' ? 0 : 50;
  const searchHealth = memoryStats?.hybrid_search_enabled ? 100 : 50;

  const overallHealth = (memoryHealth + graphHealth + documentHealth + searchHealth) / 4;

  const getHealthStatus = (score: number) => {
    if (score >= 90) return { label: 'Excellent', color: 'text-green-600', bg: 'bg-green-100 dark:bg-green-900', icon: CheckCircle };
    if (score >= 70) return { label: 'Good', color: 'text-blue-600', bg: 'bg-blue-100 dark:bg-blue-900', icon: Activity };
    if (score >= 50) return { label: 'Fair', color: 'text-yellow-600', bg: 'bg-yellow-100 dark:bg-yellow-900', icon: AlertTriangle };
    return { label: 'Poor', color: 'text-red-600', bg: 'bg-red-100 dark:bg-red-900', icon: XCircle };
  };

  const overallStatus = getHealthStatus(overallHealth);
  const OverallIcon = overallStatus.icon;

  return (
    <Card className="shadow-lg border-l-4 border-l-green-500">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Zap className="h-5 w-5 text-green-600" />
          <CardTitle>System Health</CardTitle>
        </div>
        <CardDescription>Real-time system status indicators</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Overall Health */}
        <div className={`p-4 rounded-lg ${overallStatus.bg}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <OverallIcon className={`h-8 w-8 ${overallStatus.color}`} />
              <div>
                <div className="text-sm text-muted-foreground">Overall Health</div>
                <div className={`text-2xl font-bold ${overallStatus.color}`}>
                  {overallHealth.toFixed(0)}%
                </div>
              </div>
            </div>
            <Badge className={overallStatus.color}>
              {overallStatus.label}
            </Badge>
          </div>
          <div className="mt-3 w-full bg-white dark:bg-gray-800 rounded-full h-3 overflow-hidden">
            <div
              className="bg-gradient-to-r from-green-500 to-emerald-500 h-full rounded-full transition-all duration-700"
              style={{ width: `${overallHealth}%` }}
            />
          </div>
        </div>

        {/* Individual Components */}
        <div className="space-y-4">
          {/* Memory System */}
          <div className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
            <div className="flex-1">
              <div className="text-sm font-medium">Memory System</div>
              <div className="text-xs text-muted-foreground mt-1">
                {memoryStats?.unresolved_errors || 0} unresolved errors
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-32 bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-blue-500 to-blue-600 h-full rounded-full transition-all duration-500"
                  style={{ width: `${memoryHealth}%` }}
                />
              </div>
              <span className="text-sm font-bold w-12 text-right">
                {memoryHealth.toFixed(0)}%
              </span>
            </div>
          </div>

          {/* Graph Database */}
          <div className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
            <div className="flex-1">
              <div className="text-sm font-medium">Knowledge Graph</div>
              <div className="text-xs text-muted-foreground mt-1">
                {graphStats?.relationships || 0} relationships tracked
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-32 bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-purple-500 to-purple-600 h-full rounded-full transition-all duration-500"
                  style={{ width: `${graphHealth}%` }}
                />
              </div>
              <span className="text-sm font-bold w-12 text-right">
                {graphHealth.toFixed(0)}%
              </span>
            </div>
          </div>

          {/* Document Indexing */}
          <div className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
            <div className="flex-1">
              <div className="text-sm font-medium">Document Index</div>
              <div className="text-xs text-muted-foreground mt-1">
                {documentStats?.total_chunks || 0} chunks indexed
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-32 bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-green-500 to-green-600 h-full rounded-full transition-all duration-500"
                  style={{ width: `${documentHealth}%` }}
                />
              </div>
              <span className="text-sm font-bold w-12 text-right">
                {documentHealth.toFixed(0)}%
              </span>
            </div>
          </div>

          {/* Hybrid Search */}
          <div className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
            <div className="flex-1">
              <div className="text-sm font-medium">Hybrid Search</div>
              <div className="text-xs text-muted-foreground mt-1">
                {memoryStats?.hybrid_search_enabled ? 'Semantic + Keyword' : 'Keyword only'}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-32 bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-amber-500 to-amber-600 h-full rounded-full transition-all duration-500"
                  style={{ width: `${searchHealth}%` }}
                />
              </div>
              <span className="text-sm font-bold w-12 text-right">
                {searchHealth.toFixed(0)}%
              </span>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="pt-4 border-t border-gray-200 dark:border-gray-700 grid grid-cols-2 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-blue-600">
              {((memoryStats?.total_memories || 0) / 1000).toFixed(1)}K
            </div>
            <div className="text-xs text-muted-foreground">Total Entries</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-purple-600">
              {graphStats?.memory_nodes || 0}
            </div>
            <div className="text-xs text-muted-foreground">Graph Nodes</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
