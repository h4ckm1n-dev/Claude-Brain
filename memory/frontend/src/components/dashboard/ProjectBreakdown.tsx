import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { FolderKanban, TrendingUp, Calendar } from 'lucide-react';
import { Memory } from '../../types/memory';
import { useMemo } from 'react';
import { Badge } from '../ui/badge';

interface ProjectBreakdownProps {
  memories?: Memory[];
}

export function ProjectBreakdown({ memories }: ProjectBreakdownProps) {
  const projectStats = useMemo(() => {
    if (!memories || memories.length === 0) return [];

    const projectMap = new Map<string, { count: number; types: Set<string>; latest: string }>();

    memories.forEach(memory => {
      const project = memory.project || '_global';
      const existing = projectMap.get(project) || { count: 0, types: new Set(), latest: memory.created_at };

      projectMap.set(project, {
        count: existing.count + 1,
        types: existing.types.add(memory.type),
        latest: memory.created_at > existing.latest ? memory.created_at : existing.latest,
      });
    });

    return Array.from(projectMap.entries())
      .map(([project, data]) => ({
        name: project,
        count: data.count,
        typeCount: data.types.size,
        latest: data.latest,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);
  }, [memories]);

  const totalProjects = projectStats.length;
  const totalMemories = projectStats.reduce((sum, p) => sum + p.count, 0);

  return (
    <Card className="shadow-lg border-l-4 border-l-orange-500 flex flex-col h-full">
      <CardHeader>
        <div className="flex items-center gap-2">
          <FolderKanban className="h-5 w-5 text-orange-600" />
          <CardTitle>Project Distribution</CardTitle>
        </div>
        <CardDescription>Top {totalProjects} projects by memory count</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 flex-1 flex flex-col min-h-0">
        {projectStats.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No project data available
          </div>
        ) : (
          <>
            {/* Summary */}
            <div className="grid grid-cols-2 gap-4 p-4 bg-gradient-to-br from-orange-50 to-amber-50 dark:from-orange-950 dark:to-amber-950 rounded-lg">
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-700 dark:text-orange-300">
                  {totalProjects}
                </div>
                <div className="text-xs text-orange-600 dark:text-orange-400">
                  Active Projects
                </div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-700 dark:text-orange-300">
                  {(totalMemories / totalProjects).toFixed(1)}
                </div>
                <div className="text-xs text-orange-600 dark:text-orange-400">
                  Avg per Project
                </div>
              </div>
            </div>

            {/* Project List */}
            <div className="space-y-3 flex-1 min-h-0 overflow-y-auto">
              {projectStats.map((project, index) => {
                const percentage = (project.count / totalMemories) * 100;
                const isGlobal = project.name === '_global';

                return (
                  <div
                    key={project.name}
                    className="space-y-2 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 flex-1">
                        <div className="flex items-center justify-center w-6 h-6 rounded-full bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-300 text-xs font-bold">
                          {index + 1}
                        </div>
                        <div className="flex-1">
                          <div className="font-medium text-sm truncate">
                            {isGlobal ? (
                              <span className="text-muted-foreground italic">Global</span>
                            ) : (
                              project.name
                            )}
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant="outline" className="text-xs">
                              {project.typeCount} types
                            </Badge>
                            <span className="text-xs text-muted-foreground flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {new Date(project.latest).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-orange-700 dark:text-orange-300">
                          {project.count}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {percentage.toFixed(1)}%
                        </div>
                      </div>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-orange-500 to-amber-500 h-full rounded-full transition-all duration-500"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
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
