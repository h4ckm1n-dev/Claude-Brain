import { useState } from 'react';
import { cn } from '../lib/utils';
import { useAuditTrail } from '../hooks/useAudit';
import { AuditAction, type AuditEntry } from '../types/memory';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Card } from './ui/card';

interface AuditTimelineProps {
  memoryId?: string;
  limit?: number;
  filterAction?: AuditAction;
  filterActor?: string;
  className?: string;
}

export function AuditTimeline({
  memoryId,
  limit = 50,
  filterAction,
  filterActor,
  className,
}: AuditTimelineProps) {
  const [expandedEntries, setExpandedEntries] = useState<Set<string>>(new Set());
  const { data: entries, isLoading, error } = useAuditTrail(memoryId, limit, filterAction, filterActor);

  const toggleExpanded = (entryId: string) => {
    setExpandedEntries(prev => {
      const next = new Set(prev);
      if (next.has(entryId)) {
        next.delete(entryId);
      } else {
        next.add(entryId);
      }
      return next;
    });
  };

  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center py-8', className)}>
        <div className="text-sm text-gray-500">Loading audit trail...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn('flex items-center justify-center py-8', className)}>
        <div className="text-sm text-red-500">Error loading audit trail</div>
      </div>
    );
  }

  if (!entries || entries.length === 0) {
    return (
      <div className={cn('flex items-center justify-center py-8', className)}>
        <div className="text-sm text-gray-500">No audit entries found</div>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {entries.map((entry: AuditEntry, index: number) => (
        <AuditEntry
          key={entry.id}
          entry={entry}
          isExpanded={expandedEntries.has(entry.id)}
          onToggleExpand={() => toggleExpanded(entry.id)}
          isLast={index === entries.length - 1}
        />
      ))}
    </div>
  );
}

interface AuditEntryProps {
  entry: AuditEntry;
  isExpanded: boolean;
  onToggleExpand: () => void;
  isLast: boolean;
}

function AuditEntry({ entry, isExpanded, onToggleExpand, isLast }: AuditEntryProps) {
  const actionConfig = getActionConfig(entry.action);
  const hasDetails = entry.changes || entry.metadata || entry.reason;

  return (
    <div className="flex items-start gap-3">
      {/* Timeline indicator */}
      <div className="flex flex-col items-center">
        <div
          className={cn('w-8 h-8 rounded-full flex items-center justify-center text-sm', actionConfig.color)}
        >
          {actionConfig.icon}
        </div>
        {!isLast && <div className="w-0.5 flex-1 min-h-[32px] bg-gray-300 dark:bg-gray-700" />}
      </div>

      {/* Entry content */}
      <Card className="flex-1 p-4">
        <div className="space-y-2">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="space-y-1 flex-1">
              <div className="flex items-center gap-2">
                <Badge variant="outline">{actionConfig.label}</Badge>
                <span className="text-xs text-gray-500">by {entry.actor}</span>
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">
                {formatTimestamp(entry.timestamp)}
              </div>
            </div>
            {hasDetails && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onToggleExpand}
                className="ml-2"
              >
                {isExpanded ? '▼' : '▶'}
              </Button>
            )}
          </div>

          {/* Reason */}
          {entry.reason && (
            <div className="text-sm text-gray-700 dark:text-gray-300">
              {entry.reason}
            </div>
          )}

          {/* Expanded details */}
          {isExpanded && hasDetails && (
            <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 space-y-2">
              {/* Changes */}
              {entry.changes && Object.keys(entry.changes).length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">
                    Changes:
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 rounded p-2 text-xs font-mono space-y-1">
                    {Object.entries(entry.changes).map(([key, value]) => (
                      <div key={key} className="flex items-start gap-2">
                        <span className="text-gray-500">{key}:</span>
                        <span className="text-gray-700 dark:text-gray-300 flex-1 break-all">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Metadata */}
              {entry.metadata && Object.keys(entry.metadata).length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">
                    Metadata:
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 rounded p-2 text-xs font-mono space-y-1">
                    {Object.entries(entry.metadata).map(([key, value]) => (
                      <div key={key} className="flex items-start gap-2">
                        <span className="text-gray-500">{key}:</span>
                        <span className="text-gray-700 dark:text-gray-300 flex-1 break-all">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

// Action configuration helper
function getActionConfig(action: AuditAction) {
  const configs: Record<AuditAction, { label: string; icon: string; color: string }> = {
    [AuditAction.CREATE]: {
      label: 'Created',
      icon: '➕',
      color: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    },
    [AuditAction.UPDATE]: {
      label: 'Updated',
      icon: '✏️',
      color: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    },
    [AuditAction.DELETE]: {
      label: 'Deleted',
      icon: '🗑️',
      color: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
    },
    [AuditAction.ARCHIVE]: {
      label: 'Archived',
      icon: '📦',
      color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    },
    [AuditAction.RESOLVE]: {
      label: 'Resolved',
      icon: '✅',
      color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300',
    },
    [AuditAction.PIN]: {
      label: 'Pinned',
      icon: '📌',
      color: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
    },
    [AuditAction.UNPIN]: {
      label: 'Unpinned',
      icon: '📌',
      color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    },
    [AuditAction.RATE]: {
      label: 'Rated',
      icon: '⭐',
      color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    },
    [AuditAction.REINFORCE]: {
      label: 'Reinforced',
      icon: '💪',
      color: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
    },
    [AuditAction.STATE_TRANSITION]: {
      label: 'State Changed',
      icon: '🔄',
      color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    },
    [AuditAction.TIER_PROMOTION]: {
      label: 'Tier Promoted',
      icon: '🏆',
      color: 'bg-teal-100 text-teal-700 dark:bg-teal-900 dark:text-teal-300',
    },
    [AuditAction.QUALITY_UPDATE]: {
      label: 'Quality Updated',
      icon: '⭐',
      color: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300',
    },
  };

  return configs[action] || {
    label: action,
    icon: '❓',
    color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  };
}

// Timestamp formatting helper
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}
