from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps.db import get_db
from api.crud.session import create_session, get_session
from services.game_state import GameStateService

import random
import string

router = APIRouter(prefix="/session")


def generate_session_id():
    return ''.join(random.choices(string.digits, k=4))


@router.post("")
def create_new_session(db: Session = Depends(get_db)):
    session_id = generate_session_id()
    session = create_session(db, session_id)
    return {"session_id": session.id}


@router.get("/{session_id}")
def retrieve_session(session_id: str, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    gs = GameStateService(db, session)

    return {
        "id": session.id,
        "state": gs.state
    }
