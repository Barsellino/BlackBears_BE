# schemas/user.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from core.roles import UserRole


class UserBase(BaseModel):
    battlenet_id: str
    battletag: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    battlegrounds_rating: Optional[int] = None


class UserCreate(UserBase):
    role: UserRole = UserRole.USER


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    battlegrounds_rating: Optional[int] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserRead(UserBase):
    id: int
    role: UserRole
    is_active: bool
    last_seen: Optional[datetime] = None
    is_online: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # для SQLAlchemy моделей (раніше orm_mode = True)


class UserRoleUpdate(BaseModel):
    """Схема для зміни ролі користувача (тільки для адмінів)"""
    role: UserRole