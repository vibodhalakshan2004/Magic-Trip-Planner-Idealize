import json
import re
from typing import Any, Dict, List, Optional

from google.genai import types
from google.genai.errors import ClientError, ServerError
from pydantic import ValidationError

from app.agents.gemini_client import client
from app.core.config import settings
from app.schemas.hotel import HotelAgentResponse, HotelSuggestRequest
from app.services.media_lookup import MediaLookupService


GEMINI_HOTEL_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "trip_id": {"type": "string"},
        "destination": {"type": "string"},
        "nights": {"type": "integer"},
        "rooms": {"type": "integer"},
        "summary": {"type": "string"},
        "recommended_hotels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "hotel_key": {"type": "string"},
                    "name": {"type": "string"},
                    "hotel_type": {"type": "string"},
                    "source": {"type": "string"},
                    "area": {"type": "string"},
                    "nights": {"type": "integer"},
                    "rooms": {"type": "integer"},
                    "estimated_price_per_night_lkr": {"type": "number"},
                    "total_estimated_price_lkr": {"type": "number"},
                    "rating_estimate": {"type": "number"},
                    "distance_summary": {"type": "string"},
                    "reason_for_recommendation": {"type": "string"},
                    "amenities": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "warnings": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "search_query": {"type": "string"},
                    "priority_score": {"type": "integer"}
                },
                "required": [
                    "hotel_key",
                    "name",
                    "hotel_type",
                    "source",
                    "area",
                    "nights",
                    "rooms",
                    "estimated_price_per_night_lkr",
                    "total_estimated_price_lkr",
                    "rating_estimate",
                    "distance_summary",
                    "reason_for_recommendation",
                    "amenities",
                    "warnings",
                    "search_query",
                    "priority_score"
                ]
            }
        },
        "question_for_user": {"type": "string"}
    },
    "required": [
        "trip_id",
        "destination",
        "nights",
        "rooms",
        "summary",
        "recommended_hotels",
        "question_for_user"
    ]
}


class HotelAgent:

    def __init__(self):
        self.media_lookup = MediaLookupService()

    def _make_key(self, name: str) -> str:
        key = name.lower().strip()
        key = re.sub(r"[^a-z0-9]+", "_", key)
        key = key.strip("_")

        if not key:
            return "hotel"

        return key[:80]

    def _calculate_nights(self, trip: Any) -> int:
        nights = (trip.end_date - trip.start_date).days

        if nights <= 0:
            nights = 1

        return nights
    
    def _normalize_hotel_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        hotels = data.get("recommended_hotels", [])

        for hotel in hotels:
            rating = hotel.get("rating_estimate")

            if rating is None:
                continue

            try:
                rating = float(rating)

            except (TypeError, ValueError):
                hotel["rating_estimate"] = None
                continue

            # If Gemini gives rating out of 10, convert it to rating out of 5.
            if rating > 5 and rating <= 10:
                rating = rating / 2

            # If still too high, safely cap it.
            if rating > 5:
                rating = 5

            if rating < 0:
                rating = 0

            hotel["rating_estimate"] = round(rating, 1)

        return data

    def _compose_short_description(self, hotel: Any) -> str:
        parts = []

        for value in [
            getattr(hotel, "area", None),
            getattr(hotel, "distance_summary", None),
            getattr(hotel, "reason_for_recommendation", None),
        ]:
            if value and value not in parts:
                parts.append(value.strip())

        if parts:
            return " ".join(parts)[:180].strip()

        return "Accommodation option near the selected trip area."

    def _enrich_hotels(self, trip: Any, result: HotelAgentResponse) -> HotelAgentResponse:
        for hotel in result.recommended_hotels:
            if not hotel.search_query:
                hotel.search_query = f"{hotel.name} {trip.destination} Sri Lanka"

            media = self.media_lookup.lookup_media(hotel.search_query)

            if not hotel.short_description:
                hotel.short_description = media.get("description") or self._compose_short_description(hotel)

            if not hotel.image_url:
                hotel.image_url = media.get("image_url")

        return result

    def _build_prompt(
        self,
        trip: Any,
        selected_places: List[Any],
        request: HotelSuggestRequest,
        preference: Optional[Any] = None,
    ) -> str:

        nights = self._calculate_nights(trip)

        trip_data = {
            "trip_id": str(trip.id),
            "destination": trip.destination,
            "start_date": str(trip.start_date),
            "end_date": str(trip.end_date),
            "nights": nights,
            "budget_min": trip.budget_min,
            "budget_max": trip.budget_max,
            "travelers": trip.travelers,
            "transport_type": trip.transport_type,
        }

        selected_places_data = []

        for place in selected_places:
            selected_places_data.append(
                {
                    "name": place.name,
                    "category": place.category,
                    "source": getattr(place, "source", "ai_suggested"),
                    "search_query": place.search_query,
                }
            )

        request_data = request.model_dump(mode="json")

        preference_data = None

        if preference:
            preference_data = {
                "hotel_preference": getattr(preference, "preferred_hotel_type", None),
                "travel_style": getattr(preference, "travel_style", None),
                "transport_preference": getattr(preference, "preferred_transport", None),
            }

        return f"""
You are the Hotel Recommendation Agent for MagicTripPlanner.

Recommend exactly {request.max_results} real or realistic hotels/accommodations near the user's destination.

Rules:
- Return only JSON.
- Do not use markdown.
- Keep text short.
- Recommend hotels that match budget, selected places, travelers, rooms, and preference.
- Prefer hotels convenient for visiting selected places.
- Prices must be in Sri Lankan Rupees.
- total_estimated_price_lkr = estimated_price_per_night_lkr * nights * rooms.
- priority_score must be from 1 to 10.
- source must be ai_suggested.
- search_query must be useful for Google Places or OpenStreetMap.
- hotel_type must be one of: hotel, guest_house, villa, resort, hostel, homestay, apartment.
- Do not include check_in_date or check_out_date.

Trip data:
{json.dumps(trip_data, ensure_ascii=False, indent=2)}

Selected places:
{json.dumps(selected_places_data, ensure_ascii=False, indent=2)}

Hotel request:
{json.dumps(request_data, ensure_ascii=False, indent=2)}

Stored user preferences:
{json.dumps(preference_data, ensure_ascii=False, indent=2)}
"""

    def _clean_response_text(self, text: str) -> str:
        text = text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "", 1).strip()

        if text.startswith("```"):
            text = text.replace("```", "", 1).strip()

        if text.endswith("```"):
            text = text[:-3].strip()

        return text

    def _extract_json(self, text: str) -> Dict[str, Any]:
        cleaned_text = self._clean_response_text(text)

        try:
            return json.loads(cleaned_text)

        except json.JSONDecodeError as error:
            raise ValueError(
                f"Gemini returned invalid hotel JSON: {str(error)}. "
                f"Raw response start: {cleaned_text[:1000]}"
            )

    def _mock_hotel_response(
        self,
        trip: Any,
        request: HotelSuggestRequest,
    ) -> HotelAgentResponse:
        """
        Destination-aware fallback when Gemini is unavailable.
        Uses the actual trip destination so geocoding finds the correct area.
        """
        nights = self._calculate_nights(trip)
        dest = trip.destination
        dest_key = dest.lower().replace(" ", "_").replace(",", "")

        hotels = [
            {
                "hotel_key": f"{dest_key}_resort",
                "name": f"{dest} Garden Resort",
                "short_description": f"Comfortable resort near {dest} attractions.",
                "hotel_type": "resort",
                "source": "ai_suggested",
                "area": dest,
                "nights": nights,
                "rooms": request.rooms,
                "estimated_price_per_night_lkr": 18000,
                "total_estimated_price_lkr": 18000 * nights * request.rooms,
                "rating_estimate": 4.2,
                "distance_summary": f"Convenient for {dest} town and nearby attractions.",
                "reason_for_recommendation": "Good balance of comfort, location, and views.",
                "amenities": ["wifi", "breakfast", "parking"],
                "warnings": ["Prices may vary by season."],
                "search_query": f"resort {dest} Sri Lanka",
                "priority_score": 9,
            },
            {
                "hotel_key": f"{dest_key}_hotel",
                "name": f"{dest} City Hotel",
                "short_description": f"Comfort-focused stay close to {dest} town and transport links.",
                "hotel_type": "hotel",
                "source": "ai_suggested",
                "area": f"{dest} town",
                "nights": nights,
                "rooms": request.rooms,
                "estimated_price_per_night_lkr": 22000,
                "total_estimated_price_lkr": 22000 * nights * request.rooms,
                "rating_estimate": 4.3,
                "distance_summary": f"Close to {dest} town centre and transport access.",
                "reason_for_recommendation": "Suitable for comfort and easy access to the area.",
                "amenities": ["wifi", "restaurant", "breakfast"],
                "warnings": ["May be busier during peak season."],
                "search_query": f"hotel {dest} Sri Lanka",
                "priority_score": 8,
            },
            {
                "hotel_key": f"{dest_key}_guest_house",
                "name": f"{dest} Budget Guest House",
                "short_description": f"Budget-friendly guest house near the main {dest} sightseeing area.",
                "hotel_type": "guest_house",
                "source": "ai_suggested",
                "area": dest,
                "nights": nights,
                "rooms": request.rooms,
                "estimated_price_per_night_lkr": 7500,
                "total_estimated_price_lkr": 7500 * nights * request.rooms,
                "rating_estimate": 3.9,
                "distance_summary": f"Affordable stay near {dest} attractions.",
                "reason_for_recommendation": "Good option for keeping the trip under budget.",
                "amenities": ["wifi", "basic breakfast"],
                "warnings": ["Facilities may be basic."],
                "search_query": f"guest house {dest} Sri Lanka",
                "priority_score": 7,
            },
        ]

        data = {
            "trip_id": str(trip.id),
            "destination": dest,
            "nights": nights,
            "rooms": request.rooms,
            "summary": f"Fallback hotel options for {dest}. Retry for AI-curated recommendations.",
            "recommended_hotels": hotels[: request.max_results],
            "question_for_user": "Which hotels would you like to select?",
        }

        return HotelAgentResponse.model_validate(data)

    def suggest_hotels(
        self,
        trip: Any,
        selected_places: List[Any],
        request: HotelSuggestRequest,
        preference: Optional[Any] = None,
    ) -> HotelAgentResponse:

        prompt = self._build_prompt(
            trip=trip,
            selected_places=selected_places,
            request=request,
            preference=preference,
        )

        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GEMINI_HOTEL_RESPONSE_SCHEMA,
                    temperature=0.2,
                    max_output_tokens=8192,
                ),
            )

        except (ClientError, ServerError):
            # Gemini quota (429) or service unavailable (503) — use destination-aware mock
            return self._mock_hotel_response(trip=trip, request=request)

        except Exception as error:
            error_text = str(error).lower()

            if (
                "503" in error_text
                or "unavailable" in error_text
                or "high demand" in error_text
                or "429" in error_text
                or "resource exhausted" in error_text
                or "quota" in error_text
            ):
                return self._mock_hotel_response(trip=trip, request=request)

            raise error

        if not response.text:
            return self._mock_hotel_response(
                trip=trip,
                request=request,
            )

        data = self._extract_json(response.text)
        data = self._normalize_hotel_data(data)

        try:
            result = HotelAgentResponse.model_validate(data)

        except ValidationError as error:
            raise ValueError(
                f"Gemini hotel JSON did not match HotelAgentResponse schema: {error}"
            )

        nights = self._calculate_nights(trip)

        for hotel in result.recommended_hotels:
            if not hotel.hotel_key:
                hotel.hotel_key = self._make_key(hotel.name)

            if not hotel.search_query:
                hotel.search_query = f"{hotel.name} {trip.destination} Sri Lanka"

            hotel.nights = nights
            hotel.rooms = request.rooms

            hotel.total_estimated_price_lkr = (
                hotel.estimated_price_per_night_lkr
                * nights
                * request.rooms
            )

        result = self._enrich_hotels(
            trip=trip,
            result=result,
        )

        result.recommended_hotels.sort(
            key=lambda hotel: hotel.priority_score,
            reverse=True,
        )

        return result