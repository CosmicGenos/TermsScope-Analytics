"""Google OAuth 2.0 flow using authlib."""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
SCOPES = "openid email profile"


def get_google_login_url(state: str = "") -> str:
    """Build the Google OAuth consent screen URL."""
    settings = get_settings()
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


async def exchange_code_for_user(code: str) -> Optional[dict]:
    """Exchange the auth code for tokens and fetch user info.

    Returns
    -------
    dict | None
        {"google_id", "email", "name", "avatar_url"} or None on failure.
    """
    settings = get_settings()

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )

        if token_resp.status_code != 200:
            logger.error("Google token exchange failed: %s", token_resp.text)
            return None

        tokens = token_resp.json()
        access_token = tokens.get("access_token")

        if not access_token:
            logger.error("No access token in Google response")
            return None

        # Fetch user info
        user_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_resp.status_code != 200:
            logger.error("Google userinfo fetch failed: %s", user_resp.text)
            return None

        user_data = user_resp.json()

    return {
        "google_id": user_data.get("id"),
        "email": user_data.get("email"),
        "name": user_data.get("name", user_data.get("email", "User")),
        "avatar_url": user_data.get("picture"),
    }
