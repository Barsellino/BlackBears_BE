from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.user import User
from jose import jwt, JWTError
from core.config import settings
from db import SessionLocal
from core.logging import logger


class ActivityTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware для автоматичного оновлення last_seen користувача"""

    async def dispatch(self, request: Request, call_next):
        # Оновити last_seen якщо є токен
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            db: Session = None
            try:
                # Декодувати JWT токен з перевіркою audience
                payload = jwt.decode(
                    token,
                    settings.jwt_secret_key,
                    algorithms=[settings.jwt_algorithm],
                    audience="blackbears-frontend",
                )
                # Перевірка issuer
                issuer = payload.get("iss")
                if issuer != "blackbears-backend":
                    raise JWTError("Invalid issuer")
                
                user_id = payload.get("sub")

                if user_id:
                    # Створити DB сесію напряму
                    db = SessionLocal()
                    try:
                        user = db.query(User).filter(User.id == int(user_id)).first()
                        if user:
                            user.last_seen = datetime.now(timezone.utc)
                            db.commit()
                    except Exception as e:
                        logger.error(f"Error updating last_seen for user {user_id}: {e}")
                        db.rollback()
                    finally:
                        if db:
                            db.close()
            except JWTError:
                # Невірний токен - ігноруємо
                pass
            except Exception as e:
                # Інші помилки - логуємо, але не блокуємо запит
                logger.warning(f"ActivityTrackingMiddleware error: {e}")

        response = await call_next(request)
        return response
