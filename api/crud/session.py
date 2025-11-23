from sqlalchemy.orm import Session
from models.session import GameSession

def create_session(db: Session, session_id: str):
    session = GameSession(id=session_id, state={})
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def get_all_sessions(db: Session):
    return db.query(GameSession).all()

def get_session(db: Session, session_id: str):
    return db.query(GameSession).filter(GameSession.id == session_id).first()

def update_session_state(db: Session, session_id: str, new_state: dict):
    session = get_session(db, session_id)
    if session:
        session.state = new_state
        db.commit()
        db.refresh(session)
    return session
