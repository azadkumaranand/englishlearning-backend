# English Learning API

This folder is deployable as a standalone backend service.

## Run locally (standalone)

```bash
cp .env.example .env
uv sync
uv run alembic -c alembic.ini upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Deploy on Render

Create a **Web Service** from this folder (`services/api` if deploying from the monorepo, or repo root if split out).

- Build command:

  ```bash
  pip install uv && uv sync --frozen --no-dev
  ```

- Start command:

  ```bash
  uv run --no-sync alembic -c alembic.ini upgrade head && uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```

- Health check path: `/health`

Set these Render environment variables:

- `APP_ENV=production`
- `BACKEND_CORS_ORIGINS=<your mobile origin(s) or *>`
- `JWT_SECRET_KEY=<strong-random-secret>`
- `DATABASE_URL=<Render Postgres connection string>`
- `LLM_API_KEY=<your-openai-api-key>`
- `STT_API_KEY=<your-openai-api-key>`

`DATABASE_URL` can be `postgres://...` or `postgresql://...`; the app normalizes it to `postgresql+asyncpg://...` automatically.

## Use Supabase Postgres

If you want to switch from local Postgres to Supabase, set `DATABASE_URL` to your Supabase connection string.

Important:

- If your password contains special characters like `@`, `#`, `/`, or `&`, URL-encode it before putting it in the connection string.
- Supabase direct database hosts usually require SSL.
- If Supabase says the direct host is not IPv4 compatible, use the **Session Pooler** connection string from the Supabase dashboard for local development or IPv4-only environments.

Example direct connection:

```env
DATABASE_URL=postgresql://postgres:<URL-ENCODED-PASSWORD>@db.your-project-ref.supabase.co:5432/postgres?ssl=require
```

Example with your project ref:

```env
DATABASE_URL=postgresql://postgres:<URL-ENCODED-PASSWORD>@db.zhulrahuacfmzlblowfo.supabase.co:5432/postgres?ssl=require
```

The app will normalize that to the async SQLAlchemy driver automatically.

## Split backend into its own Git repo (optional)

If you want a fully separate backend repo:

```bash
# run from monorepo root
git subtree split --prefix=services/api -b backend-only
git remote add backend <new-backend-repo-url>
git push backend backend-only:main
```

Then connect that backend repo to Render.
