#!/usr/bin/env python3

# Import all models to avoid relationship errors
from models.user import User
from models.tournament import Tournament
from models.tournament_participant import TournamentParticipant
from models.tournament_round import TournamentRound
from models.tournament_game import TournamentGame
from models.game_participant import GameParticipant

from db import SessionLocal
import random

def create_test_users():
    db = SessionLocal()
    try:
        # Check if test users already exist
        existing_count = db.query(User).filter(User.battlenet_id.like('test_%')).count()
        if existing_count > 0:
            print(f"Found {existing_count} existing test users. Skipping creation.")
            return

        users = []
        for i in range(1, 101):
            user = User(
                battlenet_id=f"test_{i}",
                battletag=f"TestUser#{i:04d}",
                name=f"Test User {i}",
                email=f"test{i}@example.com",
                battlegrounds_rating=random.randint(1000, 8000),
                is_active=True
            )
            users.append(user)
        
        db.add_all(users)
        db.commit()
        print("✅ Successfully created 100 test users")
        print("Users have IDs 1-100 and battletags TestUser#0001 to TestUser#0100")
        
    except Exception as e:
        print(f"❌ Error creating test users: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_users()