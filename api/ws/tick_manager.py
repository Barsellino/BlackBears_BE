import asyncio
import time

from api.ws.manager import manager
from api.crud.session import get_all_sessions
from services.game_state import GameStateService
from db import SessionLocal

# Глобальний лічильник тіків
GLOBAL_TICK_COUNTER = 0


class TickManager:
    def __init__(self):
        self.running = False

    async def start(self):
        """Tick manager disabled"""
        print("⏳ TickManager DISABLED")
        return
            
    def stop(self):
        """Зупиняє тікер"""
        self.running = False
        print("⏹️ TickManager STOPPED")

    async def tick_all_sessions(self):
        tick_id = int(time.time() * 1000) % 10000
        print(f"🔥 TICK #{tick_id} START")
        
        db = SessionLocal()
        try:
            sessions = get_all_sessions(db)
            for session in sessions:
                db.refresh(session)
                state = session.state
                if state and state.get("running"):
                    print(f"🔥 TICK #{tick_id} session {session.id}")
                    # Оновлюємо сесію ще раз перед створенням GameStateService
                    db.refresh(session)
                    service = GameStateService(db, session)
                    new_state = service.tick_once()
                    await manager.broadcast_state(session.id, new_state)
        except Exception as e:
            print("Tick ERROR:", e)
            if "SSL connection has been closed" in str(e):
                print("🚫 Database connection lost, stopping tick manager")
                self.running = False
        finally:
            try:
                db.close()
            except:
                pass
            print(f"🔥 TICK #{tick_id} END")


tick_manager = TickManager()