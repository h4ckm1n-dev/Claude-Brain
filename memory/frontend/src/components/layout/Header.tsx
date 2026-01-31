import { useHealth } from '../../hooks/useMemories';
import { Badge } from '../ui/badge';

export function Header({ title }: { title: string }) {
  const { data: health } = useHealth();

  return (
    <header className="h-16 border-b bg-background px-6 flex items-center justify-between">
      <h2 className="text-2xl font-semibold">{title}</h2>
      <div className="flex items-center gap-4">
        {health && (
          <div className="flex items-center gap-2">
            <Badge variant={health.status === 'healthy' ? 'default' : 'destructive'}>
              {health.status === 'healthy' ? 'System Healthy' : 'System Error'}
            </Badge>
            <Badge variant="outline">
              {health.memory_count} memories
            </Badge>
          </div>
        )}
      </div>
    </header>
  );
}
