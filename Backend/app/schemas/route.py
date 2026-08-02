from datetime import date
from typing import Any, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoutePlanRequest(BaseModel):
    day_start_time: str = Field(
        default="08:00",
        examples=["08:00"]
    )

    return_to_hotel: bool = False
    return_to_start_location: bool = True
    include_hotels: bool = False

    manual_schedule: List["ManualRouteStop"] | None = None


class ManualRouteStop(BaseModel):
    place_key: str
    day_number: int = Field(default=1, ge=1)
    start_time: str | None = None
    visit_duration_hours: float | None = Field(default=None, gt=0, le=12)


class Coordinate(BaseModel):
    latitude: float
    longitude: float


class RouteInstruction(BaseModel):
    instruction: str
    distance_km: float
    duration_minutes: float


class RouteSegment(BaseModel):
    from_name: str
    to_name: str

    start_time: str
    end_time: str

    distance_km: float
    duration_minutes: float
    transport_cost_lkr: float = 0
    transport_cost_source: str = "Planning estimate"
    fare_per_person_lkr: float | None = None
    passenger_count: int = 1
    fare_is_live: bool = False

    encoded_polyline: str
    path_coordinates: List[Coordinate]

    instructions: List[RouteInstruction]


class ItineraryStop(BaseModel):
    place_key: str
    name: str
    category: str

    date: date
    day_number: int

    arrival_time: str
    start_time: str
    end_time: str

    best_time_to_visit: str | None
    opening_hours: str | None = None
    availability_warnings: List[str] = Field(default_factory=list)

    visit_duration_hours: float

    latitude: float
    longitude: float

    travel_time_from_previous_minutes: float
    travel_distance_from_previous_km: float

    note: str | None = None


class DayRoutePlan(BaseModel):
    day_number: int
    date: date

    start_time: str
    end_time: str

    start_point_name: str
    end_point_name: str

    stops: List[ItineraryStop]
    segments: List[RouteSegment]

    day_distance_km: float
    day_travel_time_minutes: float
    day_transport_cost_lkr: float = 0

    day_encoded_polyline: str
    day_path_coordinates: List[Coordinate]


class RoutePlanResponse(BaseModel):
    trip_id: UUID
    destination: str

    start_date: date
    end_date: date

    transport_type: str

    total_distance_km: float
    total_travel_time_minutes: float
    total_transport_cost_lkr: float = 0

    full_encoded_polyline: str

    days: List[DayRoutePlan]

    map_provider: str = "OpenRouteService or OSRM"
    route_status: str = "draft"
    summary: str


class SavedRoutePlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trip_id: UUID
    total_distance_km: float
    total_travel_time_minutes: float
    total_transport_cost_lkr: float = 0
    route_status: str = "draft"
    map_provider: str | None = None
    summary: str | None = None
    full_encoded_polyline: str | None
    days: List[dict[str, Any]]
