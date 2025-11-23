from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.user import User
from jose import jwt, JWTError
from core.config import settings
from api.deps.db import get_db


class ActivityTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware для автоматичного оновлення last_seen користувача"""

    async def dispatch(self, request: Request, call_next):
        # Оновити last_seen якщо є токен
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Декодувати JWT токен
                payload = jwt.decode(
                    token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
                )
                user_id = payload.get("sub")

                if user_id:
                    # Отримати DB сесію
                    db: Session = next(get_db())
                    try:
                        user = db.query(User).filter(User.id == int(user_id)).first()
                        if user:
                            user.last_seen = datetime.now(timezone.utc)
                            db.commit()
                    finally:
                        db.close()
            except (JWTError, Exception):
                pass  # Ігноруємо помилки в middleware

        response = await call_next(request)
        return response
