"""
Сервіс для відправки WebSocket повідомлень про події турніру.
"""
import asyncio
import logging
from services.websocket_manager import websocket_manager
from db import SessionLocal

logger = logging.getLogger(__name__)


async def notify_tournament_started(tournament_id: int, current_round: int, db=None):
    """Відправити сповіщення про старт турніру"""
    # Створюємо нову сесію якщо не передана
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        # Отримуємо інформацію про турнір
        from models.tournament import Tournament
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        
        message = {
            "type": "tournament_started",
            "tournament_id": tournament_id,
            "tournament_name": tournament.name if tournament else None,
            "current_round": current_round,
            "priority": "high",
            "requires_action": True,
            "sound": "tournament_start",
            "title": "🏆 Tournament Started!",
            "message": f"Tournament '{tournament.name if tournament else 'Unknown'}' has started! Check your round and add the lobby maker as a friend in-game.",
            "action_text": "Add lobby maker as friend",
            "icon": "🏆"
        }
        
        await websocket_manager.broadcast_to_tournament(tournament_id, message, db)
        logger.info(f"Sent tournament_started notification for tournament {tournament_id}")
    finally:
        if should_close:
            db.close()


async def notify_round_started(tournament_id: int, round_number: int, is_final: bool = False, final_round_number: int = None, db=None):
    """Відправити сповіщення про старт раунду"""
    # Створюємо нову сесію якщо не передана
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        if is_final and final_round_number:
            round_name = f"Final {final_round_number}"
            round_display = f"Final {final_round_number}"
            icon = "🏆"
        elif is_final:
            round_name = f"Final {round_number}"
            round_display = f"Final {round_number}"
            icon = "🏆"
        else:
            round_name = f"Round {round_number}"
            round_display = f"Round {round_number}"
            icon = "⚔️"
        
        # Отримуємо інформацію про турнір
        from models.tournament import Tournament
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        
        message = {
            "type": "round_started",
            "tournament_id": tournament_id,
            "tournament_name": tournament.name if tournament else None,
            "round_number": round_number,
            "is_final": is_final,
            "round_name": round_name,
            "priority": "high",
            "requires_action": True,
            "sound": "round_start",
            "title": f"{icon} {round_display} Started!",
            "message": f"{round_display} of tournament '{tournament.name if tournament else 'Unknown'}' has started! Check your game and add the lobby maker as a friend.",
            "action_text": "Add lobby maker as friend",
            "icon": icon
        }
        
        await websocket_manager.broadcast_to_tournament(tournament_id, message, db)
        logger.info(f"Sent round_started notification for tournament {tournament_id}, round {round_number}")
    finally:
        if should_close:
            db.close()


async def notify_finals_started(tournament_id: int, current_round: int, finalists_count: int, db=None):
    """Відправити сповіщення про старт фіналів тільки фіналістам (топ-N гравцям)"""
    # Створюємо нову сесію якщо не передана
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        # Отримуємо інформацію про турнір
        from models.tournament import Tournament
        from models.tournament_participant import TournamentParticipant
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        
        # Отримуємо тільки топ-N гравців (фіналістів)
        top_participants = db.query(TournamentParticipant).filter(
            TournamentParticipant.tournament_id == tournament_id
        ).order_by(TournamentParticipant.total_score.desc()).limit(finalists_count).all()
        
        finalist_user_ids = [p.user_id for p in top_participants]
        
        message = {
            "type": "finals_started",
            "tournament_id": tournament_id,
            "tournament_name": tournament.name if tournament else None,
            "current_round": current_round,
            "finalists_count": finalists_count,
            "priority": "high",
            "requires_action": True,
            "sound": "finals_start",
            "title": "🏆 Finals Started!",
            "message": f"Finals of tournament '{tournament.name if tournament else 'Unknown'}' have started! You are in the top {finalists_count} players. Check your game and add the lobby maker as a friend.",
            "action_text": "Add lobby maker as friend",
            "icon": "🏆"
        }
        
        # Відправляємо тільки фіналістам (якщо вони підключені)
        await websocket_manager.broadcast_to_users(finalist_user_ids, message)
        logger.info(f"Sent finals_started notification to {len(finalist_user_ids)} finalists for tournament {tournament_id}")
    finally:
        if should_close:
            db.close()


async def notify_tournament_finished(tournament_id: int, db=None):
    """Відправити сповіщення про завершення турніру"""
    # Створюємо нову сесію якщо не передана
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        # Отримуємо інформацію про турнір
        from models.tournament import Tournament
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        
        message = {
            "type": "tournament_finished",
            "tournament_id": tournament_id,
            "tournament_name": tournament.name if tournament else None,
            "priority": "medium",
            "requires_action": False,
            "sound": "tournament_finished",
            "title": "✅ Tournament Finished",
            "message": f"Tournament '{tournament.name if tournament else 'Unknown'}' has finished. Check the results!",
            "icon": "✅"
        }
        
        await websocket_manager.broadcast_to_tournament(tournament_id, message, db)
        logger.info(f"Sent tournament_finished notification for tournament {tournament_id}")
    finally:
        if should_close:
            db.close()


# Видалено: notify_game_completed та notify_position_updated
# Тепер відправляємо тільки сповіщення про старт турнірів та раундів


def send_notification_async(tournament_id: int, notification_type: str, **kwargs):
    """
    Асинхронна відправка повідомлення (не блокує основний потік).
    Використовується для неблокуючих сповіщень.
    """
    async def _send():
        try:
            if notification_type == "tournament_started":
                await notify_tournament_started(tournament_id, kwargs.get("current_round", 1))
            elif notification_type == "round_started":
                await notify_round_started(
                    tournament_id, 
                    kwargs.get("round_number", 1),
                    kwargs.get("is_final", False)
                )
            elif notification_type == "finals_started":
                await notify_finals_started(
                    tournament_id,
                    kwargs.get("current_round", 1),
                    kwargs.get("finalists_count", 0)
                )
            elif notification_type == "tournament_finished":
                await notify_tournament_finished(tournament_id)
        except Exception as e:
            logger.error(f"Error sending notification {notification_type} for tournament {tournament_id}: {e}")
    
    # Запускаємо в окремому потоці (не блокує основний запит)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Якщо loop вже запущений, створюємо task
            asyncio.create_task(_send())
        else:
            # Якщо loop не запущений, запускаємо
            loop.run_until_complete(_send())
    except RuntimeError:
        # Якщо немає event loop, створюємо новий
        asyncio.run(_send())

