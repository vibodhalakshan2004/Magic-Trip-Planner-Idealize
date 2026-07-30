from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.destination_agent import DestinationAgent
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.preference import Preference
from app.models.selected_place import SelectedPlace
from app.models.trip import Trip
from app.models.user import User
from app.schemas.destination import (
    DestinationAgentResponse,
    DestinationSuggestRequest,
    PlaceSearchResponse,
)
from app.schemas.preference import PreferenceResponse
from app.schemas.selected_place import (
    SelectedPlaceResponse,
    SelectPlacesRequest,
    SelectPlacesResponse,
)
from app.services.geocoder import GeocoderService
from app.services.media_lookup import MediaLookupService
from app.services.place_search import PlaceSearchService
from app.services.trip_access import require_trip_access
from app.services.weather_service import WeatherService

router = APIRouter(
    prefix="/destination",
    tags=["Destination Agent"],
)

geocoder_service = GeocoderService()
media_lookup_service = MediaLookupService()
weather_service = WeatherService()


def _saved_preference_prompt(preference: Preference) -> dict:
    return {
        "has_saved_preferences": True,
        "message": "Saved preferences found. Ask the user whether to use them before generating destination suggestions.",
        "saved_preferences": PreferenceResponse.model_validate(preference).model_dump(mode="json"),
    }


def _coordinate_query(place, trip: Trip) -> str:
    if place.search_query:
        return place.search_query

    return f"{place.name}, {trip.destination}, Sri Lanka"


def _coordinate_queries(place, trip: Trip) -> list[str]:
    queries = []

    if place.search_query:
        queries.append(place.search_query)

    queries.append(f"{place.name}, {trip.destination}, Sri Lanka")
    queries.append(f"{place.name}, Sri Lanka")

    unique_queries = []

    for query in queries:
        if query and query not in unique_queries:
            unique_queries.append(query)

    return unique_queries


@router.post(
    "/trips/{trip_id}/suggest-places",
    response_model=DestinationAgentResponse,
)
def suggest_places_for_trip(
    trip_id: UUID,
    request: DestinationSuggestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = require_trip_access(db, trip_id, current_user.id, write=True)

    preference = (
        db.query(Preference)
        .filter(
            Preference.user_id == current_user.id,
        )
        .first()
    )

    if preference and request.use_saved_preferences is None:
        raise HTTPException(
            status_code=409,
            detail=_saved_preference_prompt(preference),
        )

    if request.use_saved_preferences is False:
        preference = None

    try:
        agent = DestinationAgent()

        result = agent.suggest_places(
            trip=trip,
            request=request,
            preference=preference,
        )

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Destination Agent failed: {str(error)}",
        )
    
@router.post(
    "/trips/{trip_id}/select-places",
    response_model=SelectPlacesResponse,
)
def select_places_for_trip(
    trip_id: UUID,
    request: SelectPlacesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = require_trip_access(db, trip_id, current_user.id, write=True)

    db.query(SelectedPlace).filter(
        SelectedPlace.trip_id == trip.id
    ).delete()

    selected_places = []

    for place in request.selected_places:
        latitude = place.latitude
        longitude = place.longitude

        if latitude is None or longitude is None:
            geocoded = geocoder_service.geocode_candidates(
                _coordinate_queries(place, trip)
            )
            if geocoded:
                latitude = geocoded.get("latitude")
                longitude = geocoded.get("longitude")

        weather_summary = place.weather_summary
        warnings = list(place.warnings)
        image_url = place.image_url

        if latitude is not None and longitude is not None:
            generated_weather_summary, weather_warnings = weather_service.summarize_place_weather(
                latitude=float(latitude),
                longitude=float(longitude),
                start_date=trip.start_date,
                end_date=trip.end_date,
                category=place.category,
            )

            if generated_weather_summary:
                weather_summary = generated_weather_summary

            for weather_warning in weather_warnings:
                if weather_warning not in warnings:
                    warnings.append(weather_warning)

        if not image_url:
            for query in _coordinate_queries(place, trip):
                media = media_lookup_service.lookup_media(query)

                if media.get("image_url"):
                    image_url = media.get("image_url")
                    break

        selected_place = SelectedPlace(
            trip_id=trip.id,
            place_key=place.place_key,
            name=place.name,
            category=place.category,
            source=place.source,
            short_description=place.short_description,
            reason_for_recommendation=place.reason_for_recommendation,
            best_time_to_visit=place.best_time_to_visit,
            opening_hours=place.opening_hours,
            availability_warnings=place.availability_warnings,
            estimated_visit_duration_hours=place.estimated_visit_duration_hours,
            estimated_cost_lkr_per_person=place.estimated_cost_lkr_per_person,
            priority_score=place.priority_score,
            suitable_for=place.suitable_for,
            warnings=warnings,
            search_query=place.search_query,
            weather_summary=weather_summary,
            image_url=image_url,
            latitude=latitude,
            longitude=longitude,
        )

        db.add(selected_place)
        selected_places.append(selected_place)

    db.commit()
    trip.updated_at = datetime.utcnow()
    db.commit()

    for selected_place in selected_places:
        db.refresh(selected_place)

    return {
        "trip_id": trip.id,
        "selected_places_count": len(selected_places),
        "selected_places": selected_places,
        "message": "Selected places saved successfully",
    }


@router.get(
    "/trips/{trip_id}/selected-places",
    response_model=list[SelectedPlaceResponse],
)
def get_selected_places_for_trip(
    trip_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = require_trip_access(db, trip_id, current_user.id)

    return (
        db.query(SelectedPlace)
        .filter(SelectedPlace.trip_id == trip.id)
        .order_by(SelectedPlace.priority_score.desc())
        .all()
    )

@router.get(
    "/trips/{trip_id}/place-search",
    response_model=PlaceSearchResponse,
)
def search_places_for_trip(
    trip_id: UUID,
    query: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if len(query.strip()) < 2:
        return {
            "query": query,
            "suggestions": [],
        }

    trip = require_trip_access(db, trip_id, current_user.id, write=True)

    service = PlaceSearchService()

    suggestions = service.search_places(
        query=query,
        destination=trip.destination,
        country="Sri Lanka",
        limit=5,
    )

    return {
        "query": query,
        "destination": trip.destination,
        "suggestions": suggestions,
    }
