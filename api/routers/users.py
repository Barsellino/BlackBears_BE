from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from api.deps.db import get_db
from api.crud.user import get_user_by_id
from schemas.auth import User
from core.auth import get_current_active_user
from models.user import User as UserModel

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/search", response_model=List[User])
async def search_users(
    battletag: str = None,
    name: str = None,
    limit: int = 10,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Search users by battletag or name"""
    query = db.query(UserModel)
    
    if battletag:
        query = query.filter(UserModel.battletag.ilike(f"%{battletag}%"))
    
    if name:
        query = query.filter(UserModel.name.ilike(f"%{name}%"))
    
    users = query.limit(limit).all()
    return users


@router.get("/{user_id}", response_model=User)
async def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get user profile by ID"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user