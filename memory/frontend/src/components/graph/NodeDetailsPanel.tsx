import { X, Pin, Archive, Trash2, ExternalLink } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { formatDistanceToNow } from 'date-fns';
import type { Memory } from '../../types/memory';

interface NodeDetailsPanelProps {
  node: Memory | any;
  onClose: () => void;
}

const MEMORY_TYPE_COLORS = {
  error: 'bg-red-500/15 text-red-400 border border-red-500/20',
  decision: 'bg-green-500/15 text-green-400 border border-green-500/20',
  pattern: 'bg-blue-500/15 text-blue-400 border border-blue-500/20',
  docs: 'bg-purple-500/15 text-purple-400 border border-purple-500/20',
  learning: 'bg-amber-500/15 text-amber-400 border border-amber-500/20',
  context: 'bg-white/10 text-white/60 border border-white/10',
};

export function NodeDetailsPanel({ node, onClose }: NodeDetailsPanelProps) {
  const isFullMemory = 'content' in node && 'created_at' in node;

  return (
    <div className="absolute top-0 right-0 w-96 h-full bg-[#111] shadow-2xl border-l border-white/[0.06] overflow-y-auto animate-in slide-in-from-right duration-300">
      <div className="sticky top-0 bg-[#111] border-b border-white/[0.06] p-4 flex items-center justify-between z-10">
        <h3 className="text-lg font-semibold">Memory Details</h3>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="p-4 space-y-4">
        {/* Type Badge */}
        {node.type && (
          <div>
            <Badge className={MEMORY_TYPE_COLORS[node.type as keyof typeof MEMORY_TYPE_COLORS]}>
              {node.type}
            </Badge>
          </div>
        )}

        {/* Content */}
        {isFullMemory && (
          <>
            <div>
              <h4 className="text-sm font-medium text-white/40 mb-2">Content</h4>
              <p className="text-sm">{node.content}</p>
            </div>

            {/* Tags */}
            {node.tags && node.tags.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-white/40 mb-2">Tags</h4>
                <div className="flex flex-wrap gap-2">
                  {node.tags.map((tag: string) => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Project */}
            {node.project && (
              <div>
                <h4 className="text-sm font-medium text-white/40 mb-1">Project</h4>
                <p className="text-sm">{node.project}</p>
              </div>
            )}

            {/* Scores */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="text-xs font-medium text-white/40 mb-1">Importance</h4>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-white/[0.06] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500"
                      style={{ width: `${(node.importance_score || 0) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium">{((node.importance_score || 0) * 100).toFixed(0)}%</span>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-medium text-white/40 mb-1">Recency</h4>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-white/[0.06] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500"
                      style={{ width: `${(node.recency_score || 0) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium">{((node.recency_score || 0) * 100).toFixed(0)}%</span>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-medium text-white/40 mb-1">Access Count</h4>
                <p className="text-sm font-medium">{node.access_count || 0}</p>
              </div>

              <div>
                <h4 className="text-xs font-medium text-white/40 mb-1">Tier</h4>
                <Badge variant="outline" className="text-xs">
                  {node.memory_tier || 'unknown'}
                </Badge>
              </div>
            </div>

            {/* Timestamps */}
            <div className="space-y-2 text-xs text-white/40">
              <div className="flex justify-between">
                <span>Created:</span>
                <span>{formatDistanceToNow(new Date(node.created_at), { addSuffix: true })}</span>
              </div>
              <div className="flex justify-between">
                <span>Last Accessed:</span>
                <span>{formatDistanceToNow(new Date(node.last_accessed), { addSuffix: true })}</span>
              </div>
            </div>

            {/* Status Badges */}
            <div className="flex flex-wrap gap-2">
              {node.pinned && (
                <Badge variant="outline" className="text-xs">
                  <Pin className="h-3 w-3 mr-1" />
                  Pinned
                </Badge>
              )}
              {node.archived && (
                <Badge variant="outline" className="text-xs">
                  <Archive className="h-3 w-3 mr-1" />
                  Archived
                </Badge>
              )}
              {node.type === 'error' && !node.resolved && (
                <Badge variant="destructive" className="text-xs">
                  Unresolved
                </Badge>
              )}
            </div>

            {/* Relations */}
            {node.relations && node.relations.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-white/40 mb-2">Relations</h4>
                <div className="space-y-2">
                  {node.relations.map((rel: any, idx: number) => (
                    <div key={idx} className="text-xs flex items-center gap-2 p-2 bg-[#0a0a0a] rounded border border-white/[0.04]">
                      <Badge variant="outline" className="text-xs">
                        {rel.relation_type}
                      </Badge>
                      <span className="text-white/40 truncate flex-1">
                        {rel.target_id}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Type-specific fields */}
            {node.type === 'error' && (
              <>
                {node.error_message && (
                  <div>
                    <h4 className="text-sm font-medium text-white/40 mb-2">Error Message</h4>
                    <pre className="text-xs bg-red-500/10 p-2 rounded overflow-x-auto">
                      {node.error_message}
                    </pre>
                  </div>
                )}
                {node.solution && (
                  <div>
                    <h4 className="text-sm font-medium text-white/40 mb-2">Solution</h4>
                    <p className="text-sm">{node.solution}</p>
                  </div>
                )}
              </>
            )}

            {node.type === 'decision' && (
              <>
                {node.decision && (
                  <div>
                    <h4 className="text-sm font-medium text-white/40 mb-2">Decision</h4>
                    <p className="text-sm">{node.decision}</p>
                  </div>
                )}
                {node.rationale && (
                  <div>
                    <h4 className="text-sm font-medium text-white/40 mb-2">Rationale</h4>
                    <p className="text-sm">{node.rationale}</p>
                  </div>
                )}
              </>
            )}

            {/* Source Link */}
            {node.source && (
              <div>
                <h4 className="text-sm font-medium text-white/40 mb-2">Source</h4>
                <a
                  href={node.source}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                >
                  {node.source}
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 pt-4 border-t border-white/[0.06]">
              <Button variant="outline" size="sm" className="flex-1">
                <Pin className="h-4 w-4 mr-2" />
                {node.pinned ? 'Unpin' : 'Pin'}
              </Button>
              <Button variant="outline" size="sm" className="flex-1">
                <Archive className="h-4 w-4 mr-2" />
                Archive
              </Button>
              <Button variant="destructive" size="sm">
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </>
        )}

        {!isFullMemory && (
          <div className="text-sm text-white/40">
            <p>Node ID: {node.id}</p>
            {node.label && <p>Label: {node.label}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
