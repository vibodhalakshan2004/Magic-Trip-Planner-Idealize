from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes.auth import router as auth_router
from app.api.routes.trips import router as trip_router
from app.api.routes.preferences import router as preference_router
from app.api.routes.reviews import router as review_router
from app.api.routes.destination import router as destination_router
from app.api.routes.hotels import router as hotel_router
from app.api.routes.budget import router as budget_router

from app.api.routes.route_plan import router as route_plan_router
from app.core.database import get_db
from app.core.config import settings
from app.services.google_quota import google_quota_guard


class HealthResponse(BaseModel):
    status: str
    database: str


class ProviderHealthResponse(BaseModel):
    google_key_configured: bool
    enabled: dict[str, bool]
    usage: list[dict[str, int | str]]

app = FastAPI(
    title="MagicTripPlanner API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(trip_router)
app.include_router(preference_router)
app.include_router(review_router)
app.include_router(destination_router)
app.include_router(hotel_router)
app.include_router(budget_router)
app.include_router(route_plan_router)


@app.get("/")
def root():

    return {
        "message": "MagicTripPlanner Backend Running"
    }


@app.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

    except Exception:
        return {
            "status": "degraded",
            "database": "unavailable",
        }

    return {
        "status": "ok",
        "database": "ok",
    }


@app.get("/health/providers", response_model=ProviderHealthResponse)
def provider_health():
    return {
        "google_key_configured": bool(settings.GOOGLE_API_KEY),
        "enabled": {
            "weather": bool(settings.GOOGLE_API_KEY and settings.GOOGLE_WEATHER_ENABLED),
            "places": bool(settings.GOOGLE_API_KEY and settings.GOOGLE_PLACES_ENABLED),
            "routes": bool(settings.GOOGLE_API_KEY and settings.GOOGLE_ROUTES_ENABLED),
            "geocoding": bool(settings.GOOGLE_API_KEY and settings.GOOGLE_GEOCODING_ENABLED),
        },
        "usage": [
            {
                "sku": item.sku,
                "used": item.used,
                "limit": item.limit,
                "remaining": item.remaining,
            }
            for item in google_quota_guard.status()
        ],
    }
