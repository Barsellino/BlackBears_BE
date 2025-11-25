"""
Create all database tables
Run with: python3 create_tables.py
"""
from db import Base, engine

# Import all models so they are registered with Base.metadata
from models.user import User
from models.tournament import Tournament
from models.tournament_participant import TournamentParticipant
from models.tournament_round import TournamentRound
from models.tournament_game import TournamentGame
from models.game_participant import GameParticipant

if __name__ == "__main__":
    print("🔨 Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully!")
    
    # List created tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\n📋 Created tables ({len(tables)}):")
    for table in sorted(tables):
        print(f"   - {table}")
