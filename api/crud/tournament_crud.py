from sqlalchemy.orm import Session
from typing import List, Optional
from models.tournament import Tournament
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


def get_tournaments(db: Session, skip: int = 0, limit: int = 100):
    from sqlalchemy.orm import joinedload
    from sqlalchemy import case
    
    # Sort by start_date (nulls last), then by created_at
    tournaments = db.query(Tournament).options(
        joinedload(Tournament.creator),
        joinedload(Tournament.participants)
    ).filter(Tournament.is_deleted == False).order_by(
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
        
    return tournaments


def get_user_tournaments(db: Session, user_id: int):
    return db.query(Tournament).filter(Tournament.creator_id == user_id, Tournament.is_deleted == False).all()


def update_tournament(db: Session, tournament_id: int, tournament_update: TournamentUpdate):
    db_tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not db_tournament:
        return None
    
    update_data = tournament_update.dict(exclude_unset=True)
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