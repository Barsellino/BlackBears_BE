"""
Скрипт для створення першого super admin користувача
"""
import asyncio
from sqlalchemy import select, update
from core.database import async_session
from models.user import User
from core.roles import UserRole


async def create_super_admin(battlenet_id: str):
    """Призначити роль super_admin користувачу за battlenet_id"""
    async with async_session() as session:
        # Знайти користувача
        result = await session.execute(
            select(User).where(User.battlenet_id == battlenet_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ Користувача з battlenet_id '{battlenet_id}' не знайдено")
            return
        
        # Оновити роль
        user.role = UserRole.SUPER_ADMIN
        await session.commit()
        
        print(f"✅ Super admin створено!")
        print(f"   User ID: {user.id}")
        print(f"   BattleTag: {user.battletag}")
        print(f"   Role: {user.role}")


async def list_users():
    """Показати список всіх користувачів"""
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        if not users:
            print("❌ Користувачів не знайдено")
            return
        
        print("\n📋 Список користувачів:")
        print("-" * 80)
        for user in users:
            role_emoji = {
                UserRole.SUPER_ADMIN: "👑",
                UserRole.ADMIN: "🛡️",
                UserRole.PREMIUM: "⭐",
                UserRole.USER: "👤"
            }.get(user.role, "❓")
            
            print(f"{role_emoji} {user.battletag:20} | Role: {user.role:12} | ID: {user.battlenet_id}")
        print("-" * 80)


async def main():
    print("=" * 80)
    print("🔧 Управління Super Admin")
    print("=" * 80)
    
    while True:
        print("\nОберіть дію:")
        print("1. Показати всіх користувачів")
        print("2. Створити super admin")
        print("3. Вийти")
        
        choice = input("\nВаш вибір (1-3): ").strip()
        
        if choice == "1":
            await list_users()
        
        elif choice == "2":
            battlenet_id = input("\nВведіть BattleNet ID користувача: ").strip()
            if battlenet_id:
                await create_super_admin(battlenet_id)
            else:
                print("❌ BattleNet ID не може бути порожнім")
        
        elif choice == "3":
            print("\n👋 До побачення!")
            break
        
        else:
            print("❌ Невірний вибір. Спробуйте ще раз.")


if __name__ == "__main__":
    asyncio.run(main())
