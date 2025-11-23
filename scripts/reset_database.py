#!/usr/bin/env python3

from db import engine
from sqlalchemy import text

def reset_database():
    """Reset database - keep users but clear all tournament data"""
    
    reset_sql = """
    -- Clear all tournament-related data (keep users)
    DELETE FROM game_participants;
    DELETE FROM tournament_games;
    DELETE FROM tournament_rounds;
    DELETE FROM tournament_participants;
    DELETE FROM tournaments;
    
    -- Reset sequences
    ALTER SEQUENCE tournaments_id_seq RESTART WITH 1;
    ALTER SEQUENCE tournament_participants_id_seq RESTART WITH 1;
    ALTER SEQUENCE tournament_rounds_id_seq RESTART WITH 1;
    ALTER SEQUENCE tournament_games_id_seq RESTART WITH 1;
    ALTER SEQUENCE game_participants_id_seq RESTART WITH 1;
    
    -- Show remaining data
    SELECT 'Users count:' as info, COUNT(*) as count FROM users
    UNION ALL
    SELECT 'Tournaments count:', COUNT(*) FROM tournaments;
    """
    
    try:
        with engine.connect() as connection:
            result = connection.execute(text(reset_sql))
            connection.commit()
            
            # Show results
            rows = result.fetchall()
            for row in rows:
                print(f"{row[0]} {row[1]}")
            
            print("✅ Database reset complete!")
            print("📊 Users preserved, all tournament data cleared")
            print("🎯 Ready for new tournaments with position-based scoring")
            
    except Exception as e:
        print(f"❌ Error resetting database: {e}")

if __name__ == "__main__":
    print("🔄 Resetting database...")
    print("⚠️  This will delete ALL tournament data but keep users")
    
    confirm = input("Continue? (y/N): ")
    if confirm.lower() == 'y':
        reset_database()
    else:
        print("❌ Reset cancelled")