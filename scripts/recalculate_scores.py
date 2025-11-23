"""
Скрипт для перерахунку всіх total_score з calculated_points
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from db import SessionLocal


def recalculate_all_scores():
    """Перерахувати всі total_score для всіх учасників"""
    db = SessionLocal()
    
    try:
        # Використовуємо SQL напряму
        result = db.execute(text("""
            UPDATE tournament_participants tp
            SET total_score = COALESCE(
                (SELECT SUM(gp.calculated_points)
                 FROM game_participants gp
                 WHERE gp.participant_id = tp.id),
                0.0
            )
            RETURNING id, total_score;
        """))
        
        updated_rows = result.fetchall()
        
        print(f"✅ Оновлено {len(updated_rows)} записів")
        for row in updated_rows:
            print(f"  Учасник {row[0]}: total_score = {row[1]}")
        
        db.commit()
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("Перерахунок всіх total_score...")
    recalculate_all_scores()
