"""
Скрипт для створення всіх таблиць
"""
from db import Base, engine

# Імпортуємо всі моделі
from models.user import User
from models.tournament import Tournament
from models.tournament_participant import TournamentParticipant
from models.tournament_round import TournamentRound
from models.tournament_game import TournamentGame
from models.game_participant import GameParticipant

print("Створення таблиць...")
print(f"Моделі для створення: {[table.name for table in Base.metadata.sorted_tables]}")

Base.metadata.create_all(bind=engine)

print("✅ Таблиці створено!")
