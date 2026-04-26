# =============================================================
# BACKEND DOCKERFILE — FastAPI + Python
# =============================================================
# What is a Dockerfile?
#   A script that tells Docker how to build your app into an "image".
#   Think of it like a recipe: follow the steps and you get a
#   reproducible box that runs your app the same way everywhere.
# =============================================================

# ── Step 1: Choose a base image ──────────────────────────────
# FROM picks the starting point. We start from an official Python image.
# "3.12-slim" = Python 3.12 on minimal Debian Linux (smaller than full).
# Everything we do next is layered on top of this.
FROM python:3.12-slim

# ── Step 2: Set the working directory ────────────────────────
# All future commands (COPY, RUN, CMD) happen inside /app.
# If /app doesn't exist, Docker creates it automatically.
WORKDIR /app

# ── Step 3: Install system-level dependencies ─────────────────
# Some Python packages need C libraries to compile.
#   gcc       = C compiler  (needed by some packages)
#   libpq-dev = PostgreSQL headers (needed by psycopg)
# We clean up apt cache at the end to keep the image small.
# RUN executes during BUILD time, not when the container starts.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Step 4: Install uv (fast Python package manager) ─────────
# Instead of copying uv's installer, we grab its binary directly
# from its official Docker image. This is faster than pip install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# ── Step 5: Copy dependency files FIRST ──────────────────────
# WHY copy pyproject.toml before the rest of the code?
# Docker caches each step as a "layer". If pyproject.toml hasn't
# changed, Docker skips re-running uv install (saves ~1 minute).
# If you copied ALL files first, every code change would bust the cache.
COPY pyproject.toml .

# ── Step 6: Install Python dependencies ──────────────────────
# --system  = install into system Python (not a virtualenv)
# --no-cache = don't save download cache inside the image
RUN uv pip install --system --no-cache .

# ── Step 7: Install Playwright browser (for web scraping) ────
# Playwright needs actual browser binaries inside the container.
# We only install Chromium to keep the image smaller.
RUN playwright install chromium --with-deps

# ── Step 8: Copy application source code ─────────────────────
# We copy the code AFTER installing dependencies.
# That way, editing your Python code doesn't re-trigger uv install.
COPY app/ app/

# ── Step 9: Copy alembic files for DB migrations ─────────────
COPY alembic/ alembic/
COPY alembic.ini .

# ── Step 10: Document the port ────────────────────────────────
# EXPOSE is documentation — it doesn't actually open a port.
# The real port mapping happens in docker-compose.yml.
EXPOSE 8000

# ── Step 11: Define the startup command ──────────────────────
# CMD runs when the container STARTS (every time).
# Different from RUN which runs only at build time.
# --host 0.0.0.0 is REQUIRED — without it, uvicorn only listens
# on localhost inside the container and nothing can reach it.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
