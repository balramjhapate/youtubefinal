import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * Custom hook for WebSocket connection to get real-time video processing updates
 * 
 * @param {string} videoId - Video ID to subscribe to updates
 * @param {function} onUpdate - Callback function when update is received
 * @param {object} options - Options for WebSocket connection
 * @returns {object} - WebSocket connection state and methods
 */
export function useWebSocket(videoId, onUpdate, options = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = options.maxReconnectAttempts || 10;
  const reconnectDelay = options.reconnectDelay || 3000;
  const pingInterval = options.pingInterval || 30000; // 30 seconds
  const pingTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    if (!videoId) return;

    // Determine WebSocket URL
    // In development, Vite runs on port 5173, but WebSocket should connect to Django on port 8000
    const isDev = import.meta.env.DEV;
    let wsUrl;
    
    if (isDev) {
      // Development: Connect directly to Django backend
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${protocol}//localhost:8000/ws/video/${videoId}/`;
    } else {
      // Production: Use same host as current page
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      wsUrl = `${protocol}//${host}/ws/video/${videoId}/`;
    }

    try {
      console.log(`[WebSocket] Connecting to ${wsUrl}`);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log(`[WebSocket] Connected for video ${videoId}`);
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;

        // Start ping interval
        if (pingTimeoutRef.current) {
          clearInterval(pingTimeoutRef.current);
        }
        pingTimeoutRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, pingInterval);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'pong') {
            // Pong response, connection is alive
            return;
          }
          
          if (data.type === 'video_update' && data.data) {
            console.log(`[WebSocket] Received update for video ${videoId}`, data.data);
            setLastUpdate(data);
            if (onUpdate) {
              onUpdate(data.data);
            }
          }
        } catch (err) {
          console.error('[WebSocket] Error parsing message:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        setError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log(`[WebSocket] Disconnected for video ${videoId}`, event.code, event.reason);
        setIsConnected(false);
        
        // Clear ping interval
        if (pingTimeoutRef.current) {
          clearInterval(pingTimeoutRef.current);
          pingTimeoutRef.current = null;
        }

        // Attempt to reconnect if not a normal closure
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current += 1;
          const delay = reconnectDelay * Math.min(reconnectAttempts.current, 5); // Exponential backoff, max 5x
          console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current}/${maxReconnectAttempts})...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setError('WebSocket connection failed after maximum retry attempts');
        }
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('[WebSocket] Connection error:', err);
      setError(err.message);
    }
  }, [videoId, onUpdate, pingInterval, maxReconnectAttempts, reconnectDelay]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (pingTimeoutRef.current) {
      clearInterval(pingTimeoutRef.current);
      pingTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnecting');
      wsRef.current = null;
    }
    
    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  const requestStatus = useCallback(() => {
    sendMessage({ type: 'get_status' });
  }, [sendMessage]);

  useEffect(() => {
    if (videoId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [videoId, connect, disconnect]);

  return {
    isConnected,
    lastUpdate,
    error,
    sendMessage,
    requestStatus,
    reconnect: connect,
  };
}

