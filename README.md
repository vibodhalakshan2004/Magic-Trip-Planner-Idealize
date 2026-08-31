# MagicTripPlanner

<p align="center">
  <img src="Frontend/public/logo.png" alt="MagicTripPlanner logo" width="180" />
</p>

<p align="center">
  An AI-assisted, Sri Lanka-focused trip planner that turns traveler preferences into map-verified destinations, day-by-day routes, hotel suggestions, and practical budget estimates.
</p>

MagicTripPlanner is a full-stack application built with Next.js, FastAPI, PostgreSQL, Gemini, Leaflet, and OpenStreetMap-based services. It supports guided manual planning and a durable automatic workflow that can generate, save, retry, cancel, and restore complete trip plans.

> **AI architecture:** the project does not use LangChain, LangGraph, CrewAI, or another agent framework. It uses the Google Gen AI SDK directly and coordinates the workflow with a custom Python planning worker. Gemini currently returns schema-validated structured output; external services are called explicitly by application code rather than through model-native function calling.

## Table of contents

- [Highlights](#highlights)
- [How the AI workflow works](#how-the-ai-workflow-works)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Quick start with Docker](#quick-start-with-docker)
- [Local development setup](#local-development-setup)
- [Environment variables](#environment-variables)
- [External providers and fallbacks](#external-providers-and-fallbacks)
- [Images, maps, and routing](#images-maps-and-routing)
- [Transport and budget calculation](#transport-and-budget-calculation)
- [API overview](#api-overview)
- [Project structure](#project-structure)
- [Testing and quality checks](#testing-and-quality-checks)
- [Security and privacy](#security-and-privacy)
- [Troubleshooting](#troubleshooting)
- [Current limitations](#current-limitations)

## Highlights

### AI-assisted trip planning

- Destination recommendations based on the trip, interests, travel style, saved preferences, and optional weather context.
- Hotel recommendations near daily route endpoints.
- Schema-validated Gemini responses using Pydantic-compatible response models.
- Automatic ranking and filtering so only coordinate-backed places enter the route.
- A durable full-plan job with progress updates, cancellation, retry, idempotency, and checkpoints.

### Routes and maps

- Day-by-day itinerary generation across the full date range.
- Real road geometry, distances, durations, instructions, path coordinates, and encoded polylines.
- Start-location routing on day one and optional return-to-hotel or return-to-start legs.
- Stop ordering based on preferred visit time, geographic proximity, and itinerary constraints.
- Layered geocoding with canonical-name cleanup, broader search candidates, provider caching, and fallback providers.
- Interactive Leaflet map using OpenStreetMap data.

### Hotels and budgets

- Trip-wide and per-route-day hotel search and selection.
- Hotel-aware route regeneration after daily stays are selected.
- Budget categories for accommodation, attractions, food, transport, other spending, and emergency buffer.
- Segment-by-segment transport pricing instead of a single flat trip rate.
- Per-passenger bus and train fares multiplied by traveler count.
- Group pricing for car, taxi, motorcycle, and local mixed-mode transfers.
- Optional endpoint-specific Google transit fare lookup with Sri Lankan fare-table estimates as fallback.

### Traveler experience

- Registration, login, logout, and HttpOnly cookie sessions.
- Dashboard for creating and restoring trips.
- Editable profile for name, email, password, and profile picture.
- Saved preferences and an explicit choice to reuse or replace them.
- Manual planning controls and one-click automatic planning.
- Plan version history and restoration.
- Viewer/editor collaboration with other registered users.
- Reviews, itinerary print/PDF, calendar export, offline HTML export, and sharing controls.
- Private traveler toolkit for notes, instructions, checklists, and actual expenses.
- Installable web-app metadata for supported browsers.

### Reliability

- PostgreSQL-backed jobs, plan state, caches, quota counters, and version history.
- Shared provider cache with retries and rate-aware map requests.
- Health endpoints for database and optional Google-provider status.
- Request IDs, response timing, security headers, credentialed CORS, and API/authentication rate limits.
- Automatic routing and provider fallbacks when an optional service is unavailable.

## How the AI workflow works

LangChain is not required because the orchestration is implemented directly in Python. The FastAPI application creates a database-backed planning job, and a separate worker claims and executes that job.

```mermaid
flowchart TD
    A[Traveler submits trip and preferences] --> B[FastAPI creates an idempotent planning job]
    B --> C[Planning worker creates a restore checkpoint]
    C --> D[Destination Agent requests structured Gemini recommendations]
    D --> E[Geocoder and media services enrich and validate places]
    E --> F[Best map-verified places are saved]
    F --> G[Route Agent schedules stops and builds road routes]
    G --> H[Route is confirmed]
    H --> I[Daily hotel search selects stays near route endpoints]
    I --> J[Route is regenerated with selected hotels]
    J --> K[Budget Agent prices the saved route and trip]
    K --> L[Completed plan version is saved]
```

The responsibilities are deliberately separated:

| Component | Responsibility | AI-driven? |
| --- | --- | --- |
| Destination Agent | Produces ranked destination suggestions and structured card content | Yes, Gemini |
| Hotel Agent | Produces accommodation recommendations and structured content | Yes, Gemini |
| Route Agent | Geocodes stops, schedules them, and requests route geometry | Deterministic application logic |
| Budget Agent | Aggregates trip costs and classifies budget status | Deterministic application logic |
| Planning worker | Sequences stages, saves progress, handles cancellation/retry, and creates checkpoints | Custom Python orchestration |
| Provider services | Geocoding, routing, weather, media, hotel search, transit fares, and caching | External service adapters |

Gemini calls use structured output schemas rather than free-form text parsing. The current implementation does **not** give Gemini a list of callable tools and does not use Gemini native function calling. The application controls the sequence and validates every result before saving it.

Persistent application memory comes from PostgreSQL: users, preferences, trips, selected places and hotels, routes, budgets, planning jobs, collaborators, traveler-toolkit data, provider cache entries, quota counters, and trip versions survive process restarts.

## Architecture

```mermaid
flowchart LR
    Browser[Next.js browser application] -->|Cookie-authenticated JSON API| API[FastAPI backend]
    Browser -->|Location image requests| ImageProxy[Next.js image proxy]
    API --> DB[(PostgreSQL)]
    API --> Gemini[Gemini API]
    API --> Providers[Map, weather, media, and fare providers]
    Worker[Planning worker] --> DB
    Worker --> Gemini
    Worker --> Providers
    ImageProxy --> Wikimedia[Wikimedia and allowed image hosts]
```

Docker Compose runs four services:

| Service | Purpose | Local address |
| --- | --- | --- |
| `database` | PostgreSQL 17 persistent storage | Internal Compose network |
| `backend` | FastAPI API and Alembic migration startup | `http://localhost:8000` |
| `planning-worker` | Durable automatic-plan job processor | No public port |
| `frontend` | Next.js application | `http://localhost:3000` |

## Technology stack

### Frontend

- Next.js 16 App Router
- React 19 and TypeScript
- Tailwind CSS 4
- TanStack Query
- Zustand
- React Hook Form and Zod
- Leaflet and React Leaflet
- Lucide icons

### Backend

- Python 3.12
- FastAPI
- Pydantic and pydantic-settings
- SQLAlchemy 2
- Alembic
- PostgreSQL
- Google Gen AI SDK (`google-genai`)
- HTTPX, Requests, Tenacity, and Polyline
- PyJWT, Passlib, and bcrypt

### Providers

- Gemini 2.5 Flash by default
- OpenStreetMap Nominatim and Photon geocoding
- OpenRouteService and public OSRM routing
- Wikimedia/Wikipedia media
- OpenWeather and optional Google Weather
- Optional Google Places, Routes, Geocoding, and transit fare lookup

## Production deployment

The recommended production topology is the Next.js frontend on Vercel plus the FastAPI API, continuously running planning worker, and PostgreSQL on Azure. The worker is a persistent process and should not be deployed as a Vercel Function.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the exact architecture, Vercel project settings, Azure container settings, production environment variables, and public launch checklist.

## Quick start with Docker

Docker is the simplest way to run the complete application because it starts PostgreSQL, applies migrations, launches the API, runs the planning worker, and serves the frontend.

### Prerequisites

- Docker Desktop with Docker Compose
- A Gemini API key for AI-generated destination and hotel suggestions

### 1. Create the backend environment file

From the repository root:

```powershell
Copy-Item Backend/.env.example Backend/.env
```

Edit `Backend/.env` and set at least:

```dotenv
SECRET_KEY=replace-with-a-random-secret-at-least-32-characters
GEMINI_API_KEY=your-gemini-api-key
```

The Compose file supplies its own PostgreSQL connection for the containers. Optional provider keys can remain empty.

### 2. Build and start the stack

```powershell
docker compose up --build
```

### 3. Open the application

- Frontend: [http://localhost:3000](http://localhost:3000)
- API root: [http://localhost:8000](http://localhost:8000)
- Interactive API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

### Useful Docker commands

```powershell
docker compose ps
docker compose logs -f backend planning-worker frontend
docker compose restart backend planning-worker frontend
docker compose down
```

`docker compose down` retains PostgreSQL data. The following command also deletes the local database volume and cannot be undone:

```powershell
docker compose down --volumes
```

The frontend reaches the backend through its same-origin `/api/backend` proxy. Compose supplies the internal `BACKEND_API_URL=http://backend:8000` value at runtime.

## Local development setup

### Prerequisites

- Python 3.12
- Node.js 22 and npm
- PostgreSQL 17 or a compatible PostgreSQL server

### 1. Configure PostgreSQL and environment variables

Create a database and copy the environment template:

```powershell
Copy-Item Backend/.env.example Backend/.env
```

Update `Backend/.env` with a working database URL, a secret of at least 32 characters, and a Gemini key:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/magic_trip_planner
SECRET_KEY=replace-with-a-random-secret-at-least-32-characters
GEMINI_API_KEY=your-gemini-api-key
```

Do not commit `Backend/.env`.

### 2. Install backend dependencies and apply migrations

```powershell
Set-Location Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-migrations.txt -r requirements-dev.txt
alembic upgrade head
```

### 3. Start the API

From `Backend/` with the virtual environment active:

```powershell
uvicorn app.main:app --reload
```

### 4. Start the planning worker

Open a second terminal:

```powershell
Set-Location Backend
.\.venv\Scripts\Activate.ps1
python -m app.workers.planning_worker
```

The automatic planning feature remains queued if this worker is not running.

### 5. Install and start the frontend

Open a third terminal:

```powershell
Set-Location Frontend
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment variables

Backend variables are loaded from `Backend/.env`.

### Core settings

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `DATABASE_URL` | Yes | None | PostgreSQL SQLAlchemy connection URL |
| `SECRET_KEY` | Yes | None | JWT/session signing secret; minimum 32 characters |
| `ALGORITHM` | No | `HS256` | Token-signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Login-session lifetime |
| `FRONTEND_ORIGINS` | No | Local ports | Comma-separated credentialed CORS origins |
| `SESSION_COOKIE_NAME` | No | `magictrip_session` | HttpOnly session-cookie name |
| `SESSION_COOKIE_SECURE` | No | `false` | Require HTTPS for the session cookie |
| `SESSION_COOKIE_SAMESITE` | No | `lax` | Cookie SameSite policy |
| `GOOGLE_AUTH_CLIENT_ID` | No | Empty | Public Google Identity Services Web client ID; enables Google sign-in |
| `GOOGLE_AUTH_CSRF_COOKIE_NAME` | No | `magictrip_google_csrf` | Short-lived double-submit cookie used during Google sign-in |
| `GOOGLE_AUTH_CSRF_MAX_AGE_SECONDS` | No | `600` | Google sign-in CSRF-token lifetime |
| `API_RATE_LIMIT_PER_MINUTE` | No | `180` | General API rate limit |
| `AUTH_RATE_LIMIT_PER_MINUTE` | No | `10` | Authentication endpoint rate limit |
| `PLANNING_WORKER_POLL_SECONDS` | No | `1.5` | Planning-job polling interval |
| `PROVIDER_CACHE_ENABLED` | No | `true` | Enable shared external-provider caching |
| `PROVIDER_CACHE_DEFAULT_TTL_SECONDS` | No | `3600` | Default external-provider cache lifetime |

### AI and non-Google providers

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | For AI suggestions | Empty | Server-side Gemini credential |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model identifier |
| `ORS_API_KEY` | No | Empty | Enables OpenRouteService before OSRM fallback |
| `OPENWEATHER_API_KEY` | No | Empty | Enables forecast enrichment |

### Optional Google providers

| Variable | Default | Purpose |
| --- | --- | --- |
| `GOOGLE_API_KEY` | Empty | Shared server-only Google web-services key |
| `GOOGLE_WEATHER_ENABLED` | `false` | Enable Google Weather |
| `GOOGLE_PLACES_ENABLED` | `false` | Enable Google Places adapter |
| `GOOGLE_ROUTES_ENABLED` | `false` | Enable Google Routes adapter |
| `GOOGLE_GEOCODING_ENABLED` | `false` | Enable Google Geocoding adapter |
| `GOOGLE_TRANSIT_FARES_ENABLED` | `false` | Request endpoint-specific transit fares when available |
| `GOOGLE_WEATHER_MONTHLY_LIMIT` | `3000` | Application-side weather request ceiling |
| `GOOGLE_PLACES_SEARCH_MONTHLY_LIMIT` | `1500` | Application-side Places search ceiling |
| `GOOGLE_PLACES_DETAILS_MONTHLY_LIMIT` | `400` | Application-side Places details ceiling |
| `GOOGLE_ROUTES_MONTHLY_LIMIT` | `2500` | Application-side Routes ceiling, also used by transit fares |
| `GOOGLE_GEOCODING_MONTHLY_LIMIT` | `3000` | Application-side geocoding ceiling |

All Google keys remain server-side. Never expose `GOOGLE_API_KEY` through a variable beginning with `NEXT_PUBLIC_`.

`GOOGLE_AUTH_CLIENT_ID` is a public OAuth identifier, not the `GOOGLE_API_KEY` and not a secret. The frontend obtains it from `/auth/google/config` at runtime, while the backend uses the same value to verify the token audience. This app does not require a Google OAuth client secret.

The current frontend displays OpenStreetMap tiles. Keep Google Places, Routes, and Geocoding disabled unless their use and map-display requirements have been reviewed. Google Weather and transit fare lookup can be enabled independently.

### Google account sign-in setup

1. Open [Google Auth Platform](https://console.cloud.google.com/auth/overview) and create or select a project.
2. Complete **Branding** with the Magic Trip Planner name, support email, homepage, privacy-policy URL, and developer contact.
3. Under **Audience**, choose **External** for public users. While the app is in Testing, add every Google account that needs to sign in as a test user.
4. Under **Clients**, create an OAuth client with application type **Web application**.
5. Add these **Authorized JavaScript origins**:
   - `http://localhost:3000` for local development;
   - `http://127.0.0.1:3000` if that local URL is used;
   - the exact production Vercel origin, such as `https://YOUR-PROJECT.vercel.app`;
   - the final custom domain too, when one is added.
   Google does not accept wildcard origins, so dynamic Vercel Preview URLs will not support the button unless each exact preview origin is registered. Use the stable production or custom domain for acceptance testing.
6. No Authorized redirect URI is required because the app uses the Google Identity Services JavaScript popup callback.
7. Copy the Web client ID (ending in `.apps.googleusercontent.com`) into `GOOGLE_AUTH_CLIENT_ID` in `Backend/.env` locally and on the Azure API Container App.
8. Restart the backend. The Google button appears automatically on both sign-in and registration screens.

Only the default `openid`, `email`, and `profile` identity information is used. The backend verifies the Google signature, audience, issuer, expiry, and verified email before it creates an HttpOnly Magic Trip Planner session. Existing Gmail or Google Workspace password accounts with the same verified email are linked automatically; other existing email accounts continue to use email/password to avoid unsafe account takeover through a third-party email address.

### Frontend settings

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `BACKEND_API_URL` | In production | `http://127.0.0.1:8000` in development | Server-only target for the same-origin `/api/backend` proxy |
| `NEXT_PUBLIC_API_BASE_URL` | No | `/api/backend` | Optional direct browser API base; leave unset in production |

`BACKEND_API_URL` is read at request time and can be changed without rebuilding the frontend. A `NEXT_PUBLIC_` override is embedded in browser JavaScript at build time and bypasses the first-party proxy.

## External providers and fallbacks

| Capability | Preferred provider | Fallback behavior |
| --- | --- | --- |
| Destination/hotel generation | Gemini | The API reports an actionable generation error |
| Geocoding | Optional Google, Nominatim, local Sri Lanka catalog | Broader canonical-name queries and Photon |
| Routing | Optional Google Routes or OpenRouteService | Public OSRM |
| Weather | Optional Google Weather | OpenWeather when configured, otherwise no forecast enrichment |
| Location images | Saved Wikimedia/Wikipedia source | Commons name search, themed query, then local SVG placeholder |
| Hotel search | OpenStreetMap-based search | Bounded nearby search and saved/AI estimates |
| Bus/train fares | Optional Google transit fare | Sri Lankan NTC bus-stage and railway-zone estimates |

The shared provider cache is stored in PostgreSQL, so backend and worker processes reuse the same cached responses. Google usage reservations are also persisted transactionally across processes.

Inspect provider configuration and application-side quota status without exposing credentials:

```powershell
Invoke-RestMethod http://localhost:8000/health/providers
```

## Images, maps, and routing

### Location and hotel images

Destination and hotel cards load remote images through the frontend endpoint `GET /api/image` rather than directly trusting arbitrary URLs.

The proxy:

- Accepts only HTTPS images from an allowlist of Wikimedia/Wikipedia and configured Google image hosts.
- Rewrites oversized Wikimedia thumbnail URLs to a broadly supported 1280-pixel variant.
- Streams and validates image bodies up to 10 MB.
- Keeps large upstream image bodies out of the Next.js incremental fetch cache.
- Retries a name-based Wikimedia Commons lookup when a saved image is missing or unavailable.
- Returns a local SVG placeholder only after all allowed sources fail.
- Does not cache transient placeholders, allowing a later request to recover automatically.

Profile pictures are a separate authenticated feature. JPEG, PNG, WebP, and GIF uploads are signature-checked and limited to 4 MB so requests stay below Vercel's function payload ceiling. They use private ETag-based caching.

### Location verification

AI-generated names are not trusted as map coordinates. Suggestions are processed through canonical query cleanup, destination-aware searches, progressively broader names, an offline Sri Lanka catalog, and external geocoders. Only valid latitude/longitude pairs are automatically selected.

If a name still cannot be resolved, the automatic workflow skips it and continues with verified places. Users can add a coordinate-backed result through place search.

### Route construction

The Route Agent:

1. Resolves the trip start location and every selected stop.
2. Creates one itinerary day for each trip date.
3. Assigns and orders places using time preferences and geographic distance.
4. Requests road geometry for every consecutive route segment.
5. Adds selected daily hotels when requested.
6. Optionally returns to the hotel and finally to the trip start location.
7. Stores route instructions, segment costs, coordinates, and encoded polylines for restoration.

## Transport and budget calculation

Budget calculation uses saved route segments whenever a route exists. Each origin-to-destination leg is repriced independently using its distance, endpoints, transport mode, and traveler count.

| Transport mode | Pricing unit | Behavior |
| --- | --- | --- |
| Bus/public transport | Per passenger | Endpoint fare when available; otherwise distance-derived NTC fare stages; multiplied by travelers |
| Train | Per passenger | Endpoint fare when available; otherwise railway distance-zone estimate; multiplied by travelers |
| Car, taxi, motorcycle | Per group | Distance-based vehicle estimate; not multiplied by travelers |
| Mixed | Depends on leg | Intercity legs use public-bus pricing; short local legs use a group transfer estimate |
| Walking/cycling | No ticket fare | Zero vehicle/ticket cost unless another transfer is added |

Hotel transfers are charged separately only when the selected hotel is not already represented in the route, which prevents duplicate costs. A simpler daily fallback is used only when no saved route is available.

The final budget also includes selected hotel totals, attraction fees, food per traveler per day, optional shopping/other costs, and an emergency buffer. All prices are estimates and should be verified before booking or travel.

## API overview

Interactive OpenAPI documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs) while the backend is running.

### Main endpoint groups

| Prefix | Purpose |
| --- | --- |
| `/auth` | Registration, login/logout, profile data, password, and profile picture |
| `/preferences` | Save, load, and choose whether to reuse traveler preferences |
| `/trips` | Create, list, restore, delete, and manage traveler toolkit data |
| `/destination` | Generate/search/select places and restore selected places |
| `/routes` | Generate, confirm, and restore route plans |
| `/hotels` | Generate/search/select trip-wide and per-day hotels |
| `/budget` | Calculate and restore budget estimates |
| `/planning` | Full-plan jobs, progress, cancellation, retry, and version history |
| `/collaboration` | Invite/list/remove trip viewers or editors |
| `/reviews` | Create and retrieve reviews |

### Recommended automatic workflow

1. `POST /auth/register` or `POST /auth/login`.
2. `POST /preferences/` if the traveler wants to save defaults.
3. `POST /trips/` to create a trip.
4. `POST /planning/trips/{trip_id}/jobs` with a unique `Idempotency-Key` header.
5. Poll `GET /planning/jobs/{job_id}` until the job completes, fails, or is cancelled.
6. Restore the trip, selected places/hotels, latest route, and latest budget through their read endpoints.

The planning worker must be running for step 5 to progress.

### Recommended manual workflow

1. Create the trip and decide whether to reuse saved preferences.
2. Generate destination suggestions.
3. Select coordinate-verified places.
4. Generate and confirm the initial route.
5. Search/select hotels for the trip or individual route days.
6. Regenerate the route with hotels enabled.
7. Calculate the budget after the route is saved.

Authentication uses an HttpOnly session cookie. Bearer tokens remain accepted for API clients, but the browser frontend sends cookie-authenticated requests with credentials included.

## Project structure

```text
Magic-Trip-Planner-Idealize/
|-- Backend/
|   |-- alembic/                 # Database migration environment and revisions
|   |-- app/
|   |   |-- agents/              # Destination, hotel, route, and budget agents
|   |   |-- api/routes/          # FastAPI endpoint modules
|   |   |-- core/                # Configuration, database, auth dependencies, middleware
|   |   |-- models/              # SQLAlchemy models
|   |   |-- schemas/             # Pydantic request/response schemas
|   |   |-- services/            # Maps, media, weather, cost, cache, access, versions
|   |   |-- workers/             # Durable automatic-planning worker
|   |   `-- main.py              # FastAPI application entry point
|   |-- tests/                   # Backend unit and contract tests
|   |-- .env.example             # Backend configuration template
|   |-- Dockerfile
|   |-- requirements.txt
|   |-- requirements-dev.txt
|   `-- requirements-migrations.txt
|-- Frontend/
|   |-- public/                  # Static assets and branding
|   |-- src/
|   |   |-- app/                 # Next.js routes and server image proxy
|   |   |-- components/          # UI and planner components
|   |   `-- lib/                 # API clients, state stores, types, and utilities
|   |-- Dockerfile
|   |-- next.config.ts
|   `-- package.json
|-- compose.yaml                 # Complete local stack
`-- README.md
```

## Testing and quality checks

Automated tests mock or disable paid Google providers. Normal tests, linting, and builds should not consume Google quota.

### Backend

```powershell
Set-Location Backend
.\.venv\Scripts\Activate.ps1
python -m pytest
python -m ruff check app tests
```

The test suite covers backend contracts, geocoding, Google service guards, hotel search, planning jobs, hotel-inclusive routing, transport costs, and trip access.

### Frontend

```powershell
Set-Location Frontend
npm ci
npm run lint
npm run build
```

Do not put real API keys in tests, fixtures, screenshots, logs, or CI configuration. Live provider smoke tests should be deliberate and isolated rather than run in loops.

## Security and privacy

- Session tokens are stored in HttpOnly cookies; the frontend does not store bearer tokens in local storage.
- Passwords are hashed with bcrypt and password changes require the current password.
- Profile uploads validate MIME type, file signature, and size.
- Credentialed CORS accepts only configured frontend origins.
- API and authentication endpoints have separate rate limits.
- Responses include request context and security headers.
- Provider URLs and remote image hosts are constrained to prevent arbitrary proxying.
- External-provider keys are server-only.
- Trip access distinguishes owners, editors, and viewers.
- Automatic planning creates a version checkpoint before changing a trip.
- Toolkit notes and expenses are private and excluded from offline export unless explicitly included.

For production:

```dotenv
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax
FRONTEND_ORIGINS=https://your-frontend.example
```

Use HTTPS, a strong unique `SECRET_KEY`, restricted provider credentials, database backups, and platform-level request/log monitoring.

## Troubleshooting

### The website opens but automatic planning never progresses

The planning worker is probably not running.

```powershell
docker compose ps
docker compose logs -f planning-worker
```

For local development, run `python -m app.workers.planning_worker` from `Backend/` with the virtual environment active.

### The backend fails during startup

Check configuration validation, database connectivity, and migrations:

```powershell
Set-Location Backend
alembic upgrade head
uvicorn app.main:app --reload
```

`SECRET_KEY` must be at least 32 characters, and `DATABASE_URL` must point to a reachable PostgreSQL database.

### Gemini suggestions fail

Confirm that `GEMINI_API_KEY` is present in `Backend/.env`, then restart both the backend and worker because both processes load the setting.

```powershell
docker compose restart backend planning-worker
```

### A location is not routed

- Confirm the suggestion has valid coordinates.
- Search for the place through the coordinate-backed place search.
- Re-add the verified result and regenerate the route.
- Check backend/worker logs for provider timeouts.

The automatic workflow intentionally skips unresolved labels rather than drawing an incorrect route.

### A route line is missing

Inspect the backend log for OpenRouteService, Google Routes, or OSRM errors. If `ORS_API_KEY` is configured incorrectly, remove it temporarily to allow the OSRM fallback. Also verify that every selected stop and hotel has valid coordinates.

### A location image shows the placeholder

The proxy returns a placeholder only when the saved source and all Wikimedia fallback searches fail or time out. Check the frontend log and request `/api/image` directly. Proxied location images and profile uploads are limited to 4 MB to remain below Vercel's function payload ceiling.

Because placeholders use `Cache-Control: no-store`, refreshing later can recover after a temporary upstream failure.

### Authentication works in the API but not the browser

- Verify the frontend deployment has a valid server-only `BACKEND_API_URL`.
- Confirm browser requests use `/api/backend/*`; leave `NEXT_PUBLIC_API_BASE_URL` unset for the recommended production setup.
- Add the exact frontend origin to `FRONTEND_ORIGINS`.
- Keep `SESSION_COOKIE_SECURE=false` for plain HTTP local development.
- Set it to `true` only when the site is served through HTTPS.
- Restart the frontend after changing `BACKEND_API_URL`.

### Database changes are missing

```powershell
Set-Location Backend
alembic current
alembic upgrade head
```

The API does not create or mutate the schema at import time. Alembic migrations must be applied.

### Check complete-stack health

```powershell
docker compose ps
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/health/providers
```

## Current limitations

- Prompts, search behavior, location fallbacks, transport estimates, and safety guidance are tuned primarily for Sri Lanka.
- Destination and hotel recommendations are AI-assisted suggestions, not guaranteed availability or booking inventory.
- A real place can still be missing from every configured map index; users must select a coordinate-backed result when automatic resolution fails.
- Public routing providers can be rate-limited or temporarily unavailable.
- Transit fare coverage is incomplete. Fare-table fallbacks remain estimates and travelers should verify actual ticket prices.
- Location images depend on third-party media availability and may use a representative fallback or placeholder.
- Collaboration requires the invited person to already have a MagicTripPlanner account.
- Email invitations, realtime cursors, live booking, payments, and complete authoritative Sri Lankan transport schedules are not included.
- The workflow is application-orchestrated; Gemini does not yet autonomously select and call external tools.

---

MagicTripPlanner is an academic/prototype project. Route, weather, fare, price, safety, and availability information should be verified with official providers before making travel decisions.
