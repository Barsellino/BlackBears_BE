from sqlalchemy.orm import Session
from models.user import User
from schemas.auth import UserCreate, UserUpdate


def get_user_by_battlenet_id(db: Session, battlenet_id: str):
    return db.query(User).filter(User.battlenet_id == battlenet_id).first()


def create_user(db: Session, user: UserCreate):
    db_user = User(
        battlenet_id=user.battlenet_id,
        battletag=user.battletag,
        email=user.email,
        battlegrounds_rating=user.battlegrounds_rating,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def update_user(db: Session, user_id: int, user_update: UserUpdate):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user