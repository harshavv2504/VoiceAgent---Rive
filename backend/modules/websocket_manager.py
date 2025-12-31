"""
WebSocket Connection Manager
Handles WebSocket connections and message broadcasting
"""
from fastapi import WebSocket
import logging
import json
import time
from typing import Dict, Any

# Configure logger for this module
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""
    
    def __init__(self):
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[websocket] = {"connected_at": time.time()}
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection from active connections"""
        if websocket in self.active_connections:
            del self.active_connections[websocket]
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_json(self, data: dict, websocket: WebSocket):
        """Send JSON data to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(data))
        except Exception as e:
            logger.error(f"Error sending JSON: {e}")

    async def broadcast_json(self, data: dict):
        """Broadcast JSON data to all active connections"""
        for websocket in list(self.active_connections.keys()):
            await self.send_json(data, websocket)
