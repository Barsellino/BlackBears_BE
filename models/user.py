from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import Enum as SQLEnum
from db import Base
from core.roles import UserRole


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    battlenet_id = Column(String, unique=True, index=True, nullable=False)
    battletag = Column(String, nullable=False)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    battlegrounds_rating = Column(Integer, nullable=True)
    role = Column(
        SQLEnum(UserRole, values_callable=lambda obj: [e.value for e in obj]),
        default=UserRole.USER,
        nullable=False
    )
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    @property
    def is_online(self) -> bool:
        """Користувач онлайн якщо last_seen < 5 хвилин"""
        if not self.last_seen:
            return False
        from datetime import datetime, timezone, timedelta
        return datetime.now(timezone.utc) - self.last_seen < timedelta(minutes=5)
    
    # Tournament relationships
    created_tournaments = relationship("Tournament", back_populates="creator")
    tournament_participations = relationship("TournamentParticipant", back_populates="user")