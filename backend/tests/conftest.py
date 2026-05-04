"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def sample_tos_text() -> str:
    return (_FIXTURES_DIR / "sample_tos.txt").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def sample_pdf_bytes(sample_tos_text: str) -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), sample_tos_text[:3000], fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data
