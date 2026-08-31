# MagicTripPlanner Frontend

Next.js App Router frontend for the MagicTripPlanner FastAPI backend.

## Setup

```bash
npm install
```

Create `.env.local` when the backend is not running at the development default:

```env
BACKEND_API_URL=http://127.0.0.1:8000
```

## Run

Start the backend from `Backend/`, then run:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Build

```bash
npm run build
```

## Backend Connection

API calls use the same-origin `/api/backend` route, which proxies to the server-only `BACKEND_API_URL`. Authentication uses an HttpOnly first-party session cookie. `NEXT_PUBLIC_API_BASE_URL` remains available only as an optional direct-browser override. The planner restores saved trip state from backend read endpoints and keeps the in-progress wizard state in localStorage for refresh recovery.

The optional Google button reads its public OAuth web client ID from the backend at runtime. Configure `GOOGLE_AUTH_CLIENT_ID` on the backend; no `NEXT_PUBLIC_` Google variable or OAuth client secret is required. The backend verifies every Google ID token before creating the normal app session.

For Vercel, select `Frontend` as the project Root Directory and set `BACKEND_API_URL` to the public HTTPS origin of the hosted FastAPI service. See `../DEPLOYMENT.md` for the complete Vercel + Azure deployment.
