from sqlalchemy.orm import Session
from models.tournament import Tournament
from services.tournament_strategies import SwissStrategy, TournamentStrategy
from core.exceptions import InvalidTournamentState


class TournamentManager:
    """Main tournament manager using strategy pattern"""
    
    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        self.strategy = self._get_strategy(tournament.tournament_type if hasattr(tournament, 'tournament_type') else 'SWISS')
    
    def start_tournament(self, db: Session) -> Tournament:
        """Start the tournament"""
        return self.strategy.start_tournament(db, self.tournament)
    
    def can_create_next_round(self, db: Session) -> bool:
        """Check if next round can be created"""
        return self.strategy.can_create_next_round(db, self.tournament)
    
    def create_next_round(self, db: Session):
        """Create next round"""
        return self.strategy.create_next_round(db, self.tournament)
    
    def finish_tournament(self, db: Session) -> Tournament:
        """Finish the tournament"""
        return self.strategy.finish_tournament(db, self.tournament)
    
    def get_tournament_status(self, db: Session) -> dict:
        """Get detailed tournament status"""
        can_start = self.tournament.status.value == 'registration'
        can_next_round = self.can_create_next_round(db)
        
        # Calculate max rounds
        max_rounds = self.tournament.total_rounds
            
        # Can finish if all rounds are completed
        # And we cannot create any more rounds
        can_finish = (
            self.tournament.current_round >= max_rounds and 
            not can_next_round
        )
        
        # Can start finals if:
        # - Tournament has finals enabled
        # - Finals not started yet
        # - All regular rounds completed
        can_start_finals = (
            self.tournament.with_finals and
            not self.tournament.finals_started and
            self.tournament.regular_rounds and
            self.tournament.current_round >= self.tournament.regular_rounds and
            not can_next_round
        )
        
        return {
            "tournament_id": self.tournament.id,
            "status": self.tournament.status.value,
            "current_round": self.tournament.current_round,
            "total_rounds": self.tournament.total_rounds,
            "regular_rounds": self.tournament.regular_rounds,
            "with_finals": self.tournament.with_finals,
            "finals_started": self.tournament.finals_started,
            "finals_games_count": self.tournament.finals_games_count,
            "finals_participants_count": self.tournament.finals_participants_count,
            "can_start": can_start,
            "can_create_next_round": can_next_round,
            "can_start_finals": can_start_finals,
            "can_finish": can_finish,
            "is_finished": self.tournament.status.value == 'finished'
        }
    
    def _get_strategy(self, tournament_type: str) -> TournamentStrategy:
        """Get appropriate strategy for tournament type"""
        strategies = {
            "SWISS": SwissStrategy(),
            # Future strategies can be added here
            # "ELIMINATION": EliminationStrategy(),
            # "ROUND_ROBIN": RoundRobinStrategy()
        }
        
        # Default to Swiss if type not found
        return strategies.get(tournament_type, SwissStrategy())