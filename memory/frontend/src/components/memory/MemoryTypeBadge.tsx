import { Badge } from '../ui/badge';
import { AlertCircle, BookOpen, CheckCircle, Lightbulb, FileText, GitBranch, type LucideIcon } from 'lucide-react';
import type { MemoryType } from '../../types/memory';

interface TypeConfig {
  icon: LucideIcon;
  label: string;
  color: string;
  bgColor: string;
}

const TYPE_CONFIG: Record<string, TypeConfig> = {
  error: {
    icon: AlertCircle,
    label: 'Error',
    color: 'text-red-700 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800',
  },
  docs: {
    icon: BookOpen,
    label: 'Documentation',
    color: 'text-blue-700 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800',
  },
  decision: {
    icon: CheckCircle,
    label: 'Decision',
    color: 'text-green-700 dark:text-green-400',
    bgColor: 'bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800',
  },
  pattern: {
    icon: Lightbulb,
    label: 'Pattern',
    color: 'text-yellow-700 dark:text-yellow-400',
    bgColor: 'bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800',
  },
  learning: {
    icon: FileText,
    label: 'Learning',
    color: 'text-purple-700 dark:text-purple-400',
    bgColor: 'bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800',
  },
  context: {
    icon: GitBranch,
    label: 'Context',
    color: 'text-gray-700 dark:text-gray-400',
    bgColor: 'bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700',
  },
};

interface MemoryTypeBadgeProps {
  type: MemoryType | string;
  className?: string;
  showIcon?: boolean;
}

export function MemoryTypeBadge({ type, className = '', showIcon = true }: MemoryTypeBadgeProps) {
  const typeStr = String(type);
  const config = TYPE_CONFIG[typeStr] || TYPE_CONFIG.context;
  const Icon = config.icon;

  return (
    <Badge
      variant="outline"
      className={`${config.bgColor} ${config.color} border ${className}`}
    >
      {showIcon && <Icon className="mr-1 h-3 w-3" aria-hidden="true" />}
      <span>{config.label}</span>
    </Badge>
  );
}
