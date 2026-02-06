import { useMemo } from 'react';
import { Memory } from '../../types/memory';

interface TagCloudProps {
  memories: Memory[];
  onTagClick?: (tag: string) => void;
}

export function TagCloud({ memories, onTagClick }: TagCloudProps) {
  const tagData = useMemo(() => {
    const tagCount = new Map<string, number>();

    memories.forEach(memory => {
      (memory.tags || []).forEach(tag => {
        tagCount.set(tag, (tagCount.get(tag) || 0) + 1);
      });
    });

    const maxCount = Math.max(...Array.from(tagCount.values()));
    const minCount = Math.min(...Array.from(tagCount.values()));
    const range = maxCount - minCount;

    return Array.from(tagCount.entries())
      .map(([tag, count]) => ({
        tag,
        count,
        size: range > 0 ? 12 + ((count - minCount) / range) * 24 : 18,
        opacity: range > 0 ? 0.5 + ((count - minCount) / range) * 0.5 : 0.75,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 50); // Top 50 tags
  }, [memories]);

  const colors = [
    '#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#a855f7', '#ec4899', '#06b6d4', '#8b5cf6'
  ];

  return (
    <div className="flex flex-wrap gap-3 p-4 justify-center items-center min-h-[300px]">
      {tagData.map((item, index) => (
        <button
          key={item.tag}
          onClick={() => onTagClick?.(item.tag)}
          className="transition-all duration-300 hover:scale-110 cursor-pointer font-medium"
          style={{
            fontSize: `${item.size}px`,
            color: colors[index % colors.length],
            opacity: item.opacity,
          }}
          title={`${item.count} memories`}
        >
          {item.tag}
        </button>
      ))}
    </div>
  );
}
