from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FullPlanJobCreate(BaseModel):
    use_saved_preferences: bool = True
    interests: list[str] = Field(default_factory=list)
    trip_style: Literal["relaxed", "balanced", "packed"] = "balanced"
    special_notes: str = ""
    max_places: int = Field(default=6, ge=3, le=10)
    hotel_type: str = "any"
    hotel_preference: str = ""
    rooms: int = Field(default=1, ge=1, le=10)
    food_cost_per_person_per_day_lkr: float = Field(default=2500, ge=0)
    shopping_other_cost_lkr: float = Field(default=0, ge=0)


class PlanningJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trip_id: UUID
    kind: str
    status: str
    progress: int
    current_stage: str
    result: dict[str, Any] | None
    error: str | None
    cancel_requested: bool
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime


class TripVersionCreate(BaseModel):
    label: str = Field(default="Manual save", min_length=2, max_length=160)


class TripVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trip_id: UUID
    version_number: int
    label: str
    created_at: datetime

