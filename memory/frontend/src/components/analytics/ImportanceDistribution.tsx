import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Memory } from '../../types/memory';

interface ImportanceDistributionProps {
  memories: Memory[];
}

export function ImportanceDistribution({ memories }: ImportanceDistributionProps) {
  const data = useMemo(() => {
    // Create buckets for importance scores (0-0.1, 0.1-0.2, ..., 0.9-1.0)
    const buckets = Array.from({ length: 10 }, (_, i) => ({
      range: `${(i * 0.1).toFixed(1)}-${((i + 1) * 0.1).toFixed(1)}`,
      count: 0,
      bucket: i,
    }));

    memories.forEach(memory => {
      const bucketIndex = Math.min(Math.floor(memory.importance_score * 10), 9);
      buckets[bucketIndex].count++;
    });

    return buckets;
  }, [memories]);

  const getColor = (bucket: number) => {
    if (bucket < 3) return '#ef4444'; // red for low importance
    if (bucket < 7) return '#f59e0b'; // amber for medium importance
    return '#22c55e'; // green for high importance
  };

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
        <XAxis
          dataKey="range"
          tick={{ fontSize: 11 }}
          label={{ value: 'Importance Score', position: 'insideBottom', offset: -5, fontSize: 12 }}
        />
        <YAxis
          tick={{ fontSize: 12 }}
          label={{ value: 'Count', angle: -90, position: 'insideLeft', fontSize: 12 }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
          }}
          formatter={(value: number | undefined) => [`${value || 0} memories`, 'Count']}
        />
        <Bar
          dataKey="count"
          radius={[8, 8, 0, 0]}
          animationDuration={800}
          animationBegin={0}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={getColor(entry.bucket)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
