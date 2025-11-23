from sqlalchemy.orm import Session
from typing import List
from models.tournament_game import TournamentGame
from models.game_participant import GameParticipant
from models.tournament_participant import TournamentParticipant
from schemas.tournament import TournamentGameCreate, GameParticipantCreate, GameParticipantUpdate


def create_tournament_game(db: Session, game_data: TournamentGameCreate):
    db_game = TournamentGame(**game_data.dict())
    db.add(db_game)
    db.commit()
    db.refresh(db_game)
    return db_game


def get_tournament_game(db: Session, game_id: int):
    from sqlalchemy.orm import joinedload
    from models.user import User
    
    game = db.query(TournamentGame).options(
        joinedload(TournamentGame.participants)
        .joinedload(GameParticipant.participant)
        .joinedload(TournamentParticipant.user)
    ).filter(TournamentGame.id == game_id).first()
    
    # Add user info to game participants
    if game:
        for game_participant in game.participants:
            user = game_participant.participant.user
            game_participant.user_id = user.id
            game_participant.battletag = user.battletag
            game_participant.name = user.name
    
    return game


def get_round_games(db: Session, round_id: int):
    from sqlalchemy.orm import joinedload
    from models.tournament_participant import TournamentParticipant
    from models.user import User
    
    games = db.query(TournamentGame).options(
        joinedload(TournamentGame.participants)
        .joinedload(GameParticipant.participant)
        .joinedload(TournamentParticipant.user),
        joinedload(TournamentGame.round)
    ).filter(
        TournamentGame.round_id == round_id
    ).order_by(TournamentGame.game_number).all()
    
    # Add user info to game participants and round number
    for game in games:
        game.round_number = game.round.round_number
        for game_participant in game.participants:
            user = game_participant.participant.user
            game_participant.user_id = user.id
            game_participant.battletag = user.battletag
            game_participant.name = user.name
    
    return games


def get_tournament_games(db: Session, tournament_id: int):
    return db.query(TournamentGame).filter(
        TournamentGame.tournament_id == tournament_id
    ).all()


def add_game_participant(db: Session, participant_data: GameParticipantCreate):
    db_participant = GameParticipant(**participant_data.dict())
    db.add(db_participant)
    db.commit()
    db.refresh(db_participant)
    return db_participant


def remove_game_participant(db: Session, game_id: int, participant_id: int):
    """Remove participant from specific game"""
    game_participant = db.query(GameParticipant).filter(
        GameParticipant.game_id == game_id,
        GameParticipant.participant_id == participant_id
    ).first()
    
    if game_participant:
        db.delete(game_participant)
        db.commit()
        return True
    return False


def move_participant_to_game(db: Session, participant_id: int, from_game_id: int, to_game_id: int):
    """Move participant from one game to another (drag & drop functionality)"""
    # Remove from old game
    old_game_participant = db.query(GameParticipant).filter(
        GameParticipant.game_id == from_game_id,
        GameParticipant.participant_id == participant_id
    ).first()
    
    if not old_game_participant:
        return None
    
    # Check if target game has space (max 8 players)
    target_game_count = db.query(GameParticipant).filter(
        GameParticipant.game_id == to_game_id
    ).count()
    
    if target_game_count >= 8:
        return None  # Game is full
    
    # Check if already in target game
    existing = db.query(GameParticipant).filter(
        GameParticipant.game_id == to_game_id,
        GameParticipant.participant_id == participant_id
    ).first()
    
    if existing:
        return None  # Already in target game
    
    # Remove from old game
    db.delete(old_game_participant)
    
    # Add to new game
    new_game_participant = GameParticipant(
        game_id=to_game_id,
        participant_id=participant_id
    )
    db.add(new_game_participant)
    db.commit()
    db.refresh(new_game_participant)
    
    return new_game_participant


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


def auto_assign_participants_to_games(db: Session, tournament_id: int, round_id: int):
    """Automatically assign participants to games based on current scores"""
    # Get all participants sorted by score (Swiss system pairing)
    participants = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament_id
    ).order_by(TournamentParticipant.total_score.desc()).all()
    
    # Get games for this round
    games = get_round_games(db, round_id)
    
    # Clear existing assignments for this round
    for game in games:
        db.query(GameParticipant).filter(GameParticipant.game_id == game.id).delete()
    
    # Assign 8 participants per game
    participants_per_game = 8
    for i, participant in enumerate(participants):
        game_index = i // participants_per_game
        if game_index < len(games):
            game_participant = GameParticipant(
                game_id=games[game_index].id,
                participant_id=participant.id
            )
            db.add(game_participant)
    
    db.commit()
    return games