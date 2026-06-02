# Mobile App

React Native Expo client for the English Learning App.

## Features wired to the real backend

- signup and login
- token persistence with secure storage
- onboarding persistence
- topic browsing
- practice session creation
- AI chat
- correction feedback rendering

## Environment

Create a local env file:

```bash
cp .env.example .env
```

Set the backend base URL:

```env
EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Use a host that your target can reach:

- iOS simulator: `http://127.0.0.1:8000`
- Android emulator: `http://10.0.2.2:8000`
- physical device: your machine LAN IP, for example `http://192.168.1.20:8000`

## Run

From `apps/mobileapp`:

```bash
npm install
npm run start
```

Optional targets:

```bash
npm run android
npm run ios
npm run web
```

## Backend requirements

Start the backend from the monorepo root:

```bash
cd /home/azad/ddev/learning/englearning/english-learning-app
docker compose up -d
uv run --project services/api alembic -c services/api/alembic.ini upgrade head
uv run --project services/api uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend now enables CORS through `BACKEND_CORS_ORIGINS`, which defaults to `*` in development.
