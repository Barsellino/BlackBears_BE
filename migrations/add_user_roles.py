"""
Міграція для додавання ролей користувачів
"""
from sqlalchemy import text
from db import engine


def upgrade():
    """Додає поле role до таблиці users"""
    with engine.begin() as conn:
        # Видаляємо старий enum якщо існує
        conn.execute(text("""
            DROP TYPE IF EXISTS userrole CASCADE;
        """))
        
        # Створюємо enum тип для ролей
        conn.execute(text("""
            CREATE TYPE userrole AS ENUM ('super_admin', 'admin', 'premium', 'user');
        """))
        
        # Додаємо колонку role з дефолтним значенням 'user'
        conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS role userrole DEFAULT 'user' NOT NULL;
        """))
        
        print("✅ Поле role успішно додано до таблиці users")
        
        # Призначаємо BarsellinO#2572 головним адміном
        result = conn.execute(text("""
            UPDATE users 
            SET role = 'super_admin' 
            WHERE battletag = 'BarsellinO#2572'
            RETURNING id, battletag, role;
        """))
        
        super_admin = result.fetchone()
        if super_admin:
            print(f"👑 Super Admin призначено: {super_admin[1]} (ID: {super_admin[0]})")
        else:
            print("⚠️  Користувача BarsellinO#2572 не знайдено. Призначте super admin вручну.")
        
        # Показуємо статистику
        result = conn.execute(text("""
            SELECT role, COUNT(*) as count 
            FROM users 
            GROUP BY role;
        """))
        
        print("\n📊 Статистика ролей:")
        for row in result:
            role_emoji = {
                'super_admin': '👑',
                'admin': '🛡️',
                'premium': '⭐',
                'user': '👤'
            }.get(row[0], '❓')
            print(f"   {role_emoji} {row[0]:12} - {row[1]} користувачів")


def downgrade():
    """Видаляє поле role з таблиці users"""
    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE users DROP COLUMN IF EXISTS role;
        """))
        
        conn.execute(text("""
            DROP TYPE IF EXISTS userrole;
        """))
        
        print("✅ Поле role видалено з таблиці users")


if __name__ == "__main__":
    print("Запуск міграції: додавання ролей користувачів...")
    upgrade()
