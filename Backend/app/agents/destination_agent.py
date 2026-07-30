import json
import re
from typing import Any, Dict, Optional

from google.genai import types
from google.genai.errors import ClientError, ServerError
from pydantic import ValidationError

from app.agents.gemini_client import client
from app.core.config import settings
from app.schemas.destination import DestinationAgentResponse, DestinationSuggestRequest
from app.services.geocoder import GeocoderService
from app.services.media_lookup import MediaLookupService
from app.services.weather_service import WeatherService


GEMINI_DESTINATION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "trip_id": {
            "type": "string"
        },
        "destination": {
            "type": "string"
        },
        "summary": {
            "type": "string"
        },
        "suggested_places": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "place_key": {
                        "type": "string"
                    },
                    "name": {
                        "type": "string"
                    },
                    "category": {
                        "type": "string"
                    },
                    "short_description": {
                        "type": "string"
                    },
                    "reason_for_recommendation": {
                        "type": "string"
                    },
                    "best_time_to_visit": {
                        "type": "string"
                    },
                    "estimated_visit_duration_hours": {
                        "type": "number"
                    },
                    "estimated_cost_lkr_per_person": {
                        "type": "number"
                    },
                    "priority_score": {
                        "type": "integer"
                    },
                    "suitable_for": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "warnings": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "search_query": {
                        "type": "string"
                    }
                },
                "required": [
                    "place_key",
                    "name",
                    "category",
                    "short_description",
                    "reason_for_recommendation",
                    "best_time_to_visit",
                    "estimated_visit_duration_hours",
                    "estimated_cost_lkr_per_person",
                    "priority_score",
                    "suitable_for",
                    "warnings",
                    "search_query"
                ]
            }
        },
        "question_for_user": {
            "type": "string"
        }
    },
    "required": [
        "trip_id",
        "destination",
        "summary",
        "suggested_places",
        "question_for_user"
    ]
}


class DestinationAgent:

    def __init__(self):
        self.geocoder = GeocoderService()
        self.media_lookup = MediaLookupService()
        self.weather_service = WeatherService()

    def _make_place_query(self, place: Any, trip: Any) -> str:
        if getattr(place, "search_query", None):
            return place.search_query

        return f"{place.name}, {trip.destination}, Sri Lanka"

    def _adjust_priority_for_weather(self, place: Any, weather_warnings: list[str]) -> int:
        priority_score = int(getattr(place, "priority_score", 5) or 5)
        weather_text = " ".join(weather_warnings).lower()

        if "thunderstorms" in weather_text:
            priority_score -= 2
        elif "rain is likely" in weather_text or "beach conditions may be less favorable" in weather_text:
            priority_score -= 1

        if "prefer morning or sunset visits" in weather_text:
            priority_score = max(priority_score, 4)

        return max(1, min(10, priority_score))

    def _mock_destination_response(
        self,
        trip: Any,
    ) -> DestinationAgentResponse:
        """
        Destination-aware fallback used when the Gemini API is unavailable.
        Generates generic place suggestions based on the actual trip destination,
        so geocoding and routing will find the correct area instead of returning
        hardcoded Ella-only places for every trip.
        """
        dest = trip.destination
        dest_key = dest.lower().replace(" ", "_").replace(",", "")

        data = {
            "trip_id": str(trip.id),
            "destination": dest,
            "summary": (
                f"Fallback suggestions for {dest} were generated because the AI service is temporarily unavailable. "
                "These are generic landmark categories — please retry for AI-curated picks."
            ),
            "suggested_places": [
                {
                    "place_key": f"{dest_key}_town_center",
                    "name": f"{dest} Town Center",
                    "category": "culture",
                    "short_description": f"Main town area of {dest} with local shops and restaurants.",
                    "reason_for_recommendation": "Good starting point to explore the area.",
                    "best_time_to_visit": "morning",
                    "estimated_visit_duration_hours": 2.0,
                    "estimated_cost_lkr_per_person": 0,
                    "priority_score": 8,
                    "suitable_for": ["families", "couples", "friends"],
                    "warnings": [],
                    "search_query": f"{dest} town center Sri Lanka",
                },
                {
                    "place_key": f"{dest_key}_main_temple",
                    "name": f"{dest} Main Temple",
                    "category": "religious",
                    "short_description": f"Notable temple or religious site near {dest}.",
                    "reason_for_recommendation": "Cultural and historical significance.",
                    "best_time_to_visit": "morning",
                    "estimated_visit_duration_hours": 1.5,
                    "estimated_cost_lkr_per_person": 0,
                    "priority_score": 7,
                    "suitable_for": ["families", "culture seekers"],
                    "warnings": ["Dress modestly when visiting religious sites."],
                    "search_query": f"temple {dest} Sri Lanka",
                },
                {
                    "place_key": f"{dest_key}_market",
                    "name": f"{dest} Local Market",
                    "category": "shopping",
                    "short_description": f"Local produce and craft market in {dest}.",
                    "reason_for_recommendation": "Great for experiencing local culture and buying souvenirs.",
                    "best_time_to_visit": "morning",
                    "estimated_visit_duration_hours": 1.0,
                    "estimated_cost_lkr_per_person": 500,
                    "priority_score": 6,
                    "suitable_for": ["families", "photographers"],
                    "warnings": [],
                    "search_query": f"market {dest} Sri Lanka",
                },
                {
                    "place_key": f"{dest_key}_viewpoint",
                    "name": f"{dest} Viewpoint",
                    "category": "viewpoint",
                    "short_description": f"Scenic overlook offering views around {dest}.",
                    "reason_for_recommendation": "Good for photography and enjoying the landscape.",
                    "best_time_to_visit": "sunrise",
                    "estimated_visit_duration_hours": 1.5,
                    "estimated_cost_lkr_per_person": 0,
                    "priority_score": 7,
                    "suitable_for": ["photography", "nature lovers"],
                    "warnings": [],
                    "search_query": f"viewpoint {dest} Sri Lanka",
                },
                {
                    "place_key": f"{dest_key}_nature_park",
                    "name": f"{dest} Nature Area",
                    "category": "nature",
                    "short_description": f"Natural area or park near {dest} suitable for walks.",
                    "reason_for_recommendation": "Ideal for outdoor activities and nature appreciation.",
                    "best_time_to_visit": "morning",
                    "estimated_visit_duration_hours": 2.0,
                    "estimated_cost_lkr_per_person": 0,
                    "priority_score": 7,
                    "suitable_for": ["nature lovers", "families"],
                    "warnings": [],
                    "search_query": f"nature park {dest} Sri Lanka",
                },
            ],
            "question_for_user": "Which places would you like to add to your trip?",
        }

        return DestinationAgentResponse.model_validate(data)

    def _enrich_with_weather(self, trip: Any, result: DestinationAgentResponse) -> DestinationAgentResponse:
        for place in result.suggested_places:
            query = self._make_place_query(place, trip)

            if not getattr(place, "image_url", None):
                try:
                    media = self.media_lookup.lookup_media(query)
                    place.image_url = media.get("image_url")
                except Exception:
                    pass

            try:
                geocoded = self.geocoder.geocode(query)

                if not geocoded:
                    continue

                place.latitude = geocoded.get("latitude")
                place.longitude = geocoded.get("longitude")

                weather_summary, weather_warnings = self.weather_service.summarize_place_weather(
                    latitude=float(place.latitude),
                    longitude=float(place.longitude),
                    start_date=trip.start_date,
                    end_date=trip.end_date,
                    category=place.category,
                )

                if weather_summary:
                    place.weather_summary = weather_summary

                for weather_warning in weather_warnings:
                    if weather_warning not in place.warnings:
                        place.warnings.append(weather_warning)

                place.priority_score = self._adjust_priority_for_weather(
                    place,
                    weather_warnings,
                )

            except Exception:
                continue

        return result

    def _build_prompt(
        self,
        trip: Any,
        request: DestinationSuggestRequest,
        preference: Optional[Any] = None,
    ) -> str:

        trip_data = {
            "trip_id": str(trip.id),
            "start_location": trip.start_location,
            "destination": trip.destination,
            "start_date": str(trip.start_date),
            "end_date": str(trip.end_date),
            "budget_min": trip.budget_min,
            "budget_max": trip.budget_max,
            "travelers": trip.travelers,
            "transport_type": trip.transport_type,
        }

        request_data = request.model_dump(mode="json")

        preference_data = None

        if preference:
            preference_data = {
                "travel_style": getattr(preference, "travel_style", None),
                "food_preference": getattr(preference, "food_preference", None),
                "hotel_preference": getattr(preference, "preferred_hotel_type", None),
                "transport_preference": getattr(preference, "preferred_transport", None),
                "interests": getattr(preference, "interests", None),
            }

        return f"""
You are the Destination Discovery Agent for MagicTripPlanner.

Recommend exactly 5 real attractions or places near the destination.

Rules:
- Return only JSON.
- Do not use markdown.
- Keep every text field short.
- Do not write long paragraphs.
- Do not use double quotes inside string values.
- Use simple strings only.
- priority_score must be between 1 and 10.
- estimated_cost_lkr_per_person must be a number.
- estimated_visit_duration_hours must be a number.
- category should be one of: nature, culture, food, adventure, religious, viewpoint, beach, shopping, historical, other.
- best_time_to_visit should be one of: sunrise, morning, afternoon, evening, sunset, flexible.
- Prefer places that still make sense if weather is warm or occasionally rainy during the trip dates.
- Avoid over-prioritizing weather-sensitive outdoor stops when indoor or flexible alternatives fit the same interests.

Trip data:
{json.dumps(trip_data, ensure_ascii=False, indent=2)}

User destination request:
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
            match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)

            if not match:
                raise ValueError(
                    f"Gemini did not return JSON. Raw response: {cleaned_text[:1000]}"
                )

            try:
                return json.loads(match.group(0))

            except json.JSONDecodeError:
                raise ValueError(
                    f"Gemini returned invalid JSON: {str(error)}. "
                    f"Raw response start: {cleaned_text[:1000]}"
                )

    def suggest_places(
        self,
        trip: Any,
        request: DestinationSuggestRequest,
        preference: Optional[Any] = None,
    ) -> DestinationAgentResponse:

        prompt = self._build_prompt(
            trip=trip,
            request=request,
            preference=preference,
        )

        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GEMINI_DESTINATION_RESPONSE_SCHEMA,
                    temperature=0.1,
                    max_output_tokens=8192,
                ),
            )

        except (ClientError, ServerError):
            # Gemini quota (429) or service unavailable (503) — use destination-aware mock
            result = self._mock_destination_response(trip=trip)
            return self._enrich_with_weather(trip=trip, result=result)

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
                result = self._mock_destination_response(trip=trip)
                return self._enrich_with_weather(trip=trip, result=result)

            raise error

        if not response.text:
            result = self._mock_destination_response(trip=trip)
            return self._enrich_with_weather(trip=trip, result=result)

        data = self._extract_json(response.text)

        try:
            result = DestinationAgentResponse.model_validate(data)

        except ValidationError as error:
            raise ValueError(
                f"Gemini JSON did not match DestinationAgentResponse schema: {error}"
            )

        result = self._enrich_with_weather(
            trip=trip,
            result=result,
        )

        result.suggested_places.sort(
            key=lambda place: place.priority_score,
            reverse=True,
        )

        return result
