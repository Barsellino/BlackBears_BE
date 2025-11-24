from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import random
from models.tournament import Tournament, TournamentStatus
from models.tournament_round import TournamentRound, RoundStatus
from models.tournament_game import TournamentGame, GameStatus
from models.game_participant import GameParticipant
from models.tournament_participant import TournamentParticipant
from api.crud.round_crud import create_round_with_games, start_round, complete_round
from api.crud.participant_crud import get_tournament_participants
from api.crud.game_crud import get_round_games, get_game_participants, add_game_participant
from core.exceptions import InvalidTournamentState


class TournamentStrategy(ABC):
    """Abstract base class for tournament strategies"""
    
    @abstractmethod
    def start_tournament(self, db: Session, tournament: Tournament) -> Tournament:
        """Start the tournament and create first round"""
        pass
    
    @abstractmethod
    def can_create_next_round(self, db: Session, tournament: Tournament) -> bool:
        """Check if next round can be created"""
        pass
    
    @abstractmethod
    def create_next_round(self, db: Session, tournament: Tournament) -> TournamentRound:
        """Create next round with proper player assignment"""
        pass
    
    @abstractmethod
    def finish_tournament(self, db: Session, tournament: Tournament) -> Tournament:
        """Finish tournament and calculate final positions"""
        pass


class SwissStrategy(TournamentStrategy):
    """Swiss System tournament strategy"""
    
    def start_tournament(self, db: Session, tournament: Tournament) -> Tournament:
        """Start Swiss tournament - create first round with random assignment"""
        
        # Validate tournament can start
        if tournament.status != TournamentStatus.REGISTRATION:
            raise InvalidTournamentState("start tournament - must be in registration")
        
        participants = get_tournament_participants(db, tournament.id)
        if len(participants) != tournament.total_participants:
            raise InvalidTournamentState(f"start tournament - need {tournament.total_participants} participants, have {len(participants)}")
        
        # Update tournament status
        tournament.status = TournamentStatus.ACTIVE
        tournament.current_round = 1
        db.commit()
        
        # Create first round
        first_round = create_round_with_games(db, tournament.id, 1, tournament.total_participants)
        
        # Randomly assign participants to games for first round
        self._assign_participants_randomly(db, first_round, participants)
        
        # Start the round
        start_round(db, first_round.id)
        
        db.refresh(tournament)
        return tournament
    
    def can_create_next_round(self, db: Session, tournament: Tournament) -> bool:
        """Check if all games in current round are completed"""
        
        if tournament.current_round >= tournament.total_rounds:
            return False  # Tournament is finished
        
        # Get current round
        current_round = db.query(TournamentRound).filter(
            TournamentRound.tournament_id == tournament.id,
            TournamentRound.round_number == tournament.current_round
        ).first()
        
        if not current_round:
            return False
        
        # Check if all games in current round are completed
        games = db.query(TournamentGame).filter(
            TournamentGame.round_id == current_round.id
        ).all()
        
        for game in games:
            if game.status != GameStatus.COMPLETED:
                return False
            
            # Check if all participants have results (check calculated_points or points)
            game_participants = get_game_participants(db, game.id)
            for gp in game_participants:
                # Accept either points or calculated_points
                has_result = gp.points is not None or gp.calculated_points is not None
                if not has_result:
                    return False
        
        return True
    
    def create_next_round(self, db: Session, tournament: Tournament) -> TournamentRound:
        """Create next round with Swiss system pairing"""
        
        if not self.can_create_next_round(db, tournament):
            raise InvalidTournamentState("create next round - current round not completed")
        
        # Complete current round
        current_round = db.query(TournamentRound).filter(
            TournamentRound.tournament_id == tournament.id,
            TournamentRound.round_number == tournament.current_round
        ).first()
        
        if current_round:
            complete_round(db, current_round.id)
        
        # Update tournament current round
        next_round_number = tournament.current_round + 1
        tournament.current_round = next_round_number
        
        # Create next round
        next_round = create_round_with_games(db, tournament.id, next_round_number, tournament.total_participants)
        
        # Get participants sorted by total score (Swiss pairing)
        participants = db.query(TournamentParticipant).filter(
            TournamentParticipant.tournament_id == tournament.id
        ).order_by(TournamentParticipant.total_score.desc()).all()
        
        # Assign participants to games based on current standings
        self._assign_participants_by_score(db, next_round, participants)
        
        # Start the round
        start_round(db, next_round.id)
        
        db.commit()
        db.refresh(tournament)
        return next_round
    
    def finish_tournament(self, db: Session, tournament: Tournament) -> Tournament:
        """Finish Swiss tournament and calculate final positions"""
        
        if tournament.current_round < tournament.total_rounds:
            raise InvalidTournamentState("finish tournament - not all rounds completed")
        
        # Check if all games in final round are completed
        final_round = db.query(TournamentRound).filter(
            TournamentRound.tournament_id == tournament.id,
            TournamentRound.round_number == tournament.current_round
        ).first()
        
        if final_round:
            games = db.query(TournamentGame).filter(
                TournamentGame.round_id == final_round.id
            ).all()
            
            for game in games:
                if game.status != GameStatus.COMPLETED:
                    raise InvalidTournamentState("finish tournament - not all games completed")
                
                game_participants = get_game_participants(db, game.id)
                for gp in game_participants:
                    if gp.points is None:
                        raise InvalidTournamentState("finish tournament - not all results submitted")
        
        # Complete final round
        final_round = db.query(TournamentRound).filter(
            TournamentRound.tournament_id == tournament.id,
            TournamentRound.round_number == tournament.current_round
        ).first()
        
        if final_round:
            complete_round(db, final_round.id)
        
        # Update final positions based on total scores
        from api.crud.participant_crud import update_final_positions
        update_final_positions(db, tournament.id)
        
        # Update tournament status
        tournament.status = TournamentStatus.FINISHED
        tournament.end_date = func.now()
        
        db.commit()
        db.refresh(tournament)
        return tournament
    
    def _assign_participants_randomly(self, db: Session, round_obj: TournamentRound, participants: List):
        """Randomly assign participants to games in first round"""
        
        # Shuffle participants for random assignment
        shuffled_participants = participants.copy()
        random.shuffle(shuffled_participants)
        
        # Get games for this round
        games = get_round_games(db, round_obj.id)
        
        # Assign 8 participants per game
        participants_per_game = 8
        for i, participant in enumerate(shuffled_participants):
            game_index = i // participants_per_game
            if game_index < len(games):
                game_participant = GameParticipant(
                    game_id=games[game_index].id,
                    participant_id=participant.id
                )
                db.add(game_participant)
        
        db.commit()
    
    def _assign_participants_by_score(self, db: Session, round_obj: TournamentRound, participants: List):
        """Assign participants to games based on current scores (Swiss pairing)"""
        
        # Get games for this round
        games = get_round_games(db, round_obj.id)
        
        # Batch create game participants
        game_participants = []
        participants_per_game = 8
        
        for i, participant in enumerate(participants):
            game_index = i // participants_per_game
            if game_index < len(games):
                game_participants.append(GameParticipant(
                    game_id=games[game_index].id,
                    participant_id=participant.id
                ))
        
        db.bulk_save_objects(game_participants)
        db.commit()