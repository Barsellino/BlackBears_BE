from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List
from models.tournament_participant import TournamentParticipant
from models.game_participant import GameParticipant


def join_tournament(db: Session, tournament_id: int, user_id: int):
    # Check if already joined
    existing = db.query(TournamentParticipant).filter(
        and_(
            TournamentParticipant.tournament_id == tournament_id,
            TournamentParticipant.user_id == user_id
        )
    ).first()
    
    if existing:
        return None
    
    db_participant = TournamentParticipant(
        tournament_id=tournament_id,
        user_id=user_id
    )
    db.add(db_participant)
    db.commit()
    db.refresh(db_participant)
    return db_participant


def get_tournament_participants(db: Session, tournament_id: int):
    from sqlalchemy.orm import joinedload
    return db.query(TournamentParticipant).options(
        joinedload(TournamentParticipant.user)
    ).filter(
        TournamentParticipant.tournament_id == tournament_id
    ).all()


def get_participant_by_ids(db: Session, tournament_id: int, user_id: int):
    return db.query(TournamentParticipant).filter(
        and_(
            TournamentParticipant.tournament_id == tournament_id,
            TournamentParticipant.user_id == user_id
        )
    ).first()


def leave_tournament(db: Session, tournament_id: int, user_id: int):
    participant = db.query(TournamentParticipant).filter(
        and_(
            TournamentParticipant.tournament_id == tournament_id,
            TournamentParticipant.user_id == user_id
        )
    ).first()
    
    if participant:
        db.delete(participant)
        db.commit()
        return True
    return False


def get_tournament_leaderboard(db: Session, tournament_id: int):
    from models.user import User
    from sqlalchemy.orm import joinedload
    
    participants = db.query(TournamentParticipant).options(
        joinedload(TournamentParticipant.user)
    ).filter(
        TournamentParticipant.tournament_id == tournament_id
    ).order_by(TournamentParticipant.total_score.desc()).all()
    
    # Add user info to participants
    for participant in participants:
        participant.battletag = participant.user.battletag
        participant.name = participant.user.name
    
    return participants


def update_participant_total_score(db: Session, participant_id: int):
    """Recalculate total score from all game results"""
    # Use calculated_points (Float) instead of points (Integer)
    subquery = db.query(
        func.coalesce(func.sum(GameParticipant.calculated_points), 0)
    ).filter(
        GameParticipant.participant_id == participant_id
    ).scalar_subquery()
    
    db.query(TournamentParticipant).filter(
        TournamentParticipant.id == participant_id
    ).update({TournamentParticipant.total_score: subquery}, synchronize_session=False)
    
    db.commit()


def update_final_positions(db: Session, tournament_id: int):
    """Update final positions based on total scores"""
    participants = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament_id
    ).order_by(TournamentParticipant.total_score.desc()).all()
    
    for position, participant in enumerate(participants, 1):
        participant.final_position = position
    
    db.commit()
    return participants