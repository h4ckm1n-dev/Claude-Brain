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
import { Plus, Trash2, Pin, Archive, Edit, Search, Download, FileText } from 'lucide-react';
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
    <div>
      <Header title="Memories" />
      <div className="p-6 space-y-6">
        {/* Filters and Actions */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between flex-wrap gap-2">
              <CardTitle>Memory Management</CardTitle>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => exportToCSV(filteredMemories)}
                  disabled={filteredMemories.length === 0}
                >
                  <Download className="mr-2 h-4 w-4" />
                  CSV
                </Button>
                <Button
                  variant="outline"
                  onClick={() => exportToJSON(filteredMemories)}
                  disabled={filteredMemories.length === 0}
                >
                  <Download className="mr-2 h-4 w-4" />
                  JSON
                </Button>
                <Button
                  variant="outline"
                  onClick={() => exportToMarkdown(filteredMemories)}
                  disabled={filteredMemories.length === 0}
                >
                  <FileText className="mr-2 h-4 w-4" />
                  MD
                </Button>
                <Button onClick={handleCreate}>
                  <Plus className="mr-2 h-4 w-4" />
                  Create Memory
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4">
              <div className="flex-1">
                <Input
                  placeholder="Search memories..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="max-w-md"
                />
              </div>
              <Select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="w-40"
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
        <Card>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-8 text-center text-muted-foreground">Loading memories...</div>
            ) : filteredMemories.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">No memories found</div>
            ) : (
              <div ref={tableContainerRef} className="overflow-x-auto max-h-[600px] overflow-y-auto">
                <Table className="min-w-full">
                <TableHeader>
                  <TableRow>
                    <TableHead>Type</TableHead>
                    <TableHead>Content</TableHead>
                    <TableHead>Tags</TableHead>
                    <TableHead>Project</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredMemories.map((memory) => (
                    <TableRow key={memory.id}>
                      <TableCell>
                        <MemoryTypeBadge type={memory.type} />
                      </TableCell>
                      <TableCell className="max-w-md">
                        <div className="line-clamp-2">
                          {memory.pinned && <Pin className="inline h-3 w-3 mr-1 text-yellow-500" />}
                          {memory.content}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {memory.tags.slice(0, 3).map((tag) => (
                            <Badge key={tag} variant="secondary" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                          {memory.tags.length > 3 && (
                            <Badge variant="secondary" className="text-xs">
                              +{memory.tags.length - 3}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>{memory.project || '-'}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDistanceToNow(new Date(memory.created_at), { addSuffix: true })}
                      </TableCell>
                      <TableCell>
                        <span className="text-sm font-medium">
                          {memory.importance_score.toFixed(2)}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(memory)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => pinMemory.mutate(memory.id)}
                            disabled={pinMemory.isPending}
                          >
                            <Pin className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => archiveMemory.mutate(memory.id)}
                            disabled={archiveMemory.isPending}
                          >
                            <Archive className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(memory.id)}
                            disabled={deleteMemory.isPending}
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
          <p className="text-sm text-muted-foreground">
            Showing {page * limit + 1} to {Math.min((page + 1) * limit, filteredMemories.length)} of {filteredMemories.length}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
            >
              Previous
            </Button>
            <Button
              variant="outline"
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
