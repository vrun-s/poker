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
    
    async def broadcast(self, game_id: str, data):
        connections = self.active_connections.get(game_id, [])
        remove_list = []
    
        is_game_object = hasattr(data, "get_game_state")
    
        print(f"[BCAST] game_id={game_id} is_game_object={is_game_object} connections={len(connections)}")
    
        for ws in connections:
            try:
                player_name = getattr(ws, "player_name", None)
                if is_game_object:
                    message = {
                        "type": "state_update",
                        "state": data.get_game_state(viewer_name=player_name)
                    }
                else:
                    # show a small debug marker when broadcasting raw dicts
                    message = data
                    # Optionally print what was passed
                    # print(f"[BCAST-RAW] to {player_name}: {message.keys() if isinstance(message, dict) else type(message)}")
    
                await ws.send_json(message)
                print(f"[BCAST SENT] to={player_name} type={message.get('type')}")
            except Exception as e:
                print(f"[WS ERROR] Removing closed connection for game {game_id}: {e}")
                remove_list.append(ws)
    
        for ws in remove_list:
            self.disconnect(game_id, ws)
            print(f"[WS DISCONNECT] removed socket for game {game_id}")

