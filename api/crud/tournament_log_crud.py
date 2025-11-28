from sqlalchemy.orm import Session
from typing import List
from models.tournament_log import TournamentLog
from models.user import User


def create_tournament_log(
    db: Session,
    tournament_id: int,
    user_id: int,
    action_type: str,
    action_description: str
):
    """Створити лог дії в турнірі"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    log = TournamentLog(
        tournament_id=tournament_id,
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


def get_tournament_logs(
    db: Session,
    tournament_id: int,
    skip: int = 0,
    limit: int = 50
) -> List[TournamentLog]:
    """Отримати логи турніру з пагінацією"""
    return db.query(TournamentLog).filter(
        TournamentLog.tournament_id == tournament_id
    ).order_by(
        TournamentLog.created_at.desc()
    ).offset(skip).limit(limit).all()


def get_tournament_logs_count(db: Session, tournament_id: int) -> int:
    """Отримати загальну кількість логів для турніру"""
    return db.query(TournamentLog).filter(TournamentLog.tournament_id == tournament_id).count()

