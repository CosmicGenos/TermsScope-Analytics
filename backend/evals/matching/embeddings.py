"""OpenAI text-embedding-3-small with on-disk SQLite cache.

Cache key is sha256(normalised_text) + model. Embeddings are stored as float32
LE bytes so the file stays compact.
"""

from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
from pathlib import Path

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)

_BATCH_SIZE = 256


def normalise_clause(text: str) -> str:
    """Lowercase, strip punctuation noise, collapse whitespace, drop leading
    'we ' / 'you ' that uniformly inflate similarity in legal text."""
    t = text.lower().strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"^(we|you|the\s+company|the\s+service)\s+", "", t)
    return t


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EmbeddingCache:
    """SQLite-backed embedding cache with batched OpenAI calls."""

    def __init__(self, db_path: Path, model: str) -> None:
        self.model = model
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS embeddings (
                   sha256 TEXT NOT NULL,
                   model  TEXT NOT NULL,
                   vec    BLOB NOT NULL,
                   PRIMARY KEY (sha256, model)
               )"""
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def _get_one(self, sha: str) -> np.ndarray | None:
        row = self._conn.execute(
            "SELECT vec FROM embeddings WHERE sha256=? AND model=?",
            (sha, self.model),
        ).fetchone()
        if row is None:
            return None
        return np.frombuffer(row[0], dtype=np.float32)

    def _put_one(self, sha: str, vec: np.ndarray) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO embeddings (sha256, model, vec) VALUES (?, ?, ?)",
            (sha, self.model, vec.astype(np.float32).tobytes()),
        )

    async def embed(self, texts: list[str]) -> np.ndarray:
        """Return an (n, d) float32 matrix, L2-normalised."""
        if not texts:
            return np.zeros((0, 1536), dtype=np.float32)

        normed = [normalise_clause(t) for t in texts]
        shas = [_sha256(t) for t in normed]
        cached: dict[int, np.ndarray] = {}
        misses: list[tuple[int, str]] = []

        for i, sha in enumerate(shas):
            v = self._get_one(sha)
            if v is not None:
                cached[i] = v
            else:
                misses.append((i, normed[i]))

        if misses:
            new_vectors = await self._fetch_embeddings([m[1] for m in misses])
            for (idx, _), vec in zip(misses, new_vectors, strict=True):
                self._put_one(shas[idx], vec)
                cached[idx] = vec
            self._conn.commit()
            logger.info(
                "Embeddings: %d cached, %d fetched (model=%s)",
                len(texts) - len(misses),
                len(misses),
                self.model,
            )

        d = next(iter(cached.values())).shape[0]
        out = np.zeros((len(texts), d), dtype=np.float32)
        for i, v in cached.items():
            out[i] = v
        # L2-normalise
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return out / norms

    async def _fetch_embeddings(self, texts: list[str]) -> list[np.ndarray]:
        from openai import AsyncOpenAI
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY required for embeddings")
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        vectors: list[np.ndarray] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = texts[start : start + _BATCH_SIZE]
            resp = await client.embeddings.create(model=self.model, input=batch)
            for d in resp.data:
                vectors.append(np.array(d.embedding, dtype=np.float32))
        return vectors
