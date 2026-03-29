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
   - `SUPABASE_PUBLISHABLE_KEY` or your legacy anon key.

## Run

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

Open `http://127.0.0.1:8000/api/v1/` for the built-in DEV tester webapp. The built assets are served from the backend, and the React source lives in `backend/tester-app/`.

If you update the tester UI, rebuild it before running the backend:

```bash
cd backend/tester-app
npm install
npm run build
```

## Endpoints

- `GET /health`
- `GET /api/v1/auth/config-check`
- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `POST /api/v1/media/scrape`
- `POST /api/v1/instagram/reels/scrape`
- `POST /api/v1/tiktok/videos/scrape`
- `POST /api/v1/youtube/shorts/scrape`

## Test

```bash
cd backend
uv sync --dev
uv run pytest
```

## Notes

- `me` and `logout` expect `Authorization: Bearer <access_token>`.
- `config-check` confirms the configured `SUPABASE_URL` and publishable key can reach Supabase Auth settings.
- The scrape endpoints also expect `Authorization: Bearer <access_token>` and only allow verified Supabase users.
- `POST /api/v1/media/scrape` is the simplest entrypoint: pass any supported URL and the backend auto-detects Instagram Reels, TikTok videos, or YouTube Shorts.
- `POST /api/v1/instagram/reels/scrape` accepts a public `https://www.instagram.com/reel/...` URL and returns structured Open Graph and JSON-LD metadata.
- `POST /api/v1/tiktok/videos/scrape` accepts a public TikTok video URL, including standard `@user/video/...` links.
- `POST /api/v1/youtube/shorts/scrape` accepts a public `https://www.youtube.com/shorts/...` URL.
- `logout` revokes the session in Supabase, but the current access token can remain valid until it expires.
- If email confirmation is enabled in Supabase, `signup` may return a user without an active session until the email is confirmed.
- `signup` accepts optional `metadata`, which is forwarded to Supabase as user metadata.
