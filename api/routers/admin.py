"""
Роутер для адміністративних функцій
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy.orm.attributes import flag_modified

from core.auth import get_admin, get_super_admin, get_current_active_user
from core.roles import UserRole
from api.deps.db import get_db
from models.user import User
from schemas.user import UserRead, UserRoleUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
async def get_all_users(
    limit: int = 20,
    offset: int = 0,
    search: str = None,
    role: UserRole = None,
    is_active: bool = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin)
):
    """
    Отримати список користувачів з пагінацією та фільтрами (доступно адмінам)
    
    Параметри:
    - limit: кількість записів (макс 100)
    - offset: зсув від початку (скільки пропустити)
    - search: пошук по battletag, name, email
    - role: фільтр по ролі (super_admin, admin, premium, user)
    - is_active: фільтр по активності (true/false)
    - sort_by: поле для сортування (created_at, battletag, battlegrounds_rating, last_seen)
    - sort_order: порядок сортування (asc/desc)
    """
    # Валідація параметрів
    limit = min(max(1, limit), 100)
    offset = max(0, offset)
    
    # Базовий запит
    query = db.query(User)
    
    # Фільтр по пошуку
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.battletag.ilike(search_filter)) |
            (User.name.ilike(search_filter)) |
            (User.email.ilike(search_filter))
        )
    
    # Фільтр по ролі
    if role:
        query = query.filter(User.role == role)
    
    # Фільтр по активності
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Підрахунок загальної кількості
    total = query.count()
    
    # Сортування
    sort_column = getattr(User, sort_by, User.created_at)
    if sort_order == "desc":
        # Для last_seen та інших полів, де NULL має бути в кінці
        query = query.order_by(sort_column.desc().nulls_last())
    else:
        query = query.order_by(sort_column.asc().nulls_last())
    
    # Пагінація
    users = query.offset(offset).limit(limit).all()
    
    return {
        "data": [
            {
                "id": user.id,
                "battlenet_id": user.battlenet_id,
                "battletag": user.battletag,
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
                "battlegrounds_rating": user.battlegrounds_rating,
                "role": user.role,
                "is_active": user.is_active,
                "last_seen": user.last_seen,
                "is_online": user.is_online,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
            for user in users
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.patch("/users/{user_id}/role", response_model=UserRead)
async def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin)
):
    """
    Змінити роль користувача
    - Адміни можуть змінювати ролі USER та PREMIUM
    - Тільки SUPER_ADMIN може призначати ролі ADMIN та SUPER_ADMIN
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Перевірка прав: тільки super_admin може призначати admin ролі
    if role_update.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admin can assign admin roles"
            )
    
    # Не можна змінити роль самого себе
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
    user.role = role_update.role
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_super_admin)
):
    """Деактивувати користувача (тільки для super admin)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    user.is_active = False
    db.commit()
    return {"message": f"User {user.battletag} deactivated"}


@router.get("/me/permissions")
async def get_my_permissions(current_user: User = Depends(get_current_active_user)):
    """Отримати інформацію про свої права доступу"""
    hierarchy = UserRole.get_hierarchy()
    return {
        "user_id": current_user.id,
        "battletag": current_user.battletag,
        "role": current_user.role,
        "permissions": hierarchy.get(current_user.role, [])
    }


@router.get("/stats")
async def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin)
):
    """Отримати статистику по користувачам (доступно адмінам)"""
    from sqlalchemy import func
    
    # Статистика по ролях
    role_stats = db.query(
        User.role,
        func.count(User.id).label('count')
    ).group_by(User.role).all()
    
    # Статистика по активності
    active_count = db.query(User).filter(User.is_active == True).count()
    inactive_count = db.query(User).filter(User.is_active == False).count()
    
    # Загальна кількість
    total_users = db.query(User).count()
    
    # Нові користувачі за останні 7 днів
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_week = db.query(User).filter(User.created_at >= week_ago).count()
    
    # Нові користувачі за останні 30 днів
    month_ago = datetime.utcnow() - timedelta(days=30)
    new_users_month = db.query(User).filter(User.created_at >= month_ago).count()
    
    return {
        "total_users": total_users,
        "active_users": active_count,
        "inactive_users": inactive_count,
        "new_users_week": new_users_week,
        "new_users_month": new_users_month,
        "roles": {
            role.value: count for role, count in role_stats
        }
    }

# ----------------------------------------------------------------------
# Global favorite lobby makers (per user)
# ----------------------------------------------------------------------

@router.get("/favorite-lobby-makers")
async def get_favorite_lobby_makers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return the logged‑in user's global favorite lobby makers list (ordered)."""
    fav = current_user.favorite_lobby_makers or []
    users = db.query(User).filter(User.id.in_(fav)).all()
    ordered = sorted(
        users,
        key=lambda u: fav.index(u.id) if u.id in fav else len(fav),
    )
    return {
        "priority_list": [
            {"user_id": u.id, "battletag": u.battletag, "name": u.name}
            for u in ordered
        ]
    }

@router.post("/favorite-lobby-makers")
async def add_favorite_lobby_maker(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Add a user to the caller's favorite lobby makers (append to end)."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    fav = current_user.favorite_lobby_makers or []
    if user_id not in fav:
        fav.append(user_id)
        current_user.favorite_lobby_makers = fav
        flag_modified(current_user, "favorite_lobby_makers")
        db.commit()
    return {"message": "Added", **(await get_favorite_lobby_makers(db=db, current_user=current_user))}

@router.delete("/favorite-lobby-makers/{user_id}")
async def delete_favorite_lobby_maker(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Remove a user from the caller's favorite lobby makers list."""
    fav = current_user.favorite_lobby_makers or []
    if user_id in fav:
        fav.remove(user_id)
        current_user.favorite_lobby_makers = fav
        flag_modified(current_user, "favorite_lobby_makers")
        db.commit()
    return {"message": "Removed", **(await get_favorite_lobby_makers(db=db, current_user=current_user))}

@router.put("/favorite-lobby-makers/order")
async def reorder_favorite_lobby_makers(
    priority_list: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Replace the whole ordering of favorite lobby makers.
    The list must contain exactly the same user IDs currently stored.
    """
    current = set(current_user.favorite_lobby_makers or [])
    if set(priority_list) != current:
        raise HTTPException(
            status_code=400,
            detail="Priority list must contain the same user IDs as current favorites",
        )
    current_user.favorite_lobby_makers = priority_list
    flag_modified(current_user, "favorite_lobby_makers")
    db.commit()
    return {"message": "Order updated", **(await get_favorite_lobby_makers(db=db, current_user=current_user))}

