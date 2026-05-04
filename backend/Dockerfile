FROM python:3.12-slim

WORKDIR /app

#System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv from the official image (instead of pip) for faster builds and smaller final image 
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy only the files needed for installing dependencies first (for better caching)
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Phase 1: Install dependencies without copying the whole source code
# Uses cache mount (fast rebuilds) + bind mount (no extra layer)
# --no-install-project = skip your app code, just install deps
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

#  Phase 2: Copy source code and install the project 
COPY pyproject.toml uv.lock ./
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Expose venv to PATH 
ENV PATH="/app/.venv/bin:$PATH"

# Install Scrapling browsers
# Must come AFTER PATH is set so the scrapling CLI is findable
RUN scrapling install

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]