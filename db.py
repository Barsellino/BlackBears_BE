import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings

# Завантажуємо змінні з .env
load_dotenv()

# Отримуємо URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL не знайдено в .env файлі")

# Створюємо двигун (engine) з connection pooling та SSL налаштуваннями
engine = create_engine(
    DATABASE_URL, 
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "sslmode": "require",
        "connect_timeout": 10
    }
)

# Створюємо базовий клас для моделей
Base = declarative_base()

# Фабрика сесій
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Dependency для FastAPI: отримаємо сесію та закриємо її після запиту.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print("✅ Успішне підключення!")
            print(f"Версія бази даних: {version}")
    except Exception as e:
        print("❌ Помилка підключення:")
        print(e)

if __name__ == "__main__":
    test_connection()