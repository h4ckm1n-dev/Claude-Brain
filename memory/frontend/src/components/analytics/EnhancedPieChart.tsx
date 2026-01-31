import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import type { Memory } from '../../types/memory';
import { MemoryType } from '../../types/memory';

interface EnhancedPieChartProps {
  memories: Memory[];
}

const COLORS: Record<MemoryType, string> = {
  [MemoryType.ERROR]: '#ef4444',
  [MemoryType.DECISION]: '#22c55e',
  [MemoryType.PATTERN]: '#3b82f6',
  [MemoryType.DOCS]: '#a855f7',
  [MemoryType.LEARNING]: '#f59e0b',
  [MemoryType.CONTEXT]: '#6b7280',
};

export function EnhancedPieChart({ memories }: EnhancedPieChartProps) {
  const data = Object.entries(
    memories.reduce((acc, memory) => {
      acc[memory.type] = (acc[memory.type] || 0) + 1;
      return acc;
    }, {} as Record<MemoryType, number>)
  ).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value,
    type: name as MemoryType,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={90}
          dataKey="value"
          animationBegin={0}
          animationDuration={800}
          label={(entry: any) => `${entry.name}: ${entry.value}`}
        >
          {data.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={COLORS[entry.type]}
              style={{
                transition: 'all 0.3s ease',
                cursor: 'pointer',
              }}
            />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
          }}
        />
        <Legend
          verticalAlign="bottom"
          height={36}
          formatter={(value, entry: any) => `${value}: ${entry.payload.value}`}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
