import math
import re
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.hotel_agent import HotelAgent
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.preference import Preference
from app.models.route_plan import RoutePlan
from app.models.selected_hotel import SelectedHotel
from app.models.selected_place import SelectedPlace
from app.models.trip import Trip
from app.models.user import User
from app.schemas.hotel import (
    DailyHotelSelectRequest,
    DailyHotelSelectResponse,
    DailyHotelSuggestionResponse,
    DailyHotelSuggestRequest,
    HotelAgentResponse,
    HotelSearchResponse,
    HotelSuggestRequest,
    SelectedHotelResponse,
    SelectHotelsRequest,
    SelectHotelsResponse,
)
from app.schemas.preference import PreferenceResponse
from app.services.geocoder import GeocoderService
from app.services.hotel_search import HotelSearchService
from app.services.media_lookup import MediaLookupService
from app.services.transport_cost import estimate_segment_transport_cost
from app.services.trip_access import require_trip_access

router = APIRouter(
    prefix="/hotels",
    tags=["Hotel Agent"],
)

geocoder_service = GeocoderService()
media_lookup_service = MediaLookupService()


def _saved_preference_prompt(preference: Preference) -> dict:
    return {
        "has_saved_preferences": True,
        "message": "Saved preferences found. Ask the user whether to use them before generating hotel suggestions.",
        "saved_preferences": PreferenceResponse.model_validate(preference).model_dump(mode="json"),
    }


def make_hotel_key(name: str) -> str:
    key = name.lower().strip()
    key = re.sub(r"[^a-z0-9]+", "_", key)
    key = key.strip("_")

    if not key:
        key = "hotel"

    return key[:80]


def _hotel_queries(hotel, trip: Trip) -> list[str]:
    queries = []

    if hotel.search_query:
        queries.append(hotel.search_query)

    queries.append(f"{hotel.name}, {trip.destination}, Sri Lanka")
    queries.append(f"{hotel.name} {trip.destination} Sri Lanka")
    queries.append(f"{hotel.name}, Sri Lanka")

    simplified_name = re.sub(r"[^A-Za-z0-9 ]+", " ", hotel.name).strip()

    if simplified_name and simplified_name != hotel.name:
        queries.append(f"{simplified_name}, {trip.destination}, Sri Lanka")
        queries.append(f"{simplified_name} {trip.destination} Sri Lanka")

    unique_queries = []

    for query in queries:
        cleaned_query = " ".join(query.split())

        if cleaned_query and cleaned_query not in unique_queries:
            unique_queries.append(cleaned_query)

    return unique_queries


def _compose_hotel_short_description(hotel) -> str:
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


def _latest_confirmed_route(db: Session, trip: Trip) -> RoutePlan | None:
    return (
        db.query(RoutePlan)
        .filter(
            RoutePlan.trip_id == trip.id,
            RoutePlan.route_status == "confirmed",
        )
        .order_by(RoutePlan.created_at.desc())
        .first()
    )


def _day_end_point(route_plan: RoutePlan, day_number: int, trip: Trip) -> dict:
    days = route_plan.days or []
    day = next((item for item in days if int(item.get("day_number", 0)) == day_number), None)

    if day:
        stops = day.get("stops") or []
        if stops:
            stop = stops[-1]
            if stop.get("latitude") is not None and stop.get("longitude") is not None:
                return {
                    "name": stop.get("name") or f"Day {day_number} final stop",
                    "latitude": float(stop["latitude"]),
                    "longitude": float(stop["longitude"]),
                }

        coordinates = day.get("day_path_coordinates") or []
        if coordinates:
            coordinate = coordinates[-1]
            return {
                "name": day.get("end_point_name") or f"Day {day_number} endpoint",
                "latitude": float(coordinate["latitude"]),
                "longitude": float(coordinate["longitude"]),
            }

    geocoded = geocoder_service.geocode(f"{trip.destination}, Sri Lanka")
    if not geocoded:
        raise HTTPException(status_code=400, detail="Could not locate the route day endpoint.")

    return {
        "name": trip.destination,
        "latitude": geocoded["latitude"],
        "longitude": geocoded["longitude"],
    }


def _add_transfer_fields(hotel: dict, origin: dict, trip: Trip) -> dict:
    if hotel.get("latitude") is None or hotel.get("longitude") is None:
        return {
            **hotel,
            "transfer_distance_km": 0,
            "transfer_time_minutes": 0,
            "transfer_cost_lkr": 0,
        }

    straight_line_distance = _haversine_distance_km(
        float(origin["latitude"]),
        float(origin["longitude"]),
        float(hotel["latitude"]),
        float(hotel["longitude"]),
    )
    distance = round(straight_line_distance * 1.25, 1)
    speed_kmh = {
        "walking": 4.5,
        "bike": 14,
        "bus": 25,
        "train": 35,
        "car": 35,
        "taxi": 35,
        "mixed": 30,
    }.get(trip.transport_type, 30)
    duration = round(max(distance / speed_kmh * 60, 5), 0) if distance else 0

    transfer_cost = estimate_segment_transport_cost(
        transport_type=trip.transport_type,
        distance_km=distance,
        travelers=trip.travelers,
    )

    return {
        **hotel,
        "transfer_distance_km": distance,
        "transfer_time_minutes": duration,
        "transfer_cost_lkr": transfer_cost,
        "distance_summary": hotel.get("distance_summary") or f"About {distance} km from the day route endpoint.",
    }


def _haversine_distance_km(
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
) -> float:
    earth_radius_km = 6371.0
    latitude_delta = math.radians(destination_latitude - origin_latitude)
    longitude_delta = math.radians(destination_longitude - origin_longitude)
    origin_latitude_radians = math.radians(origin_latitude)
    destination_latitude_radians = math.radians(destination_latitude)
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(origin_latitude_radians)
        * math.cos(destination_latitude_radians)
        * math.sin(longitude_delta / 2) ** 2
    )
    return earth_radius_km * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))


@router.post(
    "/trips/{trip_id}/suggest-hotels",
    response_model=HotelAgentResponse,
)
def suggest_hotels_for_trip(
    trip_id: UUID,
    request: HotelSuggestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = require_trip_access(db, trip_id, current_user.id, write=True)

    selected_places = (
        db.query(SelectedPlace)
        .filter(
            SelectedPlace.trip_id == trip.id,
        )
        .all()
    )

    if not selected_places:
        raise HTTPException(
            status_code=400,
            detail="Please select at least one place before requesting hotels.",
        )

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
        agent = HotelAgent()

        return agent.suggest_hotels(
            trip=trip,
            selected_places=selected_places,
            request=request,
            preference=preference,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Hotel Agent failed: {str(error)}",
        )


@router.get(
    "/trips/{trip_id}/hotel-search",
    response_model=HotelSearchResponse,
)
def search_hotels_for_trip(
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

    try:
        service = HotelSearchService()

        suggestions = service.search_hotels(
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

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Hotel search failed: {str(error)}",
        )


@router.post(
    "/trips/{trip_id}/select-hotels",
    response_model=SelectHotelsResponse,
)
def select_hotels_for_trip(
    trip_id: UUID,
    request: SelectHotelsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = require_trip_access(db, trip_id, current_user.id, write=True)

    db.query(SelectedHotel).filter(
        SelectedHotel.trip_id == trip.id
    ).delete(synchronize_session=False)

    selected_hotels = []

    for hotel in request.selected_hotels:
        hotel_key = hotel.hotel_key

        if not hotel_key:
            hotel_key = make_hotel_key(hotel.name)

        search_query = hotel.search_query

        if not search_query:
            search_query = f"{hotel.name} {trip.destination} Sri Lanka"

        nights = hotel.nights

        if hotel.check_in_date and hotel.check_out_date:
            nights = (hotel.check_out_date - hotel.check_in_date).days

            if nights <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid check-in/check-out dates for hotel: {hotel.name}",
                )

        total_price = (
            hotel.estimated_price_per_night_lkr
            * nights
            * hotel.rooms
        )

        if hotel.total_estimated_price_lkr > 0:
            total_price = hotel.total_estimated_price_lkr

        latitude = hotel.latitude
        longitude = hotel.longitude
        short_description = hotel.short_description
        image_url = hotel.image_url

        if latitude is None or longitude is None:
            for query in _hotel_queries(hotel, trip):
                geocoded = geocoder_service.geocode(query)

                if geocoded:
                    latitude = geocoded.get("latitude")
                    longitude = geocoded.get("longitude")
                    break

        if not image_url or not short_description:
            for query in _hotel_queries(hotel, trip):
                media = media_lookup_service.lookup_media(query)

                if not short_description and media.get("description"):
                    short_description = media.get("description")

                if not image_url and media.get("image_url"):
                    image_url = media.get("image_url")

                if short_description and image_url:
                    break

        if not short_description:
            short_description = _compose_hotel_short_description(hotel)

        selected_hotel = SelectedHotel(
            trip_id=trip.id,
            hotel_key=hotel_key,
            name=hotel.name,
            short_description=short_description,
            hotel_type=hotel.hotel_type,
            source=hotel.source,
            area=hotel.area,
            check_in_date=hotel.check_in_date,
            check_out_date=hotel.check_out_date,
            nights=nights,
            rooms=hotel.rooms,
            estimated_price_per_night_lkr=hotel.estimated_price_per_night_lkr,
            total_estimated_price_lkr=total_price,
            rating_estimate=hotel.rating_estimate,
            latitude=latitude,
            longitude=longitude,
            distance_summary=hotel.distance_summary,
            reason_for_recommendation=hotel.reason_for_recommendation,
            amenities=hotel.amenities,
            warnings=hotel.warnings,
            search_query=search_query,
            image_url=image_url,
        )

        db.add(selected_hotel)
        selected_hotels.append(selected_hotel)

    trip.updated_at = datetime.utcnow()
    db.commit()

    for selected_hotel in selected_hotels:
        db.refresh(selected_hotel)

    return {
        "trip_id": trip.id,
        "selected_hotels_count": len(selected_hotels),
        "selected_hotels": selected_hotels,
        "message": "Selected hotels saved successfully",
    }


@router.get(
    "/trips/{trip_id}/selected-hotels",
    response_model=list[SelectedHotelResponse],
)
def get_selected_hotels_for_trip(
    trip_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = require_trip_access(db, trip_id, current_user.id)

    return (
        db.query(SelectedHotel)
        .filter(SelectedHotel.trip_id == trip.id)
        .order_by(SelectedHotel.day_number.asc().nullslast(), SelectedHotel.created_at.desc())
        .all()
    )


@router.post(
    "/trips/{trip_id}/days/{day_number}/suggest",
    response_model=DailyHotelSuggestionResponse,
)
def suggest_hotels_for_route_day(
    trip_id: UUID,
    day_number: int,
    request: DailyHotelSuggestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = require_trip_access(db, trip_id, current_user.id, write=True)

    route_plan = _latest_confirmed_route(db, trip)

    if not route_plan:
        raise HTTPException(status_code=400, detail="Please confirm a route before selecting daily hotels.")

    origin = _day_end_point(route_plan, day_number, trip)
    if request.hotel_preference:
        query = request.hotel_preference
    else:
        query = "hotel" if request.hotel_type == "any" else request.hotel_type.replace("_", " ")

    service = HotelSearchService()
    raw_suggestions = service.search_hotels(
        query=query,
        destination=f"{origin['name']}, {trip.destination}",
        country="Sri Lanka",
        limit=request.max_results,
        latitude=float(origin["latitude"]),
        longitude=float(origin["longitude"]),
        radius_km=request.radius_km,
    )

    suggestions = []
    for hotel in raw_suggestions:
        if request.hotel_type != "any" and hotel.get("hotel_type") != request.hotel_type:
            continue
        enriched = _add_transfer_fields(hotel, origin, trip)
        if enriched["transfer_distance_km"] > request.radius_km:
            continue
        enriched["day_number"] = day_number
        enriched["route_plan_id"] = route_plan.id
        enriched["rooms"] = request.rooms
        suggestions.append(enriched)

    suggestions.sort(key=lambda item: item.get("transfer_distance_km", float("inf")))

    return {
        "trip_id": trip.id,
        "day_number": day_number,
        "route_plan_id": route_plan.id,
        "suggestions": suggestions,
        "summary": f"Hotel suggestions within {request.radius_km:g} km of the end of day {day_number}.",
    }


@router.post(
    "/trips/{trip_id}/days/{day_number}/select",
    response_model=DailyHotelSelectResponse,
)
def select_hotel_for_route_day(
    trip_id: UUID,
    day_number: int,
    request: DailyHotelSelectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = require_trip_access(db, trip_id, current_user.id, write=True)

    route_plan = _latest_confirmed_route(db, trip)

    if not route_plan:
        raise HTTPException(status_code=400, detail="Please confirm a route before selecting daily hotels.")

    db.query(SelectedHotel).filter(
        SelectedHotel.trip_id == trip.id,
        SelectedHotel.day_number == day_number,
    ).delete(synchronize_session=False)

    if request.go_home_without_hotel:
        trip.updated_at = datetime.utcnow()
        db.commit()
        return {
            "trip_id": trip.id,
            "day_number": day_number,
            "selected_hotel": None,
            "message": "No hotel selected for this day.",
        }

    if not request.hotel:
        raise HTTPException(status_code=400, detail="Please choose a hotel for this day.")

    hotel = request.hotel
    hotel_key = hotel.hotel_key or make_hotel_key(hotel.name)
    nights = max(hotel.nights or 1, 1)
    total_price = hotel.total_estimated_price_lkr or (
        hotel.estimated_price_per_night_lkr * nights * hotel.rooms
    )

    selected_hotel = SelectedHotel(
        trip_id=trip.id,
        route_plan_id=route_plan.id,
        day_number=day_number,
        hotel_key=hotel_key,
        name=hotel.name,
        short_description=hotel.short_description or _compose_hotel_short_description(hotel),
        hotel_type=hotel.hotel_type,
        source=hotel.source,
        area=hotel.area,
        check_in_date=hotel.check_in_date,
        check_out_date=hotel.check_out_date,
        nights=nights,
        rooms=hotel.rooms,
        estimated_price_per_night_lkr=hotel.estimated_price_per_night_lkr,
        total_estimated_price_lkr=total_price,
        rating_estimate=hotel.rating_estimate,
        latitude=hotel.latitude,
        longitude=hotel.longitude,
        distance_summary=hotel.distance_summary,
        transfer_distance_km=hotel.transfer_distance_km,
        transfer_time_minutes=hotel.transfer_time_minutes,
        transfer_cost_lkr=hotel.transfer_cost_lkr,
        reason_for_recommendation=hotel.reason_for_recommendation,
        amenities=hotel.amenities,
        warnings=hotel.warnings,
        search_query=hotel.search_query,
        image_url=hotel.image_url,
    )

    db.add(selected_hotel)
    trip.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(selected_hotel)

    return {
        "trip_id": trip.id,
        "day_number": day_number,
        "selected_hotel": selected_hotel,
        "message": "Daily hotel selection saved.",
    }


@router.get(
    "/trips/{trip_id}/daily-selections",
    response_model=list[SelectedHotelResponse],
)
def get_daily_hotel_selections(
    trip_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = require_trip_access(db, trip_id, current_user.id)

    return (
        db.query(SelectedHotel)
        .filter(SelectedHotel.trip_id == trip.id)
        .order_by(SelectedHotel.day_number.asc().nullslast(), SelectedHotel.created_at.desc())
        .all()
    )
