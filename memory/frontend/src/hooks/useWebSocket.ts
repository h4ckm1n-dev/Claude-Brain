import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';

interface WebSocketMessage {
  type:
    | 'memory_created'
    | 'memory_updated'
    | 'memory_deleted'
    | 'job_started'
    | 'job_completed'
    | 'job_failed'
    | 'process_status_changed'
    | 'pong';
  data?: any;
}

/**
 * WebSocket hook for real-time memory updates.
 *
 * Automatically connects to the WebSocket server and invalidates
 * React Query caches when memories are created, updated, or deleted.
 *
 * Usage: Call once in your root App component:
 * ```tsx
 * function App() {
 *   useWebSocket();
 *   return <YourApp />;
 * }
 * ```
 */
export function useWebSocket(url?: string) {
  const wsUrl = url || (() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/ws`;
  })();
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);

  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('[WebSocket] Connected to memory service');
          reconnectAttemptsRef.current = 0;

          // Send periodic pings to keep connection alive
          const pingInterval = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: 'ping' }));
            }
          }, 30000); // Every 30 seconds

          // Store interval ID to clear on close
          (ws as any).pingInterval = pingInterval;
        };

        ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);

            if (message.type === 'pong') {
              // Heartbeat response, ignore
              return;
            }

            console.log('[WebSocket] Received message:', message.type);

            // Invalidate relevant queries based on message type
            switch (message.type) {
              case 'memory_created':
              case 'memory_updated':
              case 'memory_deleted':
                // Invalidate all memory-related queries
                queryClient.invalidateQueries({ queryKey: ['memories'] });
                queryClient.invalidateQueries({ queryKey: ['stats'] });
                queryClient.invalidateQueries({ queryKey: ['graphStats'] });

                // Show a subtle notification (optional)
                console.log(`[WebSocket] Memory ${message.type.replace('memory_', '')}`);
                break;

              case 'job_started':
              case 'job_completed':
              case 'job_failed':
                // Invalidate job queries
                queryClient.invalidateQueries({ queryKey: ['jobs'] });
                if (message.data?.job_id) {
                  queryClient.invalidateQueries({ queryKey: ['jobs', message.data.job_id] });
                }
                console.log(`[WebSocket] Job ${message.type.replace('job_', '')}`);
                break;

              case 'process_status_changed':
                // Invalidate process and scheduler queries
                queryClient.invalidateQueries({ queryKey: ['processes'] });
                queryClient.invalidateQueries({ queryKey: ['scheduler'] });
                console.log('[WebSocket] Process status changed:', message.data);
                break;

              default:
                console.warn('[WebSocket] Unknown message type:', message.type);
            }
          } catch (error) {
            console.error('[WebSocket] Failed to parse message:', error);
          }
        };

        ws.onerror = (error) => {
          console.error('[WebSocket] Error:', error);
        };

        ws.onclose = () => {
          console.log('[WebSocket] Connection closed');

          // Clear ping interval
          if ((ws as any).pingInterval) {
            clearInterval((ws as any).pingInterval);
          }

          // Attempt to reconnect with exponential backoff
          const maxAttempts = 10;
          const baseDelay = 1000; // 1 second
          const maxDelay = 30000; // 30 seconds

          if (reconnectAttemptsRef.current < maxAttempts) {
            const delay = Math.min(
              baseDelay * Math.pow(2, reconnectAttemptsRef.current),
              maxDelay
            );

            console.log(
              `[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxAttempts})`
            );

            reconnectTimeoutRef.current = setTimeout(() => {
              reconnectAttemptsRef.current += 1;
              connect();
            }, delay);
          } else {
            console.error('[WebSocket] Max reconnection attempts reached');
          }
        };
      } catch (error) {
        console.error('[WebSocket] Failed to create connection:', error);
      }
    };

    connect();

    // Cleanup on unmount
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }

      if (wsRef.current) {
        // Clear ping interval
        if ((wsRef.current as any).pingInterval) {
          clearInterval((wsRef.current as any).pingInterval);
        }

        // Close connection
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [wsUrl, queryClient]);
}
