"""
Скрипт для видалення всіх таблиць крім users
"""
from sqlalchemy import text
from db import engine


def drop_tables_except_users():
    """Видалити всі таблиці крім users"""
    with engine.begin() as conn:
        print("🗑️  Видалення таблиць (крім users)...")
        
        # Список таблиць для видалення
        tables_to_drop = [
            'game_participants',
            'tournament_games',
            'tournament_rounds',
            'tournament_participants',
            'tournaments',
            'game_sessions'
        ]
        
        for table in tables_to_drop:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
                print(f"  ✅ Видалено таблицю: {table}")
            except Exception as e:
                print(f"  ⚠️  Помилка при видаленні {table}: {e}")
        
        print("\n✅ Готово! Таблиця users збережена.")
        print("\nТепер можна перестворити таблиці через:")
        print("  python -c 'from db import Base, engine; Base.metadata.create_all(bind=engine)'")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        drop_tables_except_users()
    else:
        confirm = input("⚠️  Це видалить всі дані турнірів та ігор! Продовжити? (yes/no): ")
        if confirm.lower() == 'yes':
            drop_tables_except_users()
        else:
            print("❌ Скасовано")
