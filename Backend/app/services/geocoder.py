import re
from collections.abc import Iterable
from typing import Optional

from app.services.google_maps import google_maps_service
from app.services.location_catalog import lookup_sri_lanka_location
from app.services.map_http import map_http_client


class GeocoderService:
    BASE_URL = "https://nominatim.openstreetmap.org/search"
    MAX_FREE_PROVIDER_ATTEMPTS = 3

    _NOISE_PATTERNS = (
        r"\b(?:tickets?|entrance\s+fees?|entry\s+fees?|opening\s+hours?)\b",
        r"\b(?:price|cost|booking|official|history)\b",
        r"\b(?:safari|hike|tour)\b(?=\s*(?:,|$))",
    )

    def _clean_query(self, query: str) -> str:
        cleaned = query.strip()
        for pattern in self._NOISE_PATTERNS:
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:and|for)\b(?=\s*(?:,|$))", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+,", ",", cleaned)
        cleaned = re.sub(r",\s*,+", ",", cleaned)
        return " ".join(cleaned.split()).strip(" ,")

    def _candidate_queries(self, queries: Iterable[str]) -> list[str]:
        candidates: list[str] = []

        for query in queries:
            if not query or not query.strip():
                continue
            cleaned = self._clean_query(query)
            for candidate in (cleaned, query.strip()):
                if candidate and candidate.casefold() not in {
                    existing.casefold() for existing in candidates
                }:
                    candidates.append(candidate)

        return candidates

    def _nominatim_geocode(self, query: str, country: str) -> Optional[dict]:
        search_text = query.strip()

        if country.lower() not in search_text.lower():
            search_text = f"{search_text}, {country}"

        params = {
            "q": search_text,
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
        }
        if country.casefold() == "sri lanka":
            params["countrycodes"] = "lk"

        try:
            results = map_http_client.get_json(
                self.BASE_URL,
                params=params,
                headers={"User-Agent": "MagicTripPlanner/1.0 academic-project"},
                timeout=12,
                cache_key=f"geocode:{search_text.lower()}",
                min_interval_seconds=1.1,
                context="Nominatim geocoding",
            )
        except Exception:
            return None

        if not results:
            return None

        item = results[0]
        if not item.get("lat") or not item.get("lon"):
            return None

        return {
            "display_name": item.get("display_name"),
            "latitude": float(item["lat"]),
            "longitude": float(item["lon"]),
            "provider": "openstreetmap",
        }

    def geocode_candidates(
        self,
        queries: Iterable[str],
        country: str = "Sri Lanka",
    ) -> Optional[dict]:
        candidates = self._candidate_queries(queries)
        if not candidates:
            return None

        if country.casefold() == "sri lanka":
            for candidate in candidates:
                local_result = lookup_sri_lanka_location(candidate)
                if local_result:
                    return local_result

        # At most one paid Google request is allowed for a logical lookup,
        # even when several free-provider query variants are available.
        if google_maps_service.enabled("geocoding"):
            try:
                google_result = google_maps_service.geocode(candidates[0], country)
                if google_result:
                    return google_result
            except Exception:
                pass

        for candidate in candidates[: self.MAX_FREE_PROVIDER_ATTEMPTS]:
            result = self._nominatim_geocode(candidate, country)
            if result:
                return result

        return None

    def geocode(
        self,
        query: str,
        country: str = "Sri Lanka",
    ) -> Optional[dict]:
        return self.geocode_candidates([query], country)
