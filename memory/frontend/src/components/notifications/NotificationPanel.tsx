import { useState, useEffect } from 'react';
import { Bell, X, Check, Info, AlertCircle, Lightbulb, Database } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Card, CardContent } from '../ui/card';
import { formatDistanceToNow } from 'date-fns';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../lib/api';

export interface Notification {
  id: string;
  type: 'suggestion' | 'capture' | 'error' | 'info';
  title: string;
  message: string;
  data: Record<string, any>;
  read: boolean;
  created_at: string;
}

const NotificationIcon = ({ type }: { type: Notification['type'] }) => {
  const icons = {
    suggestion: Lightbulb,
    capture: Database,
    error: AlertCircle,
    info: Info,
  };
  const Icon = icons[type] || Info;
  const colors = {
    suggestion: 'text-yellow-500',
    capture: 'text-blue-500',
    error: 'text-red-500',
    info: 'text-gray-500',
  };
  return <Icon className={`h-5 w-5 ${colors[type]}`} />;
};

export function NotificationPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const queryClient = useQueryClient();

  // Fetch notifications
  const { data: notifications = [] } = useQuery<Notification[]>({
    queryKey: ['notifications'],
    queryFn: async () => {
      const response = await apiClient.get('/notifications');
      return response.data;
    },
    refetchInterval: 30000, // Refetch every 30s
  });

  // Mark as read mutation
  const markRead = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.post(`/notifications/${id}/read`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  // Mark all as read mutation
  const markAllRead = useMutation({
    mutationFn: async () => {
      await apiClient.post('/notifications/mark-all-read');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  // Delete notification mutation
  const deleteNotification = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/notifications/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <div className="relative">
      {/* Bell Button */}
      <Button
        variant="ghost"
        size="icon"
        className="relative"
        onClick={() => setIsOpen(!isOpen)}
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-red-500 text-white text-xs font-bold flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </Button>

      {/* Notification Panel */}
      {isOpen && (
        <div className="fixed inset-0 z-50 md:absolute md:inset-auto md:right-0 md:top-12 md:w-96">
          {/* Mobile overlay */}
          <div
            className="md:hidden fixed inset-0 bg-black/50"
            onClick={() => setIsOpen(false)}
          />

          {/* Panel */}
          <Card className="relative md:absolute md:right-0 m-4 md:m-0 max-h-[80vh] md:max-h-[600px] flex flex-col shadow-xl">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b">
              <div className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                <h3 className="font-semibold">Notifications</h3>
                {unreadCount > 0 && (
                  <Badge variant="destructive">{unreadCount}</Badge>
                )}
              </div>
              <div className="flex gap-2">
                {unreadCount > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => markAllRead.mutate()}
                  >
                    <Check className="h-4 w-4 mr-1" />
                    Mark all read
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsOpen(false)}
                  className="md:hidden"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Notification List */}
            <CardContent className="flex-1 overflow-y-auto p-0">
              {notifications.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <Bell className="h-12 w-12 mx-auto mb-2 opacity-20" />
                  <p>No notifications</p>
                </div>
              ) : (
                <div className="divide-y">
                  {notifications.map((notification) => (
                    <div
                      key={notification.id}
                      className={`p-4 hover:bg-accent/50 transition-colors ${
                        !notification.read ? 'bg-blue-50 dark:bg-blue-950/20' : ''
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <NotificationIcon type={notification.type} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <h4 className="font-medium text-sm">{notification.title}</h4>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6 flex-shrink-0"
                              onClick={() => deleteNotification.mutate(notification.id)}
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">
                            {notification.message}
                          </p>
                          {notification.data && Object.keys(notification.data).length > 0 && (
                            <div className="mt-2 text-xs text-muted-foreground">
                              <details>
                                <summary className="cursor-pointer hover:text-foreground">
                                  View details
                                </summary>
                                <pre className="mt-1 p-2 bg-muted rounded text-xs overflow-x-auto">
                                  {JSON.stringify(notification.data, null, 2)}
                                </pre>
                              </details>
                            </div>
                          )}
                          <div className="flex items-center justify-between mt-2">
                            <span className="text-xs text-muted-foreground">
                              {formatDistanceToNow(new Date(notification.created_at), {
                                addSuffix: true,
                              })}
                            </span>
                            {!notification.read && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 text-xs"
                                onClick={() => markRead.mutate(notification.id)}
                              >
                                Mark read
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
