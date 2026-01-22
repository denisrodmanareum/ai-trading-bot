"""
WebSocket Connection Manager
"""
from typing import List, Dict
from fastapi import WebSocket
from loguru import logger
import json


class WebSocketManager:
    """Manages WebSocket connections and broadcasts"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {
            "prices": [],
            "trades": [],
            "ai": []
        }
    
    async def connect(self, websocket: WebSocket, channel: str = "prices"):
        """Accept and store new WebSocket connection"""
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)
        logger.info(f"New WebSocket connection on channel: {channel}")
    
    def disconnect(self, websocket: WebSocket, channel: str = "prices"):
        """Remove WebSocket connection"""
        if channel in self.active_connections:
            if websocket in self.active_connections[channel]:
                self.active_connections[channel].remove(websocket)
                logger.info(f"WebSocket disconnected from channel: {channel}")
    
    async def broadcast(self, message: dict, channel: str = "prices"):
        """Broadcast message to all connections on channel"""
        if channel not in self.active_connections:
            return
        
        message_str = json.dumps(message)
        dead_connections = []
        
        for connection in self.active_connections[channel]:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                dead_connections.append(connection)
        
        # Remove dead connections
        for conn in dead_connections:
            self.disconnect(conn, channel)
    
    async def send_personal(self, message: dict, websocket: WebSocket):
        """Send message to specific connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
    
    def get_connection_count(self, channel: str = None) -> int:
        """Get number of active connections"""
        if channel:
            return len(self.active_connections.get(channel, []))
        return sum(len(conns) for conns in self.active_connections.values())
