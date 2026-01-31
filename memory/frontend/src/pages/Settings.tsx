import { useState, useEffect } from 'react';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Slider } from '../components/ui/slider';
import { Settings as SettingsIcon, Bell, Database, RefreshCw, AlertCircle, Moon, Sun, Monitor, Activity, Wrench, FileText, Folder } from 'lucide-react';
import { apiClient } from '../lib/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTheme } from '../hooks/useTheme';
import { JobProgressModal } from '../components/jobs/JobProgressModal';
import type { AxiosResponse } from 'axios';

interface UserSettings {
  // Automatic Capture
  captureWebFetch: boolean;
  captureBashSuccess: boolean;
  captureBashErrors: boolean;
  captureTaskResults: boolean;

  // Suggestions
  suggestionLimit: number;
  suggestionMinScore: number;
  suggestionFrequency: 'always' | 'hourly' | 'daily' | 'never';

  // Notifications
  notificationEnabled: boolean;
  notificationSound: boolean;

  // Cache
  cacheEnabled: boolean;
  cacheTtlHours: number;
}

const DEFAULT_SETTINGS: UserSettings = {
  captureWebFetch: true,
  captureBashSuccess: true,
  captureBashErrors: true,
  captureTaskResults: true,
  suggestionLimit: 5,
  suggestionMinScore: 0.7,
  suggestionFrequency: 'always',
  notificationEnabled: true,
  notificationSound: false,
  cacheEnabled: true,
  cacheTtlHours: 24,
};

export function Settings() {
  const queryClient = useQueryClient();
  const { theme, resolvedTheme, setTheme } = useTheme();
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);
  const [saveMessage, setSaveMessage] = useState<string>('');

  // Process management state
  const [pruneParams, setPruneParams] = useState({ days: 30, max: 1000, execute: false });
  const [tagParams, setTagParams] = useState({ limit: 1000 });
  const [logViewer, setLogViewer] = useState({ logName: 'watcher', lines: 50 });
  const [activeJobId, setActiveJobId] = useState('');
  const [showJobModal, setShowJobModal] = useState(false);

  // Document indexing state
  const [indexingFolders, setIndexingFolders] = useState<string[]>([]);
  const [newFolder, setNewFolder] = useState('');

  // Fetch settings
  const { data: fetchedSettings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      try {
        const response = await apiClient.get('/settings');
        return response.data;
      } catch {
        return DEFAULT_SETTINGS;
      }
    },
  });

  useEffect(() => {
    if (fetchedSettings) {
      setSettings({ ...DEFAULT_SETTINGS, ...fetchedSettings });
    }
  }, [fetchedSettings]);

  // Save settings mutation
  const saveMutation = useMutation({
    mutationFn: async (newSettings: UserSettings) => {
      await apiClient.post('/settings', newSettings);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      setSaveMessage('Settings saved successfully!');
      setTimeout(() => setSaveMessage(''), 3000);
    },
  });

  const handleSave = () => {
    saveMutation.mutate(settings);
  };

  const handleReset = () => {
    setSettings(DEFAULT_SETTINGS);
    setSaveMessage('Settings reset to defaults');
    setTimeout(() => setSaveMessage(''), 3000);
  };

  // Process management queries
  const { data: watcherData } = useQuery<any>({
    queryKey: ['processes', 'watcher', 'status'],
    queryFn: () => apiClient.get('/processes/watcher/status').then((r: AxiosResponse) => r.data),
    refetchInterval: 5000,
  });

  const { data: schedulerData } = useQuery<any>({
    queryKey: ['scheduler', 'status'],
    queryFn: () => apiClient.get('/scheduler/status').then((r: AxiosResponse) => r.data),
    refetchInterval: 10000,
  });

  const { data: logData, refetch: refetchLog } = useQuery<any>({
    queryKey: ['logs', logViewer.logName, logViewer.lines],
    queryFn: () =>
      apiClient.get(`/logs/${logViewer.logName}`, {
        params: { lines: logViewer.lines }
      }).then((r: AxiosResponse) => r.data),
    enabled: false,
  });

  // Process management mutations
  const watcherMutation = useMutation({
    mutationFn: (start: boolean) =>
      start
        ? apiClient.post('/processes/watcher/start')
        : apiClient.post('/processes/watcher/stop'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['processes'] });
      setSaveMessage('Watcher status updated');
      setTimeout(() => setSaveMessage(''), 3000);
    },
    onError: (error: any) => {
      setSaveMessage(`Error: ${error.response?.data?.detail || error.message}`);
      setTimeout(() => setSaveMessage(''), 5000);
    },
  });

  const scriptMutation = useMutation({
    mutationFn: ({ endpoint, params }: { endpoint: string; params: any }) =>
      apiClient.post(endpoint, null, { params }),
    onSuccess: (data: AxiosResponse<any>) => {
      setActiveJobId(data.data.job_id);
      setShowJobModal(true);
    },
    onError: (error: any) => {
      setSaveMessage(`Error: ${error.response?.data?.detail || error.message}`);
      setTimeout(() => setSaveMessage(''), 5000);
    },
  });

  // Fetch indexing folders
  const { data: indexingConfig } = useQuery<any>({
    queryKey: ['indexing', 'folders'],
    queryFn: () => apiClient.get('/indexing/folders').then((r: AxiosResponse) => r.data),
  });

  // Update indexing folders mutation
  const foldersMutation = useMutation({
    mutationFn: (folders: string[]) =>
      apiClient.post('/indexing/folders', { folders }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['indexing'] });
      setSaveMessage('Indexing folders updated');
      setTimeout(() => setSaveMessage(''), 3000);
    },
    onError: (error: any) => {
      setSaveMessage(`Error: ${error.response?.data?.detail || error.message}`);
      setTimeout(() => setSaveMessage(''), 5000);
    },
  });

  // Database reset mutation
  const resetDbMutation = useMutation({
    mutationFn: () => apiClient.post('/database/reset', null, { params: { confirm: true } }),
    onSuccess: () => {
      queryClient.invalidateQueries();  // Invalidate all queries
      setSaveMessage('Database reset successfully');
      setTimeout(() => setSaveMessage(''), 3000);
    },
    onError: (error: any) => {
      setSaveMessage(`Error: ${error.response?.data?.detail || error.message}`);
      setTimeout(() => setSaveMessage(''), 5000);
    },
  });

  if (isLoading) {
    return (
      <div>
        <Header title="Settings" />
        <div className="p-6">
          <div className="flex items-center justify-center h-64">
            <div className="animate-pulse text-lg">Loading settings...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header title="Settings" />
      <div className="p-6 space-y-6">
        {saveMessage && (
          <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg p-4">
            <p className="text-green-800 dark:text-green-200 text-sm">{saveMessage}</p>
          </div>
        )}

        {/* Theme Settings */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              {resolvedTheme === 'dark' ? (
                <Moon className="h-5 w-5 text-indigo-600" />
              ) : (
                <Sun className="h-5 w-5 text-amber-600" />
              )}
              <CardTitle>Appearance</CardTitle>
            </div>
            <CardDescription>
              Customize the interface theme based on your preference
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div>
              <Label>Theme Mode</Label>
              <p className="text-sm text-muted-foreground mb-3">
                Choose your preferred color scheme
              </p>
              <div className="grid grid-cols-3 gap-3">
                <button
                  onClick={() => setTheme('light')}
                  className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all ${
                    theme === 'light'
                      ? 'border-blue-600 bg-blue-50 dark:bg-blue-950'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                  }`}
                >
                  <Sun className={`h-6 w-6 ${theme === 'light' ? 'text-blue-600' : 'text-gray-500'}`} />
                  <span className={`text-sm font-medium ${theme === 'light' ? 'text-blue-600' : 'text-gray-700 dark:text-gray-300'}`}>
                    Light
                  </span>
                </button>

                <button
                  onClick={() => setTheme('dark')}
                  className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all ${
                    theme === 'dark'
                      ? 'border-blue-600 bg-blue-50 dark:bg-blue-950'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                  }`}
                >
                  <Moon className={`h-6 w-6 ${theme === 'dark' ? 'text-blue-600' : 'text-gray-500'}`} />
                  <span className={`text-sm font-medium ${theme === 'dark' ? 'text-blue-600' : 'text-gray-700 dark:text-gray-300'}`}>
                    Dark
                  </span>
                </button>

                <button
                  onClick={() => setTheme('system')}
                  className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all ${
                    theme === 'system'
                      ? 'border-blue-600 bg-blue-50 dark:bg-blue-950'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                  }`}
                >
                  <Monitor className={`h-6 w-6 ${theme === 'system' ? 'text-blue-600' : 'text-gray-500'}`} />
                  <span className={`text-sm font-medium ${theme === 'system' ? 'text-blue-600' : 'text-gray-700 dark:text-gray-300'}`}>
                    System
                  </span>
                </button>
              </div>
              <p className="text-xs text-muted-foreground mt-3">
                {theme === 'system' && (
                  <>
                    Following system preference: <strong>{resolvedTheme}</strong>
                  </>
                )}
                {theme !== 'system' && (
                  <>
                    Current theme: <strong>{theme}</strong>
                  </>
                )}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Automatic Capture Settings */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5 text-blue-600" />
              <CardTitle>Automatic Capture</CardTitle>
            </div>
            <CardDescription>
              Control what information is automatically captured to memory
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label>WebFetch Documentation</Label>
                <p className="text-sm text-muted-foreground">
                  Auto-save documentation fetched online
                </p>
              </div>
              <Switch
                checked={settings.captureWebFetch}
                onCheckedChange={(checked) =>
                  setSettings((s) => ({ ...s, captureWebFetch: checked }))
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label>Successful Bash Commands</Label>
                <p className="text-sm text-muted-foreground">
                  Save deployment and installation commands
                </p>
              </div>
              <Switch
                checked={settings.captureBashSuccess}
                onCheckedChange={(checked) =>
                  setSettings((s) => ({ ...s, captureBashSuccess: checked }))
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label>Bash Errors</Label>
                <p className="text-sm text-muted-foreground">
                  Auto-capture failed commands with error details
                </p>
              </div>
              <Switch
                checked={settings.captureBashErrors}
                onCheckedChange={(checked) =>
                  setSettings((s) => ({ ...s, captureBashErrors: checked }))
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label>Task Agent Results</Label>
                <p className="text-sm text-muted-foreground">
                  Save output from specialized agents
                </p>
              </div>
              <Switch
                checked={settings.captureTaskResults}
                onCheckedChange={(checked) =>
                  setSettings((s) => ({ ...s, captureTaskResults: checked }))
                }
              />
            </div>
          </CardContent>
        </Card>

        {/* Suggestion Settings */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5 text-purple-600" />
              <CardTitle>Memory Suggestions</CardTitle>
            </div>
            <CardDescription>
              Configure how and when memory suggestions are shown
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <Label>Suggestion Limit</Label>
              <p className="text-sm text-muted-foreground mb-2">
                Maximum number of suggestions to show at once
              </p>
              <Input
                type="number"
                min="1"
                max="20"
                value={settings.suggestionLimit}
                onChange={(e) =>
                  setSettings((s) => ({
                    ...s,
                    suggestionLimit: parseInt(e.target.value) || 5,
                  }))
                }
              />
            </div>

            <div>
              <Label>Minimum Relevance Score</Label>
              <p className="text-sm text-muted-foreground mb-2">
                Only show suggestions above this relevance threshold (0-1)
              </p>
              <Slider
                value={[settings.suggestionMinScore]}
                onValueChange={([value]) =>
                  setSettings((s) => ({ ...s, suggestionMinScore: value }))
                }
                min={0}
                max={1}
                step={0.05}
              />
              <p className="text-sm text-right mt-1">
                Current: {settings.suggestionMinScore.toFixed(2)}
              </p>
            </div>

            <div>
              <Label>Suggestion Frequency</Label>
              <p className="text-sm text-muted-foreground mb-2">
                How often to show suggestions
              </p>
              <Select
                value={settings.suggestionFrequency}
                onChange={(e) =>
                  setSettings((s) => ({
                    ...s,
                    suggestionFrequency: e.target.value as any,
                  }))
                }
              >
                <option value="always">Every Message (Default)</option>
                <option value="hourly">Once Per Hour</option>
                <option value="daily">Once Per Day</option>
                <option value="never">Disabled</option>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Notification Settings */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Bell className="h-5 w-5 text-yellow-600" />
              <CardTitle>Notifications</CardTitle>
            </div>
            <CardDescription>
              Manage notification preferences
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label>Enable Notifications</Label>
                <p className="text-sm text-muted-foreground">
                  Show notification panel with alerts
                </p>
              </div>
              <Switch
                checked={settings.notificationEnabled}
                onCheckedChange={(checked) =>
                  setSettings((s) => ({ ...s, notificationEnabled: checked }))
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label>Notification Sound</Label>
                <p className="text-sm text-muted-foreground">
                  Play sound for new notifications (coming soon)
                </p>
              </div>
              <Switch
                checked={settings.notificationSound}
                onCheckedChange={(checked) =>
                  setSettings((s) => ({ ...s, notificationSound: checked }))
                }
                disabled
              />
            </div>
          </CardContent>
        </Card>

        {/* Cache Settings */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-green-600" />
              <CardTitle>Query Cache</CardTitle>
            </div>
            <CardDescription>
              Configure semantic query caching for faster responses
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label>Enable Cache</Label>
                <p className="text-sm text-muted-foreground">
                  Cache similar queries for faster responses
                </p>
              </div>
              <Switch
                checked={settings.cacheEnabled}
                onCheckedChange={(checked) =>
                  setSettings((s) => ({ ...s, cacheEnabled: checked }))
                }
              />
            </div>

            <div>
              <Label>Cache TTL (Hours)</Label>
              <p className="text-sm text-muted-foreground mb-2">
                How long to keep cached results (1-168 hours)
              </p>
              <Input
                type="number"
                min="1"
                max="168"
                value={settings.cacheTtlHours}
                onChange={(e) =>
                  setSettings((s) => ({
                    ...s,
                    cacheTtlHours: parseInt(e.target.value) || 24,
                  }))
                }
              />
            </div>
          </CardContent>
        </Card>

        {/* Background Processes */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-blue-600" />
              <CardTitle>Background Processes</CardTitle>
            </div>
            <CardDescription>
              Manage automated memory services
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* File Watcher */}
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <Label>File Watcher Service</Label>
                <p className="text-sm text-muted-foreground">
                  Auto-index documents as they change
                </p>
                {watcherData?.running && (
                  <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                    Running • PID {watcherData.pid} • {watcherData.last_activity || 'Active'}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={watcherData?.running ? "default" : "outline"}>
                  {watcherData?.running ? "Running" : "Stopped"}
                </Badge>
                <Switch
                  checked={watcherData?.running || false}
                  onCheckedChange={(c) => watcherMutation.mutate(c)}
                  disabled={watcherMutation.isPending}
                />
              </div>
            </div>

            {/* Scheduler */}
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <Label>Scheduled Consolidation</Label>
                <p className="text-sm text-muted-foreground">
                  Auto-cleanup every 24 hours
                </p>
                {schedulerData?.jobs?.[0]?.next_run && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Next: {new Date(schedulerData.jobs[0].next_run).toLocaleString()}
                  </p>
                )}
              </div>
              <Badge variant={schedulerData?.enabled ? "default" : "outline"}>
                {schedulerData?.enabled ? "Enabled" : "Disabled"}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Document Indexing */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-indigo-600" />
              <CardTitle>Document Indexing</CardTitle>
            </div>
            <CardDescription>
              Automatically index and search your documents
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Indexing Status */}
            <div className="p-4 rounded-lg border bg-muted/50">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="font-medium">Indexing Service</p>
                  <p className="text-sm text-muted-foreground">
                    {watcherData?.running
                      ? 'Documents are being automatically indexed'
                      : 'Enable the File Watcher to auto-index documents'}
                  </p>
                </div>
                <Badge
                  variant={watcherData?.running ? "default" : "secondary"}
                  className={watcherData?.running ? "bg-green-600" : ""}
                >
                  {watcherData?.running ? "Active" : "Inactive"}
                </Badge>
              </div>

              {watcherData?.running && (
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Watched Directory:</span>
                    <span className="font-mono">~/Documents</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Check Interval:</span>
                    <span>30 seconds</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Last Activity:</span>
                    <span>{watcherData.last_activity || 'Recently'}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Watched Folders (for file watcher) */}
            <div className="space-y-3 pt-2 border-t">
              <Label>Watched Folders (Auto-Indexing)</Label>
              <p className="text-sm text-muted-foreground">
                These folders are monitored by the File Watcher for automatic indexing. Use ~ for home directory (e.g., ~/Documents)
              </p>

              <div className="space-y-2">
                {indexingConfig?.folders?.map((folder: string, idx: number) => (
                  <div key={idx} className="flex items-center gap-2 p-2 rounded border bg-muted/30">
                    <Folder className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1 text-sm font-mono">{folder}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        const updated = indexingConfig.folders.filter((_: any, i: number) => i !== idx);
                        foldersMutation.mutate(updated);
                      }}
                      disabled={foldersMutation.isPending}
                    >
                      ✕
                    </Button>
                  </div>
                ))}
                {indexingConfig?.folders?.length === 0 && (
                  <p className="text-sm text-muted-foreground italic">No folders configured for auto-indexing</p>
                )}
              </div>

              <div className="flex gap-3 items-center">
                <Button
                  onClick={async () => {
                    try {
                      console.log('[Folder Picker] Checking API availability...');

                      // @ts-ignore - showDirectoryPicker is not in TypeScript types yet
                      if (typeof window.showDirectoryPicker !== 'function') {
                        console.error('[Folder Picker] API not available');
                        alert(
                          '⚠️ File System Access API not available\n\n' +
                          'This browser does not support the folder picker API.\n\n' +
                          'BRAVE USERS: Brave blocks this API by default for security.\n' +
                          'Enable it at: brave://flags/#file-system-access-api\n\n' +
                          'Alternative: Use the manual path input below.'
                        );
                        return;
                      }

                      console.log('[Folder Picker] Opening directory picker...');
                      // @ts-ignore
                      const dirHandle = await window.showDirectoryPicker({ mode: 'read' });
                      console.log('[Folder Picker] Folder selected:', dirHandle.name);

                      // Get the full path by requesting permission and reading
                      // Note: File System Access API doesn't expose full paths for security
                      // We'll use the name and let the user confirm the path manually
                      const folderName = dirHandle.name;
                      const folderPath = prompt(
                        `Selected folder: ${folderName}\n\nEnter the full path to this folder:\n(Use ~ for home directory, e.g., ~/Documents/${folderName})`,
                        `~/${folderName}`
                      );

                      if (folderPath && folderPath.trim()) {
                        console.log('[Folder Picker] Adding folder:', folderPath);
                        // Add to watched folders
                        const currentFolders = indexingConfig?.folders || [];
                        if (!currentFolders.includes(folderPath)) {
                          foldersMutation.mutate([...currentFolders, folderPath]);
                        } else {
                          setSaveMessage('Folder already in watch list');
                          setTimeout(() => setSaveMessage(''), 3000);
                        }
                      } else {
                        console.log('[Folder Picker] User cancelled path entry');
                      }
                    } catch (error) {
                      if ((error as Error).name === 'AbortError') {
                        console.log('[Folder Picker] User cancelled folder selection');
                      } else {
                        console.error('[Folder Picker] Error:', error);
                        alert(
                          '⚠️ Folder picker failed\n\n' +
                          `Error: ${(error as Error).message}\n\n` +
                          'BRAVE USERS: Enable File System Access API at:\n' +
                          'brave://flags/#file-system-access-api\n\n' +
                          'Alternative: Use the manual path input below.'
                        );
                      }
                    }
                  }}
                  className="flex items-center gap-2"
                  disabled={foldersMutation.isPending}
                >
                  <Folder className="h-4 w-4" />
                  Open Finder to Select Folders
                </Button>
                <p className="text-xs text-muted-foreground">
                  Chrome/Edge (or Brave with flag enabled)
                </p>
              </div>

              <div className="flex gap-2">
                <Input
                  placeholder="~/Documents/MyFolder"
                  value={newFolder}
                  onChange={(e) => setNewFolder(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && newFolder.trim()) {
                      foldersMutation.mutate([...(indexingConfig?.folders || []), newFolder]);
                      setNewFolder('');
                    }
                  }}
                />
                <Button
                  onClick={() => {
                    if (newFolder.trim()) {
                      foldersMutation.mutate([...(indexingConfig?.folders || []), newFolder]);
                      setNewFolder('');
                    }
                  }}
                  disabled={!newFolder.trim() || foldersMutation.isPending}
                >
                  Add
                </Button>
              </div>

              <div className="p-4 rounded-lg border bg-muted/30 mt-3">
                <p className="text-sm font-medium mb-2">Alternative: CLI Indexing</p>
                <code className="text-xs bg-black text-green-400 p-2 rounded block whitespace-pre-wrap">
                  python3 ~/.claude/memory/scripts/index_documents.py --path /your/folder --parallel
                </code>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex gap-2 pt-2 border-t">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => window.location.href = '/documents'}
              >
                <FileText className="h-4 w-4 mr-2" />
                View Documents
              </Button>
              <Button
                variant="outline"
                onClick={() => scriptMutation.mutate({
                  endpoint: '/indexing/reindex',
                  params: {}
                })}
                disabled={scriptMutation.isPending}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Re-index All
              </Button>
            </div>

            {/* Info */}
            <div className="text-xs text-muted-foreground space-y-1 pt-2 border-t">
              <p>• Supported formats: .txt, .md, .pdf, .docx, .py, .js, .ts, .json, .yaml, .xml</p>
              <p>• Files are chunked for optimal retrieval</p>
              <p>• Enable File Watcher in Background Processes above to activate</p>
            </div>
          </CardContent>
        </Card>

        {/* Maintenance Tools */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Wrench className="h-5 w-5 text-orange-600" />
              <CardTitle>Maintenance Tools</CardTitle>
            </div>
            <CardDescription>
              Run manual cleanup and optimization tasks
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Prune */}
            <div className="space-y-3">
              <Label>Prune Old Memories</Label>
              <p className="text-sm text-muted-foreground">
                Remove low-value memories older than specified days
              </p>
              <div className="grid grid-cols-3 gap-3">
                <Input
                  type="number"
                  placeholder="Days"
                  value={pruneParams.days}
                  onChange={(e) => setPruneParams(p => ({...p, days: parseInt(e.target.value) || 30}))}
                />
                <Input
                  type="number"
                  placeholder="Max"
                  value={pruneParams.max}
                  onChange={(e) => setPruneParams(p => ({...p, max: parseInt(e.target.value) || 1000}))}
                />
                <Button
                  onClick={() => scriptMutation.mutate({
                    endpoint: '/jobs/prune',
                    params: pruneParams
                  })}
                  disabled={scriptMutation.isPending}
                >
                  {pruneParams.execute ? 'Execute' : 'Dry Run'}
                </Button>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={pruneParams.execute}
                  onCheckedChange={(c) => setPruneParams(p => ({...p, execute: c}))}
                />
                <Label className="text-sm font-normal">Actually delete (not dry-run)</Label>
              </div>
            </div>

            {/* Tag */}
            <div className="space-y-3">
              <Label>Auto-Tag Memories</Label>
              <p className="text-sm text-muted-foreground">
                Extract tech stack entities and auto-tag
              </p>
              <div className="grid grid-cols-2 gap-3">
                <Input
                  type="number"
                  placeholder="Limit"
                  value={tagParams.limit}
                  onChange={(e) => setTagParams({limit: parseInt(e.target.value) || 1000})}
                />
                <Button
                  onClick={() => scriptMutation.mutate({
                    endpoint: '/jobs/tag',
                    params: tagParams
                  })}
                  disabled={scriptMutation.isPending}
                >
                  Run Tagger
                </Button>
              </div>
            </div>

            {/* Manual Consolidation */}
            <div className="space-y-3">
              <Label>Manual Consolidation</Label>
              <p className="text-sm text-muted-foreground mb-2">
                Merge similar memories and archive old ones
              </p>
              <Button
                onClick={() => scriptMutation.mutate({
                  endpoint: '/scheduler/jobs/consolidation_job/trigger',
                  params: {}
                })}
                disabled={scriptMutation.isPending}
                variant="outline"
                className="w-full"
              >
                Run Consolidation Now
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* System Logs */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-purple-600" />
              <CardTitle>System Logs</CardTitle>
            </div>
            <CardDescription>
              View process logs and activity history
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <Select
                value={logViewer.logName}
                onChange={(e) => setLogViewer(v => ({...v, logName: e.target.value}))}
              >
                <option value="watcher">File Watcher</option>
                <option value="consolidation">Consolidation</option>
                <option value="document-watcher">LaunchAgent</option>
              </Select>
              <Input
                type="number"
                value={logViewer.lines}
                onChange={(e) => setLogViewer(v => ({...v, lines: parseInt(e.target.value) || 50}))}
                placeholder="Lines"
                min="1"
                max="1000"
              />
              <Button onClick={() => refetchLog()}>View</Button>
            </div>

            {logData && (
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <p className="text-sm text-muted-foreground">
                    {logData.exists ? `${logData.lines?.length || 0} lines` : 'Log not found'}
                  </p>
                  {logData.exists && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        apiClient.post(`/logs/${logViewer.logName}/clear`).then(() => {
                          setSaveMessage('Log cleared');
                          setTimeout(() => setSaveMessage(''), 3000);
                          refetchLog();
                        });
                      }}
                    >
                      Clear
                    </Button>
                  )}
                </div>
                {logData.exists && logData.lines && (
                  <div className="rounded border bg-gray-50 dark:bg-gray-900 p-4 max-h-96 overflow-y-auto">
                    <pre className="text-xs font-mono whitespace-pre-wrap">
                      {logData.lines.join('\n')}
                    </pre>
                  </div>
                )}
                {!logData.exists && (
                  <div className="rounded border border-yellow-200 bg-yellow-50 dark:bg-yellow-950 dark:border-yellow-800 p-4">
                    <p className="text-sm text-yellow-800 dark:text-yellow-200">
                      Log file not found
                    </p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Advanced */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-red-600" />
              <CardTitle>Advanced</CardTitle>
            </div>
            <CardDescription>
              Dangerous operations that cannot be undone
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg border border-red-200 bg-red-50 dark:bg-red-950 dark:border-red-800">
              <div className="space-y-3">
                <div>
                  <p className="font-medium text-red-900 dark:text-red-100">Reset Database</p>
                  <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                    Permanently delete all memories, documents, and history from the database. This action cannot be undone.
                  </p>
                </div>
                <Button
                  variant="destructive"
                  onClick={() => {
                    if (confirm('⚠️ WARNING: This will permanently delete ALL memories, documents, and history.\n\nThis action CANNOT be undone.\n\nAre you absolutely sure?')) {
                      resetDbMutation.mutate();
                    }
                  }}
                  disabled={resetDbMutation.isPending}
                  className="bg-red-600 hover:bg-red-700"
                >
                  {resetDbMutation.isPending ? 'Resetting...' : 'Reset Database'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-between">
          <Button variant="outline" onClick={handleReset}>
            Reset to Defaults
          </Button>
          <Button onClick={handleSave} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? 'Saving...' : 'Save Settings'}
          </Button>
        </div>
      </div>

      {/* Job Progress Modal */}
      <JobProgressModal
        jobId={activeJobId}
        open={showJobModal}
        onClose={() => setShowJobModal(false)}
      />
    </div>
  );
}
