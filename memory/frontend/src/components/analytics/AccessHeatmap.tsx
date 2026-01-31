import { useMemo } from 'react';
import { format, eachDayOfInterval, subDays, startOfDay } from 'date-fns';
import type { Memory } from '../../types/memory';

interface AccessHeatmapProps {
  memories: Memory[];
}

export function AccessHeatmap({ memories }: AccessHeatmapProps) {
  const heatmapData = useMemo(() => {
    const today = new Date();
    const ninetyDaysAgo = subDays(today, 90);
    const days = eachDayOfInterval({ start: ninetyDaysAgo, end: today });

    const activityMap = new Map(
      days.map(day => [format(startOfDay(day), 'yyyy-MM-dd'), 0])
    );

    memories.forEach(memory => {
      const accessDate = format(startOfDay(new Date(memory.last_accessed)), 'yyyy-MM-dd');
      if (activityMap.has(accessDate)) {
        activityMap.set(accessDate, activityMap.get(accessDate)! + 1);
      }
    });

    const maxActivity = Math.max(...Array.from(activityMap.values()));

    // Group by weeks
    const weeks: Array<Array<{ date: Date; count: number; intensity: number }>> = [];
    let currentWeek: Array<{ date: Date; count: number; intensity: number }> = [];

    days.forEach((day, index) => {
      const dateKey = format(startOfDay(day), 'yyyy-MM-dd');
      const count = activityMap.get(dateKey) || 0;
      const intensity = maxActivity > 0 ? count / maxActivity : 0;

      currentWeek.push({ date: day, count, intensity });

      if ((index + 1) % 7 === 0 || index === days.length - 1) {
        weeks.push(currentWeek);
        currentWeek = [];
      }
    });

    return { weeks, maxActivity };
  }, [memories]);

  const getColor = (intensity: number) => {
    if (intensity === 0) return '#f3f4f6';
    if (intensity < 0.25) return '#dbeafe';
    if (intensity < 0.5) return '#93c5fd';
    if (intensity < 0.75) return '#3b82f6';
    return '#1e40af';
  };

  return (
    <div className="p-4 overflow-x-auto">
      <div className="inline-block">
        <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${heatmapData.weeks.length}, 12px)` }}>
          {heatmapData.weeks.map((week, weekIndex) => (
            <div key={weekIndex} className="grid gap-1" style={{ gridTemplateRows: 'repeat(7, 12px)' }}>
              {week.map((day, dayIndex) => (
                <div
                  key={dayIndex}
                  className="rounded-sm transition-all duration-200 hover:scale-125 hover:ring-2 hover:ring-blue-500 cursor-pointer"
                  style={{
                    backgroundColor: getColor(day.intensity),
                  }}
                  title={`${format(day.date, 'MMM dd, yyyy')}: ${day.count} accesses`}
                />
              ))}
            </div>
          ))}
        </div>
        <div className="flex items-center gap-2 mt-4 text-xs text-gray-600">
          <span>Less</span>
          <div className="flex gap-1">
            {[0, 0.2, 0.4, 0.6, 0.8].map((intensity, i) => (
              <div
                key={i}
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: getColor(intensity) }}
              />
            ))}
          </div>
          <span>More</span>
        </div>
      </div>
    </div>
  );
}
