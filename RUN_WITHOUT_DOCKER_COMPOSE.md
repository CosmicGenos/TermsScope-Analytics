# Run TermsScope Analytics (no docker-compose)

This repo has two parts:

- Backend (FastAPI): serves `/api/*` and Google OAuth endpoints
- Frontend (Vite/React): runs on port 5173 in dev and proxies `/api` to the backend

Below is a step-by-step way to run everything using plain `docker run` for Postgres + Redis.

---

## 0) Prerequisites

- Docker Desktop running
- Python 3.10+ (for running the backend locally) OR you can run the backend as a Docker container
- Node.js 18+ (for running the frontend)

---

## 1) Start PostgreSQL

PowerShell:

```powershell
docker run -d --name termsscope-postgres `
  -e POSTGRES_DB=termsscope `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -p 5432:5432 `
  -v termsscope_pgdata:/var/lib/postgresql/data `
  postgres:16-alpine
```

---

## 2) Start Redis

PowerShell:

```powershell
docker run -d --name termsscope-redis `
  -p 6379:6379 `
  redis:7-alpine
```

---

## 3) Create backend environment file

Copy `backend/.env.example` to `backend/.env` and fill in values.

### Connection strings (build them from username/password)

Postgres async (used by the running API):

`postgresql+asyncpg://<USER>:<PASSWORD>@<HOST>:<PORT>/<DB>`

Postgres sync (used by Alembic migrations):

`postgresql+psycopg://<USER>:<PASSWORD>@<HOST>:<PORT>/<DB>`

If you used the docker commands above and are running the backend on your machine (not in Docker), use:

- `HOST=localhost`
- `PORT=5432`
- `DB=termsscope`
- `USER=postgres`
- `PASSWORD=postgres`

Redis:

`redis://<HOST>:<PORT>/<DB_INDEX>`

With the default container above (backend on host):

- `REDIS_URL=redis://localhost:6379/0`

If your password contains special characters (like `@`, `:`, `/`), URL-encode it.

---

## 4) Create database tables (Alembic)

From `backend/`:

```powershell
alembic upgrade head
```

---

## 5) Run the backend

### Option A: Run backend on your machine (recommended for dev)

From `backend/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m playwright install chromium
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend health check:

- http://localhost:8000/health

### Option B: Run backend as a Docker container

From `backend/`:

```powershell
docker build -t termsscope-backend .
docker run --rm -p 8000:8000 --name termsscope-backend --env-file .env termsscope-backend
```

If you do this, note that `localhost` inside the container is the container itself. You will either:

- connect to Postgres/Redis via `host.docker.internal` (Docker Desktop), OR
- put all containers on a user-defined Docker network and use container names as hosts.

---

## 6) Run the frontend

From `frontend/`:

```powershell
npm install
npm run dev
```

Open:

- http://localhost:5173

In dev, the frontend uses Vite proxy to forward `/api/*` to `http://localhost:8000`.

---

## 7) Google OAuth credentials (what to create and where to put them)

The app uses a standard server-side OAuth2 “authorization code” flow:

1. Frontend sends you to `/api/auth/google/login`
2. Backend redirects you to Google consent screen
3. Google redirects back to `GOOGLE_REDIRECT_URI` (default: `http://localhost:8000/api/auth/google/callback`)
4. Backend exchanges the code for user info, creates/updates the user, then redirects to:
   `FRONTEND_URL/auth/callback?token=<JWT>`

### In Google Cloud Console

1. Create/select a project
2. Configure **OAuth consent screen** (External is fine for local dev)
3. Go to **APIs & Services → Credentials**
4. Create **OAuth client ID**
   - Application type: **Web application**
   - Authorized redirect URIs:
     - `http://localhost:8000/api/auth/google/callback`

Google will give you:

- Client ID → set `GOOGLE_CLIENT_ID`
- Client secret → set `GOOGLE_CLIENT_SECRET`

Make sure `GOOGLE_REDIRECT_URI` in `backend/.env` matches exactly what you entered in Google Console.

---

## Troubleshooting quick checks

- Backend can reach Postgres: confirm `DATABASE_URL` host/port are correct and Postgres container is running.
- Backend can reach Redis: confirm `REDIS_URL` and Redis container is running.
- Google OAuth redirect mismatch: the URI must match exactly (scheme/host/port/path).
- Frontend API calls failing in dev: confirm backend is on `http://localhost:8000` (Vite proxy target).
