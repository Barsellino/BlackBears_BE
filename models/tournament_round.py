from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db import Base
import enum


class RoundStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


class TournamentRound(Base):
    __tablename__ = "tournament_rounds"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    round_number = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    
    # Round status and timing
    status = Column(Enum(RoundStatus), default=RoundStatus.PENDING)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tournament = relationship("Tournament", back_populates="rounds")
    games = relationship("TournamentGame", back_populates="round")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('tournament_id', 'round_number', name='unique_tournament_round'),
    )