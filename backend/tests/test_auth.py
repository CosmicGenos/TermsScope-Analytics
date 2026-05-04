"""Tests for auth-gated endpoints and authentication behaviour."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_me_without_token_returns_401(client: TestClient):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_history_without_token_returns_401(client: TestClient):
    res = client.get("/api/history")
    assert res.status_code == 401


def test_history_item_without_token_returns_401(client: TestClient):
    import uuid
    res = client.get(f"/api/history/{uuid.uuid4()}")
    assert res.status_code == 401


def test_me_with_invalid_token_returns_401(client: TestClient):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


def test_google_login_redirects(client: TestClient):
    res = client.get("/api/auth/google/login", follow_redirects=False)
    assert res.status_code in (301, 302, 303, 307, 308)
    location = res.headers.get("location", "")
    assert "accounts.google.com" in location or "google.com" in location
