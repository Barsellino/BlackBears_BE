from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from core.auth import verify_token
from models.user import User
from models.tournament import Tournament
from models.tournament_participant import TournamentParticipant
from services.websocket_manager import websocket_manager
from db import SessionLocal
from fastapi import HTTPException, status
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


async def send_error(websocket: WebSocket, error_type: str, message: str, code: int = 1008):
    """Відправити повідомлення про помилку перед закриттям"""
    try:
        await websocket.send_json({
            "type": "error",
            "error_type": error_type,
            "message": message,
            "code": code,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    except:
        pass  # Якщо не вдалося відправити, просто закриваємо
    finally:
        await websocket.close(code=code, reason=message)


@router.websocket("/ws")
async def universal_websocket(
    websocket: WebSocket,
    token: str = Query(None)
):
    """
    Універсальний WebSocket endpoint для підключення користувача.
    Один підключення = сповіщення про всі турніри користувача.
    
    Використання:
    - Підключення: ws://host/ws?token=JWT_TOKEN
    - Автоматично отримує сповіщення про події всіх турнірів, де користувач є учасником
    
    Формат помилок:
    {
        "type": "error",
        "error_type": "authentication_error" | "authorization_error" | "not_found" | "validation_error",
        "message": "Error description",
        "code": 1008,
        "timestamp": "2025-01-01T12:00:00Z"
    }
    """
    
    # Перевірка токену
    if not token:
        await send_error(websocket, "authentication_error", "Token required")
        return
    
    # Створюємо сесію БД
    db = SessionLocal()
    user = None
    
    try:
        # Верифікуємо токен
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
        token_data = verify_token(token, credentials_exception)
        
        # Отримуємо користувача
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user:
            await send_error(websocket, "authentication_error", "User not found")
            return
        
        if not user.is_active:
            await send_error(websocket, "authorization_error", "User account is inactive")
            return
        
        # Отримуємо список турнірів користувача
        user_tournaments = db.query(Tournament).join(
            TournamentParticipant,
            Tournament.id == TournamentParticipant.tournament_id
        ).filter(
            TournamentParticipant.user_id == user.id,
            Tournament.is_deleted == False
        ).all()
        
    except HTTPException as e:
        await send_error(websocket, "authentication_error", str(e.detail))
        return
    except Exception as e:
        logger.error(f"WebSocket auth error: {e}")
        await send_error(websocket, "authentication_error", "Authentication failed")
        return
    finally:
        db.close()
    
    # Підключаємо користувача (універсальне підключення)
    await websocket_manager.connect(websocket, user.id)
    
    try:
        # Відправляємо привітальне повідомлення
        await websocket.send_json({
            "type": "connected",
            "user_id": user.id,
            "user_battletag": user.battletag,
            "tournaments_count": len(user_tournaments),
            "tournaments": [
                {
                    "id": t.id,
                    "name": t.name,
                    "status": t.status.value if hasattr(t.status, 'value') else str(t.status),
                    "current_round": t.current_round,
                    "total_rounds": t.total_rounds
                }
                for t in user_tournaments
            ],
            "message": "Connected successfully. You will receive notifications for all your tournaments.",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "heartbeat_interval": 30  # секунди для ping
        })
        
        # Heartbeat task для автоматичного перепідключення
        last_ping = datetime.utcnow()
        heartbeat_timeout = 60  # секунди
        
        # Очікуємо повідомлень від клієнта
        while True:
            try:
                # Очікуємо повідомлення з таймаутом для перевірки heartbeat
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                    
                    # Обробка ping/pong
                    if data == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        })
                        last_ping = datetime.utcnow()
                    elif data.startswith("{"):
                        # JSON команди (можна розширити)
                        import json
                        try:
                            command = json.loads(data)
                            if command.get("type") == "ping":
                                await websocket.send_json({
                                    "type": "pong",
                                    "timestamp": datetime.utcnow().isoformat() + "Z"
                                })
                                last_ping = datetime.utcnow()
                        except:
                            pass
                except asyncio.TimeoutError:
                    # Перевірка heartbeat
                    if (datetime.utcnow() - last_ping).total_seconds() > heartbeat_timeout:
                        logger.warning(f"Heartbeat timeout for user {user.id}")
                        break
                    # Відправляємо автоматичний ping
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"User {user.id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for user {user.id}: {e}")
    finally:
        await websocket_manager.disconnect(websocket)

