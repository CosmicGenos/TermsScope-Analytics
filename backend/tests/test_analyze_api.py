"""Tests for all 3 analysis input types and retrieval endpoints."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


# ── Submission — all 3 input types ───────────────────────────────────

def test_submit_text_input_returns_analysis_id(client: TestClient, sample_tos_text: str):
    res = client.post("/api/analyze", json={"input_type": "text", "text": sample_tos_text})
    assert res.status_code == 200
    body = res.json()
    assert "analysis_id" in body
    uuid.UUID(body["analysis_id"])  # must be a valid UUID
    assert body["status"] in ("acquiring", "complete")
    assert "cached" in body


def test_submit_url_input_returns_analysis_id(client: TestClient):
    res = client.post(
        "/api/analyze",
        json={"input_type": "url", "url": "https://example.com/terms-of-service"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "analysis_id" in body
    uuid.UUID(body["analysis_id"])
    assert body["status"] in ("acquiring", "complete")


def test_submit_txt_file_returns_analysis_id(client: TestClient, sample_tos_text: str):
    res = client.post(
        "/api/analyze/file",
        files={"file": ("terms.txt", sample_tos_text.encode(), "text/plain")},
    )
    assert res.status_code == 200
    body = res.json()
    assert "analysis_id" in body
    uuid.UUID(body["analysis_id"])
    assert body["status"] in ("acquiring", "complete")


def test_submit_pdf_file_returns_analysis_id(client: TestClient, sample_pdf_bytes: bytes):
    res = client.post(
        "/api/analyze/file",
        files={"file": ("terms.pdf", sample_pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 200
    body = res.json()
    assert "analysis_id" in body
    uuid.UUID(body["analysis_id"])


# ── Retrieval ─────────────────────────────────────────────────────────

def test_get_analysis_after_text_submit(client: TestClient, sample_tos_text: str):
    post = client.post("/api/analyze", json={"input_type": "text", "text": sample_tos_text})
    assert post.status_code == 200
    analysis_id = post.json()["analysis_id"]

    get = client.get(f"/api/analyze/{analysis_id}")
    assert get.status_code == 200
    body = get.json()
    assert body["analysis_id"] == analysis_id
    assert body["input_type"] == "text"
    assert "status" in body


def test_get_analysis_after_url_submit(client: TestClient):
    post = client.post(
        "/api/analyze",
        json={"input_type": "url", "url": "https://example.com/privacy"},
    )
    assert post.status_code == 200
    analysis_id = post.json()["analysis_id"]

    get = client.get(f"/api/analyze/{analysis_id}")
    assert get.status_code == 200
    assert get.json()["input_type"] == "url"


def test_get_analysis_after_file_submit(client: TestClient, sample_tos_text: str):
    post = client.post(
        "/api/analyze/file",
        files={"file": ("tos.txt", sample_tos_text.encode(), "text/plain")},
    )
    assert post.status_code == 200
    analysis_id = post.json()["analysis_id"]

    get = client.get(f"/api/analyze/{analysis_id}")
    assert get.status_code == 200
    assert get.json()["input_type"] == "file"


def test_get_nonexistent_analysis_returns_404(client: TestClient):
    res = client.get(f"/api/analyze/{uuid.uuid4()}")
    assert res.status_code == 404


def test_get_analysis_invalid_uuid_returns_400(client: TestClient):
    res = client.get("/api/analyze/not-a-valid-uuid")
    assert res.status_code == 400


# ── Response shape ────────────────────────────────────────────────────

def test_submission_response_has_required_fields(client: TestClient, sample_tos_text: str):
    res = client.post("/api/analyze", json={"input_type": "text", "text": sample_tos_text})
    assert res.status_code == 200
    body = res.json()
    assert set(body.keys()) >= {"analysis_id", "status", "cached"}


def test_retrieval_response_has_required_fields(client: TestClient, sample_tos_text: str):
    post = client.post("/api/analyze", json={"input_type": "text", "text": sample_tos_text})
    analysis_id = post.json()["analysis_id"]

    get = client.get(f"/api/analyze/{analysis_id}")
    body = get.json()
    assert set(body.keys()) >= {"analysis_id", "status", "input_type"}
