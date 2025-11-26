import sys
sys.path.insert(0, '/Users/maksimdriga/PycharmProjects/BleackBears_BE')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

db = SessionLocal()

# Update user role
from sqlalchemy import text
result = db.execute(
    text("UPDATE users SET role = 'super_admin' WHERE battletag = 'BarsellinO#2572'")
)
db.commit()

if result.rowcount > 0:
    print(f"✅ BarsellinO#2572 тепер SUPER_ADMIN!")
else:
    print("❌ Користувача не знайдено")

db.close()
