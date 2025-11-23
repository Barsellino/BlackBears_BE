# Швидкий старт: Система ролей

## 1. Запустити міграцію

```bash
python migrations/add_user_roles.py
```

## 2. Створити першого super admin

```bash
python create_super_admin.py
```

Або вручну через SQL:
```sql
UPDATE users SET role = 'super_admin' WHERE battlenet_id = 'YOUR_ID';
```

## 3. Використання в коді

### Захист ендпоінту за роллю

```python
from fastapi import APIRouter, Depends
from core.auth import get_admin, get_premium_user, get_super_admin
from models.user import User

router = APIRouter()

# Тільки для адмінів
@router.get("/admin-only")
async def admin_only(user: User = Depends(get_admin)):
    return {"message": "Admin access"}

# Тільки для преміум
@router.get("/premium-only")
async def premium_only(user: User = Depends(get_premium_user)):
    return {"message": "Premium access"}

# Тільки для super admin
@router.get("/super-admin-only")
async def super_admin_only(user: User = Depends(get_super_admin)):
    return {"message": "Super admin access"}
```

### Перевірка ролі в коді

```python
from core.roles import UserRole

# Перевірити доступ
if UserRole.has_permission(user.role, UserRole.PREMIUM):
    # Користувач має преміум або вище
    show_premium_features()
```

## 4. Ієрархія ролей

```
SUPER_ADMIN (👑) - має доступ до всього
    ↓
ADMIN (🛡️) - має доступ до admin, premium, user
    ↓
PREMIUM (⭐) - має доступ до premium, user
    ↓
USER (👤) - базовий доступ
```

## 5. API ендпоінти

### Адмін функції
- `GET /admin/users` - всі користувачі
- `PATCH /admin/users/{id}/role` - змінити роль
- `DELETE /admin/users/{id}` - деактивувати
- `GET /admin/me/permissions` - мої права

### Преміум функції
- `GET /premium/features` - список функцій
- `GET /premium/stats/advanced` - розширена статистика
- `GET /premium/check-access` - перевірити доступ

## 6. Приклади запитів

```bash
# Змінити роль на premium
curl -X PATCH "http://localhost:8000/admin/users/123/role" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "premium"}'

# Перевірити свої права
curl -X GET "http://localhost:8000/admin/me/permissions" \
  -H "Authorization: Bearer TOKEN"
```

Готово! 🚀
