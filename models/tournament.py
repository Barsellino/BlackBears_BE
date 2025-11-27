from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db import Base
import enum


class TournamentStatus(enum.Enum):
    REGISTRATION = "registration"
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Tournament settings
    tournament_type = Column(String, default="SWISS")  # SWISS, ELIMINATION, etc
    total_participants = Column(Integer, nullable=False)  # Must be divisible by 8
    total_rounds = Column(Integer, nullable=False)
    current_round = Column(Integer, default=0)
    
    # Lobby Maker settings
    lobby_maker_priority_list = Column(JSON, nullable=True)  # List of user_ids [1, 2, 3]
    
    # Status and timing
    status = Column(Enum(TournamentStatus), default=TournamentStatus.REGISTRATION)
    registration_deadline = Column(DateTime(timezone=True), nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    
    # New fields
    is_free = Column(Boolean, default=True, nullable=False)
    prizes = Column(JSON, nullable=True)  # List of prize descriptions
    first_round_strategy = Column(String, default="RANDOM")  # RANDOM, BALANCED, STRONG_VS_STRONG
    
    # Finals settings
    with_finals = Column(Boolean, default=False, nullable=False)
    finals_games_count = Column(Integer, nullable=True)  # How many games in finals
    finals_participants_count = Column(Integer, nullable=True)  # How many top players go to finals
    regular_rounds = Column(Integer, nullable=True)  # Original rounds count (before finals)
    finals_started = Column(Boolean, default=False, nullable=False)  # Whether finals have started
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Soft-delete flag
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Relationships
    creator = relationship("User", back_populates="created_tournaments", lazy='select')
    participants = relationship("TournamentParticipant", back_populates="tournament", cascade="all, delete-orphan", lazy='select')
    rounds = relationship("TournamentRound", back_populates="tournament", cascade="all, delete-orphan", lazy='select')
    games = relationship("TournamentGame", back_populates="tournament", cascade="all, delete-orphan", lazy='select')