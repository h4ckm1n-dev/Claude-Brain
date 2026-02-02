import { cn } from '../lib/utils';
import { MemoryState } from '../types/memory';

interface StateBadgeProps {
  state: string | MemoryState;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  className?: string;
}

export function StateBadge({ state, size = 'md', showIcon = true, className }: StateBadgeProps) {
  // State configuration with colors and descriptions
  const getStateConfig = (state: string) => {
    const stateMap: Record<string, { label: string; color: string; icon: string; description: string }> = {
      episodic: {
        label: 'Episodic',
        color: 'bg-purple-500 text-white',
        icon: '🆕',
        description: 'New memory, recently created',
      },
      staging: {
        label: 'Staging',
        color: 'bg-yellow-500 text-white',
        icon: '⏳',
        description: 'Under review, being evaluated',
      },
      semantic: {
        label: 'Semantic',
        color: 'bg-blue-500 text-white',
        icon: '💡',
        description: 'Consolidated knowledge',
      },
      procedural: {
        label: 'Procedural',
        color: 'bg-green-500 text-white',
        icon: '⚙️',
        description: 'Permanent best practice',
      },
      archived: {
        label: 'Archived',
        color: 'bg-gray-500 text-white',
        icon: '📦',
        description: 'Archived, inactive',
      },
      purged: {
        label: 'Purged',
        color: 'bg-red-500 text-white',
        icon: '🗑️',
        description: 'Marked for deletion',
      },
    };

    return stateMap[state.toLowerCase()] || {
      label: state,
      color: 'bg-gray-400 text-white',
      icon: '❓',
      description: 'Unknown state',
    };
  };

  const config = getStateConfig(state);

  // Size classes
  const sizeClasses = {
    sm: 'px-1.5 py-0.5 text-[10px]',
    md: 'px-2.5 py-0.5 text-xs',
    lg: 'px-3 py-1 text-sm',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1 rounded-full font-semibold transition-colors',
        config.color,
        sizeClasses[size],
        className
      )}
      title={`State: ${config.label} - ${config.description}`}
    >
      {showIcon && <span className="leading-none">{config.icon}</span>}
      <span>{config.label}</span>
    </div>
  );
}

// State timeline component for showing state transitions
interface StateTimelineProps {
  transitions: Array<{
    from_state: string;
    to_state: string;
    timestamp: string;
    reason?: string;
  }>;
  className?: string;
}

export function StateTimeline({ transitions, className }: StateTimelineProps) {
  if (!transitions || transitions.length === 0) {
    return (
      <div className={cn('text-sm text-gray-500 dark:text-gray-400', className)}>
        No state transitions recorded
      </div>
    );
  }

  return (
    <div className={cn('space-y-3', className)}>
      {transitions.map((transition, index) => (
        <div key={index} className="flex items-start gap-3">
          {/* Timeline line */}
          <div className="flex flex-col items-center">
            <div className="w-2 h-2 rounded-full bg-blue-500" />
            {index < transitions.length - 1 && (
              <div className="w-0.5 h-8 bg-gray-300 dark:bg-gray-700" />
            )}
          </div>

          {/* Transition info */}
          <div className="flex-1 pb-2">
            <div className="flex items-center gap-2 mb-1">
              <StateBadge state={transition.from_state} size="sm" />
              <span className="text-gray-500">→</span>
              <StateBadge state={transition.to_state} size="sm" />
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400">
              {new Date(transition.timestamp).toLocaleString()}
            </div>
            {transition.reason && (
              <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                {transition.reason}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// State distribution chart component
interface StateDistributionProps {
  distribution: Record<string, number>;
  total: number;
  className?: string;
}

export function StateDistribution({ distribution, total, className }: StateDistributionProps) {
  const states = Object.entries(distribution).map(([state, count]) => ({
    state,
    count,
    percentage: (count / total) * 100,
  }));

  return (
    <div className={cn('space-y-2', className)}>
      {states.map(({ state, count, percentage }) => (
        <div key={state} className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <StateBadge state={state} size="sm" />
            <span className="text-gray-600 dark:text-gray-400">
              {count} ({percentage.toFixed(1)}%)
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className="h-2 rounded-full transition-all duration-500"
              style={{
                width: `${percentage}%`,
                backgroundColor: getStateColor(state),
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

// Helper function to get state color for charts
function getStateColor(state: string): string {
  const colors: Record<string, string> = {
    episodic: '#a855f7', // purple
    staging: '#eab308', // yellow
    semantic: '#3b82f6', // blue
    procedural: '#22c55e', // green
    archived: '#6b7280', // gray
    purged: '#ef4444', // red
  };
  return colors[state.toLowerCase()] || '#9ca3af';
}
