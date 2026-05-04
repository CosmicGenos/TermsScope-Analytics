"""Unit tests for pure service utilities — no DB, no network required."""

from __future__ import annotations

import re

from app.services.cache import compute_content_hash


def test_hash_is_deterministic():
    assert compute_content_hash("hello world") == compute_content_hash("hello world")


def test_hash_distinct_inputs_differ():
    assert compute_content_hash("terms of service") != compute_content_hash("privacy policy")


def test_hash_is_64_char_hex():
    h = compute_content_hash("some text")
    assert re.fullmatch(r"[0-9a-f]{64}", h), f"Expected 64-char hex, got: {h!r}"


def test_hash_empty_string():
    h = compute_content_hash("")
    assert re.fullmatch(r"[0-9a-f]{64}", h)


def test_hash_large_input():
    big = "TERMS AND CONDITIONS\n" * 5000
    h = compute_content_hash(big)
    assert re.fullmatch(r"[0-9a-f]{64}", h)


def test_hash_unicode_input():
    h = compute_content_hash("Nutzungsbedingungen — Datenschutzrichtlinie")
    assert re.fullmatch(r"[0-9a-f]{64}", h)


def test_hash_same_content_different_object():
    text = "TERMS OF SERVICE " * 100
    h1 = compute_content_hash(text)
    h2 = compute_content_hash(str(text))
    assert h1 == h2
