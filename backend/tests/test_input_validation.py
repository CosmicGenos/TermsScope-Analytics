"""Tests that the API correctly rejects invalid inputs with 4xx responses."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient


# ── /api/analyze (JSON body) ──────────────────────────────────────────

def test_url_input_without_url_field_returns_422(client: TestClient):
    res = client.post("/api/analyze", json={"input_type": "url"})
    assert res.status_code == 422


def test_text_input_without_text_field_returns_422(client: TestClient):
    res = client.post("/api/analyze", json={"input_type": "text"})
    assert res.status_code == 422


def test_invalid_input_type_returns_422(client: TestClient):
    res = client.post("/api/analyze", json={"input_type": "banana", "text": "hello"})
    assert res.status_code == 422


def test_missing_input_type_returns_422(client: TestClient):
    res = client.post("/api/analyze", json={"text": "some text"})
    assert res.status_code == 422


def test_text_too_long_returns_422(client: TestClient):
    oversized = "a" * (500_001)
    res = client.post("/api/analyze", json={"input_type": "text", "text": oversized})
    assert res.status_code == 422


# ── /api/analyze/file (multipart) ────────────────────────────────────

def test_file_wrong_extension_returns_400(client: TestClient):
    res = client.post(
        "/api/analyze/file",
        files={"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert res.status_code == 400
    assert "PDF" in res.json()["detail"] or "TXT" in res.json()["detail"]


def test_file_no_filename_returns_4xx(client: TestClient):
    res = client.post(
        "/api/analyze/file",
        files={"file": ("", b"some content", "text/plain")},
    )
    assert res.status_code in (400, 422)


def test_file_too_large_returns_400(client: TestClient):
    big = b"Terms and conditions. " * 600_000  # > 10 MB
    res = client.post(
        "/api/analyze/file",
        files={"file": ("bigfile.txt", io.BytesIO(big), "text/plain")},
    )
    assert res.status_code == 400
    assert "large" in res.json()["detail"].lower()
