"""Auth dependencies for FastAPI — extract current user from JWT."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import verify_access_token
from app.db import get_db
from app.models.user import User


async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract the current user from the Authorization header (optional).

    Returns None if no valid token is provided — endpoints can then
    work in anonymous mode.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.removeprefix("Bearer ").strip()
    payload = verify_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        uid = UUID(user_id)
    except ValueError:
        return None

    result = await db.execute(select(User).where(User.id == uid))
    return result.scalar_one_or_none()


async def get_current_user_required(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """Require authentication — raises 401 if not logged in."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in with Google.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
