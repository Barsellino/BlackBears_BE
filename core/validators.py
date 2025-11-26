from sqlalchemy.orm import Session
from models.tournament import Tournament, TournamentStatus
from models.user import User
from core.exceptions import (
    TournamentNotFound, TournamentFull, TournamentClosed, 
    UnauthorizedAction, UserNotFound, InvalidTournamentState
)
from api.crud.participant_crud import get_tournament_participants
from api.crud.user import get_user_by_id


def validate_tournament_exists(db: Session, tournament_id: int) -> Tournament:
    """Validate tournament exists and return it"""
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise TournamentNotFound()
    return tournament


def validate_user_exists(db: Session, user_id: int) -> User:
    """Validate user exists and return it"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise UserNotFound()
    return user


def validate_tournament_creator(tournament: Tournament, user_id: int, action: str = "perform this action"):
    """Validate user is tournament creator"""
    if tournament.creator_id != user_id:
        raise UnauthorizedAction(action)


def validate_tournament_registration_open(tournament: Tournament):
    """Validate tournament is open for registration"""
    if tournament.status != TournamentStatus.REGISTRATION:
        raise TournamentClosed()
    
    # Check deadline
    if tournament.registration_deadline:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        deadline = tournament.registration_deadline
        
        # Ensure deadline is timezone-aware for comparison
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
            
        if now > deadline:
            raise TournamentClosed("Registration deadline has passed")


def validate_tournament_not_full(db: Session, tournament: Tournament):
    """Validate tournament has space for more participants"""
    current_participants = len(get_tournament_participants(db, tournament.id))
    if current_participants >= tournament.total_participants:
        raise TournamentFull()


def validate_tournament_can_start(db: Session, tournament: Tournament):
    """Validate tournament can be started"""
    if tournament.status != TournamentStatus.REGISTRATION:
        raise InvalidTournamentState("start tournament")
    
    current_participants = len(get_tournament_participants(db, tournament.id))
    if current_participants < 8:
        raise InvalidTournamentState(f"start tournament (need exactly {tournament.total_participants} participants, have {current_participants})")


def validate_participants_count(total_participants: int):
    """Validate participants count is valid for tournament"""
    if total_participants % 8 != 0:
        raise ValueError("Total participants must be divisible by 8")
    
    if total_participants < 8:
        raise ValueError("Tournament must have at least 8 participants")
    
    if total_participants > 128:
        raise ValueError("Tournament cannot have more than 128 participants")


def validate_rounds_count(total_rounds: int, total_participants: int):
    """Validate rounds count is reasonable"""
    if total_rounds < 1:
        raise ValueError("Tournament must have at least 1 round")
    
    # Swiss system recommendation: log2(participants) + 1
    import math
    recommended_max = math.ceil(math.log2(total_participants)) + 2
    
    if total_rounds > recommended_max:
        raise ValueError(f"Too many rounds for {total_participants} participants (recommended max: {recommended_max})")


def validate_game_capacity(current_players: int, max_players: int = 8):
    """Validate game has space for more players"""
    if current_players >= max_players:
        from core.exceptions import GameFull
        raise GameFull()


def validate_position_and_points(position: int = None, points: int = None):
    """Validate game result position and points"""
    if position is not None:
        if not (1 <= position <= 8):
            raise ValueError("Position must be between 1 and 8")
    
    if points is not None:
        if not (1 <= points <= 8):
            raise ValueError("Points must be between 1 and 8")
    
    # Validate position-points consistency (1st place = 8 points, 8th place = 1 point)
    if position is not None and points is not None:
        expected_points = 9 - position
        if points != expected_points:
            raise ValueError(f"Position {position} should have {expected_points} points, got {points}")