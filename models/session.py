from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.ext.mutable import MutableDict
from datetime import datetime

from db import Base

class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(String, primary_key=True, index=True)
    state = Column(MutableDict.as_mutable(JSON), default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)