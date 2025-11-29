from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List
from models.tournament_participant import TournamentParticipant
from models.game_participant import GameParticipant


def join_tournament(db: Session, tournament_id: int, user_id: int):
    """
    Join tournament if not joined yet.
    Якщо користувач вже зареєстрований у турнірі — повертаємо існуючий запис
    без помилки (ідемпотентна операція).
    """
    # Check if already joined
    existing = db.query(TournamentParticipant).filter(
        and_(
            TournamentParticipant.tournament_id == tournament_id,
            TournamentParticipant.user_id == user_id
        )
    ).first()
    
    if existing:
        # Вже зареєстрований – просто повертаємо існуючого учасника
        return existing
    
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


def get_finals_leaderboard(db: Session, tournament_id: int):
    """
    Get leaderboard for finals only (participants actually playing in finals,
    sorted by finals_score).

    Раніше фіналісти брались як top-N по total_score.
    Тепер беремо фактичних фіналістів з фінальних ігор (враховуємо свапи).
    """
    from models.tournament import Tournament
    from models.tournament_round import TournamentRound
    from models.tournament_game import TournamentGame
    from models.game_participant import GameParticipant
    from sqlalchemy.orm import joinedload
    
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament or not tournament.finals_started:
        return []
    
    # Знаходимо всі фінальні раунди (round_number > regular_rounds)
    regular_rounds = tournament.regular_rounds or tournament.total_rounds
    final_rounds = db.query(TournamentRound.id).filter(
        TournamentRound.tournament_id == tournament_id,
        TournamentRound.round_number > regular_rounds
    ).all()
    
    if not final_rounds:
        return []
    
    final_round_ids = [r[0] for r in final_rounds]
    
    # Всі фінальні ігри
    final_games = db.query(TournamentGame.id).filter(
        TournamentGame.tournament_id == tournament_id,
        TournamentGame.round_id.in_(final_round_ids)
    ).all()
    
    if not final_games:
        return []
    
    final_game_ids = [g[0] for g in final_games]
    
    # Фіналісти = всі унікальні TournamentParticipant.id, які є в фінальних GameParticipant
    finalist_rows = db.query(GameParticipant.participant_id).filter(
        GameParticipant.game_id.in_(final_game_ids)
    ).distinct().all()
    
    finalist_ids = [row[0] for row in finalist_rows]
    
    if not finalist_ids:
        return []
    
    participants = db.query(TournamentParticipant).options(
        joinedload(TournamentParticipant.user)
    ).filter(
        TournamentParticipant.id.in_(finalist_ids)
    ).all()
    
    # Сортуємо по finals_score (як і раніше)
    participants = sorted(participants, key=lambda p: p.finals_score or 0, reverse=True)
    
    # Додаємо публічну інформацію користувача
    for participant in participants:
        if participant.user:
            participant.battletag = participant.user.battletag
            participant.name = participant.user.name
    
    return participants


def get_finals_candidates(db: Session, tournament_id: int):
    """
    Отримати список учасників турніру, які НЕ в фіналах (кандидати для заміни фіналістів).
    Логіка:
    - знаходимо фактичних фіналістів з фінальних ігор (з урахуванням свапів)
    - повертаємо всіх інших учасників турніру, відсортованих по total_score
    """
    from models.tournament import Tournament
    from models.tournament_round import TournamentRound
    from models.tournament_game import TournamentGame
    from models.game_participant import GameParticipant
    from sqlalchemy.orm import joinedload

    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament or not tournament.with_finals:
        return []

    # Знаходимо фактичних фіналістів з фінальних ігор (як у get_finals_leaderboard)
    regular_rounds = tournament.regular_rounds or tournament.total_rounds
    final_rounds = db.query(TournamentRound.id).filter(
        TournamentRound.tournament_id == tournament_id,
        TournamentRound.round_number > regular_rounds
    ).all()

    finalist_ids = set()
    if final_rounds:
        final_round_ids = [r[0] for r in final_rounds]
        final_games = db.query(TournamentGame.id).filter(
            TournamentGame.tournament_id == tournament_id,
            TournamentGame.round_id.in_(final_round_ids)
        ).all()

        if final_games:
            final_game_ids = [g[0] for g in final_games]
            finalist_rows = db.query(GameParticipant.participant_id).filter(
                GameParticipant.game_id.in_(final_game_ids)
            ).distinct().all()
            finalist_ids = {row[0] for row in finalist_rows}

    # Всі учасники турніру
    all_participants = db.query(TournamentParticipant).options(
        joinedload(TournamentParticipant.user)
    ).filter(
        TournamentParticipant.tournament_id == tournament_id
    ).all()

    # Кандидати = всі, хто НЕ є фактичним фіналістом
    candidates = [p for p in all_participants if p.id not in finalist_ids]

    # Сортуємо по total_score (desc)
    candidates = sorted(candidates, key=lambda p: p.total_score or 0, reverse=True)

    # Додати публічну інформацію користувача
    for participant in candidates:
        if participant.user:
            participant.battletag = participant.user.battletag
            participant.name = participant.user.name

    return candidates


def update_participant_total_score(db: Session, participant_id: int):
    """Recalculate total score and finals_score from all game results"""
    from models.tournament_round import TournamentRound
    from models.tournament_game import TournamentGame
    from models.tournament import Tournament
    
    # Get participant's tournament
    participant = db.query(TournamentParticipant).filter(
        TournamentParticipant.id == participant_id
    ).first()
    
    if not participant:
        return
    
    tournament = db.query(Tournament).filter(
        Tournament.id == participant.tournament_id
    ).first()
    
    regular_rounds = tournament.regular_rounds or tournament.total_rounds
    
    # Calculate total_score from regular rounds only
    regular_score = db.query(
        func.coalesce(func.sum(GameParticipant.calculated_points), 0)
    ).join(TournamentGame, GameParticipant.game_id == TournamentGame.id
    ).join(TournamentRound, TournamentGame.round_id == TournamentRound.id
    ).filter(
        GameParticipant.participant_id == participant_id,
        TournamentRound.round_number <= regular_rounds
    ).scalar() or 0.0
    
    # Calculate finals_score from final rounds only
    finals_score = db.query(
        func.coalesce(func.sum(GameParticipant.calculated_points), 0)
    ).join(TournamentGame, GameParticipant.game_id == TournamentGame.id
    ).join(TournamentRound, TournamentGame.round_id == TournamentRound.id
    ).filter(
        GameParticipant.participant_id == participant_id,
        TournamentRound.round_number > regular_rounds
    ).scalar() or 0.0
    
    # Update both scores
    db.query(TournamentParticipant).filter(
        TournamentParticipant.id == participant_id
    ).update({
        TournamentParticipant.total_score: regular_score,
        TournamentParticipant.finals_score: finals_score
    }, synchronize_session=False)
    
    db.commit()


def update_final_positions(db: Session, tournament_id: int):
    """
    Update final positions based on scores with tiebreakers.
    
    For tournaments WITH finals: winners determined by finals_score (only finalists get top positions)
    For tournaments WITHOUT finals: winners determined by total_score
    
    Tiebreaker rules:
    1. Higher score wins (finals_score or total_score)
    2. If equal score, check best placement (lowest position number across all games)
    3. If still tied, random 50/50 (coin flip)
    """
    import random
    import json
    import logging
    from models.tournament import Tournament
    
    logger = logging.getLogger(__name__)
    
    try:
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not tournament:
            from core.exceptions import TournamentException
            raise TournamentException("Tournament not found while updating final positions")

        use_finals_score = tournament.with_finals and tournament.finals_started
        
        # Get all participants with their game results
        participants = db.query(TournamentParticipant).filter(
            TournamentParticipant.tournament_id == tournament_id
        ).all()
        
        # Separate finalists and non-finalists if tournament has finals
        finalists = []
        non_finalists = []
        
        if use_finals_score:
            # FINALS: беремо фактичних фіналістів з фінальних ігор (як у get_finals_leaderboard),
            # щоб врахувати свапи та будь-які ручні заміни складу фіналу.
            from models.tournament_round import TournamentRound
            from models.tournament_game import TournamentGame
            from models.game_participant import GameParticipant

            regular_rounds = tournament.regular_rounds or tournament.total_rounds

            # Фінальні раунди (round_number > regular_rounds)
            final_rounds = db.query(TournamentRound.id).filter(
                TournamentRound.tournament_id == tournament_id,
                TournamentRound.round_number > regular_rounds
            ).all()

            if final_rounds:
                final_round_ids = [r[0] for r in final_rounds]

                # Фінальні ігри
                final_games = db.query(TournamentGame.id).filter(
                    TournamentGame.tournament_id == tournament_id,
                    TournamentGame.round_id.in_(final_round_ids)
                ).all()

                if final_games:
                    final_game_ids = [g[0] for g in final_games]

                    # ID фіналістів з фінальних ігор
                    finalist_rows = db.query(GameParticipant.participant_id).filter(
                        GameParticipant.game_id.in_(final_game_ids)
                    ).distinct().all()

                    finalist_ids = {row[0] for row in finalist_rows}

                    # Розбиваємо всіх учасників на фіналістів і не-фіналістів
                    for p in participants:
                        if p.id in finalist_ids:
                            finalists.append(p)
                        else:
                            non_finalists.append(p)
                else:
                    # fallback: якщо чомусь немає фінальних ігор, поводимось як раніше (top-N за total_score)
                    sorted_by_total = sorted(participants, key=lambda p: -p.total_score)
                    finals_count = tournament.finals_participants_count or len(sorted_by_total)
                    finalists = sorted_by_total[:finals_count]
                    non_finalists = sorted_by_total[finals_count:]
            else:
                # fallback: якщо немає фінальних раундів
                sorted_by_total = sorted(participants, key=lambda p: -p.total_score)
                finals_count = tournament.finals_participants_count or len(sorted_by_total)
                finalists = sorted_by_total[:finals_count]
                non_finalists = sorted_by_total[finals_count:]
        else:
            # ТУРНІРИ БЕЗ ФІНАЛІВ: всі учасники змагаються за місця по total_score
            finalists = participants
        
        # Calculate best placement for finalists
        finalist_data = []
        from models.game_participant import GameParticipant
        for participant in finalists:
            game_results = db.query(GameParticipant).filter(
                GameParticipant.participant_id == participant.id
            ).all()
            
            best_placement = float('inf')
            for game_result in game_results:
                if game_result.positions:
                    try:
                        positions = json.loads(game_result.positions)
                        if positions:
                            min_position = min(positions)
                            best_placement = min(best_placement, min_position)
                    except (json.JSONDecodeError, ValueError):
                        pass
            
            if best_placement == float('inf'):
                best_placement = 999
            
            # Use finals_score for finals, total_score otherwise
            score = participant.finals_score if use_finals_score else participant.total_score
            
            finalist_data.append({
                'participant': participant,
                'score': score,
                'best_placement': best_placement,
                'random_tiebreaker': random.random()
            })
        
        # Sort finalists by: score DESC, best_placement ASC, random_tiebreaker ASC
        finalist_data.sort(
            key=lambda x: (-x['score'], x['best_placement'], x['random_tiebreaker'])
        )
        
        # Assign final positions to finalists (1, 2, 3, ... N)
        for position, data in enumerate(finalist_data, 1):
            data['participant'].final_position = position
        
        # For non-finalists, assign positions after finalists (N+1, N+2, ...)
        if non_finalists:
            non_finalist_data = []
            for participant in non_finalists:
                non_finalist_data.append({
                    'participant': participant,
                    'total_score': participant.total_score,
                    'random_tiebreaker': random.random()
                })
            
            non_finalist_data.sort(
                key=lambda x: (-x['total_score'], x['random_tiebreaker'])
            )
            
            start_position = len(finalists) + 1
            for position, data in enumerate(non_finalist_data, start_position):
                data['participant'].final_position = position
        
        db.commit()
        return [data['participant'] for data in finalist_data]
    except Exception as e:
        # Логування і прокидування як TournamentException, щоб не було 500 без пояснення
        logger.error(f"update_final_positions error for tournament {tournament_id}: {e}")
        from core.exceptions import TournamentException
        raise TournamentException(f"Failed to update final positions: {e}")