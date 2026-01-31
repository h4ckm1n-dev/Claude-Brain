import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { Badge } from './ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Activity, AlertCircle, CheckCircle, XCircle, Wifi } from 'lucide-react';

interface HealthInfo {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  uptime_seconds: number;
  dependencies: {
    [key: string]: {
      status: string;
      message: string;
      details: any;
    };
  };
  features: {
    [key: string]: boolean;
  };
  performance: {
    health_check_ms: number;
    active_websocket_connections: number;
    cache?: any;
  };
}

export function HealthStatus() {
  const { data: health, isLoading, error } = useQuery<HealthInfo>({
    queryKey: ['health', 'detailed'],
    queryFn: () => apiClient.get('/health/detailed').then(r => r.data),
    refetchInterval: 10000, // Refetch every 10 seconds
    retry: 3,
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Activity className="h-4 w-4 animate-pulse" />
        <span className="text-sm">Checking health...</span>
      </div>
    );
  }

  if (error || !health) {
    return (
      <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
        <XCircle className="h-4 w-4" />
        <span className="text-sm">Service Unavailable</span>
      </div>
    );
  }

  const isHealthy = health.status === 'healthy';
  const isDegraded = health.status === 'degraded';

  return (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full ${
        isHealthy ? 'bg-green-500' : isDegraded ? 'bg-yellow-500' : 'bg-red-500'
      } ${isHealthy ? 'animate-pulse' : ''}`} />
      <span className={`text-sm ${
        isHealthy ? 'text-green-600 dark:text-green-400' :
        isDegraded ? 'text-yellow-600 dark:text-yellow-400' :
        'text-red-600 dark:text-red-400'
      }`}>
        {isHealthy ? 'All Systems Operational' : isDegraded ? 'Service Degraded' : 'Service Unhealthy'}
      </span>
    </div>
  );
}

export function HealthDashboard() {
  const { data: health, isLoading, error } = useQuery<HealthInfo>({
    queryKey: ['health', 'detailed'],
    queryFn: () => apiClient.get('/health/detailed').then(r => r.data),
    refetchInterval: 10000,
    retry: 3,
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-8">
          <div className="flex items-center justify-center">
            <Activity className="h-8 w-8 animate-pulse text-blue-600" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !health) {
    return (
      <Card className="border-red-200 dark:border-red-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-red-600 dark:text-red-400">
            <XCircle className="h-5 w-5" />
            System Health Unavailable
          </CardTitle>
          <CardDescription>Could not connect to the memory service</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'degraded':
      case 'unhealthy':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      case 'disabled':
        return <XCircle className="h-4 w-4 text-gray-400" />;
      default:
        return <Activity className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
      healthy: 'default',
      degraded: 'secondary',
      unhealthy: 'destructive',
      disabled: 'outline',
    };

    return (
      <Badge variant={variants[status] || 'outline'}>
        {status}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      {/* Overall Status */}
      <Card className={
        health.status === 'healthy' ? 'border-green-200 dark:border-green-800' :
        health.status === 'degraded' ? 'border-yellow-200 dark:border-yellow-800' :
        'border-red-200 dark:border-red-800'
      }>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              {health.status === 'healthy' ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : health.status === 'degraded' ? (
                <AlertCircle className="h-5 w-5 text-yellow-600" />
              ) : (
                <XCircle className="h-5 w-5 text-red-600" />
              )}
              System Health
            </CardTitle>
            {getStatusBadge(health.status)}
          </div>
          <CardDescription>
            Last checked: {new Date(health.timestamp).toLocaleString()}
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Dependencies */}
      <Card>
        <CardHeader>
          <CardTitle>Dependencies</CardTitle>
          <CardDescription>External service health</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {Object.entries(health.dependencies).map(([name, dep]) => (
              <div key={name} className="flex items-center justify-between p-3 rounded-lg border">
                <div className="flex items-center gap-3">
                  {getStatusIcon(dep.status)}
                  <div>
                    <p className="font-medium capitalize">{name}</p>
                    <p className="text-sm text-muted-foreground">{dep.message}</p>
                  </div>
                </div>
                {getStatusBadge(dep.status)}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Features */}
      <Card>
        <CardHeader>
          <CardTitle>Feature Flags</CardTitle>
          <CardDescription>Enabled system features</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(health.features).map(([feature, enabled]) => (
              <div key={feature} className="flex items-center gap-2 p-2 rounded border">
                {enabled ? (
                  <CheckCircle className="h-4 w-4 text-green-600" />
                ) : (
                  <XCircle className="h-4 w-4 text-gray-400" />
                )}
                <span className="text-sm capitalize">
                  {feature.replace(/_/g, ' ')}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Performance Metrics</CardTitle>
          <CardDescription>System performance indicators</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-3 rounded border">
              <p className="text-sm text-muted-foreground">Health Check Response</p>
              <p className="text-2xl font-bold">
                {health.performance.health_check_ms.toFixed(2)} ms
              </p>
            </div>

            <div className="p-3 rounded border">
              <div className="flex items-center gap-2">
                <Wifi className="h-4 w-4 text-blue-600" />
                <p className="text-sm text-muted-foreground">WebSocket Connections</p>
              </div>
              <p className="text-2xl font-bold">
                {health.performance.active_websocket_connections}
              </p>
            </div>

            {health.performance.cache && (
              <>
                <div className="p-3 rounded border">
                  <p className="text-sm text-muted-foreground">Cache Entries</p>
                  <p className="text-2xl font-bold">
                    {health.performance.cache.total_entries || 0}
                  </p>
                </div>

                <div className="p-3 rounded border">
                  <p className="text-sm text-muted-foreground">Cache Hit Rate</p>
                  <p className="text-2xl font-bold">
                    {health.performance.cache.hit_rate
                      ? `${(health.performance.cache.hit_rate * 100).toFixed(1)}%`
                      : 'N/A'
                    }
                  </p>
                </div>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
