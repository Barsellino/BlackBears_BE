from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from api.deps.db import get_db
from models.tournament_participant import TournamentParticipant
from models.tournament import Tournament, TournamentStatus
from models.user import User

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/player/{user_id}")
async def get_player_stats(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get player tournament and game statistics"""
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all finished tournaments for this player (exclude soft‑deleted)
    finished_participations = db.query(TournamentParticipant).join(Tournament).filter(
        and_(
            TournamentParticipant.user_id == user_id,
            Tournament.status == TournamentStatus.FINISHED,
            Tournament.is_deleted == False,
            TournamentParticipant.final_position.isnot(None)
        )
    ).all()
    
    # Get all completed games for this player (exclude soft‑deleted tournaments)
    from models.game_participant import GameParticipant
    from models.tournament_game import TournamentGame, GameStatus
    import json
    
    game_results = db.query(GameParticipant).join(
        TournamentGame
    ).join(
        TournamentParticipant, GameParticipant.participant_id == TournamentParticipant.id
    ).join(
        Tournament, Tournament.id == TournamentGame.tournament_id
    ).filter(
        and_(
            TournamentParticipant.user_id == user_id,
            TournamentGame.status == GameStatus.COMPLETED,
            GameParticipant.positions.isnot(None),
            Tournament.is_deleted == False
        )
    ).all()
    
    if not finished_participations:
        return {
            "user_id": user_id,
            "battletag": user.battletag,
            "name": user.name,
            "last_seen": user.last_seen,
            "is_online": user.is_online,
            "tournaments_played": 0,
            "games_played": len(game_results),
            "stats_by_size": {},
            "game_stats": {
                "total_games": len(game_results),
                "average_game_position": 0
            }
        }
    
    # Tournament stats (as before)
    stats_by_size = {}
    
    for participation in finished_participations:
        tournament = participation.tournament
        size = tournament.total_participants
        position = participation.final_position
        
        if size not in stats_by_size:
            stats_by_size[size] = {
                "tournaments_played": 0,
                "wins": 0,
                "second_places": 0,
                "third_places": 0,
                "average_position": 0,
                "total_score": 0
            }
        
        stats = stats_by_size[size]
        stats["tournaments_played"] += 1
        
        # For tournaments with finals, use finals_score for finalists, otherwise total_score
        if tournament.with_finals and tournament.finals_started:
            # Check if user was in finals
            # If finals_score exists (even if 0), user was in finals - use finals_score
            # Otherwise, use total_score (user didn't make it to finals)
            if participation.finals_score is not None:
                score_to_use = participation.finals_score
            else:
                score_to_use = participation.total_score
        else:
            score_to_use = participation.total_score
        
        stats["total_score"] += score_to_use or 0
        
        # Count exact positions
        if position == 1:
            stats["wins"] += 1
        elif position == 2:
            stats["second_places"] += 1
        elif position == 3:
            stats["third_places"] += 1
    
    # Calculate tournament averages
    for size_stats in stats_by_size.values():
        if size_stats["tournaments_played"] > 0:
            size_stats["average_position"] = round(
                sum(p.final_position for p in finished_participations 
                    if p.tournament.total_participants == size) / size_stats["tournaments_played"], 2
            )
            size_stats["average_score"] = round(
                size_stats["total_score"] / size_stats["tournaments_played"], 2
            )
    
    # Game stats (new)
    game_positions = []
    for game_result in game_results:
        if not game_result.positions:
            continue
        
        try:
            # Try to parse as JSON string first
            if isinstance(game_result.positions, str):
                positions = json.loads(game_result.positions)
            else:
                # Already a list/dict (JSONB)
                positions = game_result.positions
            
            # Ensure positions is a list
            if not isinstance(positions, list):
                continue
            
            if len(positions) == 0:
                continue
                
            avg_position = sum(positions) / len(positions)
            game_positions.append(avg_position)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            # Skip invalid positions
            continue
    
    total_tournaments = len(finished_participations)
    total_games = len(game_results)
    
    return {
        "user_id": user_id,
        "battletag": user.battletag,
        "name": user.name,
        "last_seen": user.last_seen,
        "is_online": user.is_online,
        "tournaments_played": total_tournaments,
        "games_played": total_games,
        "stats_by_size": stats_by_size,
        "overall": {
            "wins": sum(1 for p in finished_participations if p.final_position == 1),
            "second_places": sum(1 for p in finished_participations if p.final_position == 2),
            "third_places": sum(1 for p in finished_participations if p.final_position == 3),
            "average_position": round(
                sum(p.final_position for p in finished_participations) / total_tournaments, 2
            ) if total_tournaments > 0 else 0,
            "total_score": sum(
                (p.finals_score if p.tournament.with_finals and p.tournament.finals_started and p.finals_score is not None else p.total_score) or 0
                for p in finished_participations
            )
        },
        "game_stats": {
            "total_games": total_games,
            "average_game_position": round(
                sum(game_positions) / total_games, 2
            ) if total_games > 0 else 0
        }
    }