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
import { Settings as SettingsIcon, Bell, Database, RefreshCw, AlertCircle, Moon, Sun, Monitor, Activity, Wrench, FileText, Folder, Recycle } from 'lucide-react';
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

  // Memory Lifecycle
  autoSupersedeEnabled: boolean;
  autoSupersedeThreshold: number;
  autoSupersedeUpper: number;
  dedupThreshold: number;

  // Intelligence & Analytics
  auditRetentionDays: number;
  patternDetectionIntervalHours: number;
  qualityUpdateIntervalHours: number;
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
  autoSupersedeEnabled: true,
  autoSupersedeThreshold: 0.85,
  autoSupersedeUpper: 0.91,
  dedupThreshold: 0.92,
  auditRetentionDays: 90,
  patternDetectionIntervalHours: 24,
  qualityUpdateIntervalHours: 24,
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
    onError: (error: any) => {
      setSaveMessage(`Error saving settings: ${error.response?.data?.detail || error.message}`);
      setTimeout(() => setSaveMessage(''), 5000);
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

  // Consolidation mutation
  const consolidateMutation = useMutation({
    mutationFn: ({ older_than_days = 7, dry_run = false }: { older_than_days?: number; dry_run?: boolean }) =>
      apiClient.post('/consolidate', null, { params: { older_than_days, dry_run } }),
    onSuccess: (data: AxiosResponse<any>) => {
      const result = data.data;
      setSaveMessage(`Consolidation complete: ${result.consolidated || 0} memories consolidated, ${result.archived || 0} archived`);
      setTimeout(() => setSaveMessage(''), 5000);
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
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
      <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]">
        <Header title="Settings" />
        <div className="p-6">
          <div className="flex items-center justify-center h-64">
            <div className="animate-pulse text-lg text-white/90">Loading settings...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]">
      <Header title="Settings" />
      <div className="p-4 sm:p-8 space-y-6 max-w-[1800px] mx-auto">
        {/* Hero Section */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-500/10 via-teal-500/10 to-green-500/10 p-6 border border-white/5">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 via-transparent to-teal-500/5" />
          <div className="relative flex items-center gap-4">
            <div className="p-3 bg-emerald-500/10 rounded-xl ring-1 ring-emerald-500/20">
              <SettingsIcon className="h-8 w-8 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">System Configuration</h1>
              <p className="text-white/60 mt-1">
                Customize memory capture, automation, and system behavior
              </p>
            </div>
          </div>
        </div>

        {saveMessage && (
          <div className={`backdrop-blur-sm rounded-xl p-4 ${
            saveMessage.startsWith('Error')
              ? 'bg-red-500/20 border border-red-500/30'
              : 'bg-emerald-500/20 border border-emerald-500/30'
          }`}>
            <p className={`text-sm ${saveMessage.startsWith('Error') ? 'text-red-300' : 'text-emerald-300'}`}>
              {saveMessage}
            </p>
          </div>
        )}

        {/* Theme Settings */}
        <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-emerald-500/10 transition-all">
          <CardHeader>
            <div className="flex items-center gap-2">
              {resolvedTheme === 'dark' ? (
                <Moon className="h-5 w-5 text-emerald-400" />
              ) : (
                <Sun className="h-5 w-5 text-amber-400" />
              )}
              <CardTitle className="text-white">Appearance</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Customize the interface theme based on your preference
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div>
              <Label className="text-white/90">Theme Mode</Label>
              <p className="text-sm text-white/50 mb-3">
                Choose your preferred color scheme
              </p>
              <div className="grid grid-cols-3 gap-3">
                <button
                  onClick={() => setTheme('light')}
                  className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all ${
                    theme === 'light'
                      ? 'border-emerald-500 bg-emerald-500/10 shadow-lg shadow-emerald-500/20'
                      : 'border-white/10 bg-[#0a0a0a] hover:border-white/20'
                  }`}
                >
                  <Sun className={`h-6 w-6 ${theme === 'light' ? 'text-emerald-400' : 'text-white/50'}`} />
                  <span className={`text-sm font-medium ${theme === 'light' ? 'text-emerald-400' : 'text-white/70'}`}>
                    Light
                  </span>
                </button>

                <button
                  onClick={() => setTheme('dark')}
                  className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all ${
                    theme === 'dark'
                      ? 'border-emerald-500 bg-emerald-500/10 shadow-lg shadow-emerald-500/20'
                      : 'border-white/10 bg-[#0a0a0a] hover:border-white/20'
                  }`}
                >
                  <Moon className={`h-6 w-6 ${theme === 'dark' ? 'text-emerald-400' : 'text-white/50'}`} />
                  <span className={`text-sm font-medium ${theme === 'dark' ? 'text-emerald-400' : 'text-white/70'}`}>
                    Dark
                  </span>
                </button>

                <button
                  onClick={() => setTheme('system')}
                  className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all ${
                    theme === 'system'
                      ? 'border-emerald-500 bg-emerald-500/10 shadow-lg shadow-emerald-500/20'
                      : 'border-white/10 bg-[#0a0a0a] hover:border-white/20'
                  }`}
                >
                  <Monitor className={`h-6 w-6 ${theme === 'system' ? 'text-emerald-400' : 'text-white/50'}`} />
                  <span className={`text-sm font-medium ${theme === 'system' ? 'text-emerald-400' : 'text-white/70'}`}>
                    System
                  </span>
                </button>
              </div>
              <p className="text-xs text-white/40 mt-3">
                {theme === 'system' && (
                  <>
                    Following system preference: <strong className="text-white/60">{resolvedTheme}</strong>
                  </>
                )}
                {theme !== 'system' && (
                  <>
                    Current theme: <strong className="text-white/60">{theme}</strong>
                  </>
                )}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Section Divider */}
        <div className="border-t border-white/10 pt-6">
          <h2 className="text-lg font-semibold text-white/90 mb-4">Memory Capture</h2>
        </div>

        {/* Automatic Capture Settings */}
        <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-blue-500/10 transition-all">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5 text-blue-400" />
              <CardTitle className="text-white">Automatic Capture</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Control what information is automatically captured to memory
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5 hover:border-white/10 transition-colors">
              <div>
                <Label className="text-white/90">WebFetch Documentation</Label>
                <p className="text-sm text-white/50">
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

            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5 hover:border-white/10 transition-colors">
              <div>
                <Label className="text-white/90">Successful Bash Commands</Label>
                <p className="text-sm text-white/50">
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

            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5 hover:border-white/10 transition-colors">
              <div>
                <Label className="text-white/90">Bash Errors</Label>
                <p className="text-sm text-white/50">
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

            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5 hover:border-white/10 transition-colors">
              <div>
                <Label className="text-white/90">Task Agent Results</Label>
                <p className="text-sm text-white/50">
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
        <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-purple-500/10 transition-all">
          <CardHeader>
            <div className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5 text-purple-400" />
              <CardTitle className="text-white">Memory Suggestions</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Configure how and when memory suggestions are shown
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <Label className="text-white/90">Suggestion Limit</Label>
              <p className="text-sm text-white/50 mb-2">
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
                className="bg-[#0f0f0f] border-white/10 text-white"
              />
            </div>

            <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <Label className="text-white/90">Minimum Relevance Score</Label>
              <p className="text-sm text-white/50 mb-2">
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
              <p className="text-sm text-right mt-1 text-white/70">
                Current: {settings.suggestionMinScore.toFixed(2)}
              </p>
            </div>

            <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <Label className="text-white/90">Suggestion Frequency</Label>
              <p className="text-sm text-white/50 mb-2">
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
                className="bg-[#0f0f0f] border-white/10 text-white"
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
        <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-amber-500/10 transition-all">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Bell className="h-5 w-5 text-amber-400" />
              <CardTitle className="text-white">Notifications</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Manage notification preferences
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5 hover:border-white/10 transition-colors">
              <div>
                <Label className="text-white/90">Enable Notifications</Label>
                <p className="text-sm text-white/50">
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

            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5 hover:border-white/10 transition-colors">
              <div>
                <Label className="text-white/90">Notification Sound</Label>
                <p className="text-sm text-white/50">
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
        <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-emerald-500/10 transition-all">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-emerald-400" />
              <CardTitle className="text-white">Query Cache</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Configure semantic query caching for faster responses
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5 hover:border-white/10 transition-colors">
              <div>
                <Label className="text-white/90">Enable Cache</Label>
                <p className="text-sm text-white/50">
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

            <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <Label className="text-white/90">Cache TTL (Hours)</Label>
              <p className="text-sm text-white/50 mb-2">
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
                className="bg-[#0f0f0f] border-white/10 text-white"
              />
            </div>
          </CardContent>
        </Card>

        {/* Memory Lifecycle Settings */}
        <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-cyan-500/10 transition-all">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Recycle className="h-5 w-5 text-cyan-400" />
              <CardTitle className="text-white">Memory Lifecycle</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Control how memories are deduplicated, superseded, and archived
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Auto-Supersede Toggle */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-white/5 hover:border-white/10 transition-colors">
              <div>
                <Label className="text-white/90">Auto-Supersede</Label>
                <p className="text-sm text-white/50">
                  Automatically archive older memories when a newer version is stored
                </p>
              </div>
              <Switch
                checked={settings.autoSupersedeEnabled}
                onCheckedChange={(checked) =>
                  setSettings((s) => ({ ...s, autoSupersedeEnabled: checked }))
                }
              />
            </div>

            {/* Threshold Visualization */}
            <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <Label className="text-white/90">Similarity Thresholds</Label>
              <p className="text-sm text-white/50 mb-4">
                How the system handles memories at different similarity levels
              </p>

              {/* Visual threshold bar */}
              <div className="relative h-8 rounded-lg overflow-hidden mb-4">
                <div className="absolute inset-0 flex">
                  <div
                    className="bg-white/5 flex items-center justify-center text-xs text-white/40"
                    style={{ width: `${settings.autoSupersedeThreshold * 100}%` }}
                  >
                    Ignored
                  </div>
                  <div
                    className="bg-cyan-500/20 border-x border-cyan-500/30 flex items-center justify-center text-xs text-cyan-300"
                    style={{ width: `${(settings.autoSupersedeUpper - settings.autoSupersedeThreshold) * 100}%` }}
                  >
                    Supersede
                  </div>
                  <div
                    className="bg-amber-500/20 border-r border-amber-500/30 flex items-center justify-center text-xs text-amber-300"
                    style={{ width: `${(settings.dedupThreshold - settings.autoSupersedeUpper) * 100}%` }}
                  >
                    Gap
                  </div>
                  <div
                    className="bg-emerald-500/20 flex items-center justify-center text-xs text-emerald-300"
                    style={{ width: `${(1 - settings.dedupThreshold) * 100}%` }}
                  >
                    Merge
                  </div>
                </div>
              </div>

              {/* Auto-Supersede Lower Threshold */}
              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-white/70">Supersede Threshold (lower)</span>
                  <span className="text-sm font-mono text-cyan-400">{settings.autoSupersedeThreshold.toFixed(2)}</span>
                </div>
                <Slider
                  value={[settings.autoSupersedeThreshold]}
                  onValueChange={([value]) =>
                    setSettings((s) => ({
                      ...s,
                      autoSupersedeThreshold: Math.min(value, s.autoSupersedeUpper - 0.01),
                    }))
                  }
                  min={0.70}
                  max={0.95}
                  step={0.01}
                  disabled={!settings.autoSupersedeEnabled}
                />
                <p className="text-xs text-white/40">
                  Minimum similarity to trigger auto-supersede (default: 0.85)
                </p>
              </div>

              {/* Auto-Supersede Upper Threshold */}
              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-white/70">Supersede Threshold (upper)</span>
                  <span className="text-sm font-mono text-cyan-400">{settings.autoSupersedeUpper.toFixed(2)}</span>
                </div>
                <Slider
                  value={[settings.autoSupersedeUpper]}
                  onValueChange={([value]) =>
                    setSettings((s) => ({
                      ...s,
                      autoSupersedeUpper: Math.max(
                        Math.min(value, s.dedupThreshold - 0.01),
                        s.autoSupersedeThreshold + 0.01
                      ),
                    }))
                  }
                  min={0.70}
                  max={0.95}
                  step={0.01}
                  disabled={!settings.autoSupersedeEnabled}
                />
                <p className="text-xs text-white/40">
                  Above this, deduplication takes over (default: 0.91)
                </p>
              </div>

              {/* Dedup Threshold */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-white/70">Dedup Merge Threshold</span>
                  <span className="text-sm font-mono text-emerald-400">{settings.dedupThreshold.toFixed(2)}</span>
                </div>
                <Slider
                  value={[settings.dedupThreshold]}
                  onValueChange={([value]) =>
                    setSettings((s) => ({
                      ...s,
                      dedupThreshold: Math.max(value, s.autoSupersedeUpper + 0.01),
                    }))
                  }
                  min={0.80}
                  max={0.99}
                  step={0.01}
                />
                <p className="text-xs text-white/40">
                  Near-identical content is merged instead of duplicated (default: 0.92)
                </p>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
              <p className="text-xs text-cyan-300">
                When you store "API moved to /v2", the system finds the old "/v1" memory
                (similarity ~0.88), creates a supersedes link, and archives it automatically.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Section Divider */}
        <div className="border-t border-white/10 pt-6">
          <h2 className="text-lg font-semibold text-white/90 mb-4">System Services</h2>
        </div>

        {/* Background Processes */}
        <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-blue-500/10 transition-all">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-blue-400" />
              <CardTitle className="text-white">Background Processes</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Manage automated memory services
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* File Watcher */}
            <div className="flex items-center justify-between p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <div className="flex-1">
                <Label className="text-white/90">File Watcher Service</Label>
                <p className="text-sm text-white/50">
                  Auto-index documents as they change
                </p>
                {watcherData?.running && (
                  <p className="text-xs text-emerald-400 mt-1">
                    Running • PID {watcherData.pid} • {watcherData.last_activity || 'Active'}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Badge
                  variant={watcherData?.running ? "default" : "outline"}
                  className={watcherData?.running ? "bg-emerald-500 text-white" : "bg-white/10 text-white/70"}
                >
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
            <div className="flex items-center justify-between p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <div className="flex-1">
                <Label className="text-white/90">Scheduled Consolidation</Label>
                <p className="text-sm text-white/50">
                  Auto-cleanup every 24 hours
                </p>
                {schedulerData?.jobs?.[0]?.next_run && (
                  <p className="text-xs text-white/40 mt-1">
                    Next: {new Date(schedulerData.jobs[0].next_run).toLocaleString()}
                  </p>
                )}
              </div>
              <Badge
                variant={schedulerData?.enabled ? "default" : "outline"}
                className={schedulerData?.enabled ? "bg-emerald-500 text-white" : "bg-white/10 text-white/70"}
              >
                {schedulerData?.enabled ? "Enabled" : "Disabled"}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Document Indexing */}
        <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-indigo-500/10 transition-all">
          <CardHeader>
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-indigo-400" />
              <CardTitle className="text-white">Document Indexing</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Automatically index and search your documents
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Indexing Status */}
            <div className="p-4 rounded-lg border bg-[#0a0a0a] border-white/5">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="font-medium text-white/90">Indexing Service</p>
                  <p className="text-sm text-white/50">
                    {watcherData?.running
                      ? 'Documents are being automatically indexed'
                      : 'Enable the File Watcher to auto-index documents'}
                  </p>
                </div>
                <Badge
                  variant={watcherData?.running ? "default" : "secondary"}
                  className={watcherData?.running ? "bg-emerald-500 text-white" : "bg-white/10 text-white/70"}
                >
                  {watcherData?.running ? "Active" : "Inactive"}
                </Badge>
              </div>

              {watcherData?.running && (
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between text-white/70">
                    <span className="text-white/50">Watched Directory:</span>
                    <span className="font-mono text-white/90">~/Documents</span>
                  </div>
                  <div className="flex justify-between text-white/70">
                    <span className="text-white/50">Check Interval:</span>
                    <span className="text-white/90">30 seconds</span>
                  </div>
                  <div className="flex justify-between text-white/70">
                    <span className="text-white/50">Last Activity:</span>
                    <span className="text-white/90">{watcherData.last_activity || 'Recently'}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Watched Folders */}
            <div className="space-y-3 pt-2 border-t border-white/10">
              <Label className="text-white/90">Watched Folders (Auto-Indexing)</Label>
              <p className="text-sm text-white/50">
                These folders are monitored by the File Watcher for automatic indexing. Use ~ for home directory (e.g., ~/Documents)
              </p>

              <div className="space-y-2">
                {indexingConfig?.folders?.map((folder: string, idx: number) => (
                  <div key={idx} className="flex items-center gap-2 p-2 rounded border bg-[#0a0a0a] border-white/5">
                    <Folder className="h-4 w-4 text-white/50" />
                    <span className="flex-1 text-sm font-mono text-white/90">{folder}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        const updated = indexingConfig.folders.filter((_: any, i: number) => i !== idx);
                        foldersMutation.mutate(updated);
                      }}
                      disabled={foldersMutation.isPending}
                      className="text-white/70 hover:text-white hover:bg-white/10"
                    >
                      ✕
                    </Button>
                  </div>
                ))}
                {indexingConfig?.folders?.length === 0 && (
                  <p className="text-sm text-white/40 italic">No folders configured for auto-indexing</p>
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

                      const folderName = dirHandle.name;
                      const folderPath = prompt(
                        `Selected folder: ${folderName}\n\nEnter the full path to this folder:\n(Use ~ for home directory, e.g., ~/Documents/${folderName})`,
                        `~/${folderName}`
                      );

                      if (folderPath && folderPath.trim()) {
                        console.log('[Folder Picker] Adding folder:', folderPath);
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
                  className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white"
                  disabled={foldersMutation.isPending}
                >
                  <Folder className="h-4 w-4" />
                  Open Finder to Select Folders
                </Button>
                <p className="text-xs text-white/40">
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
                  className="bg-[#0a0a0a] border-white/10 text-white"
                />
                <Button
                  onClick={() => {
                    if (newFolder.trim()) {
                      foldersMutation.mutate([...(indexingConfig?.folders || []), newFolder]);
                      setNewFolder('');
                    }
                  }}
                  disabled={!newFolder.trim() || foldersMutation.isPending}
                  className="bg-emerald-500 hover:bg-emerald-600 text-white"
                >
                  Add
                </Button>
              </div>

              <div className="p-4 rounded-lg border bg-[#0a0a0a] border-white/5 mt-3">
                <p className="text-sm font-medium mb-2 text-white/90">Alternative: CLI Indexing</p>
                <code className="text-xs bg-black text-emerald-400 p-2 rounded block whitespace-pre-wrap">
                  python3 ~/.claude/memory/scripts/index_documents.py --path /your/folder --parallel
                </code>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex gap-2 pt-2 border-t border-white/10">
              <Button
                variant="outline"
                className="flex-1 bg-[#0a0a0a] border-white/10 text-white/90 hover:bg-white/5"
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
                className="bg-[#0a0a0a] border-white/10 text-white/90 hover:bg-white/5"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Re-index All
              </Button>
            </div>

            {/* Info */}
            <div className="text-xs text-white/50 space-y-1 pt-2 border-t border-white/10">
              <p>• Supported formats: .txt, .md, .pdf, .docx, .py, .js, .ts, .json, .yaml, .xml</p>
              <p>• Files are chunked for optimal retrieval</p>
              <p>• Enable File Watcher in Background Processes above to activate</p>
            </div>
          </CardContent>
        </Card>

        {/* Section Divider */}
        <div className="border-t border-white/10 pt-6">
          <h2 className="text-lg font-semibold text-white/90 mb-4">Maintenance</h2>
        </div>

        {/* Maintenance Tools */}
        <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-orange-500/10 transition-all">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Wrench className="h-5 w-5 text-orange-400" />
              <CardTitle className="text-white">Maintenance Tools</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Run manual cleanup and optimization tasks
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Prune */}
            <div className="space-y-3 p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <Label className="text-white/90">Prune Old Memories</Label>
              <p className="text-sm text-white/50">
                Remove low-value memories older than specified days
              </p>
              <div className="grid grid-cols-3 gap-3">
                <Input
                  type="number"
                  placeholder="Days"
                  value={pruneParams.days}
                  onChange={(e) => setPruneParams(p => ({...p, days: parseInt(e.target.value) || 30}))}
                  className="bg-[#0f0f0f] border-white/10 text-white"
                />
                <Input
                  type="number"
                  placeholder="Max"
                  value={pruneParams.max}
                  onChange={(e) => setPruneParams(p => ({...p, max: parseInt(e.target.value) || 1000}))}
                  className="bg-[#0f0f0f] border-white/10 text-white"
                />
                <Button
                  onClick={() => scriptMutation.mutate({
                    endpoint: '/jobs/prune',
                    params: pruneParams
                  })}
                  disabled={scriptMutation.isPending}
                  className="bg-orange-500 hover:bg-orange-600 text-white"
                >
                  {pruneParams.execute ? 'Execute' : 'Dry Run'}
                </Button>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={pruneParams.execute}
                  onCheckedChange={(c) => setPruneParams(p => ({...p, execute: c}))}
                />
                <Label className="text-sm font-normal text-white/70">Actually delete (not dry-run)</Label>
              </div>
            </div>

            {/* Tag */}
            <div className="space-y-3 p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <Label className="text-white/90">Auto-Tag Memories</Label>
              <p className="text-sm text-white/50">
                Extract tech stack entities and auto-tag
              </p>
              <div className="grid grid-cols-2 gap-3">
                <Input
                  type="number"
                  placeholder="Limit"
                  value={tagParams.limit}
                  onChange={(e) => setTagParams({limit: parseInt(e.target.value) || 1000})}
                  className="bg-[#0f0f0f] border-white/10 text-white"
                />
                <Button
                  onClick={() => scriptMutation.mutate({
                    endpoint: '/jobs/tag',
                    params: tagParams
                  })}
                  disabled={scriptMutation.isPending}
                  className="bg-purple-500 hover:bg-purple-600 text-white"
                >
                  Run Tagger
                </Button>
              </div>
            </div>

            {/* Manual Consolidation */}
            <div className="space-y-3 p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <Label className="text-white/90">Manual Consolidation</Label>
              <p className="text-sm text-white/50 mb-2">
                Merge similar memories and archive old ones (last 7 days)
              </p>
              <Button
                onClick={() => consolidateMutation.mutate({ older_than_days: 7, dry_run: false })}
                disabled={consolidateMutation.isPending}
                variant="outline"
                className="w-full bg-[#0f0f0f] border-white/10 text-white/90 hover:bg-white/5"
              >
                {consolidateMutation.isPending ? 'Running...' : 'Run Consolidation Now'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* System Logs */}
        <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-purple-500/10 transition-all">
          <CardHeader>
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-purple-400" />
              <CardTitle className="text-white">System Logs</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              View process logs and activity history
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <Select
                value={logViewer.logName}
                onChange={(e) => setLogViewer(v => ({...v, logName: e.target.value}))}
                className="bg-[#0a0a0a] border-white/10 text-white"
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
                className="bg-[#0a0a0a] border-white/10 text-white"
              />
              <Button
                onClick={() => refetchLog()}
                className="bg-purple-500 hover:bg-purple-600 text-white"
              >
                View
              </Button>
            </div>

            {logData && (
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <p className="text-sm text-white/50">
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
                      className="text-white/70 hover:text-white hover:bg-white/10"
                    >
                      Clear
                    </Button>
                  )}
                </div>
                {logData.exists && logData.lines && (
                  <div className="rounded border bg-black border-white/10 p-4 max-h-96 overflow-y-auto">
                    <pre className="text-xs font-mono whitespace-pre-wrap text-emerald-400">
                      {logData.lines.join('\n')}
                    </pre>
                  </div>
                )}
                {!logData.exists && (
                  <div className="rounded border border-amber-500/30 bg-amber-500/10 p-4">
                    <p className="text-sm text-amber-300">
                      Log file not found
                    </p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Intelligence & Analytics Settings */}
        <Card className="bg-[#0f0f0f] border border-white/10 shadow-xl hover:shadow-purple-500/10 transition-all">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-purple-400" />
              <CardTitle className="text-white">Intelligence & Analytics</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Advanced memory intelligence settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Audit Trail Retention */}
            <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <Label className="text-white/90">Audit Trail Retention Period</Label>
              <p className="text-sm text-white/50 mb-2">
                How long to keep archived memories before purging (30-365 days)
              </p>
              <div className="flex items-center gap-3">
                <Input
                  type="number"
                  min="30"
                  max="365"
                  value={settings.auditRetentionDays}
                  onChange={(e) =>
                    setSettings((s) => ({
                      ...s,
                      auditRetentionDays: parseInt(e.target.value) || 90,
                    }))
                  }
                  className="w-32 bg-[#0f0f0f] border-white/10 text-white"
                />
                <span className="text-sm text-white/50">days</span>
              </div>
            </div>

            {/* Pattern Detection Schedule */}
            <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <Label className="text-white/90">Pattern Detection Schedule</Label>
              <p className="text-sm text-white/50 mb-2">
                How often to run relationship inference
              </p>
              <Select
                value={String(settings.patternDetectionIntervalHours)}
                onChange={(e) =>
                  setSettings((s) => ({
                    ...s,
                    patternDetectionIntervalHours: parseInt(e.target.value) || 24,
                  }))
                }
                className="bg-[#0f0f0f] border-white/10 text-white"
              >
                <option value="6">Every 6 hours</option>
                <option value="12">Every 12 hours</option>
                <option value="24">Every 24 hours</option>
              </Select>
            </div>

            {/* Quality Score Update Frequency */}
            <div className="p-4 rounded-lg bg-[#0a0a0a] border border-white/5">
              <Label className="text-white/90">Quality Score Update Frequency</Label>
              <p className="text-sm text-white/50 mb-2">
                How often to recalculate quality scores and promote tiers
              </p>
              <Select
                value={String(settings.qualityUpdateIntervalHours)}
                onChange={(e) =>
                  setSettings((s) => ({
                    ...s,
                    qualityUpdateIntervalHours: parseInt(e.target.value) || 24,
                  }))
                }
                className="bg-[#0f0f0f] border-white/10 text-white"
              >
                <option value="6">Every 6 hours</option>
                <option value="12">Every 12 hours</option>
                <option value="24">Every 24 hours</option>
              </Select>
            </div>

            <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20">
              <p className="text-xs text-purple-300">
                These settings control quality tracking, pattern detection, lifecycle state machine,
                and audit trail. Changes take effect immediately for scheduler jobs, and persist across restarts.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Advanced */}
        <Card className="bg-[#0f0f0f] border border-red-500/30 shadow-xl hover:shadow-red-500/20 transition-all">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-red-400" />
              <CardTitle className="text-white">Advanced</CardTitle>
            </div>
            <CardDescription className="text-white/60">
              Dangerous operations that cannot be undone
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg border border-red-500/30 bg-red-500/10">
              <div className="space-y-3">
                <div>
                  <p className="font-medium text-red-300">Reset Database</p>
                  <p className="text-sm text-red-200/80 mt-1">
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
                  className="bg-red-600 hover:bg-red-700 text-white shadow-lg shadow-red-500/20"
                >
                  {resetDbMutation.isPending ? 'Resetting...' : 'Reset Database'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-between pt-6 border-t border-white/10">
          <Button
            variant="outline"
            onClick={handleReset}
            className="bg-[#0a0a0a] border-white/10 text-white/90 hover:bg-white/5"
          >
            Reset to Defaults
          </Button>
          <Button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="bg-emerald-500 hover:bg-emerald-600 text-white shadow-lg shadow-emerald-500/20"
          >
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
