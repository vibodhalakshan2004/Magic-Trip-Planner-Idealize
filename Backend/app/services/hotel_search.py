import re

from app.services.map_http import map_http_client
from app.services.media_lookup import MediaLookupService
from app.services.google_maps import google_maps_service


class HotelSearchService:
    BASE_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(self):
        self.media_lookup = MediaLookupService()

    def search_hotels(
        self,
        query: str,
        destination: str,
        country: str = "Sri Lanka",
        limit: int = 5,
    ):
        google_query = f"{query}, {destination}, {country}"
        if google_maps_service.enabled("places"):
            try:
                google_results = google_maps_service.search_places(google_query, limit)
                if google_results:
                    return [self._google_suggestion(item, destination) for item in google_results]
            except Exception:
                pass

        headers = {
            "User-Agent": "MagicTripPlanner/1.0"
        }

        results = []
        seen_osm_keys = set()

        for search_text in self._search_queries(
            query=query,
            destination=destination,
            country=country,
        ):
            params = {
                "q": search_text,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": limit,
            }

            search_results = map_http_client.get_json(
                self.BASE_URL,
                params=params,
                headers=headers,
                timeout=10,
                cache_key=f"hotel-search:{search_text}:{limit}",
                min_interval_seconds=1.1,
                context="Nominatim hotel search",
            )

            for item in search_results:
                osm_key = (
                    item.get("osm_type"),
                    item.get("osm_id"),
                )

                if osm_key in seen_osm_keys:
                    continue

                seen_osm_keys.add(osm_key)
                results.append(item)

                if len(results) >= limit:
                    break

            if len(results) >= limit:
                break

        suggestions = []

        for item in results:
            display_name = item.get("display_name") or query
            name = self._extract_name(item, query)
            area = self._extract_area(item)
            media = self.media_lookup.lookup_media(display_name)

            suggestions.append(
                {
                    "hotel_key": self._make_hotel_key(display_name),
                    "name": name,
                    "short_description": media.get("description") or self._compose_short_description(area),
                    "hotel_type": self._map_hotel_type(item),
                    "source": "user_added",
                    "area": area,
                    "estimated_price_per_night_lkr": 0,
                    "total_estimated_price_lkr": 0,
                    "rating_estimate": None,
                    "latitude": float(item["lat"]) if item.get("lat") else None,
                    "longitude": float(item["lon"]) if item.get("lon") else None,
                    "distance_summary": None,
                    "reason_for_recommendation": "User searched and selected this accommodation.",
                    "amenities": [],
                    "warnings": [],
                    "search_query": display_name,
                    "image_url": media.get("image_url"),
                    "priority_score": 5,
                }
            )

        return suggestions

    def _google_suggestion(self, item: dict, destination: str) -> dict:
        name = (item.get("displayName") or {}).get("text") or "Accommodation"
        address = item.get("formattedAddress") or destination
        location = item.get("location") or {}
        return {
            "hotel_key": self._make_hotel_key(item.get("id") or name),
            "name": name,
            "short_description": f"Google Places accommodation result near {destination}. Live room inventory is not included.",
            "hotel_type": self._map_google_hotel_type(item),
            "source": "user_added",
            "area": address,
            "estimated_price_per_night_lkr": 0,
            "total_estimated_price_lkr": 0,
            "rating_estimate": None,
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "distance_summary": None,
            "reason_for_recommendation": "Accommodation returned by Google Places near the requested area.",
            "amenities": [],
            "warnings": ["Price and availability are estimates until confirmed with a booking provider."],
            "search_query": address,
            "image_url": None,
            "priority_score": 5,
        }

    def _map_google_hotel_type(self, item: dict) -> str:
        types = set(item.get("types") or [])
        primary_type = item.get("primaryType")
        if primary_type:
            types.add(primary_type)
        if "hostel" in types:
            return "hostel"
        if "resort_hotel" in types:
            return "resort"
        if "bed_and_breakfast" in types or "guest_house" in types:
            return "guest_house"
        return "hotel"

    def _search_queries(
        self,
        query: str,
        destination: str,
        country: str,
    ) -> list[str]:
        query = " ".join(query.split())
        destination = " ".join(destination.split())
        country = " ".join(country.split())

        candidates = [
            query,
            f"{query}, {country}",
            f"{query}, {destination}",
            f"{query} {destination} {country}",
            f"{query} in {destination} {country}",
            f"{query} near {destination} {country}",
            f"hotel near {query} {destination} {country}",
            f"hotel {destination} {country}",
            f"hotels in {destination} {country}",
            f"accommodation {destination} {country}",
            f"guest house {destination} {country}",
        ]

        unique_candidates = []

        for candidate in candidates:
            if candidate and candidate not in unique_candidates:
                unique_candidates.append(candidate)

        return unique_candidates

    def _extract_name(self, item: dict, fallback: str) -> str:
        address = item.get("address") or {}

        for key in [
            "tourism",
            "amenity",
            "building",
            "shop",
            "road",
        ]:
            if address.get(key):
                return address[key]

        display_name = item.get("display_name")

        if display_name:
            return display_name.split(",")[0].strip()

        return fallback.strip()

    def _extract_area(self, item: dict) -> str | None:
        address = item.get("address") or {}

        for key in [
            "suburb",
            "village",
            "town",
            "city",
            "county",
            "state",
        ]:
            if address.get(key):
                return address[key]

        return None

    def _map_hotel_type(self, item: dict) -> str:
        place_type = item.get("type")

        if place_type in ["guest_house", "guesthouse"]:
            return "guest_house"

        if place_type == "hostel":
            return "hostel"

        if place_type == "motel":
            return "hotel"

        if place_type == "apartment":
            return "apartment"

        if place_type == "resort":
            return "resort"

        return "hotel"

    def _compose_short_description(self, area: str | None) -> str:
        if area:
            return f"User-added accommodation in or near {area}."

        return "User-added accommodation near the selected destination."

    def _make_hotel_key(self, text: str) -> str:
        key = text.lower().strip()
        key = re.sub(r"[^a-z0-9]+", "_", key)
        key = key.strip("_")

        if not key:
            return "hotel"

        return key[:80]
