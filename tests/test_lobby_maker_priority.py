import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from main import app
from db import Base, engine, SessionLocal
from models.user import User
from models.tournament import Tournament, TournamentStatus
from models.tournament_participant import TournamentParticipant
from models.tournament_game import TournamentGame, GameStatus
from models.game_participant import GameParticipant
from models.tournament_round import TournamentRound
from services.tournament_strategies import SwissStrategy
from api.deps.db import get_db

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture(scope="function")
def db_session():
    """Create a fresh DB for each test (SQLite in‑memory)."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI client that uses the test DB session."""
    def _get_test_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# ----------------------------------------------------------------------
# Helper functions to create test data
# ----------------------------------------------------------------------
def create_user(db, user_id: int, battletag: str = None):
    user = User(
        id=user_id,
        battlenet_id=str(user_id),
        battletag=battletag or f"User{user_id}#1234",
        name=f"User {user_id}",
        last_seen=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_tournament(db, creator_id: int, priority_list=None, status=TournamentStatus.REGISTRATION):
    tournament = Tournament(
        name="Test Tournament",
        description="",
        creator_id=creator_id,
        tournament_type="SWISS",
        total_participants=8,
        total_rounds=1,
        current_round=0,
        status=status,
        lobby_maker_priority_list=priority_list,
    )
    db.add(tournament)
    db.commit()
    db.refresh(tournament)
    return tournament

def add_participant(db, tournament_id: int, user_id: int, final_position=None, total_score=0):
    participant = TournamentParticipant(
        tournament_id=tournament_id,
        user_id=user_id,
        final_position=final_position,
        total_score=total_score,
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant

# ----------------------------------------------------------------------
# Test: lobby maker priority is respected when assigning to games
# ----------------------------------------------------------------------
def test_lobby_maker_priority_assignment(db_session, client):
    # 1️⃣ Create creator and participants (using high unique IDs to avoid conflicts)
    creator = create_user(db_session, 9001)
    user2 = create_user(db_session, 9002)
    user3 = create_user(db_session, 9003)
    user4 = create_user(db_session, 9004)

    # 2️⃣ Create tournament with a priority list (user3 first, then user2)
    priority = [9003, 9002]
    tournament = create_tournament(db_session, creator.id, priority_list=priority)

    # 3️⃣ Add participants – include all users
    participants = [
        add_participant(db_session, tournament.id, creator.id),
        add_participant(db_session, tournament.id, user2.id),
        add_participant(db_session, tournament.id, user3.id),
        add_participant(db_session, tournament.id, user4.id),
        # Add 4 more dummy users to reach 8 participants
        add_participant(db_session, tournament.id, create_user(db_session, 9005).id),
        add_participant(db_session, tournament.id, create_user(db_session, 9006).id),
        add_participant(db_session, tournament.id, create_user(db_session, 9007).id),
        add_participant(db_session, tournament.id, create_user(db_session, 9008).id),
    ]

    # 4️⃣ Start the tournament using SwissStrategy (first round, random assignment)
    strategy = SwissStrategy()
    # The strategy expects the tournament to be in REGISTRATION state and have the exact number of participants
    tournament = strategy.start_tournament(db_session, tournament)

    # 5️⃣ Retrieve the first round and its games
    round_obj = db_session.query(TournamentRound).filter_by(tournament_id=tournament.id, round_number=1).first()
    assert round_obj is not None, "First round was not created"
    games = db_session.query(TournamentGame).filter_by(round_id=round_obj.id).all()
    assert len(games) > 0, "No games were created for the first round"

    # 6️⃣ Verify that each game has a lobby_maker_id that follows the priority list
    #    The first game should contain the highest‑priority user that is present in that game.
    for game in games:
        participants_ids = [
            db_session.query(TournamentParticipant).filter_by(id=gp.participant_id).first().user_id
            for gp in db_session.query(GameParticipant).filter_by(game_id=game.id).all()
        ]
        # Find the first priority user that is in this game's participants
        expected_lobby = None
        for uid in priority:
            if uid in participants_ids:
                expected_lobby = uid
                break
        # If none of the priority users are in the game, lobby_maker_id should stay None
        assert game.lobby_maker_id == expected_lobby

        # Also verify that the is_lobby_maker flag is set correctly on GameParticipant rows
        for gp in db_session.query(GameParticipant).filter_by(game_id=game.id).all():
            tp = db_session.query(TournamentParticipant).filter_by(id=gp.participant_id).first()
            if tp.user_id == expected_lobby:
                assert gp.is_lobby_maker is True
            else:
                assert gp.is_lobby_maker is False
