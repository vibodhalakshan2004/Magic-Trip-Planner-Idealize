from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings


class GoogleQuotaExceeded(RuntimeError):
    """Raised before an external call would exceed its configured allowance."""


@dataclass(frozen=True)
class GoogleQuotaStatus:
    sku: str
    used: int
    limit: int

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)


class GoogleQuotaGuard:
    """Persistent, process-safe counters for conservative Google API limits.

    The counter is reserved before the HTTP request. Failed calls therefore
    still consume local allowance, which intentionally errs on the safe side.
    """

    _lock = threading.Lock()

    def __init__(self, database_path: Path | None = None):
        self.database_path = Path(database_path or settings.GOOGLE_USAGE_DB_PATH)

    @staticmethod
    def _period() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    @staticmethod
    def limits() -> dict[str, int]:
        return {
            "weather": settings.GOOGLE_WEATHER_MONTHLY_LIMIT,
            "places_search": settings.GOOGLE_PLACES_SEARCH_MONTHLY_LIMIT,
            "places_details": settings.GOOGLE_PLACES_DETAILS_MONTHLY_LIMIT,
            "routes": settings.GOOGLE_ROUTES_MONTHLY_LIMIT,
            "geocoding": settings.GOOGLE_GEOCODING_MONTHLY_LIMIT,
        }

    def _connect(self) -> sqlite3.Connection:
        if self.database_path.parent != Path("."):
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS google_api_usage (
                period TEXT NOT NULL,
                sku TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (period, sku)
            )
            """
        )
        return connection

    def reserve(self, sku: str, units: int = 1) -> GoogleQuotaStatus:
        if units < 1:
            raise ValueError("Quota units must be at least one.")

        limits = self.limits()
        if sku not in limits:
            raise ValueError(f"Unknown Google API quota SKU: {sku}")

        limit = limits[sku]
        period = self._period()

        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT used FROM google_api_usage WHERE period = ? AND sku = ?",
                (period, sku),
            ).fetchone()
            used = int(row[0]) if row else 0

            if used + units > limit:
                connection.rollback()
                raise GoogleQuotaExceeded(
                    f"Google {sku} safety limit reached ({used}/{limit}). "
                    "The request was not sent; a fallback provider will be used."
                )

            new_used = used + units
            connection.execute(
                """
                INSERT INTO google_api_usage(period, sku, used)
                VALUES (?, ?, ?)
                ON CONFLICT(period, sku) DO UPDATE SET used = excluded.used
                """,
                (period, sku, new_used),
            )
            connection.commit()

        return GoogleQuotaStatus(sku=sku, used=new_used, limit=limit)

    def status(self) -> list[GoogleQuotaStatus]:
        period = self._period()
        limits = self.limits()

        with self._lock, self._connect() as connection:
            rows = dict(
                connection.execute(
                    "SELECT sku, used FROM google_api_usage WHERE period = ?",
                    (period,),
                ).fetchall()
            )

        return [
            GoogleQuotaStatus(sku=sku, used=int(rows.get(sku, 0)), limit=limit)
            for sku, limit in limits.items()
        ]


google_quota_guard = GoogleQuotaGuard()
