from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db import Base
import enum


class GameStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


class TournamentGame(Base):
    __tablename__ = "tournament_games"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    round_id = Column(Integer, ForeignKey("tournament_rounds.id"), nullable=False)
    game_number = Column(Integer, nullable=False)  # 1-8 for each round
    lobby_maker_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Game status and timing
    status = Column(Enum(GameStatus), default=GameStatus.PENDING)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tournament = relationship("Tournament", back_populates="games")
    round = relationship("TournamentRound", back_populates="games")
    participants = relationship("GameParticipant", back_populates="game")
    lobby_maker = relationship("User", foreign_keys=[lobby_maker_id])
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('round_id', 'game_number', name='unique_round_game'),
    )