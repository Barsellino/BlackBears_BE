import asyncio

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from core.exceptions import TournamentException

from db import Base, engine
from core.config import settings
from core.logging import logger
from api.ws.tick_manager import tick_manager
from models.session import GameSession  # noqa: F401
from models.user import User  # noqa: F401
from models.tournament import Tournament  # noqa: F401
from models.tournament_participant import TournamentParticipant  # noqa: F401
from models.tournament_round import TournamentRound  # noqa: F401
from models.tournament_game import TournamentGame  # noqa: F401
from models.game_participant import GameParticipant  # noqa: F401

# ROUTES
from api.routers.session import router as session_router
from api.routers.ws import router as ws_router
from api.routers.topics import router as topics_router
from api.routers.auth import router as auth_router
from api.routers.tournaments import router as tournaments_router
from api.routers.users import router as users_router
from api.routers.games import router as games_router
from api.routers.stats import router as stats_router
from api.routers.admin import router as admin_router
from api.routers.premium import router as premium_router


app = FastAPI(title="Game API", version="1.0.0")

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


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up application...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    logger.info("Starting tick manager...")
    asyncio.create_task(tick_manager.start())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down tick manager...")
    tick_manager.stop()


app.include_router(auth_router, tags=["Authentication"])
app.include_router(users_router)
app.include_router(tournaments_router)
app.include_router(games_router)
app.include_router(stats_router)
app.include_router(admin_router)
app.include_router(premium_router)
app.include_router(session_router, tags=["Session"])
app.include_router(ws_router, tags=["WS"])
app.include_router(topics_router)


@app.get("/")
def root():
    logger.info("Health check requested")
    return {"message": "OK", "status": "healthy"}