"""
Сервіс для відправки WebSocket повідомлень про події турніру.
"""
import asyncio
import logging
from datetime import datetime
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


async def notify_next_round_created(
    tournament_id: int,
    round_number: int,
    is_final: bool = False,
    final_round_number: int = None,
    db=None
):
    """Відправити сповіщення про створення нового раунду (з force_reload для перезавантаження табу)"""
    logger.info(f"[NOTIFY] Starting next_round_created for tournament {tournament_id}, round {round_number}, is_final={is_final}")
    
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
            "type": "next_round_created",
            "tournament_id": tournament_id,
            "tournament_name": tournament.name if tournament else None,
            "round_number": round_number,
            "is_final": is_final,
            "round_name": round_name,
            "force_reload": True,  # Змусити фронтенд перезавантажити таб
            "show_notification": False,  # За замовчуванням false - фронтенд сам вирішить, чи показувати пушап
            "priority": "high",
            "requires_action": True,
            "sound": "round_start",
            "title": f"{icon} {round_display} Created!",
            "message": f"{round_display} of tournament '{tournament.name if tournament else 'Unknown'}' has been created. The page will reload to show the new round.",
            "action_text": "Add lobby maker as friend",
            "icon": icon,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        logger.info(f"[NOTIFY] Message prepared: type={message['type']}, tournament_id={message['tournament_id']}, round_number={message['round_number']}, force_reload={message['force_reload']}, show_notification={message['show_notification']}")
        
        # Відправляємо всім підключеним (для оновлення UI)
        # Фронтенд сам вирішить, чи показувати пушап, перевіривши чи користувач є учасником
        await websocket_manager.broadcast_to_all(message)
        
        logger.info(f"[NOTIFY] Sent next_round_created notification to all connected users for tournament {tournament_id}, round {round_number}")
    finally:
        if should_close:
            db.close()


async def notify_tournament_finished(tournament_id: int, db=None):
    """Відправити сповіщення про завершення турніру (з force_reload для перезавантаження табу)"""
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
            "force_reload": True,  # Змусити фронтенд перезавантажити таб
            "priority": "high",  # Змінено з "medium" на "high"
            "requires_action": False,
            "sound": "tournament_finished",
            "title": "✅ Tournament Finished",
            "message": f"Tournament '{tournament.name if tournament else 'Unknown'}' has finished. The page will reload to show the final results.",
            "icon": "✅",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        await websocket_manager.broadcast_to_tournament(tournament_id, message, db)
        logger.info(f"Sent tournament_finished notification for tournament {tournament_id}")
    finally:
        if should_close:
            db.close()


async def notify_game_result_updated(
    tournament_id: int,
    game_id: int,
    round_number: int,
    is_final: bool,
    game_participant_id: int,
    participant_id: int,
    user_id: int,
    battletag: str,
    positions: list = None,
    calculated_points: float = None,
    is_lobby_maker: bool = False,
    game_status: str = "active",
    db=None
):
    """Відправити сповіщення про оновлення результату гри"""
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        from datetime import datetime
        message = {
            "type": "game_result_updated",
            "tournament_id": tournament_id,
            "game_id": game_id,
            "round_number": round_number,
            "is_final": is_final,
            "updated_participant": {
                "id": game_participant_id,  # ID з game_participants
                "participant_id": participant_id,  # ID з tournament_participants
                "user_id": user_id,
                "battletag": battletag,
                "position": positions,  # Масив позицій або null
                "calculated_points": calculated_points,
                "is_lobby_maker": is_lobby_maker
            },
            "game_status": game_status,  # 'pending' | 'active' | 'completed'
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Відправляємо всім підключеним (не тільки учасникам турніру)
        await websocket_manager.broadcast_to_all(message)
        logger.info(f"Sent game_result_updated notification for game {game_id}, participant {participant_id}")
    finally:
        if should_close:
            db.close()


async def notify_game_completed(
    tournament_id: int,
    game_id: int,
    round_number: int,
    is_final: bool,
    db=None
):
    """Відправити сповіщення про завершення гри"""
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        from datetime import datetime
        message = {
            "type": "game_completed",
            "tournament_id": tournament_id,
            "game_id": game_id,
            "round_number": round_number,
            "is_final": is_final,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Відправляємо всім підключеним (не тільки учасникам турніру)
        await websocket_manager.broadcast_to_all(message)
        logger.info(f"Sent game_completed notification for game {game_id}")
    finally:
        if should_close:
            db.close()


async def notify_position_updated(
    tournament_id: int,
    participant_id: int,
    user_id: int,
    total_score: float,
    final_position: int = None,
    db=None
):
    """Відправити сповіщення про оновлення загальних очок учасника"""
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        from datetime import datetime
        message = {
            "type": "position_updated",
            "tournament_id": tournament_id,
            "participant_id": participant_id,  # ID з tournament_participants
            "user_id": user_id,
            "total_score": total_score,
            "final_position": final_position,  # Фінальна позиція (якщо є)
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Відправляємо всім підключеним (не тільки учасникам турніру)
        await websocket_manager.broadcast_to_all(message)
        logger.info(f"Sent position_updated notification for participant {participant_id}, total_score: {total_score}")
    finally:
        if should_close:
            db.close()


async def notify_lobby_maker_assigned(
    tournament_id: int,
    game_id: int,
    round_number: int,
    lobby_maker_id: int,
    lobby_maker_participant_id: int,
    lobby_maker_battletag: str = None,
    db=None
):
    """Відправити сповіщення про призначення лоббі мейкера"""
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        from datetime import datetime
        
        # Якщо battletag не передано, отримуємо з БД
        if lobby_maker_battletag is None:
            from models.user import User
            user = db.query(User).filter(User.id == lobby_maker_id).first()
            lobby_maker_battletag = user.battletag if user else "Unknown"
        
        message = {
            "type": "lobby_maker_assigned",
            "tournament_id": tournament_id,
            "game_id": game_id,
            "round_number": round_number,
            "lobby_maker_id": lobby_maker_id,  # ID користувача (user_id)
            "lobby_maker_participant_id": lobby_maker_participant_id,  # ID з game_participants
            "lobby_maker_battletag": lobby_maker_battletag,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Відправляємо всім підключеним (для оновлення UI)
        await websocket_manager.broadcast_to_all(message)
        logger.info(f"[NOTIFY] Sent lobby_maker_assigned notification for game {game_id}, lobby_maker_id: {lobby_maker_id}")
    finally:
        if should_close:
            db.close()


async def notify_lobby_maker_removed(
    tournament_id: int,
    game_id: int,
    round_number: int,
    db=None
):
    """Відправити сповіщення про видалення лоббі мейкера"""
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        from datetime import datetime
        message = {
            "type": "lobby_maker_removed",
            "tournament_id": tournament_id,
            "game_id": game_id,
            "round_number": round_number,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Відправляємо всім підключеним (для оновлення UI)
        await websocket_manager.broadcast_to_all(message)
        logger.info(f"[NOTIFY] Sent lobby_maker_removed notification for game {game_id}")
    finally:
        if should_close:
            db.close()


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

