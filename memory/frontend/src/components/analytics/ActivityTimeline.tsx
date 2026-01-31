import { useMemo } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { format, subDays, eachDayOfInterval, startOfDay } from 'date-fns';
import type { Memory } from '../../types/memory';

interface ActivityTimelineProps {
  memories: Memory[];
}

export function ActivityTimeline({ memories }: ActivityTimelineProps) {
  const data = useMemo(() => {
    // Get last 30 days
    const today = new Date();
    const thirtyDaysAgo = subDays(today, 30);
    const days = eachDayOfInterval({ start: thirtyDaysAgo, end: today });

    // Initialize data structure
    const activityMap = new Map(
      days.map(day => [
        format(startOfDay(day), 'yyyy-MM-dd'),
        { date: format(day, 'MMM dd'), created: 0, accessed: 0 }
      ])
    );

    // Count created memories
    memories.forEach(memory => {
      const createdDate = format(startOfDay(new Date(memory.created_at)), 'yyyy-MM-dd');
      const accessedDate = format(startOfDay(new Date(memory.last_accessed)), 'yyyy-MM-dd');

      if (activityMap.has(createdDate)) {
        activityMap.get(createdDate)!.created++;
      }

      if (activityMap.has(accessedDate) && accessedDate !== createdDate) {
        activityMap.get(accessedDate)!.accessed++;
      }
    });

    return Array.from(activityMap.values());
  }, [memories]);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="colorCreated" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
          </linearGradient>
          <linearGradient id="colorAccessed" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.8}/>
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 12 }}
          interval="preserveStartEnd"
        />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
          }}
        />
        <Legend />
        <Area
          type="monotone"
          dataKey="created"
          stroke="#3b82f6"
          fillOpacity={1}
          fill="url(#colorCreated)"
          strokeWidth={2}
          name="Created"
          animationDuration={1000}
        />
        <Area
          type="monotone"
          dataKey="accessed"
          stroke="#22c55e"
          fillOpacity={1}
          fill="url(#colorAccessed)"
          strokeWidth={2}
          name="Accessed"
          animationDuration={1000}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
