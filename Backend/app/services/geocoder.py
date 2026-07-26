from typing import Optional

from app.services.google_maps import google_maps_service
from app.services.map_http import map_http_client


class GeocoderService:
    BASE_URL = "https://nominatim.openstreetmap.org/search"

    def geocode(
        self,
        query: str,
        country: str = "Sri Lanka",
    ) -> Optional[dict]:

        if not query:
            return None

        if google_maps_service.enabled("geocoding"):
            try:
                google_result = google_maps_service.geocode(query, country)
                if google_result:
                    return google_result
            except Exception:
                # Quota, availability, and configuration failures must never
                # prevent the existing no-cost provider from serving the user.
                pass

        search_text = query.strip()

        if country.lower() not in search_text.lower():
            search_text = f"{search_text}, {country}"

        cache_key = search_text.lower()

        params = {
            "q": search_text,
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
        }

        headers = {
            "User-Agent": "MagicTripPlanner/1.0 academic-project"
        }

        results = map_http_client.get_json(
            self.BASE_URL,
            params=params,
            headers=headers,
            timeout=15,
            cache_key=f"geocode:{cache_key}",
            min_interval_seconds=1.1,
            context="Nominatim geocoding",
        )

        if not results:
            return None

        item = results[0]

        result = {
            "display_name": item.get("display_name"),
            "latitude": float(item["lat"]) if item.get("lat") else None,
            "longitude": float(item["lon"]) if item.get("lon") else None,
        }

        return result
