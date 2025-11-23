from typing import Dict, List
from fastapi import WebSocket


class SessionConnectionManager:
    def __init__(self):
        # один хост на сесію
        self.host_connections: Dict[str, WebSocket] = {}

        # багато дисплеїв на сесію
        self.display_connections: Dict[str, List[WebSocket]] = {}

    # -------- HOST --------
    async def connect_host(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.host_connections[session_id] = websocket

    # -------- DISPLAY --------
    async def connect_display(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.display_connections:
            self.display_connections[session_id] = []
        self.display_connections[session_id].append(websocket)

    # -------- DISCONNECT --------
    async def disconnect(self, session_id: str, websocket: WebSocket):
        # видаляємо з display
        if session_id in self.display_connections:
            if websocket in self.display_connections[session_id]:
                self.display_connections[session_id].remove(websocket)

        # видаляємо з host
        if session_id in self.host_connections:
            if self.host_connections[session_id] == websocket:
                del self.host_connections[session_id]

    # -------- BROADCAST STATE --------
    async def broadcast_state(self, session_id: str, state: dict):
        message = {
            "type": "state",
            "session_id": session_id,
            "state": state
        }

        # розсилаємо всім дисплеям
        if session_id in self.display_connections:
            for ws in list(self.display_connections[session_id]):
                try:
                    await ws.send_json(message)
                except:
                    # автоматично чистимо мертві конекшени
                    await self.disconnect(session_id, ws)

        # відправляємо хосту (опційно, але потрібно)
        if session_id in self.host_connections:
            ws = self.host_connections[session_id]
            try:
                await ws.send_json(message)
            except:
                await self.disconnect(session_id, ws)


# Глобальний інстанс (важливо!)
manager = SessionConnectionManager()
