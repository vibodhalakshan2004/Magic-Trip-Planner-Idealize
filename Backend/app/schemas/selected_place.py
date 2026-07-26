from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SelectedPlaceInput(BaseModel):
    place_key: str
    name: str
    category: str
    source: str

    short_description: str | None = None
    reason_for_recommendation: str | None = None
    best_time_to_visit: str | None = None
    opening_hours: str | None = None
    availability_warnings: List[str] = Field(default_factory=list)

    estimated_visit_duration_hours: float = Field(default=1.5, gt=0)
    estimated_cost_lkr_per_person: float = Field(default=0, ge=0)

    priority_score: int = Field(default=5, ge=1, le=10)

    suitable_for: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    search_query: str | None = None
    weather_summary: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None


class SelectPlacesRequest(BaseModel):
    selected_places: List[SelectedPlaceInput] = Field(..., min_length=1)


class SelectedPlaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trip_id: UUID

    place_key: str
    name: str
    category: str
    source: str

    short_description: str | None
    reason_for_recommendation: str | None
    best_time_to_visit: str | None
    opening_hours: str | None
    availability_warnings: List[str]

    estimated_visit_duration_hours: float
    estimated_cost_lkr_per_person: float
    priority_score: int

    suitable_for: List[str]
    warnings: List[str]

    search_query: str | None
    weather_summary: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None


class SelectPlacesResponse(BaseModel):
    trip_id: UUID
    selected_places_count: int
    selected_places: List[SelectedPlaceResponse]
    message: str
