from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from db import Base
from datetime import datetime


class TournamentLog(Base):
    __tablename__ = "tournament_logs"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_battletag = Column(String, nullable=False)  # Зберігаємо battletag на момент дії
    user_role = Column(String, nullable=False)  # Зберігаємо роль на момент дії
    action_type = Column(String(50), nullable=False, index=True)  # 'tournament_started', 'tournament_finished', 'next_round_created', 'finals_started'
    action_description = Column(Text, nullable=False)  # Текстовий опис дії
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    tournament = relationship("Tournament", backref="logs")
    user = relationship("User", backref="tournament_logs")

