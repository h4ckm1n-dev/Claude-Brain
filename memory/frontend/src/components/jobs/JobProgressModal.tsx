import { useQuery } from '@tanstack/react-query';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Badge } from '../ui/badge';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
import { apiClient } from '../../lib/api';
import type { AxiosResponse } from 'axios';

interface JobInfo {
  job_id: string;
  script_name: string;
  args: string[];
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string;
  completed_at?: string;
  result?: {
    stdout?: string;
    stderr?: string;
  };
  error?: string;
  pid?: number;
}

interface JobProgressModalProps {
  jobId: string;
  open: boolean;
  onClose: () => void;
}

export function JobProgressModal({ jobId, open, onClose }: JobProgressModalProps) {
  const { data: job } = useQuery<JobInfo>({
    queryKey: ['jobs', jobId],
    queryFn: () => apiClient.get<JobInfo>(`/jobs/${jobId}`).then((r: AxiosResponse<JobInfo>) => r.data),
    enabled: open && !!jobId,
    refetchInterval: (query) => {
      // Stop when complete
      const data = query.state.data;
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      return 1000; // Poll every second
    },
  });

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {job?.status === 'completed' && <CheckCircle className="h-5 w-5 text-green-600" />}
            {job?.status === 'failed' && <XCircle className="h-5 w-5 text-red-600" />}
            {job?.status === 'running' && <Loader2 className="h-5 w-5 animate-spin text-blue-600" />}
            Job Progress
          </DialogTitle>
        </DialogHeader>

        {job && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Script</p>
                <p className="font-medium">{job.script_name}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Status</p>
                <Badge variant={
                  job.status === 'completed' ? 'default' :
                  job.status === 'failed' ? 'destructive' :
                  'secondary'
                }>
                  {job.status}
                </Badge>
              </div>
            </div>

            {job.args && job.args.length > 0 && (
              <div>
                <p className="text-sm text-muted-foreground mb-1">Arguments</p>
                <code className="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                  {job.args.join(' ')}
                </code>
              </div>
            )}

            {job.status === 'completed' && job.result && (
              <div className="rounded border bg-green-50 dark:bg-green-950 p-4">
                <p className="text-xs font-semibold text-green-800 dark:text-green-200 mb-2">
                  Output
                </p>
                <pre className="text-xs text-green-900 dark:text-green-100 whitespace-pre-wrap max-h-64 overflow-y-auto">
                  {job.result.stdout || 'Success (no output)'}
                </pre>
              </div>
            )}

            {job.status === 'failed' && job.error && (
              <div className="rounded border bg-red-50 dark:bg-red-950 p-4">
                <p className="text-xs font-semibold text-red-800 dark:text-red-200 mb-2">
                  Error
                </p>
                <pre className="text-xs text-red-900 dark:text-red-100 whitespace-pre-wrap max-h-64 overflow-y-auto">
                  {job.error}
                </pre>
              </div>
            )}

            {job.status === 'running' && (
              <div className="flex items-center justify-center p-8">
                <div className="text-center">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">Executing script...</p>
                </div>
              </div>
            )}

            <div className="text-xs text-muted-foreground space-y-1">
              <p>Started: {new Date(job.started_at).toLocaleString()}</p>
              {job.completed_at && (
                <p>Completed: {new Date(job.completed_at).toLocaleString()}</p>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
