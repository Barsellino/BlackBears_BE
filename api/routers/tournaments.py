from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from api.deps.db import get_db
from core.validators import (
    validate_tournament_exists, validate_user_exists, validate_tournament_creator,
    validate_tournament_registration_open, validate_tournament_not_full
)
from core.exceptions import TournamentException
from api.crud.tournament_crud import (
    create_tournament, get_tournament, get_tournaments, get_user_tournaments,
    update_tournament
)
from api.crud.participant_crud import (
    join_tournament, leave_tournament, get_tournament_participants,
    get_tournament_leaderboard
)
from api.crud.game_crud import move_participant_to_game
from services.tournament_manager import TournamentManager
from schemas.tournament import (
    Tournament, TournamentCreate, TournamentUpdate, TournamentWithParticipants,
    TournamentParticipant
)
from core.auth import get_current_active_user
from models.user import User

router = APIRouter(prefix="/tournaments", tags=["Tournaments"])


@router.post("/", response_model=Tournament)
async def create_new_tournament(
    tournament: TournamentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new tournament"""
    return create_tournament(db, tournament, current_user.id)


@router.get("/", response_model=List[Tournament])
async def list_tournaments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get list of all tournaments"""
    return get_tournaments(db, skip=skip, limit=limit)


@router.get("/my", response_model=List[Tournament])
async def get_my_tournaments(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get tournaments created by current user"""
    return get_user_tournaments(db, current_user.id)


@router.get("/{tournament_id}", response_model=TournamentWithParticipants)
async def get_tournament_details(
    tournament_id: int,
    db: Session = Depends(get_db)
):
    """Get tournament details with participants"""
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return tournament


@router.put("/{tournament_id}", response_model=Tournament)
async def update_tournament_details(
    tournament_id: int,
    tournament_update: TournamentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update tournament (only creator can update)"""
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    if tournament.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only tournament creator can update")
    
    updated_tournament = update_tournament(db, tournament_id, tournament_update)
    return updated_tournament


@router.post("/{tournament_id}/join", response_model=TournamentParticipant)
async def join_tournament_endpoint(
    tournament_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Join a tournament"""
    try:
        tournament = validate_tournament_exists(db, tournament_id)
        validate_tournament_registration_open(tournament)
        validate_tournament_not_full(db, tournament)
        
        participant = join_tournament(db, tournament_id, current_user.id)
        if not participant:
            from core.exceptions import AlreadyJoined
            raise AlreadyJoined()
        
        return participant
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{tournament_id}/leave")
async def leave_tournament_endpoint(
    tournament_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Leave a tournament"""
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    if tournament.status != "registration":
        raise HTTPException(status_code=400, detail="Cannot leave tournament after registration closes")
    
    success = leave_tournament(db, tournament_id, current_user.id)
    if not success:
        raise HTTPException(status_code=400, detail="Not participating in this tournament")
    
    return {"message": "Successfully left tournament"}


@router.get("/{tournament_id}/participants", response_model=List[TournamentParticipant])
async def get_tournament_participants_endpoint(
    tournament_id: int,
    db: Session = Depends(get_db)
):
    """Get tournament participants"""
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    return get_tournament_participants(db, tournament_id)


@router.post("/{tournament_id}/add-participant/{user_id}", response_model=TournamentParticipant)
async def add_participant_simple(
    tournament_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Add participant to tournament (simple version for testing)"""
    try:
        tournament = validate_tournament_exists(db, tournament_id)
        validate_tournament_not_full(db, tournament)
        validate_user_exists(db, user_id)
        
        participant = join_tournament(db, tournament_id, user_id)
        if not participant:
            from core.exceptions import AlreadyJoined
            raise AlreadyJoined()
        
        return participant
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class AddParticipantRequest(BaseModel):
    user_id: int

@router.post("/{tournament_id}/add-participant", response_model=TournamentParticipant)
async def add_participant_manually(
    tournament_id: int,
    request: AddParticipantRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Manually add participant to tournament (only creator can do this)"""
    try:
        tournament = validate_tournament_exists(db, tournament_id)
        validate_tournament_creator(tournament, current_user.id, "add participants")
        validate_tournament_not_full(db, tournament)
        validate_user_exists(db, request.user_id)
        
        participant = join_tournament(db, tournament_id, request.user_id)
        if not participant:
            from core.exceptions import AlreadyJoined
            raise AlreadyJoined()
        
        return participant
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{tournament_id}/remove-participant/{user_id}")
async def remove_participant_manually(
    tournament_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Manually remove participant from tournament (only creator can do this)"""
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    if tournament.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only tournament creator can remove participants")
    
    success = leave_tournament(db, tournament_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="User not participating in this tournament")
    
    return {"message": "Participant removed successfully"}


@router.put("/{tournament_id}/move-participant")
async def move_participant_between_games(
    tournament_id: int,
    participant_id: int,
    from_game_id: int,
    to_game_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Move participant from one game to another (drag & drop)"""
    try:
        tournament = validate_tournament_exists(db, tournament_id)
        validate_tournament_creator(tournament, current_user.id, "move participants")
        
        if from_game_id == to_game_id:
            raise HTTPException(status_code=400, detail="Cannot move to the same game")
        
        result = move_participant_to_game(db, participant_id, from_game_id, to_game_id)
        if not result:
            from core.exceptions import InvalidGameMove
            raise InvalidGameMove("game full or participant not found")
        
        return {"message": "Participant moved successfully"}
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{tournament_id}/start")
async def start_tournament_endpoint(
    tournament_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Start tournament (only creator can start)"""
    try:
        tournament = validate_tournament_exists(db, tournament_id)
        validate_tournament_creator(tournament, current_user.id, "start tournament")
        
        manager = TournamentManager(tournament)
        updated_tournament = manager.start_tournament(db)
        
        return {
            "message": "Tournament started successfully",
            "tournament_id": tournament_id,
            "current_round": updated_tournament.current_round,
            "status": updated_tournament.status.value
        }
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{tournament_id}/next-round")
async def create_next_round_endpoint(
    tournament_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create next round (only creator can do this)"""
    try:
        tournament = validate_tournament_exists(db, tournament_id)
        validate_tournament_creator(tournament, current_user.id, "create next round")
        
        manager = TournamentManager(tournament)
        next_round = manager.create_next_round(db)
        
        return {
            "message": "Next round created successfully",
            "tournament_id": tournament_id,
            "round_number": next_round.round_number,
            "current_round": tournament.current_round
        }
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{tournament_id}/finish")
async def finish_tournament_endpoint(
    tournament_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Finish tournament (only creator can finish)"""
    try:
        tournament = validate_tournament_exists(db, tournament_id)
        validate_tournament_creator(tournament, current_user.id, "finish tournament")
        
        manager = TournamentManager(tournament)
        finished_tournament = manager.finish_tournament(db)
        
        return {
            "message": "Tournament finished successfully",
            "tournament_id": tournament_id,
            "status": finished_tournament.status.value,
            "end_date": finished_tournament.end_date
        }
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{tournament_id}/status")
async def get_tournament_status_endpoint(
    tournament_id: int,
    db: Session = Depends(get_db)
):
    """Get tournament status and available actions"""
    tournament = validate_tournament_exists(db, tournament_id)
    manager = TournamentManager(tournament)
    return manager.get_tournament_status(db)


@router.get("/{tournament_id}/leaderboard", response_model=List[TournamentParticipant])
async def get_tournament_leaderboard_endpoint(
    tournament_id: int,
    db: Session = Depends(get_db)
):
    """Get tournament leaderboard (sorted by total score)"""
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    return get_tournament_leaderboard(db, tournament_id)


@router.get("/{tournament_id}/rounds/{round_number}/games")
async def get_round_games(
    tournament_id: int,
    round_number: int,
    db: Session = Depends(get_db)
):
    """Get all games for a specific round"""
    from api.crud.game_crud import get_round_games
    from models.tournament_round import TournamentRound
    
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    # Find round by tournament_id and round_number
    round_obj = db.query(TournamentRound).filter(
        TournamentRound.tournament_id == tournament_id,
        TournamentRound.round_number == round_number
    ).first()
    
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")
    
    games = get_round_games(db, round_obj.id)
    return games