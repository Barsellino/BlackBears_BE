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
from models.user import User
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
        
        # Assign participants based on strategy
        strategy = tournament.first_round_strategy
        if strategy == "BALANCED":
            self._assign_participants_balanced(db, first_round, participants, tournament)
        elif strategy == "STRONG_VS_STRONG":
            self._assign_participants_strong_vs_strong(db, first_round, participants, tournament)
        else:
            # Default to RANDOM
            self._assign_participants_randomly(db, first_round, participants, tournament)
        
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
        self._assign_participants_by_score(db, next_round, participants, tournament)
        
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
    
    def _assign_participants_randomly(self, db: Session, round_obj: TournamentRound, participants: List, tournament: Tournament):
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
        
        # Assign Lobby Makers
        self._assign_lobby_makers(db, round_obj, tournament)
    
    def _assign_participants_by_score(self, db: Session, round_obj: TournamentRound, participants: List, tournament: Tournament):
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
        
        # Assign Lobby Makers
        self._assign_lobby_makers(db, round_obj, tournament)

    def _assign_participants_balanced(self, db: Session, round_obj: TournamentRound, participants: List, tournament: Tournament):
        """
        Assign participants to games balancing strong players across lobbies (Snake draft).
        Example for 2 lobbies: 
        1->A, 2->B, 3->B, 4->A, 5->A, 6->B...
        """
        # Sort participants by rating (descending)
        # Assuming participant.user.battlegrounds_rating is available. If None, treat as 0.
        sorted_participants = sorted(
            participants, 
            key=lambda p: p.user.battlegrounds_rating if p.user and p.user.battlegrounds_rating else 0, 
            reverse=True
        )
        
        games = get_round_games(db, round_obj.id)
        num_games = len(games)
        
        # Prepare lists for each game
        game_assignments = [[] for _ in range(num_games)]
        
        # Snake distribution
        for i, participant in enumerate(sorted_participants):
            # Determine which game to put this participant in
            # Cycle: 0, 1, 2, ... N-1, N-1, ... 2, 1, 0
            cycle_len = num_games * 2
            pos_in_cycle = i % cycle_len
            
            if pos_in_cycle < num_games:
                game_idx = pos_in_cycle
            else:
                game_idx = cycle_len - 1 - pos_in_cycle
                
            game_assignments[game_idx].append(participant)
            
        # Save to DB
        game_participants = []
        for i, game_players in enumerate(game_assignments):
            game = games[i]
            for participant in game_players:
                game_participants.append(GameParticipant(
                    game_id=game.id,
                    participant_id=participant.id
                ))
        
        db.bulk_save_objects(game_participants)
        db.commit()
        
        self._assign_lobby_makers(db, round_obj, tournament)

    def _assign_participants_strong_vs_strong(self, db: Session, round_obj: TournamentRound, participants: List, tournament: Tournament):
        """
        Assign participants to games grouping strong players together.
        Lobby 1 gets top 8, Lobby 2 gets next 8, etc.
        """
        # Sort participants by rating (descending)
        sorted_participants = sorted(
            participants, 
            key=lambda p: p.user.battlegrounds_rating if p.user and p.user.battlegrounds_rating else 0, 
            reverse=True
        )
        
        games = get_round_games(db, round_obj.id)
        
        # Simple fill
        game_participants = []
        participants_per_game = 8
        
        for i, participant in enumerate(sorted_participants):
            game_index = i // participants_per_game
            if game_index < len(games):
                game_participants.append(GameParticipant(
                    game_id=games[game_index].id,
                    participant_id=participant.id
                ))
                
        db.bulk_save_objects(game_participants)
        db.commit()
        
        self._assign_lobby_makers(db, round_obj, tournament)

    def _assign_lobby_makers(self, db: Session, round_obj: TournamentRound, tournament: Tournament):
        """Assign Lobby Makers to games based on priority list"""
        # First, try to get global favorite lobby makers from tournament creator
        creator = db.query(User).filter(User.id == tournament.creator_id).first()
        global_favorites = creator.favorite_lobby_makers if creator and creator.favorite_lobby_makers else []
        
        # Combine global favorites with tournament-specific priority list
        # Global favorites have higher priority
        tournament_priority = tournament.lobby_maker_priority_list or []
        
        # Merge lists: global first, then tournament-specific (avoiding duplicates)
        priority_list = global_favorites + [uid for uid in tournament_priority if uid not in global_favorites]
        
        # Get games without joinedload to avoid relationship issues
        games = db.query(TournamentGame).filter(
            TournamentGame.round_id == round_obj.id
        ).all()
        
        for game in games:
            # Refresh game to ensure clean state
            db.refresh(game)
            
            game_participants = get_game_participants(db, game.id)
            
            # Find candidate from priority list
            lobby_maker_user_id = None
            
            # Check priority list first
            for user_id in priority_list:
                # Check if this user is in the game
                participant = next(
                    (gp for gp in game_participants 
                     if db.query(TournamentParticipant).filter_by(id=gp.participant_id).first().user_id == user_id),
                    None
                )
                
                if participant:
                    lobby_maker_user_id = user_id
                    break
            
            # If found, assign
            if lobby_maker_user_id:
                game.lobby_maker_id = lobby_maker_user_id
                
                # Update is_lobby_maker flag
                for gp in game_participants:
                    # Access via relationship (lazy load)
                    if gp.participant.user_id == lobby_maker_user_id:
                        gp.is_lobby_maker = True
                    else:
                        gp.is_lobby_maker = False
                        
        db.commit()