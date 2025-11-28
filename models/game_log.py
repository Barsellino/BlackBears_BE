from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from db import Base
from datetime import datetime


class GameLog(Base):
    __tablename__ = "game_logs"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("tournament_games.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_battletag = Column(String, nullable=False)  # Зберігаємо battletag на момент дії
    user_role = Column(String, nullable=False)  # Зберігаємо роль на момент дії
    action_type = Column(String(50), nullable=False, index=True)  # 'position_set', 'participant_removed', etc.
    action_description = Column(Text, nullable=False)  # Текстовий опис дії
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    game = relationship("TournamentGame", backref="logs")
    user = relationship("User", backref="game_logs")

