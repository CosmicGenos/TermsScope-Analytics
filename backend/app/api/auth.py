"""Auth API endpoints — Google OAuth login flow."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_required
from app.auth.google_oauth import exchange_code_for_user, get_google_login_url
from app.auth.jwt_handler import create_access_token
from app.config import get_settings
from app.db import get_db
from app.models.user import User
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/google/login")
async def google_login():
    """Redirect to Google OAuth consent screen."""
    url = get_google_login_url()
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback.

    Exchanges the auth code for user info, creates/updates the user,
    issues a JWT, and redirects to the frontend with the token.
    """
    settings = get_settings()

    user_data = await exchange_code_for_user(code)
    if not user_data or not user_data.get("google_id"):
        raise HTTPException(400, "Failed to authenticate with Google.")

    # Find or create user
    result = await db.execute(
        select(User).where(User.google_id == user_data["google_id"])
    )
    user = result.scalar_one_or_none()

    if user:
        # Update existing user info
        user.name = user_data["name"]
        user.avatar_url = user_data.get("avatar_url")
    else:
        # Create new user
        user = User(
            google_id=user_data["google_id"],
            email=user_data["email"],
            name=user_data["name"],
            avatar_url=user_data.get("avatar_url"),
        )
        db.add(user)
        await db.flush()

    # Create JWT
    token = create_access_token(user.id, user.email)

    # Redirect to frontend with token
    redirect_url = f"{settings.frontend_url}/auth/callback?token={token}"
    return RedirectResponse(url=redirect_url)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user_required),
):
    """Get the current authenticated user."""
    return current_user
