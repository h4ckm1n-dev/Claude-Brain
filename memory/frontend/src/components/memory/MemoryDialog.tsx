import { useEffect, useState } from 'react';
import { useCreateMemory, useUpdateMemory } from '../../hooks/useMemories';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select } from '../ui/select';
import { Card } from '../ui/card';
import type { Memory, MemoryCreate } from '../../types/memory';
import { MemoryType, MemoryTier } from '../../types/memory';
import { X } from 'lucide-react';

interface MemoryDialogProps {
  open: boolean;
  onClose: () => void;
  memory: Memory | null;
}

export function MemoryDialog({ open, onClose, memory }: MemoryDialogProps) {
  const createMemory = useCreateMemory();
  const updateMemory = useUpdateMemory();

  const [formData, setFormData] = useState<MemoryCreate>({
    type: MemoryType.LEARNING,
    content: '',
    tags: [],
    project: '',
    source: '',
    context: '',
    memory_tier: MemoryTier.EPISODIC,
  });

  const [tagsInput, setTagsInput] = useState('');

  useEffect(() => {
    if (memory) {
      setFormData({
        type: memory.type,
        content: memory.content,
        tags: memory.tags,
        project: memory.project || '',
        source: memory.source || '',
        context: memory.context || '',
        memory_tier: memory.memory_tier,
        error_message: memory.error_message,
        solution: memory.solution,
        decision: memory.decision,
        rationale: memory.rationale,
      });
      setTagsInput(memory.tags.join(', '));
    } else {
      setFormData({
        type: MemoryType.LEARNING,
        content: '',
        tags: [],
        project: '',
        source: '',
        context: '',
        memory_tier: MemoryTier.EPISODIC,
      });
      setTagsInput('');
    }
  }, [memory]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const tags = tagsInput.split(',').map(t => t.trim()).filter(Boolean);
    const data = { ...formData, tags };

    try {
      if (memory) {
        await updateMemory.mutateAsync({ id: memory.id, data });
      } else {
        await createMemory.mutateAsync(data);
      }
      onClose();
    } catch (error) {
      console.error('Failed to save memory:', error);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold">
              {memory ? 'Edit Memory' : 'Create Memory'}
            </h2>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Type</label>
              <Select
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value as MemoryType })}
                required
              >
                {Object.values(MemoryType).map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Content</label>
              <textarea
                className="w-full min-h-[120px] rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                required
                placeholder="Enter memory content..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Tags (comma-separated)</label>
              <Input
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="e.g., typescript, bug, authentication"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Project</label>
                <Input
                  value={formData.project}
                  onChange={(e) => setFormData({ ...formData, project: e.target.value })}
                  placeholder="Project name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Source</label>
                <Input
                  value={formData.source}
                  onChange={(e) => setFormData({ ...formData, source: e.target.value })}
                  placeholder="Source URL or reference"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Context</label>
              <textarea
                className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={formData.context}
                onChange={(e) => setFormData({ ...formData, context: e.target.value })}
                placeholder="Additional context..."
              />
            </div>

            {formData.type === MemoryType.ERROR && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">Error Message</label>
                  <Input
                    value={formData.error_message || ''}
                    onChange={(e) => setFormData({ ...formData, error_message: e.target.value })}
                    placeholder="Error message"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Solution</label>
                  <textarea
                    className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    value={formData.solution || ''}
                    onChange={(e) => setFormData({ ...formData, solution: e.target.value })}
                    placeholder="How to solve this error..."
                  />
                </div>
              </>
            )}

            {formData.type === MemoryType.DECISION && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">Decision</label>
                  <Input
                    value={formData.decision || ''}
                    onChange={(e) => setFormData({ ...formData, decision: e.target.value })}
                    placeholder="What was decided"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Rationale</label>
                  <textarea
                    className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    value={formData.rationale || ''}
                    onChange={(e) => setFormData({ ...formData, rationale: e.target.value })}
                    placeholder="Why this decision was made..."
                  />
                </div>
              </>
            )}

            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createMemory.isPending || updateMemory.isPending}
              >
                {memory ? 'Update' : 'Create'}
              </Button>
            </div>
          </form>
        </div>
      </Card>
    </div>
  );
}
