from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from api.deps.db import get_db
from api.crud.tournament_crud import get_tournament
from api.crud.game_crud import (
    get_tournament_game, update_game_result, get_game_participants,
    get_round_games
)
from api.crud.participant_crud import update_participant_total_score
from schemas.game_results import GameResultsSubmission, GameResultResponse, GameResultInput
from schemas.game_results_v2 import calculate_points_from_positions
from schemas.tournament import TournamentGameWithParticipants, GameParticipant
from core.auth import get_current_active_user
from core.validators import validate_tournament_exists, validate_tournament_creator
from core.exceptions import TournamentException
from models.user import User
from models.tournament_game import GameStatus

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
    try:
        # Validate game exists
        game = get_tournament_game(db, game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Validate tournament creator
        tournament = validate_tournament_exists(db, game.tournament_id)
        validate_tournament_creator(tournament, current_user.id, "submit game results")
        
        # Get current game participants
        game_participants = get_game_participants(db, game_id)
        participant_ids = {gp.participant_id for gp in game_participants}
        
        # Validate all participants are in this game
        for result in results_data.results:
            if result.participant_id not in participant_ids:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Participant {result.participant_id} is not in this game"
                )
        
        # Update results for each participant
        updated_count = 0
        for result in results_data.results:
            # Find the game participant record
            game_participant = next(
                (gp for gp in game_participants if gp.participant_id == result.participant_id),
                None
            )
            
            if game_participant:
                from schemas.tournament import GameParticipantUpdate
                update_data = GameParticipantUpdate(
                    points=result.points
                )
                update_game_result(db, game_participant.id, update_data)
                
                # Update participant's total score
                update_participant_total_score(db, result.participant_id)
                updated_count += 1
        
        # Mark game as completed if all participants have results
        if len(results_data.results) == len(game_participants):
            game.status = GameStatus.COMPLETED
            game.finished_at = func.now()
            db.commit()
        
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
    try:
        # Validate game exists
        game = get_tournament_game(db, game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Validate tournament creator
        tournament = validate_tournament_exists(db, game.tournament_id)
        validate_tournament_creator(tournament, current_user.id, "clear game results")
        
        # Check if game is completed
        if game.status == GameStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Cannot clear results of completed game")
        
        # Get game participants and clear their results
        game_participants = get_game_participants(db, game_id)
        cleared_count = 0
        
        for game_participant in game_participants:
            if game_participant.points is not None:
                game_participant.points = None
                cleared_count += 1
                
                # Recalculate participant's total score
                update_participant_total_score(db, game_participant.participant_id)
        
        # Reset game status
        game.status = GameStatus.PENDING
        game.finished_at = None
        
        db.commit()
        
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
    try:
        # Validate game exists
        game = get_tournament_game(db, game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Validate tournament creator
        tournament = validate_tournament_exists(db, game.tournament_id)
        validate_tournament_creator(tournament, current_user.id, "submit participant result")
        
        # Check if game is completed
        if game.status == GameStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Cannot modify results of completed game")
        
        # Validate participant_id matches the one in URL
        if result.participant_id != participant_id:
            raise HTTPException(status_code=400, detail="Participant ID mismatch")
        
        # Find game participant
        game_participants = get_game_participants(db, game_id)
        game_participant = next(
            (gp for gp in game_participants if gp.participant_id == participant_id),
            None
        )
        
        if not game_participant:
            raise HTTPException(status_code=404, detail="Participant not found in this game")
        
        # No position validation needed since we only use points
        
        # Update participant result
        from schemas.tournament import GameParticipantUpdate
        update_data = GameParticipantUpdate(
            points=result.points
        )
        update_game_result(db, game_participant.id, update_data)
        
        # Recalculate participant's total score
        update_participant_total_score(db, participant_id)
        
        # Check if all participants have results and mark game as completed
        all_have_results = all(
            gp.points is not None 
            for gp in get_game_participants(db, game_id)
        )
        
        if all_have_results:
            game.status = GameStatus.COMPLETED
            game.finished_at = func.now()
        
        db.commit()
        
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
    try:
        # Validate game exists
        game = get_tournament_game(db, game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Validate tournament creator
        tournament = validate_tournament_exists(db, game.tournament_id)
        validate_tournament_creator(tournament, current_user.id, "clear participant result")
        
        # Check if game is completed
        if game.status == GameStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Cannot clear results of completed game")
        
        # Find and clear participant result
        game_participants = get_game_participants(db, game_id)
        game_participant = next(
            (gp for gp in game_participants if gp.participant_id == participant_id),
            None
        )
        
        if not game_participant:
            raise HTTPException(status_code=404, detail="Participant not found in this game")
        
        game_participant.points = None
        
        # Recalculate participant's total score
        update_participant_total_score(db, participant_id)
        
        db.commit()
        
        return {
            "message": "Participant result cleared",
            "game_id": game_id,
            "participant_id": participant_id
        }
        
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
    try:
        import json
        
        # Validate positions
        if not positions or len(positions) > 8:
            raise HTTPException(status_code=400, detail="Positions must be 1-8 items")
        
        for pos in positions:
            if not (1 <= pos <= 8):
                raise HTTPException(status_code=400, detail="All positions must be between 1-8")
        
        # Check consecutive if multiple positions
        if len(positions) > 1:
            sorted_pos = sorted(positions)
            for i in range(1, len(sorted_pos)):
                if sorted_pos[i] != sorted_pos[i-1] + 1:
                    raise HTTPException(status_code=400, detail="Shared positions must be consecutive")
        
        game = get_tournament_game(db, game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        tournament = validate_tournament_exists(db, game.tournament_id)
        validate_tournament_creator(tournament, current_user.id, "submit participant position")
        
        game_participants = get_game_participants(db, game_id)
        game_participant = next(
            (gp for gp in game_participants if gp.participant_id == participant_id), None
        )
        
        if not game_participant:
            raise HTTPException(status_code=404, detail="Participant not found in this game")
        
        # Calculate points and update
        calculated_points = calculate_points_from_positions(positions)
        game_participant.positions = json.dumps(sorted(positions))
        game_participant.calculated_points = calculated_points
        game_participant.points = int(calculated_points)
        
        # Check if all participants have positions
        all_have_positions = all(
            gp.positions is not None for gp in get_game_participants(db, game_id)
        )
        
        if all_have_positions:
            game.status = GameStatus.COMPLETED
            game.finished_at = func.now()
        
        # Commit changes first before recalculating total score
        db.commit()
        
        # Now recalculate total score after commit
        update_participant_total_score(db, participant_id)
        
        return {
            "message": "Position submitted successfully",
            "game_id": game_id,
            "participant_id": participant_id,
            "positions": sorted(positions),
            "calculated_points": calculated_points,
            "game_completed": all_have_positions
        }
        
    except TournamentException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")