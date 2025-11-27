from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from api.deps.db import get_db
from api.crud.tournament_crud import get_tournament
from api.crud.game_crud import (
    get_tournament_game, get_round_games
)
from schemas.game_results import GameResultsSubmission, GameResultResponse, GameResultInput
from schemas.tournament import TournamentGameWithParticipants
from core.auth import get_current_active_user
from core.validators import validate_tournament_exists, validate_tournament_creator
from core.exceptions import TournamentException
from models.user import User
from services import games_service

router = APIRouter(prefix="/games", tags=["Games"])


@router.get("/{game_id}", response_model=TournamentGameWithParticipants)
async def get_game_details(
    game_id: int,
    db: Session = Depends(get_db)
):
    """Get game details with participants"""
    game = get_tournament_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.get("/round/{round_id}", response_model=List[TournamentGameWithParticipants])
async def get_round_games_endpoint(
    round_id: int,
    db: Session = Depends(get_db)
):
    """Get all games in a round"""
    games = get_round_games(db, round_id)
    return games


@router.put("/{game_id}/results", response_model=GameResultResponse)
async def submit_game_results(
    game_id: int,
    results_data: GameResultsSubmission,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Submit results for a game"""
    # Validate game exists
    game = get_tournament_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Validate tournament
    tournament = validate_tournament_exists(db, game.tournament_id)
    games_service.validate_tournament_not_finished(tournament)
    
    try:
        updated_count = games_service.submit_game_results_logic(
            db, game_id, results_data, current_user, tournament
        )
        
        return GameResultResponse(
            game_id=game_id,
            updated_participants=updated_count,
            message=f"Results submitted for {updated_count} participants"
        )
        
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{game_id}/results")
async def clear_game_results(
    game_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Clear all results for a game (only if game not completed)"""
    # Validate game exists
    game = get_tournament_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Validate tournament creator
    tournament = validate_tournament_exists(db, game.tournament_id)
    games_service.validate_tournament_not_finished(tournament)
    validate_tournament_creator(tournament, current_user.id, "clear game results", current_user.role)
    
    try:
        cleared_count = games_service.clear_game_results_logic(db, game_id, game)
        
        return {
            "message": f"Results cleared for {cleared_count} participants",
            "game_id": game_id
        }
        
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{game_id}/participant/{participant_id}/result")
async def submit_participant_result(
    game_id: int,
    participant_id: int,
    result: GameResultInput,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Submit result for single participant in a game"""
    # Validate game exists
    game = get_tournament_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Validate tournament
    tournament = validate_tournament_exists(db, game.tournament_id)
    games_service.validate_tournament_not_finished(tournament)
    
    try:
        all_have_results = games_service.submit_participant_result_logic(
            db, game_id, participant_id, result, current_user, tournament, game
        )
        
        return {
            "message": "Participant result submitted successfully",
            "game_id": game_id,
            "participant_id": participant_id,
            "points": result.points,
            "game_completed": all_have_results
        }
        
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{game_id}/participant/{participant_id}/result")
async def clear_participant_result(
    game_id: int,
    participant_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Clear result for specific participant in a game"""
    # Validate game exists
    game = get_tournament_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Validate tournament exists
    tournament = validate_tournament_exists(db, game.tournament_id)
    games_service.validate_tournament_not_finished(tournament)
    games_service.validate_round_not_completed(db, game)

    # Validate permissions
    # Allow if:
    # 1. User is tournament creator
    # 2. User is admin/super_admin
    # 3. User is ANY participant of this game
    # 4. User is Lobby Maker for this game
    
    is_creator = tournament.creator_id == current_user.id
    is_admin = current_user.role in ["admin", "super_admin"]
    
    # Check if user is a participant in this game
    from api.crud.game_crud import get_game_participants
    from api.crud.participant_crud import get_participant
    
    game_participants = get_game_participants(db, game_id)
    
    is_game_participant = False
    for gp in game_participants:
        # We need to get the user_id for each participant
        # Assuming gp.participant is loaded or we fetch it
        p = get_participant(db, gp.participant_id)
        if p and p.user_id == current_user.id:
            is_game_participant = True
            break
            
    # Check if user is Lobby Maker
    is_lobby_maker = game.lobby_maker_id == current_user.id
    
    # Debug logging
    from core.logging import logger
    logger.info(f"Clear result permission check: user_id={current_user.id}, participant_id={participant_id}")
    logger.info(f"is_creator={is_creator}, is_admin={is_admin}, is_game_participant={is_game_participant}, is_lobby_maker={is_lobby_maker}")
    
    if not (is_creator or is_admin or is_game_participant or is_lobby_maker):
        from core.exceptions import UnauthorizedAction
        raise UnauthorizedAction("clear participant result")
    
    try:
        games_service.clear_participant_result_logic(db, game_id, participant_id, game)
        
        return {
            "message": "Participant result cleared",
            "game_id": game_id,
            "participant_id": participant_id
        }
        
    except HTTPException:
        raise
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{game_id}/positions/batch")
async def submit_positions_batch(
    game_id: int,
    updates: List[dict],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Batch update positions for multiple participants"""
    game = get_tournament_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    tournament = validate_tournament_exists(db, game.tournament_id)
    games_service.validate_tournament_not_finished(tournament)
    
    try:
        updated_count, all_have_positions = games_service.submit_positions_batch_logic(
            db, game_id, updates, current_user, tournament, game
        )
        
        return {
            "message": f"Updated {updated_count} participants",
            "game_id": game_id,
            "game_completed": all_have_positions
        }
        
    except HTTPException:
        raise
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{game_id}/participant/{participant_id}/position")
async def submit_participant_position(
    game_id: int,
    participant_id: int,
    positions: List[int],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Submit position for single participant (can be shared positions)"""
    game = get_tournament_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    tournament = validate_tournament_exists(db, game.tournament_id)
    games_service.validate_tournament_not_finished(tournament)
    
    try:
        sorted_positions, calculated_points, all_have_positions = games_service.submit_participant_position_logic(
            db, game_id, participant_id, positions, current_user, tournament, game
        )
        
        return {
            "message": "Position submitted successfully",
            "game_id": game_id,
            "participant_id": participant_id,
            "positions": sorted_positions,
            "calculated_points": calculated_points,
            "game_completed": all_have_positions
        }
        
    except HTTPException:
        raise
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")




@router.post("/{game_id}/lobby-maker")
async def assign_lobby_maker_by_user_id(
    game_id: int,
    user_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Assign Lobby Maker to a game by user_id (creator or admin only)"""
    game = get_tournament_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    tournament = validate_tournament_exists(db, game.tournament_id)
    
    # Get user_id from body
    user_id = user_data.get('user_id')
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    try:
        user_id = int(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id must be an integer")
    
    # Find participant_id for this user in this game
    from api.crud.game_crud import get_game_participants
    game_participants = get_game_participants(db, game_id)
    
    participant = next(
        (gp for gp in game_participants if gp.participant.user_id == user_id),
        None
    )
    
    if not participant:
        raise HTTPException(
            status_code=400,
            detail=f"User {user_id} is not a participant in this game"
        )
    
    try:
        return games_service.assign_lobby_maker_logic(
            db, game_id, participant.participant_id, current_user, tournament
        )
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{game_id}/lobby-maker/{participant_id}")
async def assign_lobby_maker(
    game_id: int,
    participant_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Assign Lobby Maker to a game (creator or admin only)"""
    game = get_tournament_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    tournament = validate_tournament_exists(db, game.tournament_id)
    
    try:
        return games_service.assign_lobby_maker_logic(
            db, game_id, participant_id, current_user, tournament
        )
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{game_id}/lobby-maker")
async def remove_lobby_maker(
    game_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove Lobby Maker from a game (creator or admin only)"""
    game = get_tournament_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    tournament = validate_tournament_exists(db, game.tournament_id)
    
    try:
        return games_service.remove_lobby_maker_logic(
            db, game_id, current_user, tournament
        )
    except HTTPException:
        raise
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{game_id}/lobby-maker")
async def get_lobby_maker(
    game_id: int,
    db: Session = Depends(get_db)
):
    """Get current Lobby Maker for a game"""
    try:
        user = games_service.get_lobby_maker_logic(db, game_id)
        if not user:
            return {"lobby_maker": None, "assigned": False}
            
        return {
            "lobby_maker": {
                "id": user.id,
                "username": user.username,
                "battletag": user.battletag
            },
            "assigned": True
        }
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")