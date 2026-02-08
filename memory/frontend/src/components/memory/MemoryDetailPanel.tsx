import { useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { X, Pin, Archive, Trash2, Zap, ExternalLink, Clock, Eye, TrendingUp, Shield, Activity } from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';
import { Memory } from '../../types/memory';
import { getMemory, getRelatedMemories, pinMemory, archiveMemory, deleteMemory, reinforceMemory } from '../../api/memories';
import { MemoryTypeBadge } from './MemoryTypeBadge';
import { StateBadge } from '../StateBadge';
import { QualityBadge } from '../QualityBadge';
import { AuditTimeline } from '../AuditTimeline';

interface MemoryDetailPanelProps {
  memoryId: string | null;
  onClose: () => void;
  onNavigate?: (memoryId: string) => void;
}

export function MemoryDetailPanel({ memoryId, onClose, onNavigate }: MemoryDetailPanelProps) {
  const queryClient = useQueryClient();

  const { data: memory, isLoading } = useQuery({
    queryKey: ['memory-detail', memoryId],
    queryFn: () => getMemory(memoryId!),
    enabled: !!memoryId,
  });

  const { data: related } = useQuery({
    queryKey: ['memory-related', memoryId],
    queryFn: () => getRelatedMemories(memoryId!, 1, 10),
    enabled: !!memoryId,
  });

  const pinMutation = useMutation({
    mutationFn: () => pinMemory(memoryId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['memory-detail', memoryId] }),
  });

  const archiveMutation = useMutation({
    mutationFn: () => archiveMemory(memoryId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      onClose();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteMemory(memoryId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      onClose();
    },
  });

  const reinforceMutation = useMutation({
    mutationFn: () => reinforceMemory(memoryId!, 0.2),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['memory-detail', memoryId] }),
  });

  // Close on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  if (!memoryId) return null;

  const mem = memory as any; // Extended memory fields

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-[480px] max-w-full bg-[#0a0a0a] border-l border-white/10 z-50 flex flex-col shadow-2xl animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <h2 className="text-lg font-semibold text-white">Memory Detail</h2>
          <Button variant="ghost" size="icon" onClick={onClose} className="text-white/50 hover:text-white">
            <X className="h-5 w-5" />
          </Button>
        </div>

        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="h-8 w-8 border-2 border-purple-500/20 border-t-purple-500 rounded-full animate-spin" />
          </div>
        ) : !memory ? (
          <div className="flex-1 flex items-center justify-center text-white/40">
            Memory not found
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Type & State badges */}
            <div className="flex flex-wrap gap-2">
              <MemoryTypeBadge type={memory.type} />
              <StateBadge state={mem?.state || 'episodic'} size="sm" />
              <QualityBadge score={mem?.quality_score || 0} size="sm" showScore={true} />
              {memory.pinned && (
                <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/20">Pinned</Badge>
              )}
              {memory.resolved && (
                <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">Resolved</Badge>
              )}
            </div>

            {/* Content */}
            <Card className="bg-[#0f0f0f] border-white/10">
              <CardHeader className="py-3 border-b border-white/5">
                <CardTitle className="text-sm text-white/70">Content</CardTitle>
              </CardHeader>
              <CardContent className="pt-3">
                <div className="text-sm text-white/90 whitespace-pre-wrap leading-relaxed max-h-[300px] overflow-y-auto">
                  {memory.content}
                </div>
              </CardContent>
            </Card>

            {/* Error-specific fields */}
            {memory.error_message && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg">
                <span className="text-xs font-medium text-rose-400 block mb-1">Error Message</span>
                <p className="text-sm text-white/80 font-mono">{memory.error_message}</p>
              </div>
            )}
            {memory.solution && (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                <span className="text-xs font-medium text-emerald-400 block mb-1">Solution</span>
                <p className="text-sm text-white/80">{memory.solution}</p>
              </div>
            )}
            {memory.prevention && (
              <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                <span className="text-xs font-medium text-blue-400 block mb-1">Prevention</span>
                <p className="text-sm text-white/80">{memory.prevention}</p>
              </div>
            )}

            {/* Decision-specific fields */}
            {memory.decision && (
              <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
                <span className="text-xs font-medium text-green-400 block mb-1">Decision</span>
                <p className="text-sm text-white/80">{memory.decision}</p>
              </div>
            )}
            {memory.rationale && (
              <div className="p-3 bg-purple-500/10 border border-purple-500/20 rounded-lg">
                <span className="text-xs font-medium text-purple-400 block mb-1">Rationale</span>
                <p className="text-sm text-white/80">{memory.rationale}</p>
              </div>
            )}

            {/* Metadata Grid */}
            <Card className="bg-[#0f0f0f] border-white/10">
              <CardHeader className="py-3 border-b border-white/5">
                <CardTitle className="text-sm text-white/70 flex items-center gap-2">
                  <Activity className="h-4 w-4" /> Metadata
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-3">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="flex items-center gap-2 text-white/50">
                    <Clock className="h-3.5 w-3.5" />
                    <span>Created</span>
                  </div>
                  <span className="text-white/90">{format(new Date(memory.created_at), 'MMM d, yyyy HH:mm')}</span>

                  <div className="flex items-center gap-2 text-white/50">
                    <Eye className="h-3.5 w-3.5" />
                    <span>Accessed</span>
                  </div>
                  <span className="text-white/90">{memory.access_count}x ({memory.access_count > 0 ? formatDistanceToNow(new Date(memory.last_accessed), { addSuffix: true }) : 'never'})</span>

                  <div className="flex items-center gap-2 text-white/50">
                    <TrendingUp className="h-3.5 w-3.5" />
                    <span>Importance</span>
                  </div>
                  <span className="text-white/90">{(memory.importance_score ?? 0).toFixed(3)}</span>

                  <div className="flex items-center gap-2 text-white/50">
                    <Shield className="h-3.5 w-3.5" />
                    <span>Strength</span>
                  </div>
                  <span className="text-white/90">{(mem?.memory_strength ?? 1.0).toFixed(3)}</span>

                  <div className="flex items-center gap-2 text-white/50">
                    <Activity className="h-3.5 w-3.5" />
                    <span>Tier</span>
                  </div>
                  <span className="text-white/90">{memory.memory_tier}</span>

                  {memory.project && (
                    <>
                      <span className="text-white/50">Project</span>
                      <span className="text-blue-400">{memory.project}</span>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Tags */}
            {memory.tags?.length > 0 && (
              <div>
                <span className="text-xs font-medium text-white/50 mb-2 block">Tags</span>
                <div className="flex flex-wrap gap-1.5">
                  {memory.tags.map((tag) => (
                    <Badge key={tag} className="text-xs bg-purple-500/10 text-purple-400 border-purple-500/20">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Related Memories */}
            {related && related.length > 0 && (
              <Card className="bg-[#0f0f0f] border-white/10">
                <CardHeader className="py-3 border-b border-white/5">
                  <CardTitle className="text-sm text-white/70 flex items-center gap-2">
                    <ExternalLink className="h-4 w-4" /> Related ({related.length})
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-3 space-y-2">
                  {related.map((rel: any) => (
                    <button
                      key={rel.id}
                      onClick={() => onNavigate?.(rel.id)}
                      className="w-full text-left p-2.5 rounded-lg bg-[#0a0a0a] border border-white/5 hover:border-purple-500/30 transition-colors group"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Badge className="text-[10px] bg-blue-500/10 text-blue-400 border-blue-500/20">
                          {rel.type}
                        </Badge>
                        {rel.relations?.length > 0 && (
                          <Badge className="text-[10px] bg-white/5 text-white/50 border-white/10">
                            {rel.relations[0]?.relation_type}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-white/70 group-hover:text-white/90 line-clamp-2 transition-colors">
                        {rel.content}
                      </p>
                    </button>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* Audit Timeline */}
            <Card className="bg-[#0f0f0f] border-white/10">
              <CardHeader className="py-3 border-b border-white/5">
                <CardTitle className="text-sm text-white/70">Audit History</CardTitle>
              </CardHeader>
              <CardContent className="pt-3">
                <AuditTimeline memoryId={memoryId} limit={5} />
              </CardContent>
            </Card>
          </div>
        )}

        {/* Action Bar */}
        {memory && (
          <div className="p-4 border-t border-white/10 flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => pinMutation.mutate()}
              disabled={pinMutation.isPending}
              className="flex-1 bg-transparent border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
            >
              <Pin className="h-3.5 w-3.5 mr-1.5" />
              {memory.pinned ? 'Unpin' : 'Pin'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => reinforceMutation.mutate()}
              disabled={reinforceMutation.isPending}
              className="flex-1 bg-transparent border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
            >
              <Zap className="h-3.5 w-3.5 mr-1.5" />
              Reinforce
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => archiveMutation.mutate()}
              disabled={archiveMutation.isPending}
              className="flex-1 bg-transparent border-purple-500/30 text-purple-400 hover:bg-purple-500/10"
            >
              <Archive className="h-3.5 w-3.5 mr-1.5" />
              Archive
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (confirm('Permanently delete this memory?')) deleteMutation.mutate();
              }}
              disabled={deleteMutation.isPending}
              className="bg-transparent border-rose-500/30 text-rose-400 hover:bg-rose-500/10"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
      </div>
    </>
  );
}
