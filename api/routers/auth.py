from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import secrets
import os
from api.deps.db import get_db
from api.crud.user import get_user_by_battlenet_id, create_user, update_user
from schemas.auth import UserCreate, UserUpdate, Token, User as UserSchema
from services.battlenet_service import battlenet_service
from core.auth import create_access_token, get_current_active_user
from core.logging import logger

router = APIRouter(prefix="/auth")


@router.get("/login")
async def login():
    """Redirect to Battle.net OAuth login"""
    state = secrets.token_urlsafe(32)
    auth_url = battlenet_service.get_authorization_url(state=state)
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def auth_callback(code: str, state: str = None, db: Session = Depends(get_db)):
    """Handle Battle.net OAuth callback"""
    try:
        logger.info(f"Auth callback started with code: {code[:10]}... and state: {state}")
        
        # Exchange code for access token
        logger.info("Exchanging code for token...")
        access_token = await battlenet_service.exchange_code_for_token(code)
        if not access_token:
            logger.error("Failed to get access token")
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        logger.info(f"Got access token: {access_token[:10]}...")
        
        # Get user info from Battle.net
        logger.info("Getting user info from Battle.net...")
        user_info = await battlenet_service.get_user_info(access_token)
        if not user_info:
            logger.error("Failed to get user info")
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        logger.info(f"Got user info: {user_info.battletag}")
        
        # Get Battlegrounds rating
        logger.info("Getting Battlegrounds rating...")
        bg_rating = await battlenet_service.get_battlegrounds_rating(access_token, user_info.id)
        logger.info(f"Battlegrounds rating: {bg_rating}")
        
        # Check if user exists or create new one (with retry for DB connection issues)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                db_user = get_user_by_battlenet_id(db, user_info.id)
                if not db_user:
                    logger.info("Creating new user...")
                    user_create = UserCreate(
                        battlenet_id=user_info.id,
                        battletag=user_info.battletag,
                        email=user_info.email,
                        battlegrounds_rating=bg_rating
                    )
                    db_user = create_user(db, user_create)
                    logger.info(f"Created new user: {user_info.battletag} with BG rating: {bg_rating}")
                else:
                    # Оновити дані користувача при логіні
                    logger.info(f"User logged in: {user_info.battletag}")
                    update_data = UserUpdate(
                        battlegrounds_rating=bg_rating
                    )
                    # Оновити email якщо його немає або він змінився
                    if user_info.email and (not db_user.email or db_user.email != user_info.email):
                        logger.info(f"Updating email for user {user_info.battletag}: {user_info.email}")
                        db_user.email = user_info.email
                    # Оновити battletag якщо змінився
                    if db_user.battletag != user_info.battletag:
                        logger.info(f"Updating battletag: {db_user.battletag} -> {user_info.battletag}")
                        db_user.battletag = user_info.battletag
                    # Оновити рейтинг
                    db_user.battlegrounds_rating = bg_rating
                    db.commit()
                    db.refresh(db_user)
                break
            except Exception as db_error:
                logger.warning(f"Database attempt {attempt + 1} failed: {str(db_error)}")
                if attempt == max_retries - 1:
                    raise db_error
                # Get new DB session for retry
                db.close()
                from api.deps.db import get_db
                db = next(get_db())
        
        # Create JWT token
        logger.info("Creating JWT token...")
        jwt_token = create_access_token(data={"sub": str(db_user.id)})
        
        # Redirect to frontend with token (using hash routing)
        # Use production URL if available, otherwise localhost
        frontend_base = os.getenv("FRONTEND_URL", "http://localhost:4200")
        frontend_url = f"{frontend_base}/#/auth/success?token={jwt_token}"
        logger.info(f"Redirecting to: {frontend_url}")
        return RedirectResponse(url=frontend_url)
        
    except Exception as e:
        logger.error(f"Auth callback error: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        frontend_base = os.getenv("FRONTEND_URL", "http://localhost:4200")
        return RedirectResponse(url=f"{frontend_base}/#/auth/error")


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(current_user = Depends(get_current_active_user)):
    """Get current authenticated user info"""
    return current_user


@router.post("/logout")
async def logout():
    """Logout user (client should remove token)"""
    return {"message": "Successfully logged out"}


@router.put("/profile", response_model=UserSchema)
async def update_profile(
    user_update: UserUpdate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user profile information"""
    updated_user = update_user(db, current_user.id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user


@router.get("/test-callback")
async def test_callback(code: str = None, state: str = None):
    """Test endpoint to see callback parameters"""
    return {
        "code": code,
        "state": state,
        "message": "Callback received"
    }