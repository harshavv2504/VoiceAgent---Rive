import { useState, useCallback, useRef, useEffect } from 'react';
import { WebSocketState } from '../types';

// Connect to backend server from environment variable or use same origin
const getWebSocketUrl = () => {
  // In production (when served from same origin), use relative WebSocket URL
  if (import.meta.env.PROD) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/ws`;
  }
  // In development, use environment variable or default
  return import.meta.env.VITE_WEBSOCKET_URL || 'ws://localhost:8000/ws';
};

const WEBSOCKET_URL = getWebSocketUrl();

interface UseWebSocketProps {
  onMessage: (data: any) => void;
}

export const useWebSocket = ({ onMessage }: UseWebSocketProps) => {
  const [connectionState, setConnectionState] = useState<WebSocketState>(WebSocketState.CLOSED);
  const webSocketRef = useRef<WebSocket | null>(null);
  // Ref to track if the connection closed due to an error, preventing race conditions.
  const errorOccurredRef = useRef(false);

  const connect = useCallback(() => {
    // Prevent multiple connections
    if (webSocketRef.current && webSocketRef.current.readyState < 2) return;

    errorOccurredRef.current = false; // Reset error flag on new connection attempt
    setConnectionState(WebSocketState.CONNECTING);
    console.log('Attempting to connect to:', WEBSOCKET_URL);
    const ws = new WebSocket(WEBSOCKET_URL);
    webSocketRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnectionState(WebSocketState.OPEN);
      // Don't auto-start voice agent - let user control it manually
    };

    ws.onmessage = (event) => {
      console.log('Raw WebSocket message received:', event.data);
      // Parse JSON message and call the provided callback with parsed data
      try {
        const data = JSON.parse(event.data);
        console.log('Parsed WebSocket message:', data);
        onMessage(data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
        // Fallback to raw data if parsing fails
        onMessage(event.data);
      }
    };

    ws.onerror = (error) => {
      // Provide a more helpful error message instead of logging the event object.
      console.error('WebSocket connection failed. Please check the URL and your network connection.');
      console.error('Error details:', error);
      console.error('Make sure the backend is running on port 8000');
      errorOccurredRef.current = true;
      setConnectionState(WebSocketState.ERROR);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      webSocketRef.current = null;
      // Only transition to CLOSED if an error didn't happen right before.
      // This ensures the UI can show a "Try Again" state.
      if (!errorOccurredRef.current) {
        setConnectionState(WebSocketState.CLOSED);
      }
    };
  }, [onMessage]);

  const disconnect = useCallback(() => {
    if (webSocketRef.current) {
      setConnectionState(WebSocketState.CLOSING);
      // Send stop_voice_agent message before closing
      webSocketRef.current.send(JSON.stringify({
        type: 'stop_voice_agent'
      }));
      webSocketRef.current.close();
    }
  }, []);
  
  const toggleConnection = useCallback(() => {
    if (connectionState === WebSocketState.OPEN) {
      disconnect();
    } else if (connectionState === WebSocketState.CLOSED || connectionState === WebSocketState.ERROR) {
      connect();
    }
  }, [connectionState, connect, disconnect]);

  // Expose the send function for sending JSON messages
  const sendMessage = useCallback((message: any) => {
    if (webSocketRef.current && webSocketRef.current.readyState === WebSocket.OPEN) {
        webSocketRef.current.send(JSON.stringify(message));
    } else {
        console.warn('WebSocket is not open. Cannot send message.');
    }
  }, []);


  // Auto-connect on mount
  useEffect(() => {
    connect();
  }, [connect]);

  return { connectionState, toggleConnection, sendMessage, connect };
};
