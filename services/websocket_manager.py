from typing import Dict, List, Set
from fastapi import WebSocket
from collections import defaultdict
import json
import logging

logger = logging.getLogger(__name__)


class TournamentWebSocketManager:
    """
    Менеджер WebSocket підключень для турнірів.
    Універсальне підключення: один WebSocket на користувача, отримує сповіщення про всі турніри.
    """
    
    def __init__(self):
        # Структура: {user_id: [websocket1, websocket2, ...]}
        # Один користувач може мати кілька підключень (різні вкладки/пристрої)
        self.user_connections: Dict[int, List[WebSocket]] = defaultdict(list)
        # Зберігаємо user_id для кожного websocket для швидкого пошуку
        self.websocket_to_user: Dict[WebSocket, int] = {}  # {websocket: user_id}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Підключити користувача (універсальне підключення)"""
        await websocket.accept()
        self.user_connections[user_id].append(websocket)
        self.websocket_to_user[websocket] = user_id
        logger.info(f"User {user_id} connected (universal connection)")
    
    async def disconnect(self, websocket: WebSocket):
        """Відключити користувача"""
        if websocket not in self.websocket_to_user:
            return
        
        user_id = self.websocket_to_user[websocket]
        
        # Видаляємо websocket зі списку
        if user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            
            # Якщо у користувача більше немає підключень, видаляємо його
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Видаляємо з мапи
        del self.websocket_to_user[websocket]
        logger.info(f"User {user_id} disconnected")
    
    async def send_to_user(self, user_id: int, message: dict):
        """Відправити повідомлення конкретному користувачу"""
        if user_id not in self.user_connections:
            return
        
        disconnected = []
        for ws in list(self.user_connections[user_id]):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message to user {user_id}: {e}")
                disconnected.append(ws)
        
        # Очищаємо мертві підключення
        for ws in disconnected:
            await self.disconnect(ws)
    
    async def broadcast_to_users(self, user_ids: List[int], message: dict):
        """Відправити повідомлення групі користувачів"""
        for user_id in user_ids:
            await self.send_to_user(user_id, message)
    
    async def broadcast_to_tournament(self, tournament_id: int, message: dict, db=None):
        """
        Відправити повідомлення всім учасникам турніру.
        Отримує список учасників з БД та відправляє їм повідомлення.
        """
        if db is None:
            logger.warning("Database session required for broadcast_to_tournament")
            return
        
        # Отримуємо всіх учасників турніру
        from models.tournament_participant import TournamentParticipant
        participants = db.query(TournamentParticipant).filter(
            TournamentParticipant.tournament_id == tournament_id
        ).all()
        
        user_ids = [p.user_id for p in participants]
        await self.broadcast_to_users(user_ids, message)
    
    def get_connected_users(self) -> Set[int]:
        """Отримати список всіх підключених користувачів"""
        return set(self.user_connections.keys())
    
    def get_connection_count(self, user_id: int = None) -> int:
        """Отримати кількість підключень (всього або для конкретного користувача)"""
        if user_id:
            return len(self.user_connections.get(user_id, []))
        total = 0
        for websockets in self.user_connections.values():
            total += len(websockets)
        return total


# Глобальний інстанс менеджера
websocket_manager = TournamentWebSocketManager()

