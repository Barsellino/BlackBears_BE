import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    def __init__(self):
        self.database_url: str = os.getenv("DATABASE_URL", "")
        self.debug: bool = os.getenv("DEBUG", "False").lower() == "true"
        self.cors_origins: List[str] = [
            "http://localhost:4200",
            "http://127.0.0.1:4200",
            "https://pole-fe.vercel.app",
            "http://localhost:3000",
            "http://localhost:5173",
            "https://blackbears.com.ua"
        ]
        
        # Battle.net OAuth
        self.battlenet_client_id: str = os.getenv("BATTLENET_CLIENT_ID", "")
        self.battlenet_client_secret: str = os.getenv("BATTLENET_CLIENT_SECRET", "")
        self.battlenet_redirect_uri: str = os.getenv("BATTLENET_REDIRECT_URI", "http://localhost:8000/auth/callback")
        self.battlenet_auth_url: str = "https://oauth.battle.net/authorize"
        self.battlenet_token_url: str = "https://oauth.battle.net/token"
        self.battlenet_user_info_url: str = "https://oauth.battle.net/userinfo"
        
        # JWT
        # ВАЖЛИВО: на проді обов'язково задати JWT_SECRET_KEY через змінні оточення.
        # "fallback-secret" використовується лише для локальної розробки.
        self.jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "fallback-secret")
        self.jwt_algorithm: str = "HS256"
        # Скорочуємо час життя токена до 3 днів для кращої безпеки
        self.jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", 60 * 24 * 3))  # 3 days by default

settings = Settings()