from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db import Base


class TournamentParticipant(Base):
    __tablename__ = "tournament_participants"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Tournament results
    total_score = Column(Float, default=0.0)  # Sum of all calculated_points from regular rounds
    finals_score = Column(Float, default=0.0)  # Sum of all calculated_points from finals
    final_position = Column(Integer, nullable=True)  # Final ranking in tournament
    
    # Metadata
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tournament = relationship("Tournament", back_populates="participants")
    user = relationship("User", back_populates="tournament_participations")
    game_results = relationship("GameParticipant", back_populates="participant")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('tournament_id', 'user_id', name='unique_tournament_participant'),
    )