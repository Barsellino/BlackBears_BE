from enum import Enum
from typing import List


class UserRole(str, Enum):
    """Ролі користувачів у системі"""
    SUPER_ADMIN = "super_admin"  # Головний адмін - повний доступ
    ADMIN = "admin"              # Адмін - управління турнірами, користувачами
    PREMIUM = "premium"          # Преміум користувач - додаткові функції
    USER = "user"                # Звичайний користувач - базовий доступ
    
    @classmethod
    def get_hierarchy(cls) -> dict:
        """Повертає ієрархію ролей (вищі ролі включають права нижчих)"""
        return {
            cls.SUPER_ADMIN: [cls.SUPER_ADMIN, cls.ADMIN, cls.PREMIUM, cls.USER],
            cls.ADMIN: [cls.ADMIN, cls.PREMIUM, cls.USER],
            cls.PREMIUM: [cls.PREMIUM, cls.USER],
            cls.USER: [cls.USER],
        }
    
    @classmethod
    def has_permission(cls, user_role: str, required_role: str) -> bool:
        """Перевіряє, чи має користувач з user_role доступ до required_role"""
        hierarchy = cls.get_hierarchy()
        return required_role in hierarchy.get(user_role, [])
