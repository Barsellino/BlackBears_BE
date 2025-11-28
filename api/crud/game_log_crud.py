from sqlalchemy.orm import Session
from typing import List, Optional
from models.game_log import GameLog
from models.user import User
from core.roles import UserRole


def create_game_log(
    db: Session,
    game_id: int,
    user_id: int,
    action_type: str,
    action_description: str
):
    """Створити лог дії в грі"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    log = GameLog(
        game_id=game_id,
        user_id=user_id,
        user_battletag=user.battletag or "Unknown",
        user_role=user.role.value if hasattr(user.role, 'value') else str(user.role),
        action_type=action_type,
        action_description=action_description
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_game_logs(
    db: Session,
    game_id: int,
    skip: int = 0,
    limit: int = 50
) -> List[GameLog]:
    """Отримати логи гри з пагінацією"""
    return db.query(GameLog).filter(
        GameLog.game_id == game_id
    ).order_by(
        GameLog.created_at.desc()
    ).offset(skip).limit(limit).all()


def get_game_logs_count(db: Session, game_id: int) -> int:
    """Отримати загальну кількість логів для гри"""
    return db.query(GameLog).filter(GameLog.game_id == game_id).count()

