# Система ролей користувачів

## Ролі

Система підтримує 4 рівні доступу з ієрархією (вищі ролі мають всі права нижчих):

1. **SUPER_ADMIN** (`super_admin`) - Головний адміністратор
   - Повний доступ до всіх функцій
   - Може призначати будь-які ролі
   - Може деактивувати користувачів

2. **ADMIN** (`admin`) - Адміністратор
   - Управління турнірами
   - Перегляд всіх користувачів
   - Може змінювати ролі USER та PREMIUM
   - Доступ до всіх преміум функцій

3. **PREMIUM** (`premium`) - Преміум користувач
   - Розширена статистика
   - Пріоритетна реєстрація на турніри
   - Кастомні теми профілю
   - Без реклами
   - Ранній доступ до нових функцій

4. **USER** (`user`) - Звичайний користувач
   - Базовий доступ
   - Участь у турнірах
   - Перегляд статистики

## Міграція

Запустіть міграцію для додавання поля `role`:

```bash
python migrations/add_user_roles.py
```

## Використання в коді

### Перевірка ролі в ендпоінті

```python
from fastapi import APIRouter, Depends
from core.auth import get_admin, get_premium_user, require_role
from core.roles import UserRole
from models.user import User

router = APIRouter()

# Варіант 1: Використання готових dependency
@router.get("/admin-only")
async def admin_endpoint(current_user: User = Depends(get_admin)):
    return {"message": "Admin access"}

# Варіант 2: Використання require_role для кастомних ролей
@router.get("/premium-only")
async def premium_endpoint(current_user: User = Depends(require_role(UserRole.PREMIUM))):
    return {"message": "Premium access"}
```

### Перевірка прав у коді

```python
from core.roles import UserRole

# Перевірити, чи має користувач доступ до певної ролі
if UserRole.has_permission(user.role, UserRole.PREMIUM):
    # Користувач має преміум доступ або вище
    pass
```

## API Endpoints

### Адміністративні

- `GET /admin/users` - Список всіх користувачів (ADMIN+)
- `PATCH /admin/users/{user_id}/role` - Змінити роль користувача (ADMIN+)
- `DELETE /admin/users/{user_id}` - Деактивувати користувача (SUPER_ADMIN)
- `GET /admin/me/permissions` - Переглянути свої права

### Преміум функції

- `GET /premium/features` - Список преміум функцій (PREMIUM+)
- `GET /premium/stats/advanced` - Розширена статистика (PREMIUM+)
- `GET /premium/check-access` - Перевірити преміум доступ (всі)

## Приклади запитів

### Змінити роль користувача

```bash
# Призначити преміум
curl -X PATCH "http://localhost:8000/admin/users/123/role" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "premium"}'

# Призначити адміна (тільки super_admin)
curl -X PATCH "http://localhost:8000/admin/users/123/role" \
  -H "Authorization: Bearer SUPER_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

### Перевірити свої права

```bash
curl -X GET "http://localhost:8000/admin/me/permissions" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Створення першого super admin

Після міграції всі користувачі матимуть роль `user`. Щоб створити першого super admin, виконайте SQL:

```sql
UPDATE users 
SET role = 'super_admin' 
WHERE battlenet_id = 'YOUR_BATTLENET_ID';
```

Або створіть скрипт:

```python
# create_super_admin.py
import asyncio
from sqlalchemy import select, update
from core.database import async_session
from models.user import User
from core.roles import UserRole

async def create_super_admin(battlenet_id: str):
    async with async_session() as session:
        result = await session.execute(
            update(User)
            .where(User.battlenet_id == battlenet_id)
            .values(role=UserRole.SUPER_ADMIN)
        )
        await session.commit()
        print(f"✅ Super admin created for {battlenet_id}")

if __name__ == "__main__":
    battlenet_id = input("Enter BattleNet ID: ")
    asyncio.run(create_super_admin(battlenet_id))
```

## Інтеграція з існуючими роутерами

Додайте нові роутери до `main.py`:

```python
from api.routers import admin, premium

app.include_router(admin.router)
app.include_router(premium.router)
```
