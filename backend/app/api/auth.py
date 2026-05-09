"""Auth API endpoints — Google OAuth and email/password login."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_required
from app.auth.google_oauth import exchange_code_for_user, get_google_login_url
from app.auth.jwt_handler import create_access_token
from app.auth.password import hash_password, verify_password
from app.config import get_settings
from app.db import get_db
from app.models.user import AuthType, EmailAuthUser, GoogleAuthUser, User, UserRole
from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/google/login")
async def google_login():
    """Redirect to Google OAuth consent screen."""
    return RedirectResponse(url=get_google_login_url())


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback — find-or-create user, issue JWT."""
    settings = get_settings()

    user_data = await exchange_code_for_user(code)
    if not user_data or not user_data.get("google_id"):
        raise HTTPException(400, "Failed to authenticate with Google.")

    google_id = user_data["google_id"]

    # Look up by google_id via join so we get the User in one query
    result = await db.execute(
        select(User)
        .join(GoogleAuthUser, GoogleAuthUser.user_id == User.id)
        .where(GoogleAuthUser.google_id == google_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Refresh name and avatar in case they changed in Google
        user.name = user_data["name"]
        google_result = await db.execute(
            select(GoogleAuthUser).where(GoogleAuthUser.user_id == user.id)
        )
        google_auth = google_result.scalar_one()
        google_auth.avatar_url = user_data.get("avatar_url")
    else:
        # First-time Google sign-in — create core user + Google credential row
        user = User(
            email=user_data["email"],
            name=user_data["name"],
            role=UserRole.user,
            auth_type=AuthType.google,
        )
        db.add(user)
        await db.flush()  # populate user.id

        db.add(GoogleAuthUser(
            user_id=user.id,
            google_id=google_id,
            avatar_url=user_data.get("avatar_url"),
        ))
        await db.flush()

    token = create_access_token(user.id, user.email)
    return RedirectResponse(url=f"{settings.frontend_url}/auth/callback?token={token}")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Create a new email/password account and return a JWT."""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists.")

    user = User(
        email=body.email,
        name=body.name,
        role=UserRole.user,
        auth_type=AuthType.email,
    )
    db.add(user)
    await db.flush()

    db.add(EmailAuthUser(user_id=user.id, password_hash=hash_password(body.password)))
    await db.flush()

    token = create_access_token(user.id, user.email)
    return TokenResponse(token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email + password and return a JWT."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or user.auth_type != AuthType.email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")

    email_auth_result = await db.execute(
        select(EmailAuthUser).where(EmailAuthUser.user_id == user.id)
    )
    email_auth = email_auth_result.scalar_one_or_none()

    if not email_auth or not verify_password(body.password, email_auth.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")

    token = create_access_token(user.id, user.email)
    return TokenResponse(token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user_required)):
    """Return the currently authenticated user."""
    return current_user
