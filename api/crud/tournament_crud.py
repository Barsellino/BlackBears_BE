from sqlalchemy.orm import Session
from typing import List, Optional
from models.tournament import Tournament, TournamentStatus
from models.tournament_participant import TournamentParticipant
from schemas.tournament import TournamentCreate, TournamentUpdate


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

        # Add user info to participants
        for participant in tournament.participants:
            participant.battletag = participant.user.battletag
            participant.name = participant.user.name
        
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