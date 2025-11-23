from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from models.tournament import Tournament
from models.tournament_participant import TournamentParticipant
from models.tournament_round import TournamentRound
from models.tournament_game import TournamentGame
from models.game_participant import GameParticipant
from schemas.tournament import (
    TournamentCreate, TournamentUpdate,
    TournamentParticipantCreate,
    TournamentRoundCreate,
    TournamentGameCreate,
    GameParticipantCreate, GameParticipantUpdate
)


# Tournament CRUD
def create_tournament(db: Session, tournament: TournamentCreate, creator_id: int):
    db_tournament = Tournament(
        **tournament.dict(),
        creator_id=creator_id
    )
    db.add(db_tournament)
    db.commit()
    db.refresh(db_tournament)
    return db_tournament


def get_tournament(db: Session, tournament_id: int):
    return db.query(Tournament).filter(Tournament.id == tournament_id).first()


def get_tournaments(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Tournament).offset(skip).limit(limit).all()


def get_user_tournaments(db: Session, user_id: int):
    return db.query(Tournament).filter(Tournament.creator_id == user_id).all()


def update_tournament(db: Session, tournament_id: int, tournament_update: TournamentUpdate):
    db_tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not db_tournament:
        return None
    
    update_data = tournament_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_tournament, field, value)
    
    db.commit()
    db.refresh(db_tournament)
    return db_tournament


# Participant CRUD
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
    return db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament_id
    ).all()


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


# Round CRUD
def create_tournament_round(db: Session, round_data: TournamentRoundCreate):
    db_round = TournamentRound(**round_data.dict())
    db.add(db_round)
    db.commit()
    db.refresh(db_round)
    return db_round


def get_tournament_rounds(db: Session, tournament_id: int):
    return db.query(TournamentRound).filter(
        TournamentRound.tournament_id == tournament_id
    ).order_by(TournamentRound.round_number).all()


# Game CRUD
def create_tournament_game(db: Session, game_data: TournamentGameCreate):
    db_game = TournamentGame(**game_data.dict())
    db.add(db_game)
    db.commit()
    db.refresh(db_game)
    return db_game


def get_round_games(db: Session, round_id: int):
    return db.query(TournamentGame).filter(
        TournamentGame.round_id == round_id
    ).order_by(TournamentGame.game_number).all()


# Game Participant CRUD
def add_game_participant(db: Session, participant_data: GameParticipantCreate):
    db_participant = GameParticipant(**participant_data.dict())
    db.add(db_participant)
    db.commit()
    db.refresh(db_participant)
    return db_participant


def update_game_result(db: Session, game_participant_id: int, result_update: GameParticipantUpdate):
    db_participant = db.query(GameParticipant).filter(
        GameParticipant.id == game_participant_id
    ).first()
    
    if not db_participant:
        return None
    
    update_data = result_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_participant, field, value)
    
    db.commit()
    db.refresh(db_participant)
    return db_participant


def get_game_participants(db: Session, game_id: int):
    return db.query(GameParticipant).filter(
        GameParticipant.game_id == game_id
    ).all()


# Statistics and leaderboard
def get_tournament_leaderboard(db: Session, tournament_id: int):
    return db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament_id
    ).order_by(TournamentParticipant.total_score.desc()).all()


def update_participant_total_score(db: Session, participant_id: int):
    """Recalculate total score from all game results"""
    participant = db.query(TournamentParticipant).filter(
        TournamentParticipant.id == participant_id
    ).first()
    
    if not participant:
        return None
    
    total_points = db.query(GameParticipant).filter(
        GameParticipant.participant_id == participant_id
    ).with_entities(
        db.func.sum(GameParticipant.points)
    ).scalar() or 0
    
    participant.total_score = total_points
    db.commit()
    db.refresh(participant)
    return participant