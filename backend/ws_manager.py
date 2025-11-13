# ws_manager.py
from fastapi import WebSocket
from typing import Dict, List
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, game_id: str, websocket: WebSocket):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []
        self.active_connections[game_id].append(websocket)

    def disconnect(self, game_id: str, websocket: WebSocket):
        if game_id in self.active_connections:
            if websocket in self.active_connections[game_id]:
                self.active_connections[game_id].remove(websocket)

    async def broadcast(self, game_id: str, data: dict):
        """Send JSON to all connected clients for this game"""
        connections = self.active_connections.get(game_id, [])
        remove_list = []

        for ws in connections:
            try:
                await ws.send_json(data)
            except:
                remove_list.append(ws)

        # Remove closed connections
        for ws in remove_list:
            self.disconnect(game_id, ws)
