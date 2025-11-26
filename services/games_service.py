from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
import json

from models.user import User
from models.tournament import Tournament, TournamentStatus
from models.tournament_game import TournamentGame, GameStatus
from models.tournament_participant import TournamentParticipant
from models.game_participant import GameParticipant
from core.roles import UserRole
from core.exceptions import TournamentException
from api.crud.game_crud import (
    get_tournament_game, update_game_result, get_game_participants,
    get_round_games
)
from api.crud.participant_crud import update_participant_total_score
from schemas.game_results import GameResultsSubmission, GameResultInput
from schemas.tournament import GameParticipantUpdate
from schemas.game_results_v2 import calculate_points_from_positions


def validate_tournament_not_finished(tournament: Tournament):
    """Перевірка що турнір не завершений"""
    if tournament.status == TournamentStatus.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify results - tournament is already finished"
        )



def validate_lobby_maker_assigned(game: TournamentGame):
    """Перевірка що Lobby Maker призначений"""
    if not game.lobby_maker_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit results: Lobby Maker not assigned"
        )

def can_submit_game_results(db: Session, game_id: int, tournament_id: int, user: User) -> bool:
    """
    Перевірка чи користувач може встановлювати результати гри.
    Дозволено:
    - Учасникам цієї гри
    - Створювачу турніру
    - Адмінам та супер-адмінам
    """
    # Адміни та супер-адміни можуть все
    if user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        return True
    
    # Перевірити чи користувач - створювач турніру
    tournament = db.query(Tournament).filter_by(id=tournament_id).first()
    if tournament and tournament.creator_id == user.id:
        return True
    
    # Перевірити чи користувач - учасник цієї гри
    game_participants = get_game_participants(db, game_id)
    for gp in game_participants:
        participant = db.query(TournamentParticipant).filter_by(id=gp.participant_id).first()
        if participant and participant.user_id == user.id:
            return True
    
    return False


def submit_game_results_logic(
    db: Session,
    game_id: int,
    results_data: GameResultsSubmission,
    user: User,
    tournament: Tournament
):
    if not can_submit_game_results(db, game_id, tournament.id, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to submit results for this game"
        )
    
    game = get_tournament_game(db, game_id)
    validate_lobby_maker_assigned(game)
    
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
            update_data = GameParticipantUpdate(
                points=result.points
            )
            update_game_result(db, game_participant.id, update_data)
            
            # Update participant's total score
            update_participant_total_score(db, result.participant_id)
            updated_count += 1
    
    # Mark game as completed if all participants have results
    game = get_tournament_game(db, game_id)
    if len(results_data.results) == len(game_participants):
        game.status = GameStatus.COMPLETED
        game.finished_at = func.now()
        db.commit()
    
    return updated_count


def clear_game_results_logic(
    db: Session,
    game_id: int,
    game: TournamentGame
):
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
    
    return cleared_count


def submit_participant_result_logic(
    db: Session,
    game_id: int,
    participant_id: int,
    result: GameResultInput,
    user: User,
    tournament: Tournament,
    game: TournamentGame
):
    if not can_submit_game_results(db, game_id, tournament.id, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to submit results for this game"
        )

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
    
    # Update participant result
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
    
    return all_have_results


def clear_participant_result_logic(
    db: Session,
    game_id: int,
    participant_id: int,
    game: TournamentGame
):
    # Check if tournament is finished (already checked in router, but good to keep in mind)
    # We allow modifying completed games as long as the tournament/round isn't closed
    
    # If game was completed, we'll need to reopen it
    if game.status == GameStatus.COMPLETED:
        game.status = GameStatus.ACTIVE
        game.finished_at = None
    
    # Find and clear participant result
    game_participants = get_game_participants(db, game_id)
    game_participant = next(
        (gp for gp in game_participants if gp.participant_id == participant_id),
        None
    )
    
    if not game_participant:
        raise HTTPException(status_code=404, detail="Participant not found in this game")
    
    # Clear all result fields
    game_participant.points = None
    game_participant.positions = None
    game_participant.calculated_points = None
    
    # Mark as modified
    from sqlalchemy.orm import attributes
    attributes.flag_modified(game_participant, "positions")
    attributes.flag_modified(game_participant, "calculated_points")
    
    # Recalculate participant's total score
    update_participant_total_score(db, participant_id)
    
    db.commit()


def submit_positions_batch_logic(
    db: Session,
    game_id: int,
    updates: List[dict],
    user: User,
    tournament: Tournament,
    game: TournamentGame
):
    if not can_submit_game_results(db, game_id, tournament.id, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to submit results for this game"
        )

        
    validate_lobby_maker_assigned(game)
    
    # First, validate all positions for conflicts
    # Build a map of participant_id -> positions from updates
    update_map = {}
    for update in updates:
        participant_id = update.get("participant_id")
        positions = update.get("positions", update.get("position", []))
        
        if participant_id and positions:
            update_map[participant_id] = positions
    
    # Check for conflicts between updates and existing positions
    for participant_id, new_positions in update_map.items():
        validate_position_conflicts(db, game_id, participant_id, new_positions)
    
    # Check for conflicts within the batch itself
    all_positions_in_batch = {}
    for participant_id, positions in update_map.items():
        for pos in positions:
            if pos in all_positions_in_batch:
                # Get participant info for error message
                other_participant_id = all_positions_in_batch[pos]
                p1 = db.query(TournamentParticipant).filter_by(id=participant_id).first()
                p2 = db.query(TournamentParticipant).filter_by(id=other_participant_id).first()
                
                battletag1 = p1.user.battletag if p1 and p1.user else "Unknown"
                battletag2 = p2.user.battletag if p2 and p2.user else "Unknown"
                
                raise HTTPException(
                    status_code=400,
                    detail=f"Position conflict in batch: Position {pos} assigned to both {battletag1} and {battletag2}"
                )
            all_positions_in_batch[pos] = participant_id
        
    updated_count = 0
    
    for update in updates:
        participant_id = update.get("participant_id")
        positions = update.get("positions", update.get("position", []))
        
        if not participant_id or not positions:
            continue
        
        # Find game participant
        game_participants = get_game_participants(db, game_id)
        game_participant = next(
            (gp for gp in game_participants if gp.participant_id == participant_id), None
        )
        
        if not game_participant:
            continue
        
        # Calculate and update
        calculated_points = calculate_points_from_positions(positions)
        game_participant.positions = json.dumps(sorted(positions))
        game_participant.calculated_points = calculated_points
        game_participant.points = int(calculated_points)
        
        from sqlalchemy.orm import attributes
        attributes.flag_modified(game_participant, "positions")
        attributes.flag_modified(game_participant, "calculated_points")
        attributes.flag_modified(game_participant, "points")
        
        updated_count += 1
    
    # Check if all participants have positions
    all_have_positions = all(
        gp.positions is not None for gp in get_game_participants(db, game_id)
    )
    
    if all_have_positions:
        game.status = GameStatus.COMPLETED
        game.finished_at = func.now()
    
    db.commit()
    
    # Update total scores for all updated participants
    for update in updates:
        participant_id = update.get("participant_id")
        if participant_id:
            update_participant_total_score(db, participant_id)
            
    return updated_count, all_have_positions


def validate_position_conflicts(
    db: Session,
    game_id: int,
    participant_id: int,
    new_positions: List[int]
) -> None:
    """
    Validate that new positions don't conflict with existing positions in the game.
    Rules:
    - Each position (1-8) can only be occupied once UNLESS it's part of a shared group
    - Shared positions like [2,3] can be used max 2 times (size of group)
    - Shared positions like [2,3,4] can be used max 3 times
    - Different groups cannot overlap (if [2] is taken, [2,3] cannot be used)
    """
    game_participants = get_game_participants(db, game_id)
    new_positions_tuple = tuple(sorted(new_positions))
    
    # Count how many times each position group is used
    position_groups = {}  # {(2,3): count, (5,): count}
    
    # Track individual positions and their groups
    position_to_groups = {}  # {2: [(2,3)], 5: [(5,)]}
    
    for gp in game_participants:
        # Skip the participant we're updating
        if gp.participant_id == participant_id:
            continue
            
        # Skip participants without positions
        if not gp.positions:
            continue
            
        try:
            existing_positions = json.loads(gp.positions)
            existing_tuple = tuple(sorted(existing_positions))
            
            # Count this group
            position_groups[existing_tuple] = position_groups.get(existing_tuple, 0) + 1
            
            # Track which positions belong to which groups
            for pos in existing_positions:
                if pos not in position_to_groups:
                    position_to_groups[pos] = []
                position_to_groups[pos].append(existing_tuple)
                
        except json.JSONDecodeError:
            continue
    
    # Check if new positions conflict
    # Rule 1: Check if any position in new_positions is already used in a DIFFERENT group
    for pos in new_positions:
        if pos in position_to_groups:
            for existing_group in position_to_groups[pos]:
                if existing_group != new_positions_tuple:
                    # This position is used in a different group - conflict!
                    participant = db.query(TournamentParticipant).join(
                        GameParticipant, GameParticipant.participant_id == TournamentParticipant.id
                    ).filter(
                        GameParticipant.game_id == game_id,
                        GameParticipant.positions == json.dumps(list(existing_group))
                    ).first()
                    
                    battletag = participant.user.battletag if participant and participant.user else "Unknown"
                    
                    raise HTTPException(
                        status_code=400,
                        detail=f"Position conflict: Position {pos} is already used in group {list(existing_group)} by {battletag}. Cannot use in group {new_positions}."
                    )
    
    # Rule 2: Check if this exact group is already used max times
    current_count = position_groups.get(new_positions_tuple, 0)
    max_allowed = len(new_positions)  # Group of 2 can be used 2 times, group of 3 can be used 3 times
    
    if current_count >= max_allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Position group {new_positions} can only be used {max_allowed} times. Already used {current_count} times."
        )


def submit_participant_position_logic(
    db: Session,
    game_id: int,
    participant_id: int,
    positions: List[int],
    user: User,
    tournament: Tournament,
    game: TournamentGame
):
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
    
    # Validate position conflicts
    validate_position_conflicts(db, game_id, participant_id, positions)
    
    if not can_submit_game_results(db, game_id, tournament.id, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to submit results for this game. Only game participants, tournament creator, or admins can submit results."

        )
    
    validate_lobby_maker_assigned(game)
    
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
    
    # Mark as modified to ensure SQLAlchemy tracks the change
    from sqlalchemy.orm import attributes
    attributes.flag_modified(game_participant, "positions")
    attributes.flag_modified(game_participant, "calculated_points")
    attributes.flag_modified(game_participant, "points")
    
    # Check if all participants have positions
    all_have_positions = all(
        gp.positions is not None for gp in get_game_participants(db, game_id)
    )
    
    if all_have_positions:
        game.status = GameStatus.COMPLETED
        game.finished_at = func.now()
    
    # Commit changes first before recalculating total score
    db.commit()
    db.refresh(game_participant)
    
    # Now recalculate total score after commit
    update_participant_total_score(db, participant_id)
    
    return sorted(positions), calculated_points, all_have_positions


def assign_lobby_maker_logic(
    db: Session,
    game_id: int,
    participant_id: int,
    user: User,
    tournament: Tournament
):
    """Assign a lobby maker to a game"""
    # Validate permissions (creator or admin)
    is_admin = user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
    is_creator = tournament.creator_id == user.id
    
    if not (is_admin or is_creator):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tournament creator or admin can assign Lobby Maker"
        )
    
    game = get_tournament_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
        
    # Validate participant is in the game
    game_participants = get_game_participants(db, game_id)
    target_gp = next(
        (gp for gp in game_participants if gp.participant_id == participant_id),
        None
    )
    
    if not target_gp:
        raise HTTPException(status_code=400, detail="Participant is not in this game")
        
    # Find user_id of the participant
    participant = db.query(TournamentParticipant).filter_by(id=participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
        
    # Update game lobby maker
    game.lobby_maker_id = participant.user_id
    
    # Update is_lobby_maker flag for all participants
    for gp in game_participants:
        gp.is_lobby_maker = (gp.participant_id == participant_id)
        
    db.commit()
    db.refresh(game)
    
    return {
        "game_id": game_id,
        "lobby_maker_id": participant.user_id,
        "participant_id": participant_id,
        "message": "Lobby Maker assigned successfully"
    }


def remove_lobby_maker_logic(
    db: Session,
    game_id: int,
    user: User,
    tournament: Tournament
):
    """Remove lobby maker from a game"""
    # Validate permissions (creator or admin)
    is_admin = user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
    is_creator = tournament.creator_id == user.id
    
    if not (is_admin or is_creator):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tournament creator or admin can remove Lobby Maker"
        )
    
    game = get_tournament_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Check if any results have been submitted
    game_participants = get_game_participants(db, game_id)
    has_results = any(gp.positions is not None for gp in game_participants)
    
    if has_results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove Lobby Maker: results have already been submitted"
        )
        
    game.lobby_maker_id = None
    
    # Reset is_lobby_maker flag
    for gp in game_participants:
        gp.is_lobby_maker = False
        
    db.commit()
    
    return {"message": "Lobby Maker removed successfully"}


def get_lobby_maker_logic(
    db: Session,
    game_id: int
):
    """Get current lobby maker"""
    game = get_tournament_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
        
    if not game.lobby_maker_id:
        return None
        
    user = db.query(User).filter_by(id=game.lobby_maker_id).first()
    return user
