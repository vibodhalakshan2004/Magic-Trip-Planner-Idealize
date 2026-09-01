from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

import polyline

from app.core.config import settings
from app.services.google_quota import google_quota_guard
from app.services.map_http import map_http_client


class GoogleMapsService:
    GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
    ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
    WEATHER_DAILY_URL = "https://weather.googleapis.com/v1/forecast/days:lookup"

    @property
    def configured(self) -> bool:
        return bool(settings.GOOGLE_API_KEY)

    def enabled(self, service: str) -> bool:
        return self.configured and bool(
            {
                "weather": settings.GOOGLE_WEATHER_ENABLED,
                "places": settings.GOOGLE_PLACES_ENABLED,
                "routes": settings.GOOGLE_ROUTES_ENABLED,
                "geocoding": settings.GOOGLE_GEOCODING_ENABLED,
                "transit_fares": settings.GOOGLE_TRANSIT_FARES_ENABLED,
            }.get(service, False)
        )

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]

    def geocode(self, query: str, country: str = "Sri Lanka") -> dict | None:
        if not self.enabled("geocoding") or not query.strip():
            return None

        search_text = query.strip()
        if country.lower() not in search_text.lower():
            search_text = f"{search_text}, {country}"

        data = map_http_client.get_json(
            self.GEOCODING_URL,
            params={"address": search_text, "region": "lk", "key": settings.GOOGLE_API_KEY},
            timeout=15,
            cache_key=f"google-geocode:{self._digest(search_text.lower())}",
            context="Google Geocoding",
            before_request=lambda: google_quota_guard.reserve("geocoding"),
        )
        results = data.get("results") or []
        if not results:
            return None

        item = results[0]
        location = (item.get("geometry") or {}).get("location") or {}
        if location.get("lat") is None or location.get("lng") is None:
            return None

        return {
            "display_name": item.get("formatted_address") or search_text,
            "latitude": float(location["lat"]),
            "longitude": float(location["lng"]),
            "provider": "google_geocoding",
            "place_id": item.get("place_id"),
        }

    def search_places(
        self,
        text_query: str,
        limit: int = 5,
        *,
        included_type: str | None = None,
        strict_type_filtering: bool = False,
    ) -> list[dict]:
        if not self.enabled("places") or not text_query.strip():
            return []

        field_mask = ",".join(
            [
                "places.id",
                "places.displayName",
                "places.formattedAddress",
                "places.location",
                "places.primaryType",
                "places.types",
                "places.googleMapsUri",
            ]
        )
        request_body: dict[str, Any] = {
            "textQuery": text_query,
            "pageSize": max(1, min(limit, 10)),
            "languageCode": "en",
            "regionCode": "LK",
        }
        if included_type:
            request_body["includedType"] = included_type
            request_body["strictTypeFiltering"] = strict_type_filtering

        data = map_http_client.post_json(
            self.PLACES_TEXT_SEARCH_URL,
            json_body=request_body,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": settings.GOOGLE_API_KEY or "",
                "X-Goog-FieldMask": field_mask,
            },
            timeout=20,
            cache_key=(
                f"google-places:{self._digest(text_query.lower())}:{limit}:"
                f"{included_type or 'any'}:{int(strict_type_filtering)}"
            ),
            context="Google Places text search",
            before_request=lambda: google_quota_guard.reserve("places_search"),
        )
        return list(data.get("places") or [])[:limit]

    def route_between(self, origin: dict, destination: dict, transport_type: str) -> dict | None:
        if not self.enabled("routes"):
            return None

        mode = {
            "walking": "WALK",
            "walk": "WALK",
            "bike": "BICYCLE",
            "bicycle": "BICYCLE",
            "cycling": "BICYCLE",
            "motorcycle": "TWO_WHEELER",
        }.get((transport_type or "car").lower(), "DRIVE")

        body: dict[str, Any] = {
            "origin": {"location": {"latLng": {"latitude": origin["latitude"], "longitude": origin["longitude"]}}},
            "destination": {"location": {"latLng": {"latitude": destination["latitude"], "longitude": destination["longitude"]}}},
            "travelMode": mode,
            "languageCode": "en-US",
            "units": "METRIC",
            "polylineQuality": "HIGH_QUALITY",
        }
        if mode == "DRIVE":
            body["routingPreference"] = "TRAFFIC_AWARE"

        cache_text = f"{origin['latitude']:.5f},{origin['longitude']:.5f}:{destination['latitude']:.5f},{destination['longitude']:.5f}:{mode}"
        data = map_http_client.post_json(
            self.ROUTES_URL,
            json_body=body,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": settings.GOOGLE_API_KEY or "",
                "X-Goog-FieldMask": "routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline,routes.legs.steps.distanceMeters,routes.legs.steps.staticDuration,routes.legs.steps.navigationInstruction.instructions",
            },
            timeout=30,
            cache_key=f"google-route:{self._digest(cache_text)}",
            context="Google Routes",
            before_request=lambda: google_quota_guard.reserve("routes"),
        )
        routes = data.get("routes") or []
        if not routes:
            return None

        route = routes[0]
        encoded = ((route.get("polyline") or {}).get("encodedPolyline")) or ""
        path_coordinates = [
            {"latitude": latitude, "longitude": longitude}
            for latitude, longitude in (polyline.decode(encoded) if encoded else [])
        ]
        instructions = []
        for leg in route.get("legs") or []:
            for step in leg.get("steps") or []:
                instruction = ((step.get("navigationInstruction") or {}).get("instructions")) or "Continue"
                instructions.append(
                    {
                        "instruction": instruction,
                        "distance_km": round(float(step.get("distanceMeters") or 0) / 1000, 2),
                        "duration_minutes": round(self._seconds(step.get("staticDuration")) / 60, 1),
                    }
                )

        return {
            "distance_km": round(float(route.get("distanceMeters") or 0) / 1000, 2),
            "duration_minutes": round(self._seconds(route.get("duration")) / 60, 1),
            "encoded_polyline": encoded,
            "path_coordinates": path_coordinates,
            "instructions": instructions,
            "provider": "Google Routes",
        }

    def transit_fare(
        self,
        origin: dict,
        destination: dict,
        transit_mode: str = "bus",
    ) -> dict | None:
        """Return Google's current per-passenger fare when full fare data exists."""
        if not self.enabled("transit_fares"):
            return None

        normalized_mode = (transit_mode or "bus").lower()
        allowed_modes = ["TRAIN"] if normalized_mode == "train" else ["BUS"]
        body: dict[str, Any] = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": origin["latitude"],
                        "longitude": origin["longitude"],
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": destination["latitude"],
                        "longitude": destination["longitude"],
                    }
                }
            },
            "travelMode": "TRANSIT",
            "transitPreferences": {
                "allowedTravelModes": allowed_modes,
                "routingPreference": "FEWER_TRANSFERS",
            },
            "languageCode": "en-US",
            "units": "METRIC",
        }
        cache_text = (
            f"{origin['latitude']:.5f},{origin['longitude']:.5f}:"
            f"{destination['latitude']:.5f},{destination['longitude']:.5f}:"
            f"TRANSIT:{normalized_mode}"
        )
        data = map_http_client.post_json(
            self.ROUTES_URL,
            json_body=body,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": settings.GOOGLE_API_KEY or "",
                "X-Goog-FieldMask": (
                    "routes.distanceMeters,routes.duration,"
                    "routes.travelAdvisory.transitFare"
                ),
            },
            timeout=30,
            cache_key=f"google-transit-fare:{self._digest(cache_text)}",
            cache_ttl_seconds=900,
            context="Google transit fare",
            before_request=lambda: google_quota_guard.reserve("routes"),
        )
        routes = data.get("routes") or []
        if not routes:
            return None

        route = routes[0]
        fare = (route.get("travelAdvisory") or {}).get("transitFare") or {}
        if fare.get("currencyCode") != "LKR":
            return None

        amount = float(fare.get("units") or 0) + (float(fare.get("nanos") or 0) / 1_000_000_000)
        if amount <= 0:
            return None

        return {
            "fare_lkr": round(amount, 2),
            "distance_km": round(float(route.get("distanceMeters") or 0) / 1000, 2),
            "duration_minutes": round(self._seconds(route.get("duration")) / 60, 1),
            "provider": "Google Routes transit fare",
            "transit_mode": normalized_mode,
        }

    def daily_weather(self, latitude: float, longitude: float, days: int = 10) -> dict[date, dict]:
        if not self.enabled("weather"):
            return {}

        # Two decimal places intentionally shares a forecast for nearby stops,
        # preventing one billable request for every attraction card.
        lat_bucket = round(latitude, 2)
        lng_bucket = round(longitude, 2)
        data = map_http_client.get_json(
            self.WEATHER_DAILY_URL,
            params={
                "key": settings.GOOGLE_API_KEY,
                "location.latitude": lat_bucket,
                "location.longitude": lng_bucket,
                "days": max(1, min(days, 10)),
                "pageSize": max(1, min(days, 10)),
                "unitsSystem": "METRIC",
                "languageCode": "en",
            },
            timeout=20,
            cache_key=f"google-weather:{lat_bucket:.2f}:{lng_bucket:.2f}:{days}",
            context="Google Weather daily forecast",
            before_request=lambda: google_quota_guard.reserve("weather"),
        )

        result: dict[date, dict] = {}
        for item in data.get("forecastDays") or []:
            display_date = item.get("displayDate") or {}
            try:
                forecast_date = date(
                    int(display_date["year"]),
                    int(display_date["month"]),
                    int(display_date["day"]),
                )
            except (KeyError, TypeError, ValueError):
                continue

            parts = [item.get("daytimeForecast") or {}, item.get("nighttimeForecast") or {}]
            probabilities = [
                float((((part.get("precipitation") or {}).get("probability") or {}).get("percent")) or 0)
                for part in parts
            ]
            rain_amounts = [
                float((((part.get("precipitation") or {}).get("qpf") or {}).get("quantity")) or 0)
                for part in parts
            ]
            conditions = {
                str((((part.get("weatherCondition") or {}).get("description") or {}).get("text")))
                for part in parts
                if (((part.get("weatherCondition") or {}).get("description") or {}).get("text"))
            }
            thunderstorm_probability = max(
                [float(part.get("thunderstormProbability") or 0) for part in parts],
                default=0,
            )
            if thunderstorm_probability >= 30:
                conditions.add("Thunderstorm")

            result[forecast_date] = {
                "temp_min": (item.get("minTemperature") or {}).get("degrees"),
                "temp_max": (item.get("maxTemperature") or {}).get("degrees"),
                "max_precipitation_probability": max(probabilities, default=0) / 100,
                "rain_mm": sum(rain_amounts),
                "conditions": conditions,
                "provider": "Google Weather",
            }
        return result

    @staticmethod
    def _seconds(duration: Any) -> float:
        if not duration:
            return 0.0
        text = str(duration)
        if text.endswith("s"):
            text = text[:-1]
        try:
            return float(text)
        except ValueError:
            return 0.0


google_maps_service = GoogleMapsService()
