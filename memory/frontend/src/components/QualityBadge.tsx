import { cn } from '../lib/utils';

interface QualityBadgeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showScore?: boolean;
  className?: string;
}

export function QualityBadge({ score, size = 'md', showScore = true, className }: QualityBadgeProps) {
  // Backend returns scores in 0.0-1.0 range; normalize to 0-100 for display
  const rawScore = score <= 1 && score >= 0 ? score * 100 : score;
  const normalizedScore = Math.max(0, Math.min(100, rawScore));

  // Determine quality tier and color
  const getQualityTier = (score: number) => {
    if (score >= 80) return { label: 'Excellent', color: 'bg-green-500 text-white', ring: 'ring-green-500' };
    if (score >= 60) return { label: 'Good', color: 'bg-blue-500 text-white', ring: 'ring-blue-500' };
    if (score >= 40) return { label: 'Fair', color: 'bg-yellow-500 text-white', ring: 'ring-yellow-500' };
    if (score >= 20) return { label: 'Poor', color: 'bg-orange-500 text-white', ring: 'ring-orange-500' };
    return { label: 'Very Poor', color: 'bg-red-500 text-white', ring: 'ring-red-500' };
  };

  const tier = getQualityTier(normalizedScore);

  // Size classes
  const sizeClasses = {
    sm: 'px-1.5 py-0.5 text-[10px]',
    md: 'px-2.5 py-0.5 text-xs',
    lg: 'px-3 py-1 text-sm',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full font-semibold transition-colors',
        tier.color,
        sizeClasses[size],
        className
      )}
      title={`Quality Score: ${normalizedScore.toFixed(1)}% (${tier.label})`}
    >
      {showScore ? (
        <>
          <span className="mr-1">{tier.label}</span>
          <span className="opacity-90">({normalizedScore.toFixed(0)}%)</span>
        </>
      ) : (
        <span>{tier.label}</span>
      )}
    </div>
  );
}

// Circular progress variant for more visual representation
interface QualityProgressProps {
  score: number;
  size?: number;
  showLabel?: boolean;
  className?: string;
}

export function QualityProgress({ score, size = 40, showLabel = true, className }: QualityProgressProps) {
  // Backend returns scores in 0.0-1.0 range; normalize to 0-100 for display
  const rawScore = score <= 1 && score >= 0 ? score * 100 : score;
  const normalizedScore = Math.max(0, Math.min(100, rawScore));
  const circumference = 2 * Math.PI * (size / 2 - 4);
  const offset = circumference - (normalizedScore / 100) * circumference;

  // Color based on score
  const getColor = (score: number) => {
    if (score >= 80) return '#22c55e'; // green
    if (score >= 60) return '#3b82f6'; // blue
    if (score >= 40) return '#eab308'; // yellow
    if (score >= 20) return '#f97316'; // orange
    return '#ef4444'; // red
  };

  const color = getColor(normalizedScore);

  return (
    <div className={cn('inline-flex flex-col items-center gap-1', className)}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={size / 2 - 4}
          stroke="currentColor"
          strokeWidth="4"
          fill="none"
          className="text-gray-200 dark:text-gray-700"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={size / 2 - 4}
          stroke={color}
          strokeWidth="4"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
        {/* Score text */}
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dy=".3em"
          className="text-xs font-bold transform rotate-90"
          style={{ transformOrigin: 'center', fill: color }}
        >
          {normalizedScore.toFixed(0)}
        </text>
      </svg>
      {showLabel && (
        <span className="text-[10px] text-gray-600 dark:text-gray-400">Quality</span>
      )}
    </div>
  );
}
