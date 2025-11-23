"""
Міграція: Додати поле last_seen до таблиці users
"""
from sqlalchemy import create_engine, text
from core.config import settings

def run_migration():
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Додати колонку last_seen
        try:
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP WITH TIME ZONE;
            """))
            conn.commit()
            print("✅ Колонка last_seen успішно додана")
        except Exception as e:
            print(f"❌ Помилка при додаванні колонки: {e}")
            conn.rollback()

if __name__ == "__main__":
    run_migration()
