from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, String, Float
from sqlalchemy.orm import relationship
from db import Base


class GameParticipant(Base):
    __tablename__ = "game_participants"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("tournament_games.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("tournament_participants.id"), nullable=False)
    
    # Game results
    points = Column(Integer, nullable=True)    # Points earned (1-8) - deprecated
    positions = Column(String, nullable=True)  # JSON array of shared positions e.g. "[6,7,8]"
    calculated_points = Column(Float, nullable=True)  # Points calculated from positions
    
    # Relationships
    game = relationship("TournamentGame", back_populates="participants")
    participant = relationship("TournamentParticipant", back_populates="game_results")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('game_id', 'participant_id', name='unique_game_participant'),
    )