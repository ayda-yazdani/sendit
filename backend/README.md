# FastAPI Supabase Auth Backend

Small FastAPI service that proxies authentication to Supabase Auth.

## Features

- Email/password sign-up
- Email/password sign-in
- Session refresh
- Current-user lookup from a bearer token
- Sign-out against Supabase
- Health endpoint and CORS configuration

## Setup

1. Create a Supabase project.
2. Copy `.env.example` to `.env`.
3. Fill in:
   - `SUPABASE_URL`
   - `SUPABASE_PUBLISHABLE_KEY` or your legacy anon key

## Run

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## Endpoints

- `GET /health`
- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`

## Test

```bash
cd backend
uv sync --dev
uv run pytest
```

## Notes

- `me` and `logout` expect `Authorization: Bearer <access_token>`.
- `logout` revokes the session in Supabase, but the current access token can remain valid until it expires.
- If email confirmation is enabled in Supabase, `signup` may return a user without an active session until the email is confirmed.
- `signup` accepts optional `metadata`, which is forwarded to Supabase as user metadata.
