# api/deps/db.py
from typing import Generator

from sqlalchemy.orm import Session

from db import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependency для FastAPI: віддає сесію БД на час обробки запиту
    і гарантує її закриття після завершення.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()