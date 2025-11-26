from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List
from models.tournament_participant import TournamentParticipant
from models.game_participant import GameParticipant


def join_tournament(db: Session, tournament_id: int, user_id: int):
    # Check if already joined
    existing = db.query(TournamentParticipant).filter(
        and_(
            TournamentParticipant.tournament_id == tournament_id,
            TournamentParticipant.user_id == user_id
        )
    ).first()
    
    if existing:
        return None
    
    db_participant = TournamentParticipant(
        tournament_id=tournament_id,
        user_id=user_id
    )
    db.add(db_participant)
    db.commit()
    db.refresh(db_participant)
    return db_participant


def get_tournament_participants(db: Session, tournament_id: int):
    from sqlalchemy.orm import joinedload
    return db.query(TournamentParticipant).options(
        joinedload(TournamentParticipant.user)
    ).filter(
        TournamentParticipant.tournament_id == tournament_id
    ).all()


def get_participant_by_ids(db: Session, tournament_id: int, user_id: int):
    return db.query(TournamentParticipant).filter(
        and_(
            TournamentParticipant.tournament_id == tournament_id,
            TournamentParticipant.user_id == user_id
        )
    ).first()


def get_participant(db: Session, participant_id: int):
    return db.query(TournamentParticipant).filter(
        TournamentParticipant.id == participant_id
    ).first()


def leave_tournament(db: Session, tournament_id: int, user_id: int):
    participant = db.query(TournamentParticipant).filter(
        and_(
            TournamentParticipant.tournament_id == tournament_id,
            TournamentParticipant.user_id == user_id
        )
    ).first()
    
    if participant:
        db.delete(participant)
        db.commit()
        return True
    return False


def get_tournament_leaderboard(db: Session, tournament_id: int):
    from models.user import User
    from sqlalchemy.orm import joinedload
    
    participants = db.query(TournamentParticipant).options(
        joinedload(TournamentParticipant.user)
    ).filter(
        TournamentParticipant.tournament_id == tournament_id
    ).order_by(TournamentParticipant.total_score.desc()).all()
    
    # Add user info to participants
    for participant in participants:
        participant.battletag = participant.user.battletag
        participant.name = participant.user.name
    
    return participants


def update_participant_total_score(db: Session, participant_id: int):
    """Recalculate total score from all game results"""
    # Use calculated_points (Float) instead of points (Integer)
    subquery = db.query(
        func.coalesce(func.sum(GameParticipant.calculated_points), 0)
    ).filter(
        GameParticipant.participant_id == participant_id
    ).scalar_subquery()
    
    db.query(TournamentParticipant).filter(
        TournamentParticipant.id == participant_id
    ).update({TournamentParticipant.total_score: subquery}, synchronize_session=False)
    
    db.commit()


def update_final_positions(db: Session, tournament_id: int):
    """
    Update final positions based on total scores with tiebreakers.
    
    Tiebreaker rules:
    1. Higher total_score wins
    2. If equal total_score, check best placement (lowest position number across all games)
    3. If still tied, random 50/50 (coin flip)
    """
    import random
    import json
    
    # Get all participants with their game results
    participants = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament_id
    ).all()
    
    # Calculate best placement for each participant
    participant_data = []
    for participant in participants:
        # Get all game results for this participant
        game_results = db.query(GameParticipant).filter(
            GameParticipant.participant_id == participant.id
        ).all()
        
        # Find best placement (lowest position number)
        best_placement = float('inf')
        for game_result in game_results:
            if game_result.positions:
                try:
                    positions = json.loads(game_result.positions)
                    if positions:
                        # Get the best (lowest) position from this game
                        min_position = min(positions)
                        best_placement = min(best_placement, min_position)
                except (json.JSONDecodeError, ValueError):
                    pass
        
        # If no valid placements found, set to worst possible
        if best_placement == float('inf'):
            best_placement = 999
        
        participant_data.append({
            'participant': participant,
            'total_score': participant.total_score,
            'best_placement': best_placement,
            'random_tiebreaker': random.random()  # For 50/50 coin flip
        })
    
    # Sort by: total_score DESC, best_placement ASC, random_tiebreaker ASC
    participant_data.sort(
        key=lambda x: (-x['total_score'], x['best_placement'], x['random_tiebreaker'])
    )
    
    # Assign final positions
    for position, data in enumerate(participant_data, 1):
        data['participant'].final_position = position
    
    db.commit()
    return [data['participant'] for data in participant_data]