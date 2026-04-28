# TermsScope Analytics

An AI-powered Terms of Service and Privacy Policy analyzer. Paste a URL, drop in raw text, or upload a PDF — TermsScope reads the legal document and returns a plain-language breakdown of every clause that actually matters to you.

## What it does

Most people click "I agree" without reading. TermsScope changes that by automatically extracting and categorizing clauses across five risk domains:

| Domain | What it covers |
|---|---|
| **Privacy** | Data collection, third-party sharing, retention periods |
| **Financial** | Billing cycles, refund policies, price-change terms |
| **Data Rights** | Who owns your content, licensing grants, data portability |
| **Cancellation** | Account deletion, unsubscribe procedures |
| **Liability** | Arbitration clauses, liability caps, dispute resolution |

Each clause is tagged as **critical**, **moderate**, **positive**, or **neutral**, scored 0–100 per category, and explained in one sentence of plain English.

Analysis runs as a streaming pipeline (`acquire → enrich → validate → chunk → analyze × 5 → aggregate`) so you see progress in real time via a live progress bar. Results are cached by content hash, so the same document never gets analyzed twice.

Sign in with Google to keep a personal history of every analysis you've run.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, FastAPI, Uvicorn |
| AI pipeline | LangGraph, LangChain (OpenAI / Gemini / Claude) |
| Database | PostgreSQL 16 (async via asyncpg + SQLAlchemy 2) |
| Cache | Redis 7 |
| Migrations | Alembic |
| Scraping | Scrapling (TLS-spoofing + StealthyFetcher) |
| PDF parsing | PyMuPDF |
| Chunking | Chonkie |
| Auth | Google OAuth 2.0 + JWT |
| Frontend | React 19, TypeScript, Vite 7 |
| HTTP client | Axios |

---

## Prerequisites

Before running locally you need:

- **Python 3.10+** and [uv](https://docs.astral.sh/uv/) (Python package manager)
- **Node.js 18+** and npm
- **Docker Desktop** — used only to run PostgreSQL and Redis containers (no app containers needed)
- An **OpenAI API key** (or Google / Anthropic key if you prefer a different provider)
- A **Google OAuth app** (for the sign-in feature — optional, the analyzer works anonymously too)

---

## Local setup

### 1. Clone the repo

```bash
git clone https://github.com/CosmicGenos/TermsScope-Analytics.git
cd TermsScope_Analytics
```

### 2. Start PostgreSQL and Redis

These two commands spin up lightweight Alpine containers with persistent volumes. Your data survives container restarts.

```bash
docker run -d \
  --name termsscope-postgres \
  -e POSTGRES_DB=termsscope \
  -e POSTGRES_USER=Kavindu \
  -e POSTGRES_PASSWORD=123456 \
  -p 5433:5432 \
  -v termsscope-pgdata:/var/lib/postgresql/data \
  postgres:16-alpine

docker run -d \
  --name termsscope-redis \
  -p 6379:6379 \
  redis:7-alpine
```

> Note: Postgres is mapped to **5433** on the host (not the default 5432) to avoid clashing with any local Postgres installation.

### 3. Configure the backend

```bash
cd backend
cp .env.example .env   # if .env.example exists, otherwise create .env manually
```

Edit `backend/.env` and fill in the values below. Required fields are marked with `*`.

```env
# App
APP_NAME=TermsScope Analytics
APP_ENV=development
DEBUG=true
SECRET_KEY=your-random-secret-key-here   # * generate with: openssl rand -hex 32

# Database  *
DATABASE_URL=postgresql+asyncpg://Kavindu:123456@localhost:5433/termsscope
DATABASE_URL_SYNC=postgresql+psycopg://Kavindu:123456@localhost:5433/termsscope

# Redis  *
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=86400

# LLM provider  *  (at least one key is required)
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL= gpt-5.4-2026-03-05
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=                  # optional — for Gemini
ANTHROPIC_API_KEY=               # optional — for Claude

# Google OAuth  (optional — skip if you don't need sign-in)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

# CORS
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=["http://localhost:5173"]

# Limits
RATE_LIMIT_PER_HOUR=20
MAX_TOKEN_LIMIT=100000
MAX_FILE_SIZE_MB=10
```

### 4. Install backend dependencies and run migrations

```bash
# still inside backend/
uv run alembic upgrade head
```

This creates the `users` and `analyses` tables (plus any pending migrations).

### 5. Start the backend

```bash
uv run python run.py
```

The API server starts at **http://localhost:8000**.  
Interactive API docs are at **http://localhost:8000/docs** (visible because `DEBUG=true`).

### 6. Install frontend dependencies and start the dev server

Open a second terminal:

```bash
cd frontend
npm install        # first time only
npm run dev
```

The frontend starts at **http://localhost:3000**.

---

## Usage

1. Open **http://localhost:3000** in your browser.
2. Paste a URL (e.g. `https://example.com/terms`), type/paste raw text, or drag in a PDF.
3. Click **Analyze** and watch the live progress bar as the pipeline runs.
4. Review the results: per-category risk scores, flagged clauses, and a plain-English summary.
5. Optionally sign in with Google to save results to your history.

---

## Managing the database containers

```bash
# Check running containers
docker ps

# Stop (data is preserved in the volume)
docker stop termsscope-postgres termsscope-redis

# Start again later
docker start termsscope-postgres termsscope-redis

# Remove containers (volume is kept — data still safe)
docker rm termsscope-postgres termsscope-redis

# Nuclear option — wipe everything including stored data
docker rm -f termsscope-postgres termsscope-redis
docker volume rm termsscope-pgdata
```

---

## Project structure

```
TermsScope_Analytics/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI route handlers (analyze, auth, history)
│   │   ├── auth/           # JWT + Google OAuth helpers
│   │   ├── db/             # Async DB session & Redis client
│   │   ├── llm/            # Provider abstraction (OpenAI / Gemini / Claude)
│   │   ├── models/         # SQLAlchemy ORM models (User, Analysis)
│   │   ├── pipeline/       # LangGraph pipeline nodes, prompts, state
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # Scraper, PDF parser, Redis cache helpers
│   │   ├── config.py       # Pydantic Settings
│   │   └── main.py         # FastAPI app factory
│   ├── alembic/            # Database migrations
│   ├── tests/
│   ├── pyproject.toml
│   └── run.py              # Uvicorn entry point
└── frontend/
    ├── src/
    │   ├── components/     # Reusable UI components
    │   ├── context/        # Auth context (JWT in localStorage)
    │   ├── hooks/          # useAnalysis (SSE subscription)
    │   ├── pages/          # Home, Analyzing, Results, History, AuthCallback
    │   └── services/       # Axios API client
    ├── vite.config.ts
    └── package.json
```

---

## API overview

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/analyze` | Submit URL or text for analysis |
| `POST` | `/api/analyze/file` | Upload a PDF or TXT file |
| `GET` | `/api/analyze/{id}` | Fetch completed analysis result |
| `GET` | `/api/analyze/{id}/stream` | SSE stream for live progress |
| `GET` | `/api/auth/google/login` | Redirect to Google OAuth |
| `GET` | `/api/auth/google/callback` | OAuth callback |
| `GET` | `/api/auth/me` | Current authenticated user |
| `GET` | `/api/history` | User's analysis history (auth required) |
| `DELETE` | `/api/history/{id}` | Delete an analysis (auth required) |

Full interactive docs at `http://localhost:8000/docs` when running in development mode.

---

## LLM provider selection

The backend supports OpenAI, Google Gemini, and Anthropic Claude. Switch providers by changing `DEFAULT_LLM_PROVIDER` and `DEFAULT_LLM_MODEL` in `.env`, or pass `llm_provider` / `llm_model` fields in the analysis request body to override per-request.

| Provider value | Example model |
|---|---|
| `openai` | `gpt-5.4-2026-03-05`, `gpt-5.5-2026-04-23` |
| `gemini` | `gemini-3`, `gemini-2.5-pro` |
| `claude` | `claude`, `claude-sonnet-4-6` |
