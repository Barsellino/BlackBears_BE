from fastapi import APIRouter, WebSocket, Depends
from sqlalchemy.orm import Session
import asyncio

from api.deps.db import get_db
from api.crud.session import get_session
from api.ws.manager import manager
from services.game_state import GameStateService
from services.topics_service import TopicsService    # <- ДОДАНИЙ ІМПОРТ

router = APIRouter(prefix="/ws")


@router.websocket("/host/{session_id}")
async def ws_host(websocket: WebSocket, session_id: str, db: Session = Depends(get_db)):

    # перевіряємо, що сесія існує
    session = get_session(db, session_id)
    if not session:
        await websocket.close(code=4001)
        return

    await manager.connect_host(session_id, websocket)

    # початковий стан при підключенні
    state_service = GameStateService(db, session)
    await manager.broadcast_state(session_id, state_service.state)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") != "command":
                continue

            cmd = data.get("command")
            payload = data.get("payload", {})

            # ⬇️ ГОЛОВНЕ ВИПРАВЛЕННЯ: беремо АКТУАЛЬНУ сесію з БД
            session = get_session(db, session_id)
            if not session:
                await websocket.close(code=4002)
                return

            state_service = GameStateService(db, session)

            if cmd == "set_topic":
                topic_id = payload.get("topic_id")
                topic = TopicsService.get_by_id(topic_id)
                if topic:
                    new_state = state_service.set_topic(topic)
                else:
                    new_state = state_service.state

            elif cmd == "start_turn":
                new_state = state_service.start_turn(payload.get("player"))

            elif cmd == "pause_all":
                new_state = state_service.pause_all()

            elif cmd == "correct":
                new_state = state_service.correct()

            elif cmd == "pass_or_wrong":
                new_state = state_service.pass_or_wrong()

            elif cmd == "reset_times":
                new_state = state_service.reset_times()

            elif cmd == "next_image":
                idx = state_service._next_image_index()
                new_state = state_service._patch(imageIndex=idx)

            else:
                new_state = state_service.state

            await manager.broadcast_state(session_id, new_state)

    except Exception as e:
        print("WS host error:", e)
    finally:
        await manager.disconnect(session_id, websocket)

@router.websocket("/display/{session_id}")
async def ws_display(websocket: WebSocket, session_id: str, db: Session = Depends(get_db)):

    session = get_session(db, session_id)
    if not session:
        await websocket.close(code=4001)
        return

    await manager.connect_display(session_id, websocket)

    try:
        while True:
            await asyncio.sleep(3600)
    except:
        await manager.disconnect(session_id, websocket)