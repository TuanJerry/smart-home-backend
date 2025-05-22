from typing import Dict, List
from fastapi import WebSocket

class ConnectionManage:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print("WebSocket disconnected: Client Side")
        else: 
            ConnectionError("WebSocket not found")

    async def broadcast(self, message: Dict):
        for connection in self.active_connections:
            await connection.send_json(message)

    async def waiting(self, websocket: WebSocket):
        if websocket in self.active_connections:
            await websocket.send_json({
                "event": "Waiting",
                "message": "Nothing changed"
            })
        else: 
            ConnectionError("WebSocket not found")

manager = ConnectionManage()