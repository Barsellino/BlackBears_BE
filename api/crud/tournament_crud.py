from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from models.tournament import Tournament, TournamentStatus
from models.tournament_participant import TournamentParticipant
from schemas.tournament import TournamentCreate, TournamentUpdate


def _calculate_finalist_status(db: Session, tournament: Tournament) -> Tuple[set, set]:
    """
    Calculate original finalist IDs and actual finalist IDs for a tournament.
    Returns: (original_finalist_ids, actual_finalist_ids)
    """
    original_finalist_ids = set()
    actual_finalist_ids = set()
    
    if tournament.with_finals and tournament.finals_started:
        # Original finalists = top-N by total_score (before any swaps)
        finals_count = tournament.finals_participants_count or 8
        all_participants_sorted = sorted(
            tournament.participants,
            key=lambda p: p.total_score or 0,
            reverse=True
        )
        original_finalist_ids = {p.id for p in all_participants_sorted[:finals_count]}
        
        # Actual finalists = those who actually play in final games (after swaps)
        from models.tournament_round import TournamentRound
        from models.tournament_game import TournamentGame
        from models.game_participant import GameParticipant
        
        regular_rounds = tournament.regular_rounds or tournament.total_rounds
        final_rounds = db.query(TournamentRound).filter(
            TournamentRound.tournament_id == tournament.id,
            TournamentRound.round_number > regular_rounds
        ).all()
        
        if final_rounds:
            final_round_ids = [r.id for r in final_rounds]
            final_games = db.query(TournamentGame).filter(
                TournamentGame.tournament_id == tournament.id,
                TournamentGame.round_id.in_(final_round_ids)
            ).all()
            
            if final_games:
                final_game_ids = [g.id for g in final_games]
                finalist_rows = db.query(GameParticipant.participant_id).filter(
                    GameParticipant.game_id.in_(final_game_ids)
                ).distinct().all()
                actual_finalist_ids = {row[0] for row in finalist_rows}
    
    return original_finalist_ids, actual_finalist_ids


def create_tournament(db: Session, tournament: TournamentCreate, creator_id: int):
    tournament_data = tournament.dict()
    
    # Validate total_participants is divisible by 8
    total_participants = tournament_data['total_participants']
    if total_participants % 8 != 0:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Total participants must be divisible by 8 (got {total_participants})"
        )
    
    # Auto-calculate total_rounds if not provided
    if tournament_data.get('total_rounds') is None:
        import math
        participants = tournament_data['total_participants']
        tournament_data['total_rounds'] = math.ceil(math.log2(participants))
    
    # Store regular_rounds (original rounds before finals)
    tournament_data['regular_rounds'] = tournament_data['total_rounds']
    tournament_data['finals_started'] = False
    
    db_tournament = Tournament(
        **tournament_data,
        creator_id=creator_id
    )
    db.add(db_tournament)
    db.commit()
    return db_tournament


def get_tournament(db: Session, tournament_id: int):
    from sqlalchemy.orm import joinedload
    from models.tournament import TournamentStatus
    
    tournament = db.query(Tournament).options(
        joinedload(Tournament.creator),
        joinedload(Tournament.participants).joinedload(TournamentParticipant.user)
    ).filter(Tournament.id == tournament_id, Tournament.is_deleted == False).first()
    
    if tournament:
        tournament.occupied_slots = len(tournament.participants)
        tournament.creator_battletag = tournament.creator.battletag if tournament.creator else None

        # Populate winners for finished tournaments
        if tournament.status == TournamentStatus.FINISHED:
            # Filter out participants with no user
            valid_participants = [p for p in tournament.participants if p.user]
            
            # Sort by final_position (asc) then total_score (desc)
            sorted_participants = sorted(
                valid_participants,
                key=lambda p: (p.final_position if p.final_position is not None else 999, -p.total_score)
            )
            
            # Take top 3
            top_3 = sorted_participants[:3]
            
            # Use finals_score for tournaments with finals, total_score otherwise
            use_finals = tournament.with_finals and tournament.finals_started
            
            tournament.winners = [
                {
                    "user_id": p.user_id,
                    "battletag": p.user.battletag,
                    "final_position": p.final_position if p.final_position is not None else i+1,
                    "total_score": p.finals_score if use_finals else p.total_score
                }
                for i, p in enumerate(top_3)
            ]
        else:
            tournament.winners = []

        # Calculate finalist status
        original_finalist_ids, actual_finalist_ids = _calculate_finalist_status(db, tournament)
        
        # Add user info to participants and mark finalist status
        for participant in tournament.participants:
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
        
        # Sort participants based on tournament status
        if tournament.status == TournamentStatus.FINISHED:
            # Sort by final_position (ascending) - 1st place first
            tournament.participants.sort(
                key=lambda p: (p.final_position is None, p.final_position or 999)
            )
        elif tournament.status == TournamentStatus.ACTIVE:
            # Sort by total_score (descending) - highest score first
            tournament.participants.sort(
                key=lambda p: p.total_score or 0, 
                reverse=True
            )
        else:  # REGISTRATION or CANCELLED
            # Sort by joined_at (ascending) - first joined first
            tournament.participants.sort(
                key=lambda p: p.joined_at
            )
    
    return tournament


def get_tournaments(db: Session, skip: int = 0, limit: int = 100, status: List[TournamentStatus] = None):
    from sqlalchemy.orm import joinedload
    from sqlalchemy import case
    
    query = db.query(Tournament).options(
        joinedload(Tournament.creator),
        joinedload(Tournament.participants).joinedload(TournamentParticipant.user)
    ).filter(Tournament.is_deleted == False)
    
    if status:
        # Convert to model Enums to ensure compatibility
        model_statuses = []
        for s in status:
            try:
                # Get value whether it's an Enum or string
                val = s.value if hasattr(s, 'value') else s
                # Create model Enum from value
                model_statuses.append(TournamentStatus(val))
            except ValueError:
                continue
        
        if model_statuses:
            query = query.filter(Tournament.status.in_(model_statuses))
        
    # Sort by start_date (nulls last), then by created_at
    tournaments = query.order_by(
        case(
            (Tournament.start_date.is_(None), 1),
            else_=0
        ),
        Tournament.start_date.asc(),
        Tournament.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    for tournament in tournaments:
        tournament.occupied_slots = len(tournament.participants)
        tournament.creator_battletag = tournament.creator.battletag if tournament.creator else None
        
        # Populate winners for finished tournaments
        if tournament.status == TournamentStatus.FINISHED:
            # Filter out participants with no user (should not happen but safe check)
            valid_participants = [p for p in tournament.participants if p.user]
            
            # Sort by final_position (asc) then total_score (desc)
            # If final_position is None (not finished properly), put at end
            sorted_participants = sorted(
                valid_participants,
                key=lambda p: (p.final_position if p.final_position is not None else 999, -p.total_score)
            )
            
            # Take top 3
            top_3 = sorted_participants[:3]
            
            # Use finals_score for tournaments with finals, total_score otherwise
            use_finals = tournament.with_finals and tournament.finals_started
            
            tournament.winners = [
                {
                    "user_id": p.user_id,
                    "battletag": p.user.battletag,
                    "final_position": p.final_position if p.final_position is not None else i+1,
                    "total_score": p.finals_score if use_finals else p.total_score
                }
                for i, p in enumerate(top_3)
            ]
        else:
            tournament.winners = []
        
    return tournaments


def get_user_tournaments(db: Session, user_id: int):
    return db.query(Tournament).filter(Tournament.creator_id == user_id, Tournament.is_deleted == False).all()


def update_tournament(db: Session, tournament_id: int, tournament_update: TournamentUpdate):
    from fastapi import HTTPException
    
    db_tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not db_tournament:
        return None
    
    update_data = tournament_update.dict(exclude_unset=True)
    
    # Check if trying to update tournament structure (participants, rounds)
    structure_fields = ['total_participants', 'total_rounds']
    if any(field in update_data for field in structure_fields):
        # Only allow changes if tournament hasn't started yet
        if db_tournament.status != TournamentStatus.REGISTRATION:
            raise HTTPException(
                status_code=400,
                detail="Cannot change tournament structure (participants, rounds) after tournament has started"
            )
        
        # If changing total_participants, check if new value is valid
        if 'total_participants' in update_data:
            new_participants = update_data['total_participants']
            current_participants_count = len(db_tournament.participants)
            
            # Check if new capacity is less than current number of registered participants
            if new_participants < current_participants_count:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot reduce capacity to {new_participants}. Already have {current_participants_count} registered participants."
                )
    
    for field, value in update_data.items():
        setattr(db_tournament, field, value)
    
    db.commit()
    db.refresh(db_tournament)
    return db_tournament


def delete_tournament(db: Session, tournament_id: int):
    db_tournament = db.query(Tournament).filter(Tournament.id == tournament_id, Tournament.is_deleted == False).first()
    if db_tournament:
        # Soft delete: set flag instead of removing row
        db_tournament.is_deleted = True
        db.commit()
        return True
    return False