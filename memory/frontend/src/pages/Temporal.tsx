import { useState } from 'react';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import {
  useTemporalStats,
  useValidAt,
  useObsoleteMemories,
  useMarkObsolete,
  useRelatedAt,
} from '../hooks/useTemporal';
import {
  Clock,
  Calendar,
  Archive,
  GitBranch,
  AlertTriangle,
  History,
  Search,
} from 'lucide-react';

export function Temporal() {
  const [targetTime, setTargetTime] = useState('');
  const [selectedMemory, setSelectedMemory] = useState('');
  const [graphTime, setGraphTime] = useState('');

  const { data: stats, isLoading: statsLoading } = useTemporalStats();
  const { data: validMemories } = useValidAt(targetTime, 50);
  const { data: obsoleteMemories } = useObsoleteMemories(50);
  const markObsolete = useMarkObsolete();
  const { data: relatedMemories } = useRelatedAt(selectedMemory, graphTime || new Date().toISOString());

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]">
      <Header title="Temporal" />
      <div className="p-6 space-y-6">
        {/* Hero */}
        <div className="bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-600 rounded-2xl p-8 shadow-2xl">
          <div className="flex items-center gap-4">
            <div className="p-4 bg-white/20 backdrop-blur-sm rounded-xl">
              <History className="h-10 w-10 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">Temporal Intelligence</h1>
              <p className="text-indigo-100 mt-1">
                Time-travel through your memory knowledge base
              </p>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-500/20 rounded-lg">
                  <Clock className="h-5 w-5 text-indigo-400" />
                </div>
                <div>
                  <p className="text-xs text-white/50">Total Memories</p>
                  <p className="text-2xl font-bold text-white">
                    {statsLoading ? '...' : stats?.total_memories ?? 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <Calendar className="h-5 w-5 text-green-400" />
                </div>
                <div>
                  <p className="text-xs text-white/50">Currently Valid</p>
                  <p className="text-2xl font-bold text-white">
                    {statsLoading ? '...' : stats?.valid_memories ?? 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-500/20 rounded-lg">
                  <Archive className="h-5 w-5 text-amber-400" />
                </div>
                <div>
                  <p className="text-xs text-white/50">Obsolete</p>
                  <p className="text-2xl font-bold text-white">
                    {statsLoading ? '...' : stats?.obsolete_memories ?? 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <GitBranch className="h-5 w-5 text-purple-400" />
                </div>
                <div>
                  <p className="text-xs text-white/50">Avg Validity (days)</p>
                  <p className="text-2xl font-bold text-white">
                    {statsLoading ? '...' : (stats?.avg_validity_days ?? 0).toFixed(0)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Time Machine */}
        <Card className="bg-[#0f0f0f] border border-white/10">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Search className="h-5 w-5 text-indigo-400" />
              <CardTitle className="text-white">Time Machine</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Select a date to see what memories were valid at that point in time
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3">
              <Input
                type="datetime-local"
                value={targetTime ? targetTime.slice(0, 16) : ''}
                onChange={(e) => setTargetTime(e.target.value ? new Date(e.target.value).toISOString() : '')}
                className="bg-[#0a0a0a] border-white/10 text-white flex-1"
              />
              <Button
                onClick={() => setTargetTime(new Date().toISOString())}
                variant="outline"
                className="border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/20"
              >
                Now
              </Button>
            </div>

            {validMemories && validMemories.length > 0 && (
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                <p className="text-sm text-indigo-300">
                  {validMemories.length} memories valid at selected time
                </p>
                {validMemories.map((memory) => (
                  <div
                    key={memory.id}
                    className="p-3 rounded-lg border border-white/5 bg-[#0a0a0a] hover:border-indigo-500/30 transition-colors cursor-pointer"
                    onClick={() => {
                      setSelectedMemory(memory.id);
                      setGraphTime(targetTime);
                    }}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Badge className="bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs">
                        {memory.type}
                      </Badge>
                      {memory.is_obsolete && (
                        <Badge className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs">
                          obsolete
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-white/80 line-clamp-2">{memory.content}</p>
                  </div>
                ))}
              </div>
            )}

            {targetTime && validMemories?.length === 0 && (
              <p className="text-white/50 text-center py-4">No memories were valid at this time</p>
            )}
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Obsolete Memories */}
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardHeader>
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-400" />
                <CardTitle className="text-white">Obsolete Memories</CardTitle>
              </div>
              <CardDescription className="text-white/60">
                Memories that are no longer valid or have been superseded
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 max-h-[400px] overflow-y-auto">
              {obsoleteMemories?.map((memory) => (
                <div
                  key={memory.id}
                  className="p-3 rounded-lg border border-white/5 bg-[#0a0a0a]"
                >
                  <div className="flex items-center justify-between mb-1">
                    <Badge className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs">
                      {memory.type}
                    </Badge>
                    <span className="text-xs text-white/40">
                      {memory.valid_to ? new Date(memory.valid_to).toLocaleDateString() : 'unknown'}
                    </span>
                  </div>
                  <p className="text-sm text-white/70 line-clamp-2">{memory.content}</p>
                </div>
              ))}
              {(!obsoleteMemories || obsoleteMemories.length === 0) && (
                <p className="text-white/50 text-center py-4">No obsolete memories</p>
              )}
            </CardContent>
          </Card>

          {/* Temporal Relationships */}
          <Card className="bg-[#0f0f0f] border border-white/10">
            <CardHeader>
              <div className="flex items-center gap-2">
                <GitBranch className="h-5 w-5 text-purple-400" />
                <CardTitle className="text-white">Temporal Relations</CardTitle>
              </div>
              <CardDescription className="text-white/60">
                Click a memory in the Time Machine to see its temporal neighbors
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 max-h-[400px] overflow-y-auto">
              {selectedMemory && relatedMemories && relatedMemories.length > 0 ? (
                relatedMemories.map((rel) => (
                  <div
                    key={rel.id}
                    className="p-3 rounded-lg border border-white/5 bg-[#0a0a0a]"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Badge className="bg-purple-500/20 text-purple-300 border border-purple-500/30 text-xs">
                        {rel.relation}
                      </Badge>
                      <Badge className="bg-blue-500/20 text-blue-300 border border-blue-500/30 text-xs">
                        {rel.type}
                      </Badge>
                      <span className="text-xs text-white/40 ml-auto">
                        score: {rel.score.toFixed(2)}
                      </span>
                    </div>
                    <p className="text-sm text-white/70 line-clamp-2">{rel.content}</p>
                  </div>
                ))
              ) : (
                <p className="text-white/50 text-center py-4">
                  {selectedMemory ? 'No temporal relations found' : 'Select a memory to explore relations'}
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Mark Obsolete Action */}
        <Card className="bg-[#0f0f0f] border border-white/10">
          <CardHeader>
            <CardTitle className="text-white">Mark Memory as Obsolete</CardTitle>
            <CardDescription className="text-white/60">
              Enter a memory ID to mark it as no longer valid
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-3">
              <Input
                value={selectedMemory}
                onChange={(e) => setSelectedMemory(e.target.value)}
                placeholder="Memory ID"
                className="bg-[#0a0a0a] border-white/10 text-white flex-1"
              />
              <Button
                onClick={() => {
                  if (selectedMemory) {
                    markObsolete.mutate({ memoryId: selectedMemory });
                  }
                }}
                disabled={!selectedMemory || markObsolete.isPending}
                className="bg-amber-500 hover:bg-amber-600 text-white"
              >
                <Archive className="mr-2 h-4 w-4" />
                Mark Obsolete
              </Button>
            </div>
            {markObsolete.isSuccess && (
              <p className="mt-2 text-sm text-green-400">Memory marked as obsolete</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
