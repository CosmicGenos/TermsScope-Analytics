# =============================================================
# BASIC API TESTS — using pytest + httpx
# =============================================================
# What are these tests for?
#   The CI/CD pipeline runs these before deploying.
#   If any test fails, the deploy is blocked. This protects
#   production from broken code being shipped automatically.
#
# What is pytest?
#   Python's most popular testing framework.
#   Any function that starts with "test_" is automatically found and run.
#
# What is TestClient?
#   FastAPI provides a test client built on httpx.
#   It makes real HTTP requests to your app WITHOUT starting a server.
#   So tests run fast and don't need a real postgres/redis running.
# =============================================================

import pytest
from fastapi.testclient import TestClient

from app.main import app

# ── Test Client ───────────────────────────────────────────────
# Create one client shared across all tests in this file.
# TestClient wraps your FastAPI app and lets you call endpoints.
client = TestClient(app)


# ── Test 1: Health endpoint ───────────────────────────────────
def test_health_endpoint_returns_200():
    """
    The /health endpoint should always return HTTP 200 OK.
    If this fails, the app didn't even start correctly.
    """
    response = client.get("/health")

    # assert = "this must be true, or the test fails"
    assert response.status_code == 200


def test_health_endpoint_returns_ok_status():
    """
    The /health endpoint should return {"status": "ok", ...}.
    """
    response = client.get("/health")
    data = response.json()

    assert data["status"] == "ok"


def test_health_endpoint_returns_service_name():
    """
    The /health endpoint should include the service name.
    """
    response = client.get("/health")
    data = response.json()

    # Check the key exists and is a non-empty string
    assert "service" in data
    assert len(data["service"]) > 0


# ── Test 2: Unknown routes ────────────────────────────────────
def test_unknown_route_returns_404():
    """
    Requesting a route that doesn't exist should return 404.
    FastAPI handles this automatically — this test verifies that.
    """
    response = client.get("/this-route-does-not-exist")

    assert response.status_code == 404


# ── Test 3: Docs available in debug mode ──────────────────────
def test_docs_endpoint_is_accessible():
    """
    /docs (Swagger UI) should be available.
    Our app enables it when DEBUG=True, which is the default.
    """
    response = client.get("/docs")

    # 200 = page loaded, 404 = docs disabled (debug=False)
    assert response.status_code == 200
