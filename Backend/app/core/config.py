from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str

    SECRET_KEY: str = Field(min_length=32)

    ALGORITHM: Literal["HS256"] = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(gt=0, le=10_080)

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

    # Conservative application-side monthly limits. Their maximum accepted
    # values remain below Google's published free caps, leaving headroom for
    # console tests and delayed billing reports.
    GOOGLE_WEATHER_MONTHLY_LIMIT: int = Field(default=3_000, ge=0, le=9_000)
    GOOGLE_PLACES_SEARCH_MONTHLY_LIMIT: int = Field(default=1_500, ge=0, le=4_000)
    GOOGLE_PLACES_DETAILS_MONTHLY_LIMIT: int = Field(default=400, ge=0, le=800)
    GOOGLE_ROUTES_MONTHLY_LIMIT: int = Field(default=2_500, ge=0, le=8_000)
    GOOGLE_GEOCODING_MONTHLY_LIMIT: int = Field(default=3_000, ge=0, le=8_000)
    GOOGLE_USAGE_DB_PATH: Path = Path(".google_api_usage.sqlite3")


settings = Settings()
