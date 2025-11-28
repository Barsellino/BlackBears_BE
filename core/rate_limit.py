from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple
import time


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware для захисту від DDoS.
    Обмежує кількість запитів з одного IP.
    """
    
    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        # {ip: [(timestamp, ...), ...]}
        self.request_history: Dict[str, list] = defaultdict(list)
        self._cleanup_interval = timedelta(minutes=5)
        self._last_cleanup = datetime.now()
    
    def _get_client_ip(self, request: Request) -> str:
        """Отримати IP клієнта"""
        # Перевіряємо заголовки проксі
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _cleanup_old_requests(self):
        """Очистити старі запити (старше 1 години)"""
        now = datetime.now()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff_minute = now - timedelta(minutes=1)
        cutoff_hour = now - timedelta(hours=1)
        
        for ip in list(self.request_history.keys()):
            # Залишити тільки запити за останню хвилину та годину
            self.request_history[ip] = [
                ts for ts in self.request_history[ip]
                if ts > cutoff_hour
            ]
            
            # Видалити порожні записи
            if not self.request_history[ip]:
                del self.request_history[ip]
        
        self._last_cleanup = now
    
    def _check_rate_limit(self, ip: str) -> Tuple[bool, str]:
        """Перевірити чи не перевищено ліміт"""
        now = datetime.now()
        cutoff_minute = now - timedelta(minutes=1)
        cutoff_hour = now - timedelta(hours=1)
        
        # Підрахувати запити за останню хвилину
        requests_last_minute = sum(
            1 for ts in self.request_history[ip]
            if ts > cutoff_minute
        )
        
        # Підрахувати запити за останню годину
        requests_last_hour = sum(
            1 for ts in self.request_history[ip]
            if ts > cutoff_hour
        )
        
        # Перевірити ліміти
        if requests_last_minute >= self.requests_per_minute:
            return False, f"Rate limit exceeded: {requests_per_minute} requests per minute"
        
        if requests_last_hour >= self.requests_per_hour:
            return False, f"Rate limit exceeded: {requests_per_hour} requests per hour"
        
        # Додати поточний запит
        self.request_history[ip].append(now)
        
        return True, ""
    
    async def dispatch(self, request: Request, call_next):
        # Пропускаємо rate limiting для health check та статичних файлів
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Очистити старі запити
        self._cleanup_old_requests()
        
        # Отримати IP клієнта
        client_ip = self._get_client_ip(request)
        
        # Перевірити rate limit
        allowed, error_msg = self._check_rate_limit(client_ip)
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_msg,
                headers={"Retry-After": "60"}
            )
        
        response = await call_next(request)
        return response

