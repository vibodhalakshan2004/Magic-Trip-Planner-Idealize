# MagicTripPlanner Frontend

Next.js App Router frontend for the MagicTripPlanner FastAPI backend.

## Setup

```bash
npm install
```

Create `.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
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

All API calls use `NEXT_PUBLIC_API_BASE_URL`. Protected endpoints attach `Authorization: Bearer <access_token>` from the prototype localStorage auth store. The planner restores saved trip state from backend read endpoints and keeps the in-progress wizard state in localStorage for refresh recovery.
