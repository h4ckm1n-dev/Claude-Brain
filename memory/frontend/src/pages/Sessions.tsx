import { useState } from 'react';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import {
  useSessionStats,
  useSessionMemories,
  useConsolidateSession,
  useBatchConsolidate,
  useCreateSession,
} from '../hooks/useSessions';
import {
  Clock,
  Layers,
  Plus,
  ChevronDown,
  ChevronRight,
  Combine,
  Database,
  Activity,
} from 'lucide-react';

export function Sessions() {
  const [expandedSession, setExpandedSession] = useState<string | null>(null);
  const [newProject, setNewProject] = useState('');

  const { data: stats, isLoading: statsLoading } = useSessionStats();
  const { data: sessionMemories } = useSessionMemories(expandedSession || '');
  const consolidateSession = useConsolidateSession();
  const batchConsolidate = useBatchConsolidate();
  const createSession = useCreateSession();

  const handleCreateSession = () => {
    createSession.mutate(newProject || undefined);
    setNewProject('');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]">
      <Header title="Sessions" />
      <div className="p-6 space-y-6">
        {/* Hero */}
        <div className="bg-gradient-to-br from-teal-600 via-cyan-600 to-blue-600 rounded-2xl p-8 shadow-2xl">
          <div className="flex items-center gap-4">
            <div className="p-4 bg-white/20 backdrop-blur-sm rounded-xl">
              <Clock className="h-10 w-10 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">Session Management</h1>
              <p className="text-teal-100 mt-1">
                Track coding sessions and consolidate session memories
              </p>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-teal-500/20 rounded-lg">
                  <Layers className="h-5 w-5 text-teal-400" />
                </div>
                <div>
                  <p className="text-xs text-white/50">Total Sessions</p>
                  <p className="text-2xl font-bold text-white">
                    {statsLoading ? '...' : stats?.total_sessions ?? 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <Activity className="h-5 w-5 text-green-400" />
                </div>
                <div>
                  <p className="text-xs text-white/50">Active</p>
                  <p className="text-2xl font-bold text-white">
                    {statsLoading ? '...' : stats?.active_sessions ?? 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <Database className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-xs text-white/50">Avg Memories/Session</p>
                  <p className="text-2xl font-bold text-white">
                    {statsLoading ? '...' : (stats?.avg_memories_per_session ?? 0).toFixed(1)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <Combine className="h-5 w-5 text-purple-400" />
                </div>
                <div>
                  <p className="text-xs text-white/50">Consolidation Rate</p>
                  <p className="text-2xl font-bold text-white">
                    {statsLoading ? '...' : ((stats?.consolidation_rate ?? 0) * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-3">
          <div className="flex gap-2 flex-1 min-w-[250px]">
            <Input
              value={newProject}
              onChange={(e) => setNewProject(e.target.value)}
              placeholder="Project name (optional)"
              className="bg-[#0f0f0f] border-white/10 text-white"
            />
            <Button
              onClick={handleCreateSession}
              disabled={createSession.isPending}
              className="bg-teal-500 hover:bg-teal-600 text-white whitespace-nowrap"
            >
              <Plus className="mr-2 h-4 w-4" />
              New Session
            </Button>
          </div>
          <Button
            onClick={() => batchConsolidate.mutate(24)}
            disabled={batchConsolidate.isPending}
            className="bg-purple-500 hover:bg-purple-600 text-white"
          >
            <Combine className="mr-2 h-4 w-4" />
            {batchConsolidate.isPending ? 'Consolidating...' : 'Batch Consolidate All'}
          </Button>
        </div>

        {batchConsolidate.data && (
          <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-xl">
            <p className="text-purple-200">
              Processed {batchConsolidate.data.sessions_processed} sessions,
              consolidated {batchConsolidate.data.total_memories_consolidated} memories
            </p>
          </div>
        )}

        {/* Session List */}
        <Card className="bg-[#0f0f0f] border border-white/10">
          <CardHeader>
            <CardTitle className="text-white">Recent Sessions</CardTitle>
            <CardDescription className="text-white/60">
              Click a session to view its memories
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {stats?.recent_sessions?.length === 0 && (
              <p className="text-white/50 text-center py-8">No sessions found</p>
            )}
            {stats?.recent_sessions?.map((session) => (
              <div key={session.session_id} className="border border-white/5 rounded-lg overflow-hidden">
                <button
                  onClick={() => setExpandedSession(
                    expandedSession === session.session_id ? null : session.session_id
                  )}
                  className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {expandedSession === session.session_id ? (
                      <ChevronDown className="h-4 w-4 text-white/50" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-white/50" />
                    )}
                    <span className="text-sm font-mono text-white/80">
                      {session.session_id.slice(0, 12)}...
                    </span>
                    <Badge className="bg-blue-500/20 text-blue-300 border border-blue-500/30">
                      {session.memory_count} memories
                    </Badge>
                    <Badge className={
                      session.status === 'active'
                        ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                        : 'bg-white/10 text-white/50 border border-white/10'
                    }>
                      {session.status}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-white/40">
                      {new Date(session.created_at).toLocaleDateString()}
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation();
                        consolidateSession.mutate(session.session_id);
                      }}
                      disabled={consolidateSession.isPending}
                      className="border-purple-500/30 text-purple-300 hover:bg-purple-500/20"
                    >
                      <Combine className="h-3 w-3 mr-1" />
                      Consolidate
                    </Button>
                  </div>
                </button>

                {expandedSession === session.session_id && sessionMemories && (
                  <div className="border-t border-white/5 p-4 space-y-2 bg-[#0a0a0a]">
                    {sessionMemories.map((memory) => (
                      <div
                        key={memory.id}
                        className="p-3 rounded-lg border border-white/5 bg-[#0f0f0f]"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <Badge className="bg-teal-500/20 text-teal-300 border border-teal-500/30 text-xs">
                            {memory.type}
                          </Badge>
                          <span className="text-xs text-white/40">
                            {new Date(memory.created_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-sm text-white/80 line-clamp-2">{memory.content}</p>
                        {memory.tags?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {memory.tags?.slice(0, 5).map((tag) => (
                              <Badge key={tag} className="text-xs bg-white/5 text-white/50 border border-white/10">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                    {sessionMemories.length === 0 && (
                      <p className="text-white/50 text-sm text-center py-4">No memories in this session</p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
