from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from core.roles import UserRole


class UserBase(BaseModel):
    battletag: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    battlegrounds_rating: Optional[int] = None


class UserCreate(UserBase):
    battlenet_id: str
    role: UserRole = UserRole.USER  # Дефолтна роль для нових користувачів


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    battlegrounds_rating: Optional[int] = None


class User(UserBase):
    id: int
    battlenet_id: str
    role: UserRole
    is_active: bool
    last_seen: Optional[datetime] = None
    is_online: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None


class BattlenetUserInfo(BaseModel):
    id: str
    battletag: str
    email: Optional[str] = None