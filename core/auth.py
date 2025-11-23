from datetime import datetime, timedelta
from typing import Optional, List
from functools import wraps
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from core.config import settings
from core.roles import UserRole
from api.deps.db import get_db
from models.user import User
from schemas.auth import TokenData

security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    return token_data


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(credentials.credentials, credentials_exception)
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_role(required_role: UserRole):
    """
    Декоратор для перевірки ролі користувача.
    Використовує ієрархію ролей - вищі ролі мають доступ до функцій нижчих.
    
    Приклад використання:
    @router.get("/admin-only")
    async def admin_endpoint(user: User = Depends(require_role(UserRole.ADMIN))):
        return {"message": "Admin access granted"}
    """
    def role_checker(current_user: User = Depends(get_current_active_user)):
        if not UserRole.has_permission(current_user.role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role.value}"
            )
        return current_user
    return role_checker


def get_super_admin(current_user: User = Depends(require_role(UserRole.SUPER_ADMIN))):
    """Dependency для ендпоінтів, доступних тільки головному адміну"""
    return current_user


def get_admin(current_user: User = Depends(require_role(UserRole.ADMIN))):
    """Dependency для ендпоінтів, доступних адмінам і вище"""
    return current_user


def get_premium_user(current_user: User = Depends(require_role(UserRole.PREMIUM))):
    """Dependency для ендпоінтів, доступних преміум користувачам і вище"""
    return current_user