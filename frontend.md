# Frontend Instructions For Codex

Build the frontend as a step-based trip planner that matches the existing FastAPI backend exactly. Do not invent new endpoints, rename payload fields, or skip workflow gates enforced by the API.

## Goal

Create a frontend that helps a user:

1. Register or log in
2. Save optional travel preferences
3. Create a trip
4. Generate destination suggestions
5. Select places
6. Generate hotel suggestions
7. Select hotels
8. Generate a route plan
9. Calculate the final budget

The frontend should feel like one connected planner, not a collection of unrelated forms.

## Recommended Frontend Shape

If Codex needs to scaffold a new frontend, prefer React + TypeScript. Use a clean state-driven architecture with:

- an auth store for the access token and current user
- a planner store for trip, preferences, suggested places, selected places, suggested hotels, selected hotels, route plan, and budget
- a typed API client layer for every backend route
- reusable form, card, stepper, map, and summary components

Use Sri Lanka-aware travel copy and format money in LKR.

## Required Workflow

Implement the planner in this order because the backend enforces it:

1. `POST /auth/register` or `POST /auth/login`
2. `POST /preferences/` if the user wants to save preferences
3. `POST /trips/`
4. `GET /preferences/choice-prompt` before destination generation if you want to support saved preference reuse cleanly
5. `POST /destination/trips/{trip_id}/suggest-places`
6. `POST /destination/trips/{trip_id}/select-places`
7. `GET /preferences/choice-prompt` before hotel generation if needed
8. `POST /hotels/trips/{trip_id}/suggest-hotels`
9. `POST /hotels/trips/{trip_id}/select-hotels`
10. `POST /routes/trips/{trip_id}/generate`
11. `POST /budget/trips/{trip_id}/calculate`

Do not allow hotel generation before places are selected.
Do not allow budget calculation before at least one hotel is selected.
Route generation should happen before budget calculation whenever possible so transport cost uses real route distance.

## Auth Requirements

Use bearer token authentication for protected routes.

- Save `access_token` from login
- Send `Authorization: Bearer <token>` on all authenticated requests
- Provide logout and token reset behavior
- Redirect unauthenticated users away from planner pages

## API Contracts To Match

### Register

`POST /auth/register`

Request:

```json
{
  "name": "User Name",
  "email": "user@example.com",
  "password": "string"
}
```

### Login

`POST /auth/login`

Expected response contains:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

### Preferences

`POST /preferences/`

Request fields:

- `travel_style`
- `food_preference`
- `interests`
- `preferred_transport`
- `preferred_hotel_type`
- `budget_min`
- `budget_max`

`GET /preferences/choice-prompt`

This route is important. It returns whether saved preferences exist and what they are. Use it to show a modal or inline decision card asking the user whether to reuse saved preferences or continue with fresh inputs.

### Trip Creation

`POST /trips/`

Required request fields:

- `start_location`
- `destination`
- `start_date`
- `end_date`
- `budget_min`
- `budget_max`
- `travelers`
- `transport_type`

Supported `transport_type` values:

- `car`
- `bus`
- `train`
- `taxi`
- `bike`
- `walking`
- `mixed`

### Destination Suggestions

`POST /destination/trips/{trip_id}/suggest-places`

Request fields:

- `use_saved_preferences`
- `interests`
- `trip_style`
- `special_notes`

Supported `trip_style` values:

- `relaxed`
- `balanced`
- `packed`

Important behavior:

- If saved preferences exist and `use_saved_preferences` is omitted, the backend can return `409` with a detail payload telling the frontend to ask the user whether to reuse saved preferences.
- The frontend must handle this explicitly instead of treating it like a generic error.

Render each suggested place with:

- name
- category
- short description
- a visible short description snippet on the card, not just inside expanded details
- a preview image or thumbnail for the place
- reason for recommendation
- best time to visit
- estimated visit duration
- estimated cost per person
- priority score
- suitable_for
- warnings
- weather_summary when present
- image_url when present
- coordinates when present

Place card requirement:

- every place card should show an image area and 2 to 4 lines of descriptive copy at a glance
- prefer the backend `short_description` as the primary card description
- prefer the backend `image_url` first for the primary card image
- if the backend `image_url` is missing, the frontend may resolve one from a trusted place-image source or a curated fallback mapping
- if no image can be resolved, show a category-aware placeholder image instead of leaving the card visually empty

### Place Selection

`POST /destination/trips/{trip_id}/select-places`

Send `selected_places` using the same place object shape returned by the destination suggestion response. Allow users to select from suggestions and optionally supplement with search-based choices from `GET /destination/trips/{trip_id}/place-search?query=...`.

The backend now persists place media fields, so selected place responses can include:

- `short_description`
- `weather_summary`
- `image_url`

### Hotel Suggestions

`POST /hotels/trips/{trip_id}/suggest-hotels`

Request fields:

- `use_saved_preferences`
- `hotel_type`
- `hotel_preference`
- `rooms`
- `max_results`

Supported `hotel_type` values:

- `hotel`
- `guest_house`
- `villa`
- `resort`
- `hostel`
- `homestay`
- `apartment`
- `any`

Important behavior:

- If no selected places exist yet, this call will fail.
- If saved preferences exist and `use_saved_preferences` is omitted, the backend can return `409` with a saved-preference prompt payload.

Render each hotel with:

- name
- short description
- hotel type
- a visible short description snippet on the card
- a preview image or thumbnail for the hotel
- area
- nights
- rooms
- estimated price per night
- total estimated price
- rating estimate
- distance summary
- reason for recommendation
- amenities
- warnings
- image_url when present
- coordinates when present

Hotel card requirement:

- every hotel card should show an image area and a short summary at a glance
- prefer backend `short_description` as the primary summary text
- if `short_description` is missing, compose fallback text from `reason_for_recommendation`, `distance_summary`, and `area`
- prefer the backend `image_url` first for the primary card image
- if the backend does not provide an image URL, the frontend may resolve one from a trusted hotel-image source or a curated fallback mapping
- if no image can be resolved, show a hotel-type-aware placeholder image instead of an empty box

Allow search assist from `GET /hotels/trips/{trip_id}/hotel-search?query=...`.

### Hotel Selection

`POST /hotels/trips/{trip_id}/select-hotels`

Send `selected_hotels` using the hotel recommendation object shape.

The backend now persists hotel media fields, so selected hotel responses can include:

- `short_description`
- `image_url`

### Route Generation

`POST /routes/trips/{trip_id}/generate`

Request fields:

- `day_start_time`
- `return_to_hotel`

Use the response to build:

- a day-by-day itinerary timeline
- map markers for stops
- route polylines from `day_path_coordinates` and `full_encoded_polyline`
- segment cards with instructions, distance, and duration

Each day includes:

- start and end points
- stops
- segments
- day distance
- day travel time
- encoded polyline
- path coordinates

Each segment includes turn instructions. Show them in a collapsible directions panel.

### Budget Calculation

`POST /budget/trips/{trip_id}/calculate`

Request fields:

- `food_cost_per_person_per_day_lkr`
- `shopping_other_cost_lkr`

Render:

- budget range
- total estimated cost
- remaining budget or over-budget amount
- places cost
- hotel cost
- food cost
- transport cost
- other cost
- subtotal
- buffer
- breakdown items
- warnings
- suggestions
- summary

Use `budget_status` to drive strong visual feedback:

- `within_budget`
- `near_limit`
- `over_budget`

## UX Requirements

The UI should be built as a guided planner with visible progress. Recommended screens or sections:

1. Auth
2. Preferences
3. Trip setup
4. Destinations
5. Hotels
6. Route plan
7. Budget
8. Final review

Required UX behaviors:

- persist the current trip id and planning state locally so a refresh does not destroy the session
- show disabled future steps until prerequisite data exists
- show loading states for AI generation and route generation
- show empty states with exact next actions
- show recoverable API errors inline near the failing step
- show a dedicated decision UI for saved preference reuse when a `409` prompt is returned
- allow users to revise earlier steps and regenerate downstream data intentionally

If a user changes selected places, mark hotels, route, and budget as stale.
If a user changes selected hotels, mark route and budget as stale when relevant.

## Map And Visualization Requirements

The route response is already designed for map rendering. Build a map view that supports:

- markers for each itinerary stop
- a colored polyline per day
- a combined route overview
- clicking a stop to highlight its matching day card
- clicking a segment to reveal turn-by-turn instructions

If a decoded polyline utility is needed, use one. But do not depend on decoding alone because the backend already sends `path_coordinates` arrays that can be plotted directly.

## Media Handling Requirements

The backend now attempts to enrich places and hotels with media fields. Frontend code generated by Codex must use those backend fields first and fall back gracefully when enrichment is unavailable.

- do not block the planner if an image cannot be loaded
- lazy-load card images and show skeletons while loading
- keep image aspect ratios consistent across place and hotel cards
- always render alt text using the place or hotel name
- prefer graceful fallback images over broken image icons
- keep the short description visible even when the image fails to load
- use backend `image_url` as the first image source for both places and hotels
- use backend `short_description` as the first summary source for hotels

## Frontend Guardrails

- Do not fabricate client-side business logic that conflicts with the backend workflow.
- Do not silently swallow `409`, `400`, `401`, `404`, or `500` responses.
- Do not assume preferences should always be reused automatically.
- Do not assume every suggestion includes coordinates or weather data.
- Do not require hotel selection to be only AI-generated; allow the search-assist flow to help users refine choices.

## Implementation Priorities

If Codex builds this incrementally, use this order:

1. auth and API client
2. planner state model
3. trip and preference forms
4. destination suggestion and selection UI
5. hotel suggestion and selection UI
6. route map and itinerary timeline
7. budget dashboard
8. refresh persistence and stale-state handling

## Definition Of Done

The frontend is only complete when a user can start from login, create a trip, select places, select hotels, generate a route, and calculate a budget without needing manual API calls outside the UI.