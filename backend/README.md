
# TermsScope Analytics — Backend

This backend is a FastAPI app that needs:

- PostgreSQL (stores users + analysis history)
- Redis (caching + URL/hash mapping)
- At least one LLM API key (OpenAI by default)
- (Optional) Google OAuth credentials (for login)

The default dev URLs are:

- Backend: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

## 1) Start PostgreSQL + Redis (WITHOUT docker-compose)

You can run the required containers with plain `docker run`.

### PostgreSQL

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

macOS/Linux:

```bash
docker run -d --name termsscope-postgres \
	-e POSTGRES_DB=termsscope \
	-e POSTGRES_USER=postgres \
	-e POSTGRES_PASSWORD=postgres \
	-p 5432:5432 \
	-v termsscope_pgdata:/var/lib/postgresql/data \
	postgres:16-alpine
```

### Redis

PowerShell:

```powershell
docker run -d --name termsscope-redis `
	-p 6379:6379 `
	redis:7-alpine
```

macOS/Linux:

```bash
docker run -d --name termsscope-redis \
	-p 6379:6379 \
	redis:7-alpine
```

## 2) Configure environment variables

Create `backend/.env` from `backend/.env.example`.

Minimum required for most runs:

- `DATABASE_URL`
- `DATABASE_URL_SYNC`
- `REDIS_URL`
- `OPENAI_API_KEY` (or switch provider)

If you want Google login:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI` (must match Google Console)

### Connection string templates

Postgres async (app runtime):

`postgresql+asyncpg://<USER>:<PASSWORD>@<HOST>:<PORT>/<DB>`

Postgres sync (Alembic migrations):

`postgresql+psycopg://<USER>:<PASSWORD>@<HOST>:<PORT>/<DB>`

Redis:

`redis://<HOST>:<PORT>/<DB_INDEX>`

If your password contains special characters (like `@`, `:`, `/`), URL-encode it.

## 3) Create the database tables

This repo includes an initial Alembic migration for the `users` and `analyses` tables.

From `backend/`:

```bash
alembic upgrade head
```

## 4) Run the backend locally

### Option A: Using a Python virtualenv + pip

From `backend/`:

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m playwright install chromium
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m playwright install chromium
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option B: Build + run the backend as a Docker container

```bash
docker build -t termsscope-backend .
docker run --rm -p 8000:8000 --name termsscope-backend --env-file .env termsscope-backend
```

If Postgres/Redis are also containers and the backend is containerized, put them on the same Docker network and use container names in `DATABASE_URL` / `REDIS_URL`.

