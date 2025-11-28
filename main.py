import asyncio

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from core.exceptions import TournamentException
from core.middleware import ActivityTrackingMiddleware
from core.rate_limit import RateLimitMiddleware

from db import Base, engine
from core.config import settings
from core.logging import logger

from models.user import User  # noqa: F401
from models.tournament import Tournament  # noqa: F401
from models.tournament_participant import TournamentParticipant  # noqa: F401
from models.tournament_round import TournamentRound  # noqa: F401
from models.tournament_game import TournamentGame  # noqa: F401
from models.game_participant import GameParticipant  # noqa: F401

# ROUTES
from api.routers.auth import router as auth_router
from api.routers.tournaments import router as tournaments_router
from api.routers.users import router as users_router
from api.routers.games import router as games_router
from api.routers.stats import router as stats_router
from api.routers.admin import router as admin_router
from api.routers.premium import router as premium_router


app = FastAPI(title="Game API", version="1.0.0")

# Rate limiting middleware (має бути першим для захисту від DDoS)
app.add_middleware(RateLimitMiddleware, requests_per_minute=150, requests_per_hour=2100)

# Activity tracking middleware (має бути перед CORS)
app.add_middleware(ActivityTrackingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(TournamentException)
async def tournament_exception_handler(request: Request, exc: TournamentException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "type": "tournament_error"}
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "type": "validation_error"}
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    import traceback
    error_traceback = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"Unhandled exception: {error_traceback}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__,
            "traceback": error_traceback
        }
    )


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up application...")
    
    # Run database migrations automatically
    try:
        import subprocess
        logger.info("Running database migrations...")
        result = subprocess.run(
            ["python3", "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Migrations completed successfully: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed: {e.stderr}")
        raise RuntimeError(f"Database migration failed: {e.stderr}")
    
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application...")


app.include_router(auth_router, tags=["Authentication"])
app.include_router(users_router)
app.include_router(tournaments_router)
app.include_router(games_router)
app.include_router(stats_router)
app.include_router(admin_router)
app.include_router(premium_router)


