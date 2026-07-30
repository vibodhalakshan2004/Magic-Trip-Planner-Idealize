import re
from urllib.parse import quote, urlparse

from app.services.google_maps import google_maps_service
from app.services.map_http import map_http_client


class HotelSearchService:
    BASE_URL = "https://nominatim.openstreetmap.org/search"
    MAX_SEARCH_QUERIES = 2
    TRUSTED_IMAGE_HOSTS = {
        "upload.wikimedia.org",
        "commons.wikimedia.org",
    }

    def search_hotels(
        self,
        query: str,
        destination: str,
        country: str = "Sri Lanka",
        limit: int = 5,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_km: float = 20,
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

        centered_search = latitude is not None and longitude is not None

        for search_text in self._search_queries(
            query=query,
            destination=destination,
            country=country,
            centered=centered_search,
        )[: self.MAX_SEARCH_QUERIES]:
            params = {
                "q": search_text,
                "format": "jsonv2",
                "addressdetails": 1,
                "extratags": 1,
                "namedetails": 1,
                "countrycodes": "lk",
                "limit": limit,
            }

            if centered_search:
                params.update(
                    {
                        "viewbox": self._viewbox(float(latitude), float(longitude), radius_km),
                        "bounded": 1,
                    }
                )

            try:
                search_results = map_http_client.get_json(
                    self.BASE_URL,
                    params=params,
                    headers=headers,
                    timeout=4,
                    cache_key=f"hotel-search:{search_text}:{params.get('viewbox', '')}:{limit}",
                    min_interval_seconds=1.1,
                    context="Nominatim hotel search",
                )
            except Exception:
                continue

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

            if results:
                break

        suggestions = []

        for item in results:
            display_name = item.get("display_name") or query
            name = self._extract_name(item, query)
            area = self._extract_area(item)
            image_url = self._osm_image_url(item)
            description = self._osm_description(item)

            suggestions.append(
                {
                    "hotel_key": self._make_hotel_key(display_name),
                    "name": name,
                    "short_description": description or self._compose_short_description(area),
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
                    "image_url": image_url,
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
        centered: bool = False,
    ) -> list[str]:
        query = " ".join(query.split())
        destination = " ".join(destination.split())
        country = " ".join(country.split())

        if centered:
            candidates = [query, "hotel", "guest house", "hostel"]
        else:
            candidates = [
                f"{query}, {destination}, {country}",
                f"hotel, {destination}, {country}",
                f"guest house, {destination}, {country}",
                f"accommodation, {destination}, {country}",
            ]

        unique_candidates = []

        for candidate in candidates:
            if candidate and candidate not in unique_candidates:
                unique_candidates.append(candidate)

        return unique_candidates

    def _viewbox(self, latitude: float, longitude: float, radius_km: float) -> str:
        radius = max(2, min(radius_km, 75)) / 111
        return ",".join(
            [
                f"{longitude - radius:.6f}",
                f"{latitude + radius:.6f}",
                f"{longitude + radius:.6f}",
                f"{latitude - radius:.6f}",
            ]
        )

    def _osm_image_url(self, item: dict) -> str | None:
        tags = item.get("extratags") or {}
        value = tags.get("image") or tags.get("wikimedia_commons")

        if not value:
            return None

        if value.lower().startswith("file:"):
            filename = value.split(":", 1)[1].strip()
            if filename:
                return f"https://commons.wikimedia.org/wiki/Special:Redirect/file/{quote(filename)}"
            return None

        try:
            parsed = urlparse(value)
        except ValueError:
            return None

        if parsed.scheme == "https" and parsed.hostname in self.TRUSTED_IMAGE_HOSTS:
            return value

        return None

    def _osm_description(self, item: dict) -> str | None:
        tags = item.get("extratags") or {}
        description = tags.get("description")
        if not description:
            return None
        cleaned = " ".join(description.split())
        return cleaned if len(cleaned) <= 180 else cleaned[:177].rsplit(" ", 1)[0] + "..."

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
