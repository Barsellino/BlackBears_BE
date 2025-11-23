"""
Додати користувача Goose#2555
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from db import SessionLocal, engine
from core.roles import UserRole


def add_goose_user():
    """Додати Goose#2555 з рейтингом 8000"""
    with engine.begin() as conn:
        # Перевірити чи вже існує
        result = conn.execute(text("""
            SELECT id, battletag, battlegrounds_rating 
            FROM users 
            WHERE battletag = 'Goose#2555'
        """))
        existing = result.fetchone()
        
        if existing:
            print(f"⚠️  Користувач Goose#2555 вже існує (ID: {existing[0]})")
            print(f"   Рейтинг: {existing[2]}")
            return
        
        # Створити нового користувача
        result = conn.execute(text("""
            INSERT INTO users (battlenet_id, battletag, name, battlegrounds_rating, role, is_active)
            VALUES ('goose2555', 'Goose#2555', 'Goose', 8000, 'user', true)
            RETURNING id, battletag, battlegrounds_rating, role;
        """))
        
        new_user = result.fetchone()
        
        print("✅ Користувача Goose#2555 додано!")
        print(f"   ID: {new_user[0]}")
        print(f"   BattleTag: {new_user[1]}")
        print(f"   Рейтинг: {new_user[2]}")
        print(f"   Роль: {new_user[3]}")


if __name__ == "__main__":
    add_goose_user()
