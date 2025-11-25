"""
Seed test users via Python script
Run with: python3 seed_users.py
"""
import os
from sqlalchemy import create_engine, text
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection from .env
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file!")

engine = create_engine(DATABASE_URL)

def seed_test_users():
    """Add 20 test users to the database"""
    
    test_users = [
        ("TEST001", "ProGamer#1234", "Alex Johnson", "alex@test.com", 8500, "user"),
        ("TEST002", "DragonSlayer#5678", "Maria Garcia", "maria@test.com", 7800, "user"),
        ("TEST003", "NightHawk#9012", "John Smith", "john@test.com", 9200, "premium"),
        ("TEST004", "ShadowBlade#3456", "Emma Wilson", "emma@test.com", 6500, "user"),
        ("TEST005", "ThunderStrike#7890", "Michael Brown", "michael@test.com", 8100, "user"),
        ("TEST006", "IceQueen#2345", "Sofia Martinez", "sofia@test.com", 7500, "premium"),
        ("TEST007", "FireStorm#6789", "David Lee", "david@test.com", 8800, "user"),
        ("TEST008", "MysticMage#0123", "Olivia Taylor", "olivia@test.com", 7200, "user"),
        ("TEST009", "StealthNinja#4567", "James Anderson", "james@test.com", 9000, "premium"),
        ("TEST010", "CrimsonKnight#8901", "Isabella Thomas", "isabella@test.com", 6800, "user"),
        ("TEST011", "GoldenEagle#2346", "William Jackson", "william@test.com", 8300, "user"),
        ("TEST012", "SilverWolf#6780", "Ava White", "ava@test.com", 7600, "premium"),
        ("TEST013", "PhoenixRising#0124", "Robert Harris", "robert@test.com", 8900, "user"),
        ("TEST014", "VenomStrike#4568", "Mia Martin", "mia@test.com", 7100, "user"),
        ("TEST015", "TitanForce#8902", "Daniel Thompson", "daniel@test.com", 8600, "premium"),
        ("TEST016", "LunarEclipse#2347", "Charlotte Garcia", "charlotte@test.com", 7400, "user"),
        ("TEST017", "SolarFlare#6781", "Joseph Martinez", "joseph@test.com", 8200, "user"),
        ("TEST018", "CosmicRay#0125", "Amelia Robinson", "amelia@test.com", 7700, "premium"),
        ("TEST019", "QuantumLeap#4569", "Christopher Clark", "chris@test.com", 9100, "user"),
        ("TEST020", "NebulaDrift#8903", "Harper Rodriguez", "harper@test.com", 6900, "user"),
        # TestBattletag users (0001-0050)
        ("TEST021", "TestBattletag#0001", "Test User 1", "testuser1@test.com", 7000, "user"),
        ("TEST022", "TestBattletag#0002", "Test User 2", "testuser2@test.com", 7100, "user"),
        ("TEST023", "TestBattletag#0003", "Test User 3", "testuser3@test.com", 7200, "premium"),
        ("TEST024", "TestBattletag#0004", "Test User 4", "testuser4@test.com", 7300, "user"),
        ("TEST025", "TestBattletag#0005", "Test User 5", "testuser5@test.com", 7400, "user"),
        ("TEST026", "TestBattletag#0006", "Test User 6", "testuser6@test.com", 7500, "premium"),
        ("TEST027", "TestBattletag#0007", "Test User 7", "testuser7@test.com", 7600, "user"),
        ("TEST028", "TestBattletag#0008", "Test User 8", "testuser8@test.com", 7700, "user"),
        ("TEST029", "TestBattletag#0009", "Test User 9", "testuser9@test.com", 7800, "premium"),
        ("TEST030", "TestBattletag#0010", "Test User 10", "testuser10@test.com", 7900, "user"),
        ("TEST031", "TestBattletag#0011", "Test User 11", "testuser11@test.com", 8000, "user"),
        ("TEST032", "TestBattletag#0012", "Test User 12", "testuser12@test.com", 8100, "premium"),
        ("TEST033", "TestBattletag#0013", "Test User 13", "testuser13@test.com", 8200, "user"),
        ("TEST034", "TestBattletag#0014", "Test User 14", "testuser14@test.com", 8300, "user"),
        ("TEST035", "TestBattletag#0015", "Test User 15", "testuser15@test.com", 8400, "premium"),
        ("TEST036", "TestBattletag#0016", "Test User 16", "testuser16@test.com", 8500, "user"),
        ("TEST037", "TestBattletag#0017", "Test User 17", "testuser17@test.com", 8600, "user"),
        ("TEST038", "TestBattletag#0018", "Test User 18", "testuser18@test.com", 8700, "premium"),
        ("TEST039", "TestBattletag#0019", "Test User 19", "testuser19@test.com", 8800, "user"),
        ("TEST040", "TestBattletag#0020", "Test User 20", "testuser20@test.com", 8900, "user"),
        ("TEST041", "TestBattletag#0021", "Test User 21", "testuser21@test.com", 9000, "premium"),
        ("TEST042", "TestBattletag#0022", "Test User 22", "testuser22@test.com", 6500, "user"),
        ("TEST043", "TestBattletag#0023", "Test User 23", "testuser23@test.com", 6600, "user"),
        ("TEST044", "TestBattletag#0024", "Test User 24", "testuser24@test.com", 6700, "premium"),
        ("TEST045", "TestBattletag#0025", "Test User 25", "testuser25@test.com", 6800, "user"),
        ("TEST046", "TestBattletag#0026", "Test User 26", "testuser26@test.com", 6900, "user"),
        ("TEST047", "TestBattletag#0027", "Test User 27", "testuser27@test.com", 7000, "premium"),
        ("TEST048", "TestBattletag#0028", "Test User 28", "testuser28@test.com", 7100, "user"),
        ("TEST049", "TestBattletag#0029", "Test User 29", "testuser29@test.com", 7200, "user"),
        ("TEST050", "TestBattletag#0030", "Test User 30", "testuser30@test.com", 7300, "premium"),
        ("TEST051", "TestBattletag#0031", "Test User 31", "testuser31@test.com", 7400, "user"),
        ("TEST052", "TestBattletag#0032", "Test User 32", "testuser32@test.com", 7500, "user"),
        ("TEST053", "TestBattletag#0033", "Test User 33", "testuser33@test.com", 7600, "premium"),
        ("TEST054", "TestBattletag#0034", "Test User 34", "testuser34@test.com", 7700, "user"),
        ("TEST055", "TestBattletag#0035", "Test User 35", "testuser35@test.com", 7800, "user"),
        ("TEST056", "TestBattletag#0036", "Test User 36", "testuser36@test.com", 7900, "premium"),
        ("TEST057", "TestBattletag#0037", "Test User 37", "testuser37@test.com", 8000, "user"),
        ("TEST058", "TestBattletag#0038", "Test User 38", "testuser38@test.com", 8100, "user"),
        ("TEST059", "TestBattletag#0039", "Test User 39", "testuser39@test.com", 8200, "premium"),
        ("TEST060", "TestBattletag#0040", "Test User 40", "testuser40@test.com", 8300, "user"),
        ("TEST061", "TestBattletag#0041", "Test User 41", "testuser41@test.com", 8400, "user"),
        ("TEST062", "TestBattletag#0042", "Test User 42", "testuser42@test.com", 8500, "premium"),
        ("TEST063", "TestBattletag#0043", "Test User 43", "testuser43@test.com", 8600, "user"),
        ("TEST064", "TestBattletag#0044", "Test User 44", "testuser44@test.com", 8700, "user"),
        ("TEST065", "TestBattletag#0045", "Test User 45", "testuser45@test.com", 8800, "premium"),
        ("TEST066", "TestBattletag#0046", "Test User 46", "testuser46@test.com", 8900, "user"),
        ("TEST067", "TestBattletag#0047", "Test User 47", "testuser47@test.com", 9000, "user"),
        ("TEST068", "TestBattletag#0048", "Test User 48", "testuser48@test.com", 9100, "premium"),
        ("TEST069", "TestBattletag#0049", "Test User 49", "testuser49@test.com", 9200, "user"),
        ("TEST070", "TestBattletag#0050", "Test User 50", "testuser50@test.com", 9300, "user"),
    ]
    
    added_count = 0
    skipped_count = 0
    
    with engine.connect() as conn:
        for battlenet_id, battletag, name, email, rating, role in test_users:
            # Check if user exists
            result = conn.execute(
                text("SELECT COUNT(*) FROM users WHERE battlenet_id = :bid"),
                {"bid": battlenet_id}
            )
            exists = result.scalar() > 0
            
            if exists:
                print(f"⏭️  Skipped {battletag} (already exists)")
                skipped_count += 1
                continue
            
            # Insert user
            conn.execute(
                text("""
                    INSERT INTO users (battlenet_id, battletag, name, email, battlegrounds_rating, role, is_active, last_seen, settings)
                    VALUES (:bid, :btag, :name, :email, :rating, :role, true, :last_seen, :settings)
                """),
                {
                    "bid": battlenet_id,
                    "btag": battletag,
                    "name": name,
                    "email": email,
                    "rating": rating,
                    "role": role,
                    "last_seen": datetime.utcnow(),
                    "settings": "{}"
                }
            )
            print(f"✅ Added {battletag} (Rating: {rating})")
            added_count += 1
        
        conn.commit()
        
        # Get total count
        result = conn.execute(text("SELECT COUNT(*) FROM users WHERE battlenet_id LIKE 'TEST%'"))
        total = result.scalar()
    
    print(f"\n📊 Summary:")
    print(f"   ✅ Added: {added_count}")
    print(f"   ⏭️  Skipped: {skipped_count}")
    print(f"   📦 Total test users in DB: {total}")

if __name__ == "__main__":
    print("🌱 Seeding test users...\n")
    seed_test_users()
    print("\n✨ Done!")

