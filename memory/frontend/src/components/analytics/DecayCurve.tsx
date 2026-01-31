import { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { MemoryType } from '../../types/memory';

const COLORS: Record<MemoryType, string> = {
  [MemoryType.ERROR]: '#ef4444',
  [MemoryType.DECISION]: '#22c55e',
  [MemoryType.PATTERN]: '#3b82f6',
  [MemoryType.DOCS]: '#a855f7',
  [MemoryType.LEARNING]: '#f59e0b',
  [MemoryType.CONTEXT]: '#6b7280',
};

export function DecayCurve() {
  const data = useMemo(() => {
    // Generate decay curve data for 30 days
    const hours = Array.from({ length: 31 }, (_, i) => i * 24); // 0 to 30 days in hours

    return hours.map(h => {
      const decayFactor = Math.exp(-0.005 * h);
      return {
        days: h / 24,
        error: 0.9 * decayFactor + 0.1, // Errors maintain higher importance
        decision: 0.85 * decayFactor + 0.15,
        pattern: 0.8 * decayFactor + 0.2,
        docs: 0.7 * decayFactor + 0.3,
        learning: 0.75 * decayFactor + 0.25,
        context: 0.65 * decayFactor + 0.35,
      };
    });
  }, []);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
        <XAxis
          dataKey="days"
          tick={{ fontSize: 12 }}
          label={{ value: 'Days', position: 'insideBottom', offset: -5, fontSize: 12 }}
        />
        <YAxis
          tick={{ fontSize: 12 }}
          domain={[0, 1]}
          label={{ value: 'Recency Score', angle: -90, position: 'insideLeft', fontSize: 12 }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
          }}
          formatter={(value: number | undefined) => value ? value.toFixed(3) : '0.000'}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="error"
          stroke={COLORS.error}
          strokeWidth={2}
          dot={false}
          name="Error"
          animationDuration={1000}
        />
        <Line
          type="monotone"
          dataKey="decision"
          stroke={COLORS.decision}
          strokeWidth={2}
          dot={false}
          name="Decision"
          animationDuration={1000}
        />
        <Line
          type="monotone"
          dataKey="pattern"
          stroke={COLORS.pattern}
          strokeWidth={2}
          dot={false}
          name="Pattern"
          animationDuration={1000}
        />
        <Line
          type="monotone"
          dataKey="docs"
          stroke={COLORS.docs}
          strokeWidth={2}
          dot={false}
          name="Docs"
          animationDuration={1000}
        />
        <Line
          type="monotone"
          dataKey="learning"
          stroke={COLORS.learning}
          strokeWidth={2}
          dot={false}
          name="Learning"
          animationDuration={1000}
        />
        <Line
          type="monotone"
          dataKey="context"
          stroke={COLORS.context}
          strokeWidth={2}
          dot={false}
          name="Context"
          animationDuration={1000}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
