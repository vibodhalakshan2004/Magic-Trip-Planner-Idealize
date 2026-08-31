from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str

    SECRET_KEY: str = Field(min_length=32)

    ALGORITHM: Literal["HS256"] = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(gt=0, le=10_080)

    FRONTEND_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    SESSION_COOKIE_NAME: str = "magictrip_session"
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    GOOGLE_AUTH_CLIENT_ID: str | None = None
    GOOGLE_AUTH_CSRF_COOKIE_NAME: str = "magictrip_google_csrf"
    GOOGLE_AUTH_CSRF_MAX_AGE_SECONDS: int = Field(default=600, ge=120, le=1_800)
    API_RATE_LIMIT_PER_MINUTE: int = Field(default=180, ge=10, le=10_000)
    AUTH_RATE_LIMIT_PER_MINUTE: int = Field(default=10, ge=3, le=100)

    PLANNING_WORKER_POLL_SECONDS: float = Field(default=1.5, ge=0.2, le=30)
    PROVIDER_CACHE_ENABLED: bool = True
    PROVIDER_CACHE_DEFAULT_TTL_SECONDS: int = Field(default=3_600, ge=60, le=2_592_000)

    GEMINI_API_KEY: str

    GEMINI_MODEL: str = "gemini-2.5-flash"

    ORS_API_KEY: str | None = None

    OPENWEATHER_API_KEY: str | None = None

    # One server-side key may be used for the four enabled Google web-service
    # APIs. Never expose this value through a NEXT_PUBLIC_ variable.
    GOOGLE_API_KEY: str | None = None

    # Weather data can be shown independently. Google Places, Routes, and
    # Geocoding-derived map content remain opt-in while the UI uses an OSM map.
    GOOGLE_WEATHER_ENABLED: bool = False
    GOOGLE_PLACES_ENABLED: bool = False
    GOOGLE_ROUTES_ENABLED: bool = False
    GOOGLE_GEOCODING_ENABLED: bool = False
    GOOGLE_TRANSIT_FARES_ENABLED: bool = False

    # Conservative application-side monthly limits. Their maximum accepted
    # values remain below Google's published free caps, leaving headroom for
    # console tests and delayed billing reports.
    GOOGLE_WEATHER_MONTHLY_LIMIT: int = Field(default=3_000, ge=0, le=9_000)
    GOOGLE_PLACES_SEARCH_MONTHLY_LIMIT: int = Field(default=1_500, ge=0, le=4_000)
    GOOGLE_PLACES_DETAILS_MONTHLY_LIMIT: int = Field(default=400, ge=0, le=800)
    GOOGLE_ROUTES_MONTHLY_LIMIT: int = Field(default=2_500, ge=0, le=8_000)
    GOOGLE_GEOCODING_MONTHLY_LIMIT: int = Field(default=3_000, ge=0, le=8_000)
    @property
    def frontend_origins(self) -> list[str]:
        return [origin.strip() for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]


settings = Settings()
