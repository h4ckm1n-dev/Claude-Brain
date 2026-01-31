import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { BarChart3, TrendingUp, TrendingDown } from 'lucide-react';
import { Memory } from '../../types/memory';
import { useMemo } from 'react';
import { MemoryTypeBadge } from '../memory/MemoryTypeBadge';

interface TypeBreakdownProps {
  memories?: Memory[];
}

const TYPE_ICONS: Record<string, string> = {
  error: '❌',
  decision: '✅',
  pattern: '🔷',
  docs: '📚',
  learning: '💡',
  context: '🔍',
};

const TYPE_COLORS: Record<string, string> = {
  error: 'from-red-500 to-red-600',
  decision: 'from-green-500 to-green-600',
  pattern: 'from-blue-500 to-blue-600',
  docs: 'from-purple-500 to-purple-600',
  learning: 'from-amber-500 to-amber-600',
  context: 'from-gray-500 to-gray-600',
};

export function TypeBreakdown({ memories }: TypeBreakdownProps) {
  const typeStats = useMemo(() => {
    if (!memories || memories.length === 0) return [];

    const typeMap = new Map<string, { count: number; resolved: number; recent: number }>();

    const oneDayAgo = Date.now() - 24 * 60 * 60 * 1000;

    memories.forEach(memory => {
      const existing = typeMap.get(memory.type) || { count: 0, resolved: 0, recent: 0 };

      typeMap.set(memory.type, {
        count: existing.count + 1,
        resolved: existing.resolved + (memory.resolved ? 1 : 0),
        recent: existing.recent + (new Date(memory.created_at).getTime() > oneDayAgo ? 1 : 0),
      });
    });

    return Array.from(typeMap.entries())
      .map(([type, data]) => ({
        type,
        count: data.count,
        resolved: data.resolved,
        recent: data.recent,
        percentage: (data.count / memories.length) * 100,
      }))
      .sort((a, b) => b.count - a.count);
  }, [memories]);

  const totalMemories = memories?.length || 0;
  const totalRecent = typeStats.reduce((sum, t) => sum + t.recent, 0);

  return (
    <Card className="shadow-lg border-l-4 border-l-cyan-500">
      <CardHeader>
        <div className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-cyan-600" />
          <CardTitle>Memory Type Analysis</CardTitle>
        </div>
        <CardDescription>Detailed breakdown by type with trends</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {typeStats.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No type data available
          </div>
        ) : (
          <>
            {/* Summary */}
            <div className="grid grid-cols-3 gap-4 p-4 bg-gradient-to-br from-cyan-50 to-blue-50 dark:from-cyan-950 dark:to-blue-950 rounded-lg">
              <div className="text-center">
                <div className="text-2xl font-bold text-cyan-700 dark:text-cyan-300">
                  {typeStats.length}
                </div>
                <div className="text-xs text-cyan-600 dark:text-cyan-400">
                  Types Used
                </div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-cyan-700 dark:text-cyan-300">
                  {totalMemories}
                </div>
                <div className="text-xs text-cyan-600 dark:text-cyan-400">
                  Total Memories
                </div>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center gap-1">
                  <div className="text-2xl font-bold text-cyan-700 dark:text-cyan-300">
                    {totalRecent}
                  </div>
                  {totalRecent > 0 && <TrendingUp className="h-4 w-4 text-green-600" />}
                </div>
                <div className="text-xs text-cyan-600 dark:text-cyan-400">
                  Last 24h
                </div>
              </div>
            </div>

            {/* Type List */}
            <div className="space-y-3">
              {typeStats.map((typeStat) => {
                const Icon = TYPE_ICONS[typeStat.type] || '📝';
                const gradientClass = TYPE_COLORS[typeStat.type] || 'from-gray-500 to-gray-600';
                const resolvedPercentage = typeStat.count > 0 ? (typeStat.resolved / typeStat.count) * 100 : 0;

                return (
                  <div
                    key={typeStat.type}
                    className="p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="text-2xl">{Icon}</div>
                        <div>
                          <MemoryTypeBadge type={typeStat.type} />
                          <div className="text-xs text-muted-foreground mt-1">
                            {typeStat.percentage.toFixed(1)}% of total
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold">
                          {typeStat.count}
                        </div>
                        {typeStat.recent > 0 && (
                          <div className="flex items-center gap-1 text-xs text-green-600 justify-end">
                            <TrendingUp className="h-3 w-3" />
                            +{typeStat.recent} today
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden mb-2">
                      <div
                        className={`bg-gradient-to-r ${gradientClass} h-full rounded-full transition-all duration-500`}
                        style={{ width: `${typeStat.percentage}%` }}
                      />
                    </div>

                    {/* Additional Stats */}
                    {typeStat.type === 'error' && (
                      <div className="flex items-center justify-between text-xs mt-2">
                        <span className="text-muted-foreground">Resolved:</span>
                        <div className="flex items-center gap-2">
                          <div className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="bg-green-500 h-full rounded-full"
                              style={{ width: `${resolvedPercentage}%` }}
                            />
                          </div>
                          <span className="font-medium">
                            {typeStat.resolved}/{typeStat.count}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
