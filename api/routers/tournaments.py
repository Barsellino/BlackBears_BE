from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
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
    TournamentParticipant, LobbyMakerPriorityUpdate, TournamentStatus
)
from core.auth import get_current_active_user, get_current_user_optional
from core.roles import UserRole
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
    status: Optional[List[TournamentStatus]] = Query(None, description="Filter by tournament status"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get list of all tournaments"""
    tournaments = get_tournaments(db, skip=skip, limit=limit, status=status)
    
    # Add my_status for each tournament if user is authenticated
    if current_user:
        from models.tournament_participant import TournamentParticipant
        from models.tournament import TournamentStatus as ModelTournamentStatus
        
        for tournament in tournaments:
            participant = db.query(TournamentParticipant).filter(
                TournamentParticipant.tournament_id == tournament.id,
                TournamentParticipant.user_id == current_user.id
            ).first()
            
            if participant:
                if tournament.status == ModelTournamentStatus.REGISTRATION:
                    tournament.my_status = "registered"
                elif tournament.status == ModelTournamentStatus.ACTIVE:
                    tournament.my_status = "playing"
                elif tournament.status == ModelTournamentStatus.FINISHED:
                    tournament.my_status = "finished"
                    
                    # Check if tournament had finals and user participated in them
                    if tournament.with_finals and tournament.finals_started:
                        # Check if user was in finals (top N by total_score)
                        top_participants = db.query(TournamentParticipant).filter(
                            TournamentParticipant.tournament_id == tournament.id
                        ).order_by(TournamentParticipant.total_score.desc()).limit(tournament.finals_participants_count).all()
                        
                        top_user_ids = [p.user_id for p in top_participants]
                        if current_user.id in top_user_ids:
                            # User was in finals - show finals position
                            finalists_sorted = sorted(top_participants, key=lambda p: -p.finals_score)
                            for i, p in enumerate(finalists_sorted, 1):
                                if p.user_id == current_user.id:
                                    tournament.my_result = i
                                    tournament.was_in_finals = True
                                    break
                        else:
                            # User was NOT in finals - show regular position
                            if participant.final_position:
                                tournament.my_result = participant.final_position
                            tournament.was_in_finals = False
                    else:
                        # No finals - show regular position
                        if participant.final_position:
                            tournament.my_result = participant.final_position
                else:
                    tournament.my_status = "registered"
            else:
                tournament.my_status = None
    else:
        for tournament in tournaments:
            tournament.my_status = None
    
    return tournaments


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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get tournament details with participants"""
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    # Check if user has access to sensitive data
    has_full_access = False
    import logging
    logger = logging.getLogger(__name__)
    
    if current_user:
        # Порівнюємо enum значення правильно
        is_admin = current_user.role == UserRole.ADMIN or current_user.role == UserRole.SUPER_ADMIN
        is_creator = tournament.creator_id == current_user.id
        has_full_access = is_admin or is_creator
        # Логування для діагностики
        logger.info(f"get_tournament_details: current_user_id={current_user.id}, current_user_role={current_user.role}, current_user_role_value={current_user.role.value if hasattr(current_user.role, 'value') else current_user.role}, tournament_creator_id={tournament.creator_id}, is_admin={is_admin}, is_creator={is_creator}, has_full_access={has_full_access}")
    else:
        logger.info(f"get_tournament_details: current_user is None (no token or invalid token)")
        
    # Calculate finalist status (already done in get_tournament, but ensure it's set)
    from api.crud.tournament_crud import _calculate_finalist_status
    original_finalist_ids, actual_finalist_ids = _calculate_finalist_status(db, tournament)
        
    # Populate participant details
    for participant in tournament.participants:
        # Перевіряємо, чи user завантажений
        if not participant.user:
            # Якщо user не завантажений, завантажуємо його
            from models.user import User as UserModel
            participant.user = db.query(UserModel).filter(UserModel.id == participant.user_id).first()
        
        if participant.user:
            # Always set public info
            participant.battletag = participant.user.battletag
            participant.name = participant.user.name
            
            # Mark finalist status (only for tournaments with finals)
            if tournament.with_finals and tournament.finals_started:
                participant.was_original_finalist = participant.id in original_finalist_ids
                participant.is_swapped_finalist = (
                    participant.id in actual_finalist_ids and
                    participant.id not in original_finalist_ids
                )
                participant.plays_in_finals = participant.id in actual_finalist_ids
            else:
                participant.was_original_finalist = False
                participant.is_swapped_finalist = False
                participant.plays_in_finals = False
            
            # Set sensitive data (phone, telegram, rating)
            # Show for admin/creator (full access) or for user's own participant
            is_own_participant = current_user and participant.user_id == current_user.id
            if has_full_access or is_own_participant:
                participant.phone = participant.user.phone
                participant.telegram = participant.user.telegram
                participant.battlegrounds_rating = participant.user.battlegrounds_rating
                # Логування для діагностики
                logger.info(f"get_tournament_details: participant_id={participant.id}, user_id={participant.user_id}, phone={participant.user.phone}, telegram={participant.user.telegram}, has_full_access={has_full_access}, is_own_participant={is_own_participant}")
            else:
                # Explicitly set to None if no access (for security)
                participant.phone = None
                participant.telegram = None
                participant.battlegrounds_rating = None
                logger.info(f"get_tournament_details: participant_id={participant.id}, user_id={participant.user_id}, NO ACCESS - phone/telegram set to None, has_full_access={has_full_access}, is_own_participant={is_own_participant}")
        else:
            # Якщо user не знайдено, встановлюємо всі поля в None
            participant.battletag = None
            participant.name = None
            participant.phone = None
            participant.telegram = None
            participant.battlegrounds_rating = None
    
    # Add finals participants if finals started
    if tournament.with_finals and tournament.finals_started:
        from api.crud.participant_crud import get_finals_leaderboard
        finals_participants = get_finals_leaderboard(db, tournament_id)
        for p in finals_participants:
            p.battletag = p.user.battletag if p.user else None
            p.name = p.user.name if p.user else None
        tournament.finals = finals_participants
    else:
        tournament.finals = None
    
    # Add format info
    tournament.format = {
        "regular_rounds": tournament.regular_rounds or tournament.total_rounds,
        "final_rounds": tournament.finals_games_count if tournament.with_finals else 0,
        "finals_participants": tournament.finals_participants_count if tournament.with_finals else 0
    }
            
    return tournament


@router.put("/{tournament_id}", response_model=Tournament)
async def update_tournament_details(
    tournament_id: int,
    tournament_update: TournamentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update tournament (creator or super_admin can update)"""
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    is_super_admin = current_user.role == UserRole.SUPER_ADMIN
    if tournament.creator_id != current_user.id and not is_super_admin:
        raise HTTPException(status_code=403, detail="Only tournament creator or super admin can update")
    
    updated_tournament = update_tournament(db, tournament_id, tournament_update)
    return updated_tournament


@router.delete("/{tournament_id}")
async def delete_tournament_endpoint(
    tournament_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete tournament (creator or super_admin can delete)"""
    from api.crud.tournament_crud import delete_tournament
    
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    # Check permissions: creator or super_admin
    is_super_admin = current_user.role == UserRole.SUPER_ADMIN
    if tournament.creator_id != current_user.id and not is_super_admin:
        raise HTTPException(
            status_code=403,
            detail="Only tournament creator or super admin can delete tournament"
        )
    
    # Delete tournament
    success = delete_tournament(db, tournament_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete tournament")
    
    return {"message": "Tournament deleted successfully"}


@router.put("/{tournament_id}/lobby-makers/priority", response_model=List[int])
async def update_lobby_maker_priority(
    tournament_id: int,
    priority_data: LobbyMakerPriorityUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update lobby maker priority list (creator or super_admin)"""
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    is_super_admin = current_user.role == UserRole.SUPER_ADMIN
    if tournament.creator_id != current_user.id and not is_super_admin:
        raise HTTPException(status_code=403, detail="Only tournament creator or super admin can update priority list")
    
    # Validate that all user_ids exist
    for user_id in priority_data.priority_list:
        validate_user_exists(db, user_id)
    
    tournament.lobby_maker_priority_list = priority_data.priority_list
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(tournament, "lobby_maker_priority_list")
    
    db.commit()
    db.refresh(tournament)
    
    return tournament.lobby_maker_priority_list or []


@router.get("/{tournament_id}/lobby-makers/priority", response_model=List[int])
async def get_lobby_maker_priority(
    tournament_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get lobby maker priority list"""
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    return tournament.lobby_maker_priority_list or []


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
        
        # Log the action
        from services.tournament_manager import log_tournament_action
        log_tournament_action(
            db, 
            tournament_id, 
            current_user.id, 
            "participant_joined",
            f"joined tournament {tournament.name}"
        )
        
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
    
    from models.tournament import TournamentStatus as ModelTournamentStatus
    if tournament.status != ModelTournamentStatus.REGISTRATION:
        raise HTTPException(status_code=400, detail="Cannot leave tournament after registration closes")
    
    success = leave_tournament(db, tournament_id, current_user.id)
    if not success:
        raise HTTPException(status_code=400, detail="Not participating in this tournament")
    
    # Log the action
    from services.tournament_manager import log_tournament_action
    log_tournament_action(
        db, 
        tournament_id, 
        current_user.id, 
        "participant_left",
        f"left tournament {tournament.name}"
    )
    
    return {"message": "Successfully left tournament"}


@router.post("/{tournament_id}/auto-fill")
async def auto_fill_tournament(
    tournament_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Auto-fill tournament with random users (for testing, creator or super_admin only)"""
    from models.user import User as UserModel
    from models.tournament_participant import TournamentParticipant as ParticipantModel
    
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    # Only creator or super_admin
    is_super_admin = current_user.role == UserRole.SUPER_ADMIN
    if tournament.creator_id != current_user.id and not is_super_admin:
        raise HTTPException(status_code=403, detail="Only creator or super admin can auto-fill")
    
    # Get current participants count
    current_count = len(get_tournament_participants(db, tournament_id))
    needed = tournament.total_participants - current_count
    
    if needed <= 0:
        return {"message": "Tournament is already full", "added": 0}
    
    # Get random users who are not already in tournament
    existing_user_ids = [p.user_id for p in tournament.participants]
    existing_user_ids.append(tournament.creator_id)  # Exclude creator too
    
    available_users = db.query(UserModel).filter(
        UserModel.id.notin_(existing_user_ids),
        UserModel.is_active == True
    ).limit(needed).all()
    
    added = 0
    for user in available_users:
        participant = ParticipantModel(
            tournament_id=tournament_id,
            user_id=user.id,
            total_score=0,
            finals_score=0
        )
        db.add(participant)
        added += 1
    
    db.commit()
    
    return {
        "message": f"Added {added} participants",
        "added": added,
        "total": current_count + added,
        "needed": tournament.total_participants
    }


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


@router.get("/{tournament_id}/finals-leaderboard", response_model=List[TournamentParticipant])
async def get_finals_leaderboard_endpoint(
    tournament_id: int,
    db: Session = Depends(get_db)
):
    """Get finals leaderboard (only top participants, sorted by finals_score)"""
    from api.crud.participant_crud import get_finals_leaderboard
    
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    if not tournament.with_finals:
        raise HTTPException(status_code=400, detail="Tournament doesn't have finals")
    
    if not tournament.finals_started:
        raise HTTPException(status_code=400, detail="Finals haven't started yet")
    
    return get_finals_leaderboard(db, tournament_id)


@router.get("/{tournament_id}/finals/candidates", response_model=List[TournamentParticipant])
async def get_finals_candidates_endpoint(
    tournament_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Отримати список учасників турніру, які не потрапили у фінали (кандидати для заміни).
    
    Доступ:
    - створювач турніру
    - SUPER_ADMIN
    """
    from api.crud.participant_crud import get_finals_candidates

    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    if not tournament.with_finals:
        raise HTTPException(status_code=400, detail="Tournament doesn't have finals")

    # Якщо фінали ще не згенеровані/не стартували — теж помилка
    if not tournament.finals_started:
        raise HTTPException(status_code=400, detail="Finals haven't been generated yet")

    # Доступ тільки для creator або SUPER_ADMIN (як для майбутнього свапу)
    is_super_admin = current_user.role == UserRole.SUPER_ADMIN
    is_creator = tournament.creator_id == current_user.id
    if not (is_creator or is_super_admin):
        raise HTTPException(
            status_code=403,
            detail="Only tournament creator or super admin can view finals candidates"
        )

    return get_finals_candidates(db, tournament_id)


class FinalsSwapRequest(BaseModel):
    """Запит на заміну фіналіста іншим гравцем."""
    from_participant_id: int  # поточний фіналіст, якого прибираємо
    to_participant_id: int    # кандидат з тих, хто не в фіналі


class ParticipantSwapRequest(BaseModel):
    """Запит на заміну учасника турніру іншим користувачем (до кінця першого раунду)."""
    from_user_id: int  # користувач, якого замінюємо
    to_user_id: int    # користувач, на якого замінюємо


@router.post("/{tournament_id}/finals/swap", response_model=TournamentParticipant)
async def swap_finalist_endpoint(
    tournament_id: int,
    swap_data: FinalsSwapRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Свапнути фіналіста на іншого гравця.
    
    Умови:
    - турнір має фінали (`with_finals == True`)
    - фінали вже згенеровані (`finals_started == True`)
    - жодна фінальна гра ще не має результатів (усі final GameParticipant.positions/points == null)
    - доступ мають тільки creator турніру або SUPER_ADMIN
    """
    from api.crud.participant_crud import get_finals_candidates
    from models.tournament_round import TournamentRound
    from models.tournament_game import TournamentGame, GameStatus
    from models.game_participant import GameParticipant
    from models.tournament_participant import TournamentParticipant as TPModel

    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    if not tournament.with_finals:
        raise HTTPException(status_code=400, detail="Tournament doesn't have finals")

    if not tournament.finals_started:
        raise HTTPException(status_code=400, detail="Finals haven't been generated yet")

    # Перевірка прав доступу
    is_super_admin = current_user.role == UserRole.SUPER_ADMIN
    is_creator = tournament.creator_id == current_user.id
    if not (is_creator or is_super_admin):
        raise HTTPException(
            status_code=403,
            detail="Only tournament creator or super admin can swap finalists"
        )

    # Знайти всі фінальні раунди (round_number > regular_rounds)
    regular_rounds = tournament.regular_rounds or tournament.total_rounds
    final_rounds = db.query(TournamentRound).filter(
        TournamentRound.tournament_id == tournament_id,
        TournamentRound.round_number > regular_rounds
    ).all()

    if not final_rounds:
        raise HTTPException(status_code=400, detail="Final rounds not found")

    final_round_ids = [r.id for r in final_rounds]

    # Отримати всі фінальні ігри
    final_games = db.query(TournamentGame).filter(
        TournamentGame.tournament_id == tournament_id,
        TournamentGame.round_id.in_(final_round_ids)
    ).all()

    if not final_games:
        raise HTTPException(status_code=400, detail="Final games not found")

    # Перевірити, що в жодній фінальній грі ще немає результатів
    any_results = db.query(GameParticipant).join(TournamentGame).filter(
        TournamentGame.id.in_([g.id for g in final_games]),
        (GameParticipant.positions.isnot(None)) | (GameParticipant.points.isnot(None))
    ).first()

    if any_results:
        raise HTTPException(
            status_code=400,
            detail="Cannot swap finalists: some final games already have results"
        )

    from_id = swap_data.from_participant_id
    to_id = swap_data.to_participant_id

    if from_id == to_id:
        raise HTTPException(status_code=400, detail="Cannot swap the same participant")

    # Перевірка, що обидва учасники належать цьому турніру
    from_participant = db.query(TPModel).filter(
        TPModel.id == from_id,
        TPModel.tournament_id == tournament_id
    ).first()

    to_participant = db.query(TPModel).filter(
        TPModel.id == to_id,
        TPModel.tournament_id == tournament_id
    ).first()

    if not from_participant or not to_participant:
        raise HTTPException(status_code=404, detail="Participants must belong to this tournament")

    # Перевірка, що from_participant зараз у фіналі (фактично грає у фінальних іграх)
    final_game_ids = [g.id for g in final_games]
    actual_finalist_rows = db.query(GameParticipant.participant_id).filter(
        GameParticipant.game_id.in_(final_game_ids)
    ).distinct().all()
    actual_finalist_ids = {row[0] for row in actual_finalist_rows}

    if from_id not in actual_finalist_ids:
        raise HTTPException(status_code=400, detail="from_participant is not in finals")

    # Перевірка, що to_participant НЕ в фіналі
    if to_id in actual_finalist_ids:
        raise HTTPException(status_code=400, detail="to_participant is already in finals")

    # Замінити from_participant на to_participant у всіх фінальних іграх
    for game in final_games:
        gp = db.query(GameParticipant).filter(
            GameParticipant.game_id == game.id,
            GameParticipant.participant_id == from_id
        ).first()

        if gp:
            gp.participant_id = to_id
            # is_lobby_maker залишаємо як є (якщо цей слот був лоббі мейкером)

    db.commit()

    # Логування дії
    from services.tournament_manager import log_tournament_action
    from_btag = from_participant.user.battletag if from_participant.user else "Unknown"
    to_btag = to_participant.user.battletag if to_participant.user else "Unknown"

    log_tournament_action(
        db,
        tournament_id,
        current_user.id,
        "finals_swap",
        f"swapped finalist {from_btag} (id={from_id}) with {to_btag} (id={to_id})"
    )

    # Повертаємо того, хто тепер став фіналістом (to_participant)
    return to_participant


@router.post("/{tournament_id}/swap-participant", response_model=TournamentParticipant)
async def swap_participant_endpoint(
    tournament_id: int,
    swap_data: ParticipantSwapRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Замінити учасника турніру іншим користувачем.
    
    Умови:
    - турнір має статус REGISTRATION або ACTIVE
    - якщо ACTIVE, то current_round == 1 і перший раунд ще не завершений
    - from_user_id має бути учасником турніру
    - to_user_id не має бути учасником турніру
    - доступ мають тільки creator турніру або SUPER_ADMIN
    """
    from models.tournament_round import TournamentRound, RoundStatus
    from models.tournament_game import TournamentGame, GameStatus
    from models.game_participant import GameParticipant
    from models.tournament_participant import TournamentParticipant as TPModel
    from models.user import User as UserModel
    from models.tournament import TournamentStatus as ModelTournamentStatus

    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    # Перевірка прав доступу
    is_super_admin = current_user.role == UserRole.SUPER_ADMIN
    is_creator = tournament.creator_id == current_user.id
    if not (is_creator or is_super_admin):
        raise HTTPException(
            status_code=403,
            detail="Only tournament creator or super admin can swap participants"
        )

    # Перевірка статусу турніру
    if tournament.status not in [ModelTournamentStatus.REGISTRATION, ModelTournamentStatus.ACTIVE]:
        raise HTTPException(
            status_code=400,
            detail="Can only swap participants in registration or active tournaments"
        )

    # Якщо турнір активний, перевіряємо, що це перший раунд і він ще не завершений
    first_round = None
    if tournament.status == ModelTournamentStatus.ACTIVE:
        if tournament.current_round != 1:
            raise HTTPException(
                status_code=400,
                detail="Can only swap participants before the end of the first round"
            )

        # Перевіряємо, що перший раунд існує і не завершений
        first_round = db.query(TournamentRound).filter(
            TournamentRound.tournament_id == tournament_id,
            TournamentRound.round_number == 1
        ).first()

        if not first_round:
            raise HTTPException(status_code=400, detail="First round not found")

        if first_round.status == RoundStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail="Cannot swap participants: first round is already completed"
            )

    from_user_id = swap_data.from_user_id
    to_user_id = swap_data.to_user_id

    if from_user_id == to_user_id:
        raise HTTPException(status_code=400, detail="Cannot swap the same user")

    # Перевірка, що from_user_id є учасником турніру
    from_participant = db.query(TPModel).filter(
        TPModel.tournament_id == tournament_id,
        TPModel.user_id == from_user_id
    ).first()

    if not from_participant:
        raise HTTPException(
            status_code=404,
            detail="from_user_id is not a participant in this tournament"
        )

    # Якщо турнір активний, перевіряємо, що в іграх цього конкретного учасника немає результатів
    if tournament.status == ModelTournamentStatus.ACTIVE and first_round:
        # Перевіряємо тільки GameParticipant для цього конкретного учасника в першому раунді
        import json
        participant_game_results = db.query(GameParticipant).join(TournamentGame).filter(
            GameParticipant.participant_id == from_participant.id,
            TournamentGame.tournament_id == tournament_id,
            TournamentGame.round_id == first_round.id
        ).all()
        
        for gp in participant_game_results:
            # Перевіряємо points (має бути None)
            if gp.points is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot swap participant: this participant already has results in the first round"
                )
            
            # Перевіряємо calculated_points (має бути None)
            if gp.calculated_points is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot swap participant: this participant already has results in the first round"
                )
            
            # Перевіряємо positions (має бути None або порожній JSON масив "[]")
            if gp.positions is not None and gp.positions.strip():
                try:
                    positions = json.loads(gp.positions)
                    # Якщо positions - це не порожній список, значить є результати
                    if isinstance(positions, list) and len(positions) > 0:
                        raise HTTPException(
                            status_code=400,
                            detail="Cannot swap participant: this participant already has results in the first round"
                        )
                except (json.JSONDecodeError, ValueError, TypeError):
                    # Якщо не вдалося розпарсити як JSON, але positions не порожній - вважаємо, що є результати
                    if gp.positions.strip() not in ['[]', 'null', '']:
                        raise HTTPException(
                            status_code=400,
                            detail="Cannot swap participant: this participant already has results in the first round"
                        )

    # Перевірка, що to_user_id не є учасником турніру
    to_participant_existing = db.query(TPModel).filter(
        TPModel.tournament_id == tournament_id,
        TPModel.user_id == to_user_id
    ).first()

    if to_participant_existing:
        raise HTTPException(
            status_code=400,
            detail="to_user_id is already a participant in this tournament"
        )

    # Перевірка, що to_user_id існує
    to_user = db.query(UserModel).filter(UserModel.id == to_user_id).first()
    if not to_user:
        raise HTTPException(status_code=404, detail="to_user_id not found")

    # Зберігаємо старого користувача для логування
    from_user = from_participant.user
    from_btag = from_user.battletag if from_user else "Unknown"

    # Замінюємо user_id у TournamentParticipant
    from_participant.user_id = to_user_id
    db.commit()

    # Якщо турнір активний (перший раунд вже створений), participant_id залишається той самий
    # бо ми змінили user_id у TournamentParticipant, тому GameParticipant автоматично
    # буде посилатися на нового користувача через зв'язок participant -> user

    # Логування дії
    from services.tournament_manager import log_tournament_action
    to_btag = to_user.battletag if to_user else "Unknown"

    # Оновлюємо зв'язок, щоб отримати новий user
    db.refresh(from_participant)

    log_tournament_action(
        db,
        tournament_id,
        current_user.id,
        "participant_swapped",
        f"swapped participant {from_btag} (user_id={from_user_id}) with {to_btag} (user_id={to_user_id})"
    )

    # Повертаємо оновлений participant
    return from_participant


@router.get("/{tournament_id}/swap-participant/candidates")
async def get_swap_participant_candidates(
    tournament_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Отримати список користувачів, яких можна використати для заміни учасника турніру.
    Повертає всіх користувачів, які НЕ є учасниками цього турніру.
    
    Доступ: тільки creator турніру або SUPER_ADMIN
    """
    from models.user import User as UserModel
    from models.tournament_participant import TournamentParticipant
    
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    # Перевірка прав доступу
    is_super_admin = current_user.role == UserRole.SUPER_ADMIN
    is_creator = tournament.creator_id == current_user.id
    if not (is_creator or is_super_admin):
        raise HTTPException(
            status_code=403,
            detail="Only tournament creator or super admin can view swap candidates"
        )

    # Отримуємо ID всіх учасників турніру
    participant_user_ids = db.query(TournamentParticipant.user_id).filter(
        TournamentParticipant.tournament_id == tournament_id
    ).all()
    participant_user_ids = {row[0] for row in participant_user_ids}

    # Отримуємо всіх користувачів, які НЕ є учасниками турніру
    candidates = db.query(UserModel).filter(
        UserModel.is_active == True,
        ~UserModel.id.in_(participant_user_ids) if participant_user_ids else True
    ).order_by(UserModel.battletag).all()

    # Формуємо відповідь
    result = [
        {
            "id": user.id,
            "battletag": user.battletag,
            "name": user.name,
            "battlegrounds_rating": user.battlegrounds_rating
        }
        for user in candidates
    ]

    return result


@router.post("/{tournament_id}/add-participant/{user_id}", response_model=TournamentParticipant)
async def add_participant_simple(
    tournament_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add participant to tournament (only creator or admin can do this)"""
    try:
        tournament = validate_tournament_exists(db, tournament_id)
        
        # Check permissions: only creator or admin
        is_admin = current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
        is_creator = tournament.creator_id == current_user.id
        if not (is_admin or is_creator):
            raise HTTPException(status_code=403, detail="Only tournament creator or admin can add participants")
        
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
        validate_tournament_creator(tournament, current_user.id, "add participants", current_user.role)
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
    """Manually remove participant from tournament (creator or super_admin)"""
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    is_super_admin = current_user.role == UserRole.SUPER_ADMIN
    if tournament.creator_id != current_user.id and not is_super_admin:
        raise HTTPException(status_code=403, detail="Only tournament creator or super admin can remove participants")
    
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
        validate_tournament_creator(tournament, current_user.id, "move participants", current_user.role)
        
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
        validate_tournament_creator(tournament, current_user.id, "start tournament", current_user.role)
        
        manager = TournamentManager(tournament)
        updated_tournament = manager.start_tournament(db)
        
        # Log the action
        from services.tournament_manager import log_tournament_action
        log_tournament_action(
            db, 
            tournament_id, 
            current_user.id, 
            "tournament_started",
            f"started tournament {tournament.name}"
        )
        
        # Send WebSocket notification
        from services.notification_service import notify_tournament_started
        import asyncio
        asyncio.create_task(notify_tournament_started(tournament_id, updated_tournament.current_round))
        
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
        validate_tournament_creator(tournament, current_user.id, "create next round", current_user.role)
        
        manager = TournamentManager(tournament)
        next_round = manager.create_next_round(db)
        
        # Log the action
        from services.tournament_manager import log_tournament_action
        is_final = tournament.finals_started and next_round.round_number > tournament.regular_rounds
        round_name = f"Final {next_round.round_number - tournament.regular_rounds}" if is_final else f"Round {next_round.round_number}"
        log_tournament_action(
            db, 
            tournament_id, 
            current_user.id, 
            "next_round_created",
            f"created {round_name}"
        )
        
        # Send WebSocket notification (with force_reload)
        from services.notification_service import notify_next_round_created
        from services.games_service import send_websocket_notification_async
        final_round_number = next_round.round_number - tournament.regular_rounds if is_final else None
        send_websocket_notification_async(
            notify_next_round_created,
            tournament_id=tournament_id,
            round_number=next_round.round_number,
            is_final=is_final,
            final_round_number=final_round_number,
            db=None
        )
        
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


@router.post("/{tournament_id}/start-finals")
async def start_finals_endpoint(
    tournament_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Start finals for a tournament (only creator can start)"""
    from models.tournament import Tournament as TournamentModel
    from models.tournament_participant import TournamentParticipant
    from api.crud.round_crud import create_round_with_games, start_round
    from models.game_participant import GameParticipant
    from api.crud.game_crud import get_round_games
    
    tournament = validate_tournament_exists(db, tournament_id)
    validate_tournament_creator(tournament, current_user.id, "start finals", current_user.role)
    
    # Validations
    if not tournament.with_finals:
        raise HTTPException(status_code=400, detail="Tournament doesn't have finals enabled")
    
    if tournament.finals_started:
        raise HTTPException(status_code=400, detail="Finals already started")
    
    if tournament.current_round < tournament.regular_rounds:
        raise HTTPException(
            status_code=400, 
            detail=f"Complete all regular rounds first. Current: {tournament.current_round}, Required: {tournament.regular_rounds}"
        )
    
    # Check if last regular round exists and all games are completed
    from models.tournament_round import TournamentRound, RoundStatus
    from models.tournament_game import GameStatus
    from api.crud.round_crud import complete_round
    
    last_round = db.query(TournamentRound).filter(
        TournamentRound.tournament_id == tournament_id,
        TournamentRound.round_number == tournament.regular_rounds
    ).first()
    
    if not last_round:
        raise HTTPException(status_code=400, detail="Last regular round not found")
    
    # Check if all games in last round have results
    from api.crud.game_crud import get_game_participants
    last_round_games = get_round_games(db, last_round.id)
    for game in last_round_games:
        if game.status != GameStatus.COMPLETED:
            # Check if all participants have results
            game_participants = get_game_participants(db, game.id)
            all_have_results = all(
                gp.points is not None or gp.calculated_points is not None 
                for gp in game_participants
            )
            if not all_have_results:
                raise HTTPException(
                    status_code=400, 
                    detail="All games in last round must have results before starting finals"
                )
    
    # Complete last round if not already completed
    if last_round.status != RoundStatus.COMPLETED:
        complete_round(db, last_round.id)
    
    # Get top N participants by total_score
    top_participants = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament_id
    ).order_by(TournamentParticipant.total_score.desc()).limit(tournament.finals_participants_count).all()
    
    if len(top_participants) < tournament.finals_participants_count:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough participants. Need {tournament.finals_participants_count}, have {len(top_participants)}"
        )
    
    # Update tournament
    tournament.total_rounds = tournament.regular_rounds + tournament.finals_games_count
    tournament.finals_started = True
    
    # Create first final round
    first_final_round_number = tournament.regular_rounds + 1
    new_round = create_round_with_games(
        db, 
        tournament_id, 
        first_final_round_number, 
        tournament.finals_participants_count
    )
    
    # Assign only top participants to games
    games = get_round_games(db, new_round.id)
    participants_per_game = 8
    
    for i, participant in enumerate(top_participants):
        game_index = i // participants_per_game
        if game_index < len(games):
            game_participant = GameParticipant(
                game_id=games[game_index].id,
                participant_id=participant.id
            )
            db.add(game_participant)
    
    db.flush()
    
    # Assign lobby makers
    from services.tournament_strategies import SwissStrategy
    strategy = SwissStrategy()
    strategy._assign_lobby_makers(db, new_round, tournament)
    
    # Start the round
    start_round(db, new_round.id)
    
    # Update current round
    tournament.current_round = first_final_round_number
    
    db.commit()
    
    # Log the action
    from services.tournament_manager import log_tournament_action
    log_tournament_action(
        db, 
        tournament_id, 
        current_user.id, 
        "finals_started",
        f"started finals with {len(top_participants)} participants"
    )
    
    # Send WebSocket notification (with force_reload)
    from services.notification_service import notify_next_round_created
    from services.games_service import send_websocket_notification_async
    send_websocket_notification_async(
        notify_next_round_created,
        tournament_id=tournament_id,
        round_number=first_final_round_number,
        is_final=True,
        final_round_number=1,  # First final round
        db=None
    )
    
    # Also send finals_started notification to finalists only
    from services.notification_service import notify_finals_started
    send_websocket_notification_async(
        notify_finals_started,
        tournament_id=tournament_id,
        current_round=first_final_round_number,
        finalists_count=len(top_participants),
        db=None
    )
    
    return {
        "message": "Finals started",
        "current_round": tournament.current_round,
        "total_rounds": tournament.total_rounds,
        "finals_participants": len(top_participants)
    }


@router.post("/{tournament_id}/finish")
async def finish_tournament_endpoint(
    tournament_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Finish tournament (only creator can finish)"""
    try:
        tournament = validate_tournament_exists(db, tournament_id)
        validate_tournament_creator(tournament, current_user.id, "finish tournament", current_user.role)
        
        manager = TournamentManager(tournament)
        finished_tournament = manager.finish_tournament(db)
        
        # Log the action
        from services.tournament_manager import log_tournament_action
        log_tournament_action(
            db, 
            tournament_id, 
            current_user.id, 
            "tournament_finished",
            f"finished tournament {tournament.name}"
        )
        
        # Send WebSocket notification (with force_reload)
        from services.notification_service import notify_tournament_finished
        from services.games_service import send_websocket_notification_async
        send_websocket_notification_async(
            notify_tournament_finished,
            tournament_id=tournament_id,
            db=None
        )
        
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


@router.get("/{tournament_id}/logs")
async def get_tournament_logs(
    tournament_id: int,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all logs for tournament (participants can view)"""
    from core.roles import UserRole
    from models.tournament_round import TournamentRound
    from models.tournament_game import TournamentGame
    from api.crud.game_log_crud import get_game_logs, get_game_logs_count
    from models.tournament_participant import TournamentParticipant
    
    tournament = get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    # Check permissions: admin, super_admin, or tournament participant
    is_admin = current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
    is_creator = tournament.creator_id == current_user.id
    is_participant = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament_id,
        TournamentParticipant.user_id == current_user.id
    ).first() is not None
    
    if not (is_admin or is_creator or is_participant):
        raise HTTPException(status_code=403, detail="Only tournament participants can view tournament logs")
    
    # Get all games for this tournament
    rounds = db.query(TournamentRound).filter(
        TournamentRound.tournament_id == tournament_id
    ).all()
    
    round_ids = [r.id for r in rounds]
    games = db.query(TournamentGame).filter(
        TournamentGame.round_id.in_(round_ids)
    ).all()
    
    game_ids = [g.id for g in games]
    
    if not game_ids:
        return {
            "logs": [],
            "total": 0,
            "skip": skip,
            "limit": limit
        }
    
    # Get all logs from all games
    from models.game_log import GameLog
    game_logs = []
    if game_ids:
        game_logs = db.query(GameLog).filter(
            GameLog.game_id.in_(game_ids)
        ).all()
    
    # Get tournament logs
    from models.tournament_log import TournamentLog
    tournament_logs = db.query(TournamentLog).filter(
        TournamentLog.tournament_id == tournament_id
    ).all()
    
    # Combine and sort by date
    all_logs = []
    for log in game_logs:
        all_logs.append({
            "type": "game",
            "id": log.id,
            "game_id": log.game_id,
            "user_battletag": log.user_battletag,
            "user_role": log.user_role,
            "action_type": log.action_type,
            "action_description": log.action_description,
            "created_at": log.created_at
        })
    
    for log in tournament_logs:
        all_logs.append({
            "type": "tournament",
            "id": log.id,
            "game_id": None,
            "user_battletag": log.user_battletag,
            "user_role": log.user_role,
            "action_type": log.action_type,
            "action_description": log.action_description,
            "created_at": log.created_at
        })
    
    # Sort by created_at DESC
    all_logs.sort(key=lambda x: x["created_at"], reverse=True)
    
    total = len(all_logs)
    
    # Apply pagination
    paginated_logs = all_logs[skip:skip + limit]
    
    return {
        "logs": [
            {
                "id": log["id"],
                "type": log["type"],
                "game_id": log["game_id"],
                "user_battletag": log["user_battletag"],
                "user_role": log["user_role"],
                "action_type": log["action_type"],
                "action_description": log["action_description"],
                "created_at": log["created_at"].isoformat() + "Z"
            }
            for log in paginated_logs
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{tournament_id}/status")
async def get_tournament_status_endpoint(
    tournament_id: int,
    db: Session = Depends(get_db)
):
    """Get tournament status and available actions"""
    tournament = validate_tournament_exists(db, tournament_id)
    manager = TournamentManager(tournament)
    return manager.get_tournament_status(db)


@router.get("/{tournament_id}/rounds/{round_number}/games")
async def get_round_games(
    tournament_id: int,
    round_number: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all games for a specific round (user's game first if participating)"""
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
    
    # Check if all games in current round are completed
    from models.tournament_game import GameStatus
    all_games_completed = all(
        game.status == GameStatus.COMPLETED and all(
            gp.positions is not None or (gp.points is not None and gp.points > 0)
            for gp in game.participants
        )
        for game in games
    )
    
    # Process games: add can_edit, is_my_game, and sort
    from models.tournament import TournamentStatus
    is_tournament_finished = tournament.status == TournamentStatus.FINISHED
    is_admin = current_user.role.value in ['admin', 'super_admin']
    is_creator = tournament.creator_id == current_user.id
    
    user_game = None
    other_games = []
    
    for game in games:
        # Check if user is participant
        participant_user_ids = [gp.user_id for gp in game.participants]
        is_my_game = current_user.id in participant_user_ids
        
        # Determine if user can edit this game
        can_edit = (
            not is_tournament_finished and 
            (is_admin or is_creator or is_my_game)
        )
        
        # Add computed fields to game
        game.can_edit = can_edit
        game.is_my_game = is_my_game
        
        # Ensure calculated_points is set for all participants
        for gp in game.participants:
            if not hasattr(gp, 'calculated_points') or gp.calculated_points is None:
                if gp.points is not None:
                    gp.calculated_points = float(gp.points)
        
        # Sort games
        if is_my_game:
            user_game = game
        else:
            other_games.append(game)
    
    # Prepare sorted games list
    sorted_games = [user_game] + other_games if user_game else games
    
    # Determine if this is a final round
    is_final = False
    final_round_number = None
    if tournament.finals_started and tournament.regular_rounds and round_number > tournament.regular_rounds:
        is_final = True
        final_round_number = round_number - tournament.regular_rounds
    
    # Return tournament info with games
    return {
        "tournament": {
            "id": tournament.id,
            "current_round": tournament.current_round,
            "total_rounds": tournament.total_rounds,
            "regular_rounds": tournament.regular_rounds,
            "status": tournament.status.value,
            "all_games_completed": all_games_completed,
            "with_finals": tournament.with_finals,
            "finals_started": tournament.finals_started,
            "finals_games_count": tournament.finals_games_count
        },
        "round": {
            "id": round_obj.id,
            "number": round_obj.round_number,
            "status": round_obj.status.value,
            "created_at": round_obj.created_at,
            "started_at": round_obj.started_at,
            "completed_at": round_obj.completed_at,
            "is_final": is_final,
            "final_round_number": final_round_number
        },
        "games": sorted_games
    }


@router.post("/{tournament_id}/test-next-round-notification")
async def test_next_round_notification(
    tournament_id: int,
    round_number: int = Query(3, description="Round number to test"),
    is_final: bool = Query(False, description="Is final round"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Тестовий ендпоінт для перевірки next_round_created повідомлення.
    Відправляє тестове WebSocket повідомлення без створення раунду.
    """
    # Перевірка, чи турнір існує
    tournament = validate_tournament_exists(db, tournament_id)
    
    # Перевірка, чи користувач є учасником або адміном
    from models.tournament_participant import TournamentParticipant
    participant = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament_id,
        TournamentParticipant.user_id == current_user.id
    ).first()
    
    if not participant and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a tournament participant or admin to test notifications"
        )
    
    # Відправка тестового повідомлення
    from services.notification_service import notify_next_round_created
    from services.games_service import send_websocket_notification_async
    
    final_round_number = round_number - tournament.regular_rounds if is_final and tournament.regular_rounds else None
    
    send_websocket_notification_async(
        notify_next_round_created,
        tournament_id=tournament_id,
        round_number=round_number,
        is_final=is_final,
        final_round_number=final_round_number,
        db=db
    )
    
    return {
        "message": "Test notification sent",
        "tournament_id": tournament_id,
        "round_number": round_number,
        "is_final": is_final,
        "force_reload": True
    }