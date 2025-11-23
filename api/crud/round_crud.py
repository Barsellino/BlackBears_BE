from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from models.tournament_round import TournamentRound, RoundStatus
from models.tournament_game import TournamentGame, GameStatus
from schemas.tournament import TournamentRoundCreate


def create_tournament_round(db: Session, round_data: TournamentRoundCreate):
    db_round = TournamentRound(**round_data.dict())
    db.add(db_round)
    db.commit()
    db.refresh(db_round)
    return db_round


def get_tournament_round(db: Session, round_id: int):
    return db.query(TournamentRound).filter(TournamentRound.id == round_id).first()


def get_tournament_rounds(db: Session, tournament_id: int):
    return db.query(TournamentRound).filter(
        TournamentRound.tournament_id == tournament_id
    ).order_by(TournamentRound.round_number).all()


def get_current_round(db: Session, tournament_id: int):
    """Get the current active round"""
    return db.query(TournamentRound).filter(
        TournamentRound.tournament_id == tournament_id,
        TournamentRound.status == RoundStatus.ACTIVE
    ).first()


def start_round(db: Session, round_id: int):
    """Start a tournament round"""
    db_round = db.query(TournamentRound).filter(TournamentRound.id == round_id).first()
    if not db_round:
        return None
    
    db_round.status = RoundStatus.ACTIVE
    db_round.started_at = func.now()
    
    # Also start all games in this round
    games = db.query(TournamentGame).filter(TournamentGame.round_id == round_id).all()
    for game in games:
        game.status = GameStatus.ACTIVE
        game.started_at = func.now()
    
    db.commit()
    db.refresh(db_round)
    return db_round


def complete_round(db: Session, round_id: int):
    """Complete a tournament round"""
    db_round = db.query(TournamentRound).filter(TournamentRound.id == round_id).first()
    if not db_round:
        return None
    
    db_round.status = RoundStatus.COMPLETED
    db_round.completed_at = func.now()
    
    # Also complete all games in this round
    games = db.query(TournamentGame).filter(TournamentGame.round_id == round_id).all()
    for game in games:
        if game.status != GameStatus.COMPLETED:
            game.status = GameStatus.COMPLETED
            game.finished_at = func.now()
    
    db.commit()
    db.refresh(db_round)
    return db_round


def create_round_with_games(db: Session, tournament_id: int, round_number: int, total_participants: int):
    """Create a round with appropriate number of games"""
    # Create the round
    round_data = TournamentRoundCreate(
        tournament_id=tournament_id,
        round_number=round_number
    )
    db_round = create_tournament_round(db, round_data)
    
    # Calculate number of games needed (8 players per game)
    num_games = total_participants // 8
    
    # Create games for this round
    for game_number in range(1, num_games + 1):
        game = TournamentGame(
            tournament_id=tournament_id,
            round_id=db_round.id,
            game_number=game_number
        )
        db.add(game)
    
    db.commit()
    db.refresh(db_round)
    return db_round