"""
Роутер для преміум функцій
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.auth import get_premium_user, get_current_active_user
from api.deps.db import get_db
from models.user import User

router = APIRouter(prefix="/premium", tags=["premium"])


@router.get("/features")
async def get_premium_features(current_user: User = Depends(get_premium_user)):
    """
    Отримати доступ до преміум функцій
    Доступно тільки для користувачів з роллю PREMIUM або вище
    """
    return {
        "message": "Welcome to premium features!",
        "user": current_user.battletag,
        "role": current_user.role,
        "features": [
            "Advanced tournament statistics",
            "Priority tournament registration",
            "Custom profile themes",
            "Ad-free experience",
            "Early access to new features"
        ]
    }



@router.get("/stats/advanced")
async def get_advanced_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_premium_user)
):
    """Розширена статистика (тільки для преміум)"""
    return {
        "user_id": current_user.id,
        "message": "Advanced statistics available for premium users",
        "stats": {
            "total_tournaments": 0,  # TODO: реальна статистика
            "win_rate": 0.0,
            "average_placement": 0.0,
            "best_performance": None
        }
    }


@router.get("/check-access")
async def check_premium_access(current_user: User = Depends(get_current_active_user)):
    """Перевірити, чи має користувач преміум доступ"""
    from core.roles import UserRole
    has_premium = UserRole.has_permission(current_user.role, UserRole.PREMIUM)
    
    return {
        "user": current_user.battletag,
        "role": current_user.role,
        "has_premium_access": has_premium
    }
