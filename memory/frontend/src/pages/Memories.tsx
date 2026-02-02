import { useState, useRef } from 'react';
// import { useVirtualizer } from '@tanstack/react-virtual';
import { useMemories, useDeleteMemory, usePinMemory, useArchiveMemory } from '../hooks/useMemories';
import { Header } from '../components/layout/Header';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Plus, Trash2, Pin, Archive, Edit, Search, Download, FileText, Database } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { Memory, MemoryType } from '../types/memory';
import { MemoryDialog } from '../components/memory/MemoryDialog';
import { MemoryTypeBadge } from '../components/memory/MemoryTypeBadge';
import { exportToCSV, exportToJSON, exportToMarkdown } from '../utils/export';

export function Memories() {
  const [page, setPage] = useState(0);
  const [limit] = useState(50);
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedMemory, setSelectedMemory] = useState<Memory | null>(null);
  const tableContainerRef = useRef<HTMLDivElement>(null);

  const { data: memories, isLoading } = useMemories({
    type: typeFilter || undefined,
    limit,
    offset: page * limit,
  });

  const deleteMemory = useDeleteMemory();
  const pinMemory = usePinMemory();
  const archiveMemory = useArchiveMemory();

  const filteredMemories = memories?.filter((m: Memory) =>
    !searchQuery || m.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
  ) || [];

  // Temporarily disabled virtual scrolling due to missing dependency
  // const rowVirtualizer = useVirtualizer({
  //   count: filteredMemories.length,
  //   getScrollElement: () => tableContainerRef.current,
  //   estimateSize: () => 80,
  //   overscan: 5,
  // });

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this memory?')) {
      await deleteMemory.mutateAsync(id);
    }
  };

  const handleEdit = (memory: Memory) => {
    setSelectedMemory(memory);
    setDialogOpen(true);
  };

  const handleCreate = () => {
    setSelectedMemory(null);
    setDialogOpen(true);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]">
      <Header title="Memories" />
      <div className="p-6 sm:p-8 max-w-[1800px] mx-auto space-y-6">
        {/* Hero Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-500/10 via-purple-500/10 to-emerald-500/10 p-6 border border-white/5">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-purple-500/5" />
          <div className="relative flex items-center gap-4">
            <div className="p-3 bg-blue-500/10 rounded-xl ring-1 ring-blue-500/20">
              <Database className="h-8 w-8 text-blue-400" />
            </div>
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-white">Memory Management</h1>
              <p className="text-white/60 mt-1">
                {filteredMemories.length} memories
                {typeFilter && ` • Filtered by ${typeFilter}`}
              </p>
            </div>
          </div>
        </div>

        {/* Filters and Actions */}
        <Card className="bg-[#0f0f0f] border-white/10">
          <CardHeader className="border-b border-white/5">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <CardTitle className="text-white">Filters & Export</CardTitle>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  className="bg-[#0a0a0a] border-white/10 text-white/90 hover:bg-white/5 hover:border-purple-500/50"
                  onClick={() => exportToCSV(filteredMemories)}
                  disabled={filteredMemories.length === 0}
                >
                  <Download className="mr-2 h-4 w-4" />
                  CSV
                </Button>
                <Button
                  variant="outline"
                  className="bg-[#0a0a0a] border-white/10 text-white/90 hover:bg-white/5 hover:border-purple-500/50"
                  onClick={() => exportToJSON(filteredMemories)}
                  disabled={filteredMemories.length === 0}
                >
                  <Download className="mr-2 h-4 w-4" />
                  JSON
                </Button>
                <Button
                  variant="outline"
                  className="bg-[#0a0a0a] border-white/10 text-white/90 hover:bg-white/5 hover:border-purple-500/50"
                  onClick={() => exportToMarkdown(filteredMemories)}
                  disabled={filteredMemories.length === 0}
                >
                  <FileText className="mr-2 h-4 w-4" />
                  MD
                </Button>
                <Button
                  onClick={handleCreate}
                  className="bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white border-0"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Create Memory
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="flex gap-4 flex-wrap">
              <div className="flex-1 min-w-[200px] relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-white/30" />
                <Input
                  placeholder="Search memories..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-[#0a0a0a] border-white/10 text-white placeholder:text-white/30 focus:border-blue-500/50"
                />
              </div>
              <Select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="w-40 bg-[#0a0a0a] border-white/10 text-white"
              >
                <option value="">All Types</option>
                {Object.values(MemoryType).map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Memories Table */}
        <Card className="bg-[#0f0f0f] border-white/10 overflow-hidden">
          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-8 text-center">
                <div className="inline-flex items-center gap-3">
                  <div className="h-6 w-6 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" />
                  <span className="text-white/50">Loading memories...</span>
                </div>
              </div>
            ) : filteredMemories.length === 0 ? (
              <div className="p-8 text-center">
                <Database className="h-12 w-12 mx-auto mb-3 text-white/20" />
                <p className="text-white/30">No memories found</p>
              </div>
            ) : (
              <div ref={tableContainerRef} className="overflow-x-auto max-h-[600px] overflow-y-auto">
                <Table className="min-w-full">
                <TableHeader>
                  <TableRow className="border-b border-white/5 hover:bg-transparent">
                    <TableHead className="text-white/70">Type</TableHead>
                    <TableHead className="text-white/70">Content</TableHead>
                    <TableHead className="text-white/70">Tags</TableHead>
                    <TableHead className="text-white/70">Project</TableHead>
                    <TableHead className="text-white/70">Created</TableHead>
                    <TableHead className="text-white/70">Score</TableHead>
                    <TableHead className="text-right text-white/70">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredMemories.map((memory) => (
                    <TableRow
                      key={memory.id}
                      className="border-b border-white/5 hover:bg-white/5 transition-colors"
                    >
                      <TableCell>
                        <MemoryTypeBadge type={memory.type} />
                      </TableCell>
                      <TableCell className="max-w-md">
                        <div className="line-clamp-2 text-white/90">
                          {memory.pinned && <Pin className="inline h-3 w-3 mr-1 text-amber-400" />}
                          {memory.content}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {memory.tags.slice(0, 3).map((tag) => (
                            <Badge key={tag} className="text-xs bg-purple-500/10 text-purple-400 border-purple-500/20">
                              {tag}
                            </Badge>
                          ))}
                          {memory.tags.length > 3 && (
                            <Badge className="text-xs bg-white/5 text-white/50 border-white/10">
                              +{memory.tags.length - 3}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-white/70">{memory.project || '-'}</TableCell>
                      <TableCell className="text-sm text-white/50">
                        {formatDistanceToNow(new Date(memory.created_at), { addSuffix: true })}
                      </TableCell>
                      <TableCell>
                        <span className="text-sm font-medium text-white/90">
                          {memory.importance_score.toFixed(2)}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(memory)}
                            className="hover:bg-white/10 text-white/70 hover:text-blue-400"
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => pinMemory.mutate(memory.id)}
                            disabled={pinMemory.isPending}
                            className="hover:bg-white/10 text-white/70 hover:text-amber-400"
                          >
                            <Pin className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => archiveMemory.mutate(memory.id)}
                            disabled={archiveMemory.isPending}
                            className="hover:bg-white/10 text-white/70 hover:text-purple-400"
                          >
                            <Archive className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(memory.id)}
                            disabled={deleteMemory.isPending}
                            className="hover:bg-white/10 text-white/70 hover:text-rose-400"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pagination */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-white/50">
            Showing {page * limit + 1} to {Math.min((page + 1) * limit, filteredMemories.length)} of {filteredMemories.length}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="bg-[#0f0f0f] border-white/10 text-white/90 hover:bg-white/5 hover:border-blue-500/50"
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              className="bg-[#0f0f0f] border-white/10 text-white/90 hover:bg-white/5 hover:border-blue-500/50"
              onClick={() => setPage(page + 1)}
              disabled={filteredMemories.length < limit}
            >
              Next
            </Button>
          </div>
        </div>
      </div>

      <MemoryDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        memory={selectedMemory}
      />
    </div>
  );
}
