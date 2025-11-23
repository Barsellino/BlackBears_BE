from sqlalchemy.orm import Session
from typing import List, Optional
from models.tournament import Tournament
from models.tournament_participant import TournamentParticipant
from schemas.tournament import TournamentCreate, TournamentUpdate


def create_tournament(db: Session, tournament: TournamentCreate, creator_id: int):
    tournament_data = tournament.dict()
    
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
    
    tournament = db.query(Tournament).options(
        joinedload(Tournament.participants).joinedload(TournamentParticipant.user)
    ).filter(Tournament.id == tournament_id).first()
    
    if tournament:
        # Add user info to participants
        for participant in tournament.participants:
            participant.battletag = participant.user.battletag
            participant.name = participant.user.name
    return tournament


def get_tournaments(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Tournament).offset(skip).limit(limit).all()


def get_user_tournaments(db: Session, user_id: int):
    return db.query(Tournament).filter(Tournament.creator_id == user_id).all()


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
    db_tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if db_tournament:
        db.delete(db_tournament)
        db.commit()
        return True
    return False