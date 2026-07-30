# MagicTripPlanner

MagicTripPlanner is an AI-assisted full-stack travel planner built with FastAPI, PostgreSQL, Next.js, Gemini, OpenStreetMap services, OpenRouteService, and optional quota-guarded Google web services. It generates destination suggestions, hotel recommendations, editable route plans, weather guidance, and budget estimates for Sri Lanka-focused trips.

## Features

### Multi-agent planning
- Destination Agent suggests places based on trip data, request interests, saved user preferences, and weather-aware post-processing.
- Hotel Agent recommends accommodations near the selected places and trip destination.
- Route Agent generates day-wise itineraries with real map directions and polylines.
- Budget Agent aggregates places, hotels, food, transport, and buffer costs.

### Routing and map data
- Nominatim geocoding and search for destinations, places, and hotels.
- Selected places are auto-geocoded during save when coordinates are missing.
- Wikipedia-based media enrichment adds best-effort thumbnail images for places and hotels.
- Wikimedia Commons fallback image lookup is used when a Wikipedia summary has no usable image.
- OpenRouteService routing when `ORS_API_KEY` is configured.
- Automatic fallback to public OSRM if OpenRouteService is unavailable.
- Optional Google Routes, Places, and Geocoding adapters with automatic fallback to the existing providers.
- Google Weather daily forecasts with persistent application-side usage protection.
- OpenWeather forecast enrichment for selected places when trip dates overlap available forecast data.
- Route instructions, path coordinates, and encoded polylines for frontend map rendering.
- First day routing starts from the trip `start_location`.
- Daily stop order is optimized by time window and geographic proximity.
- Health endpoint for app and database readiness checks.
- Read endpoints for restoring saved trip, selected places, selected hotels, latest route plan, and latest budget estimate.

### Itinerary behavior
- Day-wise scheduling across the full trip date range.
- Preferred visit-time handling for sunrise, morning, afternoon, evening, and sunset stops.
- Hotel-aware end-of-day routing when return-to-hotel is enabled.
- Saved selected places and selected hotels are reused by route and budget generation.

### Media and card content
- Destination suggestions can now include `image_url` in addition to `short_description`, coordinates, and weather summaries.
- Selected place records persist `image_url` for frontend card rendering.
- Hotel suggestions can now include both `short_description` and `image_url`.
- Selected hotel records persist both `short_description` and `image_url` for frontend card rendering.

### Budget behavior
- Hotel totals are aggregated from the selected hotel records.
- Place fees are aggregated from the selected place records.
- Food cost is calculated per traveler per day.
- Transport cost uses saved route distance when a route plan exists.
- Fallback transport heuristics are used only when no route plan has been generated yet.
- Automatic emergency buffer and budget status classification.

### Traveler convenience
- Quick-start trip examples for hill-country, culture, and beach trips.
- Editable day, order, start time, and visit duration controls.
- One-click replanning for a late start, relaxed pace, or rain-friendly stop order.
- Final-summary print/PDF, calendar export, and Web Share/clipboard controls.
- A travel-day view, navigation handoff, packing checklist, and Sri Lanka verification reminders.
- A persistent traveler toolkit for private notes, emergency/meeting instructions, readiness tasks, and actual expenses.
- Actual-spend totals, per-traveler cost, and maximum-budget variance without contacting an external service.
- A self-contained offline HTML itinerary, with private toolkit data excluded unless the user explicitly includes it.
- Hotel booking-search and Google Maps handoff links that open only when the user chooses them and do not consume the project API key quota.
- Installable web-app metadata for supported browsers.
- One-click full-plan jobs with durable progress, cancellation, idempotency, and a separate worker process.
- Automatic and manual trip checkpoints with version restore.
- Viewer/editor sharing with other registered MagicTripPlanner accounts.

### Reliability and security
- HttpOnly, SameSite session cookies; bearer tokens remain accepted for API compatibility but are not stored by the frontend.
- Configurable credentialed CORS, authentication/API rate limits, request IDs, response timing, and security headers.
- Shared PostgreSQL provider cache and transaction-safe Google usage counters across backend and worker processes.
- Database indexes for trip restore, planning jobs, selected places/hotels, routes, budgets, reviews, and version history.

## Tech stack

- FastAPI
- SQLAlchemy
- PostgreSQL
- Gemini via `google-genai`
- Nominatim from OpenStreetMap
- OpenRouteService with OSRM fallback

## Project structure

```text
Backend/
  app/
    agents/
    api/routes/
    core/
    models/
    schemas/
    services/
  alembic/
  alembic.ini
  requirements.txt
  requirements-migrations.txt
```

## Environment variables

Copy `Backend/.env.example` to `Backend/.env`, then replace the placeholder values:

```dotenv
DATABASE_URL=postgresql://...
SECRET_KEY=replace-me
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
FRONTEND_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=lax
API_RATE_LIMIT_PER_MINUTE=180
AUTH_RATE_LIMIT_PER_MINUTE=10
PLANNING_WORKER_POLL_SECONDS=1.5
PROVIDER_CACHE_ENABLED=true
PROVIDER_CACHE_DEFAULT_TTL_SECONDS=3600
GEMINI_API_KEY=replace-me
GEMINI_MODEL=gemini-2.5-flash
ORS_API_KEY=optional-but-recommended
OPENWEATHER_API_KEY=optional
GOOGLE_API_KEY=optional
GOOGLE_WEATHER_ENABLED=false
GOOGLE_PLACES_ENABLED=false
GOOGLE_ROUTES_ENABLED=false
GOOGLE_GEOCODING_ENABLED=false
GOOGLE_WEATHER_MONTHLY_LIMIT=3000
GOOGLE_PLACES_SEARCH_MONTHLY_LIMIT=1500
GOOGLE_PLACES_DETAILS_MONTHLY_LIMIT=400
GOOGLE_ROUTES_MONTHLY_LIMIT=2500
GOOGLE_GEOCODING_MONTHLY_LIMIT=3000
```

Notes:
- `DATABASE_URL`, `SECRET_KEY`, and `GEMINI_API_KEY` are required.
- `ORS_API_KEY` is optional, but recommended. When present, the backend uses OpenRouteService first and falls back to OSRM if needed.
- `OPENWEATHER_API_KEY` is optional. When present, selected places are enriched with trip-date weather summaries and warnings.
- `GOOGLE_API_KEY` is a server-only key for the enabled Google Weather, Places, Routes, and Geocoding web services. Do not prefix it with `NEXT_PUBLIC_` and do not commit `Backend/.env`.
- In production, set `SESSION_COOKIE_SECURE=true` and replace `FRONTEND_ORIGINS` with the exact HTTPS frontend origin.

## Google API safety and free-limit protection

Google Maps Platform requires billing even when usage stays inside its monthly free caps. This project adds a second, stricter protection layer and does not rely only on billing alerts.

### Default behavior

- Google Weather is enabled only when `GOOGLE_API_KEY` is configured and `GOOGLE_WEATHER_ENABLED=true`.
- Google Places, Routes, and Geocoding are implemented but disabled by default while the frontend map uses Leaflet/OpenStreetMap.
- Every Google request reserves persistent local quota immediately before the HTTP request.
- Shared cached responses do not consume another local unit across backend processes.
- When a local limit is reached, the call is not sent and the existing OpenWeather, Nominatim, OpenRouteService, or OSRM provider is used.
- Trip dates outside Google's current 10-day forecast window do not trigger Weather API calls.
- Nearby locations share a weather cache bucket to prevent one request per attraction card.

Counters are stored transactionally in PostgreSQL so all containers share the same allowance. Inspect them without revealing the key:

```powershell
Invoke-RestMethod http://localhost:8000/health/providers
```

The response reports whether a key is configured, which services are enabled, and the used/remaining application allowance. It never returns the key.

### Conservative application limits

| Local counter | Default monthly limit | Published free-cap class |
| --- | ---: | ---: |
| Weather | 3,000 | 10,000 |
| Places text search | 1,500 | 5,000 Pro |
| Places detail enrichment | 400 | 1,000 Enterprise |
| Routes | 2,500 | 10,000 Essentials |
| Geocoding | 3,000 | 10,000 Essentials |

The settings schema rejects values above its built-in safety ceiling, which is still lower than the corresponding free cap. These counters only cover traffic sent by this application; calls from Cloud Console or other applications must be monitored separately.

### Required Google Cloud restrictions

1. Use a development-only Google Cloud project and billing budget.
2. Restrict the server key to exactly Places API (New), Routes API, Geocoding API, and Weather API.
3. Add server IP restrictions when the backend has a stable IP.
4. Set Cloud budget alerts and API quotas as an additional layer. Budget alerts do not stop charges by themselves.
5. Never use the live key in unit tests, CI, screenshots, logs, or committed fixtures.

### Maps display policy

Google Places results displayed on a map must use a Google map and the required attribution. The current application uses Leaflet/OpenStreetMap, so leave these settings false:

```dotenv
GOOGLE_PLACES_ENABLED=false
GOOGLE_ROUTES_ENABLED=false
GOOGLE_GEOCODING_ENABLED=false
```

Enable them only after migrating the mapped experience to Maps JavaScript API or after confirming that the relevant output is not displayed on the OSM map. Google Weather can be enabled independently after it is enabled in the same Google Cloud project. Repository defaults remain false and the non-Google providers continue as fallbacks.

### Testing policy

- Unit and contract tests mock Google responses and consume zero Google quota.
- Normal `pytest`, lint, and frontend build commands never call Google.
- Use no more than one explicit live smoke request per service after changing credentials.
- Do not run live external smoke tests in loops or CI.
- Use response field masks; never request all Place fields.
- Load detailed Place information only after a user selects a result.
- Traveler toolkit, expense, checklist, offline-export, print, calendar, and external handoff tests must use mocked/local data and consume zero Google requests.

## Setup

From `Backend/`:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-migrations.txt
pip install -r requirements-dev.txt
```

## Run the full stack with Docker

Docker Compose starts PostgreSQL, applies all Alembic migrations, and then
starts the FastAPI backend, durable planning worker, and Next.js frontend.

1. Optionally copy the backend environment template and add real API keys:

   ```powershell
   Copy-Item Backend/.env.example Backend/.env
   ```

   The stack can start with the example values, but Gemini-powered suggestions
   require a real `GEMINI_API_KEY`. Optional provider keys remain disabled until
   their matching feature flags are enabled.

2. Build and start every service from the repository root:

   ```powershell
   docker compose up --build
   ```

3. Open the application at [http://localhost:3000](http://localhost:3000).
   The API is available at [http://localhost:8000](http://localhost:8000), and
   its interactive docs are at [http://localhost:8000/docs](http://localhost:8000/docs).

Useful commands:

```powershell
docker compose ps                 # Check container health
docker compose logs -f            # Follow all service logs
docker compose down               # Stop containers and retain data
docker compose down --volumes     # Stop containers and delete local Docker data
```

PostgreSQL data, shared provider cache entries, and Google API quota counters
are stored in the `postgres_data` Docker volume. Google web-service features
remain disabled unless their individual flags are deliberately enabled. To use
a backend URL other than `http://localhost:8000`, set
`NEXT_PUBLIC_API_BASE_URL` before building the frontend, then rebuild it:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL = "http://your-host:8000"
docker compose build frontend
docker compose up -d
```

## Database setup

This backend now uses Alembic migrations instead of creating tables at import time.
The API does not mutate the schema during startup, so migrations must be applied before starting Uvicorn.

Apply the schema:

```powershell
alembic upgrade head
```

If you already have an existing database created by an older version of the app, the baseline migration is written to be safe on an already-populated schema and will add missing pieces such as the `preferences.interests` column when needed.

After pulling the latest changes, run migrations again so media/toolkit fields plus planning jobs, trip versions, collaborators, shared cache, quota counters, and performance indexes are added.

## Run the API

From `Backend/`:

```powershell
uvicorn app.main:app --reload
```

Root health response:

```json
{
  "message": "MagicTripPlanner Backend Running"
}
```

## Run tests

From `Backend/`:

```powershell
python -m pytest
```

From `Frontend/`:

```powershell
npm ci
npm run lint
npm run build
```

All automated tests use mocked or disabled Google providers. Do not add live API calls to the test suite.

## Recommended API flow

1. `POST /auth/register`
2. `POST /auth/login`
3. `POST /preferences/`
4. `POST /trips/`
5. `POST /destination/trips/{trip_id}/suggest-places`
6. `POST /destination/trips/{trip_id}/select-places`
7. `POST /hotels/trips/{trip_id}/suggest-hotels`
8. `POST /hotels/trips/{trip_id}/select-hotels`
9. `POST /routes/trips/{trip_id}/generate`
10. `POST /budget/trips/{trip_id}/calculate`
11. `PUT /trips/{trip_id}/toolkit` when the traveler saves notes, checklist items, or actual expenses

For the automatic workflow, send `POST /planning/trips/{trip_id}/jobs` with a unique `Idempotency-Key`, then poll `GET /planning/jobs/{job_id}`. Use the cancel endpoint when the traveler stops the job. The worker saves a checkpoint before it changes the itinerary.

Generating the route before the budget call gives the budget engine actual trip distance for transport cost estimation.

If saved preferences exist, call `GET /preferences/choice-prompt` before destination or hotel generation, ask the user whether to reuse them, and then send `use_saved_preferences: true` or `use_saved_preferences: false` in the suggestion request.

Useful restore/read endpoints for frontend refresh persistence:

- `GET /health`
- `GET /health/providers`
- `GET /trips/`
- `GET /trips/{trip_id}`
- `GET /destination/trips/{trip_id}/selected-places`
- `GET /hotels/trips/{trip_id}/selected-hotels`
- `GET /routes/trips/{trip_id}/latest`
- `GET /budget/trips/{trip_id}/latest`
- `GET /trips/{trip_id}/toolkit`

### Traveler toolkit and offline copy

- Toolkit records are owned by the same authenticated user as the trip and are never returned through a public link.
- Notes are limited to 5,000 characters, emergency/meeting instructions to 500 characters, checklist items to 50, and expenses to 200 per trip.
- Do not store passport numbers, payment-card details, passwords, or other secrets in the toolkit.
- The offline itinerary is a self-contained HTML file. It does not make API requests after download.
- Private notes, contacts, checklist status, and expenses are excluded from an offline file by default. The traveler must explicitly opt in before downloading them.
- Booking and direction buttons are ordinary user-opened web links. They do not expose `GOOGLE_API_KEY` and do not increment this application’s Google API counters.

## Backend notes

### Preferences
- Saved preferences now support `interests`, `preferred_transport`, and `preferred_hotel_type` consistently across the API and the AI agents.
- Destination and hotel suggestion endpoints no longer assume saved preferences should be used automatically.
- `GET /preferences/choice-prompt` returns the saved preference snapshot so the frontend can ask the user whether to reuse it or collect fresh inputs.

### Selected places
- `POST /destination/trips/{trip_id}/select-places` attempts to geocode missing coordinates before saving.
- The selected place response includes `weather_summary` when OpenWeather forecast data overlaps the trip dates.
- The selected place response can now include `image_url` for frontend thumbnails.
- Weather advisories are appended to the place `warnings` list for rain, thunderstorms, and hot outdoor conditions.

### Destination suggestions
- Destination suggestions are geocoded and weather-enriched after the Gemini response.
- Suggestion payloads can now include `latitude`, `longitude`, `weather_summary`, and `image_url` before the user selects places.
- Weather-sensitive outdoor suggestions may be slightly deprioritized when the trip forecast is unfavorable.

### Hotel suggestions
- Hotel suggestion payloads can now include `short_description` and `image_url` for frontend cards.
- Selected hotel responses can now include `short_description` and `image_url` after save.
- Daily search is bounded to two short OpenStreetMap requests, supports a 10-50 km UI radius, filters by accommodation type, and sorts results by transfer distance.
- Prices, ratings, and availability are labeled as estimates until a booking provider confirms them.

### Routing
- Daily routes begin from the trip `start_location` on day 1.
- Subsequent days use hotel or destination fallback points.
- Route ordering is optimized before calling the routing provider.

### External services
- Nominatim search and geocoding now share one rate-limited HTTP client with caching and retries.
- Routing uses OpenRouteService when available and OSRM as fallback.

## Limitations

- The travel domain is currently tuned for Sri Lanka-focused searches and prompts.
- Hotel recommendations are AI-assisted estimates, not live booking inventory.
- Transport cost is still an estimate, even when route distance is available.
- Google APIs do not provide general live hotel inventory or complete authoritative Sri Lankan train/bus schedules; booking and local-transport partners are still required for those features.
- Collaboration currently requires the invited traveler to have an account; email delivery and simultaneous live cursor editing require a notification/realtime provider.

## High-level architecture

```text
User Input
   |
HttpOnly Session + Preferences + Trip Setup
   |
Durable Planning Job (progress / cancel / checkpoint)
   |
Destination Agent
   |
Route Agent (OpenRouteService -> OSRM fallback)
   |
Daily Hotel Search (OpenStreetMap, Google disabled by default)
   |
Final Route + Budget Agent
   |
Versioned Trip Plan JSON
   |
Frontend Map + Timeline UI
```
