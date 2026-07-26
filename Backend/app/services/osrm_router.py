from typing import List

from app.core.config import settings
from app.services.google_maps import google_maps_service
from app.services.map_http import map_http_client


class OSRMRouterService:
    BASE_URL = "https://router.project-osrm.org/route/v1"
    ORS_BASE_URL = "https://api.openrouteservice.org/v2/directions"

    @property
    def provider_label(self) -> str:
        if google_maps_service.enabled("routes"):
            return "Google Routes with OpenRouteService/OSRM fallback"
        if settings.ORS_API_KEY:
            return "OpenRouteService with OSRM fallback"
        return "OSRM"

    def _profile_from_transport(self, transport_type: str) -> str:
        transport_type = (transport_type or "car").lower()

        if transport_type in ["walking"]:
            return "walking"

        if transport_type in ["bike", "bicycle", "cycling"]:
            return "cycling"

        return "driving"

    def _ors_profile_from_transport(self, transport_type: str) -> str:
        transport_type = (transport_type or "car").lower()

        if transport_type in ["walking"]:
            return "foot-walking"

        if transport_type in ["bike", "bicycle", "cycling"]:
            return "cycling-regular"

        return "driving-car"

    def _encode_polyline(
        self,
        coordinates: List[dict],
        precision: int = 5,
    ) -> str:
        factor = 10 ** precision
        output = []
        previous_lat = 0
        previous_lng = 0

        for point in coordinates:
            lat = int(round(point["latitude"] * factor))
            lng = int(round(point["longitude"] * factor))

            delta_lat = lat - previous_lat
            delta_lng = lng - previous_lng

            previous_lat = lat
            previous_lng = lng

            output.append(self._encode_value(delta_lat))
            output.append(self._encode_value(delta_lng))

        return "".join(output)

    def _encode_value(self, value: int) -> str:
        value = ~(value << 1) if value < 0 else value << 1
        encoded = ""

        while value >= 0x20:
            encoded += chr((0x20 | (value & 0x1F)) + 63)
            value >>= 5

        encoded += chr(value + 63)

        return encoded

    def _simple_instruction(self, step: dict) -> str:
        maneuver = step.get("maneuver") or {}
        maneuver_type = maneuver.get("type", "continue")
        modifier = maneuver.get("modifier")
        road_name = step.get("name")

        text = maneuver_type.replace("_", " ").title()

        if modifier:
            text += f" {modifier}"

        if road_name:
            text += f" onto {road_name}"

        return text

    def _instructions_from_ors(self, route_feature: dict) -> list[dict]:
        instructions = []

        properties = route_feature.get("properties") or {}

        for segment in properties.get("segments", []):
            for step in segment.get("steps", []):
                instructions.append(
                    {
                        "instruction": step.get("instruction", "Continue"),
                        "distance_km": round((step.get("distance", 0) or 0) / 1000, 2),
                        "duration_minutes": round((step.get("duration", 0) or 0) / 60, 1),
                    }
                )

        return instructions

    def _route_with_ors(
        self,
        origin: dict,
        destination: dict,
        transport_type: str,
    ) -> dict:
        if not settings.ORS_API_KEY:
            raise ValueError("OpenRouteService is not configured.")

        profile = self._ors_profile_from_transport(transport_type)
        url = f"{self.ORS_BASE_URL}/{profile}/geojson"
        headers = {
            "Authorization": settings.ORS_API_KEY,
            "Content-Type": "application/json",
        }
        json_body = {
            "coordinates": [
                [origin["longitude"], origin["latitude"]],
                [destination["longitude"], destination["latitude"]],
            ],
            "instructions": True,
        }

        data = map_http_client.post_json(
            url,
            json_body=json_body,
            headers=headers,
            timeout=30,
            context="OpenRouteService routing",
        )

        features = data.get("features") or []

        if not features:
            raise ValueError("OpenRouteService returned no route features.")

        feature = features[0]
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []

        properties = feature.get("properties") or {}
        summary = properties.get("summary") or {}

        path_coordinates = [
            {
                "latitude": coordinate[1],
                "longitude": coordinate[0],
            }
            for coordinate in coordinates
        ]

        encoded_polyline = self._encode_polyline(path_coordinates)

        return {
            "distance_km": round((summary.get("distance", 0) or 0) / 1000, 2),
            "duration_minutes": round((summary.get("duration", 0) or 0) / 60, 1),
            "encoded_polyline": encoded_polyline,
            "path_coordinates": path_coordinates,
            "instructions": self._instructions_from_ors(feature),
        }

    def _route_with_osrm(
        self,
        origin: dict,
        destination: dict,
        transport_type: str,
    ) -> dict:

        profile = self._profile_from_transport(transport_type)

        coordinates_text = (
            f"{origin['longitude']},{origin['latitude']};"
            f"{destination['longitude']},{destination['latitude']}"
        )

        url = f"{self.BASE_URL}/{profile}/{coordinates_text}"

        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
        }

        data = map_http_client.get_json(
            url,
            params=params,
            timeout=30,
            context="OSRM routing",
        )

        if data.get("code") != "Ok" and profile != "driving":
            fallback_url = f"{self.BASE_URL}/driving/{coordinates_text}"
            data = map_http_client.get_json(
                fallback_url,
                params=params,
                timeout=30,
                context="OSRM driving fallback",
            )

        return data

    def route_between(
        self,
        origin: dict,
        destination: dict,
        transport_type: str,
    ) -> dict:

        if google_maps_service.enabled("routes"):
            try:
                google_route = google_maps_service.route_between(
                    origin=origin,
                    destination=destination,
                    transport_type=transport_type,
                )
                if google_route:
                    return google_route
            except Exception:
                pass

        if settings.ORS_API_KEY:
            try:
                return self._route_with_ors(
                    origin=origin,
                    destination=destination,
                    transport_type=transport_type,
                )
            except Exception:
                pass

        data = self._route_with_osrm(
            origin=origin,
            destination=destination,
            transport_type=transport_type,
        )

        if data.get("code") != "Ok":
            raise ValueError(f"OSRM route failed: {data.get('message', data.get('code'))}")

        route = data["routes"][0]

        geojson_coordinates = route["geometry"]["coordinates"]

        path_coordinates = [
            {
                "latitude": coordinate[1],
                "longitude": coordinate[0],
            }
            for coordinate in geojson_coordinates
        ]

        instructions = []

        legs = route.get("legs", [])

        for leg in legs:
            for step in leg.get("steps", []):
                instructions.append(
                    {
                        "instruction": self._simple_instruction(step),
                        "distance_km": round((step.get("distance", 0) or 0) / 1000, 2),
                        "duration_minutes": round((step.get("duration", 0) or 0) / 60, 1),
                    }
                )

        encoded_polyline = self._encode_polyline(path_coordinates)

        return {
            "distance_km": round((route.get("distance", 0) or 0) / 1000, 2),
            "duration_minutes": round((route.get("duration", 0) or 0) / 60, 1),
            "encoded_polyline": encoded_polyline,
            "path_coordinates": path_coordinates,
            "instructions": instructions,
        }
