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
        can_finish = (
            self.tournament.current_round >= self.tournament.total_rounds and 
            not self.can_create_next_round(db)  # All games completed, no more rounds
        )
        
        return {
            "tournament_id": self.tournament.id,
            "status": self.tournament.status.value,
            "current_round": self.tournament.current_round,
            "total_rounds": self.tournament.total_rounds,
            "can_start": can_start,
            "can_create_next_round": can_next_round,
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