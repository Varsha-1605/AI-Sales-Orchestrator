from typing import Dict, List

from fastapi import WebSocket
from loguru import logger


# WebSocket connection manager. A session can have several pages open
# (for example the chat and the agent monitor), so each session keeps a list.
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections.setdefault(session_id, []).append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket):
        connections = self.active_connections.get(session_id, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            self.active_connections.pop(session_id, None)

    async def send_agent_update(self, session_id: str, message: dict):
        for connection in list(self.active_connections.get(session_id, [])):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error("Error sending message: {}", e)

    async def broadcast(self, message: dict):
        for session_id in list(self.active_connections):
            await self.send_agent_update(session_id, message)


# One manager shared by the API routes and the WebSocket route
manager = ConnectionManager()
